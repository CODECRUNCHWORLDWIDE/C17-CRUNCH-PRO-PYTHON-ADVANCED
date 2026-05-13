# Week 3 — Homework

Six problems, ~6 hours total. Commit each as you finish.

---

## Problem 1 — Read `Python/bytecodes.c` and pick three opcodes (60 min)

Open `Python/bytecodes.c` in the CPython main branch on GitHub:
<https://github.com/python/cpython/blob/main/Python/bytecodes.c>

Pick three opcodes — one **stack-only** (e.g., `POP_TOP`, `SWAP`), one **adaptive** (e.g., `LOAD_ATTR`, `BINARY_OP`), and one **control-flow** (e.g., `JUMP_BACKWARD`, `POP_JUMP_IF_FALSE`).

**Acceptance:** `bytecodes-reading.md` in your portfolio:

- A GitHub permalink to each chosen opcode's DSL definition.
- For each opcode: a 100-word summary of (a) its stack effect, (b) any inline cache, (c) what happens on the failure / fallback path.
- One observation: which of the three was the hardest to read, and why?

---

## Problem 2 — Verify the `LOAD_FAST` vs. `LOAD_GLOBAL` cost in nanoseconds (60 min)

Write `bench_loads.py` that times two near-identical loops:

```python
def hot_with_global(n):
    s = 0
    for _ in range(n):
        s += len([1, 2, 3])     # len is LOAD_GLOBAL_BUILTIN after warm-up
    return s

def hot_with_local(n):
    _len = len                  # capture once as a local
    s = 0
    for _ in range(n):
        s += _len([1, 2, 3])    # _len is LOAD_FAST
    return s
```

Use `pyperf` (`pip install pyperf`) or `timeit.repeat` to benchmark each at `n=1_000_000`. Run each function once first to warm specialization. Confirm `dis.dis(..., adaptive=True)` shows `LOAD_GLOBAL_BUILTIN` in the first and `LOAD_FAST` in the second.

**Acceptance:**

- `bench_loads.py` plus a `results.md` reporting the wall-clock numbers and the per-iteration delta in nanoseconds.
- Answer: in the post-PEP-659 era, is the "rebind globals as locals" micro-optimization still worth doing in hot loops? Be specific about the magnitude.

---

## Problem 3 — Build a CALL-trace using `sys.monitoring` (60 min)

Extend Exercise 1's tracer to monitor `PY_START`, `PY_RETURN`, and `CALL` events (not `INSTRUCTION`). Print a tree-style call graph of one invocation of any non-trivial standalone function (your own or stdlib). Indent by call depth. Include the `co_qualname` of every Python function entered.

**Acceptance:**

- `call_tracer.py` that runs as-is.
- A sample trace of `json.dumps({"a": [1, 2, 3]})` (or similar) committed as `call-trace-sample.txt`.
- A short note in `notes.md`: what did the trace teach you about how `json.dumps` is structured internally?

---

## Problem 4 — Demonstrate the GIL switch interval (45 min)

Write a small program that spawns two threads, each running a CPU-bound loop. Vary `sys.setswitchinterval` across the values `0.0001`, `0.005` (default), `0.1`, and `1.0`. For each: measure the wall-clock time to completion and the **maximum** time a single thread runs uninterrupted (instrument with `time.monotonic_ns()` inside the loop).

**Acceptance:**

- `switchinterval-experiment.py`.
- `switchinterval-results.md` with a table of four runs.
- A paragraph: did the default 0.005 s value give the best total throughput? Why might the OS pick differently?

---

## Problem 5 — Read `Python/ceval_gil.c` and trace one acquire (60 min)

Open `Python/ceval_gil.c` (<https://github.com/python/cpython/blob/main/Python/ceval_gil.c>).

Find the function `take_gil` (lowercase, internal). Read it line by line. Then find the place it is called from in `Python/ceval.c` (`take_gil` is `static`, so it is only called from this translation unit).

**Acceptance:**

- `gil-acquire-reading.md` containing:
  - A 250-word explanation, **in your own words**, of how a thread waiting for the GIL parks, wakes up, and acquires.
  - Permalinks to the lines you read.
  - One question you still have. (The instructor reads these.)

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 400–500 words:

1. Before this week, what was your mental model of "what the GIL does"? How has it sharpened?
2. PEP 659 specialization happens transparently. Does that change how you would write performance-sensitive Python code, or does it not matter? Be specific.
3. If you were starting a new CPU-bound Python project today (2026), would you target the stock build or the free-threaded build? Defend the choice with two concrete tradeoffs.
4. Which lecture was the hardest to follow? What single concept would have helped if it had come earlier?
5. What is the next thing you would want to learn about the CPython VM after this week? Name a file in the source tree you would open.

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 — bytecodes.c reading | 60 min |
| 2 — LOAD_FAST vs LOAD_GLOBAL bench | 60 min |
| 3 — call tracer | 60 min |
| 4 — switch interval experiment | 45 min |
| 5 — ceval_gil.c reading | 60 min |
| 6 — reflection | 45 min |
| **Total** | **~5 h 30 m** |

After homework, ship the [mini-project](./mini-project/README.md).
