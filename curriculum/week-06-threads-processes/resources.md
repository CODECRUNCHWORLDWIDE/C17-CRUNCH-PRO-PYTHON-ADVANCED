# Week 6 — Resources

All free. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — CPython source tree

| What | Where |
|------|-------|
| **`threading` module (Thread, Lock, Event, Condition, Semaphore)** | `Lib/threading.py` — <https://github.com/python/cpython/blob/main/Lib/threading.py> |
| **`_thread` low-level (OS-thread creation, `allocate_lock`)** | `Modules/_threadmodule.c` — <https://github.com/python/cpython/blob/main/Modules/_threadmodule.c> |
| **The GIL (acquire/release, eval-breaker)** | `Python/ceval_gil.c` — <https://github.com/python/cpython/blob/main/Python/ceval_gil.c> |
| **`concurrent.futures` base (`Future`, `Executor`)** | `Lib/concurrent/futures/_base.py` — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/_base.py> |
| **`ThreadPoolExecutor`** | `Lib/concurrent/futures/thread.py` — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/thread.py> |
| **`ProcessPoolExecutor` (the call-queue / result-queue / manager-thread design)** | `Lib/concurrent/futures/process.py` — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/process.py> |
| **`multiprocessing` package root** | `Lib/multiprocessing/` — <https://github.com/python/cpython/tree/main/Lib/multiprocessing> |
| **`multiprocessing.Process`** | `Lib/multiprocessing/process.py` — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/process.py> |
| **`multiprocessing.Pool`** | `Lib/multiprocessing/pool.py` — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/pool.py> |
| **Start methods (`fork`, `spawn`, `forkserver`)** | `Lib/multiprocessing/context.py` — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/context.py> |
| **`multiprocessing.Queue` (IPC)** | `Lib/multiprocessing/queues.py` — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/queues.py> |
| **`multiprocessing.shared_memory` (3.8+)** | `Lib/multiprocessing/shared_memory.py` — <https://github.com/python/cpython/blob/main/Lib/multiprocessing/shared_memory.py> |
| **`asyncio.loop.run_in_executor` (the async / sync bridge)** | `Lib/asyncio/base_events.py:BaseEventLoop.run_in_executor` — <https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py> |
| **`sys._is_gil_enabled()` (3.13+)** | `Python/sysmodule.c` — <https://github.com/python/cpython/blob/main/Python/sysmodule.c> |
| **`sysconfig.get_config_var('Py_GIL_DISABLED')`** | `Lib/sysconfig.py` — <https://github.com/python/cpython/blob/main/Lib/sysconfig.py> |

## Required PEPs

- **PEP 3148 — `concurrent.futures` — Execute Computations Asynchronously** (Brian Quinlan, 2009; landed 3.2): <https://peps.python.org/pep-3148/>
  *The motivation document for `Executor`, `Future`, `submit`, `map`, `as_completed`. The unified surface that lets `ThreadPoolExecutor` and `ProcessPoolExecutor` be a one-line swap. Required reading; ~20 minutes.*
- **PEP 703 — Making the Global Interpreter Lock Optional in CPython** (Sam Gross, 2023; accepted; rolling out via 3.13–3.15 free-threaded build): <https://peps.python.org/pep-0703/>
  *The keystone proposal of this week. §1 (Motivation) and §2 (Rationale) are mandatory; §5 (Implementation) — biased reference counting, deferred reference counting, per-object locks — is dense but rewarding. ~75 minutes for full read; 30 minutes for §§1–3.*
- **PEP 711 — PyBI: A Standard Format for Distributing Python Binaries** (Smith, 2023; informational): <https://peps.python.org/pep-0711/>
  *Background only. Relevant because `uv` and `python-build-standalone` use a PyBI-shaped format to ship the free-threaded 3.13t build. Skim §1 to know what you are downloading.*
- **PEP 371 — Addition of the `multiprocessing` package** (Jesse Noller, 2008; landed 2.6; historical): <https://peps.python.org/pep-0371/>
  *Background. The original rationale for `multiprocessing` ("a threading-like API that bypasses the GIL"). Read §1 only; ~5 minutes. Note: the API has evolved substantially since.*
- **PEP 8 — `__name__ == "__main__"` guard** (not a PEP per se, but a stdlib convention): <https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods>
  *Why every `multiprocessing` example begins with `if __name__ == "__main__":`. Critical for portability across `fork`, `spawn`, and `forkserver`.*

## Stdlib docs

- **`threading` module:** <https://docs.python.org/3/library/threading.html>
- **`concurrent.futures` module:** <https://docs.python.org/3/library/concurrent.futures.html>
- **`multiprocessing` module:** <https://docs.python.org/3/library/multiprocessing.html>
- **`multiprocessing` — contexts and start methods:** <https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods>
- **`multiprocessing.shared_memory`:** <https://docs.python.org/3/library/multiprocessing.shared_memory.html>
- **`asyncio.loop.run_in_executor`:** <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor>
- **3.13 What's New — Free-Threaded CPython:** <https://docs.python.org/3/whatsnew/3.13.html#free-threaded-cpython>
- **3.13 What's New — Experimental JIT (Tier 2; adjacent):** <https://docs.python.org/3/whatsnew/3.13.html#an-experimental-just-in-time-jit-compiler>
- **`sys._is_gil_enabled()` (3.13+):** <https://docs.python.org/3/library/sys.html#sys._is_gil_enabled>

## Free-threaded build resources

The 3.13t build is new (October 2024 release). The ecosystem is moving weekly; bookmark these.

- **Python 3.13 release notes — Free-Threaded CPython section:** <https://docs.python.org/3/whatsnew/3.13.html#free-threaded-cpython>
- **The HOWTO for free-threaded Python:** <https://docs.python.org/3/howto/free-threading-python.html>
- **The C-extension HOWTO for free-threaded support:** <https://docs.python.org/3/howto/free-threading-extensions.html>
- **`py-free-threading.github.io` — community status tracker for free-threaded packages:** <https://py-free-threading.github.io/>
- **Sam Gross's PyCon 2024 talk "Python without the GIL"** (video): <https://www.youtube.com/results?search_query=sam+gross+python+without+the+gil+pycon+2024>
- **Łukasz Langa's PyCon Italia 2024 talk on 3.13** (video, lighter intro): same channel.
- **The free-threaded NumPy story** (in-progress as of early 2026): <https://numpy.org/doc/stable/release.html> — search for "free-threaded" in recent releases.

## `joblib` and `loky` — the production toolkit

scikit-learn, pandas, and most scientific-Python parallel code goes through joblib. Loky is its modern default backend. Knowing both well is table stakes for any DS-adjacent Python role.

- **joblib docs:** <https://joblib.readthedocs.io/en/stable/>
- **joblib parallel-execution overview:** <https://joblib.readthedocs.io/en/stable/parallel.html>
- **joblib `Parallel` API:** <https://joblib.readthedocs.io/en/stable/generated/joblib.Parallel.html>
- **joblib `Memory` (transparent disk caching):** <https://joblib.readthedocs.io/en/stable/memory.html>
- **loky README:** <https://github.com/joblib/loky/blob/master/README.rst>
- **loky `get_reusable_executor`:** <https://loky.readthedocs.io/en/stable/API.html#loky.get_reusable_executor>
- **scikit-learn's parallel-execution guide (production case study):** <https://scikit-learn.org/stable/computing/parallelism.html>

## Background reading — the canon

- **Larry Hastings, *The Gilectomy and Beyond* (PyCon 2017, video + slides):** <https://lwn.net/Articles/723514/>
  *The previous serious GIL-removal attempt. Gross's PEP 703 is the third generation; reading Hastings's notes shows you what changed in approach.*
- **David Beazley, *Understanding the Python GIL* (PyCon 2010):** <https://www.dabeaz.com/python/UnderstandingGIL.pdf>
  *The classic 40-page deep dive. Predates 3.2's "new GIL," but the diagrams and the convoy-effect explanation are unmatched.*
- **David Beazley, *Generators: The Final Frontier* (2014):** <https://www.dabeaz.com/finalgenerator/FinalGenerator.pdf>
  *Tangential, but illuminating on the thread vs. coroutine dichotomy.*
- **Glyph Lefkowitz, *Unyielding* (2014):** <https://glyph.twistedmatrix.com/2014/02/unyielding.html>
  *Pre-async/await argument for explicit yields. The Twisted-era case for *not* using threads. Aged but still sharp.*
- **Raymond Hettinger, *Thinking About Concurrency* (PyCon 2017):** <https://www.youtube.com/results?search_query=raymond+hettinger+thinking+about+concurrency>
  *Practical patterns for threading + queues. The `ThreadPoolExecutor` examples are still the right shape in 2026.*
- **Sam Gross, *A Per-Interpreter GIL: Status Report* (PyCon 2023):** <https://lwn.net/Articles/938704/>
  *PEP 684 (per-interpreter GIL) is the *other* concurrency story for 3.13. Tangentially relevant — covered in Week 3.*
- **`uvloop` blog, *Asynchronous Python at GitHub-scale* (2020):** <https://magic.io/blog/uvloop-blazing-fast-python-networking/>
  *The case for `asyncio` over threads in production IO-bound services.*
- **scikit-learn issue tracker — search for "loky":** <https://github.com/scikit-learn/scikit-learn/issues?q=loky>
  *Real-world failure modes of process pools. Read three issues; you will recognise patterns.*

## Adjacent libraries (worth knowing exist; skim, don't dive)

- **`ray`** — distributed Python; abstracts processes and machines uniformly. The actor model meets futures. <https://docs.ray.io/>
- **`dask`** — lazy, parallel, distributed pandas/NumPy. `dask.delayed` is a familiar shape if you have used joblib. <https://docs.dask.org/>
- **`mpire`** — a more ergonomic `multiprocessing.Pool` with built-in tqdm, exception forwarding, dashboard. <https://github.com/sybrenjansen/mpire>
- **`pebble`** — `multiprocessing.Pool` with proper timeout support per task. <https://github.com/noxdafox/pebble>
- **`cloudpickle`** — extends pickle to handle lambdas, closures, locally-defined classes. Used by `loky` and `ray`. <https://github.com/cloudpipe/cloudpickle>
- **`anyio`** — bridges `asyncio` and `trio` with a structured-concurrency API. `anyio.to_thread.run_sync` is the cross-backend `run_in_executor`. <https://anyio.readthedocs.io/>

## Tools used this week

- **`threading`, `concurrent.futures`, `multiprocessing` (stdlib)** — no install.
- **`asyncio` (stdlib)** — no install. Used in Exercises 2 and 3, the mini-project.
- **`joblib`** — `pip install joblib`. Used in Lecture 2 and the mini-project.
- **`aiohttp`** — `pip install aiohttp`. Used in Exercise 2 and the mini-project's IO-bound workload.
- **`psutil`** — `pip install psutil`. Used to measure memory footprint in the mini-project.
- **`requests`** — `pip install requests`. Used in the thread-pool variant of the IO-bound workload (the deliberately blocking baseline).
- **CPython 3.13t (free-threaded)** — optional but recommended. Install with `uv python install 3.13t` (if your `uv` version supports it) or build from source.
- **`pytest`** — for the homework tests. `pip install pytest`.

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `Thread.start` (creates an OS thread via `_thread.start_new_thread`) | `Lib/threading.py:Thread.start` |
| `Thread.run` (the user's target callable; runs under the GIL) | `Lib/threading.py:Thread.run` |
| The eval-loop GIL drop (`eval_breaker`) | `Python/ceval.c` — search for `eval_breaker` and `take_gil` |
| `take_gil` / `drop_gil` | `Python/ceval_gil.c` — bottom of the file |
| `ThreadPoolExecutor._adjust_thread_count` (lazy worker creation) | `Lib/concurrent/futures/thread.py:_adjust_thread_count` |
| `ThreadPoolExecutor._worker` (the worker loop) | `Lib/concurrent/futures/thread.py:_worker` |
| `ProcessPoolExecutor._launch_processes` | `Lib/concurrent/futures/process.py:_launch_processes` |
| `ProcessPoolExecutor._queue_management_worker` (the manager thread) | `Lib/concurrent/futures/process.py:_queue_management_worker` |
| `multiprocessing.Process.start` | `Lib/multiprocessing/process.py:BaseProcess.start` |
| `multiprocessing.get_context` (choosing start method) | `Lib/multiprocessing/context.py:get_context` |
| `SpawnProcess._launch` (the `spawn` worker bootstrap) | `Lib/multiprocessing/popen_spawn_posix.py:Popen.__init__` |
| `ForkServerProcess._launch` (the `forkserver` worker bootstrap) | `Lib/multiprocessing/popen_forkserver.py:Popen.__init__` |
| `Pool._handle_tasks` (the pool dispatcher) | `Lib/multiprocessing/pool.py:Pool._handle_tasks` |
| `BaseEventLoop.run_in_executor` (the asyncio bridge) | `Lib/asyncio/base_events.py:BaseEventLoop.run_in_executor` |
| `sys._is_gil_enabled` (3.13+) | `Python/sysmodule.c` — function `sys_is_gil_enabled` |
| `Py_GIL_DISABLED` macro (the build flag) | `Include/internal/pycore_runtime.h` and many call sites |

## Glossary

| Term | Definition |
|------|------------|
| **CPU-bound** | A workload whose runtime is dominated by computation, not waiting. The GIL is held throughout. Examples: hashing, encoding, pure-Python loops, regex over very large strings. |
| **IO-bound** | A workload whose runtime is dominated by waiting on external resources (network, disk, database). The GIL is released during the wait. Examples: HTTP, file reads, DB queries. |
| **Mixed** | A workload that alternates between CPU and IO phases. Examples: fetch then parse, fetch then hash. The right primitive depends on the dominant phase. |
| **GIL (Global Interpreter Lock)** | The mutex that serialises Python bytecode execution in default CPython. Released across IO and across `Py_BEGIN_ALLOW_THREADS` blocks in C extensions. Removed (optionally) in 3.13t. |
| **Free-threaded build / 3.13t** | The CPython build configured with `--disable-gil`. Per PEP 703 (Gross 2023). Binary distributions tagged with the `t` suffix (e.g., `python3.13t`). |
| **`concurrent.futures.Executor`** | The PEP 3148 base class for `ThreadPoolExecutor` and `ProcessPoolExecutor`. The `submit() -> Future` and `map()` surface is identical across both, by design. |
| **`Future`** | A handle to a result that does not yet exist. `Future.result()` blocks; `Future.add_done_callback(fn)` does not. Both `concurrent.futures.Future` and `asyncio.Future` exist; they are related but not identical (the asyncio one is awaitable). |
| **`as_completed(futures)`** | An iterator over futures that yields them in completion order, not submission order. Used to stream results as they finish. |
| **`fork` (start method)** | Linux-only on practical workstations. The child process inherits a copy-on-write view of the parent's memory. Fast (~1ms). Unsafe with threads in the parent (POSIX-level). |
| **`spawn` (start method)** | The default on macOS and Windows since 3.8 / 3.4. A fresh Python interpreter is started; the target callable and arguments are pickled across. Slow (~50–200ms). Required for the `multiprocessing` module to work reliably on non-Linux platforms. |
| **`forkserver` (start method)** | A Linux/macOS hybrid. A dedicated server process is started once; subsequent worker creation forks from the server (cheap) rather than from the main process (which may hold large state). |
| **Pickle tax** | The cost of serialising arguments to and return values from a worker process via `pickle`. Per task. Can dominate for small tasks or large payloads. |
| **`__name__ == "__main__"` guard** | Required for `multiprocessing` to work on `spawn` and `forkserver` start methods. Without it, the worker re-imports the script as `__main__` and recursively spawns processes. |
| **`run_in_executor`** | `asyncio` event-loop method that runs a sync callable in a thread or process executor. The asyncio-to-blocking-library bridge. Returns an awaitable. |
| **`joblib.Parallel`** | The scientific-Python idiom for embarrassingly-parallel work. `Parallel(n_jobs=N, backend=...)( delayed(f)(x) for x in xs )`. |
| **`loky`** | The process-pool backend joblib uses by default (replacing the flakier `multiprocessing.Pool`). Adds reusable executors, robust exception forwarding, worker timeouts. |
| **`cloudpickle`** | Extension of `pickle` that handles lambdas, closures, locally-defined classes, partial functions. Required when sending closures to worker processes. |
| **Biased reference counting** | The PEP 703 §5.1 design that lets single-threaded refcount updates remain non-atomic (fast) while cross-thread refcount updates pay an atomic cost. The keystone trick that makes the free-threaded build close to the GIL build on single-threaded throughput. |
| **`Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`** | C-API macros that release / re-acquire the GIL around a blocking call in a C extension. The reason `requests` (under the hood) and `hashlib` are good citizens for threading. |
| **The colored-function problem** | Bob Nystrom 2015. Once a function is `async def`, every caller must be `async def`. Re-raised here because `asyncio` only solves IO concurrency for code you can re-paint async; `threading` does not have this constraint. |
| **The decision tree** | The one-page artifact you will commit to memory: CPU + pure Python → process pool or 3.13t threads; CPU + GIL-releasing C → thread pool; IO + greenfield → async; IO + blocking library → thread pool; mixed → thread pool or async + `run_in_executor`. |

---

*Broken link? Open an issue.*
