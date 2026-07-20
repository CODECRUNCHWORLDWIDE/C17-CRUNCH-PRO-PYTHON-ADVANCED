# Week 7 — Exercise Solutions

> Read after you have attempted each exercise. The expected numbers are from a 2024 MacBook Pro M2 (CPython 3.13.1); your hardware will produce different absolute numbers but the *ratios* should match.

## Exercise 1 — cProfile a slow function

### Expected output

`Naive (unprofiled): ~0.65 s`. `Optimised (unprofiled): ~0.28 s`. Speedup ~2.3x.

### The cumulative-sorted table (naive)

The top rows by `cumulative`:

```
   ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
        1    0.000    0.000    0.652    0.652  exercise-01-cprofile-a-slow-function.py:127(main)
        1    0.024    0.024    0.652    0.652  exercise-01-cprofile-a-slow-function.py:103(process_records)
    20000    0.062    0.000    0.612    0.000  exercise-01-cprofile-a-slow-function.py:81(transform_record)
    80000    0.084    0.000    0.529    0.000  exercise-01-cprofile-a-slow-function.py:63(normalise_field)
```

A naive read picks `transform_record` (its cumtime is 0.612, eight times the test record count). **Wrong call.** Its `tottime` is 0.062. Most of the 0.612 cumtime is inside its descendants.

### The tottime-sorted table (naive)

```
   ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
    80000    0.241    0.000    0.241    0.000  {method 'compile' of 're' objects}    # NOTE: re.compile is the cost
    80000    0.084    0.000    0.529    0.000  exercise-01-cprofile-a-slow-function.py:63(normalise_field)
    80000    0.062    0.000    0.085    0.000  {method 'sub' of 're.Pattern' objects}
    20000    0.062    0.000    0.612    0.000  exercise-01-cprofile-a-slow-function.py:81(transform_record)
    80000    0.041    0.000    0.041    0.000  {method 'strip' of 'str' objects}
    80000    0.038    0.000    0.038    0.000  {method 'lower' of 'str' objects}
```

`{method 'compile' of 're' objects}` (or, depending on Python version, `_compile` from `re`) is the actual hot leaf. It is called 80,000 times — once per `normalise_field` invocation — and recompiles `r"\s+"` every time. Module-level compile fixes it.

### The fix (optimised)

```python
_WHITESPACE_RE = re.compile(r"\s+")

def normalise_field_fast(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip().lower())
```

The optimised `tottime` table no longer shows `re.compile` at the top. The new hot leaf is the `str.lower`/`str.strip` chain plus `re.Pattern.sub`, all C built-ins. Further optimisation requires a different shape (e.g. drop the `.lower()` if input is known to be lowercase, batch normalisation across records into a vectorised pass).

### What the learner should learn

- **`tottime` sort first, always.** The cumulative sort fingers the orchestrator.
- A function with high `tottime` and low `cumtime` is a self-contained hot leaf (a candidate for rewriting or replacement).
- A function with low `tottime` and high `cumtime` is an orchestrator that delegates to expensive callees.
- Built-ins (`{method ... of ... objects}`) in the `tottime` top are an instruction: replace the *library*, not the *code*.

## Exercise 2 — line_profiler

### Expected output (unprofiled timings)

```
naive   pi=3.14164    wall=~0.42s
fast    pi=3.14164    wall=~0.28s
fastest pi=3.14164    wall=~0.24s
```

Speedups: naive → fast ~1.5x, fast → fastest ~1.17x, naive → fastest ~1.75x.

### Expected line_profiler output (under kernprof)

```
Timer unit: 1e-06 s

Total time: 0.418 s
File: exercise-02-line-profile-a-loop.py
Function: estimate_pi_naive at line N

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     N                                           @profile
     N                                           def estimate_pi_naive(n_samples, seed=42):
     N         1          5.0      5.0      0.0      rng = random.Random(seed)
     N         1          0.0      0.0      0.0      inside = 0
     N         1          1.0      1.0      0.0      history = []
     N   1000001      63234.0      0.1     15.1      for i in range(n_samples):
     N   1000000     104120.0      0.1     24.9          x = rng.random() * 2.0 - 1.0
     N   1000000      99412.0      0.1     23.8          y = rng.random() * 2.0 - 1.0
     N   1000000      52301.0      0.1     12.5          d2 = x * x + y * y
     N   1000000      36789.0      0.0      8.8          if d2 <= 1.0:
     N    785398      14210.0      0.0      3.4              inside += 1
     N   1000000      48234.0      0.0     11.5          history.append(4.0 * inside / max(1, i + 1))
     N         1          1.0      1.0      0.0      return 4.0 * inside / n_samples, history
```

### The hot line

`history.append(...)` at 11.5%. The learner usually expects the random-number generation lines (15.1%, 24.9%, 23.8%, totalling 63%) to dominate; they do, but the *unexpected* finding is that an innocuous-looking `list.append` of a floating-point computation costs ~10% of the total. The `max(1, i + 1) / 4.0 * inside` arithmetic per iteration is the silent cost.

### The fix

Remove the history maintenance entirely (`estimate_pi_fast`). The line is gone; the loop body shrinks by one line; the wall clock drops ~30%.

### Further: local binding

`estimate_pi_fastest` binds `rng_random = rng.random` outside the loop. Each `rng_random()` call inside the loop saves one attribute lookup. Recovers an additional ~10% on top of the no-history version. The line_profiler output shows the random-number lines drop from 24.9% / 23.8% to ~21% / 21%.

### What the learner should learn

- **`line_profiler` after `cProfile`.** Use it when you already know the hot function.
- **Per-line attribution surfaces silent costs.** `list.append` is fast in isolation; *frequent* `list.append` shows in the profile.
- **The kernprof-or-not shim is the right pattern** for scripts you want to run both ways.
- **Local-binding bound methods** (`rng_random = rng.random`) is a 5–15% win for tight loops. Idiomatic in CPython performance work.

## Exercise 3 — py-spy on a running process

### Expected flamegraph

A flamegraph dominated by one wide tower:

```
main
  └── loop_once
        └── slow_regex
              └── re.Pattern.findall
                    └── (catastrophic backtracking; the bottom of the regex engine)
```

`slow_regex` + `findall` together are ~90–95% of samples. `hash_round` is a thin tower; `generate_payload` is barely visible.

### Expected py-spy dump

```
Process N: python target.py
Python v3.13.x

Thread 0x... (active)
  File "target.py", line N, in slow_regex
    return len(pattern.findall(text))
  File "target.py", line N, in loop_once
    matches = slow_regex(payload)
  File "target.py", line N, in main
    result = loop_once(rng)
  File "target.py", line N, in <module>
    main()
```

### Expected diagnosis

A correct 150–250 word writeup names:

1. **Hot leaf:** `slow_regex` / `re.Pattern.findall`.
2. **Hot path:** `main` → `loop_once` → `slow_regex` → `findall`.
3. **Why slow:** catastrophic backtracking on `(a+)+b` against `aaaaaaa...b`. The pattern's nested quantifier creates O(2^N) backtracking paths. A correct diagnosis names "catastrophic backtracking" or "regex DoS" or "ReDoS."
4. **Fix:** rewrite as `a+b` (equivalent, linear), or use `regex` library with `(?>a+)+b` possessive quantifier, or use `re2` (Google's linear-time regex engine; ships as `pyre2` / `google-re2`).

### What the learner should learn

- **py-spy attaches in seconds without modifying the target.** This is the production skill.
- **A flamegraph compresses 3000 samples into one image.** The hot leaf is the widest plateau.
- **Catastrophic backtracking is a common Python performance bug**, and it is invisible to code review but obvious to a sampler.
- **The fix can be at the leaf** (rewrite the pattern) **or in library choice** (different engine), depending on constraints.
- `ptrace_scope=1` on Linux means `sudo`; this is normal, not a bug.

## Notes on running these exercises

- **All three are reproducible on CPython 3.11+.** PEP 657 (3.11) is the line/column position improvement; profilers in 3.11+ benefit from it for filename:lineno display.
- **Absolute timings vary by machine.** Compare *ratios*, not absolute seconds. On a slow VM, exercise 1 may take 2 s naive / 0.8 s optimised; the 2.5x ratio is the test.
- **The `python3 -m py_compile` smoke test** that you should run on each `.py` file in this directory is the minimum bar. Verified: each `.py` compiles clean.
- **If a learner gets stuck**, the most likely cause is environment-specific: missing `line_profiler`, `kernprof` not on PATH, `ptrace_scope=2` on Linux. The Resources file lists the install commands and the security model.

## Self-check questions

After all three exercises, you should be able to answer without re-reading:

1. Why does sorting by `cumulative` in cProfile mislead you toward orchestrators?
2. When does `tottime` differ substantially from `cumtime` for the same function?
3. What is the kernprof-or-not pattern, and why does line_profiler require it?
4. Why can py-spy attach to a process that did not start under a profiler, but cProfile cannot?
5. What flag makes `time.sleep` time visible in a py-spy flamegraph?
6. How would you tell, from a flamegraph alone, that a workload is *diffuse* (spread across many short calls) rather than concentrated in one hot leaf?

If you cannot answer any of these, re-read the corresponding lecture section before the quiz.
