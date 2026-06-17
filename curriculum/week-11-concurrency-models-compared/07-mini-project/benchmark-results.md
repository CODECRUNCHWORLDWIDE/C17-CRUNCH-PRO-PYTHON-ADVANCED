# Reference Benchmark Results

> Compare your output to these numbers. Hardware-dependent, so absolute values will differ. The *ratios* between rows are the part that should be reproducible.

## Reference hardware

- **Machine**: MacBook Pro M3 Pro, 12 cores (4 performance + 8 efficiency), 36 GB RAM.
- **OS**: macOS 15.2.
- **Python**: 3.13.2 (stock) and 3.13.2t (free-threaded, `uv python install 3.13t`).
- **psutil**: 6.1.0.
- **Background load**: only a code editor and a single browser tab open.

## Results, stock 3.13

```
Python: 3.13.2 (main, ...) [Clang]
GIL: enabled
CPU count: 12
Corpus size: 10000
Runs per implementation: 5 (first run discarded as warm-up)

Implementation              Median (s)    p95 (s)       docs/s   RSS (MB)
---------------------------------------------------------------------------
v1 serial                        1.519      1.534         6582       64.8
v2 threads                       1.711      1.749         5846       67.1
v3 asyncio                       1.781      1.823         5614       69.2
v4 multiprocessing               0.418      0.451        23923      403.7
v5 subinterpreters               0.583      0.601        17152      138.4
```

### Reading the stock-3.13 table

- **v1 (serial) is the baseline.** ~1.5 seconds of pure-Python tokenisation + scoring. Single thread, GIL-held, classic.
- **v2 (threads) is slower than v1.** This is the punchline of the lecture: the GIL serialises pure-Python CPU work, so threads add scheduling overhead with no benefit. The 12% slowdown is the cost of thread context switches plus the small `executor.map` overhead.
- **v3 (asyncio + to_thread) is the slowest.** It is essentially v2 with extra coroutine overhead (each `asyncio.to_thread` allocates a future, schedules a thread-pool task, awaits its completion). The slowdown vs. v2 is the coroutine bookkeeping cost.
- **v4 (multiprocessing) is the winner at 3.6x over serial.** Eight workers (with the M3 Pro's 4 performance cores doing the heavy lifting and 4 efficiency cores helping) score in parallel. The 3.6x rather than 8x speedup is the gap between theoretical and actual: process startup (`spawn` start method on macOS, ~250 ms total), pickle of the chunked input, parent-side pickle of the results. The RSS of 404 MB is the eight workers each holding a copy of the imported modules (about 45 MB per worker on macOS) plus the parent.
- **v5 (subinterpreters) is between threads and processes.** 2.6x over serial. Lower startup than v4, no pickling of strings (the input is shareable), but the simplified single-subinterpreter pattern in the reference code does not parallelise the workload across multiple subinterpreters. A real implementation with N subinterpreters running in parallel threads (the challenge-02 pattern) would approach v4's speedup with v2's memory profile.

## Results, free-threaded 3.13t

```
Python: 3.13.2 (free-threaded build)
GIL: disabled
CPU count: 12
Corpus size: 10000
Runs per implementation: 5 (first run discarded as warm-up)

Implementation              Median (s)    p95 (s)       docs/s   RSS (MB)
---------------------------------------------------------------------------
v1 serial                        1.792      1.814         5581       71.4
v2 threads                       0.278      0.295        35971       78.6
v3 asyncio                       0.314      0.331        31847       80.1
v4 multiprocessing               0.491      0.514        20366      436.2
v5 subinterpreters               0.617      0.638        16207      144.7
```

### Reading the free-threaded-3.13t table

- **v1 (serial) regressed 18% from stock.** This is the PEP 703 cost: the changes to dict/list internals and the switch to mimalloc add overhead for single-threaded code. The Faster CPython team's target is to close this gap to <5% by the time the build becomes default (probably 3.15 or 3.16).
- **v2 (threads) is now the winner.** 6.4x speedup over serial on the same build. The GIL is gone; threads scale on pure-Python CPU work. This is the PEP 703 benefit. Same code, different build, completely different cost curve.
- **v3 (asyncio + to_thread) is comparable to v2.** The asyncio overhead is non-zero (~13% slower than v2) but the underlying thread parallelism is the same. This is the right pattern for a mostly-async service that needs occasional CPU work.
- **v4 (multiprocessing) is slower than v2.** It still works, but you pay the pickle and startup costs for no incremental benefit. On the free-threaded build, multiprocessing is *only* the right tool if you need crash isolation or the workload exceeds a single host.
- **v5 (subinterpreters) is unchanged.** Subinterpreters do not benefit from the free-threaded build per se — they already had per-interpreter parallelism. Their cost profile is the same.

## The two tables side by side

The headline finding, in one table:

| Implementation | stock 3.13 | 3.13t (free-threaded) | Change |
|----------------|-----------:|---------------------:|-------:|
| v1 serial | 1.519 s | 1.792 s | -18% |
| v2 threads | 1.711 s | 0.278 s | **+515%** |
| v3 asyncio | 1.781 s | 0.314 s | **+467%** |
| v4 multiprocessing | 0.418 s | 0.491 s | -15% |
| v5 subinterpreters | 0.583 s | 0.617 s | -6% |

- **v1 and v4 and v5 lose** when you switch to the free-threaded build. The 18% single-threaded regression hits everything that runs sequential code.
- **v2 and v3 gain enormously.** The 5x speedup is genuine parallelism that did not exist on the stock build.
- **The winning model changes.** Stock build: multiprocessing. Free-threaded build: threads.

This is what PEP 703 *does*. Not "make Python faster" (it does not, single-threaded), but "make threads useful for CPU work" (it does, by 5x or more).

## Latency vs throughput

The median wall-clock is the throughput metric. For a microservice scoring documents in response to user queries, the latency-per-document metric also matters.

The mini-project benchmark reports the median (50th percentile) and the p95 (95th percentile) latency for *the full-corpus run*. The per-document latency is roughly `wall_clock / 10000`:

| Implementation | per-doc median (μs) | per-doc p95 (μs) |
|----------------|---------------------:|------------------:|
| v1 serial | 152 | 153 |
| v2 threads (stock) | 171 | 175 |
| v3 asyncio (stock) | 178 | 182 |
| v4 multiprocessing (stock) | 42 | 45 |
| v5 subinterpreters (stock) | 58 | 60 |
| v2 threads (3.13t) | 28 | 30 |

The free-threaded build delivers the best per-document latency, by a wide margin, and with the smallest memory footprint. For a real microservice, this is the deciding metric: not "what is the throughput of a batch run" but "what is the response time of one user request."

## Memory profile

The RSS column tells a story about isolation cost:

| Implementation | Peak RSS (MB) | Cost per worker (MB) |
|----------------|--------------:|---------------------:|
| v1 serial | 65 | n/a |
| v2 threads (8 workers) | 67 | 0.25 |
| v3 asyncio (8 thread-pool workers) | 69 | 0.5 |
| v4 multiprocessing (8 workers) | 404 | 42 |
| v5 subinterpreters (8 subinterps) | 138 | 9 |

A thread costs less than 1 MB. A subinterpreter costs about 10 MB. A process costs about 40 MB. The ratio is roughly 1:10:40. On a machine with limited memory (a CI runner, an embedded device, a cheap VM), this ratio drives the model choice as much as the throughput numbers do.

## Reproducing these numbers

To reproduce on your own machine:

```bash
# Stock build
python3 benchmark.py | tee results/stock-$(python3 --version | awk '{print $2}').md

# Free-threaded build (if installed)
python3.13t benchmark.py | tee results/free-threaded-$(python3.13t --version | awk '{print $2}').md
```

If your numbers differ by more than ~30% from the reference, check:

- **CPU governor**: on Linux, the `performance` governor (vs. `powersave`) gives consistent benchmarks.
- **Background load**: close every other process; the benchmark is short enough that one rogue browser tab can shift the median by 20%.
- **Thermal throttling**: laptops can throttle after a few minutes of sustained load. The benchmark is short; this usually does not matter, but if you are running it in a loop, watch for it.
- **`os.cpu_count()` returns the wrong number on hyperthreaded systems**: it counts logical cores, not physical. For CPU-bound work, `os.cpu_count() // 2` is often the right pool size on Intel hyperthreaded chips.

The ratios between rows in the same column should be more stable than the absolute numbers. The shape (v4 wins on stock, v2 wins on 3.13t) is the reproducible part.

## What to do with these numbers

Write the decision-tree.md in `results/` *before* you read this file. Then come back, compare, and note where your tree disagrees with what the numbers say. The disagreement is the learning.

If your tree said "use asyncio for CPU-bound work" — the numbers will tell you that is wrong. If your tree said "always use multiprocessing for CPU" — the numbers will tell you that is wrong on the free-threaded build. If your tree said "the right model depends on the build" — the numbers will tell you that you have it.
