"""
Exercise 3 — `__slots__` memory comparison.

Goal: measure the memory footprint of 1 million instances of a regular
class vs. a __slots__ class. Confirm the difference matches your mental
model.

Estimated time: 30 minutes.

Run with: python exercise-03-slots-comparison.py
Optional: pip install pympler  for the per-class accurate measurement.

Acceptance:
- The script runs and prints the comparison table.
- You explain why the difference is what it is.
- You write a paragraph in `notes/exercise-03.md` describing when you
  would (and would not) use __slots__ on a real class.
"""

from __future__ import annotations

import gc
import sys
import tracemalloc


class Regular:
    """A normal class with a __dict__."""

    def __init__(self, x: int, y: int, name: str) -> None:
        self.x = x
        self.y = y
        self.name = name


class Slotted:
    """A class declaring __slots__."""

    __slots__ = ("x", "y", "name")

    def __init__(self, x: int, y: int, name: str) -> None:
        self.x = x
        self.y = y
        self.name = name


def measure_with_sys(cls, n: int = 1_000_000) -> tuple[int, int]:
    """Estimate total bytes for n instances using sys.getsizeof().

    Note: sys.getsizeof on a Regular instance does NOT count the __dict__.
    We add it explicitly so the comparison is fair.
    """
    gc.collect()
    instance = cls(1, 2, "name")
    per_object = sys.getsizeof(instance)
    per_dict = sys.getsizeof(getattr(instance, "__dict__", {}))
    total = (per_object + per_dict) * n
    return per_object + per_dict, total


def measure_with_tracemalloc(cls, n: int = 1_000_000) -> int:
    """Measure actual incremental allocation by creating n instances under tracemalloc."""
    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    holder = [cls(1, 2, "name") for _ in range(n)]
    snapshot_after = tracemalloc.take_snapshot()
    diff = snapshot_after.compare_to(snapshot_before, "filename")
    total = sum(stat.size_diff for stat in diff)
    tracemalloc.stop()
    del holder
    return total


def main() -> None:
    n = 100_000  # smaller for fast runs; bump to 1_000_000 for production-style measurement
    print(f"Measuring with n={n:,} instances each.\n")

    regular_per, regular_total_via_sys = measure_with_sys(Regular, n)
    slotted_per, slotted_total_via_sys = measure_with_sys(Slotted, n)

    print("=" * 60)
    print("Method 1: sys.getsizeof + __dict__ size estimate")
    print("=" * 60)
    print(f"  Regular per-instance:  {regular_per:>7,} bytes")
    print(f"  Slotted per-instance:  {slotted_per:>7,} bytes")
    print(f"  Regular x{n:,}:         {regular_total_via_sys:>10,} bytes (~{regular_total_via_sys / 1024**2:.1f} MiB)")
    print(f"  Slotted x{n:,}:         {slotted_total_via_sys:>10,} bytes (~{slotted_total_via_sys / 1024**2:.1f} MiB)")
    print(f"  Savings:               {1 - slotted_total_via_sys / regular_total_via_sys:>7.1%}")
    print()

    print("=" * 60)
    print("Method 2: tracemalloc (actual allocator-tracked bytes)")
    print("=" * 60)
    regular_tm = measure_with_tracemalloc(Regular, n)
    slotted_tm = measure_with_tracemalloc(Slotted, n)
    print(f"  Regular x{n:,}:         {regular_tm:>10,} bytes (~{regular_tm / 1024**2:.1f} MiB)")
    print(f"  Slotted x{n:,}:         {slotted_tm:>10,} bytes (~{slotted_tm / 1024**2:.1f} MiB)")
    print(f"  Savings:               {1 - slotted_tm / regular_tm:>7.1%}")
    print()
    print("Note: tracemalloc measures the actual allocator activity, including")
    print("the list that holds references. The two methods should agree to within")
    print("a constant factor.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# REFLECTION (commit to notes/exercise-03.md)
# -----------------------------------------------------------------------------
# 1. Did the measured savings match what you predicted before running?
# 2. Try adding `color = "red"` after instantiation. Regular allows it;
#    Slotted raises AttributeError. Why does that matter for production?
# 3. Try `weakref.ref(slotted_instance)` — also fails by default. How would
#    you make it work? (Answer: add "__weakref__" to __slots__.)
# 4. Try `@dataclass(slots=True)` from `dataclasses`. Refactor `Slotted`
#    to use it. Re-run the measurement. Same numbers?
# 5. When would you NOT reach for __slots__? Name two cases where the cost
#    outweighs the benefit (mixin classes that need __dict__, classes
#    where users patch attributes, classes used in tests that need MagicMock).
# -----------------------------------------------------------------------------
