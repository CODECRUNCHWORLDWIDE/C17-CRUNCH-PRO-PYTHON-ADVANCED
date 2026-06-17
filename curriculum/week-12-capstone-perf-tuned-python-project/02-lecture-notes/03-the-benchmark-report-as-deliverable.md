# Lecture 03 — The Benchmark Report as Deliverable

> *Half the capstone grade is the package. The other half is the benchmark report. Treat the report the way a researcher treats a paper, the way a hiring manager treats a portfolio entry, the way a future you treats a notebook you wrote two years ago and have to reread. The report is the artefact that survives after the package gets pruned from TestPyPI, after the laptop you ran it on gets traded in, after your TestPyPI password gets rotated. The report is what a reader uses to decide whether to take you seriously.*

## 1. Why the report is graded equally with the code

A working fast implementation that nobody can reproduce is a private accomplishment. A working fast implementation with a report that lets a reader reproduce it on their own machine, within twenty percent of your numbers, is a public contribution. The reader does not have to take your word for the speedup. They can run it themselves. That property — reproducibility — is the single most important property of an engineering writeup.

A second reason: hiring managers read reports more often than they read code. Code review takes hours. Reading a one-page report takes five minutes. If your report is clean, the manager opens the code. If your report is sloppy, the code never gets opened. Optimise the funnel.

## 2. The shape of the report

The report is a single markdown file, `mini-project/REPORT.md`, with this section structure. The template in `mini-project/REPORT.template.md` is the fill-in-the-blanks version; this lecture is the reasoning.

1. **Title and abstract** (200 words max).
2. **The kernel** (300 words max).
3. **Methodology** (400 words; this is the longest section).
4. **Results** (the numbers, the chart, the table).
5. **Discussion** (the honest part — what worked, what did not, what remains).
6. **Reproduction instructions** (the part that makes the report a report).
7. **References**.

Total target length: 1500–2500 words. Anything shorter is under-documented. Anything longer is over-claimed.

## 3. The abstract

One paragraph. The reader should be able to read just this paragraph and know:

- What kernel you implemented.
- What baseline you compared against.
- What the headline speedup is.
- Which technique was responsible for the bulk of the speedup.
- What the package URL is.

Example abstract for the worked gaussian-blur capstone:

> This report describes `cc-jdoe-blurperf` (version 0.1.0), a Python package providing 2D gaussian blur for `uint8` RGB images. Against a naive triple-nested Python loop on a 2000x2000x3 test image with sigma=2.0, the package achieves a measured `447x` speedup (median of 21 runs, 95% confidence interval `[438x, 455x]`) on an Apple M3 Pro running CPython 3.13.0 on macOS 14.4. The bulk of the speedup (98%) comes from the algorithmic improvement (gaussian separability) combined with NumPy/SciPy vectorisation (Tier 1 and Tier 2 of the C17 capstone tier ladder); a hand-written C extension was not pursued because Tier 2 met the project success criteria. The package is published at <https://test.pypi.org/project/cc-jdoe-blurperf/0.1.0/> and reproduction instructions are given in section 6.

That is the entire abstract. About 130 words. Read it. The abstract is the load-bearing paragraph of the entire report.

## 4. The kernel section

Describe what the package does. State the signature of the public API:

```python
def blur(image: np.ndarray, sigma: float) -> np.ndarray:
    """Apply a 2D gaussian blur to an RGB uint8 image.

    Parameters
    ----------
    image : np.ndarray
        Shape (H, W, 3), dtype uint8.
    sigma : float
        Gaussian standard deviation in pixels. Must be positive.

    Returns
    -------
    np.ndarray
        Same shape and dtype as input.
    """
```

State the correctness oracle:

> Correctness is verified against `scipy.ndimage.gaussian_filter(image, sigma=sigma, axes=(0, 1))` with tolerance `atol=1` (within one grey-level per channel). The test suite (`tests/test_correctness.py`) runs this check on 8 fixed test images at sigmas 0.5, 1.0, 2.0, 4.0.

State the scope and non-scope:

> In scope: RGB `uint8` images; scalar sigma; zero-padded boundary handling. Out of scope: anisotropic sigma; alternative dtypes; GPU acceleration; cross-platform wheels (only macOS arm64 wheel is published; sdist is available for other platforms).

## 5. The methodology section

This is the section the reader scrutinises most carefully. Every number in the results section traces back to a choice documented here.

The methodology must specify:

- **Hardware.** Full spec. Apple M3 Pro, 11 cores (5 P-cores + 6 E-cores), 36 GB unified memory, macOS 14.4. AC power, fan unrestricted, no other userland processes active, screen brightness minimum.
- **Python.** Version, build, ABI flags. `python -V` says `3.13.0`. `sysconfig.get_config_var("Py_GIL_DISABLED")` returns `0` (stock build). Compiled with `--enable-optimizations` (Apple's `python.org` installer).
- **Dependencies.** NumPy `2.1.0`, SciPy `1.14.0`, all installed in a fresh `python -m venv` immediately before the run. No conda, no system Python.
- **Workload.** A 2000x2000x3 `uint8` array seeded with `numpy.random.default_rng(seed=42)` into a uniform `[0, 255]` distribution. Sigma fixed at 2.0. The same array is reused across all variants — this matters because allocating a 12 MB array on every iteration would itself be measurable overhead.
- **Statistic.** Median of 21 measurement runs, after 3 warm-up runs that are discarded. 95% confidence interval from bootstrap resampling (10,000 resamples). Why median: a few runs will be slow because of background OS work; the median is robust to those outliers in a way the mean is not.
- **Timer.** `time.perf_counter()`, which is the monotonic high-resolution timer ([Python docs](https://docs.python.org/3/library/time.html#time.perf_counter)). Resolution on macOS is ~40 nanoseconds; on Linux ~1 nanosecond. Both are far below the workload's runtime.
- **Memory.** `psutil.Process().memory_info().rss` ([psutil docs](https://psutil.readthedocs.io/)), sampled before and after the call. RSS is resident set size — the amount of RAM the process actually has mapped. For a single run we report the peak across `tracemalloc.get_traced_memory()` since `tracemalloc` is more accurate for in-process measurement and RSS conflates the test harness with the kernel.
- **What is and is not measured.** Wall-clock from "input is allocated and ready" to "output is returned." Allocation of input is not counted. Allocation of output by the kernel *is* counted. The cost of the correctness check is not counted. The cost of `numpy.testing.assert_allclose` against the reference is not counted, but is run separately as a sanity check.
- **Variance sources.** OS scheduler jitter, hardware thermal state, memory-allocator behaviour on each run. The number of measurement runs (21) is chosen so the bootstrap confidence interval is narrow enough to support the reported `447x` claim (the lower bound of `438x` is still well above the `100x` success threshold).

If any of these choices was non-obvious, justify it. Example: "The reused-array convention means we are not measuring allocator cost. For a single-image, latency-sensitive use case, allocator cost would matter and we would measure differently. The intended use case for this package is batch processing of many images, where allocator cost is a one-time overhead." That sentence demonstrates to the reader that you understood the trade-off.

## 6. The results section

Numbers, table, chart. In that order.

### The headline number

> **`447x` speedup** over the naive baseline. Median 21 runs. 95% CI `[438x, 455x]`. Wall-clock: 90.1 seconds (naive) → 201 ms (Tier 2). Memory: 12 MB (naive) → 80 MB (Tier 2, due to `float32` intermediate buffer).

### The full table

| Variant                         | Median wall-clock (ms) | 95% CI (ms)      | Speedup vs naive | Peak memory (MB) |
|---------------------------------|------------------------:|------------------|-----------------:|------------------:|
| Tier 0: naive triple loop       |                90,123  | [89,400, 90,800] |             1.00 |                12 |
| Tier 1: separable Python loops  |                14,250  | [14,100, 14,400] |             6.32 |                12 |
| Tier 2: NumPy/SciPy vectorised  |                   201  | [198, 205]       |           448.4  |                80 |
| Tier 3: hand C extension        |               *not pursued — see section 5*                                          |
| Tier 4: thread-pool 4 images    |                   780  | [770, 790]       |     230 / image  |               320 |

The asterisk row is load-bearing — it documents the deliberate skip, with a cross-reference to the discussion section.

### The chart

A single matplotlib chart, saved as `mini-project/figures/speedup.png`, embedded in the report. Bar chart, log scale on the y-axis (because the baseline is ~440x slower than the optimised version, a linear scale buries the lower bars), labelled axes, error bars showing the 95% CI.

Add the chart-generation script to the package's `benchmarks/` directory so the chart is reproducible.

## 7. The discussion section

The discussion is the honest section. It is where you say what you tried that did not work, what you considered and chose not to do, and what is left unfinished.

> **What worked.** The separable form of the gaussian (Tier 1) and the use of `scipy.ndimage.convolve1d` for the per-axis pass (Tier 2) account for essentially all of the speedup. Of the two, the separable form is the algorithmically interesting move; the vectorisation is mechanical once the algorithm is in the right shape.
>
> **What did not work.** An initial Tier 2 attempt using `np.apply_along_axis` was about `3x` slower than the final `convolve1d` version, because `apply_along_axis` still iterates in Python over the axis. This was caught by `cProfile` showing one Python-level `for` loop accounting for 70% of wall-clock; the fix was to call `convolve1d` directly with the `axis` parameter. Time spent: about 90 minutes including the profiling rerun.
>
> **What was considered and not pursued.** A hand-written C extension (Tier 3) was estimated to provide an additional `2.5x` based on the per-call NumPy overhead measured at approximately 80 microseconds. For a 2000x2000 image with sigma=2.0 the per-image runtime is 201 ms, so the overhead is 0.04% — negligible. For a 100x100 image processed 1000 times in a row, the same overhead would be 80% — significant. The capstone's stated use case is large images; Tier 3 was not justified. A future version targeting small-image, low-latency workloads should reach for Tier 3.
>
> **What is left unfinished.** Cross-platform wheels (only macOS arm64 published). The published sdist will work on Linux and Windows but requires a NumPy install from source on those platforms; in practice users will install NumPy from a wheel and only build this package's pure-Python source, so this is not a real limitation. A `cibuildwheel` CI workflow would close this gap in about an hour of additional work; out of scope for the one-week deadline.
>
> **Surprises.** The Tier 1 → Tier 2 speedup of approximately `70x` was larger than expected; we had estimated `30x`. Inspection showed the reason: `convolve1d` releases the GIL and the macOS thread-runner kept the workload pinned to a P-core for the entire duration, which the Python loop could not do because the GIL-held bytecode interpreter was already P-core-bound. The thermal headroom available to the C kernel was therefore higher than to the Python kernel. We could not have predicted this without measuring.

That last paragraph — the surprises — is the one a senior engineer reading the report scrutinises. It is the paragraph that distinguishes "this candidate ran the benchmark" from "this candidate understood the benchmark."

## 8. Reproduction instructions

This is the part that turns the report into a report. The reader should be able to run something like:

```bash
git clone https://github.com/jdoe/cc-jdoe-blurperf
cd cc-jdoe-blurperf
python -m venv .venv && source .venv/bin/activate
pip install -e .[benchmarks]
python benchmarks/run_all.py --output results.json
python benchmarks/make_chart.py results.json --output figures/speedup.png
```

And produce output within 20% of your numbers.

If they cannot, your report has a gap. Find it. Common gaps:

- Pinned dependency versions are in `pyproject.toml` for the package itself but not for the benchmark dependencies; the user's NumPy is a different version and runs at a different speed.
- The benchmark hard-codes a path to `~/data/test-image.png`; the reader does not have that file. Fix: generate the test data from a seed.
- The benchmark uses `time.time()` instead of `time.perf_counter()` (the resolution of the former is OS-dependent and bad on Windows).
- The benchmark prints results but does not save them; reader has no way to compare.

Run the reproduction yourself, on a venv you have never used before. If you cannot, the reader cannot either.

## 9. References

The references section is short. Cite:

- The PEPs you relied on (PEP 7, PEP 8, PEP 440, PEP 484, PEP 517, PEP 518, PEP 561, PEP 621, plus any others your capstone uses).
- The Python docs pages for any non-obvious stdlib calls.
- Any external papers or blog posts you read. The Gaussian-separability fact is older than CS; a textbook citation is fine.
- The W1–W12 lecture notes of this track.

A reference does not need a URL if it has a citable name. A reference *does* need a URL if it is a docs page or a non-canonical source.

## 10. Common report failure modes

- **Magical numbers.** "We achieved 1500x speedup." Speedup over what? On what hardware? Measured how many times? Reported as mean or median? With what variance? A capstone report that just says "1500x" with no methodology is unscoreable.
- **No methodology section.** The report jumps from "naive baseline" to "results" without explaining how. The reader cannot reproduce.
- **No discussion of what did not work.** This is suspicious — every real perf project has dead ends. Saying so demonstrates honesty and judgement.
- **Linear chart axis.** A 400x speedup chart with linear axes hides the smaller speedups in the noise. Log scale.
- **Mean instead of median.** Means are dragged by outliers. The "outlier" might be a thermal throttle, a background indexer, or a network timeout in a dependency. Use median.
- **No confidence interval.** A single number is unfalsifiable. A range is.
- **Reproduction instructions assume the developer's environment.** "Just run `python benchmark.py`" — but the reader does not have `numpy==2.1.0` pinned. Spell out the venv setup.
- **No hardware spec.** "It is fast on my machine" is not a result.

## 11. The "future work" trap

A report's discussion section can end with a "future work" paragraph. Be sparing here. The capstone is a one-week project; "future work" should mean "things a follow-up project would explore," not "things I would have done if I had time." The reader has seen a hundred reports end with "with more time we would have explored GPU acceleration"; they will discount the section. Make every sentence count.

A good future-work paragraph proposes specific, measurable next steps. Example: "A follow-up exploring Cython for the convolution kernel (estimated effort: 4 hours; estimated additional speedup: 2-3x for sigma>4 where the kernel becomes large enough that NumPy's per-call overhead is amortised) would close the gap to SciPy's `gaussian_filter` for that regime." That is specific. The reader could decide whether to pursue it. They could not decide anything from "more optimisation is possible."

## 12. Style notes

- **No exclamation marks.** The report is not a sales pitch.
- **No first-person plural to inflate.** "We discovered" is fine; "We are pleased to announce" is not.
- **Numbers in tables, not prose.** A table of speedups is easier to scan than a paragraph of them.
- **Cite, do not summarise.** A link to PEP 440 is better than a paragraph paraphrasing PEP 440.
- **Past tense for what you did. Present tense for the result.** "We measured 21 runs, the median is 201 ms."

## 13. The Saturday deliverable

By the end of Saturday:

- The package is published on TestPyPI.
- `mini-project/REPORT.md` is filled in from the template.
- `mini-project/figures/speedup.png` exists.
- `mini-project/SUBMISSION.md` contains the TestPyPI URL.
- A peer has successfully run your reproduction instructions on their machine and landed within 20% of your numbers. (If you cannot find a peer in time, run them yourself on a different machine, or on a fresh `Docker` container.)

Sunday is for the final exam and reflection.

## 14. References

- The W7 lecture notes on profiling methodology — the precursor to this lecture.
- Gregg, Brendan. *Systems Performance: Enterprise and the Cloud*, 2nd ed. (Addison-Wesley, 2020). The canonical reference for production-grade benchmarking methodology. The Python-specific chapters are sparse but the methodology chapters are universal.
- [How to write a research paper](https://cs.stanford.edu/people/widom/paper-writing.html) — Jennifer Widom, Stanford. Free; about 15 minutes. The principles transfer to a benchmark report.
- [Reproducible Builds](https://reproducible-builds.org/) project; the philosophical home of "your build should produce the same artefact on my machine as on yours." The capstone is a much weaker reproducibility claim (numbers within 20%) but the discipline is the same.
