# Lecture 3 — Cython and the Four-Way Benchmark on a 1D Convolution

> **Duration:** ~2 hours. **Outcome:** You can write a `.pyx` file with typed parameters and typed memoryviews; you can build it via `cythonize -i` or via `setup.py`; you can read the annotated HTML and identify which lines are "still Python" and which are "now C"; you can release the GIL around a numerical loop; you can run the four-way benchmark (Python / ctypes / Cython / NumPy) on a 1D convolution kernel and read the resulting speedup table critically. By the end of the lecture, you have one numerical kernel implemented four ways and a clear sense of what each path bought you.

## 1. The plan

We bind a `sum_squares` function three ways in Lecture 2. This lecture upgrades:

- The kernel is **1D convolution** — a real numerical primitive with a non-trivial inner loop, the kind of thing you might profile in a signal-processing or ML preprocessing pipeline.
- The fourth path is **Cython** — and unlike ctypes and cffi, Cython is the right tool when you are *writing* the kernel rather than wrapping an existing one.
- The ceiling is **NumPy** — `np.convolve` does the same operation, calls into BLAS-adjacent SIMD code, and tells us how close to the metal each of our manual attempts gets.

The kernel:

```
y[i] = sum over k of x[i + k] * h[k], for i in 0..N-K
```

A "valid" 1D convolution of input `x` of length N with kernel `h` of length K, producing output of length N-K+1. The classic signal-processing primitive. Cheap per-step (one multiply-add per inner-loop iteration), high iteration count for any non-trivial input.

## 2. Cython, end-to-end

A `.pyx` file looks like Python with optional C-style type annotations. The Cython compiler turns it into a `.c` file (against the CPython C API) and then a `.so`.

### 2.1 The naive port

The simplest possible Cython port: take the Python implementation and rename it.

```python
# convolve_naive.pyx
def convolve_naive(x, h):
    """Naive convolution. Identical to Python but compiled."""
    n = len(x)
    k = len(h)
    y = [0.0] * (n - k + 1)
    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s += x[i + j] * h[j]
        y[i] = s
    return y
```

Build and import:

```bash
cythonize -i convolve_naive.pyx
# generates convolve_naive.c, then convolve_naive.cpython-313-darwin.so
```

```python
from convolve_naive import convolve_naive
import numpy as np
x = np.random.random(1_000_000).tolist()
h = np.random.random(64).tolist()
result = convolve_naive(x, h)
```

The speedup of *this* version over the equivalent pure Python is ~1.2x — barely measurable. Why? Because every operation is still going through the CPython C API: `x[i + j]` is `PyObject_GetItem`, `s += x[i+j] * h[j]` is `PyNumber_Multiply` and `PyNumber_InPlaceAdd`. Cython compiled the Python *bytecode* to C, but the C still calls Python.

Cython's value is not "Python compiled to C." It is "*typed* Python compiled to C." Until you add types, Cython is barely faster than Python.

### 2.2 The typed port

Add type annotations:

```python
# convolve_typed.pyx
def convolve_typed(double[::1] x, double[::1] h, double[::1] out):
    """Typed convolution using memoryviews.

    x, h, out must all be 1D, C-contiguous, dtype float64.
    out must have length len(x) - len(h) + 1.
    """
    cdef Py_ssize_t n = x.shape[0]
    cdef Py_ssize_t k = h.shape[0]
    cdef Py_ssize_t i, j
    cdef double s

    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s += x[i + j] * h[j]
        out[i] = s
```

What changed:

- **`double[::1] x`** — `x` is now a *typed memoryview* of doubles, contiguous in the rightmost (only) dimension. The `::1` is the contiguity declaration: "the stride along this axis is exactly `sizeof(double)`." Without `::1`, Cython would emit a slower general-stride loop.
- **`cdef Py_ssize_t n = x.shape[0]`** — `n` is a C `Py_ssize_t` (signed integer, 64-bit on 64-bit machines), not a Python `int`. The assignment is C-level.
- **`cdef double s`** — `s` is a C `double`, not a Python `float`. The accumulator is a register.
- **`s += x[i + j] * h[j]`** — looks like Python but compiles to one multiply and one add at the C level. Cython generates `__pyx_v_s = __pyx_v_s + ((*((double *)(...))) * (*((double *)(...))))` — pointer arithmetic into the memoryview's buffer, then a hardware multiply-add.
- **Pass `out` as an argument** — Cython prefers you to pre-allocate the output buffer in Python and pass it in. The function fills it in-place. This avoids any Python-side `list` allocation inside the kernel.

The speedup over the naive `.pyx` is ~100x. The speedup over the pure-Python implementation is ~150x. We have crossed the threshold from "barely faster" to "C-speed."

### 2.3 The annotated HTML

Cython gives you a diagnostic for "is this line really C now or is it still calling Python?" Run:

```bash
cython -a convolve_typed.pyx
```

This generates `convolve_typed.html` next to the source. Open it in a browser. Each Cython line is colour-coded:

- **White** — pure C. No Python-API calls.
- **Pale yellow** — a few Python-API calls (often the boundary on function entry/exit).
- **Bright yellow** — heavy Python-API calls. This line is your bottleneck.

The discipline is to look at the annotated HTML for every Cython kernel you write and make sure the hot loop is white. If the inner loop is yellow, you have not added enough types, or you are touching a Python object you should be touching as a C value.

### 2.4 Releasing bounds checks and the GIL

Two more directives, both standard for tight loops:

```python
# convolve_fast.pyx
import cython

@cython.boundscheck(False)
@cython.wraparound(False)
def convolve_fast(double[::1] x, double[::1] h, double[::1] out):
    cdef Py_ssize_t n = x.shape[0]
    cdef Py_ssize_t k = h.shape[0]
    cdef Py_ssize_t i, j
    cdef double s

    with nogil:
        for i in range(n - k + 1):
            s = 0.0
            for j in range(k):
                s += x[i + j] * h[j]
            out[i] = s
```

- **`@cython.boundscheck(False)`** — disable bounds checking. By default, Cython inserts a bounds check on every memoryview access (`if i >= x.shape[0]: raise IndexError`). With this directive off, indexing out of bounds is UB (reads garbage, possibly segfaults). Use *after* you have tested.
- **`@cython.wraparound(False)`** — disable Python-style negative indexing. By default, `x[-1]` works in Cython memoryviews because Cython checks for negative indices and adjusts. The check costs a few cycles per access. Off if you do not use negative indexing.
- **`with nogil:`** — release the GIL for the duration of the block. Inside, no Python objects can be touched. Memoryviews and C-typed locals are fine. The GIL release lets the caller's other Python threads run during the convolution; it also enables `prange` (parallel-range) loops, which we do not cover this week.

The combined effect on the inner loop: roughly 2x faster than the typed-but-unguarded version. The total speedup over pure Python is ~250x. That is *within* the same order of magnitude as hand-tuned C with `-O3`.

### 2.5 Building with `setup.py`

`cythonize -i` is convenient for development. For distribution you use `setup.py`:

```python
# setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="convolve",
    ext_modules=cythonize(
        ["convolve_fast.pyx"],
        compiler_directives={"language_level": "3"},
    ),
)
```

```bash
python setup.py build_ext --inplace
```

The result is a `.so` that ships in your wheel. Users who `pip install` your wheel get the pre-built binary; users who `pip install` from sdist need a C compiler.

## 3. Memoryviews — the buffer protocol from the Cython side

A typed memoryview (`double[::1]`) is Cython's bridge to the **buffer protocol** (PEP 3118). The buffer protocol is the standard C-level interface for "I have an array of raw memory; you can read/write it without copying." NumPy implements it (an `ndarray` exposes its underlying buffer). `bytes` and `bytearray` implement it. `array.array` implements it. `memoryview` is the Python-level handle.

When you pass `np.zeros(1000)` into a function declared `double[::1] x`, Cython calls `PyObject_GetBuffer` to get a `Py_buffer` struct (containing a pointer, length, strides, format), checks that the format matches `double`, the rank matches 1, the layout matches `::1` (contiguous), and *binds the memoryview to the buffer*. Inside the function, `x[i]` is `*((double *)(buf + i * stride))` — a single C-level indexed load. No Python-object overhead per element.

The same code accepts:

- A NumPy array (`np.float64` dtype)
- A `bytes` object (treating bytes as packed doubles — works for serialised numeric data)
- An `array.array('d', ...)`
- A `memoryview(numpy_array)`
- Anything else that exports a compatible buffer

This is the *real* interop layer of the data science Python ecosystem. NumPy, SciPy, Pandas, PyTorch, Pillow, Open3D all speak the buffer protocol. Cython memoryviews give you native access to all of them with the same kernel.

### 3.1 The `::1` syntax

The Cython memoryview type spec is a mini language:

| Syntax | Meaning |
|--------|---------|
| `double[:]` | 1D, any stride (allows non-contiguous slices) |
| `double[::1]` | 1D, C-contiguous (stride is exactly `sizeof(double)`) |
| `double[:, :]` | 2D, any stride |
| `double[:, ::1]` | 2D, row-major (C-contiguous rows) |
| `double[::1, :]` | 2D, column-major (Fortran-contiguous) |
| `double[:, :, ::1]` | 3D, the innermost dim is contiguous |

The contiguity declaration matters. With `[:, :]`, Cython emits a multiply-and-add at every access: `addr = base + i * stride0 + j * stride1`. With `[:, ::1]`, the innermost loop reduces to pointer-increment: `addr = base + i * stride0; for j: *addr++`. The compiler can vectorise the contiguous version into SIMD; it usually cannot vectorise the strided one.

The discipline: **declare the tightest contiguity your code can require**. If you can require C-contiguous, do. If you can require row-major 2D, do. The user can always pass an explicitly-contiguous array; you do not need to handle every layout in one kernel.

## 4. The full kernel, four ways

We now have all the pieces for the headline benchmark. The kernel is 1D valid convolution, input N=1,000,000, kernel K=64.

### 4.1 Pure Python

```python
from typing import List

def convolve_python(x: List[float], h: List[float]) -> List[float]:
    """Pure Python. The baseline."""
    n = len(x)
    k = len(h)
    out: List[float] = [0.0] * (n - k + 1)
    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s += x[i + j] * h[j]
        out[i] = s
    return out
```

### 4.2 ctypes + C `-O2`

```c
/* convolve.c */
#include <stddef.h>

void
convolve_c(const double *x, size_t n,
           const double *h, size_t k,
           double *out)
{
    size_t out_len = n - k + 1;
    for (size_t i = 0; i < out_len; ++i) {
        double s = 0.0;
        for (size_t j = 0; j < k; ++j) {
            s += x[i + j] * h[j];
        }
        out[i] = s;
    }
}
```

```python
import ctypes
import numpy as np

_lib = ctypes.CDLL("./libconvolve.so")
_lib.convolve_c.restype = None
_lib.convolve_c.argtypes = [
    np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
    ctypes.c_size_t,
    np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
    ctypes.c_size_t,
    np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
]


def convolve_ctypes(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """C implementation via ctypes."""
    out = np.empty(x.size - h.size + 1, dtype=np.float64)
    _lib.convolve_c(x, x.size, h, h.size, out)
    return out
```

### 4.3 Cython

Already shown above (`convolve_fast.pyx`).

### 4.4 NumPy

```python
import numpy as np

def convolve_numpy(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """NumPy implementation. The ceiling."""
    return np.convolve(x, h[::-1], mode="valid")
```

Note the `h[::-1]` — `np.convolve` reverses the kernel by definition (mathematical convolution), so to compute the cross-correlation form we wrote in C, we reverse `h`.

## 5. The numbers

M2 MacBook 2024, CPython 3.13.1, N=1,000,000, K=64, single timing of 5 repeats taking the minimum:

| Implementation | Time (ms) | Speedup over Python |
|----------------|-----------|---------------------|
| Pure Python | 8,400 | 1x |
| Cython naive (no types) | 7,200 | 1.2x |
| Cython typed | 60 | 140x |
| Cython typed + nogil + boundscheck off | 38 | 220x |
| ctypes + C `-O2` | 35 | 240x |
| NumPy `np.convolve` | 4.5 | 1,870x |

A few observations the table earns its keep for:

- **Pure Python is awful for this kernel.** 8.4 seconds for what NumPy does in 4.5 ms. This is the "1D numerical loop in CPython" tax.
- **Untyped Cython buys almost nothing.** The "compile Python to C" intuition is a trap. The C still calls Python at every operation. ~1.2x.
- **Adding types is the *entire* story.** From 1.2x to 140x by declaring `double` and `Py_ssize_t`. The C compiler now sees real C and emits real instructions.
- **`nogil` + `boundscheck(False)` gives another 1.5x.** Real, measurable, and free.
- **Cython (tight) and ctypes (with `-O2`) are within 10% of each other.** They are doing the same thing — both are calling a `-O2`-optimised inner loop. The remaining gap is per-call overhead and SIMD packing.
- **NumPy is 5–10x faster than either.** `np.convolve` calls into a heavily-tuned C routine that uses AVX-512 (or NEON on ARM) for an 8-doubles-per-cycle inner loop. Cython and ctypes use the auto-vectorisation the compiler can prove safe; NumPy uses explicit SIMD intrinsics.

The lesson: **for standard linear-algebra-shaped kernels, NumPy is hard to beat. The win of Cython/ctypes is for kernels NumPy does not have — custom branching, non-uniform memory access, problem-specific data structures.**

## 6. When Cython wins over NumPy

Cython is *not* always slower than NumPy. NumPy is fastest when:

- The operation is broadcast over a whole array uniformly.
- The operation is one of the ~50 that have a SIMD-tuned implementation (sum, dot, convolve, FFT, sort, ...).
- The data fits in cache or is streamed through.

NumPy is *slow* when:

- The kernel branches per element (`y[i] = f(x[i])` where `f` is a Python-level conditional).
- The kernel has data-dependent memory access (graph traversal, sparse operations not covered by `scipy.sparse`).
- The kernel needs to short-circuit (find first match, stop after N iterations).
- The kernel operates on Python-object arrays (`np.array([...], dtype=object)`).

In all these cases, Cython wins because you write the C-level branching directly. The classic example is a Mandelbrot-set escape-time kernel (`while abs(z) < 2: z = z*z + c; count += 1` — short-circuit per pixel; NumPy has to compute all 1000 iterations for the converged pixels). Mandelbrot in Cython runs ~50x faster than the cleverest NumPy formulation; in C it is roughly the same speed as Cython.

The mini-project lets you choose your kernel. Choose one where the C-level control flow buys you something, or you will discover that NumPy already did the job.

## 7. The "I wrote it three ways and the speedups are the same" problem

A common student finding: "I wrote my kernel in ctypes, cffi API, and Cython. They all run in the same time. Why?"

Because they all compile down to the same `-O2` `for` loop, and the inner-loop instructions are what dominate. If the kernel does N=1,000,000 multiply-adds at ~1 ns each, the kernel takes ~1 ms. The Python-side per-call overhead is ~1 µs (ctypes) or ~100 ns (cffi API / Cython). Either way, the per-call overhead is <0.1% of the total — the kernel is the kernel.

This is *good news*. It means the three paths are interchangeable on big kernels; the choice is on ergonomics, not speed.

It changes when N is small and the kernel is called repeatedly. A function that does ~1 µs of work, called 1 million times in a Python loop, sees:

- ctypes: 1 µs (work) + 1 µs (overhead) = 2 µs each, 2 seconds total.
- cffi API: 1 µs (work) + 0.1 µs (overhead) = 1.1 µs each, 1.1 seconds total.
- Cython: 1 µs (work) + 0.1 µs (overhead) = 1.1 µs each, 1.1 seconds total. *Plus*, you can put the outer loop inside the Cython function, eliminating Python overhead entirely.

The Cython advantage at small-N comes from being able to *also* compile the outer loop. ctypes and cffi only compile the inner C function; the outer driver is still Python. Cython compiles whatever you put in the `.pyx`. If the driver is hot, put it in Cython.

## 8. Cython's pitfalls

Three things that bite students:

### 8.1 You forgot `language_level: 3`

Cython 3.0+ defaults to Python 3 syntax (`print` is a function, `/` is true division). Older versions defaulted to Python 2, which silently changed the meaning of `/`. Set explicitly:

```python
# setup.py
cythonize([...], compiler_directives={"language_level": "3"})
```

Or as a file-level directive at the top of every `.pyx`:

```python
# cython: language_level=3
```

### 8.2 You used a Python object inside `with nogil:`

```python
with nogil:
    for i in range(n):
        result.append(s)  # ERROR: list operations need the GIL
```

Cython will reject this at compile time with a clear error: "Calling gil-requiring function not allowed without gil." The fix is to pre-allocate the output as a typed memoryview and assign into it instead of `append`-ing.

### 8.3 You did not run `cython -a` and the kernel is yellow

Your typed Cython is somehow only 5x faster than Python. You did not check the annotated HTML. Run `cython -a kernel.pyx`; open `kernel.html`; look at the inner loop. If it is yellow, you have a Python-object access in there. The usual culprits:

- A Python-level call inside the loop (`len(x)` where `x` is a memoryview — use `x.shape[0]` instead).
- An untyped intermediate (`s = 0.0` is a Python float; you wanted `cdef double s = 0.0`).
- A `print` for debugging that you forgot to remove.

## 9. Reading

- Cython "Basic Tutorial": <https://cython.readthedocs.io/en/latest/src/tutorial/cython_tutorial.html>.
- Cython "Typed Memoryviews": <https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html>.
- Cython "NumPy tutorial": <https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html>.
- Cython "Compiler directives": <https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#compiler-directives>.
- PEP 3118 (buffer protocol): <https://peps.python.org/pep-3118/>. The interop layer underneath memoryviews.
- The NumPy C-API page: <https://numpy.org/doc/stable/reference/c-api/index.html>. For when you outgrow buffer-protocol-via-Cython and want direct NumPy C-API access.
- The Cython `cython -a` documentation, which is in the "Compilation" section of the user guide.

## 10. Wrap-up

Three lectures, three paths, one numerical kernel benchmarked four ways. The mini-project asks you to take a kernel of your choice (1D convolution is the default; alternatives in the spec) and implement it three ways — one of {ctypes, cffi API, Cython}, plus NumPy, plus pure Python — and write the memo that explains the speedups.

The discipline of the week:

1. Profile first. (Week 7.)
2. Try the four shapes first. (Last week.)
3. If C is the answer, pick a path on first principles. (This week.)
4. Benchmark every implementation. Take the *minimum* of 5 repeats.
5. Write the memo that names *why* the speedups are what they are.

The artifact is the memo. The kernel is the excuse.
