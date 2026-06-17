# Challenge 1 — Build a runnable asyncio clone in 4 hours

**Time:** ~4 hours, in one continuous block. Set a timer.
**Difficulty:** Hard.
**Prerequisite:** Exercise 1 done, all three lectures read.

## The brief

Build a runnable subset of `asyncio` in **≤300 lines of Python** (including imports and the demo `if __name__ == "__main__":` block, excluding blank lines and comments). It must expose:

1. A single-threaded event loop class with `call_soon`, `call_later`, `run_until_complete`, and `time`.
2. A `Future` with `set_result`, `set_exception`, `cancel`, `add_done_callback`, `result`, `done`, `cancelled`, and a working `__await__`.
3. A `Task` (subclass of `Future`) whose constructor schedules itself and whose `__step` drives the coroutine to completion. Cancellation must propagate to the awaited future.
4. A `sleep(seconds)` function (coroutine) that suspends the calling task for at least `seconds` seconds.
5. A `gather(*coros, return_exceptions=False)` that returns a future completing when all inputs complete; on first error (default), cancels the rest.
6. A `run(coro)` entry point analogous to `asyncio.run`.

Use only `collections`, `heapq`, `time`, `types`, `typing`, and `functools` from the standard library. **No `import asyncio` and no `selectors` for this challenge** — we are testing your understanding of the engine, not your ability to wire I/O. (The mini-project adds I/O.)

The demo (at the bottom of your file) should run three concurrent workers via `gather`, one of which fails after 50ms, and demonstrate that the other two are cancelled before they complete their sleeps. Wall-clock should be ~50ms, not the maximum of the three sleeps.

## Acceptance criteria

- [ ] Source file is named `clone.py`, ≤300 non-blank non-comment lines (verify with `grep -cv '^\s*\(#\|$\)' clone.py`).
- [ ] Imports only from the standard library.
- [ ] Runs as `python clone.py` and prints a sensible demo trace.
- [ ] `Future.__await__` yields `self` when not done; returns `self.result()` when done.
- [ ] `Task.__step` handles three cases: coroutine returns (StopIteration → `set_result`), coroutine yields a Future-like (register `__step` as a done-callback), coroutine raises (→ `set_exception`).
- [ ] `gather` cancels surviving siblings on first exception when `return_exceptions=False`.
- [ ] `Task.cancel()` propagates to `_fut_waiter`.
- [ ] No leaked tasks at the end of the demo (your output should make this obvious).

## Time budget (suggested)

| Phase | Time |
|-------|------|
| Read your Exercise 1 solution carefully **once**, then close it | 10 min |
| Sketch the API on paper (class signatures, method dispatch) | 15 min |
| Write `Future` + the state machine | 30 min |
| Write the event loop (`call_soon`, `call_later`, `_run_once`, `run_until_complete`) | 45 min |
| Write `Task.__step` and `__wakeup` | 45 min |
| Write `sleep` and the demo | 20 min |
| Write `gather` | 30 min |
| Make the demo show cancellation correctly | 30 min |
| Trim to ≤300 lines and final test | 15 min |
| **Total** | **~4 h** |

## What to expect (gotchas in advance)

1. **The first `coro.send(value)` must be `coro.send(None)`** (PEP 492). If you send anything else into a fresh coroutine, you get `TypeError: can't send non-None value to a just-started coroutine`.
2. **`StopIteration` is the result-delivery channel** — `stop.value` is what the coroutine `return`-ed. If you `except StopIteration`, take `.value`.
3. **The `_asyncio_future_blocking` marker matters.** Real asyncio sets this on `Future.__await__` to differentiate "this is an asyncio future I want you to wait on" from "this is some other yielded value." Without it, your `Task.__step` cannot distinguish a future from a bug.
4. **`add_done_callback` on a done future must `call_soon` the callback, not call it inline.** Calling inline causes re-entrance bugs when a callback that adds a callback ends up running twice.
5. **The "first send None" rule has a corollary**: `Future.__await__` yields `self`, the loop sees it; *then* `Task.__step` registers `__step` as a done-callback. When the future is set, the callback runs, calls `__step()`, which does `coro.send(None)` again. The coroutine resumes; its `__await__` re-enters; this time the future is done, so `__await__` does `return self.result()` (via `StopIteration(value)` in the generator semantics). The result becomes the value of the `await` expression.
6. **`gather`'s first-exception cancellation has to happen exactly once.** If two children fail simultaneously, you do not want to cancel each of them N times. A `_first_exc = None` flag plus a check fixes this.

## Hints

<details>
<summary>Hint 1 - the Future state machine</summary>

```python
class Future:
    _state = "PENDING"
    def set_result(self, v):
        if self._state != "PENDING": raise ...
        self._result = v
        self._state = "FINISHED"
        self._fire_callbacks()
    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True
            yield self
        return self.result()
```

Three states, three transitions. Don't over-engineer.

</details>

<details>
<summary>Hint 2 - the Task step</summary>

```python
def __step(self, _previous=None):
    exc = None
    if _previous is not None and _previous._exception is not None:
        exc = _previous._exception
    elif _previous is not None and _previous.cancelled():
        exc = CancelledError()
    try:
        result = self._coro.throw(exc) if exc else self._coro.send(None)
    except StopIteration as stop:
        self.set_result(stop.value); return
    except BaseException as e:
        self.set_exception(e); return
    if isinstance(result, Future):
        result.add_done_callback(self.__step)
    elif result is None:
        self._loop.call_soon(self.__step)
```

Read three times. Sketch on paper. Implement once.

</details>

<details>
<summary>Hint 3 - gather's done-callback</summary>

```python
def _done_cb(idx, fut):
    if outer.done(): return
    if fut.cancelled():
        if not return_exceptions:
            outer.cancel(); return
        results[idx] = CancelledError()
    elif fut.exception():
        if return_exceptions:
            results[idx] = fut.exception()
        else:
            if first_exc[0] is None:
                first_exc[0] = fut.exception()
                for o in children:
                    if not o.done(): o.cancel()
    else:
        results[idx] = fut.result()
    pending[0] -= 1
    if pending[0] == 0:
        if first_exc[0]: outer.set_exception(first_exc[0])
        else: outer.set_result(results)
```

Note the `pending[0]` list trick — Python 3 closures can't rebind a captured int, only mutate.

</details>

## Stretch (only if you finished in under 3 hours)

- Add a `TaskGroup` analogue. ~80 more lines. See Lecture 3 §5.
- Add a `wait_for(coro, timeout)` that races a `sleep(timeout)` against the coroutine and cancels whichever loses.
- Add `as_completed(*coros)` returning a generator of futures in completion order. ~30 lines.

## Submission

Commit `clone.py` plus a short `notes.md` (~200 words):

1. What was hard?
2. What did you simplify out?
3. What would you build next if you had another hour?

## Why this matters

You are about to spend a weekend on the mini-project. That mini-project is **the same clone**, but with I/O, with tests, with a README, with a small benchmark. Doing the engine first, in 4 hours, against a timer, with no reference — that is the move that turns "I sort of understand asyncio" into "I can rebuild asyncio from memory." Every senior Python engineer should be able to do this once. After this, you will read `Lib/asyncio/tasks.py` and recognize the structure.

The artifact does not need to be polished. The point is the muscle, not the artifact. The mini-project is the polished artifact.
