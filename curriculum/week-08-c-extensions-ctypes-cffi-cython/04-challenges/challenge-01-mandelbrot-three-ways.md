# Challenge 1 — Mandelbrot Three Ways

> **Implement the Mandelbrot-set escape-time computation in pure Python, ctypes (with C), and Cython. Benchmark all three plus NumPy. Explain the ratios. Time budget: 3 hours. The artifact is one folder with three implementations, a benchmark script, and a 250-word memo.**

## Why Mandelbrot

We picked 1D convolution for the exercises because it is *easy*: linear access pattern, no branching, NumPy has a tuned routine, every implementation looks the same. Mandelbrot is the opposite. The kernel has:

- **Data-dependent control flow** — each pixel iterates until `|z| > 2` or it hits the maximum iteration count. Different pixels have wildly different iteration counts.
- **Short-circuit potential** — most pixels (the ones that escape early) do 5–20 iterations; some (deep in the set boundary) do all 1,000.
- **Complex arithmetic** — `z = z*z + c` where `z, c` are complex.

This is the shape NumPy is *bad* at. `np.where`-style branching has to compute the *full* expression for every pixel and then mask. Cython and C can short-circuit. Python can short-circuit but pays the interpreter tax on every iteration.

The challenge is to see, with measured numbers, how the three paths handle a kernel where the per-element control flow is non-trivial.

## Time budget

| Phase | Time |
|------:|----:|
| 1. Read the Mandelbrot definition and the reference Python | 15 min |
| 2. Implement pure Python; time it | 30 min |
| 3. Implement C; bind via ctypes; time it | 45 min |
| 4. Implement Cython; time it | 45 min |
| 5. NumPy comparison | 20 min |
| 6. Write the memo | 25 min |
| **Total** | **3 h** |

If you finish early, try implementing it in Numba (`@numba.njit`) and see if you can beat Cython.

## 1. The kernel

Mandelbrot escape-time: for each complex point `c` in a grid, iterate `z_{n+1} = z_n^2 + c` starting from `z_0 = 0` until either `|z| > 2` (the point escapes) or `n` reaches a maximum. The output is the iteration count at which it escaped, or the maximum if it never did.

In Python:

```python
def mandelbrot_pixel(cr: float, ci: float, max_iter: int) -> int:
    """Return the escape iteration count for c = cr + ci*i, or max_iter."""
    zr, zi = 0.0, 0.0
    for n in range(max_iter):
        zr2, zi2 = zr * zr, zi * zi
        if zr2 + zi2 > 4.0:
            return n
        zi = 2.0 * zr * zi + ci
        zr = zr2 - zi2 + cr
    return max_iter
```

A 2D wrapper iterates over the grid:

```python
import numpy as np
from typing import Any

def mandelbrot_python(
    width: int, height: int,
    re_min: float, re_max: float,
    im_min: float, im_max: float,
    max_iter: int,
) -> np.ndarray:
    """Compute the Mandelbrot escape-time grid."""
    out = np.empty((height, width), dtype=np.int32)
    for j in range(height):
        ci = im_min + j * (im_max - im_min) / (height - 1)
        for i in range(width):
            cr = re_min + i * (re_max - re_min) / (width - 1)
            out[j, i] = mandelbrot_pixel(cr, ci, max_iter)
    return out
```

The default test parameters: `width=800, height=600, re_min=-2.0, re_max=1.0, im_min=-1.2, im_max=1.2, max_iter=200`.

## 2. The C implementation

Write `mandelbrot.c` with one exported function:

```c
void mandelbrot_c(
    int width, int height,
    double re_min, double re_max,
    double im_min, double im_max,
    int max_iter,
    int *out
);
```

Build:

```bash
gcc -shared -fPIC -O2 -o libmb.so mandelbrot.c
```

Bind via ctypes:

```python
import ctypes
import numpy as np

_lib = ctypes.CDLL("./libmb.so")
_lib.mandelbrot_c.restype = None
_lib.mandelbrot_c.argtypes = [
    ctypes.c_int, ctypes.c_int,
    ctypes.c_double, ctypes.c_double,
    ctypes.c_double, ctypes.c_double,
    ctypes.c_int,
    np.ctypeslib.ndpointer(dtype=np.int32, flags="C_CONTIGUOUS"),
]

def mandelbrot_ctypes(...) -> np.ndarray:
    out = np.empty((height, width), dtype=np.int32)
    _lib.mandelbrot_c(width, height, re_min, re_max, im_min, im_max, max_iter, out)
    return out
```

## 3. The Cython implementation

Write `mandelbrot.pyx`:

```python
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

def mandelbrot_cython(
    int width, int height,
    double re_min, double re_max,
    double im_min, double im_max,
    int max_iter,
    int[:, ::1] out,
):
    cdef int i, j, n
    cdef double cr, ci, zr, zi, zr2, zi2
    cdef double dx = (re_max - re_min) / (width - 1)
    cdef double dy = (im_max - im_min) / (height - 1)

    with nogil:
        for j in range(height):
            ci = im_min + j * dy
            for i in range(width):
                cr = re_min + i * dx
                zr = 0.0
                zi = 0.0
                for n in range(max_iter):
                    zr2 = zr * zr
                    zi2 = zi * zi
                    if zr2 + zi2 > 4.0:
                        break
                    zi = 2.0 * zr * zi + ci
                    zr = zr2 - zi2 + cr
                out[j, i] = n
```

Build:

```bash
cythonize -i mandelbrot.pyx
```

## 4. The NumPy implementation

NumPy *cannot* short-circuit per-element. The best you can do is vectorise the iteration and mask out converged points:

```python
def mandelbrot_numpy(width, height, re_min, re_max, im_min, im_max, max_iter):
    re = np.linspace(re_min, re_max, width)
    im = np.linspace(im_min, im_max, height)
    c = re[np.newaxis, :] + 1j * im[:, np.newaxis]
    z = np.zeros_like(c)
    out = np.full(c.shape, max_iter, dtype=np.int32)
    for n in range(max_iter):
        mask = (z.real * z.real + z.imag * z.imag) <= 4.0
        z[mask] = z[mask] * z[mask] + c[mask]
        # Record the iteration where each point first escapes:
        escaped = ~mask & (out == max_iter)
        out[escaped] = n
    return out
```

This is *honest* NumPy. It does the full `max_iter` iterations for every pixel (because there is no per-pixel break in vectorised land). The mask saves a small amount of work but the dominant cost is the un-short-circuited inner loop.

You may see a "faster" NumPy implementation online that uses `out` differently — it gives the same answers but at similar cost. The point of this challenge is that *the right vectorisation does not exist* for this kernel.

## 5. Benchmark

```python
import time

def time_min(fn, args, repeats=3):
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        elapsed = time.perf_counter() - t0
        if elapsed < best:
            best = elapsed
    return best


args = (800, 600, -2.0, 1.0, -1.2, 1.2, 200)
print(f"pure Python : {time_min(mandelbrot_python, args, 1) * 1000:.0f} ms")
print(f"ctypes      : {time_min(mandelbrot_ctypes, args, 3) * 1000:.0f} ms")
print(f"Cython      : {time_min(mandelbrot_cython, args, 3) * 1000:.0f} ms")
print(f"NumPy       : {time_min(mandelbrot_numpy, args, 3) * 1000:.0f} ms")
```

Expected, M2 MacBook 2024:

| Implementation | Time | Speedup |
|----------------|-----|---------|
| pure Python | ~35,000 ms | 1x |
| ctypes + C `-O2` | ~120 ms | ~290x |
| Cython | ~135 ms | ~260x |
| NumPy | ~1,400 ms | ~25x |

## 6. The memo

`MEMO.md`, 250 words. Address:

1. Why is the C implementation (~290x) faster than the Cython implementation (~260x)? Or, on your machine, are they within noise? Articulate what the gap (or lack of gap) means.
2. Why is NumPy *only* 25x faster than Python, when it was ~1900x faster on the convolution? Mention the no-short-circuit issue.
3. If you wanted to push past Cython's number, where would you look? (Hint: SIMD intrinsics; multi-threading via `prange`; algorithmic — early termination based on cardioid/period-2 bulb tests.)
4. Of the three paths (Python / ctypes / Cython), which would you ship to a junior engineer asked to extend this code? Justify in two sentences.

## Acceptance criteria

- [ ] Folder `challenge-01-mandelbrot/` contains: `mandelbrot.py` (Python + ctypes wrapper), `mandelbrot.c`, `mandelbrot.pyx`, `mandelbrot_numpy.py`, `bench.py`, `MEMO.md`.
- [ ] All four implementations produce the *same* iteration-count grid on the default parameters (allow off-by-one at the boundary; the comparison is `np.allclose(a, b, atol=1)`).
- [ ] The C implementation is at least 100x faster than pure Python.
- [ ] The Cython implementation is at least 80x faster than pure Python.
- [ ] The memo is 200–300 words and addresses all four questions.
- [ ] You ran `cython -a mandelbrot.pyx` and confirmed the inner loop is white.

## Common pitfalls

- **Forgetting `cdivision=True` in Cython.** Without it, Cython generates Python-style integer division with sign correction (slow). With it, you get C-style division. For this kernel, the float divisions in the inner loop benefit.
- **Using `complex` types in C or Cython without ensuring contiguous memory.** Stick to two `double`s side by side; do not use `double _Complex`.
- **Comparing implementations without setting the same `max_iter`.** A 10x change in `max_iter` is a 10x change in runtime.
- **Profiling with `max_iter=10`.** Then the kernel finishes in <1 ms and the timing is dominated by setup overhead. Use `max_iter >= 200`.

## Reading

- The Mandelbrot iteration on Wikipedia (read for definition only; the article is huge): <https://en.wikipedia.org/wiki/Mandelbrot_set>.
- Cython "Pure Python mode" — alternative syntax that lets you keep the file as `.py`: <https://cython.readthedocs.io/en/latest/src/tutorial/pure.html>. Stretch goal.
- The `numpy` Mandelbrot examples in the SciPy lectures: <https://scipy-lectures.org/intro/numpy/exercises.html#mandelbrot-set>.
