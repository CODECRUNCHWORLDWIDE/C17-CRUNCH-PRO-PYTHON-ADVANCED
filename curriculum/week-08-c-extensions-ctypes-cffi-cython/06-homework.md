# Week 8 — Homework

Six problems, ~7 hours total. Commit each as you finish.

---

## Problem 1 — Read a hand-written CPython C extension (60 min)

Open `Modules/xxlimited.c` in the CPython source tree: <https://github.com/python/cpython/blob/main/Modules/xxlimited.c>. This is CPython's reference example for "how to write a C extension using only the limited (PEP 384) API." ~300 lines.

Read it end-to-end. Find:

- The `Xxo_Type` definition — a new Python type defined in C.
- The `Xxo_new` / `Xxo_dealloc` functions — `__new__` and `__del__` at the C level.
- The `Xxo_demo` method — an instance method implemented in C.
- The `xx_exec` function — the multi-phase init slot (PEP 489).
- The `xx_module` definition — `PyModuleDef` with the slots filled in.

Then open `Modules/_testcapi.c` (a few hundred lines into it; the file is huge — search for `PyArg_ParseTuple` and `Py_BuildValue` examples): <https://github.com/python/cpython/blob/main/Modules/_testcapi.c>.

**Acceptance:** `c-extension-reading.md` in your portfolio:

- A GitHub permalink to `Xxo_demo`.
- A 250-word walkthrough of how `Xxo_demo` is called from Python: from `obj.demo(arg)` to the C function returning a `PyObject *`. Cover argument parsing, the work, the return-value construction.
- One observation about PEP 489 multi-phase init: why is `xx_exec` separate from `xx_module`?
- One observation about reference counting: where in `Xxo_new` or `Xxo_dealloc` is the ref count touched, and what would happen if you forgot the corresponding `Py_INCREF` or `Py_DECREF`?

---

## Problem 2 — Write your own `ctypes` binding to `libm` (45 min)

You do not need to write any C for this one. `libm` is the system math library. Bind a handful of functions from it.

Choose four functions from `libm` (see `man 3 math` for the list): `sqrt`, `pow`, `sin`, `log`, `erf`, `tgamma`, `lgamma`. Write a Python module `mylibm.py` that loads `libm` via ctypes and exposes typed wrappers.

A skeleton:

```python
import ctypes
import ctypes.util

_libm = ctypes.CDLL(ctypes.util.find_library("m"))

_libm.sqrt.argtypes = [ctypes.c_double]
_libm.sqrt.restype = ctypes.c_double

def sqrt(x: float) -> float:
    """sqrt(x). Calls libm sqrt(3) directly."""
    return _libm.sqrt(x)
```

Compare the speed of your `mylibm.sqrt` against Python's `math.sqrt` using `timeit`. Expected result: `math.sqrt` is *faster* because it is implemented as a CPython C extension with direct dispatch; ctypes adds libffi overhead.

**Acceptance:** `libm-binding.md` plus `mylibm.py`:

- The four functions bound, with `argtypes` and `restype` set.
- A docstring on each Python wrapper.
- A 150-word commentary on why `math.sqrt` is faster than `ctypes-libm-sqrt` despite both calling the same C function: per-call overhead. Reference Lecture 2 §3.3.
- A `pytest`-style test that verifies each function against `math.X` on 100 random inputs.

---

## Problem 3 — Convert one Python function from your portfolio to Cython (90 min)

Open any function from Week 5, 6, or 7 that does meaningful numerical work. The async crawler from Week 5 is *not* a good candidate (it is IO-bound). The Monte-Carlo simulation from Week 6 Exercise 1 *is*. Anything CPU-bound with a tight numerical inner loop works.

Steps:

1. Create a `port_to_cython/` folder.
2. Copy the function into a `.pyx` file. Rename it (suffix `_cy`) so you can run both side by side.
3. Add `cdef` type declarations to every local variable in the inner loop. Use `Py_ssize_t` for indices, `double` or `int` for values.
4. If the function operates on arrays, change the parameter types to memoryviews (`double[::1]`).
5. Build with `cythonize -i your_file.pyx`.
6. Run `cython -a your_file.pyx` and verify the inner loop is white.
7. Benchmark the Python version against the Cython version with `timeit`. Take the minimum of 5 runs.

**Acceptance:** `cython-port.md` plus the files:

- The original Python function and the Cython port, side by side.
- The annotated HTML output, committed.
- A 200-word commentary:
  - What types did you add? What did each one buy?
  - Was the inner loop white the first time, or did you have to iterate? What surprised you?
  - The measured speedup. Was it close to what you expected from the lectures?
- If the speedup is less than 20x, write an additional paragraph explaining why (likely: the function spends most of its time in something other than the typed loop, e.g. a list comprehension, a dict lookup, a regex match).

---

## Problem 4 — Use `cffi` to bind to an existing system library (60 min)

Pick a non-trivial system library you have installed: `libssl` (OpenSSL), `libz` (zlib), `libsqlite3`, `libcurl`. Pick one function from it to bind via cffi ABI mode. Suggested functions:

- `libz`: `crc32(unsigned long crc, const unsigned char *buf, unsigned int len)`.
- `libsqlite3`: `sqlite3_libversion()`. (Returns a `const char *`.)
- `libssl`: `OpenSSL_version_num()`. (Returns an unsigned long.)

Write `crc32.py` (or whichever function) that uses `cffi.FFI()` + `ffi.cdef()` + `ffi.dlopen()`. Verify the result matches a known-good implementation (e.g., `zlib.crc32(b"hello")` for `crc32`).

**Acceptance:** `cffi-system-binding.md` plus the binding:

- The library you picked, the function, the cffi binding.
- A `pytest` test verifying the cffi binding agrees with the Python stdlib equivalent.
- A 150-word commentary:
  - Why ABI mode here? (You do not own the library; no build step is acceptable.)
  - Compare the binding to what a ctypes equivalent would look like. Which is cleaner?
  - Would you reach for cffi or ctypes for this kind of system-library shim? Why?

---

## Problem 5 — Benchmark Numba against your Cython port (60 min)

Install Numba (`pip install numba`). Take the Python function from Problem 3 and add a `@numba.njit` decorator. Time it.

```python
import numba

@numba.njit
def your_function_numba(x: np.ndarray) -> np.ndarray:
    ...
```

Compare:

- Pure Python: time it.
- Cython port from Problem 3: time it.
- Numba JIT: time it.
- NumPy equivalent (if you can write one): time it.

Numba's first-call latency is significant (the JIT compile happens on first call). Time the *second* call onwards, or use `numba.types.float64(...)` AOT signature to compile ahead of time.

**Acceptance:** `numba-comparison.md`:

- The four implementations, side by side.
- A table of timings.
- A 200-word commentary:
  - How close is Numba to Cython?
  - What is the price you pay for Numba's no-separate-build property? (Hint: first-call latency; restricted Python subset; CPython-only.)
  - In what scenario would you pick Numba over Cython? (Hint: prototype-level, you do not want a build pipeline, you can tolerate the first-call hit.)
  - In what scenario would you pick Cython over Numba? (Hint: production wheel distribution, NumPy interop is critical, you want PyPy support.)

---

## Problem 6 — Read the `cryptography` library's cffi binding (90 min)

Open the `cryptography` Python library's source: <https://github.com/pyca/cryptography>. Navigate to `src/_cffi_src/`. This directory contains the cffi API-mode build scripts for the OpenSSL binding — the single most-used cffi binding in production Python.

Read `src/_cffi_src/build_openssl.py`: <https://github.com/pyca/cryptography/blob/main/src/_cffi_src/build_openssl.py>. ~200 lines, plus it `#include`s many `.h` files from `src/_cffi_src/openssl/`.

Pick three `.h` files from `src/_cffi_src/openssl/` to read (any three — `rand.h` and `ssl.h` are short and approachable; `evp.h` is longer).

**Acceptance:** `cryptography-cffi-reading.md`:

- The three `.h` files you read, with one-paragraph summaries of each.
- A 300-word commentary on the cryptography library's binding architecture:
  - How is the C interface declared? (Hint: `TYPES`, `FUNCTIONS`, `MACROS` strings; cffi parses them.)
  - How is the `set_source` populated? (Hint: it `#include`s OpenSSL's headers.)
  - Why API mode here, not ABI mode? (Hint: OpenSSL version drift; struct layout changes; build-time verification.)
  - One question you would ask the cryptography maintainers about the binding.

This problem is optional but recommended. It is the single best way to see a real, production-grade cffi binding. The pattern you read here is the pattern any non-trivial wrapper takes.

---

## Submission

Commit all files under `c17-week-08-homework/` in your portfolio repo. The expected shape:

```
c17-week-08-homework/
  c-extension-reading.md
  libm-binding.md
  mylibm.py
  cython-port/
    your_function.py
    your_function.pyx
    your_function.html      # cython -a output
  cython-port.md
  cffi-system-binding.md
  crc32.py                   # (or whichever you chose)
  numba-comparison.md
  cryptography-cffi-reading.md   # if Problem 6 attempted
```

If Problem 6 took too long, ship Problems 1–5 by the end of Sunday and tackle Problem 6 the following weekend as a stretch. The minimum bar is Problems 1, 2, 3, and either 4 or 5; the full set is the target.

## Rubric

The rubric for grading (your own self-grading):

| Criterion | Excellent (5) | Adequate (3) | Below (1) |
|-----------|---------------|--------------|-----------|
| **C-API reading depth** (Problem 1) | Walkthrough names every macro, traces ref counts, observes PEP 489 implications | Walkthrough is correct but mechanical | Vague summary; no ref-count observation |
| **Binding correctness** (Problems 2, 4) | `argtypes`/`restype` on every binding; tests pass; bindings agree with Python equivalent to floating-point tolerance | Bindings work but are missing one of {argtypes, tests, comparison}` | Binding "works" only on the demo case; no tests |
| **Cython speedup** (Problem 3) | >=20x speedup; annotated HTML is mostly white in inner loop; commentary explains *why* the speedup is what it is | 5–20x speedup; some yellow lines remain | <5x speedup; no annotated HTML inspection |
| **Numba comparison** (Problem 5) | Four implementations timed; first-call latency accounted for; commentary picks the right tool for the right scenario | Three of four implementations; commentary present | Two implementations; no commentary |
| **cryptography reading** (Problem 6) | Three headers summarised; binding architecture explained; one informed question for the maintainers | Headers read; some architecture explained | Skimmed the index; no specific reading |

Self-grade. The point is the deliverables you can show, not the score.

## Reading

- Lecture 1 §§3, 4 (the C API in 60 lines; the GIL).
- Lecture 2 §§3–5 (ctypes binding; cffi ABI vs API).
- Lecture 3 §§2.2–2.4 (typed Cython; `nogil`; bounds checks).
- The CPython "Extending and Embedding" tutorial: <https://docs.python.org/3/extending/extending.html>.
- The cffi documentation overview: <https://cffi.readthedocs.io/en/latest/overview.html>.
- PEP 7 (C style guide): <https://peps.python.org/pep-0007/>.
- PEP 384 (limited API): <https://peps.python.org/pep-0384/>.
- PEP 489 (multi-phase init): <https://peps.python.org/pep-0489/>.

## Notes

- **`argtypes` and `restype` on every ctypes binding.** Without exception. The five seconds you save by skipping them are paid back, with interest, in three hours of debugging memory corruption.
- **Run `cython -a` on every Cython kernel.** Yellow lines in the inner loop are the diagnostic for "you have not added enough types."
- **Profile before and after every change.** The number that matters is what `timeit` reports, not what your intuition reports.
- **The homework builds reflexes.** Problem 1 builds the "read C extension" reflex. Problem 2 builds the "bind a system library" reflex. Problem 3 builds the "port a hot function" reflex. Each one is what you will reach for in a real performance task. Skipping the easy ones and only doing Problem 6 robs you of the muscle build.
