# Week 3 — Exercises

Three exercises. ~30–45 min each.

1. **[Bytecode tracer](./exercise-01-bytecode-tracer.py)** — install a `sys.monitoring` callback that prints one line per opcode as a target function runs. Lays the groundwork for the mini-project.
2. **[Specialization observed](./exercise-02-specialization-observed.py)** — watch `BINARY_OP` become `BINARY_OP_ADD_INT` on the 53rd call; observe deoptimization when the input type changes; measure the speed difference with `pyperf` (or `time.perf_counter` fallback).
3. **[GIL vs. threads](./exercise-03-GIL-vs-threads.py)** — measure CPU-bound vs. IO-bound thread scaling under the GIL. If you have `python3.13t`, re-run and compare.

Each is a single Python file with TODO blocks and a hint/answer-key block at the bottom. Do them in order. All three files compile on stock CPython 3.12+ (Exercise 1 requires 3.12 for `sys.monitoring`; Exercise 2 requires 3.11 for adaptive disassembly).

## Self-check

After each exercise, you should be able to:

1. **Ex 1:** Read a stream of opcode events and explain what each one did to the value stack.
2. **Ex 2:** Predict, for any tight loop, which opcodes will specialize and to which variant.
3. **Ex 3:** Defend a `threading` vs. `multiprocessing` vs. `asyncio` choice with measured numbers, not folklore.
