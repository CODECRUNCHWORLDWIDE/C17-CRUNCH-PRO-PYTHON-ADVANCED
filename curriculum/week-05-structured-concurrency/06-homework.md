# Week 5 — Homework

Six problems, ~6 hours total. Commit each as you finish.

---

## Problem 1 — Read `Lib/asyncio/taskgroups.py` end-to-end (60 min)

Open `Lib/asyncio/taskgroups.py` in the CPython main branch on GitHub: <https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py>.

Read the whole file. It is ~250 lines as of 3.13. You should now recognise every line after Lecture 1.

**Acceptance:** `taskgroups-reading.md` in your portfolio:

- A GitHub permalink to `TaskGroup._on_task_done`.
- A 300-word, line-by-line walkthrough of what happens when:
  - Child task `B` raises a `ValueError`.
  - `_on_task_done(B)` runs and detects `task.exception() is ValueError`.
  - `_abort()` cancels every other running child.
  - The parent task (the one running `__aexit__`) is cancelled to break out of `await self._on_completed_fut`.
  - On `__aexit__`'s exit, `self._parent_task.uncancel()` absorbs the cancel; `BaseExceptionGroup` is raised.
- One observation: which line is the `_parent_task.uncancel()` call, and why does the predicate `if self._parent_task.uncancel() == 0` exist (what is it checking)?

---

## Problem 2 — Implement a `TaskGroup` analogue against your `mini_asyncio` (60 min)

Take last week's `mini_asyncio` clone. Add `tg.py`:

```python
class TaskGroup:
    """A toy TaskGroup analogue. Public surface:
      __aenter__ -> self
      __aexit__ -> wait for every spawned task, raise ExceptionGroup if any failed
      create_task(coro) -> Task
    """
    ...
```

Requirements:

- Match the asyncio TaskGroup behavior on the exercises we did this week. In particular, scenario 1 from `exercise-01-taskgroup-with-cancel.py` (a child cancelled from outside) must *not* trigger the cascade; scenario 2 (a child raises) must.
- Use `BaseExceptionGroup` (PEP 654, built into Python 3.11+).
- Use your `Future`, your `Task`, your loop. Do not import asyncio.

**Acceptance:**

- `tg.py` in your `mini_asyncio` repo (or a separate `mini_asyncio_w5` repo).
- `tests/test_taskgroup.py` with the four scenario tests from `exercise-01-taskgroup-with-cancel.py`, adapted to your loop.
- A `notes.md` paragraph: how does your implementation differ from `Lib/asyncio/taskgroups.py`? Are you using `uncancel`? If not, what compromises did you make?

---

## Problem 3 — Implement `asyncio.timeout` analogue (45 min)

Add `timeouts.py` to your `mini_asyncio` clone:

```python
class Timeout:
    def __init__(self, when: float | None): ...
    async def __aenter__(self) -> "Timeout": ...
    async def __aexit__(self, et, exc, tb): ...

def timeout(delay: float | None) -> Timeout: ...
```

Requirements:

- Schedule a callback at `loop.time() + delay` that cancels the current task.
- On `__aexit__`, if the cancellation came from your timer, call `task.uncancel()` (you will need to add `uncancel` to your `Task`) and raise `TimeoutError`.
- If the cancellation came from another source (`task.cancel()` from outside), let `CancelledError` propagate.

**Acceptance:**

- `timeouts.py` in your repo.
- A test demonstrating both: an inner deadline expires; an outer caller sees `TimeoutError`. A separate `task.cancel()` from outside the timeout context propagates as `CancelledError`.
- A `notes.md` paragraph: what is the equivalent in your loop of `Lib/asyncio/timeouts.py:_on_timeout`? Cite by file:line.

---

## Problem 4 — Build an async producer/consumer pipeline (60 min)

Write `pipeline.py` using real `asyncio` (not your clone):

- Reads URLs from stdin, one per line.
- Fans them out to N workers (CLI argument, default 16).
- Workers fetch each URL with `aiohttp` and apply a per-fetch timeout of 5s.
- Results are pushed into a sink queue.
- A single sink writer drains the queue and writes one JSON line per result to stdout.
- All tasks live in one `TaskGroup`.
- The frontier queue has `maxsize=64`; the sink queue has `maxsize=16`.

**Acceptance:**

- `pipeline.py` working: `echo -e "https://example.com/\nhttps://example.org/" | python pipeline.py 4`.
- A `results.md` capturing wall-clock for 100 URLs with N=1, 4, 16, 64. Plot or table.
- A `notes.md` paragraph: where does back-pressure manifest in your code? Add a `monitor` task that prints `frontier.qsize()` and `sink.qsize()` every second; observe when each fills.

---

## Problem 5 — Reproduce the "swallowed `CancelledError`" bug (30 min)

Write `swallow.py` that demonstrates:

```python
async def handler():
    try:
        await asyncio.sleep(1.0)
    except Exception:                 # WRONG: catches CancelledError on 3.7. Correct on 3.8+.
        await record_failure()
        return None
```

Build a small driver that runs `handler` under `asyncio.timeout(0.05)` and prints:

- On Python 3.8+ (your local install), the timeout fires and `TimeoutError` propagates correctly because `except Exception:` no longer catches `CancelledError`.
- Now change the `except Exception:` to `except BaseException:` (the bug). Re-run. Observe the timeout firing but no `TimeoutError` propagating — the `CancelledError` is swallowed and the caller sees `None` instead.

**Acceptance:**

- `swallow.py` showing both runs side by side.
- A `notes.md` paragraph: cite the [3.8 What's New](https://docs.python.org/3/whatsnew/3.8.html#asyncio) entry. Explain why this matters more in async than in sync code (hint: cancellation is the primary way async work is bounded).

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 400–500 words:

1. Before this week, what was your mental model of cancellation in async Python? How has it sharpened? Be specific about what changed.
2. Have you written code that swallows `CancelledError`? Find it (your own code or a project you contribute to). Either fix it or document it as "intentional, because X." Defend the choice.
3. The structured-concurrency rule (Smith 2018): every task has a syntactic parent. How would adopting this rule simplify a piece of async code you have shipped? Name the file and one concrete simplification.
4. The "colored function" problem: cancellation only works in async-coloured frames. Does this fact change your view of the color debate (more in favor of async colors; less in favor; unchanged)?
5. If you were starting a new IO-bound Python service today (2026), would you reach for asyncio + TaskGroup, for Trio, or for anyio? Give two concrete tradeoffs.
6. Which lecture was the hardest to follow? What single concept would have helped if it had come earlier?

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 — `Lib/asyncio/taskgroups.py` reading | 60 min |
| 2 — `TaskGroup` analogue on your clone | 60 min |
| 3 — `asyncio.timeout` analogue on your clone | 45 min |
| 4 — async producer/consumer pipeline | 60 min |
| 5 — swallowed-cancellation reproduction | 30 min |
| 6 — reflection | 45 min |
| **Total** | **~5 h** |

After homework, ship the [mini-project](./07-mini-project/00-overview.md): a robust async web crawler with cancellation handling and back-pressure to a sink.
