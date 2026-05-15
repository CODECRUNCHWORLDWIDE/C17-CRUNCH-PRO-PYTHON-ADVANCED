# Week 11 — Exercise Solutions

Read this after attempting each exercise. The numerical values below are reference outputs from an 8-core 2025-class laptop; your numbers will differ by 10–40% depending on hardware, CPU governor, and whether you have a free-threaded build installed. The *shape* of every table — which column wins, which loses — is the part you should match.

## Exercise 1 — Threads vs Asyncio

### Expected output, stock 3.13, 8-core machine

```
Workload A: SHA-256 of 1 MB buffer x 64 (GIL released by hashlib)
  serial                            245.32 ms
  threads(8)                         35.81 ms
  speedup: threads/serial = 6.85x

Workload B: pure-Python sum-of-squares x 64 (GIL held)
  serial                            148.71 ms
  threads(8)                        152.46 ms
  speedup: threads/serial = 0.98x (expect ~1.0 on stock 3.13)

Workload C: time.sleep(0.01) x 64 (GIL released; I/O-shaped)
  serial                            713.04 ms
  threads(8)                         92.18 ms
  asyncio.gather                     93.55 ms
  speedup: threads/serial = 7.73x, asyncio/serial = 7.62x
```

### Reasoning

- **Workload A** (SHA-256, 1 MB buffer): hashlib calls `Py_BEGIN_ALLOW_THREADS` for buffers ≥ 2,047 bytes. Eight threads execute the SHA-256 C code in parallel on eight cores. The speedup is bounded by `min(buffer_count, cpu_count)` and by the small per-task Python overhead. ~7x is the expected number on 8 cores.
- **Workload B** (pure-Python sum-of-squares): every `LOAD_FAST`, `BINARY_ADD`, `STORE_FAST` runs with the GIL held. Threads still alternate at the switch interval (5 ms), but the work is serialised at the bytecode level. The "speedup" is actually a small slowdown because thread switching has overhead with zero benefit. On the **free-threaded build**, this column jumps to ~6-7x — that is the PEP 703 demonstration.
- **Workload C** (`time.sleep` / `asyncio.sleep`): blocking sleep releases the GIL inside `time.sleep`. Threads sleep concurrently; asyncio runs the sleep callbacks on a heap-ordered queue. Both achieve roughly `min(task_count, cpu_count_or_pool_size)` speedup. Asyncio is comparable to threads at this scale; asyncio pulls ahead at scale ~1000+ tasks because its per-task overhead is ~50x lower.

### Common mistakes

1. Wrapping `pure_cpu_one` inside `async def` without an `await` and expecting parallelism. This is the classic blocked-loop bug; the coroutine runs serially because there is no yield point.
2. Calling `asyncio.run` inside a thread pool worker. Each thread would have its own loop, the global event loop reference would clash; the API does not support nesting this way.
3. Using `executor.submit` and never calling `.result()`. Exceptions in workers are silently swallowed until you touch the future.

## Exercise 2 — GIL release audit

### Expected output, stock 3.13

```
Candidate                       Result
---------------------------------------------------------------------------
  sha256(1MB)                    serial= 245.31ms  threads(8)=  35.78ms  speedup= 6.85x  RELEASES
  sha256(256B)                   serial=   0.97ms  threads(8)=   1.42ms  speedup= 0.68x  HOLDS
  zlib.compress(1MB)             serial= 612.45ms  threads(8)=  88.12ms  speedup= 6.95x  RELEASES
  json.loads(64KB)               serial=  68.13ms  threads(8)=  67.92ms  speedup= 1.00x  HOLDS
  re.search(64KB)                serial=   3.84ms  threads(8)=   3.91ms  speedup= 0.98x  HOLDS
  time.sleep(0.01)               serial= 320.17ms  threads(8)=  41.02ms  speedup= 7.81x  RELEASES
  pure Python sum(100k)          serial= 154.78ms  threads(8)= 159.32ms  speedup= 0.97x  HOLDS
```

### Reasoning

- **`hashlib.sha256(1 MB)`** RELEASES: the C source explicitly calls `Py_BEGIN_ALLOW_THREADS` once the buffer exceeds 2,047 bytes (the `HASHLIB_GIL_MINSIZE` constant in `Modules/hashlib.h`). Below the threshold, the per-call cost of releasing/re-acquiring the GIL would dominate; above it, the C SHA implementation parallelises cleanly.
- **`hashlib.sha256(256 B)`** HOLDS: below the threshold; the GIL is kept. The threshold is a tunable constant that has changed over CPython versions; in 3.13 it is 2,047 bytes.
- **`zlib.compress`** RELEASES: same pattern — large enough buffer triggers the GIL release.
- **`json.loads`** HOLDS: the json module is C-accelerated but the C code holds the GIL throughout. Parsing 1 MB of JSON in 4 threads takes the same wall-clock as parsing in 1 thread.
- **`re.search`** HOLDS: the `re` module's C-level regex engine does not release the GIL. The `regex` third-party library (a more modern fork) does release the GIL for long searches; `re` does not.
- **`time.sleep`** RELEASES: every blocking syscall releases the GIL. `time.sleep` is implemented via `nanosleep`/`Sleep` and the wrapper drops the GIL.
- **Pure-Python sum** HOLDS: every bytecode runs with the GIL held. This is the canonical "the GIL blocks Python-level parallelism" case.

### What this proves

The set of C modules that release the GIL is *small* and *deliberate*. Module authors must opt in with `Py_BEGIN_ALLOW_THREADS`. The default is "the GIL stays held," because dropping and re-acquiring is not free. Modules that release the GIL are the ones where the per-call work is heavy enough to amortise the overhead.

The implication for design: if you have a CPU-heavy workload, do not assume that wrapping it in `ThreadPoolExecutor` will parallelise. Verify, with a benchmark like this, that the inner C calls release the GIL. If they do not — and on the stock build, most do not — multiprocessing or the free-threaded build is the right answer.

## Exercise 3 — Multiprocessing pickle tax

### Expected output, stock 3.13, 8-core

```
Shape A: scalar int  (tiny pickle, tiny compute)
  Shape A: compute=   1.2ms  pickle_total=    3.1ms  process(8)=  342.5ms  pickle %=  0.9%

Shape B: 1 MB bytes  (medium pickle, medium compute)
  Shape B: compute= 273.4ms  pickle_total=  163.8ms  process(8)=  102.5ms  pickle %=159.8%

Shape C: 10k-dict list  (heavy pickle, medium compute)
  Shape C: compute=  70.6ms  pickle_total=  321.2ms  process(8)=  462.8ms  pickle %= 69.4%
```

### Reasoning

- **Shape A** (scalar int): the workload is so small that ProcessPoolExecutor startup (~250 ms on macOS `spawn`, ~50 ms on Linux `forkserver`) dwarfs the actual compute. The pickle tax is negligible in absolute terms; the *startup tax* is what dominates this row. ProcessPoolExecutor is slower than serial.
- **Shape B** (1 MB bytes): the SHA-256 work scales linearly across 8 cores. The pickle tax (1 MB bytes serialise at ~1.5 ms each way, ~3 ms round-trip × 64 = ~190 ms total) is paid in series on the parent's pickling, but the compute (~4.3 ms × 64 = 275 ms serial; ~35 ms × 8 = ~35 ms in parallel + parent pickle = ~100 ms total) dominates and we win. Note the `pickle %` reading "159.8%": the pickle work is paid in series on a single thread while compute is parallel, so the *total* pickle CPU exceeds the wall-clock process time. The metric counts pickle CPU, not pickle wall time.
- **Shape C** (10k-dict list): each list of 10,000 dicts pickles at ~2.5 ms each way, ~5 ms round-trip × 64 = ~320 ms of pickle CPU. The compute is small (~1 ms each). The pickle tax dominates and ProcessPoolExecutor is *slower than serial* on this shape. This is the canonical "the pickling tax killed us" result.

### Fixes for shape C

- **Bigger chunks**: pass `chunksize=8` to `executor.map`. Amortises the pickle overhead across 8 tasks.
- **Shared memory**: if the dicts are homogeneous (same keys, primitive values), encode them as a NumPy structured array, share via `multiprocessing.shared_memory`, pass only the name.
- **Switch to threads + free-threaded build**: if the workload is genuinely CPU-bound and the data is large, the free-threaded build gives you parallelism without pickling.
- **Switch to subinterpreters**: shareable types include `int`, `float`, `str`, `bytes`, `tuple`. A list of dicts of strings can be flattened into shareable form.

## Exercise 4 — Blocked event loop

### Expected output, stock 3.13

```
Task count: 10  Slow duration per task: 100ms
Expected serial wall time: 1000ms

Bug variants (expected ~serial because the loop is blocked):
  bad_a (time.sleep inside coroutine)  elapsed= 1003.4ms  parallelism=1.00x  (BLOCKED LOOP)
  bad_b (blocking I/O inside coroutine) elapsed= 1004.1ms  parallelism=1.00x  (BLOCKED LOOP)
  bad_c (CPU loop inside coroutine)     elapsed= 1058.7ms  parallelism=0.94x  (BLOCKED LOOP)

Fix variants (expected ~parallel: 5-10x speedup over serial):
  good_a (await asyncio.sleep)          elapsed=  101.2ms  parallelism=9.88x  (parallel)
  good_b (await asyncio.to_thread)      elapsed=  104.8ms  parallelism=9.54x  (parallel)
  good_c (loop.run_in_executor + thread pool) elapsed=  142.5ms  parallelism=7.02x  (parallel)
```

### Reasoning

The bad variants all share the same shape: a coroutine that runs from start to finish without a single `await`. The event loop sees one runnable task and runs it; the other nine tasks sit on the ready queue and wait. `asyncio.TaskGroup` does not magically parallelise sync code — it schedules coroutines and runs them one at a time on the loop.

- **bad_a** is the textbook example. `time.sleep` is a sync syscall; the loop has no way to know it should reschedule.
- **bad_b** is the real-world example. `requests.get`, `socket.recv` without a timeout, `open()` on a slow disk — anything that blocks the kernel. The loop sees a task running and waits.
- **bad_c** is the silent example. There is no syscall at all; just a tight Python loop holding the GIL and doing CPU work. The loop has no idea anything is happening.

The fixes:

- **good_a**: `await asyncio.sleep(...)` registers a timer with the loop and yields. The loop wakes up the task when the timer fires. This is the right pattern when you can replace the blocking call with an async-aware one.
- **good_b**: `await asyncio.to_thread(blocking_fn)` runs the sync function in the default thread pool (managed by the loop). The coroutine yields while the thread runs; the loop schedules other coroutines. This is the right pattern when you have an unavoidable blocking call (the `requests` library, a C extension that does not release the GIL).
- **good_c**: `await loop.run_in_executor(executor, cpu_fn)` is the explicit form. Use a custom executor when you want control over the pool size or thread naming. On the stock build, the speedup is limited by the GIL (if the work is pure Python); on the free-threaded build, you get true parallelism.

### Diagnostic flag

```python
asyncio.run(main(), debug=True)
# or
PYTHONASYNCIODEBUG=1 python3 program.py
```

With debug mode on, the loop logs `Executing <Task ...> took N.NN seconds` for any callback exceeding 100 ms. Turn this on whenever a service "feels" slow but no specific call is.

### What `asyncio.TaskGroup` adds (PEP 654)

In the fix variants, we used `async with asyncio.TaskGroup() as tg: ...`. This is the structured-concurrency primitive added in 3.11. The semantics:

1. Every `tg.create_task(coro)` schedules a task that is *owned* by the group.
2. When the `async with` block exits, the group waits for all tasks to complete.
3. If any task raises, the group cancels all sibling tasks (sending them `CancelledError`) and waits for them to finish before re-raising the exception as an `ExceptionGroup`.

The old pattern (`await asyncio.gather(*tasks)`) does not cancel siblings on failure by default — the surviving tasks keep running and you discover the failure only via the gather return value. `TaskGroup` makes the failure mode explicit and the cleanup automatic. In 2026, prefer `TaskGroup` for any new asyncio code that fans out work.

## Cross-cutting reflection: where the numbers diverge across machines

The reference outputs above were captured on an 8-core machine with stock 3.13. Three common reasons your numbers will diverge:

1. **CPU count and topology.** A 16-core machine will show larger speedups on workloads A and C (more parallelism available). A 4-core machine will cap the threading and multiprocessing speedups around 4x. The `os.cpu_count()` value reports logical cores, which on Intel hyperthreaded chips is 2x physical; for CPU-bound work, the right pool size is often `physical_cores` rather than `logical_cores`. On macOS Apple Silicon, the `cpu_count()` is the total of performance + efficiency cores; the efficiency cores are useful but slower, and the throughput-per-worker on them is about half that of performance cores.

2. **Thermal throttling.** Run the benchmark twice back-to-back. If the second run is 10–20% slower, the CPU throttled. The benchmark is short enough that one run does not throttle a desktop, but laptops in sustained load can. The benchmark in this exercise does five iterations and throws out the first; on a laptop with aggressive thermal management, you may want to space the runs out with a sleep or use a stand with a cooling pad.

3. **Power state and OS scheduler load.** On Linux, the `performance` governor gives consistent benchmarks; the `powersave` and `ondemand` governors will scale the CPU frequency mid-run, producing noisy numbers. On Windows, the High Performance power plan is the equivalent. The simplest check: run the benchmark twice and look at the spread. If the difference between runs is more than ~5%, the system is too noisy for meaningful single-run comparison.

The advice for trustworthy numbers: run each benchmark at least 5 times, throw out the first (cache warming, JIT effects in some interpreters), use the median rather than the mean, and report the median rather than a single number. The `bench_one` helper in `mini-project/benchmark.py` does this. The exercises here use a single-run timing for simplicity, but in any actual decision-making context, you should always have a spread.

## How the four exercises connect to the mini-project

Exercise 1 demonstrates the *headline finding* of the week: each model has a workload shape that wins it and a workload shape that loses it. The four-by-three table is the artefact.

Exercise 2 demonstrates *why* the table looks the way it does on the stock build: the GIL is a binary "held" or "released" gate, and a small set of C functions choose to release it. If you have not done Exercise 2 yet, the rest of the week's content is built on a foundation you do not have.

Exercise 3 demonstrates the *cost model* of multiprocessing. The pickling tax is not an abstract concept; it is a measurable percentage of wall-clock time. Most of the "ProcessPoolExecutor is slower than I expected" stories on Stack Overflow trace to a misunderstanding of this percentage. Once you can compute it, the surprises stop.

Exercise 4 demonstrates the *most common asyncio failure mode*. Reading about "do not block the event loop" does not produce the same kind of memory as reproducing the failure on your own laptop and watching the parallelism number stay stuck at 1.0x. The exercise is short on purpose: the lesson is in the *shape* of the bug, not in any clever solution.

The mini-project (`mini-project/benchmark.py`) is the synthesis: same workload, five implementations, three metrics, two builds. The decision tree in `mini-project/decision-tree.md` is the reference; the decision tree you write in `mini-project/results/decision-tree.md` is your own. Compare both. The disagreement is the learning.
