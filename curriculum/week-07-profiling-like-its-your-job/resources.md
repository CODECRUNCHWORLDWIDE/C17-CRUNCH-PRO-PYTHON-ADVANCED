# Week 7 — Resources

All free. Free + open tools only. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — stdlib and CPython source tree

| What | Where |
|------|-------|
| **`profile` and `cProfile` module docs** (canonical reference for the deterministic profilers) | <https://docs.python.org/3/library/profile.html> |
| **`pstats` module docs** (reading and aggregating `cProfile` output) | <https://docs.python.org/3/library/profile.html#module-pstats> |
| **`timeit` module docs** (the micro-benchmark; not a profiler, but the unit-cost measurement that complements profiling) | <https://docs.python.org/3/library/timeit.html> |
| **`tracemalloc` module docs** (stdlib memory allocation tracer; complements scalene for memory-leak hunts) | <https://docs.python.org/3/library/tracemalloc.html> |
| **`sys.setprofile`, `sys.settrace`** (the C hooks that `cProfile` and `coverage.py` use) | <https://docs.python.org/3/library/sys.html#sys.setprofile> |
| **`sys.monitoring`** (PEP 669; the 3.12+ replacement, much lower overhead) | <https://docs.python.org/3/library/sys.monitoring.html> |
| **`time.perf_counter`, `time.process_time`, `time.thread_time`** (wall vs. CPU vs. thread clocks) | <https://docs.python.org/3/library/time.html#time.perf_counter> |
| **`Lib/cProfile.py`** (the Python wrapper around `_lsprof`) | <https://github.com/python/cpython/blob/main/Lib/cProfile.py> |
| **`Lib/pstats.py`** (the table reader / sorter / printer) | <https://github.com/python/cpython/blob/main/Lib/pstats.py> |
| **`Modules/_lsprof.c`** (the C profiler — the actual instrumentation engine) | <https://github.com/python/cpython/blob/main/Modules/_lsprof.c> |
| **`Lib/profile.py`** (the pure-Python predecessor, kept for reference) | <https://github.com/python/cpython/blob/main/Lib/profile.py> |
| **`Python/legacy_tracing.c`** (the bridge between `sys.setprofile` and `PEP 669` for backwards compat) | <https://github.com/python/cpython/blob/main/Python/legacy_tracing.c> |
| **`Python/instrumentation.c`** (the PEP 669 implementation; how `sys.monitoring` events are emitted by the interpreter) | <https://github.com/python/cpython/blob/main/Python/instrumentation.c> |

## Required PEPs

- **PEP 657 — Include Fine-Grained Error Locations in Tracebacks** (Galindo Salgado, Cuevas, 2021; landed 3.11): <https://peps.python.org/pep-0657/>
  *Adds column-level position information to code objects (`co_positions`). Every profiler output in 3.11+ that prints `filename:lineno` now has access to the start/end column too; tools that surface this (`pytest`, `traceback`, `dis`) are markedly more useful. cProfile's table format did not change, but `py-spy` and `scalene` can use the new data to pinpoint within a line. ~20 minutes.*
- **PEP 669 — Low Impact Monitoring for CPython** (Mark Shannon, 2022; landed 3.12): <https://peps.python.org/pep-0669/>
  *The successor to `sys.setprofile` and `sys.settrace`. Multi-tool capable, per-event opt-in, much lower overhead. The intended foundation for next-generation profilers, debuggers, and coverage tools. py-spy 0.4+ and scalene already use it where available. ~40 minutes.*
- **PEP 525 — Asynchronous Generators** (Selivanov, 2016): <https://peps.python.org/pep-0525/>
  *Tangential. Cited here because the asyncio-aware profilers (yappi, scalene) had to handle async-generator frames specially. Read §"Implementation" only; ~10 minutes.*

Optional, of interest:

- **PEP 446 — Make Newly Created File Descriptors Non-Inheritable** (Stinner, 2014): <https://peps.python.org/pep-0446/>
  *Relevant only because py-spy uses inheritable FDs to bridge subprocess sampling; in practice it just works.*

## Stdlib profiling docs

- **The `profile` and `cProfile` user guide** — the canonical reference. Read §3 (Instant User's Manual) first; §5 (`Profile` class) second; §6 (`pstats.Stats`) third. <https://docs.python.org/3/library/profile.html>.
- **The `pstats.Stats` reference** — every method you will use programmatically: `strip_dirs()`, `sort_stats('tottime' | 'cumulative' | 'calls' | 'pcalls' | 'name' | 'file' | 'line' | 'nfl')`, `print_stats(20)`, `print_callers('foo')`, `print_callees('foo')`. <https://docs.python.org/3/library/profile.html#the-stats-class>.
- **The `timeit` user guide** — how to measure unit cost properly: outer/inner loops, the `Timer.autorange` method, the `--repeat` flag. The micro-benchmark complement to profiling. <https://docs.python.org/3/library/timeit.html>.
- **The `tracemalloc` user guide** — stdlib memory-allocation tracker. Snapshots, top-statistics, line-level attribution. Slower and noisier than scalene's allocator-injection approach, but ships with Python and is enough for many leak hunts. <https://docs.python.org/3/library/tracemalloc.html>.
- **The 3.12 What's New — `sys.monitoring`** — the practitioner's introduction to PEP 669: <https://docs.python.org/3/whatsnew/3.12.html#whatsnew312-pep669>.

## `line_profiler` and `kernprof`

`line_profiler` is the line-level deterministic profiler. Originally Robert Kern (2008), now maintained by the pyutils team (2022+). `kernprof` is the launcher.

- **`line_profiler` repository:** <https://github.com/pyutils/line_profiler>
- **`line_profiler` README** — install (`pip install line_profiler`), the `@profile` decorator (injected at runtime by `kernprof`, *not* an import from anywhere — a common confusion), `kernprof -l script.py` to record, `python -m line_profiler script.py.lprof` to print, or `kernprof -l -v script.py` to do both. <https://github.com/pyutils/line_profiler/blob/main/README.rst>.
- **`line_profiler` API reference (programmatic use):** the `LineProfiler` class; `lp.add_function(fn)`; `lp.enable() / lp.disable()`; `lp.print_stats()`. Used in tests and for ad-hoc scripted profiling.
- **PyPI:** <https://pypi.org/project/line-profiler/>.

## `py-spy` — sampling profiler, no target modification

py-spy is the production tool. Ben Frederickson 2018; Rust; reads Python stacks from outside the interpreter.

- **`py-spy` repository:** <https://github.com/benfred/py-spy>
- **`py-spy` README** — install (`pip install py-spy`; `cargo install py-spy`; `brew install py-spy`), subcommands (`record`, `top`, `dump`), the security model. *Read this end-to-end before Wednesday's lecture; it is short and excellent.* <https://github.com/benfred/py-spy/blob/master/README.md>.
- **`py-spy record` reference:** sampling rate (`--rate`), duration (`--duration`), output format (`--format flamegraph|speedscope|raw`), idle stacks (`--idle`), native stacks (`--native`), subprocess tracing (`--subprocesses`).
- **`py-spy top` reference:** the live `top`-style triage view; `--rate` controls refresh.
- **`py-spy dump` reference:** one-shot stack dump of every Python thread in a target process; the right tool for "the script is stuck, where is it stuck."
- **Ben Frederickson's 2018 launch post:** <https://www.benfrederickson.com/profiling-native-python-extensions-with-py-spy/>. The motivation and architecture, from the author.
- **PyPI:** <https://pypi.org/project/py-spy/>.
- **The "FAQ" in the README** specifically covers Linux's `ptrace_scope=1` requirement and macOS code-signing. Read this before you debug a permission denial.

## `scalene` — CPU + memory + GPU profiler, sampling

scalene is the right tool when "is this CPU- or memory-bound" is the actual question.

- **`scalene` repository:** <https://github.com/plasma-umass/scalene>
- **`scalene` README** — install (`pip install scalene`), usage (`scalene script.py`; `scalene --cli script.py` for non-Jupyter; `python -m scalene script.py`), output (web report by default, `--cli` for terminal, `--profile-only foo,bar` to filter). <https://github.com/plasma-umass/scalene/blob/master/README.md>.
- **Berger, Stern, Altmayer Pizzorno — PLDI 2023 paper "Triangulating Python Performance Issues with Scalene":** <https://dl.acm.org/doi/10.1145/3591260>. The peer-reviewed publication. Explains *why* the three-column (native / Python / system) decomposition matters, with measured case studies. ~25 minutes.
- **scalene's `--memory` mode:** the `libscaleneallocator.so` injection (Linux/macOS) that replaces `malloc` with a sampling-instrumented variant. Attributes allocations to source lines.
- **scalene's `--gpu` mode:** CUDA only; outside this week's scope.
- **PyPI:** <https://pypi.org/project/scalene/>.

## Flamegraphs — Brendan Gregg

The visualisation that organises everything.

- **Brendan Gregg, "Flame Graphs" — the canonical write-up:** <https://www.brendangregg.com/flamegraphs.html>. The 2011 invention, the rationale, the SVG layout, the "icicle" variant, diff flamegraphs. *Read this — all of it — before Wednesday.*
- **Brendan Gregg, "Flame Graphs for CPU Profiling" (LinuxCon NA 2017 keynote):** <https://www.brendangregg.com/Slides/LinuxCon2017_FlameGraphs.pdf> (slides). The talk version of the above.
- **The `FlameGraph` toolkit (`flamegraph.pl`):** <https://github.com/brendangregg/FlameGraph>. The original Perl renderer. Used out-of-the-box by `perf` and a hundred other profilers. Python tools (`py-spy`, `scalene`) ship their own SVG renderer but produce stacks that `flamegraph.pl` will also render — handy if you want a consistent visual style across languages.
- **Speedscope** (an alternative interactive flamegraph viewer, JS, browser-based; py-spy can output speedscope JSON via `--format speedscope`): <https://www.speedscope.app/>.

## Adjacent tools (cited; not required)

- **`yappi`** — async-aware deterministic + statistical profiler. Better than `cProfile` for asyncio code because it understands `Task` switches. <https://github.com/sumerc/yappi>.
- **`austin`** — frame-stack sampler, similar approach to py-spy, written in C, very low overhead, particularly strong on Linux. <https://github.com/P403n1x87/austin>.
- **`memray`** (Bloomberg) — the production-grade memory tracker. Tracks every allocation (not sampled), produces flamegraphs of allocation sites, lower noise than `tracemalloc`. The right tool for a serious memory-leak hunt. <https://github.com/bloomberg/memray>.
- **`snakeviz`** — browser visualiser for `cProfile` `.pstats` output. Renders an interactive icicle chart. <https://jiffyclub.github.io/snakeviz/>.
- **`flameprof`** — alternative flamegraph renderer for `cProfile` output. <https://github.com/baverman/flameprof>.
- **`pyinstrument`** — sampling profiler with a call-tree output rather than flamegraph; very ergonomic for "stick this in a Flask request handler." <https://github.com/joerick/pyinstrument>.
- **`viztracer`** — full execution trace + Chrome-DevTools-style visualiser. The "what happened when" complement to flamegraphs. <https://github.com/gaogaotiantian/viztracer>.

These are cited so you know they exist. **The week's required tools are `cProfile`, `line_profiler`, `py-spy`, `scalene`.** Add `tracemalloc` (stdlib) if you need allocation tracking and prefer not to install scalene's allocator.

## Background reading — the canon

- **Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd ed. (Pearson, 2020).** Chapter 6 (CPUs) is the foundational chapter. §6.5 (Profiling) is what we map to Python. Not free, but the *blog* covers ~80% of the same material: <https://www.brendangregg.com/>.
- **Donald Knuth, *Structured Programming with `go to` Statements* (Computing Surveys, 1974).** The source of "premature optimisation is the root of all evil." Read the surrounding paragraphs, not the quote: Knuth's actual point was that *measured* optimisation of the *3% that matters* is essential and that engineers should "look at that critical code; but only after that code has been identified." This entire week is the operationalisation of that paragraph.
- **John Ousterhout, "Always Measure One Level Deeper" (CACM 2018):** <https://cacm.acm.org/magazines/2018/7/229049-always-measure-one-level-deeper/fulltext>. The thesis: surface metrics lie; you need to instrument the sub-component to know the answer. The article is short and shapes how you think about *what* to instrument before *how* to instrument.
- **Emery Berger's PyCon 2022 talk "Scalene: A High-Performance CPU+GPU+Memory Profiler for Python":** <https://www.youtube.com/results?search_query=emery+berger+scalene+pycon+2022>. The 40-minute case for the three-column decomposition, with a live demo of finding a 100x speedup. Free.
- **Anthony Shaw's *CPython Internals* (Real Python, 2021), Chapter 8 "Parallelism and Concurrency", §"Profiling":** practitioner-grade walkthrough of `cProfile` and `dtrace`. Not free, but the *Real Python* free articles cover the same ground: <https://realpython.com/python-profiling/>.
- **Itamar Turner-Trauring's "Profile your Python code with cProfile and snakeviz":** <https://pythonspeed.com/articles/blocking-cpu-or-io/>. Short, practical, free. The author runs <https://pythonspeed.com/> which is the modern home of pragmatic Python performance writing.
- **Sam Stern, "Scalene: a high-performance Python profiler with AI-powered optimisations" (UMass blog 2023):** <https://github.com/plasma-umass/scalene/blob/master/docs/blog.md>. The motivation post.
- **Julia Evans, *Profiling and tracing with `perf`:* <https://jvns.ca/blog/2017/07/04/linux-tracing-systems/>. OS-level context for why language-level profilers cannot tell you everything.

## Optional installs (all pip-installable, all free)

| Tool | Install | Used in |
|------|---------|---------|
| `cProfile`, `pstats` (stdlib) | (built-in) | Lecture 2; Exercise 1; mini-project |
| `line_profiler` | `pip install line_profiler` | Lecture 2; Exercise 2; mini-project |
| `py-spy` | `pip install py-spy` | Lecture 3; Exercise 3; mini-project |
| `scalene` | `pip install scalene` | Lecture 3; Challenge 2; mini-project |
| `tracemalloc` (stdlib) | (built-in) | Challenge 2 (as a stdlib alternative to scalene's memory mode) |
| `snakeviz` | `pip install snakeviz` (optional) | Mini-project (alternative cProfile viewer) |
| `pytest` | `pip install pytest` | Homework |
| `pyinstrument` | `pip install pyinstrument` (optional) | Mentioned only |

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `cProfile.Profile` (the Python wrapper) | `Lib/cProfile.py` — `class Profile(_lsprof.Profiler)` |
| `cProfile.run`, `cProfile.runctx` | `Lib/cProfile.py` — top of file |
| `pstats.Stats.sort_stats` (sort keys) | `Lib/pstats.py:Stats.sort_stats` |
| `pstats.Stats.strip_dirs` (filename cleanup) | `Lib/pstats.py:Stats.strip_dirs` |
| `_lsprof` C profiler entry | `Modules/_lsprof.c` — `Profiler_*` functions |
| `_lsprof` per-call timing logic | `Modules/_lsprof.c` — `ptrace_enter_call` and friends |
| `sys.setprofile` registration | `Python/sysmodule.c` — `sys_setprofile` |
| `sys.monitoring` C implementation | `Python/instrumentation.c` |
| `tracemalloc` Python wrapper | `Lib/tracemalloc.py` |
| `tracemalloc` C core | `Modules/_tracemalloc.c` |
| `time.perf_counter` (high-res monotonic) | `Modules/timemodule.c` — `time_perf_counter` |
| `time.process_time` (CPU clock) | `Modules/timemodule.c` — `time_process_time` |

## Glossary

| Term | Definition |
|------|------------|
| **Profiling** | Measuring where time (or memory, or allocations, or syscalls) goes during a program's execution. Distinct from **benchmarking**, which measures end-to-end performance, and from **tracing**, which records every event. |
| **Deterministic profiling** | Instrumentation-based: every function entry and exit (or every line, etc.) is intercepted and timed. Exact for the trace collected; biased toward call-heavy code; overhead 20–40% typical. Examples: `cProfile`, `line_profiler`, `coverage.py`. |
| **Statistical profiling / Sampling profiling** | Interrupt-based: at a fixed rate (often 100 Hz), the current stack is recorded. Statistical estimate, not exact; overhead proportional to sample rate × work-per-sample, independent of call density; typical 1–3% at 100 Hz. Examples: `py-spy`, `scalene`, `perf`, `austin`. |
| **Wall-clock time** | Real-world elapsed time. `time.perf_counter()`. Includes time the process spent waiting (IO, locks, sleep). |
| **CPU time** | Time the process spent on a CPU. `time.process_time()`. Excludes sleep, IO wait, lock wait. Sum of user-mode and kernel-mode CPU time. |
| **On-CPU time** | Subset of wall-clock: the program was scheduled on a CPU. Equivalent to CPU time for single-threaded programs. |
| **Off-CPU time** | Wall-clock minus on-CPU. The program was waiting (IO, lock, sleep). Sampling profilers like py-spy can report this via `--idle`. |
| **`tottime` (cProfile)** | **Exclusive** time: time spent inside the function itself, excluding time spent in callees. The right column to sort by for "what is slow." |
| **`cumtime` (cProfile)** | **Inclusive** time: time spent inside the function *and* all functions it called. The wrong column to sort by for "what is slow" — `<module>` will always win. The right column to ask "what's the most expensive call path." |
| **`ncalls` (cProfile)** | Number of calls. Two numbers (e.g. `1234/100`) means "1234 calls, 100 of them top-level recursion entries." |
| **`percall` (cProfile)** | `tottime / ncalls` or `cumtime / ncalls` — per-call cost. The two columns named `percall` in the cProfile output refer to the column to their left. |
| **`@profile` (line_profiler)** | A decorator *injected at runtime* by `kernprof` — *not* an import. Inside a script being measured by `kernprof`, `@profile` is a free name; outside, it raises `NameError`. The common gotcha. |
| **`kernprof`** | The `line_profiler` launcher. `kernprof -l script.py` runs the script with line profiling enabled and writes `script.py.lprof`. The `-v` flag also prints the report. |
| **Flamegraph** | Brendan Gregg 2011. A stacked horizontal chart of sampled stacks. X-axis = sample count (not time); width = how often that stack appeared; height = stack depth. Sorted alphabetically left-to-right. The widest plateau at the top of a tower is the hot leaf. |
| **Icicle graph** | An inverted flamegraph: stacks point downward from the root at the top. py-spy's `--inverted` flag; the default in some viewers. |
| **Diff flamegraph** | Two flamegraphs subtracted: red bars are frames that got slower, blue bars are frames that got faster. Used for before/after comparisons of an optimisation. |
| **Speedscope** | An interactive flamegraph viewer in the browser; py-spy can output speedscope-format JSON. Useful for sharing with people who do not have py-spy installed. |
| **Heisenberg problem** | Observing perturbs the observed. In Python profiling: instrumentation slows function calls more than function bodies, biasing the profile toward call-heavy code. Mitigation: report relative costs within a single profile, not absolute times across runs. |
| **Hot leaf** | The function at the top of a hot stack — the place actually doing the work. Distinct from the **hot path**, which is how you got there. |
| **Hot path** | The chain of callers leading to a hot leaf. The fix is sometimes at the leaf, sometimes at a caller (e.g. "stop calling this so often"). |
| **PEP 657** | Fine-grained tracebacks (3.11). Adds column-level position to code objects. Profilers in 3.11+ can pinpoint *which expression on a line* rather than just the line. |
| **PEP 669** | `sys.monitoring` (3.12). Low-overhead, multi-tool monitoring API. The replacement for `sys.setprofile` and `sys.settrace`. The substrate of next-generation profilers. |
| **`sys.setprofile`** | The legacy interpreter callback that `cProfile` uses. One callback per process; per-call invocation; overhead ~30%. |
| **`sys.monitoring`** | The PEP 669 replacement. Multi-tool capable; per-event opt-in; overhead can be near-zero for events you do not register for. |
| **`process_vm_readv` (Linux) / `vm_read` (macOS)** | The syscalls py-spy uses to read another process's memory. The reason py-spy does not have to inject anything into the target. |
| **`ptrace_scope`** | Linux kernel setting controlling who can attach to whom. `0` = anyone with the same UID; `1` = parent and `sudo` only; `2` = `sudo` only. py-spy hits this. |

---

*Broken link? Open an issue.*
