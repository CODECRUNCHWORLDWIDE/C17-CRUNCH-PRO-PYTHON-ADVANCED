# Mini-Project — `c-extension-bench`: Speed Up a Pythonic Kernel by 10x or More

> Pick a numerical kernel that runs in pure Python in several seconds. Implement it three times: pure Python (with type hints), one of {ctypes + C, cffi API mode, Cython}, and (where it makes sense) NumPy. Benchmark all three under `timeit` and produce a 600–900 word memo explaining the speedups in mechanism. The target is **at least 10x** speedup over pure Python from the chosen native path; in practice you will see 30–300x depending on the kernel and path. The artifact is the memo, the benchmark numbers, and a reproducible build.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-08-c-extension-bench-<yourhandle>` containing:

1. **`README.md`** — what the project is, how to reproduce, what you found. ~200 words. Links to your repo and to the kernel definition.
2. **`MEMO.md`** — **the load-bearing artifact**. 600–900 words. Sections below.
3. **`src/kernel_python.py`** — the pure-Python reference implementation. Type hints on every function. ~50–150 lines.
4. **`src/kernel_native.*`** — the native implementation. One of:
   - `kernel.c` + `kernel.py` (ctypes binding) — for the ctypes path.
   - `kernel.c` + `build_cffi.py` + `kernel.py` (cffi API mode) — for the cffi path.
   - `kernel.pyx` + `setup.py` + `kernel.py` (Cython) — for the Cython path.
5. **`src/kernel_numpy.py`** — a NumPy implementation, when one is straightforward.
6. **`bench/bench.py`** — the benchmark script. Runs all three (or four) implementations on identical inputs and reports timings.
7. **`bench/results.txt`** — the captured output of `bench.py` on your machine, with hardware specs at the top.
8. **`scripts/build.sh`** — one-line build: compile the C/.pyx, run any cffi build, leave you ready to `python bench/bench.py`. ~10 lines.
9. **`LICENSE`** — MIT, Apache-2.0, GPL, your choice.

The memo is what people read. Everything else is the audit trail.

## Picking the kernel

The kernel must:

- **Run in pure Python in 1–30 seconds** on your machine for the default input. Faster than 1 second is too noisy to benchmark cleanly. Longer than 30 makes iteration slow.
- **Be CPU-bound, no I/O.** Reading a file once at startup is fine; reading per-iteration is not.
- **Have a meaningful inner loop of arithmetic or branching.** Not a single NumPy call that takes 3 seconds; an actual algorithm.
- **Be the kind of thing a real codebase would have.** Not a synthetic benchmark.

### Suggested kernels (pick one)

- **1D convolution** (the default; the one Lecture 3 covered). Pure-Python ~10 seconds for N=1M, K=64. Cython gets you to ~50 ms.
- **Mandelbrot escape-time** on a fixed grid. Pure-Python ~30 seconds for 800x600. C/Cython gets you to ~150 ms.
- **2D Game of Life** for K=200 generations on a 500x500 grid. Pure-Python ~30 seconds. C/Cython gets you to ~50 ms.
- **Levenshtein edit distance** between two strings of length 1000 each. Pure-Python ~3 seconds. C/Cython gets you to ~3 ms.
- **Black-Scholes batch** option pricing for 10 million `(spot, strike, vol, rate, time)` tuples. Pure-Python ~20 seconds. C/Cython gets you to ~150 ms. NumPy gets you to ~100 ms.
- **Discrete cosine transform** (DCT-II) on a 1D signal of length 10,000. Pure-Python ~5 seconds. Cython gets you to ~50 ms.
- **K-means clustering** (one iteration) on 100,000 points in 10-D with K=20. Pure-Python ~5 seconds. C/Cython gets you to ~30 ms.
- **N-body gravitational simulation** (one timestep, naive O(N²)) for N=1,000 particles. Pure-Python ~3 seconds. C/Cython gets you to ~10 ms.

If none of these appeals, propose your own in the memo. The rubric is the same: 1–30 seconds in Python; a meaningful inner loop; not pure NumPy.

## Picking the path

You implement *one* of the three native paths. Pick based on the kernel:

- **ctypes** — best when you want to ship a pre-compiled `.so` and avoid a build pipeline on the install side. Pick this if your kernel is a straightforward C function with simple argument types. Pros: zero install dependencies beyond ctypes (stdlib). Cons: per-call overhead ~1 µs; manual `argtypes` discipline.
- **cffi API mode** — best when you have non-trivial C signatures, want compile-time verification of declarations, or are wrapping a security-sensitive library. Pick this if you want production-grade build hygiene. Pros: low per-call overhead; compile-time signature check. Cons: extra build step; `cffi` dependency.
- **Cython** — best when you are writing the kernel yourself in a Python-flavoured syntax, want NumPy interop via memoryviews, or want the speed of a real C extension without writing C. Pick this if your kernel has NumPy arrays as inputs/outputs or if the kernel is non-trivial enough that Python-syntax-with-types is more productive than raw C. Pros: greatest expressiveness; fast; NumPy-friendly. Cons: build pipeline; new-ish language to learn.

The memo explains *why* you picked the path. Justify it.

## The benchmark

`bench/bench.py` must:

- Use `time.perf_counter()` (not `time.time()`).
- Run each implementation **5 times**; take the **minimum** (not mean) wall time. The minimum is the least-perturbed sample.
- Use **the same input** for every implementation (a `numpy.random.default_rng(seed=42).random(...)` is the canonical seeded random input).
- Verify all implementations produce **the same answer** to within an appropriate tolerance (`np.allclose(a, b, atol=1e-6)` for floats; `np.array_equal` for ints).
- Print a table with: implementation name, wall time, speedup vs. pure Python, ops/second (if relevant).

A skeleton:

```python
"""bench.py - compare implementations of <kernel> on identical inputs."""
from __future__ import annotations
import time
from typing import Callable, Any
import numpy as np

from src.kernel_python import kernel_python
from src.kernel_native import kernel_native
try:
    from src.kernel_numpy import kernel_numpy
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def time_min(fn: Callable[..., Any], args: tuple, repeats: int = 5) -> float:
    """Time fn(*args) `repeats` times; return the minimum wall time in seconds."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        elapsed = time.perf_counter() - t0
        if elapsed < best:
            best = elapsed
    return best


def main() -> None:
    rng = np.random.default_rng(seed=42)
    # Build the seeded input here. Same input for every implementation.
    # ...

    # Run and time each.
    t_py = time_min(kernel_python, (...,), repeats=1)
    t_nat = time_min(kernel_native, (...,), repeats=5)
    if HAS_NUMPY:
        t_np = time_min(kernel_numpy, (...,), repeats=5)

    # Verify correctness.
    r_py = kernel_python(...)
    r_nat = kernel_native(...)
    assert np.allclose(r_py, r_nat, atol=1e-6), "implementations disagree"

    # Print the table.
    print(f"{'impl':>16}  {'time (ms)':>10}  {'speedup':>8}")
    print(f"{'pure Python':>16}  {t_py * 1000:10.1f}  {1.0:>8.1f}x")
    print(f"{'native':>16}  {t_nat * 1000:10.1f}  {t_py / t_nat:>8.1f}x")
    if HAS_NUMPY:
        print(f"{'numpy':>16}  {t_np * 1000:10.1f}  {t_py / t_np:>8.1f}x")


if __name__ == "__main__":
    main()
```

## The memo

`MEMO.md`. 600–900 words. Six sections.

### Section 1 — The kernel and the workload (~100 words)

Describe the kernel in two sentences. State the input size (N, K, dimensions, whatever) and *why* you picked that size (it should be large enough to dominate per-call overhead and small enough to fit in memory). State the unprofiled wall clock of the Python implementation.

### Section 2 — The path you chose, and why (~100 words)

ctypes, cffi API mode, or Cython. Justify the choice in three sentences against the alternatives. Cite Lecture 2 §7 or Lecture 3 §6 if relevant.

### Section 3 — Implementation notes (~150 words)

What did the native implementation look like? Highlight 2–3 decisions: the data layout (C-contiguous? row-major?); the loop structure (manual SIMD-friendly inner; `with nogil:`; bounds-checks off); the boundary handling (zero-pad, mirror, clip). Mention any pitfalls you hit and how you fixed them.

### Section 4 — The numbers (~100 words)

Paste the benchmark table. Speedup vs. pure Python; speedup vs. NumPy (if NumPy is competitive). State whether you hit the ≥10x target.

### Section 5 — Why the numbers are what they are (~150 words)

*The load-bearing section.* Explain the speedup in mechanism, not in adjectives. The pure-Python loop does N bytecodes; each bytecode is ~Y ns; total ~YN ns. The native loop is ~Z ns per iteration after vectorisation; total ~ZN ns. Speedup ~Y/Z. Cover at least two of: bytecode-vs-native cost; SIMD auto-vectorisation; cache-friendliness of access pattern; GIL release (if applicable).

If NumPy beat your native implementation, explain why — usually hand-tuned SIMD or an algorithmic shortcut you did not exploit (FFT-convolution; blocked matrix multiply).

### Section 6 — What you would do next (~150 words)

If you had another week, what would you push for? Pick one:

- **Push past the native ceiling.** Use SIMD intrinsics (`<immintrin.h>` on x86; `<arm_neon.h>` on ARM). Try Cython's `prange` for multi-core. Switch to PyO3 for the safety improvements at the FFI boundary.
- **Push for distribution.** Set up `cibuildwheel` to build wheels for Linux/macOS/Windows × Python 3.11–3.13. Publish to a private PyPI or to a tag in the repo.
- **Push for the algorithm.** Profile the native version with `perf`; find the next bottleneck; pick the algorithmic shortcut (FFT, blocked tiling, approximate methods).
- **Push for safety.** Run the native binding under `valgrind` and address-sanitizer. Find any memory bugs. Test on edge cases (zero-length inputs, NaN, denormals).

Close with one sentence about what surprised you most.

## Acceptance criteria

- [ ] Repo public on GitHub (or a private link shared with the reviewer).
- [ ] `scripts/build.sh` works on a clean machine: install Python 3.13, run the script, get a working build.
- [ ] All three (or four) implementations produce the same answer, verified by `assert np.allclose(...)` or equivalent in `bench/bench.py`.
- [ ] `bench/results.txt` exists, was generated by `bench/bench.py`, includes hardware specs at the top.
- [ ] The native implementation is **at least 10x faster** than the pure-Python implementation. (Most kernels will hit 30–300x; if you got <10x, the kernel was probably a poor fit — switch.)
- [ ] `MEMO.md` exists, is 600–900 words (target; 500–1000 acceptable), and has all six sections.
- [ ] Section 5 (the mechanism section) is substantive — not "C is faster than Python" — but cites bytecode vs. native, SIMD, GIL, or cache effects.
- [ ] All Python files have type hints. All C files conform to PEP 7 style.
- [ ] You ran `python3 -m py_compile` on every `.py` file and it passes.

## Suggested order of operations

### Thursday (~2 h)

1. Pick the kernel (15 min). Read the kernel definition; understand it.
2. Write `kernel_python.py` with type hints; verify it produces a sensible output (30 min).
3. Time it. Tune the input size so a single run takes 5–15 seconds (15 min).
4. Pick the path (ctypes / cffi / Cython). Set up `scripts/build.sh` stub (10 min).
5. Start the native implementation. Get the build working (compile errors resolved) (60 min).

### Friday (~3 h)

6. Finish the native implementation. Get it producing the right answer for the seeded input (60 min).
7. Add the NumPy implementation if one is straightforward (30 min).
8. Write `bench/bench.py`. Capture `bench/results.txt` (45 min).
9. Begin `MEMO.md` — Sections 1, 2, 3 (45 min).

### Saturday (~2 h)

10. Finish `MEMO.md` — Sections 4, 5, 6 (75 min).
11. Polish: ensure all type hints are in place; run `python3 -m py_compile` on every `.py`; run `cython -a` on any `.pyx` and verify the inner loop is white (30 min).
12. Write `README.md` with reproduction instructions; push (15 min).

## Common pitfalls

- **Kernel too short.** A 0.3-second Python kernel produces noisy benchmarks. Scale up the input until Python takes at least 1–5 seconds.
- **Kernel that NumPy already does well.** A 1D `sum` is not a good kernel; NumPy's `np.sum` is unbeatable, your Cython port will lose. Pick something with branching or short-circuit behaviour where NumPy is *not* the obvious answer.
- **Forgetting `argtypes`/`restype`** on a ctypes binding. The classic. Always set them.
- **Forgetting `language_level: 3`** on a Cython build. Cython 3.0+ defaults are sensible but newer projects sometimes pin older versions. Be explicit.
- **Benchmarking with `time.time()`.** Use `time.perf_counter()`. The former is wall clock subject to NTP; the latter is monotonic, high resolution.
- **Reporting the *mean* of timings.** Report the *minimum*. The mean is corrupted by occasional GC pauses or kernel preemptions; the minimum is the least-perturbed sample.
- **Forgetting to verify correctness.** "It runs and produces *a* number" is not enough. Verify the native answer agrees with the Python answer within tolerance.
- **Writing the memo without numbers.** Section 5 must reference *measured* numbers. "I got 80x because C is faster" is not a memo; "I got 80x because the pure-Python inner loop does 4 bytecodes at ~70 ns each (~280 ns/iter) and the SIMD-vectorised C inner loop does 4 FMAs per pair at ~1 ns each (~4 ns/iter), a ratio of ~70x consistent with the measurement" is.

## Why this matters

The mini-project is the **artifact** for Week 8. Every interview for a "senior" or "staff" Python role that touches performance asks some version of "talk me through a time you sped up a hot kernel." Most candidates wave their hands at "rewrote in C" or "used NumPy." The candidates who do well point at a 700-word memo with a benchmark table that demonstrates discipline, judgement, and ownership — they picked the right path, they measured before and after, they explain *why* the numbers are what they are.

The native path you pick will become part of your reflex. If you pick ctypes this week, ctypes will be the first thing you reach for next time you need a C binding. If you pick Cython, that. The point is not to be fluent in all three by Sunday; the point is to be fluent in one of them by Sunday, and to know on first principles when to reach for the others.

The mini-project does not require shipping a wheel, opening a PR upstream, or producing a paper. It requires *one* kernel sped up *one* way with *one* honest memo explaining the result. That is the unit of work.

## Reading

- All three Week 8 lectures, end-to-end. Treat them as reference.
- The cffi or Cython tutorial, depending on the path you chose: <https://cffi.readthedocs.io/> or <https://cython.readthedocs.io/>.
- The CPython C API tutorial (read if your path is ctypes or you want to see what cffi/Cython generate): <https://docs.python.org/3/extending/extending.html>.
- PEP 7 (if you are writing C): <https://peps.python.org/pep-0007/>.
- The NumPy "C-Types Foreign Function Interface" reference: <https://numpy.org/doc/stable/reference/routines.ctypeslib.html>.

Good benching.
