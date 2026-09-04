# Week 11 — Python Concurrency Models Compared

> *Concurrency in Python in 2026 is not one model with one cost curve; it is four models with four cost curves, and the engineering judgement that separates a senior practitioner from a confused one is the ability to look at a workload and say, without ceremony, "that one's threads," "that one's asyncio," "that one's multiprocessing," or "that one's actually a job for the free-threaded build now that 3.13 ships it." The four models are not interchangeable. They have different memory profiles, different startup costs, different debugging stories, different failure modes, and — most importantly — different points along the I/O-bound to CPU-bound spectrum where each one wins. Threads release the Global Interpreter Lock for I/O and for a narrow class of C-extension calls that drop the lock explicitly (NumPy on most ufuncs, the `hashlib` SHA functions, the `zlib` compression calls); they do not release the GIL for pure-Python CPU work, and any tutorial that suggests otherwise is wrong. Asyncio is a cooperative scheduler in a single thread; it wins for high-concurrency, low-per-task-work I/O (think 10,000 open HTTP connections), and it loses — sometimes catastrophically — when a single coroutine forgets to await and blocks the event loop for the entire process. Multiprocessing sidesteps the GIL by spawning child interpreters in separate OS processes; the cost is the "pickling tax" (every argument and return value crosses a process boundary as a pickle blob) and the memory of N copies of your imports. The free-threaded build, **PEP 703**, accepted in 2023 and shipped optionally in 3.13 (October 2024), removes the GIL entirely; Sam Gross's prototype became real, threads now scale on CPU-bound work, and the cost — for now — is roughly 15–25% single-threaded slowdown and a handful of C extensions that haven't been audited yet for thread safety. Subinterpreters, **PEP 684**, added a per-interpreter GIL in 3.12 and a Python-level API in 3.13; they sit between threads and processes — lighter than `fork()`, heavier than a thread switch, with their own state and no GIL contention between them. This week is the week we stop treating concurrency as one thing.*

Welcome to Week 11 of **C17 · Crunch Pro Python Advanced**. Last week you climbed the metaprogramming ladder and learned which rung to stand on for any given problem. This week we do the same exercise for concurrency — except the ladder is wider, the cost curves are noisier, and the right answer changes depending on whether you are on the stock GIL'd build of 3.13 or the `--disable-gil` free-threaded build. The premise is unchanged: **measure, do not speculate**. The deliverable, accordingly, is a benchmark. You will score 10,000 documents — a small enough workload that you can iterate on the implementation quickly, a large enough workload that the differences between threads, asyncio, multiprocessing, and free-threaded execution become legible in throughput, latency, and resident memory. You will implement the same workload four times, you will graph the results, and you will write a one-page decision tree that you would hand a teammate who has just been told "make this faster" and is trying to figure out where to start.

The thesis is a flowchart. The right order to *think* about concurrency in 2026 — from cheapest-and-most-legible to most-invasive — is **measure first, then choose**. The four-question flowchart: (1) **Is the workload I/O-bound?** If yes, threads or asyncio; the GIL never blocks I/O syscalls, and either model will let you fan out hundreds-to-thousands of in-flight requests. (2) **Is the workload CPU-bound and pure-Python?** On the stock build, multiprocessing; on the free-threaded build, threads. The honest answer for 3.13 is "try both and pick the one that wins your specific benchmark." (3) **Is the workload CPU-bound and dominated by a single C-extension call that releases the GIL?** Threads on the stock build, threads on the free-threaded build. NumPy's `np.dot`, `hashlib.sha256().update`, and `zlib.compress` all release the GIL on entry and re-acquire on exit. (4) **Is the workload memory-bound, and would the pickling tax of multiprocessing crush you?** Shared memory (`multiprocessing.shared_memory`, added 3.8) or subinterpreters (`interpreters` module, added 3.13). The flowchart fits on an index card. The cost curves do not. We measure.

The standards are the spine. **PEP 703** (Sam Gross, accepted 2023, optional in 3.13, expected default in 3.15 or 3.16) removes the GIL. **PEP 684** (Eric Snow, accepted 2023, available 3.12) gives each subinterpreter its own GIL. **PEP 554** (Eric Snow, accepted 2024 in revised form as PEP 734) is the Python-level subinterpreters API. **PEP 3148** (Brian Quinlan, 2009) defined `concurrent.futures` — the unified `Executor` interface that lets you swap a `ThreadPoolExecutor` for a `ProcessPoolExecutor` with one constructor change. **PEP 3156** (Guido van Rossum, 2012) defined `asyncio`. **PEP 492** (Yury Selivanov, 2015) added `async`/`await`. **PEP 525** and **PEP 530** (Yury Selivanov, 2016) added async generators and async comprehensions. **PEP 654** (Irit Katriel, 2022) added `ExceptionGroup`/`except*` — the syntactic glue that makes structured concurrency tolerable in 3.11+. The Python docs are the official source: `threading` <https://docs.python.org/3/library/threading.html>, `asyncio` <https://docs.python.org/3/library/asyncio.html>, `multiprocessing` <https://docs.python.org/3/library/multiprocessing.html>, `concurrent.futures` <https://docs.python.org/3/library/concurrent.futures.html>, and the new `interpreters` module <https://docs.python.org/3/library/interpreters.html>. Sam Gross's PyCon 2023 talk "Per-Interpreter GIL and Beyond" (free, YouTube) is the canonical explainer for free-threaded Python.

The worked example is a **document scorer**. Pretend you are running a relevance-ranking microservice. The input is a corpus of 10,000 short documents (the included `data/corpus.json` is generated synthetically; nothing to download). Each document has a body, a query is fixed at module load, and "scoring" is two steps: (1) **tokenise** the body (a CPU-bound regex split plus lowercase plus stopword filter, around 100 microseconds per document on a 2025-class laptop), and (2) **score** the body against the query (a TF-IDF dot product, also CPU-bound, around 50 microseconds). The total wall-clock work is roughly 1.5 seconds of pure-Python CPU when scored serially. This is intentional. The benchmark needs to be big enough to dwarf scheduler overhead and small enough that you can run it forty times in an afternoon while tuning.

**Version one** uses **threads** via `concurrent.futures.ThreadPoolExecutor`. The result, on the stock GIL'd build, is *slightly slower than serial* — threads add scheduler overhead but the GIL serialises the actual scoring work. This is the canonical "threads make Python CPU-bound code slower" demonstration; it is true on the stock build and we record the number so we have something to compare against. We also add an I/O-bound variant — a `time.sleep(0.001)` per document, simulating a remote API call — and observe that threads now beat serial by approximately the pool size, because the GIL is released on the sleep syscall.

**Version two** uses **asyncio**. We tokenise and score inside an `async def`, schedule them through `asyncio.gather`, and observe that — for the CPU-bound version — asyncio is also slower than serial (one thread, one event loop, no parallelism for CPU work). For the I/O-bound version (we swap `time.sleep` for `await asyncio.sleep`), asyncio is the *fastest* of the four because the event loop has lower per-task overhead than a thread context switch.

**Version three** uses **multiprocessing** via `concurrent.futures.ProcessPoolExecutor`. The CPU-bound version is faster than serial by roughly `min(corpus_size / chunksize, cpu_count)` — true parallelism, true speedup, with two caveats we measure: the **startup cost** (forking or spawning N workers takes 50–300 ms depending on platform and start method), and the **pickling tax** (every chunk crosses a process boundary as a pickle blob; on the 10k corpus this is a few hundred milliseconds of pure pickle/unpickle work). We measure both. We also demonstrate `multiprocessing.shared_memory` for the case where the input data is too large to copy.

**Version four** uses the **free-threaded build**. If you have access to a free-threaded interpreter (Python 3.13+ built with `--disable-gil`, available from <https://www.python.org/downloads/> as a separate installer marked "free-threaded", or via `uv python install 3.13t`), you rerun the threading benchmark and observe linear speedup on the CPU-bound version — threads, finally, scaling on Python code. If you do not have the free-threaded build installed, the benchmark prints the missing-build message and the rest of the project still works.

**Version five (stretch)** uses **subinterpreters**. The `interpreters` module in 3.13 (PEP 734) lets you spawn a subinterpreter, run a script in it, and communicate via `interpreters.Queue`. Subinterpreters have their own GIL — true parallelism on CPU-bound work — but they share the OS process, so the startup cost is lower than `fork()` and there is no pickling tax on bytes/strings/ints (which are shared). We measure this and observe that subinterpreters are *between* threads and processes on every axis we care about.

The deliverable for the week is the five-mechanism benchmark, plus a graph that compares throughput (docs/sec), median latency (per-document microseconds), and resident memory (megabytes) across the five implementations, plus a **one-page decision tree** that explicitly answers "given workload X, which model do I reach for and why?" The benchmark is small (a few seconds of wall-clock per run) but the discipline of measuring instead of speculating is the point.

## Learning objectives

By the end of this week, you will be able to:

- **Articulate** the four (now five, counting subinterpreters) concurrency models in Python — what each one parallelises, what each one serialises, what each one costs to spin up. Cite PEP 703, PEP 684, PEP 734.
- **Predict**, given a workload description, which model will win and by approximately how much, before running the benchmark. Verify your prediction against the measurement.
- **Use** `concurrent.futures.ThreadPoolExecutor` and `concurrent.futures.ProcessPoolExecutor` interchangeably via the `Executor` protocol. Cite PEP 3148.
- **Explain** when the GIL releases for I/O (every blocking syscall — `read`, `write`, `recv`, `send`, `sleep`, `select`, `poll`, `epoll`), and when it does *not* release for CPU (every pure-Python opcode, every function call into a C extension that has not explicitly dropped the GIL). Cite the `Py_BEGIN_ALLOW_THREADS` macro: <https://docs.python.org/3/c-api/init.html#c.Py_BEGIN_ALLOW_THREADS>.
- **Write** an asyncio program that uses `asyncio.gather`, `asyncio.TaskGroup` (3.11+, PEP 654), `asyncio.Semaphore`, and `asyncio.timeout`. Articulate why you would prefer `TaskGroup` to `gather` in 2026 (structured concurrency, automatic cleanup).
- **Diagnose** the "asyncio blocked the event loop" bug — what it looks like in logs, how `asyncio.run` with `debug=True` flags it (`PYTHONASYNCIODEBUG=1`), how to fix it with `loop.run_in_executor`.
- **Write** a multiprocessing program that uses `ProcessPoolExecutor`, `multiprocessing.Manager`, and `multiprocessing.shared_memory`. Articulate the difference between `fork`, `spawn`, and `forkserver` start methods and which to choose on Linux/macOS/Windows.
- **Measure** the pickling tax — write a benchmark that times `pickle.dumps`/`pickle.loads` against the workload and reports the percentage of wall-clock the process spends crossing process boundaries.
- **Articulate** PEP 703 — what changes (the GIL is gone), what stays the same (single-threaded code semantics), what regresses (single-threaded performance by 15–25% on the prototype), and what is still being audited (third-party C extensions). Cite Sam Gross's talks.
- **Articulate** PEP 684 / PEP 734 — what a subinterpreter is, why each one having its own GIL is the headline, what `interpreters.Queue` does, what the limitations are (no shared mutable state, restricted pickle subset for transit).
- **Decide**. Given a real workload (HTTP-API fanout, image processing, training-data preprocessing, log aggregation), pick the right model and defend the choice in two sentences.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | Past the outcome set: five concurrency models, the free-threaded build and per-interpreter GILs are on no second programming course’s syllabus. |
| Industry | Choose a concurrency model for a real workload and defend it with a benchmark somebody else can rerun on their own machine. |
| Beyond the bar | The measurements are published as a table, including runs against the free-threaded build and PEP 734 subinterpreters — `mini-project/benchmark-results.md` |


## Prerequisites

- **C17 Weeks 1–10** completed. Week 3's coverage of the GIL is directly load-bearing this week; Week 4's coverage of asyncio is the foundation for Tuesday's lecture; Week 6's coverage of threads and processes is the foundation for Monday's.
- **Python 3.11+ (3.13 strongly preferred).** Some examples use `asyncio.TaskGroup` (3.11+), `ExceptionGroup` (PEP 654, 3.11+), and `interpreters` (3.13+). The free-threaded build is 3.13+ only.
- **A multi-core machine.** Most modern laptops qualify; you need at least 2 cores to observe multiprocessing speedup, 4 is better. Verify with `os.cpu_count()`.
- **`psutil` installed** for the memory measurement in the benchmark. `pip install psutil`. About 3 MB; cross-platform.
- **(Optional) The free-threaded build of Python 3.13+** for Thursday's lecture and the Version 4 benchmark. Install via `uv python install 3.13t` or from <https://www.python.org/downloads/>. The benchmark will skip Version 4 cleanly if the build is absent.

## Topics covered

- **Threads in 2026** — `threading.Thread`, `threading.Lock`, `threading.RLock`, `concurrent.futures.ThreadPoolExecutor`. The GIL release rules for I/O. The set of C extensions that drop the GIL on entry.
- **Asyncio in 2026** — `asyncio.run`, `async def`, `await`, `asyncio.gather`, `asyncio.TaskGroup` (PEP 654), `asyncio.Semaphore`, `asyncio.timeout`. The event-loop-blocking failure mode and how to spot it.
- **Multiprocessing in 2026** — `multiprocessing.Process`, `concurrent.futures.ProcessPoolExecutor`, `multiprocessing.shared_memory` (PEP 574-adjacent), `multiprocessing.Manager`. Start methods. Pickling.
- **The free-threaded build (PEP 703)** — what works, what does not, the single-threaded slowdown, the ABI flag (`Py_GIL_DISABLED`). Sam Gross's talks.
- **Subinterpreters (PEP 684, PEP 734)** — `interpreters.create()`, `interpreters.Queue`, the per-interpreter GIL, what data can cross.
- **The benchmark methodology** — `time.perf_counter`, `tracemalloc`, `psutil.Process.memory_info()`. Why median latency matters more than mean. Why throughput must report a confidence interval.
- **The decision tree** — when to reach for which model. Written down so you can hand it to a teammate.

## Weekly schedule (~33h intensive)

| Day       | Focus                                                                | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Threads end-to-end; the GIL release rules; thread pool benchmarks    | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | Asyncio end-to-end; TaskGroup; the event-loop blocking failure       | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Wednesday | Multiprocessing; pickling; shared memory; start methods              | 2h       | 1.5h      | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 6.5h        |
| Thursday  | PEP 703 (free-threaded), PEP 684 (subinterpreters), mini-project kickoff | 0h    | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Friday    | Mini-project: implement all five versions of the document scorer     | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Saturday  | Mini-project: benchmark; write the decision tree; verify on free-threaded | 0h  | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                                    | 0h       | 0h        | 0h         | 0.5h      | 1h       | 0h           | 0h         | 1.5h        |
| **Total** |                                                                      | **6h**   | **4.5h**  | **3h**     | **3h**    | **7h**   | **7h**       | **2.5h**   | **33h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | PEP 703, PEP 684, PEP 734, Sam Gross talks, the threading/asyncio/multiprocessing docs |
| [lecture-notes/01-threads-and-asyncio.md](./lecture-notes/01-threads-and-asyncio.md) | Threads and asyncio side by side. The GIL release rules. The event-loop blocking failure. PEP 3148, PEP 3156, PEP 492 |
| [lecture-notes/02-multiprocessing-and-the-pickling-tax.md](./lecture-notes/02-multiprocessing-and-the-pickling-tax.md) | Multiprocessing end-to-end. Start methods. Pickling. Shared memory. When the tax breaks the model |
| [lecture-notes/03-pep-703-and-pep-684-the-future.md](./lecture-notes/03-pep-703-and-pep-684-the-future.md) | The free-threaded build (PEP 703). Subinterpreters (PEP 684 / PEP 734). What changes in 3.15 |
| [exercises/exercise-01-thread-vs-asyncio.py](./exercises/exercise-01-thread-vs-asyncio.py) | Predict which is faster on three workloads; run it; explain the result |
| [exercises/exercise-02-gil-release-audit.py](./exercises/exercise-02-gil-release-audit.py) | Probe which C-extension calls release the GIL; build the audit table |
| [exercises/exercise-03-multiprocessing-pickle-tax.py](./exercises/exercise-03-multiprocessing-pickle-tax.py) | Measure the pickling tax on three argument shapes; report the percentage |
| [exercises/exercise-04-asyncio-blocking-event-loop.py](./exercises/exercise-04-asyncio-blocking-event-loop.py) | Reproduce the canonical "blocked event loop" bug; fix it three different ways |
| [exercises/SOLUTIONS.md](./exercises/SOLUTIONS.md) | Expected outputs, common errors, the reasoning behind each exercise |
| [challenges/challenge-01-free-threaded-audit.md](./challenges/challenge-01-free-threaded-audit.md) | Install the free-threaded build; rerun the benchmark; identify any C extension that breaks |
| [challenges/challenge-02-subinterpreter-pipeline.md](./challenges/challenge-02-subinterpreter-pipeline.md) | Build a three-stage pipeline using `interpreters.Queue`; benchmark against a process pool |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~7h) |
| [mini-project/README.md](./mini-project/README.md) | Build the document scorer five ways; benchmark; write the decision tree |
| [mini-project/decision-tree.md](./mini-project/decision-tree.md) | The reference decision tree (read after attempting your own) |

## Stretch

- Read [PEP 703](https://peps.python.org/pep-0703/) end-to-end (~90 minutes). Sam Gross, 2023. The single most consequential CPython PEP of the decade.
- Read [PEP 684](https://peps.python.org/pep-0684/) end-to-end (~30 minutes). Eric Snow, 2023. Per-interpreter GIL.
- Read [PEP 734](https://peps.python.org/pep-0734/) end-to-end (~25 minutes). The revised, accepted form of the subinterpreters API.
- Read [PEP 554](https://peps.python.org/pep-0554/) (~25 minutes). The original subinterpreters PEP; deferred in favour of PEP 734 but the rationale is still load-bearing.
- Watch Sam Gross's PyCon 2023 talk ["Per-Interpreter GIL and Beyond"](https://www.youtube.com/results?search_query=sam+gross+pycon+2023+free+threading) — about 30 minutes. The canonical free-threading talk. Free.
- Watch Sam Gross's PyCon 2024 talk ["A Per-Interpreter GIL: Concurrency and Parallelism with Subinterpreters"](https://www.youtube.com/results?search_query=sam+gross+pycon+2024) — about 30 minutes. The follow-up; covers what landed in 3.13. Free.
- Watch Lukasz Langa's keynote on free-threaded Python at PyCon 2024 (~45 minutes) — Lukasz is one of the implementers and walks through the engineering trade-offs. Free.
- Watch Yury Selivanov's PyCon 2018 talk ["Asyncio in Python 3.7 and Beyond"](https://www.youtube.com/results?search_query=yury+selivanov+asyncio+pycon) — about 45 minutes. The reference asyncio talk; Yury is the PEP 492 author. Free.
- Read [the `threading` docs](https://docs.python.org/3/library/threading.html) end-to-end (~20 minutes). About 6,000 words.
- Read [the `asyncio` docs index](https://docs.python.org/3/library/asyncio.html) plus the high-level API (~40 minutes). The full asyncio docs are 30,000+ words; skim the structure, deep-read the `asyncio.Task` and `asyncio.TaskGroup` sections.
- Read [the `multiprocessing` docs](https://docs.python.org/3/library/multiprocessing.html) end-to-end (~30 minutes). About 12,000 words.
- Read [the `interpreters` docs (3.13+)](https://docs.python.org/3/library/interpreters.html) — short, ~3,000 words. The newest module in the stdlib.

## Up next

[Week 12 — Network Programming and Production HTTP](../week-12-network-programming-production-http/) — You have now measured four concurrency models on a CPU-bound workload. Next week we put the I/O-bound side of the table under the microscope: building production HTTP clients and servers with `httpx`, `aiohttp`, `uvloop`, and the new `asyncio.StreamingResponse` machinery. The lesson of Week 11 — that asyncio's per-task cost is the lowest of the four for I/O — becomes the operating assumption of Week 12.
