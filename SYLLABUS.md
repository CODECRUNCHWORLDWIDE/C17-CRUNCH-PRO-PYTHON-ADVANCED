# C17 · Crunch Pro Python Advanced — Syllabus

**12 weeks · ~36 hrs/week full-time (or scaled) · Senior Python (C1 + C5/C16) → open-source-maintainer caliber**

The expert tier: CPython internals, concurrency, performance, native code, packaging, and the runtime knowledge that separates senior from staff.

---

**Prerequisites:** All of C1 (weeks 1–15), plus at least one of C5 (Data Science, all units, comfortable with NumPy/pandas) or C16 (Web Backend, at least through the async week). Unsure? Take the [diagnostic quiz](curriculum/diagnostic-quiz.md) — 18+/25 means you're ready; below 14, do more C1/C5/C16 first. C17 will not slow down.

**Assessment is honor-based.** No proctor, no grades. Each week you certify your own completion: the exercises run, the quiz is answered, the mini-project ships. The capstone is graded against a public rubric — a merged or under-review OSS-quality package on TestPyPI, judged the way a reviewer would.

---

## Program at a glance

| Phase | Weeks | Outcome |
|-------|-------|---------|
| **Phase 1 — The Python Runtime** | 01 – 03 | Read CPython source, bytecode, the GIL, the object model |
| **Phase 2 — Concurrency** | 04 – 06 | asyncio, structured concurrency, threads vs processes |
| **Phase 3 — Performance & Native Code** | 07 – 09 | Profiling, C extensions, packaging and distribution |
| **Phase 4 — Frontier & Capstone** | 10 – 12 | Metaprogramming, concurrency models compared, capstone |

---

## Weekly breakdown

**Week 1 — CPython Internals and the Mental Model.** What `python` is and where it lives, what happens when you run `python script.py`, the source-tree tour, the compilation pipeline (source → AST → bytecode), the `dis` module, reading a `.pyc`.

- *Mini-project:* A 50-line "Python explainer" that takes any `.py` file and prints its tokens, AST, and bytecode side by side.

**Week 2 — The Object Model: Refcounting, GC, Memory.** How `id()` works, reference counting line by line, the cyclic collector, `__slots__`, `weakref`, `gc.get_referrers`, and the tools: `tracemalloc`, `objgraph`, `memray`. Why generators leak.

- *Mini-project:* Detect a memory leak in a small real open-source project and produce a 1-page memo with `memray` flamegraphs.

**Week 3 — Bytecode, the Stack Machine, and the GIL.** The CPython evaluation loop, `LOAD_FAST` vs `LOAD_GLOBAL`, what the GIL actually protects, PEP 703 (free-threaded build), and the 3.13 subinterpreters story.

- *Mini-project:* A ~100-line bytecode tracer that prints each instruction as your code executes, via `sys.settrace`/`sys.monitoring`.

**Week 4 — `asyncio` From First Principles.** An event loop built from scratch in under 200 lines. Coroutines vs generators, tasks, futures, awaitables, the "colored function" debate, `gather`/`wait`/`TaskGroup`/`as_completed`.

- *Mini-project:* A toy `asyncio` clone — `sleep`, `gather`, `Task`, `run` — enough to run a small program against it.

**Week 5 — Structured Concurrency, Cancellation, Back-Pressure.** Why nurseries and `TaskGroup` are a step forward, cancellation and timeouts, `shield`, bounded queues and `Semaphore`, reading and writing async iterators correctly.

- *Mini-project:* A robust async web crawler that respects robots.txt, handles cancellation cleanly, and applies back-pressure to a sink.

**Week 6 — Threads, Processes, and When to Use What.** `threading`, `concurrent.futures`, `multiprocessing`, `joblib`/`loky`. CPU- vs IO-bound, when `multiprocessing` is the wrong answer, and how to think about the free-threaded build.

- *Mini-project:* Convert one CPU-bound task to multiprocessing, one IO-bound task to async, one mixed to a thread-pool — and measure each.

**Week 7 — Profiling Like It's Your Job.** `cProfile` deterministic profiling, `py-spy` and `austin` sampling, `scalene` for CPU+memory, reading flamegraphs, `timeit` gotchas, avoiding microbenchmark traps.

- *Mini-project:* Take an intentionally slow real-world script, find the bottleneck, document the fix, prove the win.

**Week 8 — C Extensions: ctypes, cffi, Cython.** Three production paths, one discipline. `ctypes` for zero-build runtime binding, `cffi` for ABI/API-mode production wraps, Cython as "Python-with-types-becomes-C." When each is right — and when not to write a C extension at all.

- *Mini-project:* Implement a numerical kernel three ways (pure Python, one of ctypes/cffi/Cython, NumPy as the ceiling) and ship a benchmark report with a ≥10× speedup and a memo explaining why.

**Week 9 — Packaging and Distribution.** The modern path end to end: one `pyproject.toml`, a PEP 517/518/660 build backend, `manylinux` wheels via `cibuildwheel`/`auditwheel`, locked dependencies, and PEP 740 trusted publishing with no stored API key.

- *Mini-project:* Publish a small library to TestPyPI — built wheel + sdist, clean-venv install, and a GitHub Actions trusted-publishing workflow on every tag — plus a 700-word choices memo.

**Week 10 — Metaprogramming, Descriptors, and Metaclasses.** How Python constructs the classes your package is made of: descriptors, `__set_name__`, class decorators, `__init_subclass__`, metaclasses, and type-checker cooperation. Which rung of the ladder to stand on.

- *Mini-project:* A validated-model library built four ways, benchmarked on definition/creation/set-time and memory, with a one-page "which mechanism when" decision tree.

**Week 11 — Python Concurrency Models Compared.** The same 10,000-document scoring workload run five ways — threads, asyncio, multiprocessing, free-threaded, subinterpreters (PEP 703 / PEP 684) — measured, not speculated. Throughput, latency, resident memory.

- *Mini-project:* A document scorer implemented five ways, graphed across throughput/latency/memory, with a one-page decision tree for a teammate told to "make this faster."

**Week 12 — Capstone: a Perf-Tuned Python Project.** Take a computational kernel from naive baseline through profiling, NumPy vectorization, a C extension, and parallelism — applying each technique only where it earns its keep, and measuring every choice.

- *Capstone:* A public TestPyPI package (suggested: `cc-<handle>-imageperf`) with a reproducible benchmark report — stated methodology, cited hardware, a confidence interval, an honest bottleneck, and a labelled speedup chart a reviewer can rerun in two commands.

---

## Weekly load

| Component | hrs/wk |
|-----------|------:|
| Lectures / readings | 6 |
| Hands-on exercises | 8 |
| Coding challenges | 4 |
| Quiz + readings | 3 |
| Homework | 6 |
| Mini-project | 7 |
| Self-study & review | 2 |
| **Total** | **36** |

Scalable down: part-time ≈ 18 hrs/wk over 24 weeks; a cohort study group at ~9 hrs/wk runs about 12 months.

---

## Outcome

You leave able to read CPython source without intimidation, profile a real bottleneck and prove the fix, write async you trust, wrap a C library three ways, package and publish to an index, and reach for the right concurrency model on evidence. The deliverable is a public, benchmarked, installable package — a portfolio piece, not a transcript line.

---

## License

GPL-3.0.
