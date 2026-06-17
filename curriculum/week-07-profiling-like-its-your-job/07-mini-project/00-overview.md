# Mini-Project — `profile-an-oss-project`: Take a Real Python Project, Profile It, Write the Report

> Pick a real, free, open-source Python project. Drive a representative workload through it. Profile under `cProfile`, `line_profiler`, `py-spy`, and `scalene`. Produce a 600–900 word public report that identifies the hottest path with numbers, includes one flamegraph SVG, names a proposed fix, and is good enough that an interviewer would accept it as evidence of profiling competence. The artifact is small (~80% writing, 20% command lines) but its job is to be the thing you point at when someone asks "tell me about a time you profiled and fixed something."

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-07-profile-an-oss-project-<yourhandle>` containing:

1. **`README.md`** — what the project is, how to reproduce, what you found. ~150 words. Plus the link to the OSS project you profiled.
2. **`REPORT.md`** — **the load-bearing artifact**. 600–900 words. Sections below.
3. **`bench/workload.py`** — the Python file that drives the profiled workload. ~50–150 lines. Self-contained: install the target, run the workload, exit.
4. **`profiles/cprofile_baseline.pstats`** — the binary `pstats` dump from cProfile.
5. **`profiles/cprofile_top.txt`** — the top 30 by `tottime` and top 30 by `cumulative`, captured to text for the report.
6. **`profiles/line_profile.txt`** — `kernprof -l -v` output for the hot function.
7. **`profiles/py-spy-flame.svg`** — the flamegraph from py-spy.
8. **`profiles/py-spy-dump.txt`** — a one-shot stack dump.
9. **`profiles/scalene.txt`** — `scalene --cli` output.
10. **`scripts/reproduce.sh`** — a shell script that, given a clean machine with Python 3.13 and pip, installs everything and re-runs all the profiles. ~20 lines.
11. **`LICENSE`** — MIT, Apache-2.0, GPL, your choice.

The report is what people read. Everything else is the audit trail.

## Picking the target

The target is *any* Python project that meets these criteria:

- **Public, free, open-source.** GitHub link must work.
- **Pure Python or mostly pure Python.** Heavy C-extension projects (numpy, pandas internals, lxml) make for boring profiles — Python is a thin wrapper and the time is invisible. Target ~80% Python, ~20% C.
- **1,000–20,000 lines of code.** Smaller and there is no interesting profile. Larger and you cannot understand the codebase in one week.
- **Has a meaningful workload you can drive in 3–30 seconds.** Faster than 3 seconds, profiling is noisy. Longer than 30, iteration is slow.
- **Not pre-optimised to death.** A project that already has benchmarks and explicit performance pull requests is harder; the easy wins are already gone. A project that has *never* been profiled is easier.

Suggested targets (any of these works):

- **`markdown-it-py`** — Markdown parser. ~5,000 lines Python. Drive: parse the GitHub-Flavoured-Markdown reference document or the entire CommonMark spec.
- **`mistune`** — alternative Markdown parser. ~3,000 lines. Drive: parse a large corpus of markdown files (mkdocs docs, GitHub README dumps).
- **`pyflakes`** — Python linter. ~3,000 lines. Drive: lint the CPython standard library.
- **`bandit`** — Python security linter. ~5,000 lines. Drive: scan a real codebase.
- **`requests`** — HTTP library. ~5,000 lines Python (urllib3 is a separate dependency). Drive: 1000 requests against a local `aiohttp.web` server with artificial latency.
- **`click`** — CLI library. ~8,000 lines. Drive: invoke a complex CLI 1000 times and measure dispatch + argument parsing.
- **`jinja2`** — template engine. ~8,000 lines. Drive: render a complex template 10,000 times.
- **`bleach`** — HTML sanitiser. ~3,000 lines. Drive: sanitise a corpus of HTML pages.
- **`humanize`** — number/time humanisation. ~1,000 lines. Drive: call `humanize.naturaltime` 1,000,000 times.
- **`pyyaml`** — YAML parser. ~5,000 lines Python. Drive: parse a large YAML corpus.

**Avoid** for this mini-project: pandas, numpy, scikit-learn (heavy C; Python is invisible); flask, django (the framework is mostly request dispatch; the time is in your handler, not theirs); pytorch (GPU-bound; out of scope).

You pick. Document the pick in the report. If unsure, `markdown-it-py` is the safe default.

## The workload

Whatever workload you pick must be:

- **Reproducible.** A specific input file or input generator with a fixed seed. The reviewer must be able to run your benchmark and get the same hot path.
- **Representative.** The workload should resemble what a real user would do, not a synthetic stress test. Parsing a Markdown file is more representative than parsing 100,000 copies of `"# hello"`.
- **3–30 seconds long** under default Python. Run a sanity timing first.
- **CPU-bound** (or mixed). The mini-project is about profiling Python time, not waiting for the network. If you pick a network-heavy target like `requests`, set up a local `aiohttp` server with 10-ms artificial latency — the profile will then surface what `requests` is doing during the wait time.

A reasonable `bench/workload.py` for `markdown-it-py`:

```python
"""Drive markdown-it-py through a representative document N times."""
from __future__ import annotations
import time
from pathlib import Path
from markdown_it import MarkdownIt

def main() -> None:
    md = MarkdownIt()
    # The CommonMark spec document is ~70KB of dense markdown. It is
    # the canonical "real" workload for any markdown parser.
    text = Path("commonmark-spec.md").read_text()
    n_iter = 200
    t0 = time.perf_counter()
    for _ in range(n_iter):
        md.parse(text)
    elapsed = time.perf_counter() - t0
    print(f"{n_iter} iterations in {elapsed:.2f}s ({elapsed/n_iter*1000:.2f} ms each)")

if __name__ == "__main__":
    main()
```

## The four profiling passes

### Pass 1 — `cProfile`

```bash
python -m cProfile -o profiles/cprofile_baseline.pstats bench/workload.py
```

Read the binary file:

```python
import pstats
s = pstats.Stats("profiles/cprofile_baseline.pstats").strip_dirs()
s.sort_stats("tottime").print_stats(30)
s.sort_stats("cumulative").print_stats(30)
```

Capture the top-30-by-tottime *and* top-30-by-cumulative tables to `profiles/cprofile_top.txt`. Both, because the report should show that you understand the difference.

### Pass 2 — `line_profiler`

Identify the hottest function from Pass 1. Add `@profile` to it (in the installed library — `pip install -e ` the cloned target, or edit the installed copy in your venv). Add the kernprof-or-not shim. Run:

```bash
kernprof -l -v bench/workload.py > profiles/line_profile.txt
```

The output is per-line for the decorated function. Save it.

### Pass 3 — `py-spy`

```bash
# Start the workload in one terminal.
python bench/workload.py

# In another terminal, find the PID and attach.
PID=$(pgrep -f bench/workload.py)
sudo py-spy dump --pid $PID > profiles/py-spy-dump.txt
sudo py-spy record -o profiles/py-spy-flame.svg --pid $PID --duration 30
```

If the workload finishes in <5 seconds, modify `bench/workload.py` to loop (run the workload in a `while True:` so py-spy has time to attach and sample).

### Pass 4 — `scalene`

```bash
scalene --cli bench/workload.py > profiles/scalene.txt
```

Save the full output. Look at the Python/Native/System split for the hot function and the Mem % column for any lines that allocate.

## The report

`REPORT.md`. 600–900 words. Six sections.

### Section 1 — Target and workload (~100 words)

Name the project, link to it, version. Describe the workload in two sentences. State the unprofiled wall clock.

### Section 2 — cProfile findings (~150 words)

Name the hottest function (by `tottime`). Name the hottest call path (by `cumulative`, then trace down to the leaf). Quote the relevant rows from `profiles/cprofile_top.txt`. State *why* sorting by `tottime` matters here — the cumulative leader is the orchestrator, the tottime leader is the actual hot leaf.

### Section 3 — line_profiler findings (~100 words)

Within the hot function from Section 2, name the hottest line and its share of the per-line total. Quote 4–6 relevant rows of the line_profiler output. Note any surprises (a line you would not have expected to be hot).

### Section 4 — py-spy findings (~100 words)

Describe the flamegraph. Include the SVG (link, or embed if your renderer supports it). Name the widest plateau, the call path beneath it. Note whether the sampling profile agrees with cProfile on which function is hot. *Disagreements* are interesting — narrate them.

### Section 5 — scalene findings (~100 words)

The Python / Native / System split for the hot function. Memory allocations attributed to which lines. Whether the workload is CPU-bound, library-bound (C extension), or memory-bound. *This is often the most informative section* — it changes the kind of fix you would propose.

### Section 6 — Proposed fix and reflection (~150 words)

Based on what the four tools converged on, propose *one* concrete fix. Be specific: "replace the `for ch in s: result += ch.lower()` loop in `markdown_it/rules_inline/text.py:42` with `s.lower()` because `str.lower` is implemented in C and is ~50x faster." You do **not** need to implement and measure the fix; the report's value is the diagnosis, not the patch. (If you *do* implement and measure, the report is stronger — add a Section 7.)

End with one paragraph of reflection: what surprised you about the codebase? What would you ask the maintainers? Would you open an issue or PR?

## Acceptance criteria

- [ ] Repo public on GitHub (or a private link shared with the reviewer).
- [ ] `scripts/reproduce.sh` works on a clean machine: install Python 3.13, run the script, get all four profile outputs.
- [ ] `bench/workload.py` is self-contained: clones or installs the target, runs the workload, exits.
- [ ] All four profile outputs exist in `profiles/`.
- [ ] `profiles/py-spy-flame.svg` is a real SVG that opens in a browser.
- [ ] `REPORT.md` exists, is 600–900 words (target; 500–1000 acceptable), and has all six sections.
- [ ] The report names a *specific* hot leaf and a *specific* proposed fix, both grounded in the profile data.
- [ ] You did not optimise for a number; you optimised for an honest diagnosis. A report that concludes "the project is already well-tuned and the bottleneck is in a C extension I cannot improve" is *valid* and worth shipping, *as long as the discipline is visible in the four-tool comparison*.

## Suggested order of operations

### Thursday (~2 h)

1. Pick the target (15 min).
2. Set up `bench/workload.py` and time it unprofiled (15 min).
3. cProfile pass: `python -m cProfile -o profiles/cprofile_baseline.pstats bench/workload.py`. Read it. Capture `cprofile_top.txt`. Identify the hot function. (60 min — reading takes longer than running.)
4. Start drafting `REPORT.md` Section 1 (workload). (30 min.)

### Friday (~3 h)

5. line_profiler pass on the hot function from Thursday. Capture `line_profile.txt`. (45 min.)
6. py-spy pass. Get `dump.txt` and `flame.svg`. Read the flamegraph in a browser. (60 min — the first time you read one carefully, it takes a while.)
7. Draft `REPORT.md` Sections 2, 3, 4. (75 min.)

### Saturday (~2 h)

8. scalene pass. Capture `scalene.txt`. Compare to cProfile and py-spy. (45 min.)
9. Draft `REPORT.md` Section 5. (30 min.)
10. Hypothesise the fix; write Section 6. (45 min.)
11. Polish: prose pass, add cross-references between sections, verify SVG renders. (30 min.)
12. Write `scripts/reproduce.sh` and verify it works in a fresh venv. (15 min.)
13. `README.md` with a link to the report and the GitHub project. (15 min.)
14. Push, sanity-check the public view, ship.

## Common pitfalls

- **Picking a target that is too small.** A 200-line library has nothing interesting in the profile; the work is in the import or in the test fixtures. Pick something with substance.
- **Picking a target that is too C-heavy.** `numpy` profiles look like 99% `<built-in method numpy.core._multiarray_umath...>` — boring, and there is no fix you can write in Python. Pick mostly-Python.
- **Workload too short.** A 0.3-second workload produces noisy profiles. Loop your driver until it runs 5+ seconds.
- **Workload too long.** A 5-minute workload makes the report cycle hours long. Aim for 5–15 seconds per profile pass.
- **Profiling the import.** `python -m cProfile bench/workload.py` profiles the entire interpreter session, including imports. If your library is slow to import, the report becomes about that. Use the context-manager form (Lecture 2 §2.2) to scope the profile.
- **Forgetting to include the flamegraph.** A profiling report without an SVG is half a report.
- **Writing 2000 words.** The constraint is 600–900. Cut the asides. State, evidence, conclude.

## Why this matters

The mini-project is the **artifact** for Week 7. Every interview for a "senior" or "staff" Python role asks some version of "tell me about a time you profiled and fixed something." Most candidates fumble. The candidates who do well say "let me show you," and they have a 700-word report with a flamegraph that demonstrates discipline, judgement, and ownership. That report is what we are building here.

It is also a real artifact in another sense: if the diagnosis is interesting, you can ship it as a GitHub issue or PR to the upstream project. That is how engineers build a public profile. The mini-project does not require it, but it is a natural next step if the work warrants.

## Reading

- All three Week 7 lectures, end-to-end. Treat them as reference.
- The chosen project's `CONTRIBUTING.md` and any existing performance discussion in their issues.
- Brendan Gregg, "Flame Graphs": <https://www.brendangregg.com/flamegraphs.html>.
- One blog post by someone who has profiled the project before, if available. (Search `<project name> profiling`.)

Good profiling.
