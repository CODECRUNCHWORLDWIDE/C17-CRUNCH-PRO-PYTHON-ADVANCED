# Challenge 02 — Reproducibility Audit

## The premise

A benchmark report is only as good as a stranger's ability to reproduce it. This challenge tests the reproducibility of your capstone before the grader does, by handing it to a peer and watching them try.

## The task

1. **Pick a peer.** Another learner in the course is ideal. If you cannot find a peer, run the audit yourself on a clean Docker container or a borrowed machine.
2. **Hand them only your README and your REPORT.md.** Do not hand them the code; they will `pip install` it from TestPyPI like any other user.
3. **Give them 60 minutes.** Watch silently. They cannot ask you questions. Note every place they get stuck.
4. **At the end of 60 minutes, compare their numbers to your reported numbers.** Same hardware family? Different? Within 20%? Different by an order of magnitude?
5. **Write a 1-page audit memo** capturing every gap you observed.

## What to watch for

The taxonomy of reproducibility gaps:

### Gap class 1: Environment

- The peer's Python version is different from yours. You assumed 3.13; they have 3.11.
- The peer's NumPy version is different. You ran with 2.1.0; they have 1.26.0.
- The peer's OS is different. You measured on macOS arm64; they are on Ubuntu x86_64.
- The peer's machine is different. You used an M3 Pro; they are on a 2018 Intel laptop on battery power.

**The fix:** state every environmental assumption in the report. Pin dependencies. State minimum hardware. State whether numbers should be expected to hold cross-platform.

### Gap class 2: Implicit setup

- The peer cannot `pip install` because they have not enabled `--extra-index-url`.
- The peer cannot run the benchmark script because the script lives in `benchmarks/` and was not included in the wheel.
- The peer needs `pytest`, `psutil`, `memray`, and one of them is not in the `[benchmarks]` extra.

**The fix:** the README must list the *exact* commands a fresh-venv user runs from install to first chart. No "obvious" steps elided.

### Gap class 3: Methodology gaps

- The peer ran the benchmark once and reported the number. Your reported number was the median of 21 runs. The single run was an outlier.
- The peer's machine has hyperthreading enabled; yours does not. The thread benchmark scales differently.
- The peer did not warm up. The first run is always slow (JIT-ish effects in NumPy's BLAS, page faults in fresh memory).

**The fix:** the benchmark *script* enforces the methodology. It runs the warm-ups, takes the median, computes the bootstrap CI. The peer should not need to know any of this. Their command is `python benchmarks/run.py` and the script prints the right numbers.

### Gap class 4: Documentation gaps

- The peer does not know what "Tier 2" means in your speedup table because you used the term without defining it.
- The peer cannot find the package on TestPyPI because the name on the page differs from the name in your README (typo, case difference, missed hyphen).
- The peer reads "this version skips the C extension" and wonders whether the wheel they installed is the C-extension version or not.

**The fix:** define terms at first use. Cross-check every name in the report against the actual TestPyPI page. State explicitly what wheel/sdist they will be installing.

### Gap class 5: Numerical precision

- The peer's numbers are *correct* but in different units. You reported "milliseconds"; their output is in "seconds." Off by 1000x.
- The peer's bootstrap CI uses a different random seed. The interval is slightly different. Is that "fails to reproduce" or "within tolerance"?

**The fix:** the benchmark script defines the unit, the seed, the methodology. The report cites the script.

## The deliverable

A markdown file `mini-project/AUDIT.md` (you will create this) containing:

### Section 1: The audit summary

One paragraph. Did your peer reproduce your numbers? Within how many percent? How long did it take? What was the single biggest blocker?

### Section 2: The gap list

A bullet list of every gap observed, classified by the taxonomy above (Environment, Implicit setup, Methodology, Documentation, Numerical precision). For each gap, the specific symptom and the fix you applied.

### Section 3: The patch diff

The report has been updated to close the gaps. The patch may be small (a few extra sentences in the README) or large (a rewrite of the methodology section). Either way, write a *diff-style* summary of what changed.

### Section 4: Reflection

Two paragraphs. What did you learn about how strangers read your report? What would you do differently for a future package?

## Acceptance criteria

You have completed Challenge 02 when:

- [ ] A peer (or a Docker container, or a stranger from a study group) has run your reproduction instructions and recorded their results.
- [ ] The audit memo exists at `mini-project/AUDIT.md` with all four sections filled.
- [ ] At least one concrete fix has been applied to the report or the benchmark script as a result of the audit. (If no fix was needed, your report is perfect *or* the audit was insufficiently rigorous. The former is rare; suspect the latter.)
- [ ] The updated reproduction instructions in your final REPORT.md reflect what was learned.

## The harder version of this challenge

If you finish the basic version with time to spare:

1. **Re-audit on different hardware.** Send the report to a peer with a different OS or CPU architecture. Cross-platform reproducibility is harder than same-platform.
2. **Re-audit a year later.** Save the rehearsal artefacts. In six months — long after C17 ends — try to reproduce your own numbers. The gaps that emerge ("I can't find my TestPyPI password" / "the package was pruned" / "NumPy 3.0 broke the API") are gaps you should think about now.
3. **Audit the *audit*.** Have your peer try, in turn, to reproduce *their* audit memo's numbers. The recursion goes one level deep before it gets silly. One level is enough.

## On giving honest feedback to your peer

If you are the auditor (rather than the auditee), your job is to record every confusion you experience, not to "give the benefit of the doubt." Confusion that you privately resolve by guessing what the author meant is *exactly* the confusion the author needs to know about. Be specific. "The README is unclear" is useless; "The README says 'install the benchmarks extras' but does not say how to invoke the benchmark afterwards, and the obvious `python -m cc_jdoe_blurperf.benchmark` is not a valid module path" is useful.

If you are the auditee, your job is to take the audit seriously, even when the gap is "obvious" to you. The fact that it was not obvious to your peer is the entire point. Resist the urge to defend; ship the fix.

## On time

This challenge is approximately a 90-minute investment:

- 60 minutes for the peer to attempt reproduction.
- 30 minutes for you to write the audit memo.

It is the highest-leverage 90 minutes of the capstone. A flawed package with a great report scores higher than a great package with a flawed report; the audit is the only way to know which side of that line you are on.

## References

- The W7 lecture notes on profiling methodology.
- Lecture 03 of this week on the benchmark report.
- [Reproducible Builds](https://reproducible-builds.org/) — the philosophical home of "bit-for-bit reproducibility." Our standard is much weaker (numbers within 20%) but the discipline is the same.
- Karl Popper, *The Logic of Scientific Discovery*, on the falsifiability criterion. A non-reproducible benchmark is unfalsifiable; an unfalsifiable benchmark is not science.
