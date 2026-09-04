# Week 3 — Bytecode, the Stack Machine, and the GIL

> *CPython is a software stack machine. Every `LOAD_FAST` pushes a `PyObject*`; every `BINARY_OP` pops two, computes, pushes one. The Global Interpreter Lock is what keeps that stack from being shredded by concurrent threads. If you can hold the picture of "one frame, one stack, one lock," you understand 80% of why Python is the way it is on multi-core hardware.*

Welcome to Week 3 of **C17 · Crunch Pro Python Advanced**. Week 1 mapped the source-to-bytecode pipeline; Week 2 went down to `PyObject` refcount discipline. This week the camera follows a single bytecode instruction from the dispatch table in `Python/ceval.c` to the value-stack pop in `_PyEval_EvalFrameDefault`, then steps back to ask: what keeps two threads from corrupting that stack? The answer is the **GIL**, and the present-tense answer (CPython 3.13+) also includes **PEP 703**'s free-threaded build and **PEP 684**'s per-interpreter GIL.

By Sunday you will have read the CPython evaluation loop, observed `LOAD_FAST` outperforming `LOAD_GLOBAL` by a measured factor, watched **PEP 659** adaptive specialization promote a generic `BINARY_OP` to `BINARY_OP_ADD_INT`, and built a 100-line bytecode tracer using `sys.monitoring` (PEP 669) that prints each instruction as your code executes.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the CPython evaluation loop at the level of `_PyEval_EvalFrameDefault` (`Python/ceval.c`): the computed-goto dispatch (`DISPATCH()`), the value stack, the instruction pointer (`next_instr`), and the per-frame execution context.
- **Read** the generated opcode handlers in `Python/generated_cases.c.h` and trace one back to its DSL definition in `Python/bytecodes.c`.
- **Predict** which bytecode opcode CPython emits for a given Python expression — and disassemble with `dis.dis(func, adaptive=True, show_caches=True)` to verify.
- **Quantify** why `LOAD_FAST` (array index into `frame->localsplus`) is roughly an order of magnitude faster than `LOAD_GLOBAL` (two dict lookups: `f_globals`, then `f_builtins`).
- **Observe** **PEP 659** adaptive specialization at runtime: count the warm-up iterations, watch a generic opcode become a type-specialized variant, watch a guard miss deoptimize it back.
- **State precisely** what the GIL protects (the integrity of CPython's interpreter state — refcount updates, free-list head pointers, the value stack of the currently-executing frame), what it does **not** protect (your application-level invariants), and how the **`sys.setswitchinterval()`** budget (5 ms by default since 3.2) interacts with `eval_breaker` checks.
- **Reason about** the four concurrent runtime modes in 2026 CPython: stock GIL build, **PEP 703** free-threaded build (`python3.13t`), **PEP 684** per-interpreter GIL via `concurrent.interpreters`, and the multi-process escape hatch.
- **Instrument** code with `sys.monitoring` (PEP 669) — the modern, low-overhead alternative to `sys.settrace` — and explain when each is appropriate.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | Past the outcome set: no second programming course reads its own language’s evaluation loop, watches an opcode specialise at runtime, or says precisely what a global interpreter lock protects and what it does not. |
| Industry | Explain to a team, with a measurement instead of folklore, why one loop is an order of magnitude slower than another that looks identical to it. |
| Beyond the bar | The learner instruments a running program with `sys.monitoring` and prints every instruction as it executes — `mini-project/README.md` |


## Prerequisites

- **C17 Weeks 1 and 2** completed. You should be able to read `dis.dis(f)` output without help, sketch the `PyObject` struct, and explain `Py_INCREF`.
- A working CPython **3.13 or newer** on your machine. The exercises assume `dis.dis(..., adaptive=True)` (3.11+) and `sys.monitoring` (3.12+). The free-threaded exercise requires the **`python3.13t`** build (configure with `--disable-gil`) or `python3.14`'s free-threaded build if you have it.
- Comfort reading C at the level of "I can follow a `switch` statement with macros."

## Topics covered

- **The CPython evaluation loop** — `_PyEval_EvalFrameDefault` in `Python/ceval.c`, the computed-goto dispatch, `DISPATCH()`, the `TARGET()` macro, the value stack (`_PyInterpreterFrame->localsplus`), the instruction pointer (`next_instr`).
- **The bytecode DSL** — `Python/bytecodes.c` is the source of truth; `Tools/cases_generator/` generates `Python/generated_cases.c.h` and `Include/internal/pycore_opcode_metadata.h`. Every opcode has a single readable definition.
- **The value stack discipline** — `PUSH(v)`, `POP()`, `STACK_GROW(n)`, `STACK_SHRINK(n)`; how a binary op is exactly two POPs and one PUSH; why stack effects must be statically known.
- **Frame execution context** — `_PyInterpreterFrame` (since 3.11, allocated on a per-thread C stack pool, not the heap); `frame->localsplus` holds locals and stack adjacent; `frame->previous` for the call chain.
- **`LOAD_FAST` vs `LOAD_GLOBAL`** — array index versus two hash-table probes. Why function-scope name resolution is fast and module-scope is slow. The compiler's "fast-locals" optimization.
- **PEP 659 — specializing adaptive interpreter** — the warm-up counter (`ADAPTIVE_COUNTER`), the family of specialized variants (`LOAD_GLOBAL_MODULE`, `LOAD_GLOBAL_BUILTIN`, `BINARY_OP_ADD_INT`, `BINARY_OP_ADD_FLOAT`, `BINARY_OP_ADD_UNICODE`, `CALL_PY_EXACT_ARGS`, etc.), guard checks, deoptimization.
- **Inline caches** — fixed-size `_Py_CODEUNIT` slots immediately following the opcode; how a specialized opcode reads its cache; the `show_caches=True` flag on `dis`.
- **The Global Interpreter Lock** — `_PyRuntimeState.ceval.gil`, `take_gil()` / `drop_gil()` in `Python/ceval_gil.c`; the `eval_breaker` mechanism; what "releasing the GIL around C calls" actually means; `Py_BEGIN_ALLOW_THREADS`.
- **`sys.setswitchinterval`** — the 5 ms scheduling budget (since 3.2; default `0.005`), how it forces a thread switch, why it does not guarantee fairness.
- **PEP 703 — free-threaded build** — biased reference counting, the per-object lock (`ob_mutex`), deferred reference counting for immortal objects, the cost (single-thread overhead ~5–15%), the gain (real parallelism), the `--disable-gil` configure option.
- **PEP 684 / PEP 734 — per-interpreter GIL and `concurrent.interpreters`** — separate `PyInterpreterState` instances each with their own GIL, channel-based message passing, what a "subinterpreter" actually is.
- **`sys.monitoring` (PEP 669)** — the modern monitoring API, low-overhead by design, the event types (`PY_START`, `PY_RETURN`, `INSTRUCTION`, `LINE`, `RAISE`, `BRANCH`, ...), the tool-id registration model. Why `sys.settrace` is no longer the recommended approach.

## Weekly schedule (~36h intensive)

| Day       | Focus                                            | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The evaluation loop, `ceval.c`, the value stack | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | `LOAD_FAST` vs `LOAD_GLOBAL` + PEP 659           | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0h         | 6.5h        |
| Wednesday | The GIL, `eval_breaker`, switch interval         | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 7h          |
| Thursday  | PEP 703, subinterpreters, `sys.monitoring`       | 0h       | 1.5h      | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6.5h        |
| Friday    | Mini-project deep work                           | 0h       | 1h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6h          |
| Saturday  | Mini-project polish                              | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                | 0h       | 0h        | 0h         | 0.5h      | 0h       | 0h           | 0h         | 0.5h        |
| **Total** |                                                  | **6h**   | **8h**    | **4h**     | **3h**    | **6h**   | **7h**       | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | CPython source pointers, PEPs, devguide |
| [lecture-notes/01-the-evaluation-loop-deep-dive.md](./lecture-notes/01-the-evaluation-loop-deep-dive.md) | `_PyEval_EvalFrameDefault`, dispatch, the value stack, frames |
| [lecture-notes/02-load-fast-vs-load-global-and-specialization.md](./lecture-notes/02-load-fast-vs-load-global-and-specialization.md) | Name-resolution cost; PEP 659 adaptive specialization |
| [lecture-notes/03-the-GIL-and-the-free-threaded-build.md](./lecture-notes/03-the-GIL-and-the-free-threaded-build.md) | `take_gil`/`drop_gil`, PEP 703, subinterpreters |
| [exercises/README.md](./exercises/README.md) | Index |
| [exercises/exercise-01-bytecode-tracer.py](./exercises/exercise-01-bytecode-tracer.py) | Print each instruction as code runs |
| [exercises/exercise-02-specialization-observed.py](./exercises/exercise-02-specialization-observed.py) | Watch a `BINARY_OP` specialize and deoptimize |
| [exercises/exercise-03-GIL-vs-threads.py](./exercises/exercise-03-GIL-vs-threads.py) | Measure thread scaling under the GIL |
| [challenges/README.md](./challenges/README.md) | Stretch challenge |
| [challenges/challenge-01-write-a-100-line-tracer.md](./challenges/challenge-01-write-a-100-line-tracer.md) | Build the mini-project's tracer from scratch in one sitting |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~6h) |
| [mini-project/README.md](./mini-project/README.md) | The 100-line bytecode tracer |

## Stretch

- Read `Python/bytecodes.c` end-to-end (it's ~3500 lines as of 3.13; ~2 hours). It is the most readable VM source file you will encounter; cleaner than `Python/ceval.c` was pre-3.12.
- Read PEP 659 in full. Then read `Python/specialize.c` — the runtime that promotes generic opcodes to specialized variants.
- Build CPython from source with `./configure --disable-gil` and re-run the GIL exercise. Compare wall-clock times.

## Up next

[Week 4 — `asyncio` from First Principles](../week-04-asyncio-first-principles/) — coming soon.
