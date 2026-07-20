# Week 8 — Exercise Solutions

> Read after you have attempted each exercise. The expected numbers are from a 2024 MacBook Pro M2 (Apple Silicon, clang 15, CPython 3.13.1). Your hardware will produce different absolute numbers; the *ratios* should match.

## Exercise 1 — ctypes first binding

### Expected output

```
[Benchmark] sum_squares, n=1,000,000
  Python :    66.40 ms
  ctypes :     0.84 ms
  speedup:   79.0x
  OK: speedup >= 30x as expected

[Benchmark] scale_inplace, n=1,000,000
  Python :    65.80 ms
  ctypes :     1.10 ms
  speedup:   59.8x
```

### Why ~80x for `sum_squares`?

The pure-Python loop does roughly: one `LIST_GET` bytecode, one `LOAD_FAST` (for `x`), one `BINARY_MULTIPLY`, one `INPLACE_ADD` per iteration. Each bytecode is roughly 60–100 ns of interpreter dispatch (PEP 659 specialised interpreter has trimmed this from CPython 3.10, but not by an order of magnitude for arithmetic on floats). For 1 million iterations, that is ~60–100 ms — which matches the observed Python time.

The C loop with `-O2` is auto-vectorised by clang: on Apple Silicon, NEON pairs 2 doubles per SIMD register, the inner loop is one FMA instruction per pair, plus a small reduction. ~125,000 cycles at 3.2 GHz is ~40 µs of pure compute, plus memory bandwidth (1M doubles = 8 MB, beyond L2; main-memory bandwidth becomes a factor). Total ~0.8 ms.

The speedup is ~80x. That is the bytecode-to-native gap for a tight arithmetic loop.

### What if you skip `argtypes` and `restype`?

`ctypes` defaults to `c_int`-returning and untyped args. For `sum_squares`:

```python
# Wrong: no restype
_lib.sum_squares(arr, arr.size)
```

Returns the bottom 32 bits of the return value, reinterpreted as a signed int. On Apple Silicon, a 64-bit `double` of ~333,000 has byte pattern that, when read as a 32-bit int, gives some garbage number. The Python side gets that garbage and you have *no idea* it is wrong unless you check the value against a Python reference.

This is the canonical ctypes failure mode: the program runs, the answer is silent garbage, the bug surfaces in production weeks later when someone notices a sum that does not match the spreadsheet.

**Always set `argtypes` and `restype` before the first call.**

### Why is `scale_inplace` slightly slower per element than `sum_squares`?

`scale_inplace` writes back to memory; `sum_squares` only reads. The write traffic is the bottleneck on bandwidth-bound kernels — writes go through the cache hierarchy and dirty cache lines. The ~1.1 ms vs ~0.8 ms gap is the cost of the writes.

The compiler can do nothing about this; the kernel is memory-bandwidth-bound, not compute-bound. The fix, if you wanted, would be to fuse the scale with whatever the *next* operation is — so the array is read and rewritten exactly once. That is the kind of optimisation NumPy can sometimes do (and is the kind of optimisation that `numexpr` and `numba.fuse` exist for).

## Exercise 2 — cffi ABI vs API mode

### Expected output

```
[Per-call overhead] n=10, 1,000,000 calls each
  ctypes       :  1.520 us/call
  cffi ABI mode:  1.180 us/call
  cffi API mode:  0.180 us/call

  cffi API vs ctypes: 8.4x faster per call

[Bulk throughput] n=1,000,000, 5 calls each, min time
  ctypes       :  0.820 ms
  cffi ABI mode:  0.815 ms
  cffi API mode:  0.810 ms
```

### Why is the per-call gap ~8x?

`ctypes` and `cffi` ABI mode both go through **libffi** — a portable library for calling functions with runtime-known signatures. libffi reads the signature, packs the arguments into the platform's calling-convention registers/stack, jumps to the function pointer, recovers the return. Per-call cost: ~500–1000 ns on x86/Apple Silicon.

`cffi` API mode generates a CPython C extension at build time. The generated `.so` includes hand-tailored unmarshal code: for `sum_squares(double *, size_t)`, the generated wrapper is roughly:

```c
static PyObject *
_cffi_d_sum_squares(PyObject *self, PyObject *args)
{
    double *buf;
    size_t n;

    /* one specialised PyArg_ParseTuple plus a cast */
    if (!PyArg_ParseTuple(args, "y#n", (char **)&buf, ...)) {
        return NULL;
    }
    double r = sum_squares(buf, n);
    return PyFloat_FromDouble(r);
}
```

No libffi. No runtime signature lookup. The call is a direct C function call with one `PyArg_ParseTuple` and one `PyFloat_FromDouble`. ~100–200 ns total.

The 8x gap is the libffi tax. For a function that does ~1 µs of useful work, this matters; for a function that does ~1 ms of useful work, it does not.

### Why is the bulk-throughput gap tiny?

The kernel does 1 million FMAs at ~1 ns each = 1 ms. The per-call overhead (1.5 µs for ctypes, 0.2 µs for cffi API) is 0.15% and 0.02% of the total respectively. Both are noise. The kernel is the cost.

### When does the per-call gap matter?

Whenever you call C frequently with small arguments. The classic shape:

```python
for row in data:
    compute_one_row(row)  # row is small; called millions of times
```

If `compute_one_row` is a C function bound via ctypes, you pay 1.5 µs per row in overhead, on top of the row's actual compute. If the row computation is itself only 1 µs, you spend 60% of your time in libffi dispatch.

The fix is either to (a) pass *all the rows* to C in one call and let C loop, or (b) use cffi API mode / Cython where per-call overhead is ~10x smaller.

### What did `cryptography` find?

The `cryptography` project's <https://cryptography.io/en/latest/faq/> FAQ entry "Why not use ctypes?" articulates four reasons:

1. **Compile-time verification**: ABI bindings cannot tell you the `.so` has the layout your declarations claim. API mode runs the C compiler against the real header, catching drift.
2. **Function pointer types**: OpenSSL has callbacks. cffi handles them naturally; ctypes' `CFUNCTYPE` is awkward.
3. **Macros**: OpenSSL is full of macros that are `#define`d functions. cffi can `#define` them in `set_source` and bind them; ctypes cannot.
4. **PyPy support**: cffi was designed for PyPy. ctypes works on PyPy but is much slower.

For a security-critical library wrapping a constantly-changing C library, these add up to a decisive case for cffi API mode.

## Exercise 3 — Cython 1D convolution

### Expected output

```
[Benchmark] n=1000000, k=64
  pure Python (extrap.)        :  9100.0 ms
  Cython naive (extrap.)       :  7600.0 ms
  Cython typed                 :    62.0 ms
  Cython fast (nogil, no chks) :    41.0 ms
  NumPy np.convolve            :     4.8 ms

[Speedup vs. pure Python (extrapolated)]
  Cython naive :     1.2x
  Cython typed :   146.8x
  Cython fast  :   222.0x
  NumPy        :  1895.8x

  OK: all speedup thresholds met
```

### Why is `convolve_naive` only 1.2x faster than Python?

Because every operation is still a Python operation. `x[i + j]` in untyped Cython is `PyObject_GetItem(x, PyLong_FromSsize_t(i + j))`. `s + x[i + j] * h[j]` is `PyNumber_Add(s, PyNumber_Multiply(...))`. The C code Cython generates is wall-to-wall C-API calls. There is *some* saving from not going through the bytecode dispatcher, but it is small.

The intuition "Cython compiles Python to fast C" is wrong. Cython compiles Python to *correct* C that *calls Python*. The speed comes from giving Cython enough types that it can compile to C that *does not* call Python.

### Why does adding types take us from 1.2x to 150x?

Three changes:

1. `cdef Py_ssize_t i, j` — the loop counters are C ints, not Python int boxes. The `range(n - k + 1)` becomes a C `for` loop with a C int.
2. `cdef double s` — the accumulator is a C `double` in a register, not a Python `float` on the heap.
3. `double[::1] x` — the array access is `*((double *)(buf + i * sizeof(double)))`, a single C load. No reference counting, no method dispatch.

The inner loop generated for `convolve_typed` is roughly:

```c
for (i = 0; i < n - k + 1; i++) {
    s = 0.0;
    for (j = 0; j < k; j++) {
        if (i + j >= x_shape[0]) goto bounds_error;  /* boundscheck */
        if (j >= h_shape[0]) goto bounds_error;
        s = s + (*(double *)(x_data + (i + j) * x_stride0))
              * (*(double *)(h_data + j * h_stride0));
    }
    out_data[i] = s;
}
```

Real C. The compiler vectorises the inner loop into SIMD. ~150x.

### What does `nogil` + bounds-check-off buy?

The bounds checks and the wraparound check are two `cmp` and one branch per memoryview access. With `wraparound=False`, the negative-index correction (`if (i < 0) i += shape;`) is omitted. With `boundscheck=False`, the upper-bound check is omitted. Together they trim ~3 instructions per access; on a kernel with 64 inner iterations, that is ~200 instructions per outer iteration. ~30% of the runtime.

The `with nogil:` block releases the GIL. For a single-threaded driver, this buys nothing directly — but it *also* tells Cython that "this code can run without the GIL," which means Cython is more aggressive about emitting pure C in the block (no Python-object access can be in there; the compiler enforces).

Combined, ~1.5x over `convolve_typed`. Total 220x over pure Python.

### Why is NumPy still 5–10x faster than `convolve_fast`?

NumPy's `np.convolve` calls into a routine that uses **hand-tuned SIMD intrinsics**. On Apple Silicon, that means explicit NEON intrinsics (`vmlaq_f64`) operating on 2 doubles per cycle. The compiler's auto-vectorisation of Cython's loop also uses NEON, but the auto-vectoriser is conservative: it has to *prove* the access pattern is safe (no aliasing, contiguous, aligned). Hand-tuned intrinsics give the same guarantees by hand without the proof obligation.

Also, NumPy uses a different convolution algorithm under the hood: for kernel sizes above ~30, it switches to FFT-based convolution (`O(N log N)` instead of `O(N*K)`). For our K=64, N=1M, FFT-convolution does ~20M operations instead of 64M; another factor of 3.

The takeaway: **NumPy is the ceiling for standard kernels. Cython is the ceiling for non-standard ones.** If your kernel looks like `np.convolve`, use `np.convolve`. If your kernel has problem-specific structure NumPy does not exploit, Cython is where the wins are.

### Reading `cython -a`

Run `cython -a exercise-03-convolve.pyx`. Open `exercise-03-convolve.html` in a browser.

You will see:

- `convolve_naive` is mostly **yellow**. Every line in the inner loop is highlighted because it goes through Python objects.
- `convolve_typed` is mostly **white** in the inner loop, **pale yellow** at the function boundary (the memoryview unpacking).
- `convolve_fast` is mostly **white**. The inner loop has no Python-API calls.

This is the diagnostic to run every time you write a Cython kernel. If the inner loop is yellow, you have not added enough types. Add `cdef` declarations until it is white; benchmark; repeat.

## Common build errors

### `error: Python.h: No such file or directory`

You do not have the CPython development headers installed. On Ubuntu/Debian:

```bash
sudo apt install python3-dev
```

On macOS, the Xcode Command Line Tools include them:

```bash
xcode-select --install
```

On Windows, install the Visual Studio Build Tools (or the Python launcher's bundled compiler).

### `ImportError: dlopen(...): symbol not found: _sum_squares`

The `.so` loaded but the named function is not exported. Common causes:

- The function was declared `static` in the C source. `static` makes it module-private; remove it for exported functions.
- You compiled with `g++` (C++ compiler) and the name was mangled. Wrap C declarations in `extern "C" { ... }`.
- The `.so` you loaded is not the one you just built (a stale `libk.so` from an earlier compile). Rebuild.

### `OSError: dlopen(./libk.so): no such file`

`ctypes.CDLL("./libk.so")` looks relative to the *current working directory*, not the script's directory. If you `cd` somewhere else and run the script, it cannot find the library. Always use an absolute path:

```python
import os
HERE = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(HERE, "libk.so")
_lib = ctypes.CDLL(LIB_PATH)
```

### Cython: `Cannot convert Python object to 'double[::1]'`

You passed a non-contiguous array to a `[::1]` memoryview. The fix is either:

- Pass a contiguous array: `np.ascontiguousarray(arr)`.
- Loosen the contiguity declaration: `double[:]` accepts any stride (at a small speed cost).

### Cython: `Operation not allowed without gil`

You did something inside `with nogil:` that requires the GIL (a Python-object access, a print, an exception raise). The fix is to move that operation outside the `nogil` block, or to use C-only operations inside.

## Stretch

- **Read the generated C file.** `cythonize` keeps `exercise-03-convolve.c` next to the `.pyx`. Open it. Search for `convolve_fast`. You will see ~150 lines of generated C that look very much like Lecture 1's `spam.c` — `PyMethodDef`, `PyArg_ParseTuple`, `Py_BuildValue`, all of it. Cython wrote it for you. ~15 minutes.
- **Run `nm` on the built `.so`.** You will see the exported `PyInit_exercise_03_convolve` symbol, plus internal functions. ~5 minutes.
- **Try Numba.** Install (`pip install numba`), decorate the Python kernel with `@numba.njit`, time it. You should see ~Cython-level speed with no separate build step. ~15 minutes. When does Numba win? When you do not want a build pipeline. When does it lose? When you need PyPy support (Numba is CPython-only) or when JIT first-call latency is unacceptable.
- **Try the kernel in PyO3.** This is a multi-hour task; not for this week. But if you are curious: install `maturin`, `maturin new --bindings pyo3`, port the kernel. You will find PyO3 produces a ~Cython-fast binding with Rust's safety properties at the boundary. The future, probably.
