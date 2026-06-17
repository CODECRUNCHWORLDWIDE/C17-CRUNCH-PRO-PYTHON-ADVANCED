# Lecture 2 — Timeouts, `shield`, and Cancellation Semantics

> **Duration:** ~2 hours. **Outcome:** You can predict exactly what happens when a task is cancelled mid-`await`; you can write nested `asyncio.timeout` blocks that compose correctly; you can use `asyncio.shield` to protect a critical region without leaking the inner task; you can explain the 3.11 `Task.uncancel`/`cancelling` API and why it solves the pre-3.11 "stolen timeout" bug; you can read `Lib/asyncio/timeouts.py` end-to-end and identify the role of every line.

## 1. Cancellation is an exception

Lecture 1 sketched the rule. Here is the mechanism in full.

`task.cancel()` does **not** kill the task. It does this:

```python
# Lib/asyncio/tasks.py, paraphrased:
def cancel(self, msg=None):
    self._log_traceback = False
    if self.done():
        return False
    self._num_cancels_requested += 1     # the "cancelling" counter, 3.11+
    if self._num_cancels_requested > 1:
        return False                     # already pending cancel
    if self._fut_waiter is not None:
        if self._fut_waiter.cancel(msg=msg):
            # Cancellation propagated to the awaited future.
            return True
    # Coroutine is currently runnable; schedule cancellation for its next step.
    self._must_cancel = True
    self._cancel_message = msg
    return True
```

Two paths:

- **The task is parked on a future** (e.g., `await asyncio.sleep(5)` is parked on the sleep future). `cancel` propagates to that future via `self._fut_waiter.cancel()`. The future transitions to `CANCELLED`. When the loop step processes the future's done-callbacks, `Task.__wakeup` runs, which calls `Task.__step` with `coro.throw(CancelledError)`. The coroutine receives the `CancelledError` from the `await` expression that was parked.

- **The task is currently runnable** (its previous step has scheduled it but it has not yet run). Sets `self._must_cancel = True`. The next call to `__step` checks this flag and throws `CancelledError` immediately.

Either way, the coroutine sees `CancelledError` raised from the `await`-statement that was suspended. From the coroutine's point of view, cancellation is *just an exception thrown at an `await` point*. It runs `try/finally`, it bubbles up the stack, it can be caught.

Cite `Lib/asyncio/tasks.py:Task.cancel` (the cancel method). Cite `Lib/asyncio/tasks.py:Task.__step` for the throw-on-must-cancel logic.

## 2. `CancelledError` is a `BaseException`

In Python 3.7 and earlier, `asyncio.CancelledError` inherited from `concurrent.futures.CancelledError` which inherited from `Exception`. This was a footgun. A typical bug:

```python
# Anti-pattern (and very common in pre-3.8 code).
async def handler():
    try:
        await do_work()
    except Exception as e:
        log.exception("work failed")
        await metrics.report_failure(e)
        return Result.failed(e)
```

When the handler is cancelled (because, say, the request timed out), `CancelledError` is thrown at the `await do_work()` point. The `except Exception:` clause catches it. The handler reports a failure to metrics. The cancellation is *swallowed*. The handler returns normally as if `do_work()` had failed in some ordinary way.

The cancelling caller — perhaps an `asyncio.timeout()` block — sees no cancellation came back. Its `__aexit__` then raises `TimeoutError`, but the inner cleanup never happened. The task that was supposed to die is still alive in the form of the `report_failure` call. In a real service this manifests as: the request handler appears to succeed; the user sees a 200 OK; the actual work is half-done.

Python 3.8 fixed this by reparenting:

```python
# Lib/asyncio/exceptions.py (3.8+):
class CancelledError(BaseException):
    """The Future or Task was cancelled."""
```

`CancelledError` now inherits directly from `BaseException`. `except Exception:` does not catch it. The handler above is now cancellation-safe.

The corollary is that you should be **very** careful with `except BaseException:` in async code. In practice:

- Use `except Exception:` for ordinary error paths (network errors, parse errors, etc.).
- Use `except CancelledError:` *only* when you mean to handle cancellation specifically (almost always: re-raise after cleanup).
- Use `except BaseException:` essentially never. The few legitimate uses are top-of-program "log and crash" handlers.

The pattern for "do cleanup on any exit, including cancellation":

```python
async def critical_op():
    resource = await acquire()
    try:
        await use(resource)
    finally:
        await release(resource)
```

`try/finally` runs on `CancelledError` too. Use it.

The pattern for "actually handle cancellation":

```python
async def cancellable_work():
    try:
        return await long_thing()
    except asyncio.CancelledError:
        # observed cancellation. Do cleanup.
        await record_cancel()
        # IMPORTANT: re-raise. Anything else is the swallowing bug.
        raise
```

Cite [PEP-less Python 3.8 What's New](https://docs.python.org/3/whatsnew/3.8.html#asyncio) for the reparenting. Cite `Lib/asyncio/exceptions.py:CancelledError` for the class definition.

## 3. `asyncio.timeout()`: the modern timeout

Since 3.11, the canonical way to bound a block of async code is the `asyncio.timeout` context manager:

```python
async def fetch_with_deadline(url: str) -> bytes:
    async with asyncio.timeout(5.0):
        return await fetch(url)
```

If `fetch(url)` does not return within 5.0 seconds, `asyncio.timeout` cancels the *current task*, the `await fetch(url)` raises `CancelledError`, the `async with` catches that cancel, and re-raises it as `TimeoutError`. Read again: the inner `await` sees `CancelledError`; the outer caller sees `TimeoutError`. That asymmetry is deliberate. It lets `try/finally` in the inner code run with the same exception type it would see for any cancellation, and lets the outer code distinguish "timed out" from "cancelled by parent."

The implementation, paraphrased from `Lib/asyncio/timeouts.py`:

```python
class Timeout:
    def __init__(self, when):
        self._state = _State.CREATED
        self._timeout_handler = None
        self._task = None
        self._when = when

    async def __aenter__(self):
        self._state = _State.ENTERED
        self._task = tasks.current_task()
        if self._when is not None:
            loop = events.get_running_loop()
            if loop.time() >= self._when:
                # Deadline already passed; cancel immediately.
                self._timeout_handler = loop.call_soon(self._on_timeout)
            else:
                self._timeout_handler = loop.call_at(self._when, self._on_timeout)
        return self

    async def __aexit__(self, et, exc, tb):
        if self._state is _State.EXPIRING:
            self._state = _State.EXPIRED
            if self._task.uncancel() <= self._cancelling and et is exceptions.CancelledError:
                # The cancel we issued is the one that propagated.
                # Re-raise as TimeoutError instead.
                raise TimeoutError from exc
        elif self._state is _State.ENTERED:
            self._state = _State.EXITED
            if self._timeout_handler is not None:
                self._timeout_handler.cancel()
                self._timeout_handler = None

    def _on_timeout(self):
        # Called by the loop when the deadline fires.
        assert self._state is _State.ENTERED
        self._state = _State.EXPIRING
        self._cancelling = self._task.cancelling()
        if not self._task.done():
            self._task.cancel()
        self._timeout_handler = None
```

Three observations:

1. **The deadline is implemented as a `call_at` callback.** `call_at(deadline, self._on_timeout)` schedules `_on_timeout` to fire at wall-clock time `deadline`. If the block exits before then, `__aexit__` cancels the handler. If the handler fires first, it calls `self._task.cancel()`. Cite `Lib/asyncio/timeouts.py:_on_timeout`.

2. **The cancel propagates through the task's *current `await`*.** Whatever the task was waiting on (a sleep, a socket read, a sub-`await` inside `fetch`) raises `CancelledError`. That exception bubbles up. The `async with asyncio.timeout(5.0):` sees the `CancelledError` arrive at its `__aexit__`.

3. **`__aexit__` calls `self._task.uncancel()` to absorb the cancel it issued.** This is the load-bearing 3.11 mechanism. Without it, the `CancelledError` would keep propagating out past the `async with`, and the *caller* would see a bare `CancelledError` — looking like *they* had been cancelled, not the inner block. With `uncancel`, the cancellation counter goes back down, and the `async with` substitutes a `TimeoutError` for the outer world. Cite `Lib/asyncio/timeouts.py:Timeout.__aexit__`.

## 4. The `cancelling` counter and `uncancel`

The 3.11 change to `Task` cancellation is the introduction of an integer counter `_num_cancels_requested`, accessed via:

- `Task.cancel()` — increments the counter; returns `True` iff this is the first increment.
- `Task.uncancel()` — decrements the counter; returns the new value.
- `Task.cancelling()` — reads the counter without modifying it.

Why a counter and not a flag? Because cancellations can stack. Picture:

```python
async def f():
    async with asyncio.timeout(10):       # outer
        async with asyncio.timeout(1):    # inner
            await asyncio.sleep(5)
```

The inner deadline fires first. The inner `_on_timeout` calls `task.cancel()` — counter goes from 0 to 1. The `await asyncio.sleep(5)` raises `CancelledError`. The inner `__aexit__` runs: `self._task.uncancel()` — counter goes from 1 to 0 — and re-raises `TimeoutError`.

Now the outer `async with` sees `TimeoutError` (not `CancelledError`) as the exit type. It does **not** call `uncancel`. It does not consume any cancellation. The `TimeoutError` propagates out of `f` normally.

Compare with the broken pre-3.11 behavior. Without the counter, `task.cancel()` was a flag. If the inner timeout cancelled and then the outer wanted to also cancel for an unrelated reason, you could not distinguish them. The "stolen timeout" bug: outer `asyncio.wait_for(coro, timeout=10)` would cancel its inner task, but if the inner task had its own `wait_for` that *also* timed out at the same instant, only one `TimeoutError` reached the application; the other became a phantom `CancelledError` that no one caught.

The counter fixes this by giving each cancellation a unique "slot." A timeout context that issued a cancel knows its slot value. If on exit the counter is back to that value, the cancel it issued has been observed and the timeout can substitute `TimeoutError`. If the counter is *higher* than the slot it expected, *someone else also cancelled* — propagate the cancel unchanged.

Read the exact predicate in `Lib/asyncio/timeouts.py:__aexit__`:

```python
if self._task.uncancel() <= self._cancelling and et is exceptions.CancelledError:
    raise TimeoutError from exc
```

`self._cancelling` was the counter value *before* `_on_timeout` issued its cancel. If after `uncancel` the counter is back at or below that value, the timeout owns the cancellation and converts it to `TimeoutError`. Otherwise (counter still higher), some other cancellation source is also active — let the `CancelledError` propagate.

Cite `Lib/asyncio/tasks.py:Task.uncancel` for the decrement; cite `Lib/asyncio/tasks.py:Task.cancelling` for the read; cite `Lib/asyncio/timeouts.py:_on_timeout` for the capture of `self._cancelling` before issuing the cancel.

## 5. `wait_for` and the 3.11 fix

`asyncio.wait_for(coro, timeout)` is the legacy timeout API. It is still supported, still in the docs, and still in heavy use, but `asyncio.timeout()` is the canonical replacement.

```python
# Legacy:
result = await asyncio.wait_for(fetch(url), timeout=5.0)

# Modern equivalent:
async with asyncio.timeout(5.0):
    result = await fetch(url)
```

Why the change? Pre-3.11, `wait_for` had a race. Sketch:

1. `wait_for` schedules the inner coroutine as a task `t`.
2. `wait_for` schedules a timeout callback at deadline.
3. Suppose `t` finishes successfully at deadline − ε.
4. The timeout callback fires at deadline.
5. Both events are now in the loop's runnable queue.
6. The timeout callback runs first by virtue of insertion order.
7. The timeout cancels `t`. But `t` is already done.
8. `wait_for` sees `t.cancelled()` is true and raises `TimeoutError`. The successful result is lost.

The 3.11 reimplementation uses `Task.uncancel` and is much more careful about ordering. Read `Lib/asyncio/tasks.py:wait_for` for the current state. The public lesson: prefer `asyncio.timeout()` for new code. `wait_for` is kept for compatibility.

Cite `Lib/asyncio/tasks.py:wait_for`. Cite [bpo-32751](https://bugs.python.org/issue32751) for the original race report.

## 6. `asyncio.shield()`: the cancellation firewall

There is a class of problem `timeout` and `cancel` cannot handle cleanly: a *critical region* that must finish even if the outer caller is cancelled.

Example: you are writing to a backend datastore. The write must not be partial — either it completes or it never started. The caller may be cancelled at any time, but the write, once issued, must run to completion.

```python
async def save(record):
    await db.commit(record)        # MUST run to completion
```

If `save` is called from a cancellable context and the caller is cancelled mid-`commit`, the commit is aborted. Half-done.

The fix is `asyncio.shield`:

```python
async def save(record):
    await asyncio.shield(db.commit(record))
```

The semantics: the *inner* coroutine (`db.commit(record)`) runs as a real `Task` on the loop. The *outer* `await` is a checkpoint on a shield-future. If the caller is cancelled, the outer `await` raises `CancelledError`, but the inner task **continues to run on the loop** — unaffected.

The implementation, paraphrased from `Lib/asyncio/tasks.py:shield`:

```python
def shield(arg):
    inner = ensure_future(arg)
    if inner.done():
        return inner
    loop = futures._get_loop(inner)
    outer = loop.create_future()
    def _inner_done_callback(inner, outer=outer):
        if outer.cancelled():
            if not inner.cancelled():
                inner.exception()    # mark exception retrieved
            return
        if inner.cancelled():
            outer.cancel()
        else:
            exc = inner.exception()
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(inner.result())
    def _outer_done_callback(outer):
        if not inner.done():
            inner.remove_done_callback(_inner_done_callback)
    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer
```

Walk through it. Two futures: `inner` is the real task; `outer` is what the caller awaits. They are *linked* by done-callbacks but not by cancellation. If the caller cancels `outer`, the `_outer_done_callback` unwires the link; the inner task keeps running. Its eventual completion has nowhere to go, but the work happens.

Cite `Lib/asyncio/tasks.py:shield` for the implementation.

There is a subtle consequence. After `shield(coro)` and the outer raises `CancelledError`, the *inner* task has not been awaited and will eventually be garbage-collected. If you care about the result, you must keep a reference and `await` it separately:

```python
async def save_with_logging(record):
    inner = asyncio.create_task(db.commit(record))
    try:
        await asyncio.shield(inner)
    except asyncio.CancelledError:
        # The caller cancelled us. The inner is still running.
        # We can choose to wait for it (in a `finally` of a parent
        # shield, perhaps) or let it complete in the background.
        log.info("save: caller cancelled; inner commit continues")
        raise
    else:
        log.info("save: commit completed cleanly")
```

`shield` is a power tool. Use it for genuinely uncancellable critical sections (commits, RPC handshakes that must complete to release resources, the *final write to a sink* in the mini-project crawler).

## 7. The four canonical cancellation bugs

The bugs you will see in production async Python. Each is a one-line fix once you see it.

### Bug 1 — Swallowed `CancelledError` via `except Exception:` (pre-3.8)

```python
async def handler():
    try:
        await work()
    except Exception:        # pre-3.8: catches CancelledError. post-3.8: does not.
        await report()
```

Fix: target the exception type precisely. `except SomeRealError:` for real errors. `except CancelledError:` + `raise` for cancellation. Or just `try/finally` for cleanup.

### Bug 2 — Swallowed `CancelledError` via explicit `except CancelledError:` without re-raise

```python
async def handler():
    try:
        await work()
    except CancelledError:
        log.info("cancelled")
        # forgot: raise
```

The handler "absorbs" the cancellation. The caller proceeds as if work completed. Fix: always `raise` after handling, unless you explicitly intend to consume the cancel and continue (rare and usually wrong).

### Bug 3 — Cancel-while-CPU-bound

```python
async def cpu_grinder():
    for i in range(10_000_000):
        result = pure_python_loop_body(i)
    return result
```

No `await` points. `task.cancel()` does nothing visible until the coroutine reaches an `await`. If there is no `await`, the cancel is never delivered. Fix: yield periodically with `await asyncio.sleep(0)`. Better fix: do the CPU work on a thread or process pool.

### Bug 4 — Cancel-the-wrong-task in nested `wait_for` (pre-3.11)

```python
async def outer():
    return await asyncio.wait_for(inner_body(), timeout=10)

async def inner_body():
    return await asyncio.wait_for(io_op(), timeout=5)
```

If both timeouts fire at nearly the same instant, the pre-3.11 implementation could mistarget cancellations. Fix: use `asyncio.timeout()` (3.11+), which uses the cancel-counter to compose correctly.

The first two are the most common. They are easy to introduce by reflex (`try: ... except Exception:` is muscle memory). When reviewing async code, look for every `except Exception:` over an `await` and ask: does the inner code do cancellation cleanup correctly?

## 8. Cancellation in `TaskGroup` revisited

You have now seen all the pieces. Walk through what `TaskGroup` actually does when a child fails:

1. Child task `B` raises `ValueError`. `Task.__step` calls `set_exception(ValueError)` on the `B` future and fires its done-callbacks.
2. `TaskGroup._on_task_done(B)` runs. It sees `B.exception() is ValueError`. It calls `self._abort()`, which calls `t.cancel()` on every other running child (`A`, `C`).
3. `_on_task_done` also calls `self._parent_task.cancel()`. This is the trick: the parent task is the one running `__aexit__`, currently awaiting `self._on_completed_fut`. Cancelling the parent task interrupts that await.
4. The parent task's `await self._on_completed_fut` raises `CancelledError`. `__aexit__`'s `try: ... except CancelledError:` catches it. It calls `_abort` again (idempotent) and re-enters the `while self._tasks:` loop.
5. Meanwhile, `A` and `C` are at their `await asyncio.sleep(...)` calls. The `cancel` propagates through the future, throws `CancelledError` into each, and their `try/finally` runs. Each task finishes (cancelled), and `_on_task_done` removes them from `self._tasks`.
6. When `self._tasks` is empty, `__aexit__`'s loop exits. It checks `self._errors == [ValueError(...)]` and raises `BaseExceptionGroup("unhandled errors in a TaskGroup", [ValueError(...)])`.
7. The cancellation it had issued on its own parent task (step 3) is "absorbed" by `self._parent_task.uncancel()` near the end of `__aexit__`. The outside world sees an `ExceptionGroup`, not a `CancelledError`.

Trace this until it is mechanical. The implementation in `Lib/asyncio/taskgroups.py` is exactly this dance. Every line has a job.

## 9. A more subtle example: cancellation across `gather`

`gather`'s pre-`TaskGroup` semantics are awkward but worth knowing because old code uses them:

```python
results = await asyncio.gather(a(), b(), c())          # may raise
results = await asyncio.gather(a(), b(), c(), return_exceptions=True)   # never raises
```

- `return_exceptions=False` (default): on first exception, gather *future-completes* with that exception. Surviving coroutines are **not cancelled** by gather itself. They keep running. The caller is expected to cancel them — which the caller usually forgets. This is the "leaked task" footgun.

- `return_exceptions=True`: every result (or exception) lands in the result list. No cancellation. Slowest sibling determines wall-clock.

In 3.10+, `gather` *was* updated so that on cancellation of the gather-future itself (e.g., the caller of `await gather(...)` is cancelled), the children are cancelled. But the "one child raised" path still does not cascade. Compare with `TaskGroup`: `TaskGroup` cancels siblings unconditionally on the first exception. This is the right behavior.

The mental model: `gather` is "wait for all, report errors." `TaskGroup` is "structured concurrency block, with full cancel cascade." Use `TaskGroup` for new code. Use `gather` only when you specifically want the "return exceptions as values" mode (`return_exceptions=True`) on independent work.

Cite `Lib/asyncio/tasks.py:gather`.

## 10. A worked example: HTTP fetch with timeout and shield

The mini-project crawler will use this exact shape. Read it now:

```python
async def fetch_and_record(url: str, sink: Sink) -> None:
    try:
        async with asyncio.timeout(10.0):
            body = await http.get(url)
    except TimeoutError:
        log.warning("fetch %s timed out", url)
        return
    # The shield protects the sink write from outer cancellation:
    # if the worker is being shut down, we still complete the write.
    await asyncio.shield(sink.write(url, body))
```

Three properties:

- A 10-second deadline on the network fetch. `TimeoutError`, not `CancelledError`, is what the caller sees.
- A shield around the sink write. If the outer worker is cancelled (shutdown, parent group abort), the partial write is not interrupted.
- `finally` semantics are preserved by `try/finally` — we did not show one here, but `http.get` and `sink.write` are responsible for their own resource cleanup; cancellation will run their `finally`s naturally.

The `shield` here is a real engineering decision. If the sink is a database, `shield` is correct: we want the write to land. If the sink is a log file with line-atomic writes, `shield` is overkill: a half-written line is not a problem. If the sink is a network socket without atomicity guarantees, you need a different design entirely (idempotency keys, retries). Choose deliberately.

## 11. Reading queue (before Lecture 3)

- `Lib/asyncio/timeouts.py` — end to end. ~15 minutes. Notice `_on_timeout` and the `uncancel`-in-`__aexit__` dance.
- `Lib/asyncio/tasks.py:shield` — the 30-line implementation. ~5 minutes.
- `Lib/asyncio/tasks.py:wait_for` — for contrast with `timeout`. ~10 minutes.
- Nathaniel J. Smith, *Control-C handling in Python and Trio* (2018). ~30 minutes. The cleanest treatment of `KeyboardInterrupt` + async cancellation in the literature.

## 12. Exercises pointer

- **Exercise 2** (today, 45 min): `exercises/exercise-02-timeout-and-shield.py`. Nested `asyncio.timeout` with a `shield` around a critical write; observe the `uncancel` counter; verify the right exception type surfaces at each layer.

## 13. Recap: the rules

| Rule | What it means |
|------|--------------|
| 1. `task.cancel()` throws `CancelledError` at the next `await`. | A coroutine with no `await` cannot be cancelled. |
| 2. `CancelledError` is a `BaseException` (3.8+). | `except Exception:` does not catch it. Cleanup with `try/finally`. |
| 3. Always re-raise an explicitly caught `CancelledError`. | Otherwise you swallow cancellation and the caller hangs. |
| 4. Use `asyncio.timeout()` for new code, not `wait_for`. | Composable, uncancel-aware, race-free. |
| 5. `cancelling()` / `uncancel()` are the new shape of cancellation. | The counter discipline is how nested timeouts compose. |
| 6. Use `asyncio.shield()` for critical sections that must not be interrupted. | The inner task continues; the outer `await` may still raise. |
| 7. The first exception in a `TaskGroup` cancels every sibling and propagates as `ExceptionGroup`. | The cancel cascade is automatic. |

If you can defend each of these in three sentences, you have absorbed Lecture 2.

## 14. Up next: Lecture 3

Back-pressure. `asyncio.Queue`, `Semaphore`, async iterators. How to fan out a million URLs through a 16-worker pool without melting the producer. The producer/consumer pattern, sentinels, and `Queue.shutdown` (3.13+). The architecture the mini-project crawler is built on.

---

*References cited in this lecture: PEP 654; Python 3.8 What's New (`CancelledError` reparenting); Python 3.11 What's New (`asyncio.timeout`, `Task.uncancel`); `Lib/asyncio/timeouts.py:Timeout.__aexit__`, `:_on_timeout`; `Lib/asyncio/tasks.py:Task.cancel`, `:Task.uncancel`, `:Task.cancelling`, `:shield`, `:wait_for`; `Lib/asyncio/exceptions.py:CancelledError`; bpo-32751 (`wait_for` race); Nathaniel J. Smith, "Control-C handling in Python and Trio" (2018).*
