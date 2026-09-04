# Week 5 — Quiz

Ten questions. Lectures closed.

---

**Q1.** Nathaniel J. Smith's one-rule definition of structured concurrency is:

- A) Every async function must be `async def` (the "colored function" rule).
- B) Every concurrent task has a syntactic parent block, and the block does not exit until every child task is done.
- C) Every coroutine must `await` at least once per second so it remains cancellable.
- D) Every `asyncio.Task` must be a member of an `asyncio.TaskGroup`.

<details>
<summary>Answer</summary>

**B** — the one-rule definition. Every other answer is a tangentially related rule, not the definition. Cite Smith 2018, *Notes on structured concurrency*.

</details>

---

**Q2.** Inside an `asyncio.TaskGroup`, child task `B` raises a `ValueError`. Sibling tasks `A` and `C` are still running their `await asyncio.sleep(...)` calls. What happens?

- A) `A` and `C` continue running; the `ValueError` is logged at shutdown.
- B) `A` and `C` are cancelled via `task.cancel()`; their `finally` blocks run; the group's `__aexit__` then raises a `BaseExceptionGroup` containing the `ValueError`.
- C) The `ValueError` is silently absorbed; the `TaskGroup` exits normally because cancellation handles errors.
- D) The group raises a single `ValueError` (matching `gather`'s default behavior); `A` and `C` continue in the background.

<details>
<summary>Answer</summary>

**B** — the cancel cascade. `_on_task_done` sees a non-`CancelledError` exception and calls `self._abort()`, which cancels every other running child. The `try/finally` in each child runs. On group exit, `BaseExceptionGroup("unhandled errors in a TaskGroup", [ValueError])` is raised. Cite `Lib/asyncio/taskgroups.py:_on_task_done`.

</details>

---

**Q3.** Since Python 3.8, `asyncio.CancelledError` inherits from:

- A) `Exception`. `except Exception:` catches it. (Unchanged from 3.7.)
- B) `BaseException`. `except Exception:` does *not* catch it; `except BaseException:` does.
- C) `KeyboardInterrupt`. Both share the "interruption" semantics.
- D) `SystemExit`. The asyncio runtime treats them identically during shutdown.

<details>
<summary>Answer</summary>

**B** — `BaseException`. The 3.8 What's New documents the reparenting. The practical consequence: `try: ... except Exception:` over an `await` is now safe; pre-3.8 it was the canonical "swallowed cancellation" bug.

</details>

---

**Q4.** Inside `async with asyncio.timeout(5):`, the deadline fires. The `await` inside the block raises:

- A) `TimeoutError`, which the inner code can catch and handle.
- B) `CancelledError`, which the inner code can catch. The outer `async with` then converts that to a `TimeoutError` after calling `Task.uncancel()`.
- C) Nothing — the block is forcibly returned-from without an exception.
- D) `RuntimeError`, because deadline expiry is a runtime fault.

<details>
<summary>Answer</summary>

**B** — inner sees `CancelledError`, outer raises `TimeoutError`. The conversion happens in `Timeout.__aexit__` after `Task.uncancel()`. The asymmetry is deliberate: inner cleanup uses the same exception path as any other cancellation; outer callers see a distinguishable error type. Cite `Lib/asyncio/timeouts.py:Timeout.__aexit__`.

</details>

---

**Q5.** `Task.uncancel()` (3.11+) is necessary because:

- A) It is the public API for "forget I called `.cancel()` on this task," used when a cancellation source (like `asyncio.timeout`) wants to absorb the cancel it issued so it does not propagate further. The underlying `_num_cancels_requested` counter is decremented.
- B) It restarts a cancelled task from the point of cancellation.
- C) It moves a cancelled task back to the `PENDING` state in the `Future` state machine.
- D) It is a 3.13 backport of Trio's `CancelScope.shield = True`.

<details>
<summary>Answer</summary>

**A** — the counter-decrement absorbtion. Without `uncancel`, nested timeouts cannot compose: an inner timeout's cancel would propagate past its `__aexit__` and the outer would mistake it for its own cancellation. Cite `Lib/asyncio/tasks.py:Task.uncancel` and `Lib/asyncio/timeouts.py:Timeout.__aexit__` for the `<= self._cancelling` predicate.

</details>

---

**Q6.** `asyncio.shield(coro)` is called from a task `T`. While the inner coroutine is running, `T` is cancelled. What happens?

- A) Both `T` and the inner coroutine are cancelled.
- B) The inner coroutine is cancelled; `T` raises `CancelledError`.
- C) `T` raises `CancelledError`; the inner coroutine continues to run on the loop (it was wrapped in a `Task` by `shield`). The inner's result is now orphaned unless the caller holds a separate reference.
- D) The cancellation is ignored entirely; both continue.

<details>
<summary>Answer</summary>

**C** — the directional semantics. `shield` wraps the inner in a real Task; the outer `await shield(...)` is a checkpoint on a separate future linked by done-callbacks. Cancelling the outer task only unwires the link; the inner task is still scheduled on the loop and runs to completion. Cite `Lib/asyncio/tasks.py:shield`.

</details>

---

**Q7.** An async pipeline has a fast producer (10 000 items/sec) and one slow consumer (100 items/sec). Bridging them with `asyncio.Queue(maxsize=100)`:

- A) Memory grows to 100 items and stays there; the producer's `put` parks each time the queue is full, throttling it to the consumer's rate. This is back-pressure.
- B) Memory grows without bound; `maxsize` is only a soft hint.
- C) The producer exits with `asyncio.QueueFull`.
- D) The consumer is sped up automatically to match the producer.

<details>
<summary>Answer</summary>

**A** — bounded memory plus back-pressure. The producer's `put` is the regulator. This is the entire reason `maxsize` exists. Cite `Lib/asyncio/queues.py:Queue.put`.

</details>

---

**Q8.** Which is true about `asyncio.Queue.shutdown()` (3.13+)?

- A) It clears the queue immediately and silently.
- B) With `immediate=False`, it marks the queue closed: subsequent `put` raises `QueueShutDown`, `get` on an empty queue raises `QueueShutDown`, but pending items can still be drained.
- C) It blocks until every `task_done` has been called.
- D) It only works on `asyncio.PriorityQueue`, not the base `Queue`.

<details>
<summary>Answer</summary>

**B** — `shutdown(immediate=False)` semantics. `immediate=True` is the harder variant that drops pending items. Cite `Lib/asyncio/queues.py:Queue.shutdown` (3.13). Also Python 3.13 What's New.

</details>

---

**Q9.** `asyncio.Semaphore(N)` vs. `asyncio.Queue(maxsize=N)` — choose `Queue` when:

- A) You need to bound the *number of items in flight* in a pipeline. The queue is both a buffer and the back-pressure regulator.
- B) Always. `Queue` is strictly more powerful.
- C) You want a counter without storage.
- D) You need to throttle a single class of operation (e.g., outbound HTTP calls).

<details>
<summary>Answer</summary>

**A** — `Queue` is storage + back-pressure; `Semaphore` is a counter. Choose `Semaphore` for "at most N concurrent connections to host H." Choose `Queue` for "pipeline of items with N consumers downstream." Both are valid bound primitives, but they bound *different things*.

</details>

---

**Q10.** A common pre-3.11 bug, before `TaskGroup`, was:

- A) Forgetting to `await` an `asyncio.create_task(...)`, so the child either leaked (no waiter) or its exception was silently swallowed (no observer).
- B) Calling `asyncio.run` more than once in the same process.
- C) Using `async for` on a regular generator.
- D) Setting the event loop policy on Windows.

<details>
<summary>Answer</summary>

**A** — the "leaked task" / "swallowed exception" bug. Surface area: `create_task(coro)` returns a `Task`; if no one `await`s it, the coroutine eventually runs (the loop schedules it), but the parent function has returned and the result is lost. If the coroutine raises, the exception lands on the Task object; asyncio prints a warning at shutdown, but the caller is long gone. `TaskGroup` retired this bug class.

</details>

If 9+: ship homework. 7–8: re-read Lectures 1 and 2. <7: re-read all three.

---
