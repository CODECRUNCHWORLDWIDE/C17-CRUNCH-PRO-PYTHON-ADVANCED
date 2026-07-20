# C17 · Crunch Pro Python Advanced — Full Syllabus

**12 weeks · ~432 hours full-time · ~36 hrs/week · Senior Python → open-source maintainer caliber**

This is the **table of contents** for the entire C17 track. Each week links to a detailed README with objectives, materials, exercises, challenges, a quiz, homework, and a mini-project that builds toward your capstone open-source contribution.

---

## Program at a glance

| Phase | Weeks | Outcome |
|-------|-------|---------|
| **Phase 1 — The Python Runtime** | 01 – 03 | Read CPython source, understand bytecode, the GIL, memory |
| **Phase 2 — Concurrency** | 04 – 06 | asyncio, threads, processes, the right tool for each |
| **Phase 3 — Performance & Native Code** | 07 – 09 | Profiling, vectorization, Cython, ctypes, free-threaded Python |
| **Phase 4 — Frontier Topics** | 10 – 12 | Advanced typing, PyTorch, Python security, capstone |

---

## How the weekly load adds up

| Component | hrs/wk |
|-----------|------:|
| Lectures / readings | 6 |
| Hands-on exercises | 8 |
| Coding challenges | 4 |
| Quiz + readings | 3 |
| Homework problems | 6 |
| Mini-project | 7 |
| Self-study & review | 2 |
| **Total** | **36** |

---

## Weekly breakdown

### Phase 1 — The Python Runtime

#### [Week 1 — CPython Internals and the Mental Model](week-01-cpython-internals-and-the-mental-model/)

What is `python`? Where does it live on your disk? What happens when you type `python script.py`? The CPython source tree tour. The compilation pipeline: source → AST → bytecode. The `dis` module. Reading a `.pyc` file.

- **Mini-project:** Write a 50-line "Python explainer" that takes any `.py` file, prints its tokens, AST, and bytecode side by side.

#### [Week 2 — The Object Model: Refcounting, GC, Memory](week-02-object-model-refcounting-gc-memory/)

How `id()` actually works. Reference counting line by line. The cyclic garbage collector. `__slots__`, `weakref`, `gc.get_referrers`. Tools: `tracemalloc`, `objgraph`, `memray`. Why generators leak when you think they don't.

- **Mini-project:** Detect a memory leak in a real (small) open-source project and produce a 1-page memo with `memray` flamegraphs.

#### [Week 3 — Bytecode, the Stack Machine, and the GIL](week-03-bytecode-stack-machine-gil/)

The CPython evaluation loop. `LOAD_FAST` vs. `LOAD_GLOBAL` (and why globals are slower). What the GIL actually protects. PEP 703 (no-GIL / free-threaded build). The 3.13 subinterpreters story.

- **Mini-project:** A 100-line CPython bytecode "tracer" that prints each instruction as your code executes, using `sys.settrace`/`sys.monitoring`.

---

### Phase 2 — Concurrency

#### [Week 4 — `asyncio` from First Principles](week-04-asyncio-first-principles/)

Build an event loop from scratch in <200 lines. Coroutines vs. generators. Tasks, futures, awaitables. The "colored function" debate. `gather`, `wait`, `TaskGroup`, `as_completed`.

- **Mini-project:** Implement a *toy* `asyncio` clone with `sleep`, `gather`, `Task`, `run` — enough to run a small program against it.

#### [Week 5 — Structured Concurrency, Cancellation, Back-Pressure](week-05-structured-concurrency-cancellation-backpressure/)

Why nurseries (Trio) and `TaskGroup` (asyncio 3.11+) are a step forward. Cancellation, timeouts, `shield`. Back-pressure: bounded queues, `asyncio.Semaphore`. Reading and writing async iterators correctly.

- **Mini-project:** A robust async web crawler that respects robots.txt, handles cancellation cleanly, and applies back-pressure to a sink.

#### [Week 6 — Threads, Processes, and When to Use What](week-06-threads-processes-when-to-use-what/)

`threading`, `concurrent.futures`, `multiprocessing`, `joblib`, the `loky` backend. CPU- vs. IO-bound. When `multiprocessing` is the wrong answer. The 3.13 free-threaded build: how to think about it.

- **Mini-project:** Convert one CPU-bound task to multiprocessing, one IO-bound task to async, one mixed to thread-pool — and measure each.

---

### Phase 3 — Performance & Native Code

#### [Week 7 — Profiling Like It's Your Job](week-07-profiling-like-its-your-job/)

`cProfile` deterministic profiling. `py-spy` sampling. `austin`. `scalene` for CPU+memory together. Reading flamegraphs. Avoiding microbenchmark traps. `timeit` gotchas.

- **Mini-project:** Take an intentionally slow real-world script (provided), find the bottleneck, document the fix, prove the win.

#### [Week 8 — NumPy / Vectorization / SIMD](week-08-numpy-vectorization-simd/)

Why a `for` loop over a NumPy array is slow. Broadcasting. View vs. copy. `numpy.einsum`. SIMD on modern CPUs. The cost of dtype conversions. A taste of JAX/PyTorch tensors as the next step up.

- **Mini-project:** Rewrite a pure-Python image-processing function with NumPy. Beat the original by ≥100× and document the steps.

#### [Week 9 — C Extensions: ctypes, cffi, Cython, PyO3](week-09-c-extensions-ctypes-cffi-cython-pyo3/)

When pure Python isn't fast enough. `ctypes` for quick wraps. `cffi` for production wraps. Cython for "Python with types becomes C." A short look at `PyO3` (Rust). When to NOT write a C extension.

- **Mini-project:** Wrap a C function (`libc.h` `strlen` will do for warm-up) three ways — `ctypes`, `cffi`, `Cython` — and write up the tradeoffs.

---

### Phase 4 — Frontier Topics

#### [Week 10 — Advanced Typing: Generics, Protocols, ParamSpec](week-10-advanced-typing-generics-protocols-paramspec/)

`TypeVar`, `Generic[T]`, `Protocol`, `runtime_checkable`, `TypeGuard`, `ParamSpec`, `assert_type`, `Self`, structural vs. nominal subtyping. When type hints actually catch bugs.

- **Mini-project:** Take a real Django/FastAPI codebase (or a substantial one of your own) and make `mypy --strict` pass on at least one module.

#### [Week 11 — Deep Learning with PyTorch (Just Enough)](week-11-deep-learning-with-pytorch/)

We don't try to teach machine learning here — that's C5's job. C17 covers PyTorch as a Python library: tensors, autograd, `nn.Module`, the training loop, debugging gradient flow, saving and loading state dicts, `torch.compile` in 2026.

- **Mini-project:** Train a 3-layer MLP on MNIST from scratch — no `Trainer` class, no `Lightning` — and write up what you learned about the runtime.

#### [Week 12 — Python Security + Open-Source Capstone](week-12-python-security-and-oss-capstone/)

The Python security tour: `pickle`, `eval`, unsafe YAML, SSRF, ReDoS, prototype pollution analogues, supply chain. `bandit`, `semgrep`, `pip-audit`. Then: ship your **first non-trivial OSS PR**.

- **Capstone:** A merged (or under-review) pull request to a real open-source Python project. The PR write-up explains the bug or feature, the fix, the testing, and what you learned.

---

## Skills progression chart

```text
W1  ─ CPython source, compilation, bytecode
W2  │ refcounting, GC, memory tools
W3  ─ the GIL, free-threaded, subinterpreters
W4  ─ asyncio first principles
W5  │ structured concurrency
W6  ─ threads vs processes vs async
W7  ─ profiling tools
W8  │ NumPy vectorization
W9  ─ C extensions (ctypes, cffi, Cython, PyO3)
W10 ─ advanced typing
W11 │ PyTorch as a Python library
W12 ─ Python security + OSS capstone
```

---

## Adapting the syllabus

- **Part-time (18 hrs/wk):** Each "week" becomes 2 weeks. Total = 24 weeks (~6 months).
- **Cohort study group (9 hrs/wk):** One unit every two weeks. ~12 months. Excellent format if you can find peers — half the value of C17 is having someone to argue about cancellation semantics with.

---

## What this track depends on

C17 is the apex of the Python tracks. It reaches back to:

- **C1 Weeks 1–15** (entire C1)
- **C5 Units 1–4** (NumPy, pandas, scikit-learn) — required for Week 8
- **C16 Weeks 7–8** (FastAPI, async) — strongly recommended before Week 4

If you can't do those, do them first. C17 will *not* slow down.

---

## What you won't learn (but should)

To keep the track focused, C17 does not cover:

- **MLOps / model deployment at scale** — see C5 and C15.
- **Production Kubernetes / Terraform** — see C15.
- **Distributed Python (Ray, Dask, Spark)** — touched in stretch readings only. Pick one and go deep after C17.
- **Compiler-level work on CPython itself** — for that, read the [CPython internals book by Anthony Shaw](https://realpython.com/cpython-internals-paperback/) (paid) or the [CPython developer documentation](https://devguide.python.org/) (free).
- **Quantum / scientific computing-specific Python** — niche; SciPy / sympy / xarray are excellent but out of scope.

---

## License

GPL-3.0. Fork, adapt, teach. If you improve it, PR it back so the next learner benefits.
