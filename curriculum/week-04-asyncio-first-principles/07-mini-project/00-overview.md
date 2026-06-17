# Mini-Project — `mini_asyncio`: a toy `asyncio` clone

> Build a real, reusable subset of `asyncio` from scratch. ≤500 lines of pure Python. No `import asyncio`. Supports `Future`, `Task`, `sleep`, `gather`, `run`, and (stretch) a `TaskGroup` analogue and an I/O selector. Publish it on GitHub.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-04-mini-asyncio-<yourhandle>` containing:

1. **`mini_asyncio/__init__.py`** — the package, re-exporting `run`, `sleep`, `gather`, `Task`, `Future`, `get_running_loop`, `CancelledError`, `TimeoutError`. ≤500 non-blank, non-comment lines total across the package. Pure stdlib. Compiles on CPython 3.11+.
2. **`mini_asyncio/loop.py`** — the `EventLoop` class with `call_soon`, `call_later`, `run_until_complete`, and the `_run_once` step (timers + optional selector for I/O).
3. **`mini_asyncio/futures.py`** — `Future` with the full PENDING → {FINISHED, CANCELLED} state machine.
4. **`mini_asyncio/tasks.py`** — `Task`, `gather`, `sleep`, `wait_for` (stretch).
5. **`mini_asyncio/runner.py`** — `run(coro)` analogue of `asyncio.run`, with proper teardown.
6. **`README.md`** — what it is, how to install (`pip install -e .` or just `python -m`), how to use it, example output, a paragraph on the design tradeoffs.
7. **`examples/`** — at least two short scripts whose trace is illuminating. One must use `gather` with one failing child to demonstrate sibling cancellation. One must use `sleep` to demonstrate concurrent timer overlap.
8. **`tests/test_mini_asyncio.py`** — at least five tests covering:
   - A single coroutine returns a value via `run`.
   - Two coroutines with overlapping sleeps complete in `max(...)` wall-clock, not `sum(...)`.
   - A coroutine that raises propagates the exception out of `run`.
   - `gather(a, b, c)` returns `[a_result, b_result, c_result]` in input order.
   - `gather(a, raising_b, c)` with `return_exceptions=False` cancels `a` and `c` and raises the exception from `b`.
9. **`design.md`** — 600–900 words on:
   - The state machine of `Future`. Cite PEP 492 and the asyncio source.
   - The `Task.__step` algorithm. Cite `Lib/asyncio/tasks.py:Task.__step` by file:line.
   - What you chose to omit (almost certainly: I/O selector, `call_soon_threadsafe`, signal handling, ContextVar propagation, subprocess support). Argue your priorities.
   - What you would add if you had another week.

## What the clone must do

- **Run any pure-Python coroutine program** that uses only `sleep`, `gather`, `Task`, `run` from your package, with semantics matching `asyncio` for those primitives.
- **`Task.__step` must drive the coroutine correctly**: send `None` first; on `StopIteration`, capture `.value` as the result; on exception, set the exception; on a yielded `Future`, register `__step` as the future's done-callback.
- **`Future.__await__` must yield self while pending and return result when done.** Set `_asyncio_future_blocking = True` before the yield (the marker your `Task.__step` reads).
- **`gather` must cancel siblings on first exception** (default mode). Must support `return_exceptions=True`.
- **`sleep(seconds)` must schedule a timer and return a coroutine that awaits the future the timer completes.** `sleep(0)` must yield to the loop without scheduling a timer (the canonical fairness checkpoint).
- **`run(coro)` must construct a fresh loop, wrap `coro` in a `Task`, `run_until_complete`, and close the loop cleanly.** No leaked tasks.
- **`CancelledError` must propagate cleanly** from `task.cancel()` through `_fut_waiter` into the coroutine at its next `await`.

## Acceptance criteria

- [ ] Repo public on GitHub at the URL above.
- [ ] `cloc mini_asyncio/` reports ≤500 lines, blanks and comments excluded.
- [ ] `pytest tests/` passes on CPython 3.11 and 3.13.
- [ ] `python examples/fan_out.py` produces a readable trace showing concurrent sleeps.
- [ ] `python examples/cancellation.py` produces a readable trace showing sibling cancellation.
- [ ] `design.md` exists and explains the choices.
- [ ] README at the repo root is sufficient for a reviewer to install, run, and read the output without asking you.

## Suggested order of operations

### Phase 1 — Bones (90 min)

1. From Challenge 1, you already have a working ≤300-line single-file draft. Start there. If you didn't do the challenge: do it now (4h); then come here.
2. Move it into the new repo. Split into `loop.py`, `futures.py`, `tasks.py`, `runner.py`. Add `__init__.py` with the re-exports.
3. Add the `tests/` directory. Pin Python 3.11+ in `pyproject.toml`.

### Phase 2 — Tests first (90 min)

4. Write the five required tests. They should all fail at first; the tests are the spec.
5. Make them pass one by one. Resist the temptation to add features the tests don't drive.

### Phase 3 — Polish the demos (90 min)

6. `examples/fan_out.py`: kicks off 10 coroutines with random sleep durations 0.01–0.10s; `gather`s them; prints "done in X.Xs" where X.X is approximately 0.10, not 0.55.
7. `examples/cancellation.py`: 3 coroutines; the middle one raises after 0.05s; the other two have 0.20s sleeps. Print the "finally cleanup" line for each. Wall-clock ~0.05s.
8. Confirm both examples are visually convincing as proof your loop is real.

### Phase 4 — CLI / runtime polish (60 min)

9. Add a `python -m mini_asyncio examples/fan_out.py` runner that reads a target script and executes it under your loop. (Optional but good portfolio polish.)
10. Make sure `run` cleans up: no leaked tasks, no warnings on shutdown.

### Phase 5 — Documentation and publish (60 min)

11. Write the `design.md` thoughtfully. This is the artifact that survives the longest.
12. Push to GitHub. Verify the example output renders correctly in the rendered README.

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| `mini_asyncio/` ≤ 500 lines and clear | 20% | Reads top-to-bottom in one pass; no clever tricks needed |
| Correctness: `sleep`, `gather`, `Task`, `Future`, `run` | 30% | All five primitives match real `asyncio` for the documented behaviors |
| Tests | 15% | All five required tests, plus two of your own |
| `design.md` is technically substantive | 20% | Cites `Lib/asyncio/tasks.py` by file:line, PEP 492 by section, explains tradeoffs without hand-waving |
| README is reviewer-friendly | 10% | One-screen install + use; clear examples |
| Optional: stretch features | 5% | See below |

## Stretch (optional, +5%)

Pick one (or more):

- **`TaskGroup` analogue.** ~80 lines. Implement the `async with`-style structured-concurrency primitive from Lecture 3 §5. Must use `ExceptionGroup` on PEP 654-aware Python (3.11+).
- **`wait_for(coro, timeout)`.** Race a `sleep(timeout)` against the coroutine; cancel whichever loses; raise `TimeoutError` if the coroutine didn't finish.
- **I/O selector.** Add a `selectors.DefaultSelector` to `_run_once`. Support `loop.sock_recv` and `loop.sock_send` for raw TCP. Implement an `examples/tcp_echo.py` that uses your loop, not `asyncio`. ~100 more lines.
- **`as_completed(*coros)`** returning an iterator of futures in completion order. ~30 lines.
- **Eager-task-factory.** Mirror the 3.12 optimization where a coroutine that returns without `await`-ing runs synchronously inside `Task.__init__` instead of being scheduled for a future tick. Document the speedup in the `design.md`.

## Why this matters

A toy `asyncio` clone is the kind of artifact a senior Python engineer should have built once. The real `asyncio` is 12 000 lines; yours is 500. The 500 are the *engine*. After this project, when you read `Lib/asyncio/tasks.py:Task.__step` in production, you will recognize every line. When a colleague says "the loop is wedged," you will know to ask "wedged in what phase — timers, selector, or callback dispatch?" When you debug a hanging coroutine, you will be able to draw the cycle of futures and callbacks on a whiteboard from memory.

This artifact is **public-facing**: it goes on your GitHub, it's reasonable to mention in a senior-role interview ("I built a 500-line asyncio clone with `sleep`, `gather`, `Task`, and structured concurrency"). The ones in the wild — David Beazley's `curio`, the `trio` project itself — are larger and more featureful, but the *core* in each of them is exactly what you are building. After this project, you can read the source of any of those tools and recognize the shape.

## Submission

Push to GitHub. Paste the URL into `c17-week-04-submission.md` in your portfolio repo with one sentence on what you'd do next if you had another day.

After: continue to [Week 5 — Structured Concurrency, Cancellation, Back-Pressure](../../week-05-structured-concurrency-cancellation-backpressure/) — coming soon. Week 5 takes this clone's `TaskGroup` analogue and hardens it.
