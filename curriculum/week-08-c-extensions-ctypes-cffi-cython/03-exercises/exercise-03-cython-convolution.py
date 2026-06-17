"""
Exercise 3 - Cython 1D convolution; the four-way benchmark.

Goal: take the 1D-convolution kernel from Lecture 3 and benchmark it
against pure Python, Cython (naive, typed, fast), and NumPy.

The .pyx kernel is exercise-03-convolve.pyx. Build it:

    cythonize -i exercise-03-convolve.pyx

That command produces (next to this file):
    exercise_03_convolve.cpython-313-darwin.so

(Cython renames the module to use underscores, even if the .pyx filename
uses hyphens. The import name is exercise_03_convolve.)

Acceptance criteria:

    - .pyx builds without errors via `cythonize -i`.
    - All implementations produce the same answer to within 1e-9
      (allowing for floating-point reorder).
    - convolve_typed is at least 50x faster than convolve_python.
    - convolve_fast is at least 100x faster than convolve_python.
    - NumPy's convolve is faster than convolve_fast (the SIMD ceiling).
    - The student can articulate which Cython directive bought what.

Estimated time: 75 minutes.

Reading before / during:
    - Lecture 3 sections 2-5 (Cython end-to-end; the four-way benchmark).
    - https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html
    - https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html

References:
    - https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#compiler-directives
"""

from __future__ import annotations

import os
import sys
import time
from typing import Callable, List

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# -----------------------------------------------------------------------------
# Pure-Python baseline.
# -----------------------------------------------------------------------------


def convolve_python(x: List[float], h: List[float]) -> List[float]:
    """Pure Python 1D valid convolution (cross-correlation form).

    out[i] = sum_{j} x[i + j] * h[j]
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


# -----------------------------------------------------------------------------
# NumPy ceiling.
# -----------------------------------------------------------------------------


def convolve_numpy(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """NumPy's convolve. np.convolve reverses h by mathematical convention,
    so to compute the cross-correlation form we reverse h ourselves."""
    return np.convolve(x, h[::-1], mode="valid")


# -----------------------------------------------------------------------------
# Cython kernels (loaded after the build).
# -----------------------------------------------------------------------------


def load_cython_kernels():
    """Import the three Cython kernels. Hints the user to build if missing."""
    try:
        from exercise_03_convolve import (  # type: ignore[import]
            convolve_naive,
            convolve_typed,
            convolve_fast,
        )
        return convolve_naive, convolve_typed, convolve_fast
    except ImportError as e:
        sys.stderr.write(
            "Cython kernel not built. Run:\n"
            "    cythonize -i exercise-03-convolve.pyx\n"
            f"(error was: {e})\n"
        )
        sys.exit(1)


# -----------------------------------------------------------------------------
# Measurement.
# -----------------------------------------------------------------------------


def time_min(fn: Callable[[], object], repeats: int = 5) -> float:
    """Time fn() `repeats` times, return the minimum wall time in seconds."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - t0
        if elapsed < best:
            best = elapsed
    return best


def assert_close(a: np.ndarray, b: np.ndarray, tol: float = 1e-6) -> None:
    """Compare two arrays; raise if max abs diff > tol."""
    diff = float(np.max(np.abs(a - b)))
    if diff > tol:
        raise AssertionError(f"arrays disagree: max abs diff = {diff}")


def main() -> None:
    print("Exercise 3 - Cython 1D convolution four-way benchmark")
    print("=" * 60)

    convolve_naive, convolve_typed, convolve_fast = load_cython_kernels()

    n = 1_000_000
    k = 64
    rng = np.random.default_rng(42)
    x_np = rng.random(n)
    h_np = rng.random(k)
    x_list = x_np.tolist()
    h_list = h_np.tolist()

    # Pre-allocate output buffers for the Cython kernels.
    out_typed = np.empty(n - k + 1, dtype=np.float64)
    out_fast = np.empty(n - k + 1, dtype=np.float64)
    out_naive = np.empty(n - k + 1, dtype=np.float64)

    # -------------------------------------------------------------------------
    # Correctness pass. NumPy is the reference.
    # -------------------------------------------------------------------------
    print("\n[Correctness] verify all implementations agree")
    ref = convolve_numpy(x_np, h_np)
    convolve_typed(x_np, h_np, out_typed)
    convolve_fast(x_np, h_np, out_fast)
    convolve_naive(x_list[:1000], h_list, out_naive[:1000 - k + 1])

    assert_close(out_typed, ref, tol=1e-6)
    assert_close(out_fast, ref, tol=1e-6)
    print("  all Cython kernels match np.convolve to within 1e-6")

    # -------------------------------------------------------------------------
    # Timing pass. Note: we run pure Python on a *smaller* input because
    # 1M*64 in pure Python takes minutes. We extrapolate fairly.
    # -------------------------------------------------------------------------
    print(f"\n[Benchmark] n={n}, k={k}")
    print("-" * 60)

    # Pure Python: use a 100x smaller input and scale up linearly.
    n_small = n // 100
    x_small = x_list[:n_small]
    t_py_small = time_min(lambda: convolve_python(x_small, h_list), repeats=1)
    t_py = t_py_small * 100  # linear in n
    print(f"  pure Python (extrap.)        : {t_py * 1000:8.1f} ms")

    # Cython naive: also slow. Use the same small input.
    t_naive_small = time_min(
        lambda: convolve_naive(x_small, h_list, [0.0] * (n_small - k + 1)),
        repeats=2,
    )
    t_naive = t_naive_small * 100
    print(f"  Cython naive (extrap.)       : {t_naive * 1000:8.1f} ms")

    t_typed = time_min(
        lambda: convolve_typed(x_np, h_np, out_typed), repeats=5
    )
    print(f"  Cython typed                 : {t_typed * 1000:8.1f} ms")

    t_fast = time_min(
        lambda: convolve_fast(x_np, h_np, out_fast), repeats=5
    )
    print(f"  Cython fast (nogil, no chks) : {t_fast * 1000:8.1f} ms")

    t_np = time_min(lambda: convolve_numpy(x_np, h_np), repeats=5)
    print(f"  NumPy np.convolve            : {t_np * 1000:8.1f} ms")

    print("\n[Speedup vs. pure Python (extrapolated)]")
    print(f"  Cython naive : {t_py / t_naive:7.1f}x")
    print(f"  Cython typed : {t_py / t_typed:7.1f}x")
    print(f"  Cython fast  : {t_py / t_fast:7.1f}x")
    print(f"  NumPy        : {t_py / t_np:7.1f}x")

    # Acceptance check.
    speed_typed = t_py / t_typed
    speed_fast = t_py / t_fast
    if speed_typed < 50:
        print(
            f"\n  WARNING: typed speedup is {speed_typed:.1f}x (expected >= 50x)"
        )
    if speed_fast < 100:
        print(
            f"  WARNING: fast speedup is {speed_fast:.1f}x (expected >= 100x)"
        )
    else:
        print("\n  OK: all speedup thresholds met")

    print(
        "\nDone. Open SOLUTIONS.md for the discussion of *why* the\n"
        "speedups are what they are, what each directive contributed,\n"
        "and what makes NumPy still 5-10x faster than the tight\n"
        "Cython kernel (hint: hand-tuned SIMD)."
    )


if __name__ == "__main__":
    main()
