# Week 1 — Quiz

Ten questions. Lectures closed. Aim for 9/10.

---

**Q1.** Which of the following is *not* a Python implementation?

- A) PyPy
- B) MicroPython
- C) Cython
- D) GraalPy

<details>
<summary>Answer</summary>

**C** — Cython is *not* a Python implementation; it's a tool that compiles Python (with optional types) to C extensions runnable inside CPython.

</details>

---

**Q2.** Where on disk does CPython cache compiled bytecode?

- A) The same directory as the source, with extension `.pyc`.
- B) `~/.python-cache/`.
- C) The `__pycache__/` subdirectory next to the source.
- D) `/tmp/pyc/`.

<details>
<summary>Answer</summary>

**C** — `__pycache__/`, named after [PEP 3147](https://peps.python.org/pep-3147/).

</details>

---

**Q3.** What does the first 4 bytes of a `.pyc` file represent?

- A) The Python version as a UTF-8 string.
- B) A magic number that identifies which Python version compiled it.
- C) The size of the source file.
- D) The number of bytecode instructions in the file.

<details>
<summary>Answer</summary>

**B** — Magic number identifying the Python version. Compare with `importlib.util.MAGIC_NUMBER`.

</details>

---

**Q4.** Which CPython source file contains the main bytecode evaluation loop?

- A) `Python/compile.c`
- B) `Python/ceval.c`
- C) `Objects/typeobject.c`
- D) `Modules/_loop.c`

<details>
<summary>Answer</summary>

**B** — `Python/ceval.c`. The "CEVAL" name predates modern naming conventions.

</details>

---

**Q5.** Disassembling `def f(): return 1 + 2` shows `LOAD_CONST 3` instead of two loads and a `BINARY_OP`. Why?

- A) The CPython JIT recompiled it on first call.
- B) The compiler performed constant folding at compile time.
- C) `dis` simplifies output for readability.
- D) Python's parser merges adjacent constants.

<details>
<summary>Answer</summary>

**B** — Constant folding. The compiler evaluates `1 + 2` at compile time and emits the result as a single constant.

</details>

---

**Q6.** Why is `LOAD_FAST` faster than `LOAD_GLOBAL`?

- A) `LOAD_FAST` skips the bytecode interpreter entirely.
- B) `LOAD_GLOBAL` always raises an exception that's caught internally.
- C) `LOAD_FAST` is an array index; `LOAD_GLOBAL` is a hash-table lookup.
- D) They're identical in speed in Python 3.11+.

<details>
<summary>Answer</summary>

**C** — `LOAD_FAST` reads from a C array on the frame (one pointer dereference). `LOAD_GLOBAL` probes the globals dict (and possibly builtins), which is a hash-table lookup.

</details>

---

**Q7.** In which CPython directory would you find the C implementation of the `dict` type?

- A) `Lib/`
- B) `Objects/`
- C) `Python/`
- D) `Modules/`

<details>
<summary>Answer</summary>

**B** — `Objects/dictobject.c`. Built-in object types live in `Objects/`.

</details>

---

**Q8.** What is the `RESUME` opcode (introduced in Python 3.11)?

- A) Resumes a paused thread.
- B) Marks the entry point of a function or block; required at the start of every code object.
- C) Continues execution of a generator after `yield`.
- D) Restores the stack after an exception.

<details>
<summary>Answer</summary>

**B** — `RESUME` marks function/block entry points. It's also where the interpreter inserts adaptive specialization hooks.

</details>

---

**Q9.** Which module would you use to dump the abstract syntax tree of a Python source string?

- A) `tokenize`
- B) `ast`
- C) `dis`
- D) `parser`

<details>
<summary>Answer</summary>

**B** — `ast`. `ast.parse(...)` produces the tree; `ast.dump(...)` prints it.

</details>

---

**Q10.** PEP 552 introduced "hash-based" `.pyc` files. Why?

- A) Faster import times.
- B) Reproducible builds — the same source always produces the same `.pyc`.
- C) Encryption.
- D) Smaller `.pyc` files.

<details>
<summary>Answer</summary>

**B** — Reproducible builds. The hash-based pyc records a hash of the source instead of a timestamp, so identical sources produce identical pycs across machines.

</details>

If under 7, re-read the lectures you missed. If 9+, you're ready for the [homework](./homework.md).

---
