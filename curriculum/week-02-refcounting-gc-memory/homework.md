# Week 2 — Homework

Six problems, ~6h. Commit each.

---

## Problem 1 — Run `tracemalloc` against your Week-1 mini-project (60 min)

Take the `pyexplain` CLI you built in Week 1. Run it under `tracemalloc.start()` against a large input file (e.g., a 5,000-line Python source). Capture the top 10 allocation lines.

**Acceptance:**

- `tracemalloc-pyexplain.md` in your portfolio with the output and a 100-word reflection: where would you optimize first?

---

## Problem 2 — Build a class with `__slots__` and measure (45 min)

Write two versions of a `LogRecord` class with fields `timestamp`, `level`, `message`, `module`, `func`. One regular, one slotted. Construct 1,000,000 of each. Measure with `sys.getsizeof` and `tracemalloc`. Report the savings ratio.

**Acceptance:**

- `slots-measurement.py` that runs and prints the comparison.
- `slots-results.md` with the numbers and a paragraph on when the savings are worth it.

---

## Problem 3 — Detect the cycle in this code (60 min)

```python
class Tree:
    def __init__(self, value):
        self.value = value
        self.children = []
        self.parent = None

def add_child(parent, child):
    parent.children.append(child)
    child.parent = parent

root = Tree(0)
left = Tree(1)
right = Tree(2)
add_child(root, left)
add_child(root, right)
```

**Acceptance:**

- `cycle-analysis.md` in your portfolio answering:
  - Is there a cycle in the object graph? Draw it.
  - Will refcounting alone free `root` when the variable goes out of scope?
  - How would you redesign with `weakref` to avoid the cycle?
  - Measure (with `tracemalloc`): how does the leak grow if you build 1,000 trees and discard them?

---

## Problem 4 — Find a leak in a real Flask/FastAPI demo (90 min)

Take any small open-source Flask/FastAPI demo (or your own from C16 Week 1 mini-project). Run it under `memray run` with a stress test that hits 1,000 requests. Capture the flamegraph.

**Acceptance:**

- A `memray.bin` file (or the flamegraph HTML export) committed.
- `leak-or-not.md` with your conclusion: is there a leak? If yes, where? If no, what's the steady-state memory and is that reasonable?

---

## Problem 5 — Read `Modules/gcmodule.c` (45 min)

Browse the CPython source for the cyclic GC. Find the function that walks objects looking for cycles.

**Acceptance:**

- `gcmodule-reading.md` with:
  - GitHub permalink to the function you read.
  - A 200-word summary in your own words of how it identifies a cycle.
  - One thing you learned that wasn't in this week's lectures.

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 300-400 words:

1. Before this week, did you have a mental model of "what dying objects look like" in Python? How has it changed?
2. Which of `tracemalloc` / `memray` / `objgraph` will you reach for first in real work? Why?
3. Will you use `__slots__` more after this week? In what kinds of classes?
4. What's still confusing? Be specific.

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 — tracemalloc against pyexplain | 60 min |
| 2 — slots measurement | 45 min |
| 3 — cycle analysis | 60 min |
| 4 — Flask/FastAPI leak hunt | 90 min |
| 5 — Read gcmodule.c | 45 min |
| 6 — Reflection | 45 min |
| **Total** | **~5 h 45 m** |

After homework, ship the [mini-project](./mini-project/README.md).
