# Week 8 — C Extensions: ctypes, cffi, Cython

> *Three production paths. One discipline. `ctypes` (Thomas Heller, originally a third-party package, landed in the stdlib in Python 2.5) is a pure-Python foreign-function interface: you point it at a `.so`/`.dylib`/`.dll`, declare argument and return types, and call C from Python with zero build step at install time — the binding is constructed at runtime by reading the shared library's symbol table. `cffi` (Armin Rigo + Maciej Fijalkowski, 2013; the FFI that powers `cryptography`, `bcrypt`, `psycopg2-c`, and most of the security-sensitive end of the data ecosystem) is a two-mode FFI: **ABI mode** for `ctypes`-equivalent runtime binding and **API mode** for a C-compiler-mediated binding that is faster and catches header mismatches at build time. `Cython` (Stefan Behnel, Robert Bradshaw, Sage 2007; née Pyrex, William Stein 2002) is a *language*: you write `.pyx` files in a Python-superset with optional C type annotations, the Cython compiler emits a `.c` file against the CPython C API, you build a `.so`, you `import` it like any module. **This week you learn when each is the right answer, you measure the speedup against pure Python on a numerical kernel, and you ship one production-shaped C extension that makes a Pythonic implementation at least 10x faster.***

Welcome to Week 8 of **C17 · Crunch Pro Python Advanced**, the second week of Phase 3 (Performance & Native Code). Week 7 left you with the profiling toolkit and a discipline: name the hot leaf, name the hot path, propose the fix. The proposal is usually one of four shapes — algorithm change, data-structure change, library replacement, work elimination. This week is the fifth shape, the one you reach for when none of those four is on the table: **drop into C**.

The thesis is small: **pure Python is fast enough for almost everything; for the 1% where it is not, three well-understood paths take you from a Python function to a C-extension function that is 10–500x faster.** The corollary is large: **most engineers who reach for C reach badly.** They write a CPython-C-API extension when `ctypes` would have done. They write `ctypes` when `cffi` would have caught the header drift that ate a weekend. They write Cython when a NumPy vectorisation would have given the same speedup with zero build pipeline. The judgement is in *not* writing C when you do not need to, and in picking the lightest path when you do.

The three paths cover the production grid. **`ctypes`** is the right tool when (a) the C code you want to call already exists, compiled as a `.so`, with a stable ABI, and (b) you want zero build pipeline on the install side — `pip install yourpkg` should not require a C compiler on the user's machine. The cost is per-call overhead (a function-pointer dispatch through libffi, plus argument marshalling) of roughly 1–3 microseconds, and the discipline of declaring `argtypes` and `restype` correctly — `ctypes` cannot read your C headers and will happily corrupt memory if you lie. The win is *truly* zero-build distribution: you ship a wheel with a precompiled `.so` and your Python code calls into it without ever invoking `gcc` on the install machine. This is how `numpy` ships its BLAS calls on its slow path, how most "wrap a vendor DLL" shims work, and how a surprising amount of the embedded-Python ecosystem talks to firmware.

**`cffi`** is the Armin Rigo project from 2013, born out of PyPy's need for a FFI that did not depend on the CPython C API (which PyPy emulates expensively). It is now the FFI of choice for the security-sensitive end of the Python ecosystem: `cryptography` (which wraps OpenSSL), `bcrypt`, `argon2-cffi`, `psycopg2-c`, `nacl`. It has two modes. **ABI mode** is `ctypes`-equivalent — point at a `.so`, declare types in C syntax, call. Slightly nicer ergonomics than `ctypes` (C declarations are parsed from real C-header text instead of Python class definitions), same runtime characteristics. **API mode** is the real win: cffi generates a small C wrapper file at build time, you compile it once with the user's C compiler (or ship a precompiled wheel), and the resulting binding is *faster* than ABI mode (no libffi dispatch; direct C calls) and *safer* (the compiler verifies header-to-call agreement). API mode is what `cryptography` uses; if you are wrapping a non-trivial C library that will live in production, API mode is the default. Repository: <https://github.com/python-cffi/cffi> (note the org name change from `lwfm/cffi` in 2023). Docs: <https://cffi.readthedocs.io/>.

**`Cython`** is the third path and the most expressive. It is not an FFI — it is a *programming language*, a Python superset with optional static typing, that compiles down to C against the CPython C API. You write `.pyx` files that look like Python with `cdef int` annotations sprinkled in, you run `cythonize`, you get a `.so`, you `import`. The win is two-fold. First, *typed* Cython code runs at C speed: `cdef int i` is a real C `int`, the loop body is real C, the call overhead from Python is one C-API boundary crossing. Second, Cython has *first-class NumPy support* via the **buffer protocol** and **typed memoryviews** (`double[:, ::1] arr`) — you can pass NumPy arrays into Cython functions with zero copy and operate on them with plain C-style loops. The cost is the build pipeline: every install requires either a wheel-build CI or a C compiler on the user's machine. The win is performance ceiling: a well-tuned Cython numerical kernel is within a factor of 2 of hand-tuned C, and frequently within 10% of NumPy's own routines. Repository: <https://github.com/cython/cython>. Docs: <https://cython.readthedocs.io/>.

We will, deliberately, **not** go deep on **PyO3** (Rust bindings to CPython, 2017–) or **pybind11** (C++ to CPython, 2016–). Both are excellent. PyO3 is the future for new native modules where you have a choice — Rust's safety guarantees apply to the FFI boundary in a way that C's do not, and the build pipeline (`maturin`) is the most ergonomic of the bunch. pybind11 is the workhorse for the C++ side of the ecosystem (`pytorch`, `tensorflow`, `Open3D`). Both deserve their own week. This week is the *baseline trio* that every Python engineer should be fluent in, because the three together cover ~90% of production C extension work. PyO3 and pybind11 are pointers for Week 12 and beyond.

The fourth comparison point is **the raw CPython C API** itself — writing a `Modules/foo.c` against `Python.h`, defining `PyMethodDef` tables, calling `Py_BuildValue` and `PyArg_ParseTuple`, returning `PyObject *`. This is what every C extension actually compiles down to. Cython generates it; cffi API mode generates it; ctypes bypasses it. We will read 80 lines of a hand-written C extension on Wednesday so you know what your tools are doing — but you will not write a hand-rolled one. The CPython C API is not the right place to start; it is the place you end up when one of the three tools above is unavailable or you are contributing to CPython itself.

The deliverable for the week is a **C-extension benchmark report**. You pick a numerical kernel — 1D convolution is the default; alternatives include a Mandelbrot-set escape-time computation, a Levenshtein-distance implementation, a Black-Scholes option-pricing batch — implement it three ways (pure Python with type hints; one of {ctypes, cffi, Cython}; NumPy as a sanity ceiling), and produce a benchmark report with `timeit` numbers, a per-implementation speedup table, and a 600–900 word memo explaining *why* the speedups are what they are. The memo grounds the numbers in mechanism: the per-call overhead of `ctypes`, the cache-friendliness of the C inner loop, the SIMD vectorisation NumPy gets for free. This is the artifact you point at when an interviewer asks "what does a 100x speedup look like and what did it cost."

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish** the three paths on first principles: explain when `ctypes` is the right choice (existing `.so`, no build pipeline), when `cffi` is (security-sensitive code, header-driven binding, multi-Python-implementation support), and when `Cython` is (greenfield kernel, NumPy interop, performance ceiling). Cite the relevant docs: <https://docs.python.org/3/library/ctypes.html>, <https://cffi.readthedocs.io/>, <https://cython.readthedocs.io/>.
- **Build** a C library (`gcc -shared -fPIC -O2 -o libk.so kernel.c`) and call it from Python via `ctypes`: load via `CDLL`, declare `argtypes` and `restype`, pass arrays via `ctypes.POINTER(c_double)` or via `numpy.ctypeslib.ndpointer`, interpret the return. Articulate why `argtypes`/`restype` are mandatory and what happens when you omit them.
- **Write** a `cffi` binding in both modes: **ABI mode** with `ffi.cdef()` + `ffi.dlopen()`, and **API mode** with `ffi.set_source()` + a `build_module.py` that runs at install time (or once, offline). Measure the per-call overhead of each and explain the difference.
- **Author** a `.pyx` file with typed parameters (`cdef double[::1] arr`), build it with `cythonize -i kernel.pyx` (or via `setup.py` with `Cython.Build.cythonize`), and `import` it. Demonstrate the speedup over equivalent Python and articulate which Cython annotations produced it (`cdef`, `cpdef`, `@cython.boundscheck(False)`, `@cython.wraparound(False)`).
- **Compare** the three implementations of one kernel under `timeit` and (where available) `perf stat`. Tabulate operations-per-second; explain why ctypes is fast for big-N (amortises FFI overhead over many ops) and slow for small-N (one-call overhead dominates); explain why Cython's overhead is per-call into the extension, not per-array-element.
- **Read** a CPython C API extension well enough to understand what `Cython` and `cffi` API mode generate: `PyArg_ParseTuple("dd", &x, &y)`, `Py_BuildValue("d", result)`, `PyMethodDef` and `PyModuleDef`, `PyMODINIT_FUNC`. Cite <https://docs.python.org/3/c-api/index.html>.
- **Apply** PEP 7 (C style guide for CPython) to any C you write that touches the C API: indentation, brace style, naming. Cite <https://peps.python.org/pep-0007/>.
- **Diagnose** the canonical failures: (1) ABI drift — a `ctypes` binding compiled against one `struct` layout, run against a `.so` with a different layout, silent corruption; (2) GIL mishandling — calling a long-running C function without `Py_BEGIN_ALLOW_THREADS`, starving the rest of the program; (3) reference-counting leaks — a hand-written C extension that forgot one `Py_DECREF`, slow memory growth; (4) cache thrash — a Cython 2D inner loop in row-major access pattern on a column-major array, 10x slower than it should be.
- **Decide** between `ctypes`/`cffi`/`Cython` and the *fourth* option — "do not write C; vectorise with NumPy" — by measuring both. The right answer is often the fourth.
- **Cite** the C-API URLs, PEP 7, cffi docs, Cython docs, and the relevant CPython source files (`Modules/_ctypes/_ctypes.c`, `Objects/abstract.c` for buffer protocol).

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | `EECS 280` — Compile and link a multi-file program, and reason about what crosses the boundary between separately built units. |
| Industry | Decide whether a hot loop is worth a native extension at all, and be able to state the maintenance cost before anybody writes a line of C. |
| Beyond the bar | One kernel is written three ways — `ctypes`, `cffi` and Cython — and benchmarked against the fourth option of not writing C at all — `challenges/challenge-01-mandelbrot-three-ways.md` |


## Prerequisites

- **C17 Weeks 1–7** completed. In particular: Week 1 (CPython object model and the C-API surface — `PyObject *`, reference counting, the GIL), Week 3 (the GIL specifically — you cannot reason about a C extension's threading behaviour without it), Week 7 (the profiling discipline — you measure before and after, every time).
- **A working C compiler.** `gcc` 9+ on Linux, `clang` 13+ on macOS (ships with Xcode Command Line Tools), or MSVC on Windows. `gcc --version` or `clang --version` must succeed. If it does not: install `build-essential` (Ubuntu/Debian), Xcode CLT (`xcode-select --install`), or the Windows Build Tools.
- **CPython 3.11+** (3.13 preferred). Cython 3.0+ requires Python 3.7+ and works cleanly on 3.13. cffi 1.16+ supports 3.13. ctypes is stdlib; nothing to install.
- **Working knowledge of C** sufficient to read 50–100 lines of straightforward numerical code: pointers, `for` loops, `malloc`/`free` (we will mostly avoid manual memory management in this week's exercises), function declarations. If C is rusty, allocate 60 minutes Monday evening to skim <https://www.cs.cmu.edu/~213/> Lab 0 or any introductory pointer tutorial.
- A **NumPy** install (`pip install numpy`) — used as the "fourth comparison point" and for the buffer protocol demos.
- **Cython** (`pip install cython`) and **cffi** (`pip install cffi`). Both ship binary wheels for major platforms; no compiler needed for the install, but you do need a compiler to build *your* extensions.

## Topics covered

- **Why drop into C at all** — the four-shape fix taxonomy from Week 7 (algorithm, data structure, library, work elimination), and the fifth shape (drop into C). The Knuth precondition: profile first. The Berger corollary: if the profile shows >50% time in pure Python interpretation, *some* native rewrite is on the table.
- **The CPython C API at a glance** — `PyObject *`, `Py_INCREF`/`Py_DECREF`, the GIL, `PyArg_ParseTuple`, `Py_BuildValue`, `PyMethodDef`, `PyModuleDef`, `PyMODINIT_FUNC`. We read a 60-line hand-written extension. We do not write one. Cite <https://docs.python.org/3/c-api/index.html>.
- **`ctypes` end-to-end** — `CDLL("libfoo.so")`, function-by-name resolution, `argtypes` and `restype`, array passing via `numpy.ctypeslib.ndpointer`, struct passing via `ctypes.Structure`. The per-call overhead (~1 µs) and when it dominates. The ABI-drift failure mode. Cite <https://docs.python.org/3/library/ctypes.html>.
- **`cffi` ABI mode** — `ffi.cdef()` with verbatim C declarations, `ffi.dlopen()`, the same runtime model as ctypes with nicer ergonomics. When to prefer it over ctypes (you have C-header text already; you want to support PyPy). Cite <https://cffi.readthedocs.io/en/latest/overview.html#abi-versus-api>.
- **`cffi` API mode** — `ffi.set_source()` + `ffi.cdef()`, the build step, the compiled `_kernel_cffi.cpython-313-darwin.so` artifact, the speed and safety win. The standard build script pattern. Cite <https://cffi.readthedocs.io/en/latest/cdef.html>.
- **`Cython` end-to-end** — `.pyx` syntax, `cdef int` typed locals, `cpdef` functions (callable from both Python and Cython), `cython -a kernel.pyx` for the annotated HTML output, `cythonize -i` for in-place builds, `setup.py` with `cythonize()`. The directive cheatsheet: `boundscheck`, `wraparound`, `cdivision`, `nonecheck`. Cite <https://cython.readthedocs.io/en/latest/src/userguide/language_basics.html>.
- **Cython + NumPy** — typed memoryviews (`double[:, ::1]`), the buffer protocol, why memoryviews are zero-copy and what `::1` means (C-contiguous). Cite <https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html>.
- **Benchmarking the four paths** — pure Python, ctypes, cffi (one mode), Cython, NumPy (the ceiling). The `timeit` discipline: `repeat=5, number=auto`, take the *minimum* (Python wisdom; the minimum is the least-perturbed). The `perf stat` cross-check on Linux. Speedup tables, ops/second.
- **The GIL and C extensions** — `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` in hand-written C; `with nogil:` blocks in Cython; `release_gil=True` in cffi API mode. When releasing the GIL helps (long C computation, multi-threaded driver) and when it does not (short C call, single-threaded driver).
- **Pointers to the next layer** — PyO3 (Rust + CPython), pybind11 (C++ + CPython), nanobind (modern pybind11 successor). One paragraph each, with repository links, so you know where to go.
- **Free no-build alternatives** — Numba (`@jit` decorator, LLVM-based, ~5 minute install), `np.vectorize` (slow, but trivial), JAX (`@jit`, XLA-based, GPU-friendly). Cited; not the focus of this week.

## Weekly schedule (~33h intensive)

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Why drop into C; the C API at a glance; ctypes overview     | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | `ctypes` deep dive; first .so + first binding               | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Wednesday | `cffi` (ABI + API mode); `Cython` intro                     | 2h       | 1.5h      | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 6.5h        |
| Thursday  | Cython with NumPy memoryviews; mini-project kickoff         | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Friday    | Mini-project: implement the kernel three ways               | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Saturday  | Mini-project: benchmark, memo, polish                       | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                            | 0h       | 0h        | 0h         | 0.5h      | 1h       | 0h           | 0h         | 1.5h        |
| **Total** |                                                             | **6h**   | **4.5h**  | **3h**     | **3h**    | **7h**   | **7h**       | **2.5h**   | **33h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | ctypes / cffi / Cython docs, PEP 7, the C API URLs, CPython source pointers, PyO3 and pybind11 links |
| [lecture-notes/01-why-c-extensions-and-the-c-api.md](./lecture-notes/01-why-c-extensions-and-the-c-api.md) | When to drop into C; the CPython C API in 60 lines; reading a hand-written extension; the GIL implications |
| [lecture-notes/02-ctypes-and-cffi.md](./lecture-notes/02-ctypes-and-cffi.md) | `ctypes.CDLL`, `argtypes`/`restype`, struct passing; `cffi` ABI vs. API mode; when to pick each |
| [lecture-notes/03-cython-and-the-benchmark.md](./lecture-notes/03-cython-and-the-benchmark.md) | `.pyx` syntax; typed memoryviews; the build step; the four-way benchmark on a 1D convolution kernel |
| [exercises/exercise-01-ctypes-first-binding.py](./exercises/exercise-01-ctypes-first-binding.py) | Compile a 30-line C file; load via ctypes; call a `sum_squares` function on a NumPy array |
| [exercises/exercise-01-kernel.c](./exercises/exercise-01-kernel.c) | The C source for Exercise 1 |
| [exercises/exercise-02-cffi-abi-and-api.py](./exercises/exercise-02-cffi-abi-and-api.py) | The same kernel via cffi ABI; then API mode; compare per-call overhead |
| [exercises/exercise-02-build_cffi.py](./exercises/exercise-02-build_cffi.py) | The cffi API-mode build script |
| [exercises/exercise-03-cython-convolution.py](./exercises/exercise-03-cython-convolution.py) | A Cython `.pyx` for 1D convolution; build via `cythonize`; benchmark vs. pure Python |
| [exercises/exercise-03-convolve.pyx](./exercises/exercise-03-convolve.pyx) | The Cython source for Exercise 3 |
| [exercises/SOLUTIONS.md](./exercises/SOLUTIONS.md) | Expected speedups, common build errors, the reasoning |
| [challenges/challenge-01-mandelbrot-three-ways.md](./challenges/challenge-01-mandelbrot-three-ways.md) | Implement Mandelbrot escape-time in pure Python, ctypes, and Cython; benchmark; explain the ratios |
| [challenges/challenge-02-gil-release.md](./challenges/challenge-02-gil-release.md) | A long-running C function; release the GIL; measure the speedup under threads vs. without |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~7h) |
| [mini-project/README.md](./mini-project/README.md) | Speed up a Pythonic numerical kernel by 10x or more via one of the three paths; ship a benchmark report |

## Stretch

- Read PEP 7 end-to-end (~15 minutes): <https://peps.python.org/pep-0007/>. C style guide for CPython. Brace placement, indentation, naming. Every line of C you write that touches the C API should conform.
- Read [`Modules/_ctypes/_ctypes.c`](https://github.com/python/cpython/blob/main/Modules/_ctypes/_ctypes.c) — the C implementation of `ctypes`. Skim the first 300 lines (the `CDataObject` definition, the `CFuncPtr_call` function). About 30 minutes. The takeaway: ctypes is a thin wrapper around libffi (`Modules/_ctypes/libffi/`); every call goes through a libffi dispatch.
- Build PyPy from source (or `pip install pypy3`) and run the same cffi binding under PyPy. cffi was designed for this; expect the *cffi binding itself* to run at native speed on PyPy. ~30 minutes.
- Read the [Cython `Cython/Compiler/`](https://github.com/cython/cython/tree/master/Cython/Compiler) source — start with `Compiler/Main.py` (the entry point) and `Compiler/Code.py` (the C code generator). About 60 minutes. The takeaway: Cython is a real compiler with a lexer, parser, type inferencer, and code generator.
- Read [PEP 384](https://peps.python.org/pep-0384/) — Defining a Stable ABI for CPython extension modules. About 30 minutes. The PEP that makes "ship one wheel for all Python versions" feasible for some extensions. Adopted slowly; relevant for distribution.
- Watch one talk by **Stefan Behnel** (Cython maintainer) on Cython internals — search "Stefan Behnel Cython" on YouTube; the EuroPython talks are typically free. ~45 minutes.
- Read the [PyO3 user guide's "Migrating from CPython C API" page](https://pyo3.rs/) (~30 minutes). The future. Even if you do not write Rust this year, knowing what PyO3 looks like makes a 2027 conversation easier.
- Read [Cython's "Numpy tutorial"](https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html) end-to-end (~25 minutes). The buffer-protocol mental model is the same shape as the `array` and `memoryview` work from Week 1.

## Up next

[Week 9 — Memory Layout, NumPy, and the Buffer Protocol](../week-09-memory-layout-numpy-buffer-protocol/) — You touched memoryviews this week; next week we go deeper. Why C-contiguous matters. Why a transpose is free in NumPy but a copy in C. The cost of a cache miss in numbers. The buffer protocol as the *real* interop layer of the Python ecosystem.
