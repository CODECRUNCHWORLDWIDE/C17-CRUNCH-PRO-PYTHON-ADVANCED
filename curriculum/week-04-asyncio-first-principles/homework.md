# Week 4 — Homework

Six problems, ~6 hours total. Commit each as you finish.

---

## Problem 1 — Read `Lib/asyncio/tasks.py` and trace one step (60 min)

Open `Lib/asyncio/tasks.py` in the CPython main branch on GitHub:
<https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py>

Find the `Task` class. Find `Task.__step` (look for `def __step` — note the double underscore).

**Acceptance:** `task-step-reading.md` in your portfolio:

- A GitHub permalink to the exact line where `__step` is defined.
- A 250-word, line-by-line walkthrough of one full `__step` call when the coroutine yields a `Future`. Cover: where does `coro.send` happen, where is the `_fut_waiter` set, where is `__wakeup` registered, what does the `_must_cancel` flag do.
- One observation: which line of `__step` would you change if you were implementing the `eager-task-factory` optimization landed in 3.12 (read the surrounding code if unfamiliar).

---

## Problem 2 — Implement `wait_for` on top of your toy loop (45 min)

Take Exercise 1's `clone.py` (or your in-progress mini-project) and add:

```python
async def wait_for(awaitable, timeout):
    """Wait at most `timeout` seconds for `awaitable`. Raise TimeoutError if
    it doesn't finish in time. Cancel the underlying task on timeout."""
```

**Acceptance:**

- `wait_for_demo.py` running against your clone, demonstrating both success (short-running) and timeout (long-running).
- A `notes.md` paragraph: what is the order of cancel propagation? If `wait_for` cancels the inner task, and the inner task is in a `try/finally`, when does the finally block run *relative to* `wait_for` raising `TimeoutError`?

---

## Problem 3 — Benchmark `gather` vs. `TaskGroup` (45 min)

Write `bench_gather_vs_taskgroup.py` that runs 1000 short-sleep coroutines (each `await asyncio.sleep(0.001)`) two ways:

```python
async def via_gather():
    await asyncio.gather(*[asyncio.sleep(0.001) for _ in range(1000)])

async def via_taskgroup():
    async with asyncio.TaskGroup() as tg:
        for _ in range(1000):
            tg.create_task(asyncio.sleep(0.001))
```

Benchmark each with `time.perf_counter()`, averaged over 20 runs.

**Acceptance:**

- `bench_gather_vs_taskgroup.py` plus a `results.md` with the wall-clock numbers (mean and stdev).
- Answer: is there a measurable overhead to `TaskGroup` vs. `gather` in the no-error case? Why or why not? (Hint: read the `gather` source. `gather` *also* creates a Task per coroutine. Both should be within noise.)

---

## Problem 4 — Build a simple async TCP echo server (60 min)

Using **real** `asyncio` (not your clone), write `echo_server.py` and `echo_client.py`:

- Server: listens on `127.0.0.1:5050`. Each accepted connection reads one line, sends it back, closes. Handles many concurrent connections.
- Client: opens N concurrent connections, sends "hello {i}\n" on each, reads the response, asserts the echo is correct.

Use `asyncio.start_server`, `asyncio.open_connection`, and `StreamReader`/`StreamWriter`.

**Acceptance:**

- Both scripts working.
- A `notes.md` paragraph: trace one connection's lifetime. What primitive completes the `await reader.readline()` call? (Read `Lib/asyncio/streams.py` and find out.)
- Bonus: confirm via `lsof -p PID` that the server holds N file descriptors but only one thread.

---

## Problem 5 — Read PEP 654 and write your own `except*` example (45 min)

PEP 654 is the most important asyncio-adjacent PEP since PEP 492. Read it: <https://peps.python.org/pep-0654/>.

**Acceptance:**

- `pep654-reading.md` containing:
  - A 250-word summary of `ExceptionGroup` and `except*` in your own words.
  - A code snippet (yours, not from the PEP) that raises a group of three different exception types, then uses three `except*` clauses to handle them, then runs `assert` on each clause's `eg.exceptions` to confirm correct splitting.
  - One subtlety the PEP discusses that you'd missed before reading it.

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 400–500 words:

1. Before this week, what was your mental model of "how `asyncio` runs a coroutine"? How has it sharpened? Be specific about what changed.
2. The "colored function" debate (Nystrom 2015). After three weeks of working with asyncio at the interpreter level, do you find the colors more useful or more burdensome? Defend with one concrete codebase you've worked on.
3. If you were starting a new IO-bound Python service today (2026), would you reach for `asyncio` + `aiohttp`, or for stdlib threads, or for something else? Give two concrete tradeoffs.
4. Which lecture was the hardest to follow? What single concept would have helped if it had come earlier?
5. What is the next thing you would want to learn about `asyncio` after this week? Name a file in `Lib/asyncio/` you would open.

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 — `Lib/asyncio/tasks.py` reading | 60 min |
| 2 — implement `wait_for` on your clone | 45 min |
| 3 — bench `gather` vs `TaskGroup` | 45 min |
| 4 — async TCP echo server | 60 min |
| 5 — PEP 654 reading | 45 min |
| 6 — reflection | 45 min |
| **Total** | **~5 h** |

After homework, ship the [mini-project](./mini-project/README.md).
