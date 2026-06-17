# Week 1 Homework

Six problems, ~6 hours total. Commit each in your Week 1 repo.

---

## Problem 1 — Map the CPython repo (45 min)

Produce a one-page Markdown file `notes/cpython-map.md` that summarizes, for each top-level directory in the CPython repo, what's in it and one specific file you found interesting.

**Acceptance.** A table with at least 8 rows (one per top-level directory of interest), each row including the directory, a one-sentence "what's in it," and one file path you actually looked at. Linked permalinks preferred.

---

## Problem 2 — Compare bytecode across Python versions (1 h)

Pick three Python versions you can install (a venv each, or via `pyenv`, or via Docker images): for instance `3.11`, `3.12`, `3.13`. Disassemble the same function on each:

```python
def f(xs):
    return sum(x * 2 for x in xs if x > 0)
```

**Acceptance.** A file `notes/dis-across-versions.md` contains:

- The three `dis.dis(f)` outputs labeled clearly.
- A short list of opcodes that differ (introduced, removed, renamed).
- A sentence or two of speculation on why each change happened (link the PEP if you can find it — PEP 659 and PEP 626 are likely candidates).

---

## Problem 3 — A function that prints its own bytecode (45 min)

Write `self_inspect.py` containing a function `inspect_me` that, when called, prints **its own bytecode** without using `dis` directly on the source file (it can use `dis` introspectively on `inspect_me.__code__`).

**Acceptance.** Running `python self_inspect.py` prints disassembly of `inspect_me`. The script is committed.

---

## Problem 4 — Read `Lib/dis.py` (45 min)

Open `Lib/dis.py` from your local Python install (`python -c "import dis; print(dis.__file__)"`). Read the first ~150 lines.

**Acceptance.** A file `notes/reading-dis.md` containing:

- A one-paragraph summary of how `dis.dis(...)` actually works — what data structures does it walk?
- One specific helper function you found in `dis.py` that you'd want to reuse in your own tooling (e.g., `findlinestarts`, `Bytecode`).
- A 1-sentence answer to: "Could I have written `dis.dis` myself, given enough time?"

---

## Problem 5 — `python -O` and `python -OO` (45 min)

Run each of:

```bash
python -c "import sys; print(sys.flags)"
python -O -c "import sys; print(sys.flags)"
python -OO -c "import sys; print(sys.flags)"
```

Then disassemble a small function under each:

```python
def f():
    assert 1 == 2, "this assertion will be removed under -O"
    return "doc" if __debug__ else "no-debug"
```

**Acceptance.** A file `notes/optimization-flags.md` containing:

- The `sys.flags` output for each invocation, side-by-side.
- The disassembly of `f` under each flag, showing how `-O` strips the assertion and the debug branch.
- A one-paragraph explanation of when (and why) you'd actually use `-O` in production — and when you wouldn't.

---

## Problem 6 — Reflection (30 min)

Write `notes/week-01-reflection.md` (300–400 words) answering:

1. What did you most expect to know about Python that turned out to be wrong?
2. Which lecture changed your mental model the most?
3. What did the diagnostic quiz get right or wrong about your readiness?
4. What's one piece of CPython internals you want to go deeper on after C17?

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 1 h |
| 3 | 45 min |
| 4 | 45 min |
| 5 | 45 min |
| 6 | 30 min |
| **Total** | **~4 h 30 min** |

When done, push your Week 1 repo and start the [mini-project](./07-mini-project/00-overview.md).
