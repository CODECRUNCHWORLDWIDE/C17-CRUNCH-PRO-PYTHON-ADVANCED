# Week 7 — Quiz

Ten questions. Lectures closed.

---

**Q1.** In a `cProfile` output, the function with the largest `cumtime` is:

- A) Always the function you should rewrite — it has the most wall-clock attributable to it.
- B) Almost never the function you should rewrite — it is usually an orchestrator whose `cumtime` is the sum of its descendants' costs. Sort by `tottime` to find the leaf doing actual work.
- C) Always `<built-in method builtins.exec>` because that's where Python starts.
- D) The function with the most call sites in the source code.

<details>
<summary>Answer</summary>

**B** — Sort by `tottime` to find the leaf; `cumtime` finds the orchestrator. Lecture 1 §11, Lecture 2 §§5, 7.

</details>

---

**Q2.** A sampling profiler at 100 Hz, run for 10 seconds, takes approximately how many samples?

- A) 100.
- B) 1,000.
- C) 100,000 — one per millisecond of work-time.
- D) Depends on how many function calls the program made; sampling profilers count calls.

<details>
<summary>Answer</summary>

**B** — 100 Hz × 10 s = 1,000 samples. Lecture 1 §3, Lecture 3 §5.

</details>

---

**Q3.** `time.perf_counter()` versus `time.process_time()`:

- A) Identical; the names are aliases.
- B) `perf_counter` is wall-clock (includes sleep, IO, lock wait); `process_time` is CPU time (excludes them). For "how long did the user wait" use `perf_counter`; for "how much CPU did this code use" use `process_time`.
- C) `process_time` is faster and should be used everywhere.
- D) `perf_counter` requires `sudo` on Linux; `process_time` does not.

<details>
<summary>Answer</summary>

**B** — wall vs. CPU clock. Lecture 1 §2.

</details>

---

**Q4.** A function `slow_fn` shows `tottime=0.05`, `cumtime=2.5` in a cProfile output for a 3-second run. The right interpretation is:

- A) `slow_fn` is the hot leaf — 0.05 seconds of work, 2.5 seconds wall.
- B) `slow_fn` is an orchestrator: it spent 0.05 seconds in its own body but 2.5 seconds in functions it called. Look at what it calls (`print_callees`) — that is where the time went.
- C) The profile is corrupt; `cumtime` cannot exceed `tottime`.
- D) `slow_fn` has a sleep call that accounts for 2.45 seconds.

<details>
<summary>Answer</summary>

**B** — high `cumtime`, low `tottime` is an orchestrator; the time went to callees. Lecture 1 §11, Lecture 2 §3.

</details>

---

**Q5.** `@profile` in a script being measured by `line_profiler` is:

- A) Imported from `line_profiler` at the top of the file: `from line_profiler import profile`.
- B) A decorator injected into the global namespace by `kernprof` when it runs the script. Running the script directly (without `kernprof`) raises `NameError`. The common workaround is a `try: profile except NameError: def profile(fn): return fn` shim at the top.
- C) A built-in available in all Python 3.11+ scripts.
- D) Synonymous with `cProfile.Profile()` and produces the same output.

<details>
<summary>Answer</summary>

**B** — `kernprof` injects the decorator at runtime; the shim makes scripts run with or without it. Lecture 2 §8.1.

</details>

---

**Q6.** `py-spy record -o flame.svg --pid 12345 --duration 30` will, on a default Ubuntu 24.04 box, often fail with permission denied because:

- A) py-spy is missing a Python plugin.
- B) Linux's `ptrace_scope=1` (the default) restricts cross-process memory reading to descendants of the calling process or `sudo`. Fix: run with `sudo`, or temporarily set `sysctl kernel.yama.ptrace_scope=0` on a development box.
- C) The flamegraph SVG renderer requires a graphical display.
- D) py-spy requires Python to be compiled with `--enable-profiling`.

<details>
<summary>Answer</summary>

**B** — `ptrace_scope=1` is the default; `sudo` or sysctl. Lecture 3 §3.

</details>

---

**Q7.** In a flamegraph, the x-axis represents:

- A) Wall-clock time, left to right.
- B) Sample count for each stack — a wider bar means the stack was on top in more samples. The bars are *not* in time order; they are sorted alphabetically by frame name.
- C) Call depth.
- D) Memory consumption per frame.

<details>
<summary>Answer</summary>

**B** — sample count, alphabetic. Lecture 3 §§4, 12.

</details>

---

**Q8.** `scalene` distinguishes "Python time" from "Native time" per line. The single most actionable use of that distinction is:

- A) It is mostly cosmetic; the totals are what matter.
- B) It tells you whether to rewrite the Python (Python time high → algorithm/data-structure change in Python) or to swap the library (Native time high → the wrapper is essentially free; replace the C library, batch larger, use a different one). The fix is different for each.
- C) It is required for `pip install` to work.
- D) It is the difference between bytecode and AST execution and applies only to interpreted code.

<details>
<summary>Answer</summary>

**B** — fix shape depends on column shape. Lecture 3 §§9, 13.

</details>

---

**Q9.** A workload runs in ~5 seconds. `cProfile` shows one function dominating `tottime`. `scalene` shows that function with 5% Python time and 80% allocations attributed to a `list()` constructor on a particular line. The right fix is:

- A) Rewrite the Python loop body in C.
- B) Eliminate the list materialisation — use a generator or in-place processing — because the workload is memory-bound, not CPU-bound. Faster Python in the loop body would not help when the loop is mostly allocator pressure.
- C) Use `multiprocessing.Pool` for parallelism.
- D) Increase `--rate` in py-spy.

<details>
<summary>Answer</summary>

**B** — memory-bound; generator/in-place. Challenge 2.

</details>

---

**Q10.** The heisenberg problem in profiling refers to:

- A) Python's threading model preventing accurate per-thread measurement.
- B) The fact that observation perturbs the observed: profilers slow their targets, and the slowdown is non-uniform (instrumentation profilers slow function-call-heavy code more than function-body-heavy code), biasing the profile. The mitigations: compare *ratios within a single profile* rather than absolute times across runs; use sampling when call density is high; sanity-check profile totals against unprofiled wall clock.
- C) A bug in `cProfile` that was fixed in 3.11.
- D) The garbage collector running during a profile.

<details>
<summary>Answer</summary>

**B** — observation perturbs; ratios within a run, not absolutes across. Lecture 1 §4.

</details>

---

## Self-reflection

If you got 9 or 10 right: you have the discipline. The mini-project will exercise it on a real codebase; expect it to be qualitatively harder, not quantitatively (the questions are the same, the answers come from a less-tame target).

If you got 7 or 8 right: the gap is usually in one of two places — the `tottime` vs. `cumtime` reflex (Q1, Q4) or the production-vs-local tool choice (Q6, Q8). Re-read the lecture sections cited above before Thursday.

If you got 6 or fewer right: re-read all three lectures. The exercises will not stick without the mental model the lectures build. The investment is ~4 hours; it returns many times over for the rest of the curriculum and your career.
