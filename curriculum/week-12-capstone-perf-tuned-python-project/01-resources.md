# Week 12 Resources — Capstone: Perf-Tuned Python Project

The resource list for the capstone is necessarily wider than the other weeks because the capstone integrates every prior week. We organise it by purpose: (1) packaging and distribution, the load-bearing material for the deliverable; (2) the PEP index, every standard cited across the track; (3) the per-week reading recap, one canonical doc per prior week; (4) talks and external references. Everything below is free.

## Packaging and distribution (the load-bearing material)

The single most important document this week is the **PyPA Packaging User Guide**. It is the authoritative reference, it is current, and it is maintained by the same people who maintain `pip`, `build`, `twine`, and the PyPI infrastructure.

- [packaging.python.org — full guide](https://packaging.python.org/). The index. Bookmark this.
- [packaging.python.org — Packaging Python Projects tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/). The official end-to-end tutorial. About 20 minutes to read; this is the spine of Lecture 02.
- [packaging.python.org — Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/). The reference for the practice index. Every capstone publishes here.
- [packaging.python.org — Writing your `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/). The `[project]` table reference.
- [packaging.python.org — Configuring metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/). The full specification.
- [packaging.python.org — Distributing packages](https://packaging.python.org/en/latest/tutorials/installing-packages/). The reverse direction; understand what `pip install` does to your distribution so you can structure your distribution to work with it.
- [packaging.python.org — Including files in source distributions](https://packaging.python.org/en/latest/guides/using-manifest-in/). When you need `MANIFEST.in`; you usually do when shipping a C extension.
- [packaging.python.org — Specifying dependencies](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/). The difference between `dependencies` in `pyproject.toml` and `requirements.txt`. Capstones use the former.
- [test.pypi.org](https://test.pypi.org/). The practice index. Free to register, free to upload, packages do not persist forever.
- [pypi.org/help](https://pypi.org/help/). The PyPI help index. Trusted publishing, API tokens, account recovery.
- [`build` documentation](https://build.pypa.io/). The PyPA `build` tool — `python -m build` is the canonical way to build sdists and wheels.
- [`twine` documentation](https://twine.readthedocs.io/). The PyPA upload tool.
- [`pip` documentation](https://pip.pypa.io/). The installer. Read the section on `--index-url`, `--extra-index-url`, and `--no-index`.

## The PEP index (cited across W1–W12)

The capstone cites a lot of PEPs. They are organised here by category, with a one-line summary.

### Standards: language and runtime

- [PEP 7 — Style Guide for C Code](https://peps.python.org/pep-0007/). The C style for CPython itself. Read if you write a C extension.
- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/). The reference Python style guide. Apply with judgement; do not litigate.
- [PEP 20 — The Zen of Python](https://peps.python.org/pep-0020/). Tim Peters' aphorisms. "Readability counts." "Now is better than never."
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/). The docstring spec. Capstones get docstrings on every public name.

### Standards: type hints

- [PEP 484 — Type Hints](https://peps.python.org/pep-0484/). Guido van Rossum, Jukka Lehtosalo, Łukasz Langa. The original; 3.5+.
- [PEP 526 — Syntax for Variable Annotations](https://peps.python.org/pep-0526/). 3.6+.
- [PEP 561 — Distributing and Packaging Type Information](https://peps.python.org/pep-0561/). The `py.typed` marker. Load-bearing for the capstone.
- [PEP 585 — Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/). 3.9+. Use `list[int]`, not `List[int]`.
- [PEP 604 — Allow writing union types as `X | Y`](https://peps.python.org/pep-0604/). 3.10+. Use `int | None`, not `Optional[int]`.
- [PEP 612 — Parameter Specification Variables](https://peps.python.org/pep-0612/). 3.10+. `ParamSpec` for decorator typing.
- [PEP 646 — Variadic Generics](https://peps.python.org/pep-0646/). 3.11+. `TypeVarTuple`.
- [PEP 673 — Self Type](https://peps.python.org/pep-0673/). 3.11+.
- [PEP 692 — Using `TypedDict` for more precise `**kwargs` typing](https://peps.python.org/pep-0692/). 3.12+.
- [PEP 695 — Type Parameter Syntax](https://peps.python.org/pep-0695/). 3.12+. The `type Alias = ...` and `def f[T](x: T) -> T` syntax.

### Standards: async, concurrency, GIL

- [PEP 3148 — `concurrent.futures`](https://peps.python.org/pep-3148/). Brian Quinlan, 2009. The unified Executor interface.
- [PEP 3156 — Asynchronous IO Support Rebooted: the "asyncio" Module](https://peps.python.org/pep-3156/). Guido van Rossum, 2012.
- [PEP 492 — Coroutines with async and await syntax](https://peps.python.org/pep-0492/). Yury Selivanov, 2015. 3.5+.
- [PEP 525 — Asynchronous Generators](https://peps.python.org/pep-0525/). Yury Selivanov, 2016. 3.6+.
- [PEP 530 — Asynchronous Comprehensions](https://peps.python.org/pep-0530/). Yury Selivanov, 2016. 3.6+.
- [PEP 654 — Exception Groups and `except*`](https://peps.python.org/pep-0654/). Irit Katriel, 2022. 3.11+.
- [PEP 684 — A Per-Interpreter GIL](https://peps.python.org/pep-0684/). Eric Snow, 2023. 3.12+.
- [PEP 703 — Making the Global Interpreter Lock Optional in CPython](https://peps.python.org/pep-0703/). Sam Gross, 2023. 3.13+ (optional build).
- [PEP 734 — Multiple Interpreters in the Stdlib](https://peps.python.org/pep-0734/). Eric Snow, 2024. 3.13+. The `interpreters` module.

### Standards: data model and runtime semantics

- [PEP 442 — Safe object finalization](https://peps.python.org/pep-0442/). Antoine Pitrou, 2013. 3.4+. Removed the "objects with `__del__` cannot be in cycles" restriction.
- [PEP 487 — Simpler customisation of class creation](https://peps.python.org/pep-0487/). Martin Teichmann, 2015. 3.6+. `__init_subclass__` and `__set_name__`.
- [PEP 657 — Include Fine Grained Error Locations in Tracebacks](https://peps.python.org/pep-0657/). 3.11+. The `~~~~~^^^^^` underline in error messages.
- [PEP 659 — Specializing Adaptive Interpreter](https://peps.python.org/pep-0659/). Mark Shannon, 2021. 3.11+. The Faster CPython initiative.

### Standards: C-extension and ABI

- [PEP 384 — Defining a Stable ABI](https://peps.python.org/pep-0384/). Martin von Löwis, 2009. The `Py_LIMITED_API` flag.
- [PEP 489 — Multi-phase extension module initialisation](https://peps.python.org/pep-0489/). Petr Viktorin, 2013. 3.5+. Required for subinterpreter compatibility.
- [PEP 652 — Maintaining the Stable ABI](https://peps.python.org/pep-0652/). Petr Viktorin, 2021. The follow-up to PEP 384.

### Standards: packaging

- [PEP 376 — Database of Installed Python Distributions](https://peps.python.org/pep-0376/). The `*.dist-info/` directory layout.
- [PEP 427 — The Wheel Binary Package Format 1.0](https://peps.python.org/pep-0427/). The wheel format.
- [PEP 440 — Version Identification and Dependency Specification](https://peps.python.org/pep-0440/). The version-string spec. Critical for the capstone.
- [PEP 503 — Simple Repository API](https://peps.python.org/pep-0503/). What TestPyPI and PyPI implement.
- [PEP 508 — Dependency specification for Python Software Packages](https://peps.python.org/pep-0508/). The `requirements`/`dependencies` string grammar.
- [PEP 517 — A build-system independent format for source trees](https://peps.python.org/pep-0517/). The build-backend interface.
- [PEP 518 — Specifying Minimum Build System Requirements for Python Projects](https://peps.python.org/pep-0518/). The `[build-system]` table of `pyproject.toml`.
- [PEP 621 — Storing project metadata in `pyproject.toml`](https://peps.python.org/pep-0621/). The `[project]` table.
- [PEP 631 — Dependency specification in `pyproject.toml`](https://peps.python.org/pep-0631/). Subsumed by PEP 621.
- [PEP 660 — Editable installs for `pyproject.toml`-based builds](https://peps.python.org/pep-0660/). The modern replacement for `setup.py develop`.
- [PEP 668 — Marking Python base environments as "externally managed"](https://peps.python.org/pep-0668/). The reason your system Python now refuses `pip install`. Use `venv` or `uv`.
- [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/). For single-file scripts; not the capstone case, but worth knowing.

## Python documentation (per-prior-week canonical reference)

One link per prior week. Each is the docs page the lectures of that week pulled from.

- **W1**: [The Python/C API](https://docs.python.org/3/c-api/). Specifically [Type Objects](https://docs.python.org/3/c-api/typeobj.html) and [The Standard Type Hierarchy](https://docs.python.org/3/reference/datamodel.html#the-standard-type-hierarchy).
- **W2**: [The `gc` module](https://docs.python.org/3/library/gc.html) and [The `tracemalloc` module](https://docs.python.org/3/library/tracemalloc.html) and [The Reference Counting section of the C-API](https://docs.python.org/3/c-api/refcounting.html).
- **W3**: [The `dis` module](https://docs.python.org/3/library/dis.html). The full bytecode reference. Read alongside `dis.dis(your_function)` on real code.
- **W4**: [The `asyncio` module index](https://docs.python.org/3/library/asyncio.html). Specifically [`asyncio.run`](https://docs.python.org/3/library/asyncio-runner.html) and [`asyncio.Task`](https://docs.python.org/3/library/asyncio-task.html).
- **W5**: [`asyncio.TaskGroup`](https://docs.python.org/3/library/asyncio-task.html#task-groups) and [`ExceptionGroup`](https://docs.python.org/3/library/exceptions.html#ExceptionGroup).
- **W6**: [The `threading` module](https://docs.python.org/3/library/threading.html), [The `multiprocessing` module](https://docs.python.org/3/library/multiprocessing.html), [The `concurrent.futures` module](https://docs.python.org/3/library/concurrent.futures.html).
- **W7**: [The `cProfile` module](https://docs.python.org/3/library/profile.html), [The `timeit` module](https://docs.python.org/3/library/timeit.html), and the external tools [py-spy](https://github.com/benfred/py-spy) and [memray](https://bloomberg.github.io/memray/).
- **W8**: [Extending and Embedding the Python Interpreter](https://docs.python.org/3/extending/). The full C-extension reference; read it once.
- **W9**: [The Python Packaging User Guide](https://packaging.python.org/). Linked again because this week.
- **W10**: [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html) by Raymond Hettinger. The single best descriptors reference.
- **W11**: [The `interpreters` module](https://docs.python.org/3/library/interpreters.html). New in 3.13.

## External tools (free, pip-installable, used in the capstone)

- [`build`](https://build.pypa.io/) — `python -m build`. The PyPA build front-end.
- [`twine`](https://twine.readthedocs.io/) — upload tool for sdists and wheels.
- [`hatchling`](https://hatch.pypa.io/latest/) — the default build backend recommended for the capstone unless you specifically need `setuptools`. Pure-Python, fast, supports PEP 660 editables out of the box.
- [`setuptools`](https://setuptools.pypa.io/) — the original build backend. Use it if your capstone has a C extension and you want the simplest possible `ext_modules` declaration.
- [`scikit-build-core`](https://scikit-build-core.readthedocs.io/) — alternative build backend for C extensions, especially CMake-based. Out of scope for most capstones but worth knowing exists.
- [`cibuildwheel`](https://cibuildwheel.readthedocs.io/) — builds wheels for every Python version and platform from a single CI workflow. Out of scope for the capstone (we ship sdist-only, or a single platform-specific wheel) but the production tool for real-world packages.
- [`py-spy`](https://github.com/benfred/py-spy) — sampling profiler. Free, MIT.
- [`memray`](https://bloomberg.github.io/memray/) — memory profiler. Free, Apache 2.0, Bloomberg.
- [`mypy`](https://mypy-lang.org/) — static type checker. Free, MIT.
- [`pytest`](https://docs.pytest.org/) — test runner. Free, MIT.

## Talks (free, YouTube)

- Brett Cannon, "How to write a Python package in 2024" (PyCon 2024). Free; about 45 minutes. The canonical modern-packaging talk.
- Antonio Cuni, "How to make Python fast in 2024" (EuroPython 2024). Free; about 45 minutes.
- Pablo Galindo Salgado, "Memray: a memory profiler for Python" (PyCon 2023). Free; about 30 minutes. The author.
- Sam Gross, "Per-Interpreter GIL and Beyond" (PyCon 2023). Free; about 30 minutes.
- Łukasz Langa, "Python at the speed of light" (PyCon 2024 keynote). Free; about 45 minutes.
- Mark Shannon, "The Faster CPython project: progress and plans" (PyCon 2024). Free; about 30 minutes.
- Raymond Hettinger, "Beyond PEP 8 — Best practices for beautiful intelligible code" (PyCon 2015). Older but still load-bearing for capstones. Free.

## Books (free or library-accessible)

- *Fluent Python*, Luciano Ramalho, 2nd edition (O'Reilly, 2022). Chapter 21 (Coroutines and asyncio) and Chapter 24 (Class metaprogramming) are particularly relevant.
- *CPython Internals*, Anthony Shaw (Real Python, 2021). The most accessible book on CPython internals; first 60 pages cover what we did in W1.
- *High Performance Python*, Micha Gorelick & Ian Ozsvald, 2nd edition (O'Reilly, 2020). The classic book on Python perf engineering; the chapter on C extensions and the chapter on multiprocessing are the most useful for the capstone.

## Hardware and reproducibility

Your benchmark report must state hardware. The minimum information:

- CPU model (e.g. "Apple M3 Pro, 11 cores, 5 performance + 6 efficiency"; "Intel Xeon E5-2680 v4, 14 cores @ 2.4 GHz").
- RAM (e.g. "36 GB unified memory"; "64 GB DDR4").
- OS and version (e.g. "macOS 14.4.1"; "Ubuntu 22.04.4 LTS").
- Python version including build flags (e.g. "CPython 3.13.0, default GIL-enabled build"; "CPython 3.13.0t, free-threaded build").
- Whether the laptop was on battery or AC power (battery power throttles aggressively on most modern laptops; report runs are AC-only).
- Whether thermal throttling occurred (run `pmset -g thermlog` on macOS, `dmesg | grep -i thermal` on Linux; report any throttle event).
- The seed for any random data generation.
- The number of warm-up runs and measurement runs.

A reviewer with the same Python version and a similar machine should be able to land within 20% of your reported numbers. If they cannot, your methodology has a gap; finding the gap is part of the capstone.

## Where the capstone publishes

- **TestPyPI** — <https://test.pypi.org/>. Free, no review, packages persist but are not guaranteed forever. The capstone publishes here.
- **PyPI** — <https://pypi.org/>. The real index. Out of scope for the capstone (we do not publish unfinished work to the real index), but the same `twine upload` command with a different `--repository` flag works once you are ready.

## Naming your capstone package

The PyPI namespace is global and first-come-first-served. To avoid collisions:

- Prefix with `cc-` (Code Crunch).
- Then your handle (e.g. `cc-jane-doe-`).
- Then a kernel descriptor (e.g. `cc-jane-doe-imageperf`).

Examples that should not collide as of the time of writing: `cc-jdoe-blurperf`, `cc-jdoe-sobel`, `cc-jdoe-tinyparser`, `cc-jdoe-ratelim`, `cc-jdoe-mandelbrot`. Check first: `pip index versions cc-<your-name>-<kernel>` should report "no matching distribution" before you proceed.

## On time and scope

You have one week. The exercises walk you through the pipeline on a 50-line script in the first three days. The mini-project — your actual capstone — gets the back four days. Budget your time accordingly. The single most common capstone failure is over-scoping the kernel on Monday and discovering on Saturday that the package does not yet build. **Start small, ship, then expand.** A working 100-line capstone published on TestPyPI on Friday beats a half-finished 1,000-line capstone on Sunday night.
