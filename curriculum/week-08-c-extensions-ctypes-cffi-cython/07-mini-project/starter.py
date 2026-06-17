"""
mini-project starter - the 1D-convolution skeleton.

This is the default kernel from the mini-project spec. Use it as a starting
point if you have not picked a different kernel.

The pure-Python reference implementation is here. Your job:

  1. Pick a native path (ctypes / cffi API mode / Cython).
  2. Implement the same kernel in that path. Save it next to this file
     (kernel_native.py, kernel.c or kernel.pyx as appropriate).
  3. Write bench/bench.py that times all implementations against this one.
  4. Write MEMO.md explaining the speedups.

Acceptance: the native implementation produces the same answer as
convolve_python to within 1e-6, and is at least 10x faster on the default
inputs.

Reading:
  - All three Week 8 lectures.
  - Lecture 3 in particular: it walked through this exact kernel.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np


def convolve_python(x: List[float], h: List[float]) -> List[float]:
    """Pure-Python 1D valid convolution (cross-correlation form).

    out[i] = sum_{j} x[i + j] * h[j], for i in 0..len(x)-len(h).

    Uses Python lists, not NumPy. Type-hinted for explicitness.

    Parameters
    ----------
    x : list of float
        The input signal.
    h : list of float
        The kernel (filter).

    Returns
    -------
    out : list of float
        The convolved output, length len(x) - len(h) + 1.
    """
    n = len(x)
    k = len(h)
    out: List[float] = [0.0] * (n - k + 1)
    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s += x[i + j] * h[j]
        out[i] = s
    return out


def reference_numpy(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """NumPy reference. Use to verify correctness of your native impl.

    np.convolve reverses h by mathematical convention, so we reverse it
    here to compute the cross-correlation form.
    """
    return np.convolve(x, h[::-1], mode="valid")


def make_inputs(n: int, k: int, seed: int = 42) -> tuple:
    """Generate the default seeded inputs. Returns (x_list, h_list, x_np, h_np)."""
    rng = np.random.default_rng(seed=seed)
    x_np = rng.random(n)
    h_np = rng.random(k)
    return x_np.tolist(), h_np.tolist(), x_np, h_np


def time_min(fn, args: tuple, repeats: int = 1) -> float:
    """Time fn(*args) `repeats` times; return the minimum wall time."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        elapsed = time.perf_counter() - t0
        if elapsed < best:
            best = elapsed
    return best


def main() -> None:
    """Time the pure-Python implementation. Use this number as the baseline.

    The default inputs are N=1,000,000 and K=64. On a 2024 MacBook Pro M2
    this takes ~8 seconds in pure Python. If your machine is slower or
    faster, tune N until single-run time is in [5s, 20s].
    """
    n = 1_000_000
    k = 64

    print(f"Generating inputs: N={n}, K={k}")
    x_list, h_list, x_np, h_np = make_inputs(n, k)

    # On large inputs, pure Python is too slow to time directly. We measure
    # on a 100x smaller input and extrapolate linearly. Replace this with a
    # direct measurement once you are confident your machine handles it.
    print("Timing pure Python on N/100 and extrapolating...")
    n_small = n // 100
    x_small = x_list[:n_small]
    t_small = time_min(convolve_python, (x_small, h_list), repeats=1)
    t_py_extrapolated = t_small * 100
    print(f"  pure Python (extrapolated): {t_py_extrapolated * 1000:.0f} ms")

    print("\nReference NumPy timing:")
    t_np = time_min(reference_numpy, (x_np, h_np), repeats=5)
    print(f"  NumPy:                      {t_np * 1000:.1f} ms")
    print(f"  speedup of NumPy over Py:   {t_py_extrapolated / t_np:.0f}x")

    print(
        "\nNow:\n"
        "  1. Pick a path: ctypes / cffi API mode / Cython.\n"
        "  2. Implement the convolve kernel in that path.\n"
        "  3. Verify it agrees with reference_numpy on small inputs.\n"
        "  4. Benchmark it. Target: >=10x faster than pure Python (extrap).\n"
        "  5. Write MEMO.md."
    )


if __name__ == "__main__":
    main()
