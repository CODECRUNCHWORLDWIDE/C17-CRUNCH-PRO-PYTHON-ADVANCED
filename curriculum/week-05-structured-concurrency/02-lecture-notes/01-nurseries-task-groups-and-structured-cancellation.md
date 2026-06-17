# Lecture 1 — Nurseries, `TaskGroup`, and Structured Cancellation

> **Duration:** ~2 hours. **Outcome:** You can state Nathaniel J. Smith's one-rule definition of structured concurrency; you can implement an asyncio `TaskGroup` analogue in 80 lines; you can read `Lib/asyncio/taskgroups.py` end-to-end; you can predict exactly which tasks are running, cancelled, or pending after any sequence of `tg.create_task(...)` calls and child failures; and you can explain why this single API change between Python 3.10 and 3.11 retired an entire bug class.

## 1. The bug that ate the 2010s

Open a terminal. Type this:

```python
import asyncio

async def child():
    await asyncio.sleep(10)
    print("child done")

async def parent():
    asyncio.create_task(child())   # <-- here
    print("parent returning")

asyncio.run(parent())
```

Run it. The output is:

```
parent returning
sys:1: RuntimeWarning: coroutine 'child' was never awaited
Task was destroyed but it is pending!
task: <Task pending name='Task-2' coro=<child() running at .../t.py:3>>
```

The child never ran. `asyncio.run` returned when `parent` returned, and as part of shutdown it ran a `Task.cancel()` on every still-pending task. The child was never given a chance to finish, but the parent never *waited* for it either. Worst of both worlds: the work is lost, and the diagnostic comes out *after* the program has technically succeeded.

This pattern — `create_task` without `await` — is the original sin of asyncio. It scales: replace `child()` with a real HTTP call, the parent is a request handler, and you have a production server that quietly drops one in a thousand log writes. The fault is structural. `asyncio.create_task` returns a `Task`, but the *caller* now owns the reference and is responsible for `await`-ing it. If the caller forgets, the child leaks. The compiler does not warn you; the type system does not warn you; if you are lucky, asyncio prints a runtime warning at shutdown, but only because shutdown happens to enumerate pending tasks.

Every comparable primitive has the same defect: `threading.Thread.start()`, `os.fork()`, Go's `go` statement, `pthread_create`. Smith's 2018 essay frames it sharply: *a function that spawns a concurrent task and returns without waiting for it has destroyed the relationship between caller and work*. The work is now floating. It outlives the function that created it. Its errors land elsewhere. Cancellation — if it ever comes — races whatever buffer the work is in the middle of.

Structured concurrency is the rule that fixes this. It is one sentence:

> **Every concurrent task must have a syntactic parent block, and the block must not return until every child task is done.**

That is the whole idea. Trio (2017) was the first Python library built around this rule. asyncio retrofitted it in 3.11 as `TaskGroup` (PEP 654). After today's lecture you will recognise every line of `Lib/asyncio/taskgroups.py` (~250 lines as of 3.13).

## 2. Smith's rule, restated as an API

The rule translates into a context manager:

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(child_a())
    tg.create_task(child_b())
    tg.create_task(child_c())
# At this point all three children are done.
# If any of them raised, we are inside an ExceptionGroup.
```

The `async with` block is the parent. The `tg.create_task(...)` calls add children. The `__aexit__` of the `async with` *waits* for every child to finish. There is no way to leak a task here. There is no way for a child to outlive the block. There is no way for an error in `child_b` to silently disappear — every error survives into an `ExceptionGroup` raised on exit (PEP 654; we revisit `except*` in §6).

Compare with the unstructured version of the same fan-out:

```python
# Unstructured: the child is unowned.
t1 = asyncio.create_task(child_a())
t2 = asyncio.create_task(child_b())
t3 = asyncio.create_task(child_c())
await asyncio.gather(t1, t2, t3)        # forgot? leaked. raised?  silent.
```

Three places to be careful: did you `await` the gather; did you handle exceptions correctly; if one raised, did you cancel the other two. The `TaskGroup` version is one place: the `async with`. That is the win.

## 3. The asyncio implementation, in 80 lines

Read `Lib/asyncio/taskgroups.py` in CPython main. The file is ~250 lines but most of that is error reporting. The core is this skeleton:

```python
class TaskGroup:
    def __init__(self):
        self._loop = None
        self._parent_task = None
        self._parent_cancel_requested = False
        self._tasks = set()
        self._errors = []
        self._base_error = None
        self._on_completed_fut = None
        self._aborting = False
        self._entered = False
        self._exiting = False

    async def __aenter__(self):
        self._entered = True
        self._loop = events.get_running_loop()
        self._parent_task = tasks.current_task(self._loop)
        return self

    def create_task(self, coro, *, name=None, context=None):
        if not self._entered:
            raise RuntimeError("TaskGroup has not been entered")
        if self._exiting and not self._tasks:
            raise RuntimeError("TaskGroup is finished")
        if self._aborting:
            raise RuntimeError("TaskGroup is shutting down")
        task = self._loop.create_task(coro, name=name, context=context)
        task.add_done_callback(self._on_task_done)
        self._tasks.add(task)
        return task

    def _on_task_done(self, task):
        self._tasks.discard(task)
        if self._on_completed_fut is not None and not self._tasks:
            if not self._on_completed_fut.done():
                self._on_completed_fut.set_result(True)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is None:
            return
        self._errors.append(exc)
        if self._is_base_error(exc) and self._base_error is None:
            self._base_error = exc
        if self._parent_task.done():
            return  # already exiting
        self._abort()
        if not self._parent_cancel_requested:
            self._parent_cancel_requested = True
            self._parent_task.cancel()

    def _abort(self):
        self._aborting = True
        for t in self._tasks:
            if not t.done():
                t.cancel()

    async def __aexit__(self, et, exc, tb):
        self._exiting = True
        # Cancel siblings if we got here via an exception from inside the block.
        if exc is not None and self._is_base_error(exc) and self._base_error is None:
            self._base_error = exc
        propagate_cancellation_error = (
            exc if et is exceptions.CancelledError else None
        )
        if et is not None and not self._aborting:
            self._abort()
        # Wait for every child task to finish.
        while self._tasks:
            if self._on_completed_fut is None:
                self._on_completed_fut = self._loop.create_future()
            try:
                await self._on_completed_fut
            except exceptions.CancelledError as ex:
                if not self._aborting:
                    propagate_cancellation_error = ex
                    self._abort()
            self._on_completed_fut = None
        # All children done. Maybe raise.
        if self._base_error is not None:
            raise self._base_error
        if self._parent_cancel_requested:
            # Absorb the cancel we issued on the parent task so it doesn't leak.
            if self._parent_task.uncancel() == 0 and propagate_cancellation_error is None:
                pass
        if exc is not None and exc is not propagate_cancellation_error:
            self._errors.append(exc)
        if self._errors:
            errors = self._errors
            self._errors = None
            me = BaseExceptionGroup("unhandled errors in a TaskGroup", errors)
            raise me from None
```

(This is paraphrased from `Lib/asyncio/taskgroups.py` in 3.13. The original is ~250 lines including the `_is_base_error` helper, docstrings, and various 3.11 → 3.13 hardenings around `parent_cancel_requested`.)

Walk through it. Three observations are load-bearing:

1. **`_on_task_done` is the heart of abort-on-first-error.** When *any* child task finishes with an exception that is not a `CancelledError`, `_on_task_done` calls `self._abort()` (which cancels every other still-running child) and `self._parent_task.cancel()` (which interrupts the parent's `await self._on_completed_fut`). This is how a single failure propagates outward to its siblings. Cite `Lib/asyncio/taskgroups.py:_on_task_done`.

2. **`__aexit__` is a loop, not a one-shot.** As long as `self._tasks` is non-empty, the parent awaits an `_on_completed_fut` future that `_on_task_done` resolves when the last child finishes. If the parent is *itself* cancelled mid-wait (because another sibling failed, because an outer timeout fired, because the user pressed Ctrl-C), the `except CancelledError` clause inside the `while` loop kicks off another `_abort()` and continues waiting. The block does not exit until every child is genuinely done. Cite `Lib/asyncio/taskgroups.py:__aexit__`.

3. **`parent_task.uncancel()` is the new 3.11+ trick.** The `_on_task_done` callback called `self._parent_task.cancel()` to interrupt the parent's wait. But the parent did not actually *want* to be cancelled — it wanted to be told a child failed. The `uncancel()` call on exit "absorbs" that cancellation so it does not propagate out of the `async with` as a `CancelledError`. This is the entire reason `Task.uncancel` exists in 3.11+. Cite `Lib/asyncio/tasks.py:Task.uncancel`.

You can read every line of this file and explain it now. Try.

## 4. Trio's nursery, for contrast

Trio (Smith, 2017) is the asyncio alternative that grew up around structured concurrency from day one. The API:

```python
import trio

async def parent():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(child_a)
        nursery.start_soon(child_b)
        nursery.start_soon(child_c)
    # All three children done. No leak. No surviving tasks.
```

Substantively identical to `TaskGroup`. Two surface differences:

- Trio takes a *callable* (`child_a`), asyncio takes a *coroutine object* (`child_a()`). This matters because Trio's `start_soon` can attach context and traceback metadata before the coroutine is even constructed; asyncio constructs the coroutine eagerly at call site.
- Trio's `nursery.start` (no `_soon`) is the "start and synchronise" variant — it waits for the child to reach its first checkpoint before returning. asyncio has no direct equivalent; you would write a small `Event` to simulate it.

Trio's cancellation system is *also* different — cleaner, in our view, but a different story. Trio has explicit `CancelScope` objects: every `async with trio.fail_after(5):` opens a scope, and cancellation is targeted at a scope, not at a task. asyncio's `Task.cancel` is targeted at a task. We will see in Lecture 2 that asyncio's 3.11+ `asyncio.timeout` context manager *approximates* a `CancelScope` by leveraging the new `Task.uncancel` counter — but the implementation is awkward because the underlying primitive is still per-task.

If you have any reason to start a new async project in 2026 and the rest of your stack does not pin you to asyncio, **read the Trio docs first** before making the choice. Trio has been right about the model for eight years; asyncio is slowly catching up, but it carries the historical baggage. (For most teams the answer is still asyncio, because `aiohttp`, `httpx`, FastAPI, every cloud SDK is asyncio-native. anyio is the bridge — Lecture 1 §6.)

## 5. `ExceptionGroup` and `except*` revisited

PEP 654 is the language-level enabler of structured concurrency. The problem it solves: when N children run concurrently and M of them fail, you want all M exceptions surfaced to the caller, not just one.

The container type is `ExceptionGroup` (or `BaseExceptionGroup` for groups that include `BaseException` members like `KeyboardInterrupt`). It is constructed with a message and a list:

```python
raise ExceptionGroup(
    "two children failed",
    [ValueError("a"), TypeError("b")],
)
```

The match construct is `except*`. It splits a group:

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(maybe_raise_value_error())
        tg.create_task(maybe_raise_type_error())
        tg.create_task(maybe_raise_runtime_error())
except* ValueError as eg:
    # eg is an ExceptionGroup containing only the ValueErrors.
    for e in eg.exceptions:
        log.warning("value error: %s", e)
except* TypeError as eg:
    # eg is an ExceptionGroup containing only the TypeErrors.
    for e in eg.exceptions:
        log.warning("type error: %s", e)
# Any RuntimeError that was raised in a child propagates out of this try/except
# as a smaller residual ExceptionGroup, because we didn't catch it.
```

Three semantic subtleties that are easy to miss:

- **`except*` always operates on the group**, even when the group has one member. `except ValueError` (single star) does *not* match the single-member `ExceptionGroup([ValueError(...)])`. You must use `except*`. This is a deliberate language choice: it makes the structured-concurrency path always look the same regardless of how many children failed.
- **The split residual is re-raised, not dropped.** If the try/except catches `ValueError` and `TypeError` but the original group contained a `RuntimeError`, the `RuntimeError` survives as a new, smaller `ExceptionGroup` and propagates upward. Nothing is lost.
- **`BaseExceptionGroup` is the wider container.** If any child raised a `BaseException` (e.g., `KeyboardInterrupt`, or `SystemExit`, or — pre-3.8 — `CancelledError`), the group is a `BaseExceptionGroup`, not an `ExceptionGroup`. This matters because `BaseExceptionGroup` is not caught by `except Exception:`. Read PEP 654 §2.4 for the type hierarchy.

The `TaskGroup` implementation in §3 raises a `BaseExceptionGroup` (line: `me = BaseExceptionGroup(...)`). It does this unconditionally because it cannot know at construction time whether any child raised a `BaseException`. The Python runtime then narrows it to `ExceptionGroup` if every member is an `Exception`. This is built into the `BaseExceptionGroup` constructor. Cite [PEP 654 §2.5 "BaseExceptionGroup and ExceptionGroup"](https://peps.python.org/pep-0654/#exception-types).

## 6. anyio: structured concurrency that runs everywhere

`anyio` (Wennergren, 2018+) is a third-party library that runs on both asyncio and Trio backends. It exposes the Trio API on top of either runtime. Its central type is `anyio.create_task_group()`:

```python
import anyio

async def parent():
    async with anyio.create_task_group() as tg:
        tg.start_soon(child_a)
        tg.start_soon(child_b)
```

That `tg.start_soon(child_a)` works on both `asyncio` and `trio`. anyio's `CancelScope` (`async with anyio.CancelScope() as scope: ...`) is a true Trio-style scope on both backends; `anyio.move_on_after(5)` and `anyio.fail_after(5)` are the timeout primitives. If you are writing library code that wants to be backend-agnostic — `httpx`, `starlette`, `hypercorn`, `fastapi` all use anyio internally — this is the right layer.

Read [anyio's task groups docs](https://anyio.readthedocs.io/en/stable/tasks.html) and notice how thin the surface is. The reason it can be that thin is that *all three* runtimes (Trio, asyncio post-3.11, anyio) have converged on the same conceptual API. This is Smith's argument in action: there is exactly one right shape for this primitive.

## 7. The implementation tour: read `Lib/asyncio/taskgroups.py`

Open <https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py>. It is ~250 lines. Read it with these checkpoints:

| Concept | Where in the file |
|---------|-------------------|
| The `TaskGroup` class body, instance state | top of the file, `class TaskGroup:` |
| `__aenter__` — capture loop and parent task | `async def __aenter__` |
| `create_task` — schedule and register | `def create_task` |
| `_on_task_done` — abort-on-first-error | `def _on_task_done` |
| `_abort` — cancel every running child | `def _abort` |
| `__aexit__` — the wait loop, the uncancel dance, the ExceptionGroup raise | `async def __aexit__` |
| `_is_base_error` — `BaseException` vs. `Exception` discrimination | small helper |

By the time you finish reading this lecture, that file should feel familiar. Every primitive — `_on_task_done`, `_abort`, `uncancel` — has a one-line role.

## 8. Cancellation, briefly (preview of Lecture 2)

You have seen `_abort` call `t.cancel()` on every still-running child. `Task.cancel` in asyncio is exception-based: it sets a flag and arranges to `throw()` a `CancelledError` into the coroutine at its next `await`. There is no synchronous "kill thread"; there is no signal; there is only the next checkpoint.

The consequences are substantial and we will spend Lecture 2 on them. A summary now, for orientation:

1. **`CancelledError` runs your `finally` blocks** just like any other exception. This is the *good* consequence. Async code that uses `try/finally` for cleanup is cancellation-safe by default.

2. **A coroutine that never `await`s cannot be cancelled.** A tight loop of pure CPU work blocks the loop just like in any other concurrency model. (See: the "GIL but it's also single-threaded" property of asyncio.)

3. **`except Exception:` *does* catch `CancelledError` on Python 3.7 and earlier**, where it was an `Exception`. On 3.8+, `CancelledError` is a `BaseException`, so `except Exception:` does *not* catch it. **`except BaseException:` does.** A handler that catches and silently swallows a cancellation is one of the most painful bugs to diagnose in async Python. We will see real examples.

4. **`Task.cancel()` returns `True` or `False`.** `True` if the task was running (or scheduled) and is now flagged for cancellation; `False` if the task is already done. The return value is rarely useful and frequently confusing. Cite `Lib/asyncio/tasks.py:Task.cancel`.

5. **3.11+ added `Task.uncancel()` and `Task.cancelling()`.** These are the new shape of cancellation. `cancel()` increments a counter; `uncancel()` decrements it; the task is "pending cancellation" iff the counter is > 0. This lets nested `asyncio.timeout()` contexts compose correctly. Lecture 2 §4 is the deep dive.

## 9. A worked example: the file-import service

You are writing a service that processes uploaded files. Each upload triggers three concurrent tasks: extract metadata, run a virus scan, and write a thumbnail. If any one fails, the upload is rejected and the others are cancelled. The user gets one error response, with all detected problems.

The structured-concurrency version:

```python
async def handle_upload(upload: Upload) -> Result:
    try:
        async with asyncio.TaskGroup() as tg:
            meta_task = tg.create_task(extract_metadata(upload))
            scan_task = tg.create_task(virus_scan(upload))
            thumb_task = tg.create_task(write_thumbnail(upload))
        # All three completed successfully.
        return Result(
            metadata=meta_task.result(),
            virus_clean=scan_task.result(),
            thumbnail_url=thumb_task.result(),
        )
    except* VirusFound as eg:
        return Result.rejected(reason="virus", details=[e.signature for e in eg.exceptions])
    except* MetadataError as eg:
        return Result.rejected(reason="metadata", details=[str(e) for e in eg.exceptions])
    except* OSError as eg:
        return Result.rejected(reason="storage", details=[str(e) for e in eg.exceptions])
```

Read it again. The semantics are:

- All three tasks run concurrently.
- If `virus_scan` finishes first with `VirusFound`, `_on_task_done` cancels `extract_metadata` and `write_thumbnail`. Both run their `finally` cleanups. `__aexit__` waits for both. Then `__aexit__` raises `BaseExceptionGroup([VirusFound(...)])`. The `except* VirusFound` clause catches it. The handler returns a rejection.
- If `extract_metadata` and `write_thumbnail` *both* fail simultaneously (e.g., the storage backend is down), both exceptions land in the same group. The `except* OSError` clause catches both.
- If the user disconnects (the upstream cancels `handle_upload`), the `async with` aborts every child, every child runs its `finally`, the cancellation propagates outward.

There are no leaked tasks. There are no swallowed errors. There is no "did I remember to cancel the siblings?" The block is the lifetime. This is the pattern.

The pre-3.11 version of the same handler is 40 lines of `try/except`, `done_task = asyncio.create_task(...)`, manual cancellation in a `finally`, and a `for task in pending: task.cancel()` loop. It worked. Half the time. The mistake everyone made was forgetting to cancel one of the siblings, or putting the cancellation in the wrong `try` arm. After three years of running it in production, every team I have seen has hit one of those bugs.

## 10. Recap: the rules

| Rule | What it means |
|------|--------------|
| 1. Every task has a parent block. | Use `async with asyncio.TaskGroup() as tg: tg.create_task(...)`. Never `asyncio.create_task(coro)` outside a group. |
| 2. The block does not return until every child is done. | `__aexit__` is a `while self._tasks:` loop. If you exit the block, every child is in a terminal state. |
| 3. One failure cancels every sibling. | `_on_task_done` calls `self._abort()`. The first non-CancelledError exception is the trigger. |
| 4. Every error survives. | `__aexit__` raises `BaseExceptionGroup` containing every collected error. `except*` splits it. |
| 5. Cancellation is exception-based. | `Task.cancel()` arranges to `throw(CancelledError)` at the next `await`. `try/finally` cleanups run. |
| 6. `CancelledError` is a `BaseException`. | `except Exception:` does *not* catch it (3.8+). `except BaseException:` does, but you almost never want to. |
| 7. Use `Task.uncancel()` to absorb cancels you issued. | When you cancel a task internally as a signalling mechanism (as `TaskGroup` does to wake `__aexit__`), `uncancel()` it on the way out. |

If you can defend each of these in three sentences, you have absorbed Lecture 1.

## 11. Reading queue (before Lecture 2)

- `Lib/asyncio/taskgroups.py` — end to end. ~20 minutes.
- Nathaniel J. Smith, *Notes on structured concurrency* — the first three sections (the "go statement considered harmful" argument). ~30 minutes.
- PEP 654 §2 (`ExceptionGroup`) and §3 (`except*`). ~20 minutes.

## 12. Exercises pointer

- **Exercise 1** (today, 45 min): `exercises/exercise-01-taskgroup-with-cancel.py`. Run a `TaskGroup` with one child cancelled mid-flight from outside; verify sibling cancellation and `finally`-block ordering.

## 13. Up next: Lecture 2

Cancellation in depth. `asyncio.timeout`, `shield`, `wait_for`, `Task.uncancel`, the cancellation state machine in 3.11+. The "swallowed `CancelledError`" bug. The "stolen timeout" bug. Nested timeouts and why `uncancel` is the load-bearing primitive that makes them compose.

---

*References cited in this lecture: PEP 492, PEP 525, PEP 654; Nathaniel J. Smith, "Notes on structured concurrency" (2018); `Lib/asyncio/taskgroups.py:_on_task_done`, `:__aexit__`, `:_abort`; `Lib/asyncio/tasks.py:Task.cancel`, `:Task.uncancel`; `Lib/asyncio/exceptions.py:CancelledError`; Trio docs §nurseries; anyio docs §task groups.*
