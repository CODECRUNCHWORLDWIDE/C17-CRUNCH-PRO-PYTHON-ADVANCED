# Week 5 — Challenges

One stretch challenge this week. The mini-project (the full crawler) is the main deliverable; the challenge is a small, time-boxed version you build in one Thursday sitting before the multi-day project.

1. **[Async crawler with cancellation, in 3 hours](./challenge-01-async-crawler-with-cancellation.md)** — a single-file crawler skeleton (~250 lines) that exercises every primitive from the week's lectures: `TaskGroup`, `asyncio.timeout`, `shield`, `Queue(maxsize=...)`, `Semaphore`, structured shutdown on `KeyboardInterrupt`. Lower-scope than the mini-project (no robots.txt, no real network — runs against a local test server fixture), but high-density. The "muscle build" for the mini-project. (~3 hours)

If you finish early, port the challenge's structure on top of `anyio` (you will need `pip install anyio aiohttp`). The diff against the asyncio version is illuminating: `anyio.create_task_group()` instead of `asyncio.TaskGroup()`, `anyio.fail_after(s)` instead of `asyncio.timeout(s)`, `anyio.CancelScope` instead of `asyncio.shield`. The structured-concurrency vocabulary is shared; the surface details differ.
