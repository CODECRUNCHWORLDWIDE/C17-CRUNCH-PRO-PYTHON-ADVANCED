# Lecture 3 — `py-spy` and `scalene` for Production and Memory

> **Duration:** ~2 hours. **Outcome:** You can attach `py-spy` to a running Python process in ten seconds, produce a flamegraph, and read it without consulting the docs; you can run `scalene` and interpret the native/Python/system breakdown; you can name the failure mode each tool addresses that the deterministic profilers from Lecture 2 cannot; you have an opinion, defended with citations, on when to reach for each of the four tools.

## 1. The plan

Lecture 2 covered the deterministic profilers that ship with (or near) the standard library. They are excellent at one thing: telling you where time goes in a CPU-dominated local workload that you can run end-to-end with the profiler attached. They are bad at three things: (1) measuring a production process you cannot restart, (2) distinguishing pure-Python time from C-extension time, (3) telling you anything at all about memory. This lecture is the rest of the toolkit.

`py-spy` (Ben Frederickson, 2018) is a sampling profiler that runs *outside* the target process. It does not require you to import anything, decorate anything, or change how the target was launched. You hand it a PID and it reads stacks across the address-space boundary. Use it whenever you would otherwise have to restart the target, which is most of the time in production.

`scalene` (PLASMA Lab, UMass Amherst — Berger, Stern, Altmayer Pizzorno, 2020+) is a sampling profiler that adds three things `py-spy` does not: per-line attribution, a native/Python/system time breakdown, and memory-allocation sampling. Use it when "is this CPU-bound or memory-bound" or "is the time in my Python or in the C library it calls" is the open question.

Flamegraphs (Brendan Gregg, 2011) are the visualisation that organises the output of either tool — and the output of every other sampling profiler across every language and OS. They are not specific to Python. The mental model transfers; learn it once and you can read profiles from `perf` and `dtrace` and Java Flight Recorder unchanged.

By the end of the lecture you have run both tools and read at least one flamegraph generated from each.

## 2. `py-spy` — install, sanity check

```bash
pip install py-spy
```

`py-spy` ships as a self-contained Rust binary wrapped in a wheel. There is no source build unless you ask for one (`cargo install py-spy` builds from source). After install, `py-spy --version` confirms it.

The most useful invocation is the live `top`:

```bash
py-spy top --pid PID
```

This opens a `top(1)`-style live view of the target process's Python stacks. Refreshes ~once per second; shows the busiest functions by sample count, alongside their share of the wall clock. Excellent for "the script is running and seems slow; let me look." Press `q` to exit.

The other two subcommands:

```bash
py-spy record -o flame.svg --pid PID --duration 30
py-spy dump --pid PID
```

`record` samples the process for `--duration` seconds (default 60) and writes a flamegraph SVG. `dump` takes one stack snapshot of every Python thread in the target process — useful for "is this script stuck? where?" (Far cheaper than starting a sampler when you just need one stack.)

## 3. The security model

Reading another process's memory is a privileged operation on every modern OS. py-spy hits this immediately.

**Linux** uses `process_vm_readv` (a syscall introduced in kernel 3.2) gated by `ptrace_scope`:

- `ptrace_scope=0`: any process with the same UID can attach. Permissive; rare in modern distros.
- `ptrace_scope=1` (the default on Ubuntu, Fedora, most modern Linux): a process can only attach to its own descendants, or anyone if `sudo`. **This is the default; most py-spy "permission denied" errors are this.**
- `ptrace_scope=2`: only `sudo` can attach to anything.
- `ptrace_scope=3`: ptrace disabled entirely. Rare; security-hardened systems.

To check: `cat /proc/sys/kernel/yama/ptrace_scope`. To temporarily lower (for the current boot): `sudo sysctl kernel.yama.ptrace_scope=0`. To make permanent: edit `/etc/sysctl.d/10-ptrace.conf`. **Do not lower `ptrace_scope` on a shared production box without your security team.**

The pragmatic workaround on a developer laptop or single-tenant prod box: `sudo py-spy top --pid PID`. The pragmatic workaround in a managed environment: install py-spy in the container that owns the target process, and run `py-spy top --pid 1` (or whatever PID 1 is in the container).

**macOS** requires either `sudo` or that the py-spy binary be code-signed with `task_for_pid` entitlement. The pip-installed wheel is *not* signed, so you will use `sudo`. The macOS error message ("could not get information from process") is not informative; if you see it on macOS, try `sudo` and the issue evaporates.

**Windows** has no equivalent restriction; py-spy works without `sudo` against any process the user owns.

## 4. `py-spy record` — the flamegraph

```bash
py-spy record -o flame.svg --pid 12345 --duration 30
```

After 30 seconds (or `Ctrl-C` for early stop) you have an SVG. Open it in a browser. The interactivity is built into the SVG: hover over a bar to see the frame name and sample count; click a bar to zoom in; the search bar (top-right) highlights frames by substring.

The structure of the flamegraph (Lecture 1 §11 had the concept; now the picture):

- **X-axis = sample count.** Wider bars are more samples (more time on the stack). The full width is the total number of samples. **The x-axis is *not* time-ordered.** Sampling order is ignored; bars at the same depth are sorted alphabetically by frame name.
- **Y-axis = stack depth.** The root frame is at the bottom; deeper calls stack upward. Each tower represents one or more samples that shared a stack prefix.
- **Wide plateaus at the top = hot leaves.** A wide bar at the highest depth of a tower is "this function was on the CPU for many samples." This is where the work is.
- **Tall, narrow towers = deep call chains.** Sometimes meaningful (recursion, deep middleware); sometimes just noise.
- **Wide bases, narrow tops = diffusion.** Your time is spread thinly across many short calls. There is no one hot leaf; the fix is structural (rearchitect the call shape) rather than local (rewrite one function).

The flamegraph viewer's "Find" feature is more useful than people realise. Type a function name and every occurrence highlights — useful for "how much time across the whole program does anything called `parse` take." That total is the *sum of the highlighted widths*, which the SVG can compute for you.

## 5. `py-spy` flags worth knowing

```bash
py-spy record -o flame.svg --pid PID --duration 60 --rate 250 --idle --subprocesses --threads
```

- `--rate N` — samples per second. Default 100. Increase for short captures of fast functions; decrease for long captures or low-overhead production attaches.
- `--duration N` — capture length in seconds. Defaults to 60. Captures stop on Ctrl-C or after the duration.
- `--idle` — include stacks that were not on a CPU. Without `--idle`, time spent in `time.sleep` or blocked on IO is invisible. With `--idle`, those stacks appear, marked. **Essential when diagnosing "the script seems to do nothing" — you need to see the sleep.**
- `--subprocesses` — also sample child processes. The default samples only the PID you named. Useful for `multiprocessing.Pool`-shaped programs.
- `--threads` — show each thread separately in the flamegraph (interleaved bars). Default merges threads. For multi-threaded code, the per-thread view is much more readable.
- `--native` — also sample C extension frames. Requires building py-spy with Rust toolchain (or installing the `py-spy[native]` extra). When available, the flamegraph shows C frames in a different colour. **The right flag when your bottleneck is inside a C extension and `cProfile` couldn't see it.**
- `--format {flamegraph,speedscope,raw}` — output format. `flamegraph` (default) is the SVG. `speedscope` is JSON for the browser tool at <https://www.speedscope.app/>. `raw` is the underlying stack samples, one per line, in `flamegraph.pl` format.
- `--nonblocking` — sample without pausing the target. Slightly less accurate (small chance of inconsistent stack reads) but does not stop the target even briefly. Use in latency-sensitive production. The default pauses the target for ~10 microseconds per sample.

## 6. `py-spy dump` — one-shot stack snapshot

For "is this script stuck, and if so, where" — there is no need for a 30-second sample. One stack is enough.

```bash
py-spy dump --pid PID
```

Output:

```
Process 12345: python script.py
Python v3.13.0 (/usr/bin/python3.13)

Thread 0x7f8a1c4d5740 (active)
  File "script.py", line 42, in process_records
    out = transform(r)
  File "script.py", line 18, in transform
    parts.append(format_field(record, k))
  File "script.py", line 6, in format_field
    return f"{k}={record[k]}"

Thread 0x7f8a1c1cd700 (idle)
  File "/usr/lib/python3.13/threading.py", line 1234, in wait
    waiter.acquire()
```

This is gold for "the script has been running 20 minutes; what is it doing?" — one command, one stack per thread, no need to disrupt the target. Try this before reaching for `record`.

## 7. `py-spy` vs. `cProfile` on the same workload

Run a script with `python -m cProfile -s tottime script.py` and `py-spy record -o flame.svg --pid $(pgrep -f script.py) --duration 30` in parallel terminals. Compare.

Things that will agree:

- The hottest function (within statistical noise from py-spy).
- The hot path (the chain of callers).
- The relative order of the top ~5 functions.

Things that will differ:

- **`cProfile`'s call counts are exact**; py-spy's are not directly comparable (py-spy doesn't count calls, it counts samples). If you need "this function was called 1,234,567 times," cProfile.
- **py-spy sees C frames (with `--native`)** that cProfile cannot. If a Python wrapper calls a slow C function, cProfile blames the Python wrapper; `py-spy --native` shows the C frame doing the work.
- **py-spy can see idle time (with `--idle`)**; cProfile reports wall-clock for the Python call but doesn't decompose it. If you need to know "is this slow because of sleep," py-spy with `--idle`.
- **py-spy is safe to run for hours**; cProfile's trace buffer grows with every call. cProfile is appropriate for finite, scriptable workloads; py-spy for long-lived services.

Pick the tool that matches the question. Both, sometimes; that's a fine workflow.

## 8. `scalene` — install, sanity check

```bash
pip install scalene
```

scalene also ships wheels with prebuilt native components (`libscaleneallocator.so` on Linux/macOS for the memory mode). On install, `scalene --version` confirms.

The simplest invocation:

```bash
scalene script.py
```

By default scalene opens a web report in your browser when the script finishes. For a terminal report (CI, headless servers):

```bash
scalene --cli script.py
```

For "just the program output, then the report at the end":

```bash
scalene --cli --html script.py        # write HTML to scalene-report.html
scalene --cli --json script.py        # write JSON to scalene-report.json
```

scalene profiles by default; no decorators required, no code changes.

## 9. The scalene output, line by line

The `--cli` report is a table per file with one row per line. The columns (in order):

| Column | Meaning |
|--------|---------|
| **Time %** — Python | Wall-clock percentage spent executing Python bytecode at this line. |
| **Time %** — native | Wall-clock percentage spent in C-extension code called from this line. |
| **Time %** — system | Wall-clock percentage spent in syscalls (read, write, sleep, lock acquire) at this line. |
| **Mem %** | Memory allocations attributed to this line as a percentage of total allocations. Only present with `--memory` (which is on by default in 1.5+). |
| **Mem Avg / Peak** | Average and peak resident set attributed. |
| **Copy MB/s** | Memory copy bandwidth at this line (useful for "is this `.copy()` actually expensive"). |
| **GPU** | (CUDA only; ignore for this curriculum.) |
| **Line** | Source code. |

The single most valuable thing scalene tells you that no other tool does: **the split between Python time and native time on a single line.** A line like `result = pandas.read_csv("data.csv")` will report 0.1% Python time and 98% native time — the wrapper is essentially free; the C parser is the work. A line like `result = sum(x**2 for x in xs)` will report 98% Python time and 0% native time — the work is in the bytecode loop. The right fix is different for each: for the former, you cannot speed it up by rewriting Python (move to pyarrow, batch larger, or do less); for the latter, the rewrite candidate is "use `numpy.sum` over a vectorised array" — push the work to C.

The memory column is the second valuable thing. Set `--memory` (default in 1.5+); the column shows allocations per line. A line like `intermediate = [transform(x) for x in xs]` might report 200 MB of allocations — and the fix is to use a generator (yields one transformed item at a time) instead of materialising the list.

## 10. The scalene web report

If you do not pass `--cli`, scalene opens a browser tab. The web report is the same data with three improvements: (1) a sortable table; (2) optional AI suggestions (deprecated and removed in newer versions — ignore); (3) per-line graphs over time, which are excellent for catching the "a long loop slowed down halfway through" pattern. For a one-shot profile read, the `--cli` output is faster; for an investigation, the web report is better.

## 11. Choosing between `py-spy` and `scalene`

Both are sampling profilers; both produce per-line attribution; both are production-safe (with caveats). When do you reach for which?

| Symptom / question | Tool |
|--------------------|------|
| "The production service is stuck and I cannot restart it." | `py-spy dump --pid PID` |
| "The production service is slow and I can attach but not modify." | `py-spy record --pid PID` |
| "Local workload is slow; I want a flamegraph." | `py-spy record` (after starting the script in another terminal) |
| "Is the bottleneck in my Python code or in the C library it calls?" | `scalene` |
| "Is the bottleneck CPU or memory?" | `scalene --memory` |
| "Which line is allocating 200 MB?" | `scalene --memory` (or `tracemalloc` if scalene unavailable) |
| "I need a snapshot of every thread's stack in a stuck process." | `py-spy dump` |
| "I have a Jupyter notebook." | `scalene` (it has special-cased notebook support; `%scalene` cell magic) |
| "Asyncio event loop slowness." | `py-spy` (handles native frames; can see the loop's `select` call) |

scalene cannot attach to a running process. It must be launched as `scalene script.py`. py-spy *can* attach. This is the most important practical difference; it determines tool choice in production.

Conversely, py-spy cannot tell you Python-vs-native time without `--native` (which requires a build with Rust toolchain), and py-spy cannot tell you anything about memory allocations. scalene's two strongest features are exactly those.

In a typical 2026 workflow: scalene on the laptop, py-spy in production. The lecture sequence reflects this: you use py-spy when you cannot restart the target; you use scalene when you can.

## 12. Reading a flamegraph — the discipline

A flamegraph is the densest representation of a profile available. A 30-second sampling profile at 100 Hz is 3000 stacks; a flamegraph is one image. The discipline of reading it well repays itself many times over.

Five rules:

1. **Look at the top, not the bottom.** The bottom of every tower is your script's entry point; everything goes through there. The interesting work is at the *top* — the leaves doing the actual computation. Wide bars at the top = hot leaves.

2. **A wide plateau is the hot leaf.** If you see a plateau the same width as some part of its tower, that frame *is* doing the work. If you see a plateau much narrower than its tower, that frame is delegating most of its time to callees.

3. **Hover and search are not optional.** SVG flamegraphs are interactive: hover over a bar to see exact sample counts; use the search box (top-right) to highlight all frames matching a string. The `% on stack` and `% by self` reported on hover are the cumulative and exclusive equivalents from cProfile, computed from samples.

4. **Read alphabetically, not chronologically.** A flamegraph does *not* show time order. Two adjacent bars at the same depth are not adjacent in time — they are adjacent in alphabetical order. The bar at the right of a wide plateau is not "what happened next"; it is "the alphabetically next-named frame that was also on the stack a similar amount."

5. **Compare two flamegraphs by overlaying them.** Brendan Gregg's *diff flamegraphs* (red = slower, blue = faster) are produced by subtracting two stack-sample sets. Use this for before/after comparisons. The `difffolded.pl` tool in <https://github.com/brendangregg/FlameGraph> does the math; py-spy can also write its raw output in flamegraph.pl-compatible format (`--format raw`) so you can feed two raw files into difffolded.

Two patterns to recognise on sight:

**Diffusion.** A wide, flat base; many thin towers; no clear hot leaf. Your time is spread across hundreds of short calls. Localised optimisation will not help; you need to restructure (batch the work, cache the results, change the algorithm).

**A tall tower with a small hot leaf at the top.** Your bottleneck is a deep call chain ending in a small function. The fix is usually at one of the intermediate layers — "stop calling this so often" rather than "make this faster." Look at the layer where the width starts narrowing; that is where caching helps.

## 13. The decision table for the four tools

A summary you commit to memory.

| Symptom | Tool | Why |
|---------|------|-----|
| Local CPU workload, "where's the time going" | `cProfile` | Function-level, exact, no install. |
| Within hot function, which line | `line_profiler` | Per-line, deterministic. |
| Production stall, cannot restart | `py-spy dump` | One stack snapshot, no target modification. |
| Production stall, want flamegraph | `py-spy record` | Sampling, ~1% overhead. |
| Local CPU workload, Python vs. C question | `scalene` | Per-line split into native/Python time. |
| Memory leak or memory pressure | `scalene --memory` | Per-line allocations. |
| Async event loop slowness | `py-spy` (or `yappi`) | py-spy sees the loop's syscalls. |
| Web app hot endpoint | `py-spy record --subprocesses` | Sample the gunicorn workers. |

When you do not have an opinion, **cProfile first, py-spy second, scalene third, line_profiler fourth**. The order tracks the cost of pulling out the tool: cProfile is one CLI flag, py-spy is one `pip install`, scalene is the same plus a slightly more elaborate UI, line_profiler requires a code change.

## 14. PEP 669 and the future

`sys.monitoring` (PEP 669, Mark Shannon, 2022; landed 3.12) is the modern replacement for `sys.setprofile`. The motivation: `sys.setprofile` had one callback per process and was always-on for every event, so two profilers in the same process collided and the overhead was significant. `sys.monitoring` supports up to 6 simultaneous "tool IDs," lets each tool register only for the events it cares about, and emits events through a much faster path.

The PEP is worth reading (~40 minutes) for the architectural improvements. The practical implication for this week's tools:

- `cProfile` is in the process of being ported to `sys.monitoring` (CPython issue #103615 and follow-ups). The default `cProfile` will use the new API in 3.14 if not earlier. Same API, lower overhead.
- `py-spy` 0.4+ optionally uses `sys.monitoring` when available, but its primary mode remains out-of-process sampling. The `sys.monitoring` mode is for in-process bursts of higher-resolution sampling.
- `scalene` already uses `sys.monitoring` on 3.12+ where available. The PLDI 2023 paper describes the earlier `setprofile`-based design; recent versions have been quietly upgraded.
- `coverage.py` 7.4+ uses `sys.monitoring` and is dramatically faster than the `settrace`-based predecessor.

If you are choosing a profiler in 2026, you do not need to think about PEP 669 explicitly — the tools handle it. If you are *building* a profiler, you read the PEP and use the new API.

## 15. `tracemalloc` — the stdlib memory profiler

scalene's memory mode is the best memory profiler we have, but it requires an extra install. `tracemalloc` (3.4+, stdlib) is the fallback.

```python
import tracemalloc

tracemalloc.start(25)  # capture up to 25 frames per allocation

# ... run the workload ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)
```

Each entry in `top_stats` is a `tracemalloc.Statistic` with `size`, `count`, and `traceback` attributes. The `lineno` key aggregates by source line; alternatives are `"filename"`, `"traceback"`. The `tracemalloc.Snapshot.compare_to(other_snapshot, "lineno")` method is how you find leaks: take a snapshot, run the workload, take another, compare. The lines whose `size_diff` is positive are the ones allocating without freeing.

`tracemalloc` is slower than scalene (it traces every allocation, not samples) and noisier (the trace includes the tracemalloc machinery itself), but it is in the standard library. Use it when scalene is unavailable; switch to scalene when you can.

## 16. `memray` — the production memory tool

Out of scope but worth citing: `memray` (Bloomberg, 2022) is the production memory profiler. Tracks every allocation, lower overhead than `tracemalloc`, flamegraph output, attaches to running processes. The right tool for a serious memory-leak hunt that scalene's sampling cannot pinpoint. <https://github.com/bloomberg/memray>.

We do not cover memray in depth this week; the curriculum's memory deep-dive is C17's Week 2 (refcounting and the cycle GC) and any further memory work goes through scalene's allocation column for sampling and tracemalloc/memray for exact tracking.

## 17. Worked example: attaching py-spy to a long-running script

Terminal 1:

```bash
python long_running_script.py
```

The script prints nothing for 30+ seconds.

Terminal 2:

```bash
# Get the PID.
pgrep -f long_running_script.py
# Or use top/ps to find it.

# Quick: what is it doing right now?
py-spy dump --pid 12345

# Better: 30 seconds of sampling.
py-spy record -o long.svg --pid 12345 --duration 30
```

Open `long.svg`. The hot leaf is `compute_signature` (made up). Click; you see the call path that led there: `main` → `process_all` → `process_one` → `compute_signature`. The `compute_signature` plateau is 78% of samples.

Now, the question that distinguishes a profile from a fix: **is `compute_signature` actually expensive, or am I just calling it too often?** Look at the next level up: how wide is `process_one` (the caller)? If `process_one` is also ~78% wide, the program spends almost all its time inside `compute_signature` and the fix is at the leaf. If `process_one` is wider than `compute_signature` (other leaves at its level), then `compute_signature` is one of several things the loop does, and the leaf-level fix is still right. If `process_all` is 78% and `process_one` is much narrower, the fix is at `process_all` — probably "we are calling `process_one` more times than we should."

The flamegraph encodes both pieces of information in the same image: the *width* tells you cost; the *vertical stacking* tells you the call shape. Read both.

## 18. Production gotchas

- **`ptrace_scope=1` on most Linux distros.** Use `sudo` or lower the setting on a developer box; both fine. On production: install py-spy in the same container as the target if possible.
- **Containerised targets.** py-spy must run in the same PID namespace as the target. Easiest: `docker exec` into the container, install py-spy there, attach.
- **PID 1.** If your target *is* PID 1 (a common pattern for Docker containers running a single Python process), the PID is `1`. py-spy works fine against PID 1.
- **CPython binaries stripped of symbols.** py-spy needs symbols to find the interpreter state. The standard CPython binary has them; some custom builds (Alpine `apk` packages occasionally) do not. Symptom: "could not find a Python interpreter" or "could not determine Python version." Fix: install `python3.13-dbg` or rebuild with symbols.
- **Forking without `--subprocesses`.** A `multiprocessing.Pool` workload will appear to be doing nothing if you only attach to the parent. Use `--subprocesses`. Same for any `subprocess.Popen` shape.
- **scalene + threading.** scalene's memory and CPU sampling are per-thread but interpretation can be tricky for multi-threaded code. Recent versions (1.5+) handle it well; older versions could attribute samples to the wrong thread. Pin scalene >= 1.5 for threaded code.
- **scalene + multiprocessing.** scalene tracks the main process by default. Use `--profile-all` (or set `SCALENE_PROFILE_ALL=1`) to profile children too. Output is per-process.

## 19. Read for Mini-Project

Before Thursday's mini-project kickoff:

- The "Examples" section of the py-spy README (~5 minutes): <https://github.com/benfred/py-spy#examples>.
- The "Output" section of the scalene README (~5 minutes): <https://github.com/plasma-umass/scalene#output>.
- Brendan Gregg's flamegraph post one more time (~10 minutes), focusing on "Reading the Graph": <https://www.brendangregg.com/flamegraphs.html>.
- Pick a target. Skim the README of two or three candidate open-source Python projects you might profile: `flask`, `requests`, `markdown-it-py`, `pyflakes`, `bandit`, `httpx`, `pydantic` (v1), the test suite of any small library. Anything 1k–20k LOC with a representative workload you can drive. (Avoid pandas, numpy — too much C; the profile is uninteresting from Python's side.)

## 20. Summary

- `py-spy` is the production sampling profiler. No target modification. Attach by PID. Three subcommands: `top` (live), `record` (flamegraph SVG), `dump` (one-shot stack). Cite <https://github.com/benfred/py-spy>.
- Security: Linux `ptrace_scope=1` is the default; use `sudo` or lower the setting. macOS: `sudo`. Windows: works.
- Key flags: `--rate`, `--duration`, `--idle`, `--subprocesses`, `--threads`, `--native`, `--nonblocking`. Each opens up one class of measurement.
- `scalene` is the local sampling profiler with native/Python/system splits and memory tracking. Cannot attach to running processes. Cite <https://github.com/plasma-umass/scalene>.
- Flamegraphs (Brendan Gregg 2011): x = samples, y = stack depth, alphabetical not temporal. Wide leaves = hot leaves; tall thin towers = deep chains; flat bases = diffusion.
- The four-tool decision table: cProfile for local CPU; line_profiler for line-level; py-spy for production sampling and flamegraphs; scalene for Python-vs-native and memory. Always read both `tottime` and the flamegraph hot leaf; they should agree, and when they don't, the disagreement is informative.
- PEP 669 (`sys.monitoring`, 3.12+) is the modern profiling substrate; tools are migrating. As a user you get lower overhead; as a tool author you get composability.
- `tracemalloc` (stdlib) is the memory fallback when scalene is unavailable; `memray` (Bloomberg) is the production memory tool. Both are out-of-scope for this week's required toolkit but cited.
