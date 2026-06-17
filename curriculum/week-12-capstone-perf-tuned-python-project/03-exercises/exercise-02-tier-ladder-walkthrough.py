"""Exercise 02 — Walk the tier ladder on a small kernel.

Goal: implement the same 1D blur kernel from exercise-01 at four tiers:

    Tier 0: naive Python loop (already provided, imported from this file).
    Tier 1: algorithmic note — for 1D blur there is no separability to
            exploit (already 1D), but we *can* precompute a prefix sum
            for the box-blur approximation; we do the gaussian here, so
            Tier 1 is "use builtin sum/zip more efficiently."
    Tier 2: NumPy vectorisation.
    Tier 3: SciPy convolve1d.

Time each tier. Report the speedups. Compare against the success criterion
(at least 50x against Tier 0).

Run:
    python3 exercise-02-tier-ladder-walkthrough.py

Notes:
    - NumPy and SciPy are required. `pip install numpy scipy`.
    - This file imports from exercise-01-naive-baseline-and-profile.py if
      it is on the path; we re-implement the small helpers here to keep
      the exercise self-contained.

References:
    - https://numpy.org/doc/stable/reference/generated/numpy.convolve.html
    - https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.convolve1d.html
"""

from __future__ import annotations

import math
import time
from typing import Sequence

try:
    import numpy as np
    from scipy.ndimage import convolve1d
except ImportError:
    np = None  # type: ignore[assignment]
    convolve1d = None  # type: ignore[assignment]


def make_kernel_1d(sigma: float) -> list[float]:
    """Same kernel as exercise-01."""
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    radius: int = math.ceil(3 * sigma)
    raw: list[float] = [
        math.exp(-(i * i) / (2 * sigma * sigma)) for i in range(-radius, radius + 1)
    ]
    total: float = sum(raw)
    return [v / total for v in raw]


def blur_tier0_naive(row: Sequence[int], sigma: float) -> list[int]:
    """Tier 0: pure-Python, nested loop. Slowest correct version."""
    kernel: list[float] = make_kernel_1d(sigma)
    radius: int = len(kernel) // 2
    n: int = len(row)
    out: list[int] = [0] * n
    for i in range(n):
        acc: float = 0.0
        for j in range(-radius, radius + 1):
            src_i: int = i + j
            if 0 <= src_i < n:
                acc += kernel[j + radius] * row[src_i]
        out[i] = max(0, min(255, int(round(acc))))
    return out


def blur_tier1_builtins(row: Sequence[int], sigma: float) -> list[int]:
    """Tier 1: still pure-Python, but lifted to builtin `sum` + slicing.

    The inner loop is replaced with a generator expression handed to the
    builtin `sum`, which iterates in C. This is a small speedup (typically
    2-3x) over the explicit Python loop.
    """
    kernel: list[float] = make_kernel_1d(sigma)
    radius: int = len(kernel) // 2
    n: int = len(row)
    out: list[int] = [0] * n
    for i in range(n):
        lo: int = max(0, i - radius)
        hi: int = min(n, i + radius + 1)
        k_lo: int = lo - (i - radius)
        # Use builtin sum + zip; both iterate in C.
        acc: float = sum(
            k * v for k, v in zip(kernel[k_lo : k_lo + (hi - lo)], row[lo:hi])
        )
        out[i] = max(0, min(255, int(round(acc))))
    return out


def blur_tier2_numpy(row: Sequence[int], sigma: float):  # type: ignore[no-untyped-def]
    """Tier 2: NumPy vectorisation via np.convolve.

    Returns a numpy array; the test harness handles the comparison.
    """
    if np is None:
        raise RuntimeError("NumPy not installed; install with: pip install numpy")
    kernel: list[float] = make_kernel_1d(sigma)
    arr = np.asarray(row, dtype=np.float32)
    k = np.asarray(kernel, dtype=np.float32)
    out = np.convolve(arr, k, mode="same")
    return np.clip(out, 0, 255).astype(np.uint8)


def blur_tier3_scipy(row: Sequence[int], sigma: float):  # type: ignore[no-untyped-def]
    """Tier 3: SciPy ndimage.convolve1d.

    SciPy's convolve1d is a C kernel with the GIL released for the bulk
    of the call. Typically a few times faster than np.convolve for the
    same input.
    """
    if convolve1d is None:
        raise RuntimeError("SciPy not installed; install with: pip install scipy")
    kernel: list[float] = make_kernel_1d(sigma)
    arr = np.asarray(row, dtype=np.float32)
    k = np.asarray(kernel, dtype=np.float32)
    out = convolve1d(arr, k, mode="constant", cval=0.0)
    return np.clip(out, 0, 255).astype(np.uint8)


def time_function(func, row, sigma, runs: int = 5) -> float:  # type: ignore[no-untyped-def]
    """Return the median wall-clock in milliseconds."""
    times: list[float] = []
    for _ in range(runs):
        t0: float = time.perf_counter()
        _ = func(row, sigma)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return times[len(times) // 2]


def correctness_compare(
    out_naive: list[int], out_tier: Sequence[int], tier_name: str, atol: int = 2
) -> bool:
    """Compare a tier output against the naive baseline within a tolerance.

    `atol=2` allows up to 2 grey-level difference per pixel — accounts
    for float vs int rounding differences between tiers.
    """
    if len(out_naive) != len(out_tier):
        print(f"  [{tier_name}] FAIL: length mismatch")
        return False
    max_diff: int = max(abs(int(a) - int(b)) for a, b in zip(out_naive, out_tier))
    if max_diff > atol:
        print(f"  [{tier_name}] FAIL: max grey-level difference = {max_diff} > {atol}")
        return False
    print(f"  [{tier_name}] OK: max grey-level difference = {max_diff}")
    return True


def main() -> None:
    import random

    random.seed(42)
    n: int = 50_000
    row: list[int] = [random.randint(0, 255) for _ in range(n)]
    sigma: float = 2.0

    print(f"Workload: n={n} pixels, sigma={sigma}")
    print(f"Kernel size: {len(make_kernel_1d(sigma))} taps")
    print()

    # Correctness reference.
    print("Correctness checks (atol=2 grey-levels):")
    out0 = blur_tier0_naive(row, sigma)
    correctness_compare(out0, out0, "Tier 0 (self)")
    correctness_compare(out0, blur_tier1_builtins(row, sigma), "Tier 1")
    if np is not None:
        correctness_compare(out0, list(blur_tier2_numpy(row, sigma)), "Tier 2")
    else:
        print("  [Tier 2] SKIP: NumPy not installed")
    if convolve1d is not None:
        correctness_compare(out0, list(blur_tier3_scipy(row, sigma)), "Tier 3")
    else:
        print("  [Tier 3] SKIP: SciPy not installed")

    print()
    print("Wall-clock (median of 5 runs, milliseconds):")
    t0: float = time_function(blur_tier0_naive, row, sigma)
    t1: float = time_function(blur_tier1_builtins, row, sigma)
    print(f"  Tier 0 (naive loop):       {t0:8.2f} ms   (1.00x)")
    print(f"  Tier 1 (builtin sum):      {t1:8.2f} ms   ({t0 / t1:6.2f}x)")
    if np is not None:
        t2: float = time_function(blur_tier2_numpy, row, sigma)
        print(f"  Tier 2 (numpy.convolve):   {t2:8.2f} ms   ({t0 / t2:6.2f}x)")
    if convolve1d is not None:
        t3: float = time_function(blur_tier3_scipy, row, sigma)
        print(f"  Tier 3 (scipy.convolve1d): {t3:8.2f} ms   ({t0 / t3:6.2f}x)")

    # SUCCESS CRITERION: at least 50x speedup from Tier 0 to Tier 2.
    # If you do not see 50x, your environment is unusual; document it in
    # SOLUTIONS.md and proceed.
    print()
    print("Done. Cross-check the speedups against the table in SOLUTIONS.md.")


if __name__ == "__main__":
    main()
