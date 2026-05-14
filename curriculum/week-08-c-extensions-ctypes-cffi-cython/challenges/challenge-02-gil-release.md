# Challenge 2 — GIL Release and Parallel Speedup

> **Take a Cython-or-C kernel that does ~500 ms of pure-C numerical work. Call it from 1, 2, 4, and 8 Python threads. Measure the speedup at each thread count, with the GIL held vs. with the GIL released. Explain the curve. Time budget: 2 hours.**

## Why this matters

The GIL conversation in Week 3 was theoretical: "the GIL serialises Python bytecode execution; threads cannot run Python in parallel." This challenge makes the conversation operational: **threads *can* run *C* in parallel — but only if the C function explicitly releases the GIL.**

The single most common production failure of a numerical Python service is: "we wrote a fast C kernel, we called it from a `ThreadPoolExecutor`, and we got *zero* speedup because the kernel does not release the GIL." The fix is one line of code (`Py_BEGIN_ALLOW_THREADS` in C, `with nogil:` in Cython, `release_gil=True` in cffi API mode). The diagnostic is the kind of thing that costs a week if you do not know to look.

This challenge: write the kernel, write the driver, draw the curve.

## Time budget

| Phase | Time |
|------:|----:|
| 1. Implement the heavy kernel in Cython, with and without `nogil` | 30 min |
| 2. Write the threading driver | 20 min |
| 3. Benchmark at 1, 2, 4, 8 threads, both modes | 30 min |
| 4. Draw the curve (matplotlib or ASCII) | 15 min |
| 5. Write the memo explaining the curves | 25 min |
| **Total** | **2 h** |

## 1. The kernel

Pick a kernel that does ~500 ms of pure-C work. A few options that all work:

- **Brute-force prime-counting in a range.** Trial division up to `sqrt(n)` for each candidate; count how many primes are in `[lo, hi)`. ~500 ms for `[2, 2_000_000)`.
- **Mandelbrot escape-time on a large grid.** From Challenge 1, with `max_iter=2000` and `width=height=1000`. ~500 ms.
- **Iterated multiply-add over a large NumPy array.** `for k in range(1000): arr = arr * c1 + c2`. ~500 ms for N=10M.

Pick one. The choice does not matter; the GIL behaviour does.

## 2. The two-variant Cython

The kernel must be written twice — once releasing the GIL, once not. The cleanest pattern is one `.pyx` with two functions:

```python
# heavy.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

def heavy_with_gil(double[::1] x, double[::1] out, int n_iter):
    """Heavy kernel; does not release the GIL."""
    cdef Py_ssize_t i, k
    cdef Py_ssize_t n = x.shape[0]
    for k in range(n_iter):
        for i in range(n):
            out[i] = x[i] * 1.0001 + 0.0001
            x[i] = out[i]


def heavy_no_gil(double[::1] x, double[::1] out, int n_iter):
    """Same kernel; releases the GIL for the duration."""
    cdef Py_ssize_t i, k
    cdef Py_ssize_t n = x.shape[0]
    with nogil:
        for k in range(n_iter):
            for i in range(n):
                out[i] = x[i] * 1.0001 + 0.0001
                x[i] = out[i]
```

The two functions compile to nearly-identical C. The difference is one `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` pair around the outer loop in `heavy_no_gil`.

## 3. The driver

```python
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
import numpy as np

from heavy import heavy_with_gil, heavy_no_gil

N = 10_000_000
N_ITER = 50  # tune so single-thread takes ~500 ms

def make_buffers():
    """Create independent input and output buffers per call (so threads
    do not contend on the same memory)."""
    x = np.ones(N, dtype=np.float64)
    out = np.empty(N, dtype=np.float64)
    return x, out


def run_one(fn: Callable, _: int) -> float:
    x, out = make_buffers()
    t0 = time.perf_counter()
    fn(x, out, N_ITER)
    return time.perf_counter() - t0


def bench(fn: Callable, n_threads: int, n_calls: int) -> float:
    """Run n_calls of fn() across n_threads. Return total wall time."""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        futures = [ex.submit(run_one, fn, i) for i in range(n_calls)]
        for f in futures:
            f.result()
    return time.perf_counter() - t0


def main():
    # Calibrate. Pick N_ITER so single-call is ~500 ms.
    x, out = make_buffers()
    t = time.perf_counter()
    heavy_no_gil(x, out, N_ITER)
    single = time.perf_counter() - t
    print(f"Single call: {single * 1000:.0f} ms")
    print(f"(target ~500 ms; adjust N_ITER if needed)")

    n_calls = 8
    for n_threads in [1, 2, 4, 8]:
        t_with = bench(heavy_with_gil, n_threads, n_calls)
        t_without = bench(heavy_no_gil, n_threads, n_calls)
        print(
            f"\n[{n_threads} threads, {n_calls} calls]"
            f"\n  with GIL: {t_with:.2f}s"
            f"\n  no  GIL: {t_without:.2f}s"
            f"\n  speedup of nogil at {n_threads} threads: "
            f"{t_with / t_without:.2f}x"
        )


if __name__ == "__main__":
    main()
```

## 4. Expected curves

M2 MacBook 2024, 8 calls of ~500 ms each, total work ~4 seconds:

| Threads | with GIL | without GIL | nogil speedup |
|--------:|---------:|------------:|--------------:|
| 1 | 4.0 s | 4.0 s | 1.0x |
| 2 | 4.1 s | 2.1 s | 2.0x |
| 4 | 4.2 s | 1.1 s | 3.8x |
| 8 | 4.5 s | 0.7 s | 6.4x |

The with-GIL column is *flat* (and slightly worse at higher thread counts due to GIL contention overhead). The no-GIL column scales nearly linearly with cores up to the number of physical cores, then plateaus (hyperthreading does not help much for this kernel).

Your numbers will vary. The shape will not.

## 5. The memo

`MEMO.md`, 300 words. Address:

1. **Why is the with-GIL column flat?** The threads serialise on the GIL; only one is running the kernel at any time. Adding threads adds context-switching overhead without parallelism.
2. **Why does the no-GIL column scale less than linearly?** Three factors: (a) memory bandwidth is shared across cores, so a bandwidth-bound kernel cannot scale further than the memory subsystem allows; (b) hyperthreading shares execution units; (c) the OS adds context-switch overhead.
3. **At 8 threads, why is the no-GIL kernel ~6.4x faster than 1 thread, not 8x?** Pick two of: memory bandwidth, NUMA effects, thermal throttling, OS scheduling jitter.
4. **What would the curve look like for a kernel that does I/O instead of computation?** A `time.sleep` kernel would scale nearly linearly even *with* the GIL — because `time.sleep` releases the GIL internally. Most I/O does. The GIL is a CPU-bound bottleneck, not an I/O-bound one.
5. **In production code, where do you put the `with nogil:` block?** Around any C-only computation longer than ~10 microseconds. Shorter than that and the release/acquire overhead is comparable to the work.

## Acceptance criteria

- [ ] Folder `challenge-02-gil-release/` contains: `heavy.pyx`, `setup.py` or just the cythonized `.so`, `bench.py`, `MEMO.md`, optionally a `curve.png`.
- [ ] Both `heavy_with_gil` and `heavy_no_gil` exist and produce the same output.
- [ ] The benchmark runs for at least 1, 2, 4, 8 threads.
- [ ] At 4 threads, `heavy_no_gil` is at least 2x faster than `heavy_with_gil`. (Less than that and your kernel might be too short — increase `N_ITER`.)
- [ ] The memo is 250–350 words and addresses all five questions.

## Common pitfalls

- **The kernel is too short.** A 50 ms kernel run on 8 threads becomes a 6 ms job; measurement noise (timer resolution, JIT warm-up) dominates. Make sure single-thread is at least 300 ms.
- **You share buffers across threads.** Each call should have its own `x` and `out`. Otherwise threads contend on the same memory and you measure cache-line ping-pong, not parallel speedup.
- **You use `multiprocessing` instead of `threading`.** Multiprocessing always scales linearly (modulo IPC) because each process has its own GIL. The point of this challenge is to see the thread-level behaviour. Stick to `ThreadPoolExecutor`.
- **You expect 8x at 8 threads on a 4-core CPU.** Apple Silicon M2 has 4 performance cores + 4 efficiency cores. Most consumer x86 chips are 4–8 cores. Hyperthreading doubles the *logical* count without doubling throughput. 6–7x is the realistic ceiling at "8 threads" on most modern laptops.
- **You forget `boundscheck=False`.** Cython's bounds checks happen on every memoryview access, *requires the GIL*, and would force the function to acquire the GIL inside the `nogil` block. With bounds checking off, the inner loop is pure C and the GIL stays released.

## Reading

- Cython "Working with Python arrays" — when memoryviews and nogil mix: <https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html#using-memoryviews>.
- The GIL in the C API docs: <https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock>.
- Cython's `prange` for parallel loops (the next step up from `with nogil:`): <https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html>. Stretch goal: rewrite the kernel using `prange` and see if you can get the same speedup without the Python-side thread pool.
