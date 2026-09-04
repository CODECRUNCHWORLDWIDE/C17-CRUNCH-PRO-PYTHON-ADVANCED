# Week 4 — Quiz

Ten questions. Lectures closed.

---

**Q1.** A native coroutine in Python (an `async def` function) compiles to code whose `co_flags` include:

- A) `CO_GENERATOR` only.
- B) `CO_COROUTINE` (and not `CO_GENERATOR`).
- C) Neither flag; coroutines are a runtime construct, not a compile-time one.
- D) Both `CO_GENERATOR` and `CO_COROUTINE` simultaneously.

<details>
<summary>Answer</summary>

**B** — `CO_COROUTINE` (and not `CO_GENERATOR`). PEP 492 added the new flag and the new type `types.CoroutineType`. Coroutines are a *compile-time* distinction from generators; the runtime mechanics are nearly identical.

</details>

---

**Q2.** Calling an `async def` function does what?

- A) Runs the body to completion and returns the value.
- B) Returns a `coroutine` object without executing the body. The body runs only when something `.send(None)`-s into it (or `await`s it).
- C) Returns the first value yielded by the body.
- D) Schedules the body on the running event loop and returns a `Task`.

<details>
<summary>Answer</summary>

**B** — calling an `async def` returns a fresh coroutine object; the body does not run until something pulls on it via `send(None)` or `await`. This is the same lazy-evaluation behavior generators have.

</details>

---

**Q3.** An object is "awaitable" iff:

- A) It is an instance of `types.CoroutineType`.
- B) It defines `__await__()` returning an iterator, OR is a native coroutine, OR is a generator decorated with `@types.coroutine`.
- C) It is registered with `asyncio.set_event_loop_policy`.
- D) It inherits from `asyncio.Future`.

<details>
<summary>Answer</summary>

**B** — the duck-typed awaitable protocol. See `_PyCoro_GetAwaitableIter` in `Objects/genobject.c` for the authoritative implementation.

</details>

---

**Q4.** Inside `Future.__await__`, the body is roughly:

```python
def __await__(self):
    if not self.done():
        self._asyncio_future_blocking = True
        yield self
    return self.result()
```

The `yield self` is consumed by:

- A) The Python interpreter, which special-cases yielded futures.
- B) The driving `Task.__step`, which receives `self` as the value out of `coro.send(None)`, then registers `Task.__step` as a done-callback on the yielded future.
- C) The `await` keyword, which short-circuits the yield.
- D) The CPython garbage collector.

<details>
<summary>Answer</summary>

**B** — `Task.__step` is the consumer of yielded futures. It sees the future come back as the value of `coro.send(None)`, validates `_asyncio_future_blocking`, registers itself as a done-callback, and parks. When the future fires, the callback re-enters `__step`, which sends back into the coroutine.

</details>

---

**Q5.** The asyncio event loop's `_run_once` step (in `Lib/asyncio/base_events.py`) performs roughly these phases, in order:

- A) (1) poll selector, (2) drain ready callbacks, (3) check timers.
- B) (1) drain expired timers into ready, (2) poll selector with timeout = next-timer-deadline, (3) drain ready callbacks exactly once.
- C) (1) acquire the GIL, (2) drain ready callbacks, (3) release the GIL.
- D) (1) call into libuv, (2) wait for completion, (3) translate events to Python.

<details>
<summary>Answer</summary>

**B** — the canonical three phases. Drain timers first so an overdue timer doesn't get starved by an I/O poll; pick the selector timeout from the next timer deadline so we wake at the right time.

</details>

---

**Q6.** A coroutine running on the asyncio loop yields a non-`Future` object (say, the integer 42) into `Task.__step`. The loop reacts by:

- A) Treating 42 as a delay in seconds and calling `sleep(42)`.
- B) Raising a `RuntimeError` ("Task got bad yield: 42"), because the asyncio convention is that yielded values must be `Future`-like.
- C) Silently dropping the value and continuing.
- D) Wrapping 42 in a `Future` whose result is 42 and immediately resuming.

<details>
<summary>Answer</summary>

**B** — `RuntimeError("Task got bad yield: ...")`. The asyncio convention is strict. (Trio's convention is the opposite — strings are checkpoint markers — but Trio is not asyncio.)

</details>

---

**Q7.** `asyncio.gather(coro_a, coro_b, coro_c)` (default `return_exceptions=False`) where `coro_b` raises after 50 ms. What happens to `coro_a` and `coro_c`?

- A) They run to completion regardless; gather only reports the first exception.
- B) They are cancelled the moment `coro_b` raises; gather raises the first exception once they finish cancellation.
- C) They are silently leaked; the user is expected to cancel them by hand.
- D) `gather` re-raises an `ExceptionGroup` containing only `coro_b`'s exception; `coro_a` and `coro_c` continue.

<details>
<summary>Answer</summary>

**B** — gather's default semantics are fail-fast: first exception cancels the rest. `gather` resolves only after all children finish (either with a result or with the propagation of the cancellation).

</details>

---

**Q8.** `asyncio.TaskGroup` (PEP 654, added in 3.11) differs from `asyncio.gather` in that:

- A) It is faster on hot paths.
- B) Its `__aexit__` waits for every spawned task, cancels them on any sibling failure, and re-raises *every* collected exception inside an `ExceptionGroup` — no error is lost.
- C) It accepts only sync callables, not coroutines.
- D) It is single-threaded by design, whereas `gather` uses a thread pool.

<details>
<summary>Answer</summary>

**B** — the structured-concurrency promise. No task escapes the `async with`; all errors survive into the ExceptionGroup; cancellation is cooperative and complete.

</details>

---

**Q9.** `except* ValueError as eg:` matches:

- A) The single `ValueError` raised in a `try` block.
- B) Every `ValueError` in an `ExceptionGroup`; the remaining non-`ValueError` members are re-raised as a smaller residual `ExceptionGroup`.
- C) `ValueError` *and* its subclasses, but not when wrapped in an `ExceptionGroup`.
- D) Any exception whose `__cause__` is a `ValueError`.

<details>
<summary>Answer</summary>

**B** — PEP 654's "split" semantics. `except*` catches matching members and leaves the rest as a residual group. No exception is silently discarded.

</details>

---

**Q10.** A common pre-`TaskGroup` bug, when using `asyncio.gather`, was:

- A) Tasks ran in undefined order, so the result list was scrambled.
- B) When one child failed, surviving children kept running in the background as "leaked tasks" because gather raised before cancelling them — and the caller forgot to cancel manually.
- C) The GIL prevented two coroutines from running concurrently.
- D) `gather` allocated 8 MB per task, exhausting memory at fan-out >100.

<details>
<summary>Answer</summary>

**B** — the classic leak. `gather` raises before children finish cancelling — and in the default mode, it does not cancel survivors at all. The caller had to remember to `for t in pending: t.cancel()`. `TaskGroup` made this automatic, which is why every new asyncio program should default to it.

</details>

If 9+: ship homework. 7-8: re-read Lectures 2 and 3. <7: re-read all three.

---
