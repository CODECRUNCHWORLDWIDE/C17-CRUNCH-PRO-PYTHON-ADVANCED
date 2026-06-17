# Mini-Project — A 100-Line CPython Bytecode Tracer

> Build a real, reusable bytecode tracer. ≤100 lines of Python. Uses `sys.monitoring` (PEP 669) on 3.12+ with an optional `sys.settrace` fallback for older interpreters. Publish it on GitHub.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-03-bytecode-tracer-<yourhandle>` containing:

1. **`pytrace.py`** — the tracer itself. ≤100 non-blank, non-comment lines. Pure stdlib. Compiles on CPython 3.12+. Optional fallback path for 3.10/3.11 via `sys.settrace`.
2. **`pytrace_cli.py`** — a small CLI wrapper: `python -m pytrace_cli path/to/script.py [-- script-args...]` runs the script under the tracer and writes a trace to stdout (or to `--out file.txt`).
3. **`README.md`** — what it is, how to install (it's stdlib, so `python pytrace_cli.py` is the install), how to use it, example output, a paragraph on the design tradeoffs.
4. **`tests/test_pytrace.py`** — at least three tests covering:
   - Tracing a function with a nested call shows correct indentation.
   - Tracing the same function twice does not leak the tool id.
   - The trace records the same number of `PY_START` events as `PY_RETURN` events.
5. **`examples/`** — at least two short scripts whose trace is illuminating: one with a `for` loop (so `FOR_ITER` shows up), one with a recursive function (so depth indentation shows up).
6. **`design.md`** — 600–900 words on:
   - Why `sys.monitoring` and not `sys.settrace`.
   - What you chose to print and what you chose to omit (e.g., did you print stack effects? cache contents? line numbers?).
   - What you would add if you had another week.

## What the tracer must do

- **Trace every executed opcode** in the target callable and all Python callees it transitively invokes.
- **Show**, per opcode line: depth-indented `co_qualname`, byte offset, mnemonic, oparg.
- **Resolve oparg friendliness** at least minimally: for `LOAD_FAST` show the variable name (`code.co_varnames[oparg]`); for `LOAD_CONST` show the const repr (`code.co_consts[oparg]`); for `LOAD_GLOBAL` show the name (the high bit of oparg is the `pushnull` flag in 3.12+ — handle it). For other opcodes, the raw oparg integer is fine.
- **Emit a summary** at the end: total instructions, total frames entered, wall-clock elapsed, peak depth.
- **Be teardown-clean.** Two invocations in the same process must both work. No leaked tool id.
- **Skip C/builtin functions cleanly.** `sys.monitoring` only fires on Python-level code; the tracer must not crash when a C function is called from a Python frame.

## Acceptance criteria

- [ ] Repo public on GitHub at the URL above.
- [ ] `cloc pytrace.py` (or equivalent) reports ≤100 lines, blanks and comments excluded.
- [ ] `python tests/test_pytrace.py` (or `pytest`) passes on CPython 3.12 and 3.13.
- [ ] `python pytrace_cli.py examples/fib.py` produces a readable trace.
- [ ] `design.md` exists and explains the choices.
- [ ] README at the repo root is sufficient for a reviewer to install, run, and read the output without asking you.

## Suggested order of operations

### Phase 1 — Bones (90 min)

1. From Challenge 1, you already have a working ≤100-line draft. Start there. If you didn't do the challenge: do it now (90 min); then come here.
2. Move it into the new repo. Add the `tests/` directory.

### Phase 2 — Polish the trace (90 min)

3. Add oparg pretty-printing for `LOAD_FAST` / `LOAD_CONST` / `LOAD_GLOBAL`. Look up the relevant `code.co_*` attribute by opcode mnemonic. Use a small dict mapping mnemonic → resolver.
4. Add the summary line at the end: counts, peak depth, elapsed.
5. Verify total line count stays ≤100. If you overshoot, drop the prettiest-but-least-essential resolver until you fit.

### Phase 3 — CLI + tests (120 min)

6. Build `pytrace_cli.py`. It should `runpy.run_path(target, run_name="__main__")` under the tracer.
7. Write the three required tests. Use `subprocess.run([sys.executable, "pytrace_cli.py", "examples/fib.py"], ...)` for end-to-end coverage; use direct imports for unit coverage.

### Phase 4 — Documentation and publish (60 min)

8. Write the `design.md` thoughtfully. This is the artifact that survives the longest.
9. Push to GitHub. Verify the example output renders correctly in the rendered README.

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| `pytrace.py` ≤ 100 lines and clear | 25% | Reads top-to-bottom in one pass; no clever tricks needed |
| Correctness: depth, mnemonics, oparg, summary | 25% | Trace matches `dis.dis` instruction-by-instruction on the demo |
| Tests | 15% | All three required tests, plus one of your own |
| `design.md` is technically substantive | 20% | Cites PEP 669 by section, explains tradeoffs without hand-waving |
| README is reviewer-friendly | 10% | One-screen install + use; clear example |
| Optional: stretch features | 5% | See below |

## Stretch (optional, +5%)

Pick one:

- **Stack-effect column.** Use `dis.stack_effect(opcode, oparg)` to print +N / −N alongside each instruction. Useful for the reader to visualize the stack.
- **Specialization-aware output.** Print the *specialized* opcode name (the rewritten one) by reading directly from `code.co_code` at the offset. Compare to the static `dis.dis` (which shows un-specialized by default) and call out where they differ.
- **Trace filter.** A `--filter REGEX` flag that traces only frames whose `co_qualname` matches the regex.
- **Stack-content snapshot.** *Hard.* For a small set of opcodes (`LOAD_*`, `STORE_FAST`), inspect the running frame via `sys._getframe(0)` from inside the callback and pretty-print the top of stack. Requires careful handling of frame ownership; the tracer's own frame is not the target frame.
- **Replace `sys.monitoring` with `sys.settrace` as a fallback** for 3.10/3.11 and document the fidelity loss in `design.md`.

## Why this matters

A bytecode tracer is the kind of tool a senior Python engineer should be able to write in an afternoon when debugging a hard runtime problem. The ones in the wild (`hunter`, `Python-Trace`, `birdseye`) are larger and more featureful, but the **core** in each of them is exactly what you are building. After this project, you can read the source of any of those tools and recognize the shape.

This artifact is **public-facing**: it goes on your GitHub, it's reasonable to mention in a senior-role interview ("I built a 100-line bytecode tracer that handles depth, oparg pretty-printing, and PEP 669"). It is one of the cheapest credibility signals you can ship out of this course.

## Submission

Push to GitHub. Paste the URL into `c17-week-03-submission.md` in your portfolio repo with one sentence on what you'd do next if you had another day.

After: continue to [Week 4 — `asyncio` from First Principles](../../week-04-asyncio-first-principles/) — coming soon.
