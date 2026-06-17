# Week 8 — Resources

All free. Free + open tools only. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — stdlib and CPython source tree

| What | Where |
|------|-------|
| **`ctypes` module docs** (canonical reference for the stdlib FFI) | <https://docs.python.org/3/library/ctypes.html> |
| **`ctypes.Structure`, `Union`, `Array`** (struct/union/array marshalling) | <https://docs.python.org/3/library/ctypes.html#structures-and-unions> |
| **`ctypes.CDLL`, `WinDLL`, `OleDLL`** (the loaders) | <https://docs.python.org/3/library/ctypes.html#loading-dynamic-link-libraries> |
| **CPython C API — index** (the surface that every native extension uses) | <https://docs.python.org/3/c-api/index.html> |
| **C API — Extending and Embedding** (the tutorial; the canonical "first C extension") | <https://docs.python.org/3/extending/extending.html> |
| **C API — Reference counting** (`Py_INCREF`, `Py_DECREF`, the ownership rules) | <https://docs.python.org/3/c-api/refcounting.html> |
| **C API — Argument parsing** (`PyArg_ParseTuple`, format strings) | <https://docs.python.org/3/c-api/arg.html> |
| **C API — Module initialisation** (`PyModuleDef`, `PyMODINIT_FUNC`) | <https://docs.python.org/3/c-api/module.html> |
| **C API — Buffer protocol** (the zero-copy interop layer; NumPy, memoryview, Cython memoryviews) | <https://docs.python.org/3/c-api/buffer.html> |
| **`array` module docs** (the stdlib typed-array; useful for ctypes without NumPy) | <https://docs.python.org/3/library/array.html> |
| **`memoryview` docs** (the Python-level handle on a buffer) | <https://docs.python.org/3/library/stdtypes.html#memoryview> |
| **`Modules/_ctypes/_ctypes.c`** (the C implementation of ctypes; a wrapper around libffi) | <https://github.com/python/cpython/blob/main/Modules/_ctypes/_ctypes.c> |
| **`Modules/_ctypes/callproc.c`** (the call-into-C path; libffi dispatch) | <https://github.com/python/cpython/blob/main/Modules/_ctypes/callproc.c> |
| **`Lib/ctypes/__init__.py`** (the Python-side wrappers) | <https://github.com/python/cpython/blob/main/Lib/ctypes/__init__.py> |
| **`Modules/_testcapi.c`** (CPython's own test extension; an instructive read of "C extension in CPython style") | <https://github.com/python/cpython/blob/main/Modules/_testcapi.c> |

## Required PEPs

- **PEP 7 — Style Guide for C Code** (van Rossum, Warsaw, 2001): <https://peps.python.org/pep-0007/>
  *The style guide for any C in CPython. K&R braces, 4-space indent, no tabs in new code, max 79 columns. Every line of C you write that will be reviewed by a CPython core developer must conform. Even outside CPython, conforming is the norm in the extension ecosystem. ~15 minutes.*
- **PEP 384 — Defining a Stable ABI** (Lemburg, von Löwis, 2010): <https://peps.python.org/pep-0384/>
  *The "limited API" — a subset of the C API that is guaranteed stable across Python 3.x versions. Extensions built against the limited API can be loaded by any 3.x interpreter without rebuild. Adoption has been slow but is increasing; `cryptography` and a few others ship limited-API wheels. ~30 minutes.*
- **PEP 489 — Multi-phase extension module initialization** (Viktorin, 2013): <https://peps.python.org/pep-0489/>
  *The modern module-init contract. Replaces the legacy single-phase `PyMODINIT_FUNC PyInit_foo(void) { return PyModule_Create(...); }`. Required for sub-interpreters; preferred for everything else. Cython 3.0+ emits multi-phase init by default. ~25 minutes.*
- **PEP 3118 — Revising the buffer protocol** (Travis Oliphant et al., 2006): <https://peps.python.org/pep-3118/>
  *The buffer protocol — how NumPy arrays, `memoryview`, `bytes`, `bytearray`, Cython memoryviews, PIL images, and audio buffers all interoperate without copying. The most important interop PEP in the data-science end of the ecosystem. ~40 minutes.*

Optional, of interest:

- **PEP 587 — Python Initialization Configuration** (Stinner, 2019): <https://peps.python.org/pep-0587/>
  *Relevant if you embed Python in a C/C++ host. Not the main path this week.*

## `ctypes` — the stdlib FFI

`ctypes` is the stdlib foreign-function interface. Thomas Heller; landed in 2.5 (2006). No build step; no compile-time binding.

- **The `ctypes` user guide** — read §15.17.1 (Tutorial) end-to-end before Tuesday: <https://docs.python.org/3/library/ctypes.html#ctypes-tutorial>.
- **The `ctypes.Structure` reference** — passing C structs by value or by pointer: <https://docs.python.org/3/library/ctypes.html#structures-and-unions>.
- **The data-types table** — `c_int`, `c_long`, `c_double`, `c_char_p`, `c_void_p`, `c_size_t`. Memorise the first six: <https://docs.python.org/3/library/ctypes.html#fundamental-data-types>.
- **`numpy.ctypeslib.ndpointer`** — the canonical adapter for "pass a NumPy array to a C function": <https://numpy.org/doc/stable/reference/routines.ctypeslib.html>.
- **`ctypes` source in CPython** — `Lib/ctypes/__init__.py` and `Modules/_ctypes/`. The Python side is ~1500 lines; the C side wraps libffi.

## `cffi` — Armin Rigo's FFI; the cryptography stack's choice

cffi is the production-grade FFI. Armin Rigo, Maciej Fijalkowski, 2013. Used by `cryptography`, `bcrypt`, `psycopg2-c`, `argon2-cffi`, `nacl`.

- **`cffi` documentation home** — <https://cffi.readthedocs.io/>. Read the "Overview" page end-to-end before Wednesday.
- **`cffi` ABI vs. API** — the *fundamental* decision in cffi. The doc page is essential: <https://cffi.readthedocs.io/en/latest/overview.html#abi-versus-api-level>.
- **`cffi.cdef()` reference** — how to declare C signatures and types from real C-header text: <https://cffi.readthedocs.io/en/latest/cdef.html>.
- **`cffi.set_source()` reference** — API mode's build-time entry point: <https://cffi.readthedocs.io/en/latest/cdef.html#ffi-set-source-preparing-out-of-line-modules>.
- **`cffi` PyPI** — <https://pypi.org/project/cffi/>. Ships binary wheels for major platforms.
- **`cffi` GitHub** — <https://github.com/python-cffi/cffi> (note the org name; was `lwfm/cffi`, now community-maintained).
- **The `cryptography` library's `_openssl.py` cffi binding** — the most-read production cffi binding in the world. ~5000 lines of `ffi.cdef`. <https://github.com/pyca/cryptography/blob/main/src/_cffi_src/build_openssl.py>. Read for shape, not detail.

## `Cython` — the Python-superset compiler

Cython is a *language*, not a binding library. Stefan Behnel and the Cython core team; née Pyrex (William Stein, 2002); Cython since 2007.

- **Cython documentation home** — <https://cython.readthedocs.io/>. Read the "Tutorials" overview before Wednesday.
- **Cython "Basic Tutorial"** — the hello-world: `.pyx`, `cythonize`, the build. <https://cython.readthedocs.io/en/latest/src/tutorial/cython_tutorial.html>.
- **Cython "Language Basics"** — `cdef`, `cpdef`, `def`, types, the C/Python boundary: <https://cython.readthedocs.io/en/latest/src/userguide/language_basics.html>.
- **Cython "Typed Memoryviews"** — the zero-copy interop with NumPy and other buffer-protocol producers: <https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html>.
- **Cython "NumPy tutorial"** — the canonical worked example; read it after Wednesday's lecture: <https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html>.
- **Cython "Compiler directives"** — `boundscheck`, `wraparound`, `cdivision`, `nonecheck`, `initializedcheck`, `language_level`: <https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#compiler-directives>.
- **Cython "Profiling tutorial"** — wiring Cython modules into `cProfile`: <https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html>.
- **`cython -a kernel.pyx`** — the annotated HTML output. Yellow lines = expensive Python-API calls; white lines = pure C. Inspect for every kernel you write. Documented in the "Compilation" section.
- **Cython GitHub** — <https://github.com/cython/cython>. The compiler source is in `Cython/Compiler/`; the runtime helpers in `Cython/Includes/`.
- **Cython PyPI** — <https://pypi.org/project/Cython/>.

## The CPython C API — for reading

You will not write a hand-rolled C extension this week. You will read one. These are the references when you do.

- **"Extending Python with C or C++"** — the canonical tutorial: <https://docs.python.org/3/extending/extending.html>.
- **"Defining Extension Types"** — when you need a new Python type implemented in C: <https://docs.python.org/3/extending/newtypes_tutorial.html>.
- **"Python/C API Reference Manual"** — the full reference: <https://docs.python.org/3/c-api/>.
- **`PyArg_ParseTuple` format strings** — the lookup table for "how do I parse a `(double, double, int)` tuple": <https://docs.python.org/3/c-api/arg.html#parsing-arguments>.
- **`Py_BuildValue` format strings** — the mirror table for "how do I return a Python int from a C `int`": <https://docs.python.org/3/c-api/arg.html#building-values>.
- **The GIL — `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`** — releasing the GIL around long C work: <https://docs.python.org/3/c-api/init.html#releasing-the-gil-from-extension-code>.

## Adjacent tools (cited; not required)

- **PyO3** — Rust bindings to CPython. The most ergonomic native-extension toolchain in 2026. `maturin` for builds. <https://github.com/PyO3/pyo3>. Docs: <https://pyo3.rs/>.
- **pybind11** — C++11+ bindings to CPython. The C++ workhorse. <https://github.com/pybind/pybind11>. Docs: <https://pybind11.readthedocs.io/>.
- **nanobind** — pybind11's successor, by the same author (Wenzel Jakob). Smaller, faster, requires C++17+. <https://github.com/wjakob/nanobind>.
- **Numba** — `@jit` decorator, LLVM-based, no separate compile step. Free, pip-installable, works on NumPy arrays. <https://numba.pydata.org/>.
- **JAX** — `@jit` with XLA backend; the JIT-compiled NumPy. CPU and GPU. <https://github.com/google/jax>.
- **mypyc** — the mypy team's experimental Python-to-C compiler that uses your existing type hints. Used inside mypy itself. <https://mypyc.readthedocs.io/>.
- **f2py** — Fortran to Python; ships with NumPy. The original "compile a numerical kernel and call from Python" path; predates ctypes. Relevant if you encounter Fortran code in scientific computing. <https://numpy.org/doc/stable/f2py/>.
- **SWIG** — the legacy interface generator that originated the multi-language wrapping pattern. Mentioned for historical context; not the recommended path for new code. <https://www.swig.org/>.

These are cited so you know they exist. **The week's required tools are `ctypes` (stdlib), `cffi`, `Cython`.** Add `numpy` for the buffer-protocol demos.

## Background reading — the canon

- **Travis Oliphant, *Guide to NumPy*, 2nd ed. (CreateSpace, 2015).** Chapter 11 covers the buffer protocol and C-side array access. Not free in print, but the *NumPy* documentation covers the same ground: <https://numpy.org/doc/stable/reference/c-api/index.html>.
- **The CPython "Extending and Embedding" tutorial** — read end-to-end (~45 minutes) at least once in your career. The reference C extension (the `spam` module) is the shape every hand-written extension takes: <https://docs.python.org/3/extending/extending.html>.
- **Sturla Molden, "Python C extensions: a tutorial":** <https://www.crashcourse.io/tutorial/python-c-extension>. Practical, short, free. The author has built more numerical Python C extensions than most.
- **Stefan Behnel's PyCon talks on Cython** — search "Stefan Behnel Cython PyCon" on YouTube. The "Fast Native Code for Python" and "What's New in Cython" talks are the maintained "state of Cython" status reports. Free.
- **The `cryptography` library's design doc** — a public discussion of *why* they chose cffi over ctypes and over hand-written C: <https://cryptography.io/en/latest/faq/#why-not-use-ctypes>. ~5 minutes; the most useful "cffi vs. ctypes" essay you will find.
- **Armin Rigo, "cffi 1.0: The Definite Guide" (2015):** archived at <https://lwn.net/Articles/615858/>. The motivation post from the cffi author. About 15 minutes.
- **Brett Cannon, "Why does Python need PyO3 and pybind11?" (2022):** <https://snarky.ca/>. Search for the post. About 10 minutes; the case for native extensions in the modern era.
- **Itamar Turner-Trauring's "Python's `ctypes`: A tutorial" and "Cython vs. cffi vs. ctypes":** <https://pythonspeed.com/articles/python-c-extensions/>. Short, practical, free.

## Optional installs (all pip-installable, all free)

| Tool | Install | Used in |
|------|---------|---------|
| `ctypes` (stdlib) | (built-in) | Lecture 1, 2; Exercise 1; mini-project |
| `cffi` | `pip install cffi` | Lecture 2; Exercise 2; mini-project |
| `Cython` | `pip install cython` | Lecture 3; Exercise 3; Challenge 1, 2; mini-project |
| `numpy` | `pip install numpy` | All exercises (the comparison ceiling) |
| `pytest` | `pip install pytest` | Homework |
| `numba` | `pip install numba` (optional) | Stretch / mentioned only |
| `pyperf` | `pip install pyperf` (optional) | Mini-project (rigorous benchmarking) |

You also need:

- **A C compiler.** `gcc` 9+ (Linux), `clang` 13+ (macOS, via Xcode CLT), or MSVC 2019+ (Windows). Verify with `gcc --version` or `clang --version` or `cl /?`.
- **`make`** for the example Makefiles in the exercises. Optional; the exercises also document the raw `gcc` line.

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `ctypes` Python wrapper | `Lib/ctypes/__init__.py` |
| `ctypes` C implementation | `Modules/_ctypes/_ctypes.c` |
| `ctypes` call dispatch (libffi bridge) | `Modules/_ctypes/callproc.c` |
| libffi (vendored) | `Modules/_ctypes/libffi/` |
| `array` module C source | `Modules/arraymodule.c` |
| Buffer protocol C surface | `Objects/abstract.c` — search for `PyObject_GetBuffer` |
| `memoryview` C source | `Objects/memoryobject.c` |
| `PyArg_ParseTuple` implementation | `Python/getargs.c` |
| `Py_BuildValue` implementation | `Python/modsupport.c` |
| `PyModule_Create` implementation | `Objects/moduleobject.c` |
| The example "Modules/spam.c" referenced by the C extension tutorial | `Modules/xxlimited.c` (the modern equivalent; uses limited API) |

## Glossary

| Term | Definition |
|------|------------|
| **FFI (Foreign Function Interface)** | A mechanism to call functions written in one language from another. In Python, `ctypes` and `cffi` are FFIs to C; PyO3 is an FFI to Rust; pybind11 is to C++. |
| **ABI (Application Binary Interface)** | The runtime contract between compiled code: calling conventions, register usage, struct layouts. Two libraries with the same API can have different ABIs. `ctypes` binds at ABI level. |
| **API (Application Programming Interface)** | The source-code contract: function signatures, header declarations. `cffi` API mode binds at API level via a C compiler. |
| **`.so` / `.dylib` / `.dll`** | Shared library files. Linux: `libfoo.so`. macOS: `libfoo.dylib` (or `.so` for Python-loaded). Windows: `foo.dll`. |
| **`-fPIC`** | "Position-independent code" — the compiler flag required for shared libraries on Linux/macOS. `gcc -shared -fPIC -O2 -o libk.so kernel.c`. |
| **`PyObject *`** | The opaque pointer type that every Python value is, at the C level. Reference-counted. |
| **`Py_INCREF` / `Py_DECREF`** | Macros that increment/decrement a `PyObject`'s reference count. The single most error-prone aspect of hand-written C extensions. |
| **GIL (Global Interpreter Lock)** | CPython's coarse-grained lock on interpreter state. C extensions can release it via `Py_BEGIN_ALLOW_THREADS` for long pure-C computations, allowing other threads to run. |
| **`PyMODINIT_FUNC`** | The macro for the module init function's return type. Each extension module exports exactly one `PyInit_<modname>` function with this return type. |
| **`PyMethodDef`** | A C struct that describes one Python-callable function: name, function pointer, argument convention, docstring. |
| **`PyArg_ParseTuple`** | The C function that converts a Python argument tuple into C values. Format strings: `"i"` for int, `"d"` for double, `"s"` for string, `"O"` for any object. |
| **Buffer protocol** | The interop layer that lets a `bytes`, `bytearray`, `array.array`, `memoryview`, NumPy array, or Cython memoryview share a raw memory region without copying. PEP 3118. |
| **C-contiguous** | Array memory layout where the rightmost index varies fastest — row-major. The default for C and for NumPy arrays. Cython syntax: `double[::1]` (1D) or `double[:, ::1]` (2D). |
| **F-contiguous** | Fortran-style column-major: leftmost index varies fastest. Common in scientific libraries. Cython syntax: `double[::1, :]`. |
| **Typed memoryview** | A Cython type (`cdef double[::1] x`) that gives C-speed access to buffer-protocol data without the Python-object overhead. Zero copy. |
| **`cythonize`** | The Cython build helper. Reads `.pyx`, generates `.c`, invokes the C compiler, produces a `.so`. Used in `setup.py` or as a CLI. |
| **`cython -a`** | The annotation flag: generates an HTML report colouring lines by Python-API usage. Yellow = expensive (Python object call); white = pure C. Essential for tuning. |
| **`@cython.boundscheck(False)`** | A Cython directive that disables array bounds checking. Speeds up tight loops; introduces UB if you index out of bounds. Use *after* you have tested. |
| **`@cython.wraparound(False)`** | A Cython directive that disables Python-style negative indexing (`arr[-1]`). Speeds up tight loops; do not use negative indices if you set this. |
| **`with nogil:`** | A Cython block that releases the GIL. The code inside must not touch any Python objects — only C-typed locals and memoryview slices. |
| **libffi** | A C library for invoking arbitrary C functions at runtime given a description of their signature. The substrate of `ctypes` and `cffi` ABI mode. <https://sourceware.org/libffi/>. |
| **PEP 7** | The C style guide for CPython. K&R braces, 4-space indent, ~79 columns. Applies to every C file in the CPython tree. |
| **Stable ABI / Limited API** | PEP 384. A subset of the C API guaranteed stable across 3.x releases. Extensions built against it work on any 3.x interpreter without rebuild. Files: `Include/cpython/` is full API; `Include/` (top level) is stable. |
| **Multi-phase init** | PEP 489. The modern module-init pattern: `PyModuleDef_Init` + `Py_mod_exec` slot, instead of returning a module from `PyInit_foo`. Required for sub-interpreters. |

---

*Broken link? Open an issue.*
