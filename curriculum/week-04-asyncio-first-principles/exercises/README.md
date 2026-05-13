# Week 4 — Exercises

Three exercises, ~5 hours total. Do them in order.

| # | File | Time | What you build |
|--:|------|-----:|----------------|
| 1 | [exercise-01-toy-event-loop.py](./exercise-01-toy-event-loop.py) | 90 min | A ~200-line event loop + Future + Task + sleep that runs two coroutines concurrently. No `import asyncio`. |
| 2 | [exercise-02-async-vs-thread-fetch.py](./exercise-02-async-vs-thread-fetch.py) | 60 min | A local HTTP server + 200 concurrent fetches three ways (ThreadPoolExecutor, asyncio + aiohttp, asyncio + run_in_executor bridge). Compare wall-clock, memory, latency. |
| 3 | [exercise-03-taskgroup-fan-out.py](./exercise-03-taskgroup-fan-out.py) | 45 min | Watch `asyncio.TaskGroup` cancel siblings on first failure, then collect *every* error into an `ExceptionGroup`. Compare to `gather`. |

## Order of operations

- **Monday afternoon:** Exercise 1, after Lecture 1. The lecture gives you the model; the exercise gives you the muscle.
- **Tuesday afternoon:** Exercise 2, after Lecture 2. Run it on your laptop and write down the numbers — the order of magnitude is the lesson.
- **Wednesday afternoon:** Exercise 3, after Lecture 3. Read the output carefully, especially the `finally` lines.

## How to verify

```bash
python exercise-01-toy-event-loop.py
python exercise-02-async-vs-thread-fetch.py
python exercise-03-taskgroup-fan-out.py
```

All three are standalone scripts. No `pytest`. No setup. Exercise 2 will use `aiohttp` if installed and fall back to `urllib` if not.

## What "done" looks like

For each: the script ran, the output matches the shape in the `# EXPECTED OUTPUT` comment block at the bottom, and you can answer the questions in the `# REFLECTION` section without re-reading the lecture.

If you cannot, the lecture is closer to where you need to look than the exercise solution is. Re-read.
