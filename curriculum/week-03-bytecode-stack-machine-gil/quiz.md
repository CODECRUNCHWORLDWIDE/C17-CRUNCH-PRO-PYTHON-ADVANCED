# Week 3 — Quiz

Ten questions. Lectures closed.

---

**Q1.** A `_Py_CODEUNIT` is:

- A) A 32-bit integer holding one opcode plus three argument bytes.
- B) A 16-bit unit: 8 bits of opcode plus 8 bits of oparg.
- C) A variable-length structure depending on the opcode family.
- D) A Python-level object exposed by the `dis` module.

<details>
<summary>Answer</summary>

**B** — 16-bit unit: 8-bit opcode + 8-bit oparg. Larger args use `EXTENDED_ARG`.

</details>

---

**Q2.** The bytecode array's "inline cache" entries between instructions are:

- A) Free-standing instructions executed by the dispatch loop.
- B) Payload `_Py_CODEUNIT`s that adaptive opcode handlers read but the dispatcher steps over.
- C) Part of `code.co_consts`.
- D) Optional — they exist only when the user passes `--with-pgo` to `configure`.

<details>
<summary>Answer</summary>

**B** — payload `_Py_CODEUNIT`s; the dispatcher steps over them via the per-opcode `INLINE_CACHE_ENTRIES_*` count generated from `bytecodes.c`.

</details>

---

**Q3.** In a function `def f(): print(x)` where `x` is a module-level name, which opcode does the compiler emit for `x`?

- A) `LOAD_FAST` — `x` is referenced inside the function, so it is local.
- B) `LOAD_GLOBAL` — `x` is not assigned in the function body, so it is global.
- C) `LOAD_NAME` — Python falls back to `LOAD_NAME` for any name not classified as local.
- D) `LOAD_DEREF` — closure variable.

<details>
<summary>Answer</summary>

**B** — `LOAD_GLOBAL`. The compiler classifies `x` as global because it is not assigned anywhere in `f`'s body. (`LOAD_NAME` is used only in class bodies / `exec` contexts, not in function bodies.)

</details>

---

**Q4.** `LOAD_FAST` is roughly an order of magnitude faster than generic `LOAD_GLOBAL` because:

- A) `LOAD_FAST` skips refcount manipulation.
- B) `LOAD_FAST` is an array index into `frame->localsplus`; `LOAD_GLOBAL` does up to two dict probes.
- C) `LOAD_FAST` is implemented in assembly; `LOAD_GLOBAL` is implemented in Python.
- D) `LOAD_GLOBAL` always takes a slow path through `PyObject_GetAttrString`.

<details>
<summary>Answer</summary>

**B** — array index vs. two hash-table probes (`f_globals`, then `f_builtins`).

</details>

---

**Q5.** After PEP 659 warm-up, a hot `LOAD_GLOBAL print(x)` call site typically rewrites itself to:

- A) `LOAD_FAST` — the runtime promotes globals to locals when hot.
- B) `LOAD_GLOBAL_MODULE` — `print` is found in `f_globals`.
- C) `LOAD_GLOBAL_BUILTIN` — `print` is not in `f_globals`, so it is found in `f_builtins`.
- D) `LOAD_NAME` — always the safe slow-path target.

<details>
<summary>Answer</summary>

**C** — `LOAD_GLOBAL_BUILTIN`. `print` is a builtin name, found in `f_builtins`, not in the module's `f_globals`.

</details>

---

**Q6.** A specialized opcode like `BINARY_OP_ADD_INT` deoptimizes (reverts to generic `BINARY_OP`) when:

- A) The interpreter runs out of memory for the inline cache.
- B) A guard fails — for instance, an operand is no longer `int`.
- C) The adaptive counter overflows.
- D) `sys.settrace` is enabled.

<details>
<summary>Answer</summary>

**B** — a guard miss triggers deopt. The opcode is rewritten back to generic in place.

</details>

---

**Q7.** The GIL protects:

- A) Every user-defined data structure from concurrent modification.
- B) The integrity of CPython's interpreter state — refcounts, free lists, the value stack of the running frame — by serializing bytecode execution to one thread at a time.
- C) Only `dict`, `list`, and `set` from concurrent modification; other types are not protected.
- D) Atomicity of arbitrary multi-statement Python operations.

<details>
<summary>Answer</summary>

**B** — the precise statement. The GIL protects interpreter state, not your application invariants.

</details>

---

**Q8.** A pure-Python tight loop running in two threads on a stock GIL build typically shows:

- A) ~2× speedup vs. one thread (the GIL releases between iterations).
- B) ~1× speedup (no parallelism for pure-Python CPU work).
- C) ~4× speedup if `sys.setswitchinterval(0)` is set.
- D) A `RuntimeError` from `threading`.

<details>
<summary>Answer</summary>

**B** — ~1×. The GIL serializes Python bytecode, so two threads share one core's worth of work.

</details>

---

**Q9.** `sys.setswitchinterval(0.005)`:

- A) Forces a thread switch after exactly 5 ms of wall-clock time.
- B) Hints to the interpreter that, after roughly 5 ms, the running thread should set `GIL_DROP_REQUESTED` so another Python thread gets a turn.
- C) Disables the GIL for 5 ms.
- D) Sets the operating system's `nice` value.

<details>
<summary>Answer</summary>

**B** — it is a hint that triggers `GIL_DROP_REQUESTED` after the interval; not a hard switch.

</details>

---

**Q10.** The PEP 703 free-threaded build differs from the stock GIL build in that:

- A) Refcounts are eliminated entirely; only the cyclic GC manages memory.
- B) Biased reference counting, per-object locks on containers, deferred refcounting for immortal objects — together allowing real parallel Python execution at a ~10% single-thread overhead.
- C) Python source files are compiled to a different bytecode.
- D) Subinterpreters are required; there is no shared global state.

<details>
<summary>Answer</summary>

**B** — biased reference counting + per-object locks + deferred refcounting, as specified in PEP 703.

</details>

If 9+: ship homework. 7-8: re-read Lectures 2 and 3. <7: re-read all three.

---
