"""
Exercise 2 - line_profiler. Pinpoint the hot line inside a hot function.

Goal: get fluent with `kernprof -l -v` on a 30-line hot function. The
function does several things per iteration; cProfile would only tell
you "this whole function is slow." line_profiler tells you which lines.

Workload: a Monte Carlo estimator of pi. We sample N random points in
[-1, 1]^2 and count how many fall in the unit disk. The estimate is
4 * inside / N. Pure Python, no numpy. Plenty of per-iteration cost.

The naive implementation in `estimate_pi_naive` has four suspicious
lines:

  - random.random() called twice (one per coordinate)
  - the squared-distance computation in pure Python
  - the if-comparison and counter increment
  - the per-iteration history list append (a deliberate red herring)

Run line_profiler and you find that the history append - which you
might have thought was free - eats a meaningful share of the wall clock.
The fix is "do not maintain the history at all unless asked."

Acceptance criteria:

  - The script runs end-to-end without `kernprof` (the kernprof-or-not
    shim at the top makes @profile a no-op when not under kernprof).
  - Under `kernprof -l -v exercise-02-line-profile-a-loop.py`, the per-line
    table shows estimate_pi_naive with hits=N for each loop-body line.
  - The student identifies that the `history.append` line accounts for
    a non-trivial percentage of the per-iteration time.
  - estimate_pi_fast (no history kept) is at least 1.3x faster than
    estimate_pi_naive on the same N.

Estimated time: 30 minutes.

Run with:
    # First, baseline timings without kernprof:
    python exercise-02-line-profile-a-loop.py

    # Then under kernprof for the per-line table:
    kernprof -l -v exercise-02-line-profile-a-loop.py

Reading before / during:
  - Lecture 2 sections 8 - 8.3 (line_profiler in depth).
  - https://github.com/pyutils/line_profiler

References:
  - line_profiler README: https://github.com/pyutils/line_profiler
  - docs.python.org/3/library/random.html
"""

from __future__ import annotations

import random
import time
from typing import List, Tuple

# -----------------------------------------------------------------------------
# kernprof-or-not shim. Lets the script run with or without `kernprof`.
# When the script is run with `kernprof -l`, the launcher injects a
# `profile` decorator into builtins; otherwise we define a no-op.
# -----------------------------------------------------------------------------

try:
    profile  # type: ignore[name-defined,used-before-def]  # noqa: F821
except NameError:

    def profile(fn):
        return fn


# -----------------------------------------------------------------------------
# The naive estimator. Several distinct per-iteration costs.
# -----------------------------------------------------------------------------


@profile
def estimate_pi_naive(n_samples: int, seed: int = 42) -> Tuple[float, List[float]]:
    """
    Sample n_samples points in [-1, 1]^2; count how many are inside the
    unit disk. Return (pi_estimate, history).

    The history list records the running estimate every 1000 samples.
    It is a deliberate red herring - it looks free, it is not.
    """
    rng = random.Random(seed)
    inside = 0
    history: List[float] = []
    for i in range(n_samples):
        x = rng.random() * 2.0 - 1.0
        y = rng.random() * 2.0 - 1.0
        d2 = x * x + y * y
        if d2 <= 1.0:
            inside += 1
        history.append(4.0 * inside / max(1, i + 1))
    return 4.0 * inside / n_samples, history


# -----------------------------------------------------------------------------
# The fast estimator. Same algorithm; no history maintenance.
# -----------------------------------------------------------------------------


@profile
def estimate_pi_fast(n_samples: int, seed: int = 42) -> float:
    """
    Same algorithm; do not maintain the running history. The per-iteration
    append is the bottleneck the line profiler exposes.
    """
    rng = random.Random(seed)
    inside = 0
    for _ in range(n_samples):
        x = rng.random() * 2.0 - 1.0
        y = rng.random() * 2.0 - 1.0
        if x * x + y * y <= 1.0:
            inside += 1
    return 4.0 * inside / n_samples


# -----------------------------------------------------------------------------
# An even faster estimator. local-bind the random.random for a small win.
# Useful to see in the line_profiler output - the `rng_random = rng.random`
# binding removes a per-iteration attribute lookup.
# -----------------------------------------------------------------------------


@profile
def estimate_pi_fastest(n_samples: int, seed: int = 42) -> float:
    """Local-bind the bound method. Saves one attribute lookup per iteration."""
    rng = random.Random(seed)
    rng_random = rng.random  # avoid attribute lookup in the inner loop
    inside = 0
    for _ in range(n_samples):
        x = rng_random() * 2.0 - 1.0
        y = rng_random() * 2.0 - 1.0
        if x * x + y * y <= 1.0:
            inside += 1
    return 4.0 * inside / n_samples


# -----------------------------------------------------------------------------
# Driver.
# -----------------------------------------------------------------------------


def main() -> None:
    n = 1_000_000
    print(f"Estimating pi with {n:,} samples each.\n")

    # The estimator should agree across versions (same seed).
    t0 = time.perf_counter()
    pi_naive, _history = estimate_pi_naive(n)
    t_naive = time.perf_counter() - t0
    print(f"naive  pi={pi_naive:.5f}    wall={t_naive:.3f}s")

    t0 = time.perf_counter()
    pi_fast = estimate_pi_fast(n)
    t_fast = time.perf_counter() - t0
    print(f"fast   pi={pi_fast:.5f}    wall={t_fast:.3f}s")

    t0 = time.perf_counter()
    pi_fastest = estimate_pi_fastest(n)
    t_fastest = time.perf_counter() - t0
    print(f"fastest pi={pi_fastest:.5f}   wall={t_fastest:.3f}s")

    # Sanity check: all three should agree.
    assert abs(pi_naive - pi_fast) < 1e-9
    assert abs(pi_naive - pi_fastest) < 1e-9

    print(f"\nspeedup naive -> fast:    {t_naive / t_fast:.2f}x")
    print(f"speedup fast  -> fastest: {t_fast / t_fastest:.2f}x")
    print(f"speedup naive -> fastest: {t_naive / t_fastest:.2f}x\n")

    print("To see per-line attribution, run:")
    print("  kernprof -l -v exercise-02-line-profile-a-loop.py")
    print()
    print("The line_profiler table will show that estimate_pi_naive spends a")
    print("meaningful share of its time on the history.append line. Removing")
    print("the history list (estimate_pi_fast) recovers that time. Local-binding")
    print("rng.random (estimate_pi_fastest) recovers a smaller additional win.")


if __name__ == "__main__":
    main()
