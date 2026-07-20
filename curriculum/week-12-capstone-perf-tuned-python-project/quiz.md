# Final Exam — C17 Crunch Pro Python Advanced (W1–W12 cumulative)

This is the cumulative final exam for C17. Twenty questions covering Weeks 1–12. Closed book; allow 60 minutes. Answers and brief rationales are at the bottom of the file — read them only after completing the questions.

Mark each question A, B, C, or D. Several questions have multiple defensible answers; pick the one *best* defended by the cited PEP or stdlib doc.

---

## Section 1 — Internals and runtime (W1–W3)

### 1. The `ob_refcnt` field of a CPython `PyObject` is incremented by:

A. The cyclic garbage collector during the mark phase.
B. Every `Py_INCREF` macro invocation in C extension code.
C. Every Python-level `id(obj)` call.
D. The `dis` module when disassembling code that references the object.

### 2. CPython's cyclic garbage collector handles which case that reference counting alone cannot?

A. Deallocation of objects with `__del__`.
B. Reference cycles between objects that are otherwise unreachable.
C. Deallocation of objects in the global namespace.
D. Concurrent modification by multiple threads.

### 3. The `LOAD_FAST` bytecode in CPython 3.11+ is faster than `LOAD_NAME` because:

A. `LOAD_FAST` uses an integer index into a fixed-size local variables array; `LOAD_NAME` does a dictionary lookup.
B. `LOAD_FAST` releases the GIL during execution; `LOAD_NAME` does not.
C. `LOAD_FAST` is implemented in assembly; `LOAD_NAME` is implemented in Python.
D. `LOAD_FAST` is specialised by PEP 659; `LOAD_NAME` is not.

### 4. According to PEP 442 (3.4+), an object with `__del__` defined:

A. Cannot participate in a reference cycle without leaking.
B. Can participate in a reference cycle and be safely finalised by the GC.
C. Bypasses reference counting entirely.
D. Is always tracked by the cyclic GC regardless of type.

---

## Section 2 — Async and concurrency (W4–W6, W11)

### 5. `asyncio.TaskGroup`, introduced in 3.11 per PEP 654, replaces which pattern?

A. `asyncio.run(main())`.
B. `asyncio.gather(*tasks)` with manual exception handling.
C. `asyncio.sleep(0)` for cooperative yielding.
D. The `await` keyword.

### 6. When does the Global Interpreter Lock release in CPython 3.13 stock build?

A. On every Python bytecode boundary.
B. On every C-extension call.
C. On blocking I/O syscalls and on C-extension calls that explicitly use `Py_BEGIN_ALLOW_THREADS`.
D. Only when the `gc` module runs.

### 7. The pickling tax in `multiprocessing` refers to:

A. The license fee for `multiprocessing`.
B. The wall-clock cost of serialising function arguments and return values to bytes for inter-process transit.
C. The memory cost of N copies of the Python interpreter.
D. The disk I/O cost of swap pages.

### 8. PEP 703 (free-threaded CPython, 3.13+) removes the GIL. As of 3.13, the typical single-threaded performance impact is:

A. No measurable change.
B. A 15-25% slowdown.
C. A 2x slowdown.
D. A 2x speedup.

### 9. PEP 684 (per-interpreter GIL, 3.12+) means:

A. Each subinterpreter has its own independent GIL; bytecode in different subinterpreters runs in true parallel.
B. The GIL is permanently removed.
C. Each thread has its own GIL.
D. The GIL is now optional at runtime via a flag.

---

## Section 3 — Profiling and optimisation (W7, W8)

### 10. `cProfile` reports cumulative time per function. The correct way to identify the *line* costing the most time is:

A. Use `cProfile` with the `--line` flag.
B. Use `line_profiler` (third-party, the `@profile` decorator) or `py-spy --output flamegraph.svg`.
C. Use `dis` on the function.
D. Use `gc.get_stats()`.

### 11. Releasing the GIL inside a C extension is done with:

A. The `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` macro pair.
B. The `PyGILState_Release` function.
C. The `import gil; gil.release()` call.
D. Setting `tp_flags |= Py_TPFLAGS_NO_GIL` on the type.

### 12. PEP 489 (multi-phase extension initialisation, 3.5+) is required for:

A. C extensions to be importable at all.
B. C extensions to support `importlib.reload`.
C. C extensions to be compatible with subinterpreters (PEP 684).
D. C extensions to release the GIL.

### 13. The PEP 384 / PEP 652 "stable ABI" allows a single compiled `.so` to work across:

A. All Python versions ever.
B. All Python versions from 3.X onward, where X is the minimum supported by the `Py_LIMITED_API` macro value chosen.
C. All operating systems.
D. All Python implementations including PyPy.

---

## Section 4 — Packaging (W9, W12)

### 14. The minimum `pyproject.toml` for a modern package contains:

A. Only `[build-system]`.
B. Only `[project]`.
C. Both `[build-system]` (PEP 518) and `[project]` (PEP 621).
D. `[build-system]`, `[project]`, and `[setup]`.

### 15. PEP 440 defines a valid version string. Which is NOT valid?

A. `1.0.0a1`
B. `1.0.0rc1`
C. `1.0.0.post1`
D. `1.0.0-alpha`

### 16. To distribute type information per PEP 561, you must include:

A. A `mypy.ini` file at the package root.
B. An empty file named `py.typed` at the importable package root.
C. The `Typing :: Typed` classifier in `pyproject.toml`.
D. Both B and C; the classifier alone is informational, the file is the actual signal.

### 17. To install from TestPyPI without losing access to NumPy and other real-PyPI packages:

A. `pip install <pkg> --index-url https://test.pypi.org/simple/`
B. `pip install <pkg> --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/`
C. `pip install <pkg> --no-index --find-links https://test.pypi.org/`
D. `pip install <pkg>` after modifying `/etc/hosts`.

---

## Section 5 — Metaprogramming and the capstone (W10, W12)

### 18. PEP 487 introduced `__init_subclass__` (3.6+), which replaces approximately 90% of:

A. Decorator uses.
B. Descriptor uses.
C. Metaclass uses.
D. Type-hint uses.

### 19. The "tier ladder" of perf optimisation taught in Week 12 orders techniques by:

A. Alphabetical order of the technique name.
B. Increasing implementation complexity, with the lowest-complexity wins (algorithm, vectorisation) applied before high-complexity wins (C extensions, parallelisation).
C. The order they were added to CPython.
D. PEP number ascending.

### 20. The benchmark report deliverable should include all of the following EXCEPT:

A. Hardware specification (CPU, RAM, OS, Python version).
B. The exact dependency versions used.
C. The median wall-clock with a confidence interval.
D. A speculative "future work" section claiming a 10x further improvement is achievable without measurement.

---

## Answer key with brief rationale

1. **B.** `Py_INCREF` and `Py_DECREF` are the C macros that adjust `ob_refcnt`. PEP 7 / C-API docs <https://docs.python.org/3/c-api/refcounting.html>. The GC does not change refcounts; `id()` returns the address.
2. **B.** Reference cycles. The cyclic GC, documented in the `gc` module, is the cycle-collector layered on top of refcounting.
3. **A.** `LOAD_FAST` indexes into `frame->f_localsplus` directly; `LOAD_NAME` walks scopes via dict lookup. PEP 659 specialisation does make many bytecodes faster but is orthogonal to the `LOAD_FAST` vs `LOAD_NAME` distinction.
4. **B.** PEP 442 lifted the restriction; in 3.4+, finalisers run during cycle collection.
5. **B.** `TaskGroup` is the structured-concurrency replacement for `gather`. PEP 654.
6. **C.** I/O syscalls release the GIL (the bytecode dispatcher checks for it on syscall entry/exit). C extensions release the GIL only when they explicitly invoke `Py_BEGIN_ALLOW_THREADS`. Pure Python does NOT release on every bytecode in 3.13 stock build — the periodic-release timer is one mechanism, but it does not fire on every bytecode.
7. **B.** Pickling tax: the time and CPU spent serialising/deserialising at the process boundary.
8. **B.** 15-25% on the prototype; expected to narrow in 3.14 and later.
9. **A.** Per-interpreter GIL: independent GILs.
10. **B.** `line_profiler` is the standard line-attribution profiler.
11. **A.** `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`. Documented at <https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock>.
12. **C.** Subinterpreter compatibility requires multi-phase init.
13. **B.** The stable ABI works from a specified minimum version onward, not across all versions ever.
14. **C.** Both sections are required by PEP 518 and PEP 621 respectively.
15. **D.** `1.0.0-alpha` is not PEP 440. The valid spelling is `1.0.0a1`.
16. **D.** The `py.typed` marker is mandatory; the classifier is supplementary metadata for the index.
17. **B.** Both index URLs.
18. **C.** `__init_subclass__` replaces the bulk of metaclass uses.
19. **B.** Increasing complexity. The discipline of the tier ladder is to stop climbing when you have hit the success criteria.
20. **D.** Speculative future-work claims without measurement are an anti-pattern. A, B, C are all required.

---

## Scoring

- 18-20 correct: excellent. You internalised the track. Use the capstone to show it off.
- 15-17 correct: good. Review the missed questions; the answer-key rationales link to the canonical references.
- 12-14 correct: passing. Reread the lecture notes of the relevant weeks before submitting the capstone.
- Below 12: re-do the homework problems before submitting. The exam is cumulative; the gaps are diagnosable.

The exam grade does not gate capstone submission. It is a diagnostic. The grade that matters is the capstone rubric (`mini-project/RUBRIC.md`).
