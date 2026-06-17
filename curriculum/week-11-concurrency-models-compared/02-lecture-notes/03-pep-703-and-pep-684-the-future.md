# Lecture 3 — PEP 703 (Free-Threaded) and PEP 684 (Subinterpreters)

> The two PEPs that will, between them, redefine how Python concurrency looks by the end of the decade. PEP 703 removes the GIL — the headline change, the one Sam Gross worked on for four years, the one that finally landed in 3.13 as an opt-in `--disable-gil` build. PEP 684 gives each subinterpreter its own GIL — the structural change that arrived as a C-API in 3.12 and a Python-level API (PEP 734) in 3.13. Together they tell you what the next decade of Python concurrency looks like: more threads, more parallelism, less pickling. This lecture is the honest assessment of where the two PEPs stand in May 2026.

## PEP 703: the free-threaded build

The proposal: make the GIL optional. The build is selected at compile time with `--disable-gil` (in 3.13) or, equivalently, `--enable-experimental-free-threading` (the name used in some packaging contexts). The resulting interpreter is binary-incompatible with the standard build — different ABI, different `Py_GIL_DISABLED` preprocessor symbol, different wheel tag (`cp313t` instead of `cp313`). You install it side by side with the stock build; you select it by interpreter path (`/usr/local/bin/python3.13t`) or via tooling (`uv python install 3.13t`).

The semantics:

- **All single-threaded code behaves identically**. The same source compiles, the same bytecode runs, the same results come out.
- **Multi-threaded CPU-bound code scales**. The GIL is not present; threads run in parallel on multiple cores; pure-Python loops actually parallelise.
- **Single-threaded performance regresses by 15–25%** on the 3.13 prototype. This is the cost of changing dict/list/set internals to be thread-safe without a global lock (biased reference counting, deferred reference counting, per-object locks). Sam Gross's PyCon 2024 talk includes the benchmark; the regression is being chipped away by the Faster CPython team each release.
- **C extensions need to opt in**. A C extension built against the stock ABI assumes the GIL is held when it runs. The free-threaded build will refuse to import a C extension unless the extension's module init function sets `Py_mod_gil = Py_MOD_GIL_NOT_USED` (declaring it free-threading-safe) or unless the user passes `PYTHON_GIL=0` (forcing the GIL back on for un-audited extensions).
- **Most pure-Python code "just works"**. The stdlib has been audited. NumPy ≥ 2.1 has free-threading wheels. The major scientific Python stack (NumPy, SciPy, scikit-learn, pandas, polars) has wheels as of late 2024 / early 2025. The long tail of small C extensions is still being audited.

### How the GIL was removed (the engineering)

The GIL existed for one practical reason: CPython's reference counting is not thread-safe without it. Every `Py_INCREF` and `Py_DECREF` on a shared object would race; the reference count could go negative and the object could be freed early; you would get use-after-free crashes. The GIL serialised everything, the reference counts never raced, the heap stayed consistent.

PEP 703 replaces this with four mechanisms:

1. **Biased reference counting**. Each object has an "owner thread." Increments and decrements from the owner thread are non-atomic (cheap). Increments and decrements from other threads use atomic operations (expensive). For the common case — an object is created, used, and destroyed by one thread — there is no atomic overhead.
2. **Deferred reference counting** for cyclic data structures and frequently-shared objects (modules, types, frame objects). These have a tristate: an "immortal" mode (refcount never touched), a "deferred" mode (changes are batched), and a "normal" mode.
3. **`mimalloc` as the allocator**. CPython's default allocator (pymalloc) is not thread-safe without the GIL. PEP 703 swaps it for `mimalloc`, Microsoft's thread-safe arena allocator.
4. **Per-object locks** for dict, list, set, and a few other mutable containers. The dict implementation now has a fine-grained lock per dict; concurrent reads from multiple threads do not block; concurrent writes are serialised on that single dict's lock, not on a global lock.

The result is a CPython that is binary-compatible at the API level (with one exception: extensions must opt in) but ABI-incompatible at the wheel-tag level. Source compatibility is excellent. ABI compatibility is the long pole.

### What works, what does not (May 2026)

**Works on 3.13t**:

- The entire stdlib, including `asyncio`, `multiprocessing`, `threading`.
- NumPy 2.1+, SciPy 1.13+, scikit-learn 1.5+, pandas 2.2+, polars 1.0+.
- Most pure-Python libraries (requests, httpx, click, pydantic, fastapi).
- The `concurrent.futures.ThreadPoolExecutor` — and now it actually scales on CPU work.

**Does not work or is still being audited**:

- TensorFlow as of mid-2025 had partial support; check the project's compatibility page.
- PyTorch had a free-threading audit underway but no production wheels at time of writing.
- Older C extensions that were never updated.
- A handful of stdlib edge cases involving `signal` handling and `os.fork` interactions.

The Faster CPython tracking page <https://faster-cpython.github.io/> publishes a rolling status of free-threading readiness.

### Writing free-threading-safe Python

Most pure-Python code is already free-threading-safe — Python's threading.Lock works the same, dict access is now per-dict-locked, `list.append` is atomic on `mimalloc`. The places to be careful:

1. **Race conditions that the GIL was hiding**. A pattern like `counter += 1` was *almost* atomic on the stock build because the GIL released between bytecodes only at the switch interval (5 ms). On the free-threaded build, the GIL is gone; `counter += 1` is three bytecodes (LOAD, ADD, STORE) and any of them can race with another thread. The fix: use `threading.Lock` or `itertools.count()` (which is atomic in C).
2. **Mutable singletons**. A module-level cache like `_CACHE: dict[str, str] = {}` is now legitimately concurrent. Reads and writes are protected by the dict's per-instance lock, but a `_CACHE.setdefault(k, expensive_compute(k))` is not atomic — the expensive_compute can race with another thread also missing the same key. The fix: use `functools.lru_cache` (which has been updated to be thread-safe), or wrap the setdefault in a lock.
3. **`__slots__` classes with mutable defaults**. Less common, but a `__slots__` class whose `__init__` shares a list among instances has always been wrong; on free-threading the wrongness is more likely to manifest as a race rather than a logical bug.

The good news: the patterns you should already have been writing (locks around shared mutable state, `concurrent.futures` for parallel work, no global mutable singletons in library code) are exactly the patterns that survive free-threading without modification. The patterns that break are the patterns that were always a bit dodgy and were getting away with it on the GIL.

### Performance: when free-threading pays

Sam Gross's PyCon 2024 numbers (and reproducible benchmarks from the Faster CPython team):

| Workload | Stock 3.13 | Free-threaded 3.13 |
|----------|-----------:|-------------------:|
| pyperformance suite (single-threaded) | 1.0x | 0.80–0.85x |
| Fibonacci (recursive, pure Python, 8 threads) | 1.0x (no speedup) | 6.5x |
| Mandelbrot (pure Python, 8 threads) | 1.0x | 7.2x |
| NumPy matmul, 8 threads | 7.0x (GIL released) | 7.1x |
| asyncio HTTP fanout | 1.0x | 0.95x (slight regression from per-task overhead) |

The pattern: free-threading is a regression on single-threaded code and on I/O-bound code, a strong win on multi-threaded CPU work. For workloads where you mostly use 1 core, stay on the stock build. For workloads where you have CPU work and multiple cores, the free-threaded build is now a real option that was not available 18 months ago.

### When to switch

In May 2026, the right operational stance is:

- **Continue to write code that works on both builds.** This is easy; almost all Python code does.
- **Run your CI on both builds.** GitHub Actions has had `python-version: '3.13t'` since late 2024. Catch C-extension incompatibilities at PR time, not at deploy time.
- **Use the free-threaded build for CPU-bound services that you can isolate.** Image processing, data ETL, training-data preprocessing — workloads where you would have reached for `multiprocessing` and you can now use threads.
- **Stay on the stock build for production services until 3.15.** The single-threaded regression is meaningful for I/O-heavy services and the long tail of C extensions is still settling.

The default-on transition (when `--disable-gil` becomes the default and the stock build becomes the opt-in) is expected no earlier than 3.15 (October 2026) and may slip to 3.16 (October 2027). The PEP explicitly does not promise a date; the steering council promised that the transition would not happen until single-threaded performance regression was eliminated and the C-extension long tail was healthy.

## PEP 684 and PEP 734: subinterpreters

The parallel proposal: instead of removing the GIL, replicate it. Each subinterpreter gets its own GIL, its own module dict, its own type system. They share the OS process — same address space, same file descriptors — but they do not share the interpreter state. The C-API for this landed in 3.12 (PEP 684); the Python-level `interpreters` module landed in 3.13 (PEP 734).

The design: a subinterpreter is a Python interpreter inside the same process. It has its own GIL, its own `sys.modules`, its own `builtins`. Two subinterpreters in the same process can execute Python bytecode simultaneously on different cores. Communication between them goes through a restricted set of "shareable" types (PEP 734 §"Shareable Types"): bytes, str, int, float, bool, None, tuples and lists of shareable types, and the `interpreters.Queue` primitive that wraps these in a queue-shaped API.

```python
import interpreters
from typing import Any


def run_in_subinterpreter() -> Any:
    interp: interpreters.Interpreter = interpreters.create()
    q: interpreters.Queue = interpreters.Queue()
    interp.exec(
        """
import sys
result = sum(i * i for i in range(100000))
"""
    )
    interp.close()
    return None
```

The `interpreters.Interpreter` is a handle. The `interp.exec(source)` runs a string of source code in the subinterpreter (with the subinterpreter's own GIL, on a thread of the subinterpreter's choosing). The `interpreters.Queue` is the only way to pass data into or out of the subinterpreter.

### The trade-off curve

Subinterpreters sit between threads and processes on every axis:

| Axis | Threads | Subinterpreters | Processes |
|------|---------|-----------------|-----------|
| GIL contention | Yes (stock) / No (free-threaded) | No (per-interp GIL) | No (per-process GIL) |
| Memory cost per worker | ~64 KB | ~2-4 MB | ~30-60 MB |
| Startup cost | ~100 μs | ~10 ms | 50-300 ms (`spawn`) |
| Data sharing | Direct (same memory) | Shareable types only | Pickle + IPC |
| Crash isolation | None (one crashes, all die) | Partial (one crashes, process may stay alive) | Full (one crashes, others survive) |
| C extension compatibility | Full | Limited (extension must be subinterpreter-safe) | Full |

The pitch: subinterpreters give you parallelism without pickling, at a fraction of the memory cost of multiprocessing, with crash isolation halfway between threads and processes. The cost: a more restricted programming model (shareable types only) and a still-incomplete C-extension audit.

### What subinterpreters are good for (May 2026)

The honest assessment: subinterpreters in 3.13 are *new*. The `interpreters` module is a few hundred lines of Python around a C-API that was finalised in 3.12. The community is still discovering the right patterns. A few use cases have emerged:

1. **Multi-tenant Python embedding**. If you are embedding Python in another application and you want each tenant's code to run in isolation without spawning OS processes, subinterpreters are the right tool. The C-API has been used by `mod_wsgi` and `pyodide` for years; the Python-level API now makes this accessible from Python itself.
2. **CPU-bound parallelism without pickling**. If your workload involves passing strings and numbers between workers and you cannot use the free-threaded build (because of a C extension), subinterpreters can be faster than multiprocessing.
3. **Sandboxed evaluation**. A subinterpreter can be isolated enough that running untrusted-ish code in it is safer than running it in the main interpreter. Not as safe as a separate process (an extension can still crash the host); safer than `eval` in the same interpreter.

What they are **not** good for:

- Anything that requires passing arbitrary Python objects. Shareable types only.
- Anything with a heavy C-extension dependency that has not been audited. Most extensions are not yet subinterpreter-safe.
- Workloads where the per-task work is small. The startup cost of a subinterpreter (~10 ms) dwarfs the benefit for sub-millisecond tasks.

### PEP 554 vs. PEP 734

PEP 554 was the original subinterpreters PEP, opened in 2017. It was *deferred* (not rejected) because the API design was still in flux. PEP 734 is the accepted, shipped form, with an updated API. The `interpreters` module name and the `Queue` primitive come from PEP 734. References to PEP 554 in older blog posts are still mostly correct on the *concept* but use API names that have changed.

If you read about subinterpreters and see `_xxsubinterpreters` (the private C-API module) or `interpreters.run_string()`, you are reading pre-3.13 material. The 3.13 API uses public names: `interpreters.create()`, `Interpreter.exec()`, `interpreters.Queue`.

## The decision tree, updated for 2026

The full table, all five models:

| Workload | Stock 3.13 best | Free-threaded 3.13 best |
|----------|-----------------|--------------------------|
| 1–50 concurrent HTTP calls | Threads | Threads |
| 500–10,000 concurrent HTTP calls | Asyncio | Asyncio |
| CPU-bound pure Python, small data | Multiprocessing | Threads |
| CPU-bound pure Python, large data | Subinterpreters | Threads |
| CPU-bound C-extension (NumPy etc.) | Threads | Threads |
| Multi-tenant embedded Python | Subinterpreters | Subinterpreters |
| Heterogeneous tasks (I/O + CPU mixed) | Asyncio + `to_thread` for CPU | Asyncio + `to_thread` for CPU |

The way to *use* this table: identify the dominant cost (I/O wait time, CPU compute, data volume), identify the build (stock or free-threaded), pick the row. Verify with a benchmark before you commit code.

## What you will build in the mini-project

The mini-project this week is to build the same document-scoring workload five times: serial baseline, `ThreadPoolExecutor`, `asyncio.gather`, `ProcessPoolExecutor`, and `interpreters.Queue`. You will measure throughput, median latency, and resident memory. You will produce a graph and a decision tree.

If you have the free-threaded build installed (you should — `uv python install 3.13t` takes 30 seconds), you will run all five benchmarks twice: once on stock 3.13, once on 3.13t. The 3.13t run is the demonstration that PEP 703 is real: the thread-pool number jumps from "no speedup" to "linear speedup."

That table — the five models, the two builds, the three metrics — is the artefact of this week. Put it on a one-page document. When a teammate asks "how do I make this Python code faster," you hand them the page.

## Further reading

- **PEP 703 — Making the Global Interpreter Lock Optional in CPython** — <https://peps.python.org/pep-0703/>. Sam Gross, 2023.
- **PEP 684 — A Per-Interpreter GIL** — <https://peps.python.org/pep-0684/>. Eric Snow, 2023.
- **PEP 734 — Multiple Interpreters in the Stdlib** — <https://peps.python.org/pep-0734/>. Eric Snow, 2024.
- **PEP 554 — Multiple Interpreters in the Stdlib (deferred)** — <https://peps.python.org/pep-0554/>.
- **`interpreters` docs (3.13+)** — <https://docs.python.org/3/library/interpreters.html>.
- **Sam Gross, "Per-Interpreter GIL and Beyond"** (PyCon 2023, ~30 min). Free on YouTube.
- **Sam Gross, "A Per-Interpreter GIL"** (PyCon 2024, ~30 min). Free on YouTube.
- **Faster CPython tracking page** — <https://faster-cpython.github.io/>. Rolling status.
- **Anthony Shaw, "Subinterpreters: Python 3.12 and beyond"** (PyCon AU 2023, ~40 min). Free.
- **`colesbury/nogil`** — <https://github.com/colesbury/nogil>. Sam Gross's reference prototype.

## Appendix A: the timeline that got us here

A quick history. Skip if you do not care about the politics; read if you want to know why Python concurrency looks the way it does.

- **1989** — Guido begins implementing CPython. The reference-counting garbage collector is the design choice that locks in the GIL.
- **1992** — CPython 0.9.x ships. The GIL is already there.
- **2005** — Greg Stein's "free-threaded Python" patch for 1.4. Made the interpreter 2x slower on single-threaded benchmarks. Rejected.
- **2007** — Adam Olsen's `python-safethread` fork. Similar regression. Rejected.
- **2010-2015** — David Beazley's "Inside the Python GIL" talks educate a generation of Python programmers about the GIL's actual semantics. The community accepts the GIL is real and is here to stay.
- **2015** — Larry Hastings begins the "Gilectomy" project at PyCon. Removes the GIL by adding atomic operations everywhere. Single-threaded performance regresses 25-30%. The project is shelved in 2017; Larry's PyCon talks remain the canonical "here is what is hard about removing the GIL" reference.
- **2017** — Eric Snow opens PEP 554 for stdlib subinterpreters. Defers due to API design questions and lack of C-API support.
- **2021** — Sam Gross publishes the `nogil` fork. Uses biased reference counting, deferred reference counting, mimalloc, per-object locks. Single-threaded regression is ~15% rather than 30%.
- **2023, January** — Sam Gross opens PEP 703.
- **2023, July** — The steering council accepts PEP 703, conditional on (a) closing the single-threaded regression to <10%, (b) demonstrating ecosystem viability.
- **2023, October** — PEP 684 (per-interpreter GIL at the C-API level) ships in 3.12.
- **2024, January** — `--disable-gil` build option lands in CPython main.
- **2024, October** — Python 3.13 ships. `--disable-gil` is opt-in, `cp313t` wheel tag is registered with PyPI. NumPy 2.1 with free-threading support ships the same week.
- **2024, December** — Eric Snow's PEP 734 accepted as the replacement for PEP 554. `interpreters` module added to the stdlib for 3.13.
- **2025** — The Faster CPython team begins systematic work on closing the single-threaded regression. Quarterly status updates on <https://faster-cpython.github.io/>.
- **2026, May (now)** — Single-threaded regression at ~15-20% on representative benchmarks. Ecosystem audit ongoing; ~30% of top-1000 PyPI packages have `cp313t` wheels.
- **2026, October (expected)** — Python 3.14. No default change.
- **2027, October (target)** — Python 3.15. Possible default change to free-threaded build. Steering council has not committed.
- **2028, October (fallback)** — Python 3.16. If 3.15 deferred, 3.16 is the target.

The pattern: 20 years of failed attempts to remove the GIL, two years of successful engineering once the right approach was found. The right approach was *not* "make every operation atomic"; it was "make uncontended operations cheap and contended operations correct." Biased reference counting is the key insight.

## Appendix B: the mental model for free-threaded code

Most pure-Python code is already free-threading-safe. The patterns that break are the patterns that were always a bit racy and were getting away with it due to the GIL's coarse-grained serialisation.

The mental shift: on the stock build, a sequence of bytecodes appears atomic if no I/O or C-extension call happens in the middle. The 5 ms switch interval means that a *single* short Python statement (`counter += 1`) almost never gets preempted. The behaviour is *as if* the GIL were a lock around every "small" Python statement.

On the free-threaded build, this near-atomicity disappears. `counter += 1` is three bytecodes (`LOAD_FAST`, `BINARY_ADD`, `STORE_FAST`), and any of the three can interleave with another thread's execution of the same three bytecodes. The result: classic lost-update races.

The fix is the discipline you should have been practising anyway:

1. **Wrap all shared mutable state in a lock.** `threading.Lock` is the default; `threading.RLock` if you need re-entrancy; `threading.Semaphore` if you need counting; `queue.Queue` if you have a producer-consumer pattern.
2. **Or: use immutable data plus replacement.** Build a new dict/list and assign it. Python's dict assignment is atomic on the free-threaded build (per-dict lock).
3. **Or: use the C-implemented atomics.** `itertools.count()` is atomic. `threading.local()` is per-thread by construction. `collections.deque.append` and `deque.popleft` are atomic.

The patterns that *fail* on the free-threaded build are the patterns that were never actually safe — they just appeared safe under the GIL's serialisation. Migrating to free-threaded does not break correct code; it reveals always-incorrect code.

## Appendix C: when subinterpreters do not buy you what you wanted

Subinterpreters look like the best of both worlds: parallelism without pickling, isolation without process overhead. The reality is more nuanced. Three places where the model leaks.

**One: third-party C extensions need explicit support.** A C extension is loaded once per interpreter; subinterpreters do not share imported modules. If the extension uses module-level state (a static variable in C), each subinterpreter sees its own copy. If the extension uses *process-level* state (a thread-local or a process-global), subinterpreters share it and the GIL no longer protects it. Extensions need to be audited for subinterpreter compatibility separately from free-threading compatibility. The audit is more invasive — most C extensions assume "one Python interpreter per process" implicitly.

**Two: the shareable-types list is short.** `bytes`, `str`, `int`, `float`, `bool`, `None`, tuples and lists of these, and `memoryview` over bytes. That is the list. Sets, dicts, custom classes, NumPy arrays, dataclasses — none of these can cross. To pass a dict between subinterpreters, you must serialise to (key-tuple, value-tuple) and rebuild on the other side. This is structurally similar to pickle, just with a smaller set of acceptable types. Some workloads fit; many do not.

**Three: startup is real.** A subinterpreter takes ~10 ms to spin up in 3.13. The startup cost is the import system running again — every `import threading`, `import sys`, etc. that your worker code needs. For long-running workers this is fine; for short-lived workers (sub-100 ms tasks), the startup cost dominates.

The right mental model for subinterpreters in 2026: a third option that wins for a narrow band of workloads (CPU-bound, shareable-typed data, long-running workers). For workloads outside that band, threads or processes remain the right answer.

## Appendix D: what about `nogil` in other languages?

Python is not the first language to attempt removing a global interpreter lock. The lessons from elsewhere:

- **Ruby's GVL** (Global VM Lock) was the analogue. Ruby 3.0 (2020) introduced Ractors — Ruby's subinterpreters. Same trade-off: per-Ractor lock, shareable-types restriction. Adoption has been slow because most Ruby code uses mutable shared state, which Ractors forbid.
- **OCaml 5** (2022) introduced effect handlers and a multi-domain runtime. The single-threaded regression was minimal because OCaml's existing runtime had less GIL-dependent code than CPython's.
- **JavaScript** never had a GIL — V8 is single-threaded by design, and Worker Threads run in isolated contexts that communicate by structured cloning (analogous to pickle).
- **Go and Rust** were designed from the start with no global lock; their concurrency primitives are the standard.

The pattern across languages: removing a GIL is hard precisely when the language semantics implicitly relied on it. CPython relied on the GIL for reference counting; Ruby relied on it for VM-level invariants. The languages without a GIL did not pay the migration cost. The languages with one are paying it now.

For Python specifically, the engineering decision in PEP 703 is: rather than rewrite Python's semantics to not need the GIL (the Ruby/OCaml route), keep the semantics and rebuild the runtime to make them work without a single global lock. This is more conservative; it preserves backward compatibility at the cost of more complex internals. Whether that was the right trade is a question for 2028, when we will see how many third-party C extensions actually made the audit and how many were quietly abandoned.
