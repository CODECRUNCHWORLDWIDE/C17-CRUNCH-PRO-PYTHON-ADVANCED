# Week 6 — Exercises

Three short, focused exercises. Each runs in 30–45 minutes. Each isolates one primitive from the lectures and exercises it with a small, deliberate measurement.

All three require **Python 3.11 or newer**; the free-threaded variants in Exercises 1 and 2 are gated on detecting 3.13t at runtime and will skip cleanly if unavailable. Exercise 2 requires `aiohttp` (`pip install aiohttp`) and `requests` (`pip install requests`).

| # | File | Focus | Time |
|---|------|-------|------|
| 1 | [`exercise-01-CPU-bound-with-multiprocessing.py`](./exercise-01-CPU-bound-with-multiprocessing.py) | Pure-Python CPU kernel under serial / thread pool / process pool / 3.13t threads | 45 min |
| 2 | [`exercise-02-IO-bound-with-async.py`](./exercise-02-IO-bound-with-async.py) | The same N HTTP fetches under `asyncio.gather`, `ThreadPoolExecutor`, `ProcessPoolExecutor` | 45 min |
| 3 | [`exercise-03-mixed-with-threadpool.py`](./exercise-03-mixed-with-threadpool.py) | A fetch-then-hash worker; observe where each primitive wins | 30 min |

## How to do them

Read the lecture for the day before the exercise:

- Exercise 1 ← Lecture 1 (threading + GIL) and Lecture 2 (multiprocessing). Also Lecture 3 if you have 3.13t installed.
- Exercise 2 ← Lecture 1 §3 (the GIL-release test, applied to HTTP).
- Exercise 3 ← Lecture 1 §4 (the executor idioms) and Lecture 2 §8 (`run_in_executor`).

Then run the script. Then **read the source**: the comments are the spec. Then answer the reflection questions at the bottom of each file.

The expected-output sections at the bottom of each file are approximate (timings vary by hardware) but the *ordering* of the timing rows is the load-bearing observation. If your ordering does not match, the workload classification is wrong; re-read the relevant lecture before continuing.

## What to commit

For each exercise, in your portfolio:

- The script (unmodified, or modified with your stretch additions).
- A `notes.md` (5–10 lines) with: (a) your machine spec — `os.cpu_count()`, Python version, OS; (b) the timing table you observed; (c) one sentence on whether the ordering matched the expected; (d) one citation from `Lib/concurrent/futures/*.py` or `Lib/multiprocessing/*.py` related to what surprised you.

These three short artifacts plus the homework writeups are sufficient evidence you have done the work; do not over-produce.
