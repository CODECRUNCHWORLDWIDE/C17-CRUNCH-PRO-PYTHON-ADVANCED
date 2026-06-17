# Week 6 — Challenges

One stretch challenge this week. The mini-project (the three-workload benchmark with a full memo) is the main deliverable; the challenge is a single-sitting compressed version you finish on Wednesday or Thursday before the multi-day project.

1. **[Three implementations of the same workload, in three hours](./challenge-01-3-implementations-of-same-workload.md)** — pick one workload (the challenge defines a CPU-bound image-blur kernel by default) and implement it three ways: `multiprocessing` (or `ProcessPoolExecutor`), `asyncio` (with `run_in_executor` for the CPU phase), and `ThreadPoolExecutor`. Produce one comparison table and a short paragraph defending which one you would ship. ~3 hours. The "muscle build" for the mini-project. Lower scope (one workload instead of three; no free-threaded variant required; no memo polish) but high density.

If you finish early, port the implementation to use `joblib.Parallel(n_jobs=N, backend="loky")` and add it to the comparison table. The relevant diff against `ProcessPoolExecutor` is illuminating: warm-pool reuse, `cloudpickle` for closures, automatic memmap for large NumPy inputs.
