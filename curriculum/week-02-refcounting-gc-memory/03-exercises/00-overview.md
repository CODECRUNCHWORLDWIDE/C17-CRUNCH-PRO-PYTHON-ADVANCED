# Week 2 — Exercises

Three exercises. ~30 min each.

1. **[Trace refcounts](./exercise-01-trace-refcounts.py)** — watch counts move with `sys.getrefcount`.
2. **[Build a cycle](./exercise-02-build-a-cycle.py)** — construct, detect, break a reference cycle.
3. **[`__slots__` comparison](./exercise-03-slots-comparison.py)** — measure the memory win on 1M instances.

Each is a Python file with TODO blocks and an embedded HINT block at the bottom. Do them in order.

## Self-check

After each exercise, you should be able to:

1. **Ex 1:** Predict the refcount of a freshly-bound name without running the code.
2. **Ex 2:** Recognize a cycle in code at a glance.
3. **Ex 3:** Defend a choice to use `__slots__` (or not) on a real class.
