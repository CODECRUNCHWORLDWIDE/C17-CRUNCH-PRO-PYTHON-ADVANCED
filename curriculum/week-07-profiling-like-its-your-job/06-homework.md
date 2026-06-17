# Week 7 — Homework

Six problems, ~7 hours total. Commit each as you finish.

---

## Problem 1 — Read `Lib/cProfile.py` and skim `Modules/_lsprof.c` (60 min)

Open the Python wrapper: <https://github.com/python/cpython/blob/main/Lib/cProfile.py>. ~200 lines.

Open the C implementation: <https://github.com/python/cpython/blob/main/Modules/_lsprof.c>. ~1100 lines; you do not need to read all of it.

Read `cProfile.py` end-to-end. Find:

- The `Profile` class and its `__enter__` / `__exit__` (3.9+ context manager support).
- The `run` and `runctx` module-level helpers.
- The `runcall` instance method (run a function under the profile and return its result).
- The `_pyformat` private function that formats `pstats` output (note: it is implemented in `Lib/pstats.py`, not here).

Then in `_lsprof.c`, find:

- The `ProfilerObject` C struct (~line 30).
- The `profiler_callback` C function (~line 350; it is the function registered with `PyEval_SetProfile`).
- The `Profiler_enable` and `Profiler_disable` methods — what calls `PyEval_SetProfile`? When?

**Acceptance:** `cprofile-reading.md` in your portfolio:

- A GitHub permalink to `profiler_callback`.
- A 300-word walkthrough of: what happens when user code calls `pr.enable()`; what the per-call C path looks like (entry → record time → look up function descriptor → on exit, record delta and accumulate); how `pr.disable()` unregisters.
- One observation: where does `_lsprof` get the per-edge timing? (Hint: `roptimes` array.)
- One critique: in 100 words, would you redesign anything? (PEP 669 already did; cite it.)

---

## Problem 2 — `cProfile` on a small open-source library's test suite (60 min)

Pick a small Python library that has a test suite that runs in 5–30 seconds: candidates include `markdown-it-py`, `pyflakes`, `bandit`, `click`, `httpx` (just the unit tests, not the integration tests), `jinja2`, `mistune`, `mistletoe`.

```bash
git clone https://github.com/$ORG/$REPO
cd $REPO
pip install -e .[test]
python -m cProfile -o tests.pstats -m pytest -x tests/
```

(Or substitute the project's test invocation; many use `nox`, `tox`, or `make test`.)

Open the `tests.pstats` file:

```python
import pstats
s = pstats.Stats("tests.pstats").strip_dirs().sort_stats("tottime")
s.print_stats(30)
```

**Acceptance:** `library-cprofile.md` in your portfolio:

- The library you picked and why.
- The top 10 by `tottime` (paste the table).
- The top 10 by `cumulative` (paste the table).
- A 200-word observation: which library functions dominate? Is it the test fixtures, the assertions, the parser, the AST walker? Are most of the top entries in *your library's* code or in `pytest`, `unittest`, `_pytest`?
- One question you would ask the maintainers based on the profile. (You do not have to ask it.)

---

## Problem 3 — `line_profiler` on a function you wrote in Week 5 or 6 (45 min)

Open any function from Week 5 or Week 6 that processes meaningful data (the async crawler from Week 5, the multiprocessing kernel from Week 6 Exercise 1, the `concurrency-bench` workloads). Decorate the function with `@profile`, add the kernprof-or-not shim, run `kernprof -l -v`.

**Acceptance:** `line-profiler-week5or6.md`:

- The function (paste, or link to it in your portfolio).
- The `kernprof -l -v` output (paste).
- A 200-word commentary: which line is hottest? Was it where you expected? Was the *next* hottest line a surprise? Would you change anything?

If the function is dominated by IO or `await`, the per-line output may not be useful — note that, and pick a different function (synchronous, CPU-touching) for this problem.

---

## Problem 4 — `py-spy` on a 30+ second workload (60 min)

Write `long_running.py` that runs for at least 60 seconds doing meaningful work: a Monte Carlo simulation, a brute-force search, anything CPU-bound that you can run from a single Python command. (You can re-use Week 6 Exercise 1 with `n_samples=50_000_000`.)

Start it in one terminal. In another terminal:

```bash
sudo py-spy dump --pid $(pgrep -f long_running.py)
sudo py-spy record -o flame.svg --pid $(pgrep -f long_running.py) --duration 30
sudo py-spy top --pid $(pgrep -f long_running.py)    # leave running 30s, watch
```

**Acceptance:** `py-spy-session.md`:

- The `long_running.py` source.
- The `py-spy dump` output (paste).
- The `flame.svg` (commit to repo or upload to a public host and link).
- A 150-word reading of the flamegraph: name the hot leaf, the hot path, and one observation about the shape (concentrated tower vs. diffuse base).

If you cannot use `sudo` and `ptrace_scope=1` is set, document the workaround you used: lowering the sysctl temporarily, running both processes in a Docker container, or using macOS (where `sudo` is more straightforward).

---

## Problem 5 — `scalene` on the same workload (60 min)

Run `scalene --cli long_running.py > scalene.txt` on the workload from Problem 4 (or any 5+ second CPU workload). Capture the full output to `scalene.txt`.

**Acceptance:** `scalene-session.md`:

- The full `scalene.txt` (paste, or link to it in the portfolio).
- A 250-word commentary:
  - Did scalene agree with py-spy on which function is hot?
  - For the hot function: what does the Python / Native / System breakdown say? Is the workload CPU-bound (high Python column) or library-bound (high Native column) or syscall-bound (high System column)?
  - The Mem % column: any line with non-trivial allocations? Could those be eliminated?
  - One thing scalene revealed that py-spy did not.

---

## Problem 6 — Pick a real OSS issue marked "performance" and analyse it (90 min, optional but recommended)

Browse the GitHub issues of any popular Python library — `requests`, `httpx`, `pandas`, `flask`, `pydantic`, `pillow`, `cryptography`, `pyyaml`, `markdown-it-py`. Filter by label `performance`. Pick *one* open issue with a reproduction case.

Reproduce the slow behaviour on your machine. Profile with `cProfile` and (if you can build a runnable case) with `py-spy`. Read the issue's existing discussion.

**Acceptance:** `oss-perf-issue.md`:

- Link to the issue.
- One-paragraph summary of what is reported as slow.
- Your reproduction: how did you set it up; what was the wall clock; what did `cProfile` show?
- Your read: do you agree with the existing diagnosis in the comments? If there is no diagnosis yet, what is yours?
- One sentence: would you contribute the analysis as a comment on the issue?

This problem is *not* "fix the bug." It is "do the same disciplined profiling on real, open-source, contested code that the maintainers have not necessarily resolved." The point is to see what your skills look like against a real target. The artifact is your analysis; whether you ship it back to the project is up to you.

---

## Submission

Commit all files under `c17-week-07-homework/` in your portfolio repo. The expected shape:

```
c17-week-07-homework/
  cprofile-reading.md
  library-cprofile.md
  line-profiler-week5or6.md
  py-spy-session.md
  scalene-session.md
  oss-perf-issue.md           # if Problem 6 attempted
  long_running.py
  flame.svg
  scalene.txt
  tests.pstats
```

If Problem 6 took too long, ship Problems 1–5 by the end of Sunday and tackle Problem 6 the following weekend as a stretch. The minimum bar is Problems 1, 2, 4, and either 3 or 5; the full set is the target.

## Reading

- Lecture 1 §§1–13.
- Lecture 2 §§1–15.
- Lecture 3 §§1–20.
- The cProfile docs Instant User's Manual: <https://docs.python.org/3/library/profile.html#instant-user-s-manual>.
- py-spy README "Examples" section: <https://github.com/benfred/py-spy#examples>.
- scalene README "Usage" and "Output" sections: <https://github.com/plasma-umass/scalene>.
- Brendan Gregg, "Flame Graphs": <https://www.brendangregg.com/flamegraphs.html>.
- PEP 657 (column-level traceback positions, 3.11): <https://peps.python.org/pep-0657/>.
- PEP 669 (`sys.monitoring`, 3.12): <https://peps.python.org/pep-0669/>.

## Notes

- **Use the tools in order.** cProfile → line_profiler (if needed) → py-spy (if production-shaped) → scalene (if CPU-vs-memory in question). Skipping the order is the most common cause of wasted hours.
- **`sudo` is normal for py-spy on Linux and macOS.** Do not spend an hour trying to find a clever way around it; use `sudo` and move on.
- **Profile the unprofiled wall clock before and after every change.** The number that matters is what the user experiences, not what the profile reports.
- **The homework is six problems for a reason.** Each one builds a different reflex: read C, profile real code, find the hot line, attach to a process, see the memory split, engage with a real OSS issue. Skipping the easy ones and only doing Problem 6 robs you of the muscle build.
