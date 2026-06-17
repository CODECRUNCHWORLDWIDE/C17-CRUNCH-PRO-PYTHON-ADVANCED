# Challenge 2 — Subinterpreter Pipeline

> Time budget: 2 hours. Equipment: Python 3.13+ (the `interpreters` module is 3.13 and later only). No third-party libraries required.

## The setup

PEP 734 (the accepted form of PEP 554) shipped in Python 3.13 as the `interpreters` standard-library module. The module exposes a Python-level API for creating subinterpreters — independent Python interpreters that share the same OS process but have their own GIL, their own module dict, and their own type system. Two subinterpreters can execute Python bytecode simultaneously on two cores without the pickling tax of multiprocessing.

The API is small. `interpreters.create()` returns an `Interpreter`. `interp.exec(source)` runs a string of Python source in the subinterpreter (on whichever OS thread you call it from; the subinterpreter has its own GIL, not its own thread). `interpreters.Queue()` creates a queue that can pass shareable types (`bytes`, `str`, `int`, `float`, `bool`, `None`, and tuples/lists of these) across subinterpreter boundaries.

This challenge asks you to build a three-stage pipeline using subinterpreters and to benchmark it against the equivalent multiprocessing pipeline.

## The pipeline

```
Stage 1 (input):  generate 1000 strings ("doc_0001", "doc_0002", ...)
Stage 2 (work):   uppercase + reverse + repeat each string 100 times
Stage 3 (output): collect the results and verify the count is 1000
```

Each stage runs in its own subinterpreter. Stage 1 puts strings on `queue_a`. Stage 2 reads from `queue_a`, processes, puts on `queue_b`. Stage 3 reads from `queue_b`, counts, prints the result. This is the canonical "pipeline" pattern; it shows up in stream processing, log aggregation, ETL, and any workflow with a fan-out and a join.

## The task

1. **Read PEP 734** end-to-end. <https://peps.python.org/pep-0734/>. About 4,500 words; 25 minutes.

2. **Implement the subinterpreter pipeline.** Create three subinterpreters. Stage 1 and Stage 3 run in subinterpreters; Stage 2 may run in the main interpreter or in another subinterpreter. Use `interpreters.Queue` to pass data between stages. Use `threading.Thread` to drive the subinterpreters from the main script (each `interp.exec` call is blocking until the subinterpreter finishes).

3. **Implement the multiprocessing equivalent.** Three processes connected by `multiprocessing.Queue`. Same workload, same input count, same output verification.

4. **Benchmark.** Run each implementation 10 times. Record start-up time, wall-clock throughput (strings per second), and total resident memory (use `psutil.Process(pid).memory_info().rss`).

5. **Write the comparison.** A short markdown file with:
    - The two implementations side by side.
    - A table comparing startup time, throughput, peak memory.
    - Three bullet points on the API differences: what was easier in subinterpreters, what was harder, what surprised you.
    - A recommendation for the workload: subinterpreters or multiprocessing, and why.

## Skeleton

```python
"""A starting point for the subinterpreter pipeline.

Fill in the `# TODO` blocks. Run on Python 3.13+ (subinterpreters
are a 3.13 feature).
"""
import interpreters
import threading
from typing import Any

DOC_COUNT = 1000


def stage_1_source() -> str:
    """Source code to run in subinterpreter 1: produce strings."""
    return """
import interpreters
queue_a = interpreters.Queue(qid_a)
for i in range(1000):
    queue_a.put(f"doc_{i:04d}")
queue_a.put(None)  # sentinel
"""


def stage_2_source() -> str:
    """Source code to run in subinterpreter 2: transform strings."""
    return """
# TODO: read from queue_a, transform, write to queue_b, forward sentinel.
"""


def stage_3_source() -> str:
    """Source code to run in subinterpreter 3: count results."""
    return """
# TODO: read from queue_b until sentinel, count, print the count.
"""


def main() -> None:
    queue_a: interpreters.Queue = interpreters.Queue()
    queue_b: interpreters.Queue = interpreters.Queue()
    # TODO: create three subinterpreters, run each on its own thread,
    #       join the threads, verify the output count is DOC_COUNT.
    print("TODO")


if __name__ == "__main__":
    main()
```

The subinterpreter API in 3.13 changed slightly during the PEP 734 finalization. Refer to the current docs at <https://docs.python.org/3/library/interpreters.html> for the canonical signatures; the skeleton above may need small adjustments depending on the exact 3.13.x release you run.

## Deliverable

A folder `challenge-02-results/` in your homework directory with:

- `subinterp_pipeline.py` — your subinterpreter implementation.
- `process_pipeline.py` — your multiprocessing implementation.
- `bench.py` — the benchmark script that runs each 10 times and reports.
- `comparison.md` — the table and the recommendation.

## Grading rubric

- **Both pipelines run correctly and produce 1000 outputs** (40%).
- **Benchmark script measures startup, throughput, and memory; reports a 95% confidence interval** (20%).
- **The comparison.md table compares the two implementations on at least three quantitative axes** (15%).
- **The "what was easier / harder / surprised you" bullets are specific (not generic)** (15%).
- **The recommendation is defended in two sentences with reference to the measured numbers** (10%).

## Hints

- The `interpreters.Queue` is a *cross-interpreter* queue. It is *not* the same object as `queue.Queue` or `multiprocessing.Queue`. Read the docs section on shareable types carefully.
- A subinterpreter does not share `sys.modules` with the main interpreter. Every `import` inside the subinterpreter is fresh; the import system runs again. This is one source of the subinterpreter startup cost (about 10 ms in 3.13).
- You cannot share Python objects across subinterpreters directly. To pass a string, the string must be one of the shareable types — fortunately, strings, bytes, ints, floats, and bools all are.
- Multiprocessing's `Queue` is slower than `interpreters.Queue` for in-process pipelines. The latter does not pickle.
- Use `time.perf_counter()` for wall-clock measurement. Use `psutil.Process(pid).memory_info().rss` for resident memory. Use `psutil.Process(pid).children(recursive=True)` to find child processes if needed.

## What you should take away

Subinterpreters in 3.13 are *new*. The community is still discovering the right patterns. This pipeline is one of the patterns that has emerged as a good fit: stages that pass small data between each other, where the per-stage compute is non-trivial but the per-message overhead matters.

The trade-off you will measure: subinterpreters have lower startup cost than multiprocessing (no process spawn, no module re-import in the child process) and lower per-message cost (no pickling). They have higher startup cost than threads (~10 ms vs ~100 μs) and lower flexibility (only shareable types can cross). For workloads where pickling is a bottleneck and the data is small-typed, subinterpreters are now a real third option that was not available 18 months ago.

In 2026, the right operational stance is: use subinterpreters for *new* problems that fit the shareable-type constraint; do not migrate existing multiprocessing code unless the pickling tax is measurably hurting you.

## References

- **PEP 684** — Per-interpreter GIL (the C-API change). <https://peps.python.org/pep-0684/>. Eric Snow, 2023.
- **PEP 734** — Multiple Interpreters in the Stdlib (the Python-level API). <https://peps.python.org/pep-0734/>. Eric Snow, 2024.
- **`interpreters` docs** — <https://docs.python.org/3/library/interpreters.html>.
- **Eric Snow, "A Per-Interpreter GIL"** (PyCon 2023, ~30 min). Free on YouTube.
- **Anthony Shaw, "Subinterpreters: Python 3.12 and beyond"** (PyCon AU 2023, ~40 min). Free.
- **Real Python — "Python's New Subinterpreter Support"** — <https://realpython.com/python313-subinterpreters/>.
