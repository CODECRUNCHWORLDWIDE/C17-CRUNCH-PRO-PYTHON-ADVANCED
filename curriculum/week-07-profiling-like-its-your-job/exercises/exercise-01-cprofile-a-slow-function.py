"""
Exercise 1 - cProfile a slow function. Find the *real* bottleneck.

Goal: prove in code that the function with the largest cumulative time
in a cProfile table is almost never the function you should fix. The
function you should fix is the one with the largest *tottime*; the
function with the largest cumtime usually just calls a lot of things.

The workload below is deliberately misleading:

  - process_records is a thin orchestrator. It calls validate_record
    and then transform_record on each row. Its cumtime will be ~100%
    of the run (it covers the whole call tree below it). Its tottime
    will be near zero.

  - transform_record looks like the heavy function. It builds a string
    with sorting and formatting. A naive read of the cumulative-sorted
    cProfile table will single it out as "the slow one." It is not.

  - normalise_field is the hot leaf. It is called once per field per
    record - O(records x fields_per_record) - and it does several
    things per call (lowercase, strip, replace, possibly compile a
    regex). The fix is here.

Acceptance criteria:

  - Script runs end-to-end on CPython 3.11+.
  - Sorted-by-cumulative output puts <module>, main, process_records,
    and transform_record near the top.
  - Sorted-by-tottime output puts normalise_field and string built-ins
    (re.sub, str.strip, str.lower) near the top.
  - The student identifies normalise_field as the hot leaf and the
    `re.compile` inside it as the per-call cost.
  - The optimised version (move the compile outside the loop) is at
    least 2x faster end-to-end.

Estimated time: 45 minutes.

Run with:
    python exercise-01-cprofile-a-slow-function.py

Reading before / during:
  - Lecture 1 sections 9, 11 (the obvious-looking bottleneck).
  - Lecture 2 sections 3, 5, 7 (tottime vs. cumtime).
  - docs.python.org/3/library/profile.html

References:
  - https://docs.python.org/3/library/profile.html
  - PEP 657 (column-level position info, 3.11+): https://peps.python.org/pep-0657/
"""

from __future__ import annotations

import cProfile
import pstats
import re
import time
from typing import Iterable, List


# -----------------------------------------------------------------------------
# The workload.
# -----------------------------------------------------------------------------


def normalise_field(value: str) -> str:
    """
    The hot leaf. Called once per field per record.

    Notice the *re.compile inside the function* - a pattern that recompiles
    the same regex thousands of times. This is the bottleneck.
    """
    pattern = re.compile(r"\s+")  # <-- the trap. Compile-per-call.
    stripped = value.strip()
    lowered = stripped.lower()
    return pattern.sub(" ", lowered)


def validate_record(record: dict[str, str]) -> bool:
    """Quick sanity checks. Should be fast; is."""
    required = ("id", "name", "email")
    if not all(k in record for k in required):
        return False
    if not record["id"].isdigit():
        return False
    return True


def transform_record(record: dict[str, str]) -> str:
    """
    Builds a "|"-joined string. *Looks* like the work-doer. It is mostly
    a dispatcher: it iterates record keys and calls normalise_field
    on each. Its tottime is small; its cumtime is large.
    """
    keys = sorted(record.keys())
    parts: List[str] = []
    for k in keys:
        value = normalise_field(record[k])
        parts.append(f"{k}={value}")
    return "|".join(parts)


def process_records(records: Iterable[dict[str, str]]) -> List[str]:
    """Outer loop. tottime near zero; cumtime ~100% of the run."""
    out: List[str] = []
    for r in records:
        if validate_record(r):
            out.append(transform_record(r))
    return out


# -----------------------------------------------------------------------------
# The optimised version. After profiling, this is what you write.
# -----------------------------------------------------------------------------


_WHITESPACE_RE = re.compile(r"\s+")  # module-level - compile once.


def normalise_field_fast(value: str) -> str:
    """Same semantics; pattern compiled exactly once at import time."""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def transform_record_fast(record: dict[str, str]) -> str:
    keys = sorted(record.keys())
    parts: List[str] = []
    for k in keys:
        parts.append(f"{k}={normalise_field_fast(record[k])}")
    return "|".join(parts)


def process_records_fast(records: Iterable[dict[str, str]]) -> List[str]:
    out: List[str] = []
    for r in records:
        if validate_record(r):
            out.append(transform_record_fast(r))
    return out


# -----------------------------------------------------------------------------
# Test data + driver.
# -----------------------------------------------------------------------------


def make_records(n: int) -> List[dict[str, str]]:
    """A list of synthetic records with the same shape. Whitespace is
    inserted in some fields so normalise_field has a non-trivial pattern
    match to do."""
    out: List[dict[str, str]] = []
    for i in range(n):
        out.append(
            {
                "id": str(i),
                "name": f"  User    {i}  ",
                "email": f"user{i}@example.com",
                "phone": f"+1   555  {i:04d}",
            }
        )
    return out


def time_unprofiled(fn, records: List[dict[str, str]]) -> float:
    """Time a function on the records list, return wall-clock seconds."""
    t0 = time.perf_counter()
    fn(records)
    return time.perf_counter() - t0


def print_sorted(stats: pstats.Stats, key: str, n: int = 15) -> None:
    """Print top n rows of a Stats object sorted by `key`."""
    print(f"\n----- Top {n} by {key} -----")
    stats.sort_stats(key).print_stats(n)


def main() -> None:
    records = make_records(20_000)
    print(f"Test corpus: {len(records)} records, 4 fields each.\n")

    # 1. Baseline (unprofiled).
    t_naive = time_unprofiled(process_records, records)
    print(f"Naive (unprofiled):       {t_naive:.3f}s")

    # 2. Optimised (unprofiled).
    t_fast = time_unprofiled(process_records_fast, records)
    print(f"Optimised (unprofiled):   {t_fast:.3f}s")
    print(f"Speedup: {t_naive / t_fast:.2f}x\n")

    # 3. Profile the naive implementation. The point of the exercise.
    print("=" * 70)
    print("Profiling the NAIVE implementation. Read both tables.")
    print("=" * 70)
    with cProfile.Profile() as pr:
        process_records(records)

    stats = pstats.Stats(pr).strip_dirs()
    print_sorted(stats, "cumulative", 15)
    print_sorted(stats, "tottime", 15)

    print(
        "\nThe cumulative-sorted table will lead you to optimise transform_record\n"
        "or process_records. The tottime-sorted table will lead you to the actual\n"
        "hot leaf: normalise_field, where re.compile is invoked per-call.\n"
    )

    # 4. Profile the optimised implementation. The hot leaf moves.
    print("=" * 70)
    print("Profiling the OPTIMISED implementation. Note the hot leaf shifts.")
    print("=" * 70)
    with cProfile.Profile() as pr2:
        process_records_fast(records)

    stats2 = pstats.Stats(pr2).strip_dirs()
    print_sorted(stats2, "tottime", 15)

    print(
        "\nAfter the fix, normalise_field is no longer hot. The remaining tottime\n"
        "is spread across str.strip, str.lower, re.Pattern.sub, and dict access.\n"
        "These are built-ins - further optimisation requires a different shape\n"
        "(e.g. precompile, batch, skip empty values), not a faster Python rewrite.\n"
    )


if __name__ == "__main__":
    main()
