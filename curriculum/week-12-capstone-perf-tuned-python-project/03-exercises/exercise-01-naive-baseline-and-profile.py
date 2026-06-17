"""Exercise 01 — The naive baseline and the profile.

Goal: write a naive baseline for a small image kernel (1D blur over a
grayscale row), profile it with cProfile, and identify the hot line. The
exercise is intentionally small so you can finish it in 20 minutes; the
discipline being practised is profile-first, not optimise-first.

Run:
    python3 exercise-01-naive-baseline-and-profile.py

References:
    - PEP 7 (CPython C style) — informational only here.
    - https://docs.python.org/3/library/profile.html
    - https://docs.python.org/3/library/time.html#time.perf_counter
"""

from __future__ import annotations

import cProfile
import math
import pstats
import time
from typing import Sequence


def make_kernel_1d(sigma: float) -> list[float]:
    """Build a 1D normalised gaussian kernel.

    Length is 2 * ceil(3 * sigma) + 1.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    radius: int = math.ceil(3 * sigma)
    raw: list[float] = [
        math.exp(-(i * i) / (2 * sigma * sigma)) for i in range(-radius, radius + 1)
    ]
    total: float = sum(raw)
    return [v / total for v in raw]


def blur_naive(row: Sequence[int], sigma: float) -> list[int]:
    """The naive baseline: pure-Python loop, no NumPy.

    Walks the row with a Python `for` loop, computes a weighted sum over
    the neighbourhood, clamps to [0, 255], stores as int. Boundary
    handling: zero-padding.
    """
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


def correctness_check(out: list[int], expected_length: int) -> None:
    """Sanity check on the baseline output."""
    assert len(out) == expected_length, "length mismatch"
    assert all(0 <= v <= 255 for v in out), "out-of-range pixel"


def measure_wallclock(row: list[int], sigma: float, runs: int = 5) -> float:
    """Run blur_naive `runs` times. Return the median wall-clock (seconds)."""
    times: list[float] = []
    for _ in range(runs):
        t0: float = time.perf_counter()
        _ = blur_naive(row, sigma)
        times.append(time.perf_counter() - t0)
    times.sort()
    return times[len(times) // 2]


def profile_run(row: list[int], sigma: float) -> str:
    """Run blur_naive once under cProfile. Return the formatted top-10 report."""
    profiler: cProfile.Profile = cProfile.Profile()
    profiler.enable()
    _ = blur_naive(row, sigma)
    profiler.disable()
    stats: pstats.Stats = pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE)
    # Capture the top 10 to a string.
    import io

    buf: io.StringIO = io.StringIO()
    stats.stream = buf
    stats.print_stats(10)
    return buf.getvalue()


def main() -> None:
    # A row of 50,000 grayscale pixels (uint8 range). Seed-deterministic.
    import random

    random.seed(42)
    row: list[int] = [random.randint(0, 255) for _ in range(50_000)]
    sigma: float = 2.0

    out: list[int] = blur_naive(row, sigma)
    correctness_check(out, len(row))

    median_seconds: float = measure_wallclock(row, sigma, runs=5)
    print(f"Median wall-clock over 5 runs: {median_seconds * 1000:.1f} ms")

    print("\ncProfile top-10 (cumulative):")
    print(profile_run(row, sigma))

    # The discipline question: which function or which line accounted for
    # most of the wall-clock? Answer in the comment below, then SOLUTIONS.md.
    #
    # YOUR ANSWER HERE:
    # ----------------------------------------------------------------
    # Hot path (your interpretation of the cProfile output):
    #
    #
    # ----------------------------------------------------------------


if __name__ == "__main__":
    main()
