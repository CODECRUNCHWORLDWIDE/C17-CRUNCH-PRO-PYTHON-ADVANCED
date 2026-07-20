# Challenge 1 — Profile, Identify, Rewrite to 10x

> **Take a small, intentionally slow function. Profile it. Identify the hot path. Rewrite for ~10x speedup. Re-profile to prove the win.** Time budget: 2 hours. The artifact is one folder with a before/after pair, two profile dumps, and a 200-word memo.

## Time budget

| Phase | Time |
|------:|----:|
| 1. Read the target function | 10 min |
| 2. Time the baseline | 10 min |
| 3. Profile with `cProfile`, sort `tottime` | 15 min |
| 4. Profile with `line_profiler`, find hot line | 15 min |
| 5. Hypothesise fix | 10 min |
| 6. Implement rewrite | 30 min |
| 7. Re-time, re-profile, write memo | 30 min |
| **Total** | **2 h** |

If you blow past 2 hours, *stop*, ship what you have, and write the memo describing what you got to and what is next. A 3x win that ships beats a hypothetical 10x.

## 1. The target

Pick **one** of these. They are all intentionally slow. None of them is a trick: each has a well-defined faster shape that ~10x is achievable from a single rewrite.

### Option A — Word frequency counter (string-heavy)

```python
def word_frequencies(text: str) -> dict[str, int]:
    """
    Count word frequencies in `text`. Slow on purpose.
    Test corpus: ~1 MB of plain text (try a Project Gutenberg book).
    """
    counts: dict[str, int] = {}
    words = text.split()
    for w in words:
        word = ""
        for ch in w:
            if ch.isalpha():
                word += ch.lower()
        if word:
            if word in counts:
                counts[word] = counts[word] + 1
            else:
                counts[word] = 1
    return counts
```

Test corpus: download any Project Gutenberg text (`https://www.gutenberg.org/`). Recommended: *Pride and Prejudice* (~700 KB) or *Moby Dick* (~1.2 MB). Both are free, plain-text, in English.

Why it is slow: per-char string concatenation (`word += ch.lower()`); per-call `str.isalpha`/`str.lower`; dict lookup followed by dict update (double lookup); no use of `collections.Counter`.

10x candidates: regex tokenisation + `Counter`; pre-`.lower()` the whole string then `str.split` on a regex.

### Option B — Fibonacci-of-a-list (algorithmic)

```python
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

def fibs_in_range(start: int, end: int) -> list[int]:
    """Return [fib(start), fib(start+1), ..., fib(end-1)]."""
    return [fib(i) for i in range(start, end)]
```

Test workload: `fibs_in_range(0, 30)`. (Beyond 30 the naive `fib` takes longer than the homework.)

Why it is slow: exponential recursion; no memoisation; per-element re-recomputation.

10x candidates: `functools.lru_cache`; iterative version; closed-form (Binet's formula) — pick one. The `@lru_cache` change is one line; ~1000x for `fibs_in_range(0, 30)`.

### Option C — Sliding-window maximum (algorithmic, O(nk) → O(n))

```python
def sliding_window_max(values: list[int], k: int) -> list[int]:
    """
    For each window of size k in `values`, return the maximum.
    Naive: O(n * k).
    """
    out: list[int] = []
    for i in range(len(values) - k + 1):
        out.append(max(values[i : i + k]))
    return out
```

Test workload: `values = [random.randint(0, 1_000_000) for _ in range(100_000)]; k = 1000`.

Why it is slow: O(n*k) work; each `max(values[i:i+k])` re-scans `k` elements.

10x candidates: monotonic deque (`collections.deque`) for O(n); `numpy` strided view + `np.max` (if numpy allowed) for ~50x in C.

### Option D — Find your own

Have a piece of code you've been meaning to make faster? **Use it.** The constraint: the workload must take at least 1 second to run, must be reproducible (deterministic seed if random input), and must have an obvious-in-hindsight ~10x rewrite. Document your choice in the memo's first paragraph.

## 2. The deliverable

A folder `challenge-01/` with:

| File | What's inside |
|------|---------------|
| `slow.py` | The original (your chosen target unchanged). |
| `fast.py` | Your rewrite. Same name signature; same output on the same inputs. |
| `bench.py` | The driver. Times both, prints the speedup, asserts outputs match. |
| `slow.pstats` | The `cProfile` dump of `slow.py` on the test workload. |
| `fast.pstats` | The same for `fast.py`. |
| `slow.lprof` | The `line_profiler` output of the slow function. |
| `MEMO.md` | 200 words: hot leaf, hot path, hypothesis, fix, measured speedup. |

`bench.py` template:

```python
import time
from slow import target as slow_target
from fast import target as fast_target

def time_once(fn, inputs) -> float:
    t0 = time.perf_counter()
    fn(inputs)
    return time.perf_counter() - t0

if __name__ == "__main__":
    inputs = ...  # your test workload
    expected = slow_target(inputs)
    actual = fast_target(inputs)
    assert expected == actual, "outputs differ - the fast version is wrong"
    t_slow = min(time_once(slow_target, inputs) for _ in range(3))
    t_fast = min(time_once(fast_target, inputs) for _ in range(3))
    print(f"slow: {t_slow:.4f}s")
    print(f"fast: {t_fast:.4f}s")
    print(f"speedup: {t_slow / t_fast:.2f}x")
```

`MEMO.md` template (you may copy the headings):

```markdown
# Memo: $TARGET, profiled and rewritten

## Workload
$ONE_SENTENCE — the workload and its size.

## Hot leaf (before)
$FROM_CPROFILE — the function with the largest tottime.

## Hot path (before)
$FROM_CPROFILE — the chain `main -> ... -> hot_leaf`.

## Hypothesis
$ONE_PARAGRAPH — why is the hot leaf hot? What is the underlying cost?

## Fix
$ONE_PARAGRAPH — what did you change?

## Measurement
$ONE_LINE — wall-clock before, wall-clock after, speedup ratio.

## Reflection
$ONE_LINE — what would you do next if you needed another 10x?
```

## 3. Acceptance criteria

- [ ] `slow.py` and `fast.py` produce identical outputs on the same input (assert in `bench.py` passes).
- [ ] `bench.py` reports a speedup of **at least 5x**. (10x is the target; 5x is the bar.)
- [ ] `slow.pstats` and `fast.pstats` exist and were generated by `cProfile.dump_stats(...)`. They are readable with `python -m pstats slow.pstats`.
- [ ] `slow.lprof` exists. Generated by `kernprof -l slow.py` (the target function decorated with `@profile` and the kernprof-or-not shim in place).
- [ ] `MEMO.md` exists, is ~200 words (150 minimum, 300 maximum), and contains all six sections from the template.
- [ ] You did **not** simply switch to `numpy` for a workload that does not warrant it. (Option C with numpy is fine; option A with numpy is not — it should remain a Python-and-Counter rewrite.)

## 4. Scoring rubric (if you want one)

| Criterion | Weight |
|-----------|-------:|
| The output of `fast.py` is identical to `slow.py` on the test input | 25% |
| The measured speedup is at least 5x | 20% |
| The cProfile + line_profiler artifacts demonstrate the discipline | 20% |
| The MEMO correctly names the hot leaf and the hot path | 20% |
| The MEMO's hypothesis and fix are coherent and connect to the profile | 10% |
| The reflection paragraph proposes a *plausible* next-10x step | 5% |

## 5. Common traps

- **Optimising before profiling.** Don't. Run the slow code once unprofiled, twice profiled (cProfile + line_profiler), *then* hypothesise. Optimising by intuition wastes the budget.
- **Switching libraries to claim a speedup.** Substituting `numpy.add` for `sum(...)` is *real* but it is not the discipline this challenge is teaching. Stay within stdlib unless the workload is genuinely numerical.
- **A 10x speedup that breaks correctness.** The `assert expected == actual` in `bench.py` is non-negotiable. A wrong-but-fast result is not faster; it is wrong.
- **Re-profiling and finding a new hot leaf, then "fixing" that too.** Scope creep. The challenge is *one* rewrite that produces ~10x. Document the *next* candidate in your reflection paragraph; don't fix it.
- **Profiling in 50ms of work.** Profilers are noisy at sub-second scales. Pick a workload that runs at least 1 second unprofiled, ideally 3–5 seconds.

## 6. Worth knowing

The 10x bar exists because it is the threshold at which a rewrite is *worth* the risk. Below ~3x, the cost (review, regression risk, future maintenance) usually outpaces the win. At 10x or more, the rewrite carries itself: end users feel the change, and the engineering organisation forgives the new code's surface area.

Profiling is what tells you whether a rewrite is in the 10x neighbourhood *before* you write it. The discipline scales: a senior performance engineer at a large shop does this same loop in 90 seconds, on production code, before opening a PR. The 2-hour budget here is for the muscle build.

## 7. Reading

- Lecture 1 §§7, 8, 9, 11. The "hot leaf, hot path, predicted fix" loop.
- Lecture 2 §§3, 5, 7, 11. Sorting by `tottime`; the cumulative trap; the workflow.
- Optional: Knuth, *Structured Programming with go to Statements* (1974). The original "premature optimisation" paragraph. ~30 minutes if you read the whole article; ~5 minutes for the relevant section.

---

When you finish, commit the `challenge-01/` folder. The mini-project (Thursday onward) is the same loop on a real OSS project, at higher fidelity, with a flamegraph and a public report. This is the rehearsal.
