# Week 11 — Homework

Six problems. Budget about 7 hours total. Submit a single markdown document with one section per problem plus the requested code files. Number the sections to match this page. Cite primary sources (PEP, docs, talk).

## Problem 1 — Write the four-model decision flowchart on a single page (60 min)

Produce a one-page (PDF, Markdown, or plain SVG — your choice) flowchart that a teammate could use, with no prior context, to pick the right Python concurrency model for a workload.

Constraints:

- The flowchart must answer at least these five workload archetypes: (a) HTTP API fanout with 5,000 concurrent requests; (b) image processing on a folder of 10,000 PNGs (CPU-bound, NumPy and Pillow); (c) parsing a 50 GB log file line by line (mixed CPU and disk I/O); (d) running 200 Selenium scrapers in parallel (subprocess + I/O); (e) training a small ML model on a CPU-only laptop (pure CPU; NumPy and pandas).
- Every leaf node must name a concrete model: `serial`, `ThreadPoolExecutor`, `asyncio.gather`, `ProcessPoolExecutor`, `interpreters.Queue`, or "switch to free-threaded build."
- Every decision node must have a one-line justification ("Does the work release the GIL? See `hashlib.sha256` audit in Exercise 2.").
- The flowchart fits on one page printed at A4 / Letter.

Deliverable: `problem-1-flowchart.{md,pdf,svg}`. Three to five sentences of commentary on which leaves you found hard to assign and why.

## Problem 2 — Measure your own service (90 min)

Pick a Python script or service you (or your team) actually runs. Could be a build script, a deployment hook, a daily data refresh, a side-project web app. Profile it.

Steps:

1. **Identify the hot path.** Run with `python3 -X importtime script.py` or `py-spy record -o profile.svg -- python3 script.py`. Find the function that takes the most wall-clock time.
2. **Classify the hot path** as I/O-bound or CPU-bound. If CPU-bound, classify further: pure-Python or C-extension. If I/O-bound, classify: network or disk.
3. **Predict which concurrency model would improve it**, based on this week's decision tree. Be specific about the predicted speedup.
4. **Implement the prediction**, even if just on a branch. Measure the actual speedup.
5. **Compare** prediction to measurement. If you were wrong, write 2-3 sentences on why.

Deliverable: a `problem-2-profile.md` describing the script, the hot path, the prediction, the implementation diff (or a link to the branch), and the comparison. Plus the profile artifact (`profile.svg`, `importtime.txt`, or equivalent).

## Problem 3 — Reproduce a real-world asyncio blocking bug (60 min)

Find a real-world report of an "asyncio is slow / asyncio is not parallel" bug. Good sources: the asyncio GitHub issues (<https://github.com/python/cpython/issues?q=is%3Aissue+label%3Atopic-asyncio>), the FastAPI issue tracker, the httpx issue tracker, the Stack Overflow asyncio tag.

Steps:

1. **Find one issue** where the bug was diagnosed as "the event loop was blocked by sync code." Note the issue URL.
2. **Read the discussion.** What was the original code? What was the symptom?
3. **Reproduce the bug** in a 30-line script in your homework directory. Make the script fail (in the sense that the throughput is comparable to serial).
4. **Apply the fix** the issue ultimately recommended. Make the script succeed.
5. **Write a one-paragraph post-mortem** in the style of an SRE post-mortem: timeline, root cause, remediation, prevention.

Deliverable: `problem-3-blocked-loop/{bug.py, fix.py, postmortem.md}`. The post-mortem must cite the original issue URL.

## Problem 4 — Audit a C extension you depend on for GIL release (60 min)

Pick one C extension your project uses: NumPy, SciPy, Pillow, cryptography, lxml, sqlalchemy, polars, your-favourite-orm, etc.

Steps:

1. **Find the project's source code** on GitHub.
2. **`grep -r "Py_BEGIN_ALLOW_THREADS"`** in the C source. Count the occurrences. List the top three by relevance (the functions you actually call most).
3. **For each of the three, write one sentence** on what the function does and what the GIL-release decision implies.
4. **Cross-reference with the documentation**. Does the project document its GIL behaviour? Cite the doc URL.
5. **Write one paragraph** on the practical implication for your project: which calls release, which do not, what that means for whether `ThreadPoolExecutor` is a good fit.

Deliverable: `problem-4-c-extension-audit.md`. Three top functions, three implications, one paragraph.

## Problem 5 — Predict-and-measure on the free-threaded build (90 min)

If you completed Challenge 1, you have the free-threaded build installed. If not, install it now (`uv python install 3.13t`; 30 seconds).

Pick a Python program where you genuinely do not know in advance whether the free-threaded build will help. Good candidates: a recursive Fibonacci, a sorting benchmark, an NLP tokeniser, a JSON-heavy CSV processor.

Steps:

1. **Write a benchmark** that runs the program with `ThreadPoolExecutor(8)` (or 4, 16 — your choice of pool size).
2. **Predict, in writing**, whether free-threaded will win or lose, and by what factor. Justify in two sentences.
3. **Run the benchmark on stock 3.13.** Record throughput.
4. **Run the benchmark on 3.13t.** Record throughput.
5. **Compute the ratio.** Compare to your prediction.

Deliverable: `problem-5-free-threaded.md`. Prediction, two measurements, ratio, two sentences on whether your prediction was right or wrong. Plus the benchmark code (`problem-5-bench.py`).

## Problem 6 — Read PEP 703 § "Performance" (60 min)

Read the "Performance" section of PEP 703 (<https://peps.python.org/pep-0703/#performance>). About 4,000 words; 30 minutes.

Then write a 500-word essay in the form of a memo to your engineering director, explaining:

- What the free-threaded build does to single-threaded performance (the regression number).
- What it does to multi-threaded performance on CPU-bound workloads (the speedup number).
- The two biggest engineering trade-offs the PEP names.
- Your recommendation: should the team migrate to 3.13t in the next 6 months, in the next 18 months, or wait until 3.15 makes it default?

The memo must cite PEP 703 by section number and at least two other primary sources (the Faster CPython tracking page, a Sam Gross talk, the official Python release notes).

Deliverable: `problem-6-memo.md`. 500 words. Bullet points are fine; complete sentences in the recommendation are mandatory.

## Submission

A folder `homework-week-11/` containing:

```
homework-week-11/
├── problem-1-flowchart.md (or .pdf or .svg)
├── problem-2-profile.md
├── problem-2-profile.svg (or equivalent artifact)
├── problem-3-blocked-loop/
│   ├── bug.py
│   ├── fix.py
│   └── postmortem.md
├── problem-4-c-extension-audit.md
├── problem-5-free-threaded.md
├── problem-5-bench.py
└── problem-6-memo.md
```

Each `.py` file must pass `python3 -m py_compile <file>`. Each `.md` file must cite at least one primary source. Total expected effort: ~7 hours. Submit by end of Sunday.

## Grading

- Problem 1: 15% (clarity, completeness, fits on a page).
- Problem 2: 20% (real measurement, honest prediction, comparison to actual).
- Problem 3: 15% (real bug, runs and fails, runs and succeeds).
- Problem 4: 10% (grep count is correct, three implications are specific).
- Problem 5: 20% (benchmark works on both builds, ratio is computed).
- Problem 6: 20% (memo is 500 words, three citations, recommendation defended).
