# Lecture 3 — `Task`, `Future`, `gather`, and `TaskGroup`

> **Duration:** ~1.75 hours. **Outcome:** You can implement `Future` and `Task` against your toy loop with correct cancellation; you can write `gather` in 30 lines; you can build a `TaskGroup` that raises `ExceptionGroup` per PEP 654; and you can pick the right concurrency primitive (`gather` / `wait` / `as_completed` / `TaskGroup`) for any given problem.

## 1. `Future`: a value-or-exception cell with callbacks

`asyncio.Future` is a very small state machine:

```
            ┌────────────┐
            │  PENDING   │
            └─────┬──────┘
                  │
       ┌──────────┼──────────┐
       │          │          │
    cancel()  set_result  set_exception
       │          │          │
       ▼          ▼          ▼
  CANCELLED   FINISHED    FINISHED
              (.result()  (.result()
               returns V)  raises E)
```

Three terminal states, two productive setters (`set_result`, `set_exception`), one cancellation. Once terminal, immutable. `add_done_callback(cb)` registers a callback to be invoked when the future becomes terminal — or invoked *immediately via* `call_soon` if the future is already terminal.

The implementation skeleton (drawn from `Lib/asyncio/futures.py:Future`, 3.13):

```python
class Future:
    _state = "PENDING"
    _result = None
    _exception = None
    _loop = None
    _callbacks = ()

    def __init__(self, loop=None):
        self._loop = loop or get_event_loop()
        self._callbacks = []

    def done(self):
        return self._state != "PENDING"

    def cancelled(self):
        return self._state == "CANCELLED"

    def result(self):
        if self._state == "CANCELLED":
            raise CancelledError
        if self._state == "PENDING":
            raise InvalidStateError("Result is not ready.")
        if self._exception is not None:
            raise self._exception
        return self._result

    def exception(self):
        if self._state == "CANCELLED":
            raise CancelledError
        if self._state == "PENDING":
            raise InvalidStateError("Exception is not set.")
        return self._exception

    def set_result(self, result):
        if self._state != "PENDING":
            raise InvalidStateError(f"{self._state}: {self!r}")
        self._result = result
        self._state = "FINISHED"
        self._schedule_callbacks()

    def set_exception(self, exc):
        if self._state != "PENDING":
            raise InvalidStateError(f"{self._state}: {self!r}")
        self._exception = exc
        self._state = "FINISHED"
        self._schedule_callbacks()

    def cancel(self, msg=None):
        if self._state != "PENDING":
            return False
        self._state = "CANCELLED"
        self._cancel_message = msg
        self._schedule_callbacks()
        return True

    def add_done_callback(self, fn):
        if self._state != "PENDING":
            self._loop.call_soon(fn, self)
        else:
            self._callbacks.append(fn)

    def remove_done_callback(self, fn):
        filtered = [cb for cb in self._callbacks if cb is not fn]
        removed = len(self._callbacks) - len(filtered)
        self._callbacks[:] = filtered
        return removed

    def _schedule_callbacks(self):
        callbacks, self._callbacks = self._callbacks, []
        for cb in callbacks:
            self._loop.call_soon(cb, self)

    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True   # marker the real Task reads
            yield self                              # the only line that matters
        if not self.done():
            raise RuntimeError("await wasn't resumed by the loop")
        return self.result()
```

`__await__` is the entire awaitable contract. Read it carefully:

1. If the future is not done, yield `self` (so the driving task sees what we're waiting on).
2. After we are resumed (the loop sent us back), the future must be done. Return its result.

The yield-self protocol is the asyncio convention. Trio uses a different convention; both are valid implementations of "I am awaitable."

Cite `Lib/asyncio/futures.py:Future` (~line 50–280 in 3.13). The real class has a few more methods (`_log_traceback`, `get_loop`, repr) but the state machine is exactly what's above.

## 2. `Task`: the coroutine driver

A `Task` is a `Future` whose result is the return value of a coroutine. Its constructor schedules the coroutine to start. Its `__step` method drives one step of the coroutine; its `__wakeup` re-enters the step after the awaited future completes.

```python
class Task(Future):
    def __init__(self, coro, loop=None):
        super().__init__(loop=loop)
        self._coro = coro
        self._fut_waiter = None
        self._must_cancel = False
        self._loop.call_soon(self.__step)

    def cancel(self, msg=None):
        if self.done():
            return False
        if self._fut_waiter is not None:
            if self._fut_waiter.cancel(msg=msg):
                return True
        self._must_cancel = True
        return True

    def __step(self, exc=None):
        coro = self._coro
        if self._must_cancel:
            if not isinstance(exc, CancelledError):
                exc = CancelledError()
            self._must_cancel = False

        try:
            if exc is None:
                result = coro.send(None)
            else:
                result = coro.throw(exc)
        except StopIteration as stop:
            super().set_result(stop.value)
            return
        except CancelledError as e:
            super().cancel(msg=str(e) if e.args else None)
            return
        except BaseException as e:
            super().set_exception(e)
            return

        # `result` should be a Future-like (or None for `yield`).
        if isinstance(result, Future):
            if result._asyncio_future_blocking:
                result._asyncio_future_blocking = False
                result.add_done_callback(self.__wakeup)
                self._fut_waiter = result
                if self._must_cancel:
                    if result.cancel():
                        self._must_cancel = False
            else:
                raise RuntimeError(f"yielded future was not _asyncio_future_blocking: {result!r}")
        elif result is None:
            # Bare yield: re-schedule for the next iteration.
            self._loop.call_soon(self.__step)
        else:
            raise RuntimeError(f"Task got bad yield: {result!r}")

    def __wakeup(self, future):
        try:
            future.result()
        except BaseException as exc:
            self.__step(exc=exc)
        else:
            self.__step()
        future = None  # break cycle
```

Five subtleties:

1. **`_asyncio_future_blocking` is a contract marker.** When `Future.__await__` yields self, it sets this flag. `__step` reads it; if it's not set, the loop refuses to treat the value as a future-to-wait-on. This prevents a coroutine from accidentally yielding a generic value and stalling forever.
2. **`_fut_waiter`** tracks what we're waiting on so that `cancel()` can propagate cancellation to it. If you cancel a task that's currently awaiting `asyncio.sleep(10)`, you want the sleep's underlying future to be cancelled, not just a flag on the task.
3. **`_must_cancel`** is a queued cancellation: if `cancel()` is called between scheduler ticks, the next `__step` notices and throws `CancelledError` into the coroutine.
4. **`__wakeup`** is the loop callback. It is *the* bridge: the loop completes a future, the future runs its done-callbacks (one of which is `__wakeup`), `__wakeup` calls `__step`, `__step` sends a value into the coroutine. The coroutine has been "resumed."
5. **`future = None` at the end of `__wakeup`** is reference-cycle hygiene. The task holds the future as `_fut_waiter`; the future holds the task as a callback. Breaking the reference manually accelerates collection on stock CPython without waiting for the cyclic GC.

Cite `Lib/asyncio/tasks.py:Task.__step` (~line 230, 3.13). The real version handles ContextVar propagation (PEP 567), bound-task tracking, exception swallowing for "fire and forget" tasks, and the C-accelerated path in `Modules/_asynciomodule.c`. The skeleton above is faithful to the mechanism.

## 3. `gather`: many coroutines, one result

`asyncio.gather(*coros)` wraps each input as a `Task`, returns a future that completes when all of them do. Two modes:

- `return_exceptions=False` (default): on first exception, cancel the rest; the gather future raises the first exception.
- `return_exceptions=True`: never raise; the gather future's result is `[result_or_exception, ...]` in input order.

The implementation skeleton:

```python
def gather(*coros_or_futures, return_exceptions=False):
    if not coros_or_futures:
        loop = get_running_loop()
        outer = loop.create_future()
        outer.set_result([])
        return outer

    loop = None
    children = []
    for arg in coros_or_futures:
        if isinstance(arg, Future):
            fut = arg
        else:
            fut = ensure_future(arg)
        children.append(fut)
        if loop is None:
            loop = fut._loop

    outer = loop.create_future()
    results = [_UNSET] * len(children)
    pending = [len(children)]
    first_exc = [None]

    def _done_cb(idx, fut):
        if outer.done():
            return
        if fut.cancelled():
            if not return_exceptions:
                outer.cancel()
                return
            results[idx] = CancelledError()
        else:
            exc = fut.exception()
            if exc is not None:
                if return_exceptions:
                    results[idx] = exc
                else:
                    if first_exc[0] is None:
                        first_exc[0] = exc
                        # Cancel all the others.
                        for other in children:
                            if not other.done():
                                other.cancel()
            else:
                results[idx] = fut.result()

        pending[0] -= 1
        if pending[0] == 0:
            if first_exc[0] is not None and not return_exceptions:
                outer.set_exception(first_exc[0])
            else:
                outer.set_result(results)

    for idx, fut in enumerate(children):
        fut.add_done_callback(functools.partial(_done_cb, idx))

    return outer
```

Read this carefully. The pattern is **fan-out, then fan-in by counter**: we kick off N tasks, each sets a slot in `results` and decrements `pending`; when `pending` hits zero, we complete the gather future.

The first-exception cancellation is the policy decision that's caused the most grief. By default, `gather(a, b, c)` cancels `b` and `c` the moment `a` fails. This is reasonable for "I want all results, or none." It is wrong for "I want partial results." Hence `return_exceptions=True`. It is wrong, also, for "I want structured failure" — that is `TaskGroup`.

Cite `Lib/asyncio/tasks.py:gather` (~line 720, 3.13). The real implementation has more error reporting and a special `_GatheringFuture` subclass for cancellation semantics; the algorithm is identical.

## 4. `wait` and `as_completed`: the cousins

`asyncio.wait(coros, return_when=FIRST_COMPLETED | FIRST_EXCEPTION | ALL_COMPLETED, timeout=None)` returns `(done, pending)`: two sets of futures. Does not cancel pending automatically — that is the caller's responsibility. Useful for "race two operations and take the first" or "wait at most 30 seconds for any of these."

`asyncio.as_completed(coros, timeout=None)` returns an iterator of futures in completion order. The classic use is "process the first response first, even if it isn't the first sent":

```python
async def fetch_all(urls):
    coros = [fetch(u) for u in urls]
    for fut in asyncio.as_completed(coros):
        result = await fut
        process_first(result)
```

Both `wait` and `as_completed` exist because `gather` is too opinionated about cancellation and ordering for some real workloads. They are lower-level. They are also older — `as_completed` predates native coroutines.

Cite `Lib/asyncio/tasks.py:wait` (~line 460) and `as_completed` (~line 600). Read both.

## 5. `TaskGroup`: structured concurrency, PEP 654

Added in 3.11 (PEP 654 was the enabler). The `TaskGroup` is an async context manager: every task you create with `tg.create_task(coro)` is owned by the group, and `__aexit__` waits for all of them, re-raising errors as an `ExceptionGroup`.

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(worker_a())
        tg.create_task(worker_b())
        tg.create_task(worker_c())
    # All three complete (or all are cancelled) before we get here.
    # If any raised, we got an ExceptionGroup containing all the raises.
```

The three properties:

1. **No task escapes the block.** When `main` returns from `async with`, no task created in it is still running. This is the *structured* promise: lifetimes nest. (Compare to `loop.create_task(coro)` outside any group, which can run beyond its creator's scope.)
2. **Cancellation is cooperative and complete.** If `worker_b` raises `ValueError`, `worker_a` and `worker_c` are cancelled (a `CancelledError` is thrown into each at its next `await`). `__aexit__` waits for *all* of them to finish their cancellation, including running `finally` blocks, before re-raising.
3. **All errors are preserved.** If `worker_a` raised `IOError` and `worker_c` raised `KeyError` (and `worker_b` was cancelled cleanly), the `async with` re-raises `ExceptionGroup("...", [IOError(...), KeyError(...)])`. You catch with `except*`:

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(might_io_error())
        tg.create_task(might_key_error())
except* IOError as eg:
    for e in eg.exceptions:
        log(e)
except* KeyError as eg:
    for e in eg.exceptions:
        handle(e)
```

The skeleton implementation (drawn from `Lib/asyncio/taskgroups.py`, 3.13):

```python
class TaskGroup:
    def __init__(self):
        self._tasks = set()
        self._loop = None
        self._entered = False
        self._exiting = False
        self._aborting = False
        self._errors = []
        self._on_completed_fut = None
        self._base_error = None

    async def __aenter__(self):
        self._entered = True
        self._loop = asyncio.get_running_loop()
        return self

    async def __aexit__(self, et, exc, tb):
        self._exiting = True

        if exc is not None and self._is_base_error(exc) and self._base_error is None:
            self._base_error = exc

        if exc is not None and self._tasks and not self._aborting:
            # The body of `async with` raised. Cancel children, then wait.
            self._abort()

        # Wait for every task to finish.
        while self._tasks:
            if self._on_completed_fut is None:
                self._on_completed_fut = self._loop.create_future()
            try:
                await self._on_completed_fut
            except CancelledError:
                if not self._aborting:
                    self._abort()
            self._on_completed_fut = None

        # Re-raise: BaseException > propagated `exc` > ExceptionGroup.
        if self._base_error is not None:
            raise self._base_error
        if self._errors:
            errors = self._errors
            self._errors = None       # break cycle
            me = ExceptionGroup("unhandled errors in a TaskGroup", errors)
            raise me from None

    def create_task(self, coro):
        if not self._entered or self._exiting and not self._tasks:
            raise RuntimeError("TaskGroup is not in a state to create new tasks")
        task = self._loop.create_task(coro)
        task.add_done_callback(self._on_task_done)
        self._tasks.add(task)
        return task

    def _abort(self):
        self._aborting = True
        for t in self._tasks:
            if not t.done():
                t.cancel()

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
        if not self._aborting:
            self._abort()
            # Also cancel the body of `async with` if it is still running.
            # In the real impl this is done via a parent-task reference.

    @staticmethod
    def _is_base_error(exc):
        return isinstance(exc, BaseException) and not isinstance(exc, Exception)
```

Read this against `Lib/asyncio/taskgroups.py:TaskGroup`. The real file is ~200 lines; the algorithm here is faithful, missing only:

- The parent-task tracking that lets the group cancel the body of `async with` (not just the child tasks).
- The interaction with `asyncio.timeout` for shared deadlines.
- The fine-grained `BaseException` vs `Exception` ordering for `KeyboardInterrupt`.

**Why this matters:** before `TaskGroup` (i.e., on `gather`), if your "fire 100 requests" routine had one failing request, the other 99 *kept running*, leaking resources, possibly competing with your retry. With `TaskGroup`, the 99 are cancelled at the first failure, their `try/finally` blocks run, sockets are closed, file handles released. This is structured concurrency: lifetimes nest, errors don't lose information, cancellation is a first-class story.

The rule of thumb for 2026:

> **For any new async code, default to `TaskGroup`. Use `gather` only if you have a specific reason (return-exceptions, integrating with an older callback-driven API).**

## 6. `ExceptionGroup` and `except*`, briefly

PEP 654 added two language features:

```python
raise ExceptionGroup("msg", [exc1, exc2, exc3])

try:
    ...
except* ValueError as eg:           # note the *
    for e in eg.exceptions:
        ...
except* (TypeError, KeyError) as eg:
    ...
```

Three properties:

1. **`except*` catches by type, but leaves the rest.** If the group has `[ValueError(...), TypeError(...)]` and we have `except* ValueError`, the `ValueError` is caught; the `TypeError` is automatically re-raised as a new `ExceptionGroup`. No exception is silently lost.
2. **A bare `Exception` will not catch an `ExceptionGroup`** via plain `except Exception`. You must use `except*` or catch `ExceptionGroup` explicitly. This was a deliberate design choice to prevent accidental swallowing of structured errors.
3. **Nested groups flatten on `except*` matching.** If a task in your group raised an `ExceptionGroup` already (perhaps it had its own `TaskGroup`), `except*` matches into the nested structure.

This is exactly the protocol `TaskGroup` needs to re-raise multiple sibling failures without losing any.

Cite the PEP (<https://peps.python.org/pep-0654/>) and CPython's `Lib/test/test_exception_group.py` for canonical examples.

## 7. Choosing the right tool

| You want | Use | Why |
|----------|-----|-----|
| Run N independent things to completion, fail-fast on any error | **`TaskGroup`** | structured; clean cancellation; ExceptionGroup |
| Same, but tolerate per-task errors and collect them | `TaskGroup` with `try/except` inside each child, OR `gather(return_exceptions=True)` | both work; TaskGroup is more composable |
| Run N things, want the *first* result and cancel the rest | `asyncio.wait([...], return_when=FIRST_COMPLETED)` followed by manual cancellation, OR a `TaskGroup` with a "winning" sentinel | wait is lower-level; TaskGroup composes |
| Process results as they arrive, in completion order | `asyncio.as_completed([...])` | the only stdlib API that gives you that order |
| Bound the wall-clock of a group | `asyncio.timeout()` around the `async with` | `timeout` is 3.11+; uses `CancelledError` |
| Fire-and-forget a long-running task at module load | `loop.create_task(coro)` outside any group | breaks structured concurrency; only use if you mean it |

If you can recall this table from memory after the lecture you have the engineering judgment. The mechanism is the previous six sections; the judgment is this one.

## 8. The wakeup protocol, end to end

Trace one `await` from invocation to resumption. Coroutine code:

```python
async def main():
    result = await asyncio.sleep(0.5, "the result")
    print(result)
```

Step by step:

1. `asyncio.run(main())` constructs an event loop, wraps `main()` in a `Task`, calls `run_until_complete`.
2. `loop.call_soon(task.__step)` schedules the first step.
3. `_run_once` drains `_ready`, calls `task.__step()`.
4. `task.__step` does `coro.send(None)`. The coroutine runs up to `await asyncio.sleep(0.5, ...)`.
5. `sleep`: creates `future = loop.create_future()`, calls `loop.call_later(0.5, future.set_result, "the result")`, then `yield from future.__await__()`.
6. `future.__await__` sees `not self.done()`, yields `self` (the future).
7. The yield propagates back through `sleep` to `main` (via the `await` desugaring) and out of `coro.send(None)`. The return value is the future.
8. `task.__step` sees the future, registers `task.__wakeup` as a done-callback, sets `task._fut_waiter = future`, returns.
9. `_run_once` finishes draining `_ready`. `_ready` is now empty. `_scheduled` has one timer (the `call_later` from step 5). `_run_once` polls the selector with `timeout = 0.5` (next timer deadline).
10. 500ms later (give or take selector resolution), `_run_once` wakes; `time.monotonic() >= deadline`; the timer handle moves from `_scheduled` to `_ready`.
11. The timer handle runs: `future.set_result("the result")`. The future is now FINISHED.
12. `future._schedule_callbacks` runs: it `call_soon`s `task.__wakeup` with `self` (the future) as argument.
13. `_run_once`'s next iteration drains `_ready` again. `task.__wakeup(future)` runs. It does `future.result()` (returns `"the result"`, no exception), then `task.__step()`.
14. `task.__step` does `coro.send(None)` again. The coroutine resumes at the `await` point; the `await` expression evaluates to `"the result"`. Execution continues. `print("the result")`.
15. Coroutine returns. `coro.send(None)` raises `StopIteration(None)`. `task.__step` catches it, calls `task.set_result(None)`. The task is FINISHED.
16. The task's done-callback (registered by `run_until_complete`) calls `loop.stop()`.
17. `_run_once` returns. The `while not self._stopping` loop exits. `run_forever` returns.
18. `run_until_complete` returns `task.result()` (which is `None`).

**Read this trace twice.** Every primitive in asyncio is one of these 18 steps. The mini-project rebuilds them.

## 9. Cancellation, briefly

We are saving the full story for Week 5, but the minimum you need now:

- `task.cancel()` requests cancellation. It does *not* immediately stop anything.
- If the task is currently waiting on a future, `task._fut_waiter.cancel()` is called. The future enters CANCELLED. The future's done-callbacks run. `task.__wakeup` is called. `__wakeup` calls `future.result()`, which raises `CancelledError`. `__wakeup` re-enters `__step` with `exc=CancelledError`. `__step` calls `coro.throw(CancelledError())`. The exception propagates out of the coroutine's current `await` point.
- The coroutine can catch the `CancelledError` and continue (rare; usually a bug). The convention is to let it propagate or to do `finally:` cleanup and re-raise.
- `task.cancelled()` returns True only after the cancellation has *completed*, not when it was requested.

In a `TaskGroup`, the group raises `CancelledError` into every child the moment any child fails. Each child's `finally:` block runs. The group waits for all of them. Then re-raises as `ExceptionGroup`.

## 10. What you should be able to do now

- Write `Future` (full state machine) from memory in ~50 lines.
- Write `Task.__step` from memory in ~30 lines.
- Write `gather` (with the first-exception cancel) in ~30 lines.
- Open `Lib/asyncio/taskgroups.py` and tag every method as one of: "the public API" (`__aenter__`, `__aexit__`, `create_task`); "the abort/cancel machinery" (`_abort`, `_on_task_done`); "the BaseException pile" (`_is_base_error`).
- Pick, for any concurrency problem stated in plain English, the right stdlib primitive from §7's table.

You are now ready to build the toy clone. The mini-project is one weekend's work and a portfolio piece. Onward.
