# Decision Tree — Python Concurrency in 2026

> Read this *after* you have written your own decision tree. Compare. Note disagreements. The reference is not the final word; it is a record of one set of trade-offs that a senior engineer might prioritise. Your tree may rank the same trade-offs differently and be just as defensible.

## The tree

```
START: Describe the workload in one sentence.

  ├─ Q1. Is the workload primarily I/O-bound?
  │       (e.g., HTTP calls, database queries, file reads, network sockets)
  │
  │     YES → continue to Q2.
  │     NO  → jump to Q4.
  │
  ├─ Q2. How many concurrent tasks do you need to support?
  │
  │     < 100   → ThreadPoolExecutor. Simpler debugging, lower cognitive load.
  │              The 100-task threshold is approximate; choose the lower
  │              number if your team has more experience with threads.
  │
  │     100 - 1,000   → ThreadPoolExecutor still works, asyncio is also fine.
  │                     Pick by team preference and library availability.
  │
  │     > 1,000  → asyncio. Per-task memory overhead is ~100x lower than
  │              threads. Threads at this scale exhaust file descriptors
  │              and stack memory; asyncio scales to 10,000+ in-flight
  │              tasks on a single process.
  │
  ├─ Q3. Is there ALSO a small amount of CPU-bound work mixed in?
  │       (e.g., parsing JSON responses, computing a hash)
  │
  │     If using threads     → already fine; GIL releases on the I/O,
  │                            and the small CPU work serialises briefly.
  │
  │     If using asyncio     → wrap the CPU work in asyncio.to_thread
  │                            or loop.run_in_executor with a thread pool.
  │                            Never run sync CPU work directly inside an
  │                            async coroutine; you will block the loop.
  │
  │   END for I/O-bound branch.
  │
  ├─ Q4. The workload is CPU-bound. Is the heavy work a C-extension call
  │       that releases the GIL? (NumPy ufuncs, hashlib on large buffers,
  │       zlib, lzma, cryptography library.)
  │
  │     YES → ThreadPoolExecutor on stock 3.13. The C extension drops
  │           the GIL inside its work; threads parallelise on cores.
  │           Pool size = os.cpu_count(). This is the easy case.
  │
  │     NO (work is pure Python) → continue to Q5.
  │
  ├─ Q5. Are you on the free-threaded build (Python 3.13t or later)?
  │
  │     YES → ThreadPoolExecutor. The free-threaded build removes the GIL
  │           for pure-Python CPU work. Threads scale on cores. This is
  │           the simplest, lowest-overhead option.
  │
  │     NO  → continue to Q6.
  │
  ├─ Q6. How large is the per-task data argument?
  │
  │     Small (< 1 KB per task)   → ProcessPoolExecutor. The pickling tax
  │                                 is negligible; the parallelism gain
  │                                 dominates. Use chunksize tuning to
  │                                 amortise startup cost.
  │
  │     Medium (1 KB – 1 MB)       → ProcessPoolExecutor with chunksize
  │                                  set so that each chunk contains
  │                                  > 100 ms of compute work. This keeps
  │                                  pickle overhead < 10% of wall-clock.
  │
  │     Large (> 1 MB per task)    → continue to Q7.
  │
  ├─ Q7. Can the per-task data be represented as a fixed-shape buffer
  │       (a NumPy array, a bytes buffer, a struct)?
  │
  │     YES → ProcessPoolExecutor + multiprocessing.shared_memory.
  │           Allocate the buffer once in the parent; pass only the name
  │           to each worker. Workers attach to the existing buffer; no
  │           pickle of the data itself. This is the production pattern
  │           for "share a giant NumPy array across multiprocessing workers."
  │
  │     NO (the data is an arbitrary Python object graph) → continue to Q8.
  │
  ├─ Q8. Is the data shareable across subinterpreters?
  │       (bytes, str, int, float, bool, None, tuples/lists of these)
  │
  │     YES → interpreters.Queue (PEP 734). Lower startup cost than
  │           multiprocessing, no pickling on bytes/strings, real
  │           parallelism due to per-interpreter GIL. New in 3.13;
  │           verify your C extensions are subinterpreter-safe.
  │
  │     NO  → You are out of standard options on the stock build.
  │           Options:
  │             - Switch to free-threaded build (loop back to Q5).
  │             - Use joblib + cloudpickle for the closure/lambda case.
  │             - Use a third-party distributed framework (ray, dask).
  │             - Restructure the workload to fit one of the boxes above.
```

## The flowchart compressed to a table

If you do not have time to walk the tree, the same information as a table indexed by (I/O vs CPU) × (data size) × (build):

|                              | Stock 3.13 | Free-threaded 3.13t |
|------------------------------|------------|---------------------|
| I/O, small concurrency        | threads | threads |
| I/O, large concurrency        | asyncio | asyncio |
| CPU, C-ext that releases GIL  | threads | threads |
| CPU, pure-Python, small data  | multiprocessing | threads |
| CPU, pure-Python, large data, fixed shape | multiprocessing + shared_memory | threads |
| CPU, pure-Python, large data, arbitrary | subinterpreters or multiprocessing+cloudpickle | threads |
| Mixed I/O and CPU             | asyncio + asyncio.to_thread | asyncio + asyncio.to_thread |

## Six concrete workloads

### 1. HTTP API fanout: 5,000 concurrent requests to a vendor

**I/O-bound, large concurrency.** asyncio with `httpx.AsyncClient`. Use a semaphore to cap concurrency to whatever the vendor allows (often 100–500). On both stock and free-threaded builds, asyncio is the right tool.

### 2. Image processing: resize 10,000 PNGs with Pillow

**CPU-bound, C-extension that releases the GIL.** Pillow's image operations release the GIL. `ThreadPoolExecutor(os.cpu_count())`. The same code works on both stock and free-threaded builds. On the free-threaded build, the speedup is identical (you were already parallelising at the C level).

### 3. Parse 50 GB of log files line by line

**Mixed I/O and CPU.** The disk read is I/O-bound; the per-line parsing is CPU-bound. asyncio is heavy here because the I/O pattern is sequential streaming, not concurrent fanout. The right model is a single thread reading the file, a `ProcessPoolExecutor` parsing chunks. On the free-threaded build, replace the process pool with a thread pool.

### 4. Run 200 Selenium scrapers in parallel

**I/O-bound, but each "task" is actually a subprocess running a browser.** The Python concurrency model is irrelevant for the parallelism — Selenium spawns a separate browser process per session, and the OS parallelises. Use asyncio if you want to coordinate the 200 sessions on a single event loop, threads if you want one Python thread per browser. Either works.

### 5. Train a small ML model on a CPU-only laptop

**CPU-bound, C-extension heavy (NumPy, scikit-learn).** Internal BLAS calls in NumPy and scikit-learn already use multiple threads via OpenMP / MKL. Adding Python-level concurrency on top often hurts (oversubscription: more threads than cores). The right answer is "do not concurrify; let the C library do it." If you need to train multiple models in parallel (hyperparameter search), use `ProcessPoolExecutor` so each model gets its own thread budget.

### 6. Score 10,000 documents (this week's mini-project)

**CPU-bound, pure Python.** On stock 3.13: `ProcessPoolExecutor` with chunked input. On free-threaded 3.13t: `ThreadPoolExecutor`. The benchmark in this folder demonstrates both.

## The meta-pattern

The tree above optimises for **simplicity and measurability**. Every leaf is a model you can swap in with one constructor change, and every leaf has a clear failure mode you can detect with `psutil` or `tracemalloc`.

The alternative meta-pattern — building elaborate hybrid systems with custom schedulers, async-over-threads, threads-over-subinterpreters — exists in some production systems and is justified for some workloads. It is *almost never* justified at the size of workload covered in this course. If you find yourself reaching for a custom scheduler, you have probably misclassified the workload; back up to the top of the tree.

## The forecast: how the tree changes in 2027–2028

Three changes are likely:

1. **The free-threaded build becomes default** (probably 3.15, October 2026, or 3.16, October 2027). When this happens, the "stock 3.13" column of the table disappears, the "threads" answer wins more often, and the "multiprocessing" answer recedes to the "you need crash isolation" case. The full table collapses into a thinner table.

2. **Subinterpreter adoption broadens.** The `interpreters` module is new in 3.13 and the community is still learning the patterns. Two years from now, expect production patterns for "subinterpreters as lightweight workers" to be documented. Expect at least one major library (likely a web framework or a task queue) to use subinterpreters internally.

3. **The pickling tax stops mattering as much.** Either because multiprocessing is less needed (threads work for CPU on the free-threaded build) or because better alternatives ship (subinterpreters, shared-memory patterns, async-over-IPC). The tax does not go to zero, but it stops being the leading question in the tree.

The tree as written is correct for **May 2026**. Revisit annually. The Python release calendar makes "annually" a meaningful cadence: 3.13 was October 2024, 3.14 is October 2025, 3.15 is October 2026. Each release brings either a new model into stdlib or a significant performance change to an existing one.

## How to use this tree in a code review

When a PR proposes `multiprocessing.Pool`, `concurrent.futures.ThreadPoolExecutor`, or `asyncio.gather`, ask three questions:

1. **What workload classification did the author use to choose this model?** (I/O vs CPU; data size; build target.)
2. **Was there a measurement?** A benchmark, even informal, demonstrating that the chosen model wins.
3. **What is the failure mode?** What happens when the workload grows 10x?

If the answers are clear, approve. If the answers are "I thought threads would be faster," ask for the benchmark. The discipline of this tree is not "use the right model"; the discipline is "be able to defend the choice with a number." Either you measured, or you can articulate why measurement is not necessary for this scale of decision. Both are acceptable; "I thought it would be faster" is not.

## References

- **PEP 703** — Free-threaded build. <https://peps.python.org/pep-0703/>.
- **PEP 734** — Subinterpreters in the stdlib. <https://peps.python.org/pep-0734/>.
- **The Python docs** for `threading`, `asyncio`, `multiprocessing`, `concurrent.futures`, and `interpreters`.
- **Sam Gross, "Per-Interpreter GIL and Beyond"** (PyCon 2023). Free.
- **David Beazley, "Inside the Python GIL"** (PyCon 2009). The history.
