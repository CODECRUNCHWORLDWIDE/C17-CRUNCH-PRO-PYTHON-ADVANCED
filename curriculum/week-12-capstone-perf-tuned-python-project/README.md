# Week 12 — Capstone: Perf-Tuned Python Project

> *Twelve weeks ago we opened a CPython source tarball and walked through `Include/cpython/object.h` to understand what a Python object actually is. Eleven weeks ago we read `PyObject_GC_Track` in `Modules/gcmodule.c` and watched the cyclic garbage collector decide which of our objects survived. Ten weeks ago we ran `dis.dis(f)` on our own functions and learned to read CPython bytecode the way a C programmer reads assembly. Nine weeks ago we wrote our first `async def`, scheduled it through `asyncio.run`, and felt — for the first time — what a cooperative scheduler does when you ask it to interleave ten thousand I/O-bound tasks. Eight weeks ago we built a `TaskGroup` and learned why structured concurrency is the answer to `gather`'s decade of footguns. Seven weeks ago we crossed the threads-and-processes boundary and measured the pickling tax. Six weeks ago we attached `cProfile`, `py-spy`, and `memray` to a real workload and learned which numbers in a profiler report actually mean something. Five weeks ago we wrote a C extension with `PyMethodDef` and `Py_BuildValue` and the GIL-release macros, ran it against a pure-Python baseline, and watched the hot loop drop from 4 seconds to 40 milliseconds. Four weeks ago we built a `pyproject.toml` with `[build-system]` requires, ran `python -m build`, and uploaded our first sdist+wheel pair to TestPyPI. Three weeks ago we wrote a decorator factory that built a class at module-import time, used `__init_subclass__` for compile-time validation, and learned which metaprogramming tools are worth using and which are not. Last week we ran the same workload through threads, asyncio, multiprocessing, free-threaded threads, and subinterpreters — five times — and produced a decision tree that we would hand a teammate. This week is the capstone. This week you take all of that — every technique, every measurement discipline, every PEP citation — and you ship a public Python package on TestPyPI with a benchmark report demonstrating measurable speedup against a naive baseline. This is the deliverable that turns a track on a transcript into a portfolio piece a hiring manager can install with `pip install --index-url https://test.pypi.org/simple/ <your-package>` and run themselves.*

Welcome to Week 12 of **C17 · Crunch Pro Python Advanced** — the final week. You arrived in Week 1 knowing Python well enough to ship working code; you leave in Week 12 knowing CPython well enough to debug it, package it, distribute it, and tune it. The deliverable this week is not another isolated exercise. The deliverable is **a public Python package** — one that you choose, one that you scope, one that you build end to end, one that you publish on TestPyPI under your own namespace, and one that you accompany with a benchmark report demonstrating that every perf technique from the track was applied where appropriate and measured for impact. You will not apply every technique to every line of code; the discipline of the senior practitioner is knowing which techniques to skip. You will, however, **measure** every choice you make. The report says: here was the naive baseline, here is what I tried, here is what worked, here is what did not, here is the speedup with a confidence interval. Twelve weeks of CPython internals collapse, this week, into the difference between "I think this is faster" and "I measured this, it is `4.8x` faster on this benchmark with this hardware, here are the numbers."

The thesis of the capstone is **measured engineering**. The senior Python engineer in 2026 is not the one who knows every C-API function in `Include/cpython/`. The senior Python engineer is the one who can pick a computational kernel — image filter, ML inference graph, parser, simulation, graph algorithm — and walk it through a structured progression: profile the baseline, find the hot path, decide whether to optimise the Python (W2 data structure choice, W3 bytecode awareness, W7 algorithmic improvement), parallelise the Python (W4 asyncio for I/O, W6 multiprocessing for CPU, W11 model selection), or replace the Python (W8 C extension, NumPy vectorisation, Cython). And then the senior engineer **ships the result** — properly packaged (W9), distributed on the index, versioned, type-hinted (W10 metaprogramming where it earns its keep), and documented with a benchmark methodology a reviewer can reproduce. That progression is the capstone. The kernel you pick is up to you.

The standards are the spine, and we list them by week so the wrap-up sidebar lives in the README. **Week 1** (CPython internals) gave you `PyObject`, `ob_refcnt`, `ob_type`, and the reference-counting model defined by `Py_INCREF`/`Py_DECREF`; the canonical reference is the [C-API data model](https://docs.python.org/3/c-api/structures.html) and **PEP 7** (CPython C style). **Week 2** (memory and GC) gave you the cyclic garbage collector, three generations, `gc.collect`, `tracemalloc`, and the data model defined by **PEP 442** (safe object finalisation). **Week 3** (bytecode and `dis`) gave you the CPython evaluation loop in `Python/ceval.c`, the bytecode taxonomy defined by **PEP 659** (specialising adaptive interpreter, 3.11+), and the `dis` module documented at <https://docs.python.org/3/library/dis.html>. **Week 4** (asyncio fundamentals) gave you the event loop, `async def`, `await`, defined by **PEP 3156**, **PEP 492**, **PEP 525**, **PEP 530**. **Week 5** (structured concurrency) gave you `asyncio.TaskGroup`, `ExceptionGroup`/`except*`, defined by **PEP 654** (3.11+) and Nathaniel Smith's Trio writings as prior art. **Week 6** (threads vs processes) gave you `threading`, `multiprocessing`, the `concurrent.futures.Executor` interface defined by **PEP 3148**, and the GIL release rules documented in `Py_BEGIN_ALLOW_THREADS`. **Week 7** (profiling) gave you `cProfile`, `py-spy` (Ben Frederickson), `memray` (Bloomberg), `tracemalloc`, and the methodology of "measure before optimising" attributed to Donald Knuth (1974). **Week 8** (C extensions) gave you `PyMethodDef`, `PyModuleDef`, `Py_BuildValue`, `PyArg_ParseTuple`, the multi-phase initialisation defined by **PEP 489**, and the stable ABI defined by **PEP 384** and extended by **PEP 652**. **Week 9** (packaging and distribution) gave you `pyproject.toml` defined by **PEP 518** (build-system), **PEP 517** (build backends), **PEP 621** (project metadata), **PEP 660** (editable installs), and the TestPyPI/PyPI distinction documented at <https://packaging.python.org/>. **Week 10** (metaprogramming) gave you decorators, descriptors, `__init_subclass__` defined by **PEP 487**, `__set_name__`, metaclasses, and the judgement to use them sparingly. **Week 11** (concurrency models compared) gave you the decision tree — threads, asyncio, multiprocessing, free-threaded (**PEP 703**), subinterpreters (**PEP 684**/**PEP 734**). **Week 12** is the application of all of the above to a single shippable artefact.

The worked example — and the **suggested kernel** if you do not already have a project in mind — is an **image-processing library**. You pick a single non-trivial filter (gaussian blur with a 5x5 kernel; sobel edge detection; a small JPEG-style block DCT) and ship it as a Python package called `cc-<your-handle>-imageperf`. The naive baseline is a triple-nested Python `for` loop over pixels. The progression is: (1) profile it with `cProfile` and confirm the hot path is the inner loop; (2) refactor to NumPy ufuncs and measure the speedup (typically 50–200x for free); (3) write a single C extension for the convolution kernel and measure (typically another 5–20x over NumPy for small kernels because of allocation overhead); (4) wrap the C extension with a Python API that releases the GIL on entry and add a `ProcessPoolExecutor` fanout for multi-image workloads; (5) profile end-to-end and verify the speedup with `time.perf_counter` and `memray`. Then package it, type-hint the public API, write a `tests/` directory with one regression test per filter, write a `benchmarks/` directory with a reproducible methodology, and upload to TestPyPI. The README of the package itself becomes a smaller, focused version of this README. The reviewer (a hiring manager, a peer, your future self) can install and run the benchmark in two commands. **The alternative kernels are listed in `mini-project/README.md`** — pick whichever calls to you; the rubric is identical.

The capstone is graded against a rubric (`mini-project/RUBRIC.md`). Half the score is the package itself — does it install cleanly, do the tests pass, is the type-hint coverage complete, does the version comply with **PEP 440**, does the metadata comply with **PEP 621**. The other half is the benchmark report — does it state the methodology in enough detail to reproduce, does it cite the hardware, does it report a confidence interval, does it identify the bottleneck honestly (some bottlenecks cannot be optimised further within CPython; saying so is part of the discipline), does it show the speedup chart with both axes labelled. We are not grading wallclock — a 2x speedup with a credible methodology beats a 50x speedup that the reviewer cannot reproduce.

The expectation, by the end of the week, is that you can hand a stranger your TestPyPI page and they can install, run, and reproduce your benchmark on their own machine inside ten minutes. That is the bar.

## Learning objectives (W12)

By the end of this week, you will be able to:

- **Scope** a perf-tuned Python project. Pick a single computational kernel that is small enough to ship in a week and substantial enough to demonstrate every technique from Weeks 1–11. Justify the choice in two sentences.
- **Profile** the baseline. Run `cProfile`, `py-spy`, and `memray` against the naive implementation. Identify the single line or single function that accounts for >80% of the wall-clock. Cite Week 7.
- **Optimise** the hot path through the right tier. For most kernels the tier order is: (a) algorithmic improvement, (b) NumPy or stdlib vectorisation, (c) Cython or pure-C extension, (d) parallelisation. Skip tiers you do not need. Cite Weeks 2, 3, 7, 8.
- **Parallelise** correctly. Pick threads, asyncio, multiprocessing, or free-threaded based on the decision tree from Week 11. Defend the choice in writing. Cite Weeks 4, 5, 6, 11.
- **Write** a C extension where it earns its keep. The convolution kernel, the bytewise hash, the bytewise tokeniser — these are the kinds of inner loops that justify the maintenance cost. Cite Week 8 and **PEP 489**.
- **Package** the result. `pyproject.toml` with **PEP 621** metadata, **PEP 440** versioning, **PEP 561** typing markers (`py.typed`), a `MANIFEST.in` if you ship C source, a working `python -m build`. Cite Week 9.
- **Distribute** to TestPyPI. Register an account, mint an API token, upload via `twine`, verify with `pip install --index-url https://test.pypi.org/simple/`. Cite <https://packaging.python.org/en/latest/guides/using-testpypi/>.
- **Type-hint** the public API. PEP 484 (original type hints), PEP 526 (variable annotations), PEP 585 (built-in generics in 3.9+), PEP 604 (`X | Y` syntax in 3.10+), PEP 695 (type aliases and generic syntax in 3.12+). Cite Week 10.
- **Apply** metaprogramming where it earns its keep. Most capstones use zero or one decorator and zero metaclasses. The reviewer should be able to read the public API without consulting PEP 487. Cite Week 10.
- **Benchmark** with a methodology the reviewer can reproduce. State the hardware, the Python version, the seed, the warm-up runs, the measurement runs, the statistic (median, not mean), and the confidence interval. Cite Week 7's methodology section.
- **Report**. The benchmark report is a markdown document. It is part of the deliverable. Treat it as a paper, not as an afterthought.
- **Ship**. The package goes live on TestPyPI. The benchmark report goes in `mini-project/REPORT.md`. The TestPyPI URL goes in `mini-project/SUBMISSION.md`.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | `COP 3337` — Deliver a substantial multi-file program of your own design: build it, test it, document it, and defend the result. |
| Industry | Hand your work to somebody else, watch them fail to reproduce it, and close every gap in the methodology before it ships. |
| Beyond the bar | The benchmark report is a graded deliverable in its own right — hardware, seed, warm-up runs, median and interval all stated — and a peer audits it — `challenges/challenge-02-reproducibility-audit.md` |


## The W1–W12 wrap-up (sidebar)

The track in one paragraph per week, written as a take-home reference:

- **W1 — CPython internals.** Every Python object is a `PyObject` with `ob_refcnt` and `ob_type`. Reference counting is the primary memory-management mechanism. The Global Interpreter Lock serialises bytecode execution. The CPython evaluation loop lives in `Python/ceval.c`. Read it once, do not read it weekly. **PEP 7** (C style), **PEP 8** (Python style).
- **W2 — Memory and GC.** Reference counting handles >99% of cases; the cyclic garbage collector handles cycles. Three generations, oldest collected least often. `gc.collect()`, `gc.get_stats()`, `gc.set_threshold()`. `tracemalloc` for allocation tracing. **PEP 442** (safe finalisation, 3.4+).
- **W3 — Bytecode and `dis`.** Every Python source compiles to a `code` object containing a tuple of bytecodes. `dis.dis(f)` shows them. **PEP 659** (specialising adaptive interpreter, 3.11+) made common bytecodes ~25% faster. The bytecode set is documented in `Python/ceval.c` and `Include/internal/pycore_opcode.h`.
- **W4 — Asyncio fundamentals.** `async def` returns a coroutine. The event loop schedules coroutines cooperatively. `await` yields control. `asyncio.run` is the only event-loop entry point you need. **PEP 3156** (asyncio), **PEP 492** (`async`/`await`), **PEP 525** (async generators), **PEP 530** (async comprehensions).
- **W5 — Structured concurrency.** `asyncio.TaskGroup` (3.11+) replaces `asyncio.gather` for new code. Errors propagate via `ExceptionGroup` and are caught with `except*`. The scope is the lifetime; you cannot leak a task. **PEP 654** (3.11+).
- **W6 — Threads vs processes.** Threads share memory and the GIL; processes share neither. `concurrent.futures.Executor` is the unified interface. The GIL releases for I/O and for a narrow class of C-extension calls. **PEP 3148** (`concurrent.futures`).
- **W7 — Profiling.** `cProfile` for deterministic call-counting, `py-spy` for sampling production processes, `memray` for memory allocations, `tracemalloc` for in-process memory diffs. Profile before you optimise. Median is not mean. Knuth, 1974.
- **W8 — C extensions.** `PyMethodDef` declares functions, `PyModuleDef` declares modules, `Py_BuildValue`/`PyArg_ParseTuple` cross the C/Python boundary. Release the GIL on long-running C code with `Py_BEGIN_ALLOW_THREADS`. **PEP 489** (multi-phase init), **PEP 384** (stable ABI), **PEP 652** (stable ABI extended).
- **W9 — Packaging and distribution.** `pyproject.toml` is the only configuration file you need. `python -m build` produces sdist + wheel. `twine upload --repository testpypi` publishes them. **PEP 518** (build system), **PEP 517** (build backends), **PEP 621** (project metadata), **PEP 660** (editable installs), **PEP 440** (versioning).
- **W10 — Metaprogramming.** Decorators wrap. Descriptors customise attribute access. `__init_subclass__` (**PEP 487**, 3.6+) replaces 90% of metaclass uses. Metaclasses are the nuclear option. Use them sparingly.
- **W11 — Concurrency models compared.** Threads for I/O on the stock build. Asyncio for high-concurrency low-per-task I/O. Multiprocessing for CPU-bound pure-Python on the stock build. Free-threaded (**PEP 703**, 3.13+) for CPU-bound pure-Python without the pickling tax. Subinterpreters (**PEP 684**/**PEP 734**, 3.12+/3.13+) for everything in between.
- **W12 — Capstone.** All of the above, applied to one shippable artefact, measured honestly, distributed publicly. The capstone is the deliverable; the deliverable is the proof.

## Prerequisites

- **C17 Weeks 1–11** completed. This week is a capstone; every prior week is load-bearing.
- **Python 3.11+ (3.13 strongly preferred).** Several examples use features from 3.11 (`TaskGroup`, `ExceptionGroup`, `tomllib`) and 3.12 (PEP 695 generic syntax) and 3.13 (free-threaded build, `interpreters` module).
- **A TestPyPI account.** Free. Register at <https://test.pypi.org/account/register/>. Generate a project-scoped API token *after* your first successful upload (TestPyPI requires the project to exist before you can scope the token to it — first upload uses an account-scoped token; refresh to project-scoped immediately after).
- **`build` and `twine` installed locally.** `pip install build twine`. Both are part of the recommended PyPA toolchain.
- **A working C toolchain** if your capstone includes a C extension. macOS: Xcode Command Line Tools (`xcode-select --install`). Linux: `build-essential` (Debian/Ubuntu) or `gcc` (Fedora/RHEL). Windows: MSVC Build Tools.
- **`psutil`, `numpy`, `cProfile`, `memray`, `py-spy`** installed in your benchmark environment. All free; all pip-installable.

## Topics covered

- **Capstone scoping.** Pick a kernel. Justify the choice. Write the success criteria *before* you write the code.
- **The naive baseline.** Write the slowest version first, on purpose. Get it correct. Snapshot the wall-clock and the memory footprint.
- **The profiler-driven tier ladder.** Algorithm → vectorisation → C extension → parallelisation. Skip tiers you do not need.
- **Packaging end to end.** `pyproject.toml`, `MANIFEST.in`, `py.typed`, `python -m build`, `twine upload --repository testpypi`.
- **The benchmark report.** Methodology, hardware, statistics, charts, honest discussion of remaining bottlenecks.
- **The W1–W12 wrap-up.** A take-home reference for the track.

## Weekly schedule (~36h capstone-intensive)

| Day       | Focus                                                                | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Scope the capstone; pick the kernel; write the success criteria; baseline implementation | 2h    | 1.5h      | 0h         | 0.5h      | 1h       | 1h           | 0.5h       | 6.5h        |
| Tuesday   | Profile baseline; identify hot path; apply tier 1 (algorithm) and tier 2 (vectorisation) | 1.5h  | 1.5h      | 0h         | 0.5h      | 1h       | 2h           | 0.5h       | 7h          |
| Wednesday | Tier 3 (C extension where appropriate); GIL release; benchmark each tier             | 1.5h  | 1.5h      | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 8h          |
| Thursday  | Tier 4 (parallelisation); pick the right model; benchmark; package skeleton          | 0h    | 0h        | 0h         | 0.5h      | 1h       | 3h           | 0.5h       | 5h          |
| Friday    | Packaging end-to-end; `pyproject.toml`; `py.typed`; `python -m build`; test install   | 0h    | 0h        | 0h         | 0.5h      | 1h       | 3h           | 0.5h       | 5h          |
| Saturday  | Upload to TestPyPI; write the REPORT.md; reproduce on a clean venv                    | 0h    | 0h        | 0h         | 0h        | 0h       | 3h           | 0.5h       | 3.5h        |
| Sunday    | Final exam (W1–W12 cumulative) + reflection                                           | 0h    | 0h        | 0h         | 1h        | 0h       | 0h           | 0h         | 1h          |
| **Total** |                                                                      | **5h**   | **4.5h**  | **1h**     | **3.5h**  | **5h**   | **14h**      | **3h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview; the W1–W12 wrap-up sidebar |
| [resources.md](./resources.md) | The PyPA documentation index, TestPyPI guides, every PEP cited from W1 through W12, profiling tools |
| [lecture-notes/01-capstone-scoping-and-the-tier-ladder.md](./lecture-notes/01-capstone-scoping-and-the-tier-ladder.md) | How to scope a perf project; the tier ladder; the discipline of skipping tiers |
| [lecture-notes/02-packaging-end-to-end-with-testpypi.md](./lecture-notes/02-packaging-end-to-end-with-testpypi.md) | The full lifecycle: `pyproject.toml` → `build` → `twine upload --repository testpypi` → `pip install` verification |
| [lecture-notes/03-the-benchmark-report-as-deliverable.md](./lecture-notes/03-the-benchmark-report-as-deliverable.md) | How to write a benchmark report a reviewer can reproduce |
| [exercises/exercise-01-naive-baseline-and-profile.py](./exercises/exercise-01-naive-baseline-and-profile.py) | Write the naive baseline; profile it; identify the hot path |
| [exercises/exercise-02-tier-ladder-walkthrough.py](./exercises/exercise-02-tier-ladder-walkthrough.py) | Apply the tier ladder to a 1D blur kernel; measure each tier |
| [exercises/exercise-03-packaging-skeleton.py](./exercises/exercise-03-packaging-skeleton.py) | Generate the `pyproject.toml`, `src/` layout, `py.typed`, and verify with `python -m build` |
| [exercises/exercise-04-testpypi-dry-run.py](./exercises/exercise-04-testpypi-dry-run.py) | Dry-run the TestPyPI upload locally; lint the metadata; verify the wheel contents |
| [exercises/SOLUTIONS.md](./exercises/SOLUTIONS.md) | Expected outputs, common errors, the reasoning behind each exercise |
| [challenges/challenge-01-end-to-end-rehearsal.md](./challenges/challenge-01-end-to-end-rehearsal.md) | One-day rehearsal: take a 50-line script through the full pipeline before committing to your capstone kernel |
| [challenges/challenge-02-reproducibility-audit.md](./challenges/challenge-02-reproducibility-audit.md) | Hand your benchmark to a peer and watch them try to reproduce it; fix every gap in the methodology |
| [quiz.md](./quiz.md) | Final exam — 20 questions covering W1–W12 |
| [homework.md](./homework.md) | Six problems (~5h) — the homework is the capstone work split into daily checkpoints |
| [mini-project/README.md](./mini-project/README.md) | The capstone brief — pick a kernel, ship a package, write the report |
| [mini-project/RUBRIC.md](./mini-project/RUBRIC.md) | The grading rubric — half package, half report |
| [mini-project/REPORT.template.md](./mini-project/REPORT.template.md) | The benchmark report template — fill in the blanks |
| [mini-project/SUBMISSION.md](./mini-project/SUBMISSION.md) | Where to record your TestPyPI URL and reproduction command |
| [mini-project/example-package/](./mini-project/example-package/) | A complete worked example — the image-blur capstone implementation |

## Stretch

- Read [the PyPA Packaging User Guide](https://packaging.python.org/) end-to-end (~3 hours). The single best free packaging reference; maintained by the Python Packaging Authority.
- Read [PEP 621](https://peps.python.org/pep-0621/) (~30 minutes). The `pyproject.toml` `[project]` table specification.
- Read [PEP 440](https://peps.python.org/pep-0440/) (~40 minutes). Version specification; the rules for `1.0.0a1`, `1.0.0rc1`, `1.0.0.post1`, etc.
- Read [PEP 561](https://peps.python.org/pep-0561/) (~15 minutes). The `py.typed` marker for distributing type information.
- Read [PEP 660](https://peps.python.org/pep-0660/) (~20 minutes). Editable installs (`pip install -e .`) — the modern replacement for `setup.py develop`.
- Read [PEP 517](https://peps.python.org/pep-0517/) and [PEP 518](https://peps.python.org/pep-0518/) (~50 minutes combined). The build-system specification.
- Read [PEP 489](https://peps.python.org/pep-0489/) (~30 minutes). Multi-phase initialisation for C extensions — required for subinterpreter compatibility.
- Read [PEP 384](https://peps.python.org/pep-0384/) and [PEP 652](https://peps.python.org/pep-0652/) (~40 minutes). The stable ABI — what `Py_LIMITED_API` buys you.
- Read [PEP 703](https://peps.python.org/pep-0703/) end-to-end if you have not already (~90 minutes). Sam Gross, free-threaded Python.
- Watch [Brett Cannon's PyCon 2023 talk on the modern packaging stack](https://www.youtube.com/results?search_query=brett+cannon+pycon+packaging) (~45 minutes). Free.
- Watch [Antonio Cuni's PyCon 2024 talk on writing fast Python](https://www.youtube.com/results?search_query=antonio+cuni+pycon+fast+python) (~45 minutes). Free.
- Watch [Pablo Galindo Salgado's PyCon 2024 talk on memray](https://www.youtube.com/results?search_query=pablo+galindo+memray+pycon) (~30 minutes). Free; Pablo is the maintainer.

## Up next

This is the last week of **C17 · Crunch Pro Python Advanced**. There is no `week-13-*` folder. The track ends here.

What comes after: the rest of the C-track catalogue continues to exist (see `MASTER-CURRICULUM.md` at the org root). The natural next step if you enjoyed the perf-and-packaging emphasis of C17 is **C7 · Crunch Wire** (the 24-week deep specialisation on systems and networking), or **C23 · Crunch Agents** (LLM agent engineering with the Anthropic SDK, which uses many of the same packaging and async techniques you practised here). Outside the C-track, the highest-leverage next reading is **the CPython developer guide** at <https://devguide.python.org/> if you want to contribute upstream, or **the SciPy/NumPy contributor docs** at <https://numpy.org/devdocs/dev/> if you want to apply your C-extension skills to the scientific Python ecosystem.

The capstone is the proof that the track happened. Ship it.
