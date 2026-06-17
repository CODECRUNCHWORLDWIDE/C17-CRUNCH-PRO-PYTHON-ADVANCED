# Week 6 — Threads, Processes, and When to Use What

> *Three primitives. Three cost profiles. One decision tree. `threading.Thread` shares the address space and pays a context-switch tax; in the default build it serialises on the GIL for pure-Python work but releases it across the C-extension boundary and across IO syscalls. `multiprocessing.Process` is a UNIX-style fork (or a `spawn` on macOS/Windows) plus a `pickle`-based IPC channel — true parallelism on N cores, but every argument and every return value is serialised twice and copied across an address-space boundary. `asyncio` is N coroutines on one OS thread, multiplexed by a selector — cheapest in memory by two orders of magnitude, but every blocking call must be re-engineered to yield. The 3.13 free-threaded build (`python3.13t`, PEP 703, Sam Gross) finally retires the GIL and makes `threading.Thread` a real parallelism primitive for pure-Python work — at the cost of single-threaded throughput and ecosystem maturity. **This week you measure all four against the same three workloads and produce a defensible recommendation per workload.***

Welcome to Week 6 of **C17 · Crunch Pro Python Advanced**. Weeks 4 and 5 reconstructed `asyncio` from first principles and then layered structured concurrency, cancellation, and back-pressure on top. By Sunday of Week 5 you had a ~500-line async crawler that obeys robots.txt, applies politeness delays, shields its sink writes, and exits cleanly on SIGINT. The asyncio half of the concurrency story is now a tool in your hand, not a mystery.

This week is the other half. Threads. Processes. The choice. The CPython 3.13 free-threaded build (PEP 703) revisited from the practitioner's perspective — not "what is the GIL" (Week 3 covered that) but "what changes about my code when the GIL is gone, what does *not* change, and what should I be measuring before I rewrite anything." And, woven through every lecture, the question that drives the week: **for a given workload, what is the right concurrency primitive, and how do I prove it?**

The classification dimension is well-known but rarely taught honestly. **CPU-bound** work — hashing, encoding, numerical kernels, regex over large strings — wants real parallelism. On default CPython 3.13, that means `multiprocessing` or a C-extension that drops the GIL (NumPy, Cython `nogil`, native code via `ctypes`). On 3.13t (free-threaded), it can mean `threading.Thread`. **IO-bound** work — HTTP, database calls, disk reads — wants concurrency, not parallelism. `asyncio` is usually the right choice in 2026; `threading` is the right choice when an existing blocking library is too expensive to rewrite. **Mixed** work — a worker that does a fetch, then a parse, then another fetch — wants a thread pool with the GIL or an event loop with a `run_in_executor` escape hatch. The decision is not "which primitive is best." It is "which primitive is right for *this* workload, given *these* constraints, on *this* Python build."

We are going to stop guessing and start measuring. Every lecture this week ends with a benchmark. Every exercise ends with a wall-clock and a `cProfile` table. The mini-project asks you to take three small, deliberate workloads — one CPU-bound, one IO-bound, one mixed — implement each with the *wrong* primitive first to feel the pain, then implement each with the *right* primitive, and produce a one-page memo that defends your choice with numbers.

`concurrent.futures` (PEP 3148, Brian Quinlan, 2009; landed 3.2) is the unifying abstraction across this week. `ThreadPoolExecutor` and `ProcessPoolExecutor` share the same `submit() -> Future` and `map()` surface — swap one for the other and your code is unchanged. This is not a coincidence; Quinlan designed the API specifically to make the threads-vs-processes decision a one-line edit. We will use this leverage in the exercises: write the workload against `Executor`, then run it under both executors, then compare.

`joblib` (Gaël Varoquaux et al., 2008+) and its `loky` (Olivier Grisel, Tom Moreau, 2017+) backend are the production thread/process pool toolkit the scientific Python world settled on. `joblib.Parallel(n_jobs=N)(delayed(f)(x) for x in xs)` is the right answer for most embarrassingly-parallel work in a notebook; `loky` is the robust process backend that scikit-learn shipped to replace the stdlib's flakier `multiprocessing.Pool` on macOS and Windows. We will cover both — not because they are wildly different from stdlib, but because they are what your colleagues actually use, and the underlying choices (forkserver vs. spawn, pickle-by-value vs. memmap-by-reference, cloudpickle for closures) are real production concerns.

The 3.13 free-threaded build returns in Lecture 3. Week 3 introduced the GIL, the eval-loop slot, the gilstate functions, and PEP 703 at the level of "what changes inside CPython." This week we look at it from the *user's* perspective: how do I install 3.13t, how do I detect at runtime whether the GIL is enabled (`sys._is_gil_enabled()`), what does my measurement look like with vs. without the GIL, and what gotchas have already surfaced (free-threaded NumPy is staged; `functools.lru_cache` is now atomic; `dict` and `list` have per-object locks; reference counting uses biased locking — Hopkinson, Gross 2023). We will run a small `threading` benchmark on both builds and read the numbers in the same room.

By Sunday you will have shipped a small portfolio piece — call it `concurrency-bench` or whatever you like — that takes the same three workloads, runs them through `asyncio`, `threading`, `ThreadPoolExecutor`, `ProcessPoolExecutor`, `joblib(threading)`, `joblib(loky)`, plus a free-threaded variant if you can build 3.13t, and produces a comparison table plus a one-page memo. This is the artifact you point to in interviews when someone asks "how would you parallelise that workload" — you have an answer with numbers.

## Learning objectives

By the end of this week, you will be able to:

- **Classify** a workload as CPU-bound, IO-bound, or mixed by reading code and applying the GIL-release test: "during the slowest operation in this code, is the GIL held?" Apply this to standard cases (HTTP, hashing, NumPy, regex, file IO, JSON parsing) and defensible edge cases (gzip decompression, the JSON C accelerator, `re` patterns over very large strings).
- **Choose** the right concurrency primitive per workload and defend the choice with at least two numbers: wall-clock and per-task CPU. The decision tree: CPU-bound + pure Python → `ProcessPoolExecutor` (or 3.13t threads); CPU-bound + C-extension that drops the GIL → `ThreadPoolExecutor`; IO-bound + greenfield → `asyncio`; IO-bound + brownfield blocking library → `ThreadPoolExecutor`; mixed → `ThreadPoolExecutor` or `asyncio` with `loop.run_in_executor`.
- **Implement** the same workload three ways (async, thread pool, process pool) using `concurrent.futures.Executor` as the common surface. Compare wall-clock, per-task CPU, and memory footprint.
- **Explain** the cost model of `multiprocessing.Process` vs. `threading.Thread`: process spawn cost (10–100 ms typical, much higher on Windows `spawn`), pickle round-trip on every `submit()`, `fork` vs. `spawn` vs. `forkserver` start methods, and why a 1-ms task in a process pool is slower than running it serially.
- **Articulate** what changes about your code when the GIL is gone (3.13t): pure-Python CPU-bound threading suddenly scales near-linearly, shared-state bugs that the GIL was hiding now manifest as real races, free-threaded-incompatible C extensions are tagged and disabled. Cite PEP 703 (Gross 2023) and `Doc/whatsnew/3.13.rst` §Free-Threaded.
- **Use** `concurrent.futures.ThreadPoolExecutor` and `ProcessPoolExecutor` idiomatically: `as_completed` for streaming results, `map` for ordered output, `chunksize` for the process pool's pickle amortisation, `initializer` for per-worker setup.
- **Use** `joblib.Parallel` with the right backend: `threading` for GIL-releasing code, `loky` (the default in modern joblib) for pure-Python CPU work, `multiprocessing` only when you must reproduce legacy behaviour. Know what `delayed`, `parallel_backend`, and `Memory` do.
- **Diagnose** the four canonical mistakes: using `multiprocessing` for a 1-ms task (overhead dwarfs the work), using `threading` for pure-Python CPU work on default CPython (the GIL serialises you), using `asyncio` for a blocking library call (the loop stalls for every task), using a process pool inside Jupyter on Windows without an `if __name__ == "__main__":` guard (recursive process spawning).
- **Cite** the relevant PEPs and source files from memory: PEP 3148 (`concurrent.futures`), PEP 703 (free-threaded), PEP 711 (PyBI; relevant because of 3.13t binary distribution), `Lib/concurrent/futures/thread.py`, `Lib/concurrent/futures/process.py`, `Lib/multiprocessing/`, the joblib `Parallel` API, the loky README.

## Prerequisites

- **C17 Weeks 1–5** completed. In particular: Week 3 (GIL, free-threaded build, PEP 703 at the C level) and Week 4 (`asyncio` from first principles). You should be able to explain what the GIL protects, what an `await` does to the GIL, and what a `Task` is.
- A working CPython **3.13 or newer**. The standard build is sufficient for the bulk of the week. The free-threaded build (3.13t) is required only for Lecture 3's measurements and the optional stretch of the mini-project; we will tell you how to install it.
- Comfort with `subprocess`, `signal`, and basic OS process model from C1 / C16. If new: re-read the Python docs on `subprocess.run` and the `signal` module before Monday.
- Optional: install `joblib` (`pip install joblib`), `aiohttp` (`pip install aiohttp`, already from Week 5), `psutil` (`pip install psutil`) for memory measurement.
- A machine with **at least 4 CPU cores**. The CPU-bound benchmarks are pointless on a single-core VM. If you only have a single-core machine, run the benchmarks on a cloud instance.

## Topics covered

- **The four primitives, side by side** — `threading.Thread`, `asyncio.Task`, `multiprocessing.Process`, `concurrent.futures.Executor`. Cost model per primitive: spawn time, per-task overhead, memory per unit of concurrency, IPC cost, what is shared.
- **The CPU/IO/mixed classification** — The GIL-release test. The canonical examples. The edge cases (CPython's JSON accelerator releases the GIL; the `re` module mostly does not; `hashlib` does; `bz2` and `lzma` do; pure-Python loops do not).
- **`threading` revisited** — `Thread.start()`, `Thread.join()`, `Lock`, `RLock`, `Event`, `Condition`, `Semaphore`. What the GIL protects (the bytecode interpreter's atomic operations on object refcounts and dict lookups) and what it does *not* protect (your application invariants). Cite `Lib/threading.py` and `Python/ceval_gil.c`.
- **`concurrent.futures` as the unified API** — `Executor.submit() -> Future`, `Executor.map()`, `as_completed`, `wait`. Why the same code works against `ThreadPoolExecutor` and `ProcessPoolExecutor` with a one-line change. Cite `Lib/concurrent/futures/_base.py`, `Lib/concurrent/futures/thread.py`, `Lib/concurrent/futures/process.py`. PEP 3148 (Quinlan 2009).
- **`multiprocessing` in depth** — `Process`, `Pool`, `Queue`, `Pipe`, `Manager`, `shared_memory`. The three start methods (`fork`, `spawn`, `forkserver`) and what each costs. The pickle requirement for every argument and return value. Why a pure-Python `lambda` cannot cross the boundary without `cloudpickle`. Cite `Lib/multiprocessing/context.py`, `Lib/multiprocessing/pool.py`.
- **When `multiprocessing` is the wrong answer** — Tasks under ~10ms. Workloads that share large state (the state is pickled per worker). Workloads on macOS/Windows where `spawn` cost is high (~200ms per worker). Workloads with deep recursion (pickle stack-depth limit). Workloads using objects with unpickleable members (open files, sockets, threading locks).
- **`joblib.Parallel` and the `loky` backend** — `Parallel(n_jobs=N, backend="loky")(delayed(f)(x) for x in xs)`. Why scikit-learn replaced `multiprocessing.Pool` with loky (semantics around exceptions, worker timeout, reusable pools). The `threading` backend for GIL-releasing kernels. `Memory(location=...)` for transparent disk caching of expensive function calls.
- **The 3.13 free-threaded build, revisited from the user side** — Install (`uv python install 3.13t` or build from source with `--disable-gil`). Detect at runtime: `sys._is_gil_enabled()`, `sysconfig.get_config_var('Py_GIL_DISABLED')`. What changes (pure-Python threading scales). What does not (the language semantics). What surprises (single-threaded throughput is ~10% slower; some C extensions are not compatible yet; biased reference counting; per-object locks). Cite PEP 703 §Implementation, §Reference Counting, §Compatibility.
- **The decision tree** — A one-page flowchart you will commit to memory by Sunday. Used in the mini-project to justify every primitive choice.

## Weekly schedule (~34h intensive)

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Threading revisited, the GIL in practice, `concurrent.futures` | 2h    | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | `multiprocessing`, joblib, loky, when each is wrong         | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Wednesday | The 3.13 free-threaded build, benchmarking discipline       | 2h       | 1.5h      | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 6.5h        |
| Thursday  | Mini-project kickoff: the three workloads, the harness      | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Friday    | Mini-project deep work: measurement, the memo               | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Saturday  | Mini-project polish: free-threaded variant, the comparison  | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                            | 0h       | 0h        | 0h         | 0.5h      | 1h       | 0h           | 0h         | 1.5h        |
| **Total** |                                                             | **6h**   | **4.5h**  | **3h**     | **3h**    | **7h**   | **7h**       | **2.5h**   | **33h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview |
| [resources.md](./01-resources.md) | `threading`, `concurrent.futures`, `multiprocessing`, `joblib`, `loky`, PEP 3148, PEP 703 |
| [lecture-notes/01-threading-and-the-GIL-revisited.md](./02-lecture-notes/01-threading-and-the-GIL-revisited.md) | `threading.Thread`, the GIL-release test, `concurrent.futures.ThreadPoolExecutor`, what threads are *and are not* good for in 3.13 |
| [lecture-notes/02-multiprocessing-and-when-its-wrong.md](./02-lecture-notes/02-multiprocessing-and-when-its-wrong.md) | `multiprocessing.Process`, `Pool`, the three start methods, the pickle tax, joblib + loky, the wrong-primitive failure modes |
| [lecture-notes/03-the-3-13-free-threaded-build-revisited.md](./02-lecture-notes/03-the-3-13-free-threaded-build-revisited.md) | PEP 703 from the practitioner's side, installing 3.13t, detecting at runtime, measuring pure-Python threading scaling with and without the GIL |
| [exercises/README.md](./03-exercises/00-overview.md) | Index |
| [exercises/exercise-01-CPU-bound-with-multiprocessing.py](./03-exercises/exercise-01-CPU-bound-with-multiprocessing.py) | A pure-Python CPU kernel under `ThreadPoolExecutor` vs. `ProcessPoolExecutor`; observe the GIL serialise the threads and the processes scale |
| [exercises/exercise-02-IO-bound-with-async.py](./03-exercises/exercise-02-IO-bound-with-async.py) | The same N HTTP fetches under `asyncio.gather`, `ThreadPoolExecutor(max_workers=N)`, `ProcessPoolExecutor`; observe the orders of magnitude |
| [exercises/exercise-03-mixed-with-threadpool.py](./03-exercises/exercise-03-mixed-with-threadpool.py) | A worker that fetches then hashes; the right shape is `asyncio` + `loop.run_in_executor` for the hash, but a thread pool is the simpler answer |
| [challenges/README.md](./04-challenges/00-overview.md) | Stretch challenge |
| [challenges/challenge-01-3-implementations-of-same-workload.md](./04-challenges/challenge-01-3-implementations-of-same-workload.md) | One workload, three primitives, one timed sitting — produce the comparison table |
| [quiz.md](./05-quiz.md) | 10 MCQ |
| [homework.md](./06-homework.md) | Six problems (~6h) |
| [mini-project/README.md](./07-mini-project/00-overview.md) | `concurrency-bench`: three workloads, every primitive, a one-page memo |

## Stretch

- Build CPython 3.13t from source (`./configure --disable-gil && make -j8`) if `uv python install 3.13t` is not available on your platform. The 30-minute build is itself an education; you see the `--disable-gil` flag flow through to `Py_GIL_DISABLED` macros throughout the source tree. The CPython devguide has the step-by-step.
- Read Sam Gross's [PEP 703 — Making the Global Interpreter Lock Optional in CPython](https://peps.python.org/pep-0703/) end-to-end (~75 minutes). Sections 1–3 are essential; §4 (Specification) and §5 (Implementation) are dense but rewarding. The biased reference-counting design (§5.1) is the keystone of the whole proposal.
- Read [`Lib/concurrent/futures/process.py`](https://github.com/python/cpython/blob/main/Lib/concurrent/futures/process.py) end-to-end (~600 lines, 30 min). The "call queue / result queue / work item / executor manager thread" design is more elaborate than the thread executor; the comments explain why.
- Install `loky` directly (`pip install loky`) and read its [README](https://github.com/joblib/loky/blob/master/README.rst) (~10 min). The "reusable executor" idea — workers persist across `Executor` lifetimes — is the production fix for `ProcessPoolExecutor`'s spawn cost.
- Read [Larry Hastings's *Gilectomy* retrospective (2017)](https://lwn.net/Articles/723514/). The previous serious attempt at removing the GIL, and the lessons that informed PEP 703. Compare and contrast with Gross's approach. The biased-refcount design (Gross 2023) is the key insight Hastings did not have.
- Skim [scikit-learn's parallel-backend docs](https://scikit-learn.org/stable/computing/parallelism.html). They cite joblib + loky for a reason; the failure modes they document are the production case study.

## Up next

[Week 7 — Profiling Like It's Your Job](../week-07-profiling-like-its-your-job/) — `cProfile`, `py-spy`, `austin`, `scalene`, flamegraphs. The benchmarking discipline you start this week becomes a real toolkit next week. Phase 3 (Performance & Native Code) begins.
