# Challenge 2 — Memory-Bound vs. CPU-Bound: Use `scalene` to Tell Them Apart

> Two workloads. One is CPU-bound (slow because of arithmetic). The other is memory-bound (slow because of allocation pressure and copying). They have similar wall-clock times. **`cProfile` cannot tell them apart. `scalene` can.** Time budget: 90 minutes.

## The setup

Save these two workloads as `cpu_bound.py` and `memory_bound.py`.

### `cpu_bound.py`

```python
"""
Workload A: CPU-bound. A tight pure-Python arithmetic loop.
Wall-clock: ~5 seconds on a 2024 laptop. Almost all of it on the CPU.
Almost no allocation.
"""
from __future__ import annotations

def compute(n: int) -> float:
    """Sum of f(i) for i in [0, n), where f is moderately expensive arithmetic."""
    total = 0.0
    for i in range(n):
        x = i * 1.0 + 0.1
        # A handful of arithmetic operations per iteration. Pure Python.
        total += (x * x - x) / (x + 1.0)
    return total

def main() -> None:
    result = compute(5_000_000)
    print(f"compute -> {result:.6f}")

if __name__ == "__main__":
    main()
```

### `memory_bound.py`

```python
"""
Workload B: memory-bound. A loop that builds and rebuilds large lists.
Wall-clock: ~5 seconds (intentionally chosen to match Workload A).
Almost all of it spent in allocator and GC; very little in arithmetic.
"""
from __future__ import annotations

def grow_and_throw_away(n: int) -> int:
    """Build a list of size n, copy it, slice it, drop it, repeat."""
    total = 0
    for _ in range(50):
        xs = list(range(n))             # allocate n ints
        ys = xs[::2]                    # copy half - allocates again
        zs = [y * 2 for y in ys]        # list comprehension - third allocation
        total += sum(zs)                # the only "real work"
        del xs, ys, zs                  # explicit drop - the allocator churns
    return total

def main() -> None:
    result = grow_and_throw_away(200_000)
    print(f"grow_and_throw_away -> {result}")

if __name__ == "__main__":
    main()
```

(Adjust `5_000_000` and `200_000` so each script runs in 3–6 seconds on your machine.)

## The exercise

1. **Confirm wall-clock similarity.** Run each with `time`:

   ```bash
   time python cpu_bound.py
   time python memory_bound.py
   ```

   Tune the inner numbers (`5_000_000`, `200_000`, `50`) until both report similar `real` times (~3–6 s each). Record the times.

2. **cProfile cannot distinguish them by symptom.** Profile both:

   ```bash
   python -m cProfile -s tottime cpu_bound.py
   python -m cProfile -s tottime memory_bound.py
   ```

   For `cpu_bound.py`, the hot function is `compute`; `tottime` ≈ the run time. For `memory_bound.py`, the hot function is `grow_and_throw_away`; `tottime` ≈ similar fraction of the run time. **Neither cProfile output mentions allocation, copying, or GC.** From the cProfile tables alone, both workloads look like "a Python loop is slow."

3. **scalene tells them apart.** Profile both:

   ```bash
   scalene --cli cpu_bound.py
   scalene --cli memory_bound.py
   ```

   For `cpu_bound.py`: scalene reports ~90% **Python time** at the lines inside `compute`. The "Mem %" column shows ~0% — the loop allocates one float per iteration (which is small and the GC reclaims it).

   For `memory_bound.py`: scalene reports a more distributed picture. The "Mem %" column lights up at the `xs = list(range(n))`, `ys = xs[::2]`, and `zs = [y*2 for y in ys]` lines — together accounting for 60–80% of allocations. The "System time" column may show non-zero from the allocator/GC. The "Python time" is moderate, not dominant.

4. **The diagnosis writeup.** Write `diagnosis.md`:

   - Confirm the wall-clock numbers (one line each, with `time` output).
   - One paragraph for the CPU-bound case: where does scalene attribute the time, and how does that explain the wall clock?
   - One paragraph for the memory-bound case: same questions.
   - One sentence per workload: what would the right fix look like, in principle? (You do not need to implement.)

5. **The validation.** Implement *one* of the fixes and re-measure. Add the speedup to `diagnosis.md`.

   - For the CPU-bound case: `numpy` vectorisation (`np.arange(n).astype(float) * 1.0 + 0.1` and so on) typically 50–100x. Or `numba.njit` if available. Or sit with the Python loop and demonstrate that without changing language, there is no large win — that is also a valid answer.
   - For the memory-bound case: avoid materialising the intermediate lists; use generators. Replace `xs = list(range(n)); ys = xs[::2]; zs = [y*2 for y in ys]` with `zs = (i*2 for i in range(0, n, 2))` and consume directly via `total += sum(zs)`. Typical speedup: 3–5x with much less memory.

## Deliverable

A folder `challenge-02/` with:

| File | What's inside |
|------|---------------|
| `cpu_bound.py` | The CPU-bound workload (as given, with your tuned `n`). |
| `memory_bound.py` | The memory-bound workload (as given, with your tuned `n`). |
| `cpu_fixed.py` or `memory_fixed.py` | Whichever you optimised (one of them is enough). |
| `cprofile_outputs.txt` | The `cProfile -s tottime` outputs of both originals, captured. |
| `scalene_cpu.txt` | The `scalene --cli` output of `cpu_bound.py`. |
| `scalene_memory.txt` | The `scalene --cli` output of `memory_bound.py`. |
| `diagnosis.md` | The writeup. ~300 words. |

`diagnosis.md` template:

```markdown
# Memory-bound vs. CPU-bound diagnosis

## Wall clocks
- cpu_bound.py: $X.X s
- memory_bound.py: $Y.Y s

## What cProfile saw
Both scripts: one function dominates `tottime`. The hot function is named, the
hot path is named. cProfile gives no indication of what *kind* of slow it is.

## What scalene saw
### cpu_bound.py
scalene attributes $Z% of wall time to the Python column at the line
$LINE_REFERENCE. Memory allocations: $W%. The workload is CPU-bound: the
interpreter is executing bytecode the entire run.

### memory_bound.py
scalene attributes $A% to Python and shows allocations of $BMB at lines
$LINE_REFERENCES. The workload is memory-bound: most of the wall clock is
the allocator and GC moving objects, not the arithmetic.

## What a fix would look like
- cpu_bound.py: $ONE_SENTENCE (typically: push work to C via numpy or numba).
- memory_bound.py: $ONE_SENTENCE (typically: avoid intermediate materialisation,
  use generators, reuse buffers).

## Measured fix
I implemented the fix for $WHICH_ONE. Before: $T_BEFORE s. After: $T_AFTER s.
Speedup: $RATIOx. The improvement is consistent with the scalene attribution:
the column scalene flagged is the one that shrank in the optimised version.
```

## Acceptance criteria

- [ ] Both workloads run in similar wall-clock time (within 50% of each other).
- [ ] cProfile outputs are saved; both show "one function dominates `tottime`" with no indication of CPU vs. memory.
- [ ] scalene outputs are saved; the CPU-bound one shows mostly Python time, the memory-bound one shows substantial allocations.
- [ ] One workload has been optimised (your choice); the speedup is measured and consistent with the scalene attribution.
- [ ] `diagnosis.md` is ~300 words and addresses all four sections.

## Why this challenge matters

The trap this challenge teaches: **a slow Python program looks the same under cProfile whether it is CPU-bound, memory-bound, or syscall-bound**. The deterministic profiler only times function calls; it does not know what *kind* of work the function did. For most Python work, the answer is "CPU" and cProfile is sufficient. But for ~20% of slow programs the answer is "memory" or "syscalls" or "GC pressure," and applying CPU-style optimisations (faster algorithms, tighter loops) makes no difference because the bottleneck is not the CPU.

scalene's three-column decomposition (Berger et al., PLDI 2023) is the right tool to distinguish them. Once you have *seen* the difference between a "90% Python" profile and a "50% Python, large alloc column" profile, you cannot un-see it. The fix becomes obvious from the column shape.

## Optional extension

Add a *third* workload: **syscall-bound**. A loop that opens, reads, and closes a small file 10,000 times. Same wall clock (5 s). cProfile shows `os.open` and `os.read` at the top, but you might dismiss them as "fast built-ins." scalene's "System time" column should light up. The fix is to open the file once and read in a loop — but the diagnosis comes from the column shape.

## Reading

- Lecture 3 §§8–11 (scalene in depth).
- Berger et al., PLDI 2023 (~25 minutes): <https://dl.acm.org/doi/10.1145/3591260>.
- scalene README "Output" section: <https://github.com/plasma-umass/scalene#output>.

---

This challenge is shorter than Challenge 1 because the discipline is narrower: see the columns; reason from the columns; pick the right fix. The reward is a profiling instinct you cannot get from cProfile alone.
