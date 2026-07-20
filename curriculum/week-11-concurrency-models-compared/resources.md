# Week 11 — Resources

All free. All authoritative. The five most important entries are PEP 703, PEP 684, PEP 734, Sam Gross's two PyCon talks, and the Python docs for `threading`, `asyncio`, `multiprocessing`, and `interpreters`. Read those first; the rest is supporting cast.

## Primary sources (read first)

### The PEPs

- **PEP 703 — Making the Global Interpreter Lock Optional in CPython** (Sam Gross, accepted 2023, optional in 3.13, expected default no earlier than 3.15). The single most consequential CPython PEP of the decade. <https://peps.python.org/pep-0703/>. About 18,000 words. The "Motivation," "Specification," and "Backwards Compatibility" sections are non-negotiable; the implementation notes (biased reference counting, deferred reference counting, mimalloc, the changes to dict/list/set internals) are worth a second pass if you ever plan to maintain a C extension. The PEP is dense; budget 90 minutes for the first read.
- **PEP 684 — A Per-Interpreter GIL** (Eric Snow, accepted 2023, available 3.12). The C-API-level change. <https://peps.python.org/pep-0684/>. About 5,000 words.
- **PEP 734 — Multiple Interpreters in the Stdlib** (Eric Snow, accepted 2024, available 3.13). The Python-level API; the `interpreters` module. <https://peps.python.org/pep-0734/>. About 4,500 words. Supersedes PEP 554.
- **PEP 554 — Multiple Interpreters in the Stdlib** (Eric Snow, deferred, 2017 onward). The original subinterpreters proposal; technically deferred in favour of PEP 734, but the rationale section is still load-bearing. <https://peps.python.org/pep-0554/>. About 4,000 words.
- **PEP 3148 — futures - execute computations asynchronously** (Brian Quinlan, accepted 2009, available 3.2). The PEP that defined `concurrent.futures`. <https://peps.python.org/pep-3148/>. About 5,500 words. The single most-implemented stdlib concurrency abstraction; you will use `ThreadPoolExecutor` and `ProcessPoolExecutor` constantly.
- **PEP 3156 — Asynchronous IO Support Rebooted: the "asyncio" module** (Guido van Rossum, accepted 2012, available 3.4). The original asyncio PEP. <https://peps.python.org/pep-3156/>. About 12,000 words. Long; skim once for the design rationale.
- **PEP 492 — Coroutines with async and await syntax** (Yury Selivanov, accepted 2015, available 3.5). The `async`/`await` syntax. <https://peps.python.org/pep-0492/>. About 7,000 words.
- **PEP 525 — Asynchronous Generators** (Yury Selivanov, 2016, available 3.6). <https://peps.python.org/pep-0525/>.
- **PEP 530 — Asynchronous Comprehensions** (Yury Selivanov, 2016, available 3.6). <https://peps.python.org/pep-0530/>.
- **PEP 654 — Exception Groups and except\*** (Irit Katriel, 2022, available 3.11). The syntactic glue under `asyncio.TaskGroup`. <https://peps.python.org/pep-0654/>. About 6,000 words.
- **PEP 711 — PyBI: a standard format for distributing Python Binaries** (deferred, but relevant for free-threaded distribution). <https://peps.python.org/pep-0711/>.

### The Python docs

- **`threading`** — <https://docs.python.org/3/library/threading.html>. The official source. About 6,000 words. Read the `Thread`, `Lock`, `RLock`, `Condition`, `Event`, and `Semaphore` sections; skim the rest.
- **`asyncio`** — <https://docs.python.org/3/library/asyncio.html>. The index. The "High-level API" section (~30 pages of online docs) is the reference for `asyncio.run`, `asyncio.gather`, `asyncio.TaskGroup`, `asyncio.Semaphore`, `asyncio.timeout`, `asyncio.to_thread`. The "Low-level API" section is for library authors.
- **`multiprocessing`** — <https://docs.python.org/3/library/multiprocessing.html>. The official source. About 12,000 words. The "Contexts and start methods" section (~2,000 words on `fork`, `spawn`, `forkserver`) is the section that traps most people.
- **`concurrent.futures`** — <https://docs.python.org/3/library/concurrent.futures.html>. About 3,500 words. The unified `Executor` interface; the single most-used module of the four.
- **`multiprocessing.shared_memory`** — <https://docs.python.org/3/library/multiprocessing.shared_memory.html>. The shared-memory module added in 3.8. The escape hatch from the pickling tax.
- **`interpreters` (3.13+)** — <https://docs.python.org/3/library/interpreters.html>. The newest stdlib concurrency module. About 3,000 words.
- **The C-API GIL macros** — <https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock>. `Py_BEGIN_ALLOW_THREADS` and `Py_END_ALLOW_THREADS`. The C-API contract for "release the GIL while we do this." Five paragraphs; required reading.

### Free-threading explainers (Sam Gross and friends)

- **Sam Gross — "Per-Interpreter GIL and Beyond"** (PyCon US 2023) — search YouTube; ~30 minutes. The talk that introduced PEP 703 to a wide audience. Free. Highest-priority watch.
- **Sam Gross — "A Per-Interpreter GIL"** (PyCon US 2024) — ~30 minutes. The follow-up; what landed in 3.13. Free.
- **Lukasz Langa — keynote at PyCon US 2024 on free-threaded Python** — ~45 minutes. The implementation perspective. Free.
- **Donghee Na — "Implementing free-threading in 3.13"** (PyCon US 2024) — ~30 minutes. The technical changes to dict/list internals. Free.
- **"Python 3.13 free-threading" — Faster CPython blog** — <https://faster-cpython.github.io/>. Periodic updates from the Faster CPython team on the free-threaded build's performance. Free.
- **The PEP 703 reference repository** — <https://github.com/colesbury/nogil>. Sam Gross's original `nogil` fork. The reference implementation; the historical record.

### The subinterpreter explainers

- **Eric Snow — "A Per-Interpreter GIL: Concurrency and Parallelism with Subinterpreters"** (PyCon US 2023) — ~30 minutes. Free.
- **Anthony Shaw — "Subinterpreters: Python 3.12 and beyond"** (PyCon AU 2023) — ~40 minutes. Free.
- **"Python's New Subinterpreter Support: A Quick Tour"** — Real Python (2024) — <https://realpython.com/python313-subinterpreters/>. Free. The practitioner's introduction.

## Reference implementations (read after you have written your own)

- **`Lib/concurrent/futures/thread.py`** — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/thread.py>. About 250 lines. The reference implementation of `ThreadPoolExecutor`. Worth a careful read.
- **`Lib/concurrent/futures/process.py`** — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/process.py>. About 800 lines. The reference implementation of `ProcessPoolExecutor`. Has interesting code for handling pickle errors and worker crashes.
- **`Lib/asyncio/base_events.py`** — <https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py>. About 2,000 lines. The reference event loop. The single hardest stdlib module to read; do not start here.
- **`Lib/asyncio/tasks.py`** — <https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py>. About 1,000 lines. `asyncio.Task`, `asyncio.gather`, `asyncio.TaskGroup`. The reference for high-level asyncio.
- **`Lib/multiprocessing/process.py`** — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/process.py>. About 400 lines. The reference `Process` class.
- **`Lib/multiprocessing/shared_memory.py`** — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/shared_memory.py>. About 500 lines. The reference shared-memory implementation.
- **`Lib/interpreters/__init__.py` and `Lib/concurrent/interpreters/__init__.py` (3.13+)** — <https://github.com/python/cpython/tree/main/Lib/interpreters>. About 600 lines. The Python-level wrapper around the C-API subinterpreter machinery.

## Third-party libraries (production-grade examples)

- **`uvloop`** — <https://github.com/MagicStack/uvloop>. A drop-in replacement for the asyncio event loop, written in Cython on top of libuv. About 2-4x faster than the stdlib loop on most I/O workloads. Install: `pip install uvloop`. Free. The reference implementation for "what an optimised event loop looks like."
- **`trio`** — <https://github.com/python-trio/trio>. The structured-concurrency-first alternative to asyncio. The reference for what `asyncio.TaskGroup` borrowed from. Documentation: <https://trio.readthedocs.io/>. Free.
- **`anyio`** — <https://github.com/agronholm/anyio>. A compatibility shim that lets a library work on both asyncio and trio. The reference for cross-event-loop code. Free.
- **`gevent`** — <http://www.gevent.org/>. The greenlet-based concurrency library; a historical alternative to asyncio. Worth knowing exists; do not write new code against it in 2026.
- **`ray`** — <https://www.ray.io/>. Distributed multiprocessing. The reference for "multiprocessing scaled past one host." Free for open use.
- **`dask`** — <https://www.dask.org/>. The other distributed-multiprocessing library; the reference for the data-science end of the spectrum. Free.
- **`joblib`** — <https://joblib.readthedocs.io/>. The lightweight alternative to `ProcessPoolExecutor`; pickles smartly with memmap support. Free.

## Free talks (watch one or two)

- **Sam Gross — "Per-Interpreter GIL and Beyond"** (PyCon 2023) — search YouTube. The PEP 703 explainer. Free. Top priority.
- **David Beazley — "Inside the Python GIL"** (PyCon 2009) — <https://www.dabeaz.com/python/UnderstandingGIL.pdf> (slides; talk is on YouTube). About 60 minutes. Old but still the clearest explanation of *why* the GIL exists. Free.
- **David Beazley — "Generators, Coroutines, Native Threads, Asyncio: Going Beyond Pyalgo"** (PyCon 2015) — search YouTube. About 60 minutes. The reference talk for how Python concurrency primitives compose. Free.
- **Yury Selivanov — "Asyncio in Python 3.7 and Beyond"** (PyCon 2018) — search YouTube. About 45 minutes. Free.
- **Lukasz Langa — keynote PyCon 2024 on free-threaded Python** — search YouTube. About 45 minutes. Free.
- **Anthony Shaw — "Subinterpreters"** (PyCon AU 2023) — search YouTube. About 40 minutes. Free.
- **Raymond Hettinger — "Thinking About Concurrency"** (PyCon Russia 2016) — <https://www.youtube.com/watch?v=Bv25Dwe84g0>. About 45 minutes. The reference talk on `threading.Lock` discipline. Free.
- **Aaron Patterson — "Threads aren't evil"** (RubyConf 2019, but applies to Python) — covers the same conceptual territory in a different language. Free.

## Books (if you have one already; nothing to buy)

- **"Python Concurrency with asyncio"** by Matthew Fowler, Manning 2022. The textbook reference for asyncio in production. If your university has access; do not buy unless you want to keep it.
- **"High Performance Python"** by Micha Gorelick and Ian Ozsvald, 2nd edition, O'Reilly 2020. Chapters 9-10 ("The multiprocessing Module," "Clusters and Job Queues") are the multiprocessing reference. Older but largely still correct.
- **"Effective Python"** by Brett Slatkin, 3rd edition, Addison-Wesley 2024. Items 53-66 cover concurrency. The pragmatic reference; quick chapters, well-organised.
- **"Fluent Python"** by Luciano Ramalho, 2nd edition, O'Reilly 2022. Chapters 19-21 cover concurrency. The textbook-quality reference.

## Blogs and articles

- **"The C10K problem"** by Dan Kegel (1999, periodically updated) — <http://www.kegel.com/c10k.html>. The historical problem statement that motivated all of modern concurrency. Required reading once, ever; it is the "why" behind every event loop ever shipped.
- **"How the heck does async/await work in Python 3.5?"** by Brett Cannon (2016) — <https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/>. The deep dive on the `__await__` protocol. Free.
- **"asyncio: a hands-on walkthrough"** by Brad Solomon on Real Python — <https://realpython.com/async-io-python/>. Free. The standard practitioner's introduction.
- **"Speed Up Your Python Program With Concurrency"** by Jim Anderson on Real Python — <https://realpython.com/python-concurrency/>. Free. The standard concurrency-for-beginners explainer; covers the four-model comparison at a beginner level.
- **"Things I Wish Someone Had Told Me About Python Threading"** by Will McGugan (2024) — find via Will's blog at <https://www.willmcgugan.com/>. The "lessons learned" essay; covers `threading.local`, GIL release, and the canonical mistakes.
- **"Notes on the GIL"** by Larry Hastings (2015, the "Gilectomy" attempt) — search "Hastings Gilectomy PyCon." The failed precursor to PEP 703. Worth knowing the history.
- **"Coroutines and async/await for the working programmer"** by James Bennett (2019) — <https://www.b-list.org/weblog/2019/jun/03/python-async/>. Free.

## Tooling

- **`asyncio.run(main(), debug=True)`** — turns on coroutine-leak warnings, slow-callback warnings, and unconsumed-task warnings. Set `PYTHONASYNCIODEBUG=1` as an environment variable for the same effect. The single most useful asyncio diagnostic flag. Free; built in.
- **`psutil`** — <https://pypi.org/project/psutil/>. The cross-platform process-inspection library. Used in the benchmark for resident memory. Install: `pip install psutil`. Free.
- **`py-spy`** — <https://github.com/benfred/py-spy>. The sampling profiler that does not require modifying the target program. Install: `pip install py-spy`. Free. The right tool for "this asyncio app is mysteriously slow; what's blocking the loop?"
- **`viztracer`** — <https://github.com/gaogaotiantian/viztracer>. Trace visualiser; understands asyncio coroutines as first-class entities. Install: `pip install viztracer`. Free.
- **`memray`** — <https://github.com/bloomberg/memray>. Bloomberg's memory profiler; handles multiprocess targets. Install: `pip install memray`. Free.
- **`tracemalloc`** — stdlib, <https://docs.python.org/3/library/tracemalloc.html>. The benchmark uses it for per-instance memory. No install.
- **`timeit`** — stdlib, <https://docs.python.org/3/library/timeit.html>. The benchmark uses it for class-creation and instance-creation time. No install.
- **`hyperfine`** — <https://github.com/sharkdp/hyperfine>. Rust-written benchmarking CLI; runs your script N times and reports a confidence interval. Install: via your package manager (`brew install hyperfine`, `apt install hyperfine`). Free. The right tool when you want to compare two binaries from outside the process.
- **`uv`** — <https://github.com/astral-sh/uv>. The Astral Python installer. `uv python install 3.13t` installs the free-threaded build of 3.13 alongside the stock build. Free. The cleanest way to get free-threaded Python in 2026.

## Diagnosis cookbook (when something goes wrong)

| Symptom | Likely cause | Reference |
|---------|--------------|-----------|
| Threads slower than serial on pure-Python CPU work | GIL serialised the work | PEP 703 motivation |
| Threads exactly as fast as serial on I/O work | I/O not actually blocking; or the work is too small | `threading` docs |
| Asyncio one-task latency huge, others fine | One coroutine forgot to await; blocked the loop | `asyncio` debug mode |
| Asyncio "Task was destroyed but it is pending" | Forgot to await or cancel a task; use `TaskGroup` | PEP 654 |
| `multiprocessing` worker hangs on Linux after fork | Forked process inherited a held lock | Python docs §"Contexts and start methods" |
| `multiprocessing.Pool` startup very slow on macOS | Default start method changed to `spawn` in 3.8; re-imports everything | Multiprocessing docs |
| `RuntimeError: There is no current event loop` | Called `asyncio.get_event_loop()` outside `asyncio.run` | asyncio.run docs |
| `pickle.PicklingError` from `ProcessPoolExecutor` | Closure or lambda passed as argument; cannot pickle | `pickle` docs |
| `psutil` shows N copies of imports after `multiprocessing` | Expected on `spawn`; each worker re-imports the parent | Multiprocessing docs |
| `interpreters.NotShareableError` | Tried to send a non-shareable type across `interpreters.Queue` | PEP 734 §"Shareable Types" |
| Free-threaded build 20% slower single-threaded | Expected; the cost of removing the GIL on the prototype | PEP 703 §"Performance" |
| C extension crashes on free-threaded build | Extension not yet audited for thread safety; check `Py_GIL_DISABLED` | PEP 703 §"C API" |

## Standards-citation cheat sheet (for the quiz)

| Construct | PEP | Year | Author |
|-----------|----:|-----:|--------|
| `concurrent.futures.Executor` | 3148 | 2009 | Brian Quinlan |
| `asyncio` (original) | 3156 | 2012 | Guido van Rossum |
| `async`/`await` syntax | 492 | 2015 | Yury Selivanov |
| Async generators | 525 | 2016 | Yury Selivanov |
| Async comprehensions | 530 | 2016 | Yury Selivanov |
| Exception groups / `except*` | 654 | 2022 | Irit Katriel |
| Per-interpreter GIL (C-API) | 684 | 2023 | Eric Snow |
| Free-threaded build (`--disable-gil`) | 703 | 2023 | Sam Gross |
| `interpreters` stdlib module | 734 | 2024 | Eric Snow |

## Anti-resources (do not learn from these)

- **Any tutorial dated 2014 or earlier on asyncio.** Pre-PEP 492, asyncio used generator-based coroutines (`@asyncio.coroutine` and `yield from`). The syntax is deprecated and removed; the explanation in those tutorials does not match modern code.
- **"Threading in Python is useless because of the GIL."** Partially correct, very misleading. Threads release the GIL for I/O — that is the overwhelming majority of real Python work. The framing is wrong; the conclusion is wrong.
- **"Use multiprocessing for any speedup."** The pickling tax is real and substantial; on small workloads it can wipe out the parallelism gain. Measure.
- **"Asyncio is faster than threading."** False as a general statement. Asyncio has lower per-task overhead than threading for *I/O-bound* work with *many* tasks; the corollary is not "asyncio is faster" but "asyncio scales further on the same hardware before context-switch cost dominates."
- **"The free-threaded build is the future; use it now."** Half-true. The build is opt-in and several major C extensions are still being audited. For production code in 2026 the stock build is still the right default; for new code and new benchmarks, dual-build CI is the right move.

## Where to ask questions

- **The Python forum** — <https://discuss.python.org/>. The `core-dev` category is where the PEP 703 implementation discussions actually happened.
- **The Python Discord** — <https://pythondiscord.com/>. Active `#async` channel; moderated and helpful.
- **`#python-asyncio` on Libera.Chat IRC** — historical, still active.
- **`r/learnpython`** — for "I have a threadpool and it does X, why?"
- **`r/python`** — for "I have an opinion about asyncio vs trio."
- **The Faster CPython issues tracker** — <https://github.com/faster-cpython/ideas/issues>. Read more than you post; the implementers hang out here.
