# Mini-Project — The Five-Way Document Scorer

> Build the same workload five times. Measure. Decide. The deliverable for this week is not the code (you will write less than 500 lines); the deliverable is the *table* and the *decision tree* — the artefacts you can hand to a teammate.

## The workload

A relevance-ranking microservice. The input is a corpus of 10,000 short documents, generated synthetically (the `generate_corpus.py` helper produces them; you do not need to download anything). The query is fixed at module load. The work, per document, is two steps:

1. **Tokenise** the body: regex-split on whitespace, lowercase, strip stopwords. About 100 μs per document on a 2025-class laptop.
2. **Score** the body against the query: count query-term occurrences, compute a normalised score. About 50 μs per document.

The total CPU work is roughly 1.5 seconds when scored serially. Small enough to iterate quickly; large enough to dwarf scheduler overhead in the parallel variants.

## What you build

```
mini-project/
├── README.md                  # this file
├── decision-tree.md           # reference decision tree (read after attempting yours)
├── benchmark.py               # the five-way benchmark
├── scorer/                    # the five implementations
│   ├── __init__.py
│   ├── common.py              # shared tokenisation, scoring, corpus
│   ├── v1_serial.py           # baseline
│   ├── v2_threads.py          # ThreadPoolExecutor
│   ├── v3_asyncio.py          # asyncio.gather (+ asyncio.to_thread)
│   ├── v4_multiprocessing.py  # ProcessPoolExecutor
│   └── v5_subinterpreters.py  # interpreters (3.13+ only; skipped on older)
└── results/
    ├── stock-3.13.md          # benchmark output on stock build
    ├── free-threaded-3.13.md  # benchmark output on 3.13t (if installed)
    └── decision-tree.md       # your decision tree, written before reading the reference
```

The five `scorer/v*.py` files implement the same public function: `score_corpus(corpus, query) -> list[tuple[str, float]]`. The benchmark imports them and times each one with `time.perf_counter`, `tracemalloc`, and `psutil.Process.memory_info()`.

## The acceptance test

Before benchmarking, verify that all five implementations produce the *same* output. The order of the result list may differ (sorting by score is a separate concern), but the set of `(doc_id, score)` pairs must be equal across all five.

```python
from scorer import v1_serial, v2_threads, v3_asyncio, v4_multiprocessing
expected = set(v1_serial.score_corpus(corpus, query))
assert set(v2_threads.score_corpus(corpus, query)) == expected
assert set(v3_asyncio.score_corpus(corpus, query)) == expected
assert set(v4_multiprocessing.score_corpus(corpus, query)) == expected
```

If any implementation disagrees with the serial baseline, the implementation is wrong; fix it before measuring.

## Implementing each version

### v1 — serial

The simplest. A `for` loop. About 15 lines including imports. The baseline; do not optimise.

### v2 — threads (ThreadPoolExecutor)

`concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count())`. Pass the per-document scorer as the callable, the list of documents as the iterable.

Expected on stock 3.13: slower than serial. The work is pure-Python CPU; the GIL serialises it. You will measure this and record it as the canonical "threads do not parallelise Python CPU work on the stock build" datapoint.

Expected on 3.13t: linear speedup with cores. Same code, different build. This is the PEP 703 demonstration.

### v3 — asyncio

The CPU work is sync. To run it under asyncio, wrap each per-document call in `asyncio.to_thread`. The fanout becomes:

```python
async def score_corpus_async(corpus, query):
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(asyncio.to_thread(score_one, doc, query))
                 for doc in corpus]
    return [t.result() for t in tasks]
```

Expected on stock 3.13: comparable to v2 (both use the same default thread pool under the hood). Slightly slower than v2 due to coroutine overhead.

The point of v3 is *not* to win the CPU benchmark — asyncio cannot parallelise CPU on the stock build. The point is to demonstrate the correct *pattern* for "I have a mostly-async service that occasionally needs to do CPU work." The `asyncio.to_thread` escape hatch is the right answer in 2026.

### v4 — multiprocessing (ProcessPoolExecutor)

`concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count())`. Same `executor.map` shape as v2.

Set the start method explicitly at module top, inside `if __name__ == "__main__":`:

```python
import multiprocessing
multiprocessing.set_start_method("spawn", force=True)
```

Use `chunksize=125` or so for the 10,000-document corpus across 8 workers — that gives each worker about 1,250 documents per chunk, amortising the per-task pickle overhead.

Expected: 4-6x speedup over serial. Not the theoretical 8x because of (a) startup cost (50-300 ms on `spawn`), (b) pickle tax on input and output, (c) the parent thread doing the pickle work in series. Measure all three.

### v5 — subinterpreters (3.13+ only)

The `interpreters` module is the new stdlib API. The skeleton:

```python
import interpreters
import threading

def score_corpus_subint(corpus, query):
    n_workers = os.cpu_count() or 4
    chunks = chunk_into(corpus, n_workers)
    results_queue = interpreters.Queue()
    threads = []
    for chunk in chunks:
        interp = interpreters.create()
        t = threading.Thread(target=run_worker,
                             args=(interp, chunk, query, results_queue))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    # Drain the queue.
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    return results
```

You will need to serialise the corpus chunks into shareable types. The simplest path: pass a list of tuples `(doc_id, body_string)` — both `str` and `tuple` are shareable. Inside the subinterpreter, deserialise and run the scorer.

Skip v5 cleanly on Python < 3.13 with a `try: import interpreters except ImportError:` guard.

## The benchmark

`benchmark.py` runs each version 5 times, throws out the first run (warm-up), and reports median, p95, and p99 latency, throughput in docs/sec, and peak RSS via `psutil`.

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time, tracemalloc, psutil, os, statistics
from scorer.common import load_corpus
from scorer import v1_serial, v2_threads, v3_asyncio, v4_multiprocessing

def bench_one(name, fn, corpus, query, runs=5):
    times = []
    proc = psutil.Process(os.getpid())
    for _ in range(runs):
        start = time.perf_counter()
        fn(corpus, query)
        times.append(time.perf_counter() - start)
    # Throw out the warm-up run.
    times = times[1:]
    return {
        "name": name,
        "median_s": statistics.median(times),
        "p95_s": sorted(times)[int(0.95 * len(times))],
        "throughput": len(corpus) / statistics.median(times),
        "rss_mb": proc.memory_info().rss / (1024 * 1024),
    }
```

Run it. Capture the output. Save to `results/stock-3.13.md`. If you have the free-threaded build installed, run it again with `python3.13t benchmark.py` and save to `results/free-threaded-3.13.md`.

## The decision tree

After you have the numbers, write `results/decision-tree.md` *before* reading `decision-tree.md` (the reference). Your decision tree must answer:

- For a 10,000-document scorer like this one, which model wins on stock 3.13?
- Which wins on 3.13t?
- If the corpus grew to 1,000,000 documents (100x), which model would scale best?
- If the per-document work was *I/O* (HTTP lookup) instead of CPU (tokenise + score), which model would win?
- If the per-document work was 10x heavier (1 ms tokenise + 0.5 ms score), would the answer change?

Two to three sentences per question. After writing yours, read the reference and note where you disagreed and why.

## The expected results

The reference numbers from an 8-core 2025-class laptop, stock 3.13, no other load:

| Implementation | Median wall-clock | Throughput | Peak RSS |
|----------------|------------------:|-----------:|---------:|
| v1 serial | 1.52 s | 6,580 docs/s | 65 MB |
| v2 threads | 1.71 s | 5,850 docs/s | 68 MB |
| v3 asyncio | 1.78 s | 5,620 docs/s | 70 MB |
| v4 multiprocessing | 0.42 s | 23,800 docs/s | 410 MB (8 workers × ~45 MB each + parent) |
| v5 subinterpreters | 0.58 s | 17,200 docs/s | 140 MB (8 subinterps × ~9 MB each + parent) |

On the free-threaded build 3.13t:

| Implementation | Median wall-clock | Throughput | Peak RSS |
|----------------|------------------:|-----------:|---------:|
| v1 serial | 1.78 s (regression) | 5,620 docs/s | 72 MB |
| v2 threads | 0.28 s | 35,700 docs/s | 78 MB |
| v3 asyncio | 0.31 s | 32,300 docs/s | 80 MB |
| v4 multiprocessing | 0.49 s | 20,400 docs/s | 440 MB |
| v5 subinterpreters | 0.62 s | 16,100 docs/s | 145 MB |

The two takeaways:

1. **On stock 3.13, multiprocessing wins for CPU-bound work.** Threads and asyncio are essentially the serial baseline plus overhead. Subinterpreters sit between threads and processes on every axis.
2. **On 3.13t, threads win.** Same code, no pickling, no process startup, no separate workers — just threads scaling on a CPU workload that finally parallelises. Multiprocessing is now *slower* than threads because it still pays the pickle and startup costs without any benefit.

The 25% single-threaded regression in v1 between stock and 3.13t is the PEP 703 cost. The 4x improvement in v2 is the PEP 703 benefit. Whether the tradeoff is worth it for your service is a per-service question.

## Grading rubric

- **All five implementations produce identical outputs to v1** (20%).
- **Benchmark runs cleanly on stock 3.13 and produces a results file** (15%).
- **Benchmark runs cleanly on 3.13t (if installed) or skips v5 gracefully on <3.13** (15%).
- **Your decision-tree.md answers all five questions** (20%).
- **You compared your decision tree to the reference and noted any disagreements** (10%).
- **Code is clean: type hints on every function, no top-level state, `if __name__ == "__main__":` guards in v4** (20%).

## What you should take away

Five implementations of the same workload. Five different cost profiles. The benchmark itself is straightforward; the engineering content is the *reading* of the numbers and the *transfer* of that reading to a different workload. This is the skill that this week is built around: looking at a workload, picking the right model, and being able to defend the pick with measurement.

The two skills in tension this week: **measurement** (run it, do not speculate) and **modelling** (predict before measuring, so you can recognise when the measurement is surprising). Both are necessary; either alone is incomplete. The senior engineering judgement is when one outranks the other for a given decision.

## References

- **PEP 703** — Free-threaded build. <https://peps.python.org/pep-0703/>.
- **PEP 684 / PEP 734** — Subinterpreters. <https://peps.python.org/pep-0684/>, <https://peps.python.org/pep-0734/>.
- **PEP 3148** — `concurrent.futures`. <https://peps.python.org/pep-3148/>.
- **PEP 654** — `asyncio.TaskGroup` and `ExceptionGroup`. <https://peps.python.org/pep-0654/>.
- **The Python docs** for `threading`, `asyncio`, `multiprocessing`, `concurrent.futures`, and `interpreters`.
- **Sam Gross, "Per-Interpreter GIL and Beyond"** (PyCon 2023, ~30 min). The reference talk.
