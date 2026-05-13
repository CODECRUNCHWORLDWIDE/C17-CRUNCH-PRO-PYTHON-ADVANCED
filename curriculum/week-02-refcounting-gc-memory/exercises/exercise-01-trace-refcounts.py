"""
Exercise 1 — Trace refcounts

Goal: predict the refcount of an object at six points in the program below.
Run the script, compare your predictions to actual values, and explain any
surprises.

Estimated time: 30 minutes.

Run with: python exercise-01-trace-refcounts.py

Acceptance criteria:
- You have written predictions for each TODO before running the script.
- You can explain every "actual vs predicted" discrepancy.
- Your reflections are committed to `notes/exercise-01.md` in your portfolio.

Important:
- sys.getrefcount(x) always reports one MORE than the "real" count because
  passing x to getrefcount is itself a reference. So when reading "actual:
  3" treat it as "real count is 2".
- Singletons (None, True, False, small ints -5..256, interned short strings)
  have artificially high counts because they're shared across the interpreter.
"""

from __future__ import annotations

import sys


def show(label: str, obj) -> None:
    """Print actual refcount, accounting for getrefcount's own bump."""
    # subtract 1 to undo getrefcount's increment, for clarity
    print(f"{label:<40} actual_real={sys.getrefcount(obj) - 1}")


def main() -> None:
    print("Stage 1: bind a fresh list to x")
    x = ["a"]
    # TODO: write your predicted refcount of x here in a comment, then run.
    # PREDICTION:
    show("1. fresh x = ['a']", x)

    print("\nStage 2: bind y to the same list")
    y = x
    # TODO: predict
    # PREDICTION:
    show("2. y = x", x)

    print("\nStage 3: put x into a list 3 times")
    container = [x, x, x]
    # TODO: predict
    # PREDICTION:
    show("3. container = [x, x, x]", x)

    print("\nStage 4: del y")
    del y
    # TODO: predict
    # PREDICTION:
    show("4. del y", x)

    print("\nStage 5: container.clear()")
    container.clear()
    # TODO: predict
    # PREDICTION:
    show("5. container.clear()", x)

    print("\nStage 6: a tuple holding x (immutable container — same rules)")
    tup = (x, x)
    # TODO: predict
    # PREDICTION:
    show("6. tup = (x, x)", x)

    print()
    print("Bonus — singleton behavior:")
    print(f"  sys.getrefcount(None)            = {sys.getrefcount(None)}")
    print(f"  sys.getrefcount(42)              = {sys.getrefcount(42)}")
    print(f"  sys.getrefcount(257)             = {sys.getrefcount(257)}")
    print()
    print("Notice: small ints (-5..256) are CACHED, so refcounts are huge.")
    print("257 is not cached, so a fresh literal gets its own object.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# REFLECTION (do AFTER running and recording your predictions)
# -----------------------------------------------------------------------------
# 1. Where were your predictions correct?
# 2. Which stage surprised you, and why?
# 3. Why does the count NOT change when we move from stage 5 (cleared
#    container) to stage 6 (added to a tuple)?
#    Answer: it does change — by exactly 2 (one per tuple slot). If your
#    prediction missed this, you're conflating "tuple is immutable" with
#    "tuple doesn't bump refcounts." Tuples DO hold references. They just
#    can't reassign them.
# 4. Write a similar exercise with a dict holding x as a value. Does the
#    refcount go up by 1 (for the dict's value reference)? What about a
#    dict where x is the key?
#
# -----------------------------------------------------------------------------
# ANSWER KEY (DO NOT READ until you've predicted)
# -----------------------------------------------------------------------------
# Stage 1: 1 (just x)
# Stage 2: 2 (x and y)
# Stage 3: 5 (x, y, container slot 0, container slot 1, container slot 2)
# Stage 4: 4 (x, container slot 0, container slot 1, container slot 2)
# Stage 5: 1 (just x — container.clear() decrements each slot)
# Stage 6: 3 (x, tup slot 0, tup slot 1)
#
# These are the "real" counts, i.e., what `show()` prints (after we subtract
# the getrefcount bump).
# -----------------------------------------------------------------------------
