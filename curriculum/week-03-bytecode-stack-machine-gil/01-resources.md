# Week 3 — Resources

All free. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — CPython source tree

| What | Where |
|------|-------|
| **Bytecode DSL — every opcode in one file** | `Python/bytecodes.c` — <https://github.com/python/cpython/blob/main/Python/bytecodes.c> |
| **The evaluation loop** | `Python/ceval.c` — <https://github.com/python/cpython/blob/main/Python/ceval.c> |
| **Generated opcode handlers** | `Python/generated_cases.c.h` — <https://github.com/python/cpython/blob/main/Python/generated_cases.c.h> |
| **Opcode metadata (names, stack effects, cache sizes)** | `Include/internal/pycore_opcode_metadata.h` — <https://github.com/python/cpython/blob/main/Include/internal/pycore_opcode_metadata.h> |
| **The cases generator (compiles the DSL)** | `Tools/cases_generator/` — <https://github.com/python/cpython/tree/main/Tools/cases_generator> |
| **PEP 659 specialization runtime** | `Python/specialize.c` — <https://github.com/python/cpython/blob/main/Python/specialize.c> |
| **GIL acquire/release** | `Python/ceval_gil.c` — <https://github.com/python/cpython/blob/main/Python/ceval_gil.c> |
| **Frame object internals** | `Include/internal/pycore_frame.h` — <https://github.com/python/cpython/blob/main/Include/internal/pycore_frame.h> |
| **Opcode numeric IDs** | `Lib/opcode.py` — <https://github.com/python/cpython/blob/main/Lib/opcode.py> |
| **`sys.monitoring` C implementation** | `Python/instrumentation.c` — <https://github.com/python/cpython/blob/main/Python/instrumentation.c> |
| **Free-threaded build, biased refcounting** | `Objects/object.c`, `Include/object.h` — search `_Py_REF_LOCAL` / `_Py_REF_SHARED` |

## Required PEPs

- **PEP 659 — Specializing Adaptive Interpreter** (Shannon, 2021; implemented in 3.11):
  <https://peps.python.org/pep-0659/>
- **PEP 669 — Low Impact Monitoring for CPython** (Shannon, 2022; landed 3.12):
  <https://peps.python.org/pep-0669/>
- **PEP 703 — Making the Global Interpreter Lock Optional** (Gross, 2023; accepted 2024; experimental in 3.13 as `python3.13t`):
  <https://peps.python.org/pep-0703/>
- **PEP 684 — A Per-Interpreter GIL** (Snow, 2022; landed 3.12):
  <https://peps.python.org/pep-0684/>
- **PEP 734 — Multiple Interpreters in the Stdlib** (Snow, 2023; `concurrent.interpreters` in 3.14):
  <https://peps.python.org/pep-0734/>
- **PEP 626 — Precise line numbers for debugging** (Shannon, 2020) — relevant for tracing:
  <https://peps.python.org/pep-0626/>

## CPython devguide — the canonical reference

- **The CPython developer's guide on `ceval`:**
  <https://devguide.python.org/internals/interpreter/>
- **Compiler design (covers the codegen side):**
  <https://devguide.python.org/internals/compiler/>
- **Adaptive interpreter overview (devguide):**
  <https://devguide.python.org/internals/interpreter/#adaptive-interpreter>

## Stdlib docs

- **`dis` — disassembler:** <https://docs.python.org/3/library/dis.html>
  Note: `dis.dis(func, adaptive=True, show_caches=True)` shows specialized opcodes and inline-cache slots (3.11+).
- **`sys.settrace` — legacy tracing:** <https://docs.python.org/3/library/sys.html#sys.settrace>
- **`sys.monitoring` — PEP 669 monitoring API:** <https://docs.python.org/3/library/sys.monitoring.html>
- **`sys.setswitchinterval`:** <https://docs.python.org/3/library/sys.html#sys.setswitchinterval>
- **`threading` — the GIL is mentioned at the top of this page:** <https://docs.python.org/3/library/threading.html>
- **`concurrent.interpreters` (3.14+):** <https://docs.python.org/3/library/concurrent.interpreters.html>

## Background reading

- **Mark Shannon's "Faster CPython" plan (the umbrella under which PEP 659 lives):**
  <https://github.com/markshannon/faster-cpython/blob/master/plan.md>
- **Brandt Bucher & Mark Shannon, "Inside CPython 3.11's New Specializing, Adaptive Interpreter"** — PyCon 2022 talk (free on YouTube; check the captions for transcript).
- **Sam Gross's PEP 703 design doc (longer than the PEP itself):**
  <https://docs.google.com/document/d/18CXhDb1ygxg-YXNBJNzfzZsDFosB5e6BfnXLlejd9l0/>
- **Anthony Shaw, "CPython Internals" — chapter on the evaluation loop** (free on Real Python):
  <https://realpython.com/cpython-internals-paperback/>
- **Eli Bendersky, "A deeper look at the CPython virtual machine"** (older but still accurate on the dispatch design):
  <https://eli.thegreenplace.net/2017/adventures-in-jit-compilation-part-1-an-interpreter/>

## Tools used this week

- **`dis` (stdlib)** — disassembler. No install.
- **`sys.monitoring` (stdlib, 3.12+)** — the modern tracer API. No install.
- **`pyperf`** — accurate microbenchmarks. `pip install pyperf`. Used in Exercise 2.
- **`py-spy`** (optional, for the GIL exercise) — sampling profiler that shows time spent waiting on the GIL. `pip install py-spy`.

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `_PyEval_EvalFrameDefault` | `Python/ceval.c` (search the symbol; ~line 700 in 3.13) |
| Computed-goto `DISPATCH()` macro | `Python/ceval_macros.h` |
| `TARGET()` / `PREDICT()` macros | `Python/ceval_macros.h` |
| `_PyInterpreterFrame` struct | `Include/internal/pycore_frame.h` |
| Per-opcode definitions | `Python/bytecodes.c` (one block per opcode) |
| `LOAD_FAST` definition | `Python/bytecodes.c`, search `inst(LOAD_FAST,` |
| `LOAD_GLOBAL` family | `Python/bytecodes.c`, search `inst(LOAD_GLOBAL,` (then `_LOAD_GLOBAL_MODULE`, `_LOAD_GLOBAL_BUILTIN`) |
| `BINARY_OP` family | `Python/bytecodes.c`, search `inst(BINARY_OP,` |
| Specialization promotion | `Python/specialize.c`, `_Py_Specialize_LoadGlobal`, `_Py_Specialize_BinaryOp` |
| `take_gil` / `drop_gil` | `Python/ceval_gil.c` |
| `eval_breaker` checks | `Python/ceval.c`, search `_Py_HandlePending` |
| `sys.monitoring` dispatch | `Python/instrumentation.c` |

## Glossary

| Term | Definition |
|------|------------|
| **Evaluation loop** | The function (`_PyEval_EvalFrameDefault`) that decodes and executes bytecode one instruction at a time. |
| **Value stack** | A per-frame array of `PyObject*` slots; opcodes push and pop from this. |
| **Frame** | `_PyInterpreterFrame` — the runtime activation record for one Python function call. |
| **`next_instr`** | The instruction pointer: points to the next `_Py_CODEUNIT` to execute in the frame's code object. |
| **`_Py_CODEUNIT`** | A 16-bit unit: 8-bit opcode + 8-bit oparg. Bytecode arrays are arrays of these. |
| **Inline cache** | Fixed-size `_Py_CODEUNIT` slots adjacent to a specialized opcode; hold per-call-site state. |
| **Dispatch** | The decode-then-jump step at the top of every instruction; uses computed-gotos where the compiler supports them. |
| **Specialization** | PEP 659's runtime opcode rewriting: a generic opcode becomes a type-specific variant after warm-up. |
| **Deoptimization** | The reverse: when a guard misses, the specialized opcode rewrites itself back to generic. |
| **GIL** | Global Interpreter Lock; a single mutex serializing access to interpreter state. |
| **`eval_breaker`** | A set of bit flags polled at every backward jump; tells the loop to check for signals, GIL drops, etc. |
| **Switch interval** | `sys.setswitchinterval` — the wall-clock budget (default 5 ms) after which a thread is asked to drop the GIL. |
| **Free-threaded build** | The PEP 703 build that removes the GIL; biased refcounting + per-object locks. Named `python3.13t`. |
| **Subinterpreter** | A `PyInterpreterState` with its own GIL, modules, and singletons. PEP 684 made these isolated; PEP 734 exposed them. |
| **`sys.monitoring`** | The PEP 669 monitoring API. Designed for low overhead. Replaces `sys.settrace` for new tools. |

---

*Broken link? Open an issue.*
