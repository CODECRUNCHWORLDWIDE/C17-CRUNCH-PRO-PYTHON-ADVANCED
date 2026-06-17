# Week 5 — Exercises

Three short, focused exercises. Each runs in 30–45 minutes. Each isolates one primitive from the lectures and exercises it with a small, deliberate test program.

All three require **Python 3.11 or newer**. Exercise 3 has a feature-detect for `Queue.shutdown()` (3.13+) and falls back to a sentinel on 3.11–3.12.

| # | File | Focus | Time |
|---|------|-------|------|
| 1 | [`exercise-01-taskgroup-with-cancel.py`](./exercise-01-taskgroup-with-cancel.py) | `asyncio.TaskGroup`: cancel-vs-raise, `finally`-block ordering, ExceptionGroup | 45 min |
| 2 | [`exercise-02-timeout-and-shield.py`](./exercise-02-timeout-and-shield.py) | `asyncio.timeout`, nested timeouts, `asyncio.shield`, the `cancelling`/`uncancel` counter | 45 min |
| 3 | [`exercise-03-bounded-queue-fan-out.py`](./exercise-03-bounded-queue-fan-out.py) | `asyncio.Queue(maxsize=K)`, producer/consumer back-pressure, the "slow sink" cascade | 45 min |

## How to do them

Read the lecture for the day before the exercise. Then run the script. Then **read the source**: the comments are the spec. Then answer the reflection questions at the bottom of each file.

The expected-output sections at the bottom of each file are deliberately literal. If your output does not match — by more than ±20 ms in timings — something is wrong with your local asyncio configuration; debug before continuing.

## What to commit

For each exercise, in your portfolio:

- The script (unmodified, or modified with your stretch additions).
- A short `notes.md` (5–10 lines) answering the reflection questions and citing one line of the relevant `Lib/asyncio/*.py` source.

These three short artifacts plus the homework writeups are sufficient evidence you have done the work; do not over-produce.
