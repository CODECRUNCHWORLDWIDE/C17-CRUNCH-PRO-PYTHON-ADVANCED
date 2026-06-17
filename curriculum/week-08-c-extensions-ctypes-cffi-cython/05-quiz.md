# Week 8 — Quiz

Ten questions. Lectures closed.

---

**Q1.** A C function called from Python via `ctypes` *without* `argtypes` and `restype` set:

- A) Will refuse to run and raise a `TypeError` until you set them.
- B) Will run, but ctypes will use default coercion (Python ints → C `int`, Python floats → C `double`, strings → `char *`). This works for trivial signatures and silently corrupts memory or returns garbage for non-trivial ones. Always set `argtypes` and `restype` on every binding.
- C) Will run at 10x the speed of the typed version because skipping `argtypes` skips a check.
- D) Is identical to a `cffi` API-mode call.

---

**Q2.** The cffi *API mode* differs from ABI mode in that:

- A) API mode does not need a C compiler at any point.
- B) API mode requires a one-time C-compiler build step (at install or in the wheel pipeline), generates a CPython C extension at the binding boundary, and produces ~10x lower per-call overhead than ABI mode. ABI mode is `ctypes`-equivalent — runtime binding through libffi.
- C) API mode only works on Linux.
- D) API mode is what PyPy uses; ABI mode is what CPython uses.

---

**Q3.** A Cython `.pyx` file without any `cdef` type annotations, compiled and called from Python:

- A) Runs at C speed because Cython is "Python compiled to C."
- B) Runs at *roughly* Python speed (~1.1–1.5x faster) because every operation still goes through the CPython C API at the C level. The speedup of Cython comes from *typed* annotations that let the inner loop compile to real C; without types, Cython just compiles Python to C-that-calls-Python.
- C) Refuses to compile.
- D) Releases the GIL automatically.

---

**Q4.** A Cython typed memoryview declared `double[::1] x` requires:

- A) The input must be a Python `list` of floats.
- B) The input must export the buffer protocol (NumPy array, `array.array`, `memoryview`, `bytes`, ...) with `dtype=float64` and *C-contiguous* layout (the `::1` declares contiguity). The kernel accesses elements with one C-level indexed load each, no Python overhead.
- C) The input must be a Cython object created by `cython.array(...)`.
- D) The `::1` is a typo; the correct syntax is `double[]`.

---

**Q5.** In a Cython kernel, `with nogil:`:

- A) Disables the Cython compiler's optimisations.
- B) Releases the GIL for the duration of the block. Inside, you may only access C-typed locals and buffer-protocol data (memoryviews); any access to a Python object inside is a compile-time error. The win: other Python threads can run concurrently with this kernel, enabling true multi-threaded parallelism for CPU-bound C work.
- C) Is mandatory in all `.pyx` files.
- D) Is the same as `@cython.boundscheck(False)`.

---

**Q6.** `ctypes` per-call overhead is roughly:

- A) 10 nanoseconds.
- B) 1–3 microseconds, dominated by argument marshalling and the libffi dispatch. For a C function that does ~1 µs of useful work, this overhead is 50% of the runtime — and the right fix is to call C *less often with more data*, not the opposite.
- C) 1 millisecond.
- D) Zero; ctypes is a compile-time binding.

---

**Q7.** `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` in a hand-written CPython C extension:

- A) Acquire and release the GIL respectively.
- B) Release the GIL on entry to the block, restore on exit. Inside the block, the C code may not touch any `PyObject *` — there is no way to safely access Python state when the GIL is held by another thread. The pattern is essential for any long-running pure-C computation that should not block other Python threads.
- C) Are deprecated in 3.13.
- D) Are macros that expand to no-ops on Linux.

---

**Q8.** The recommended path for *wrapping an existing C library* (the binding is the product) in 2026 is:

- A) Hand-write a CPython C extension; it gives you the most control.
- B) `cffi` API mode: compile-time verification of declarations against the real C headers, ~10x lower per-call overhead than ABI mode, the precedent of `cryptography`, `bcrypt`, `psycopg2-c`, and `argon2-cffi`. ctypes is acceptable for trivial bindings and for system libraries you do not own.
- C) Cython, regardless of whether you wrote the C.
- D) PyO3, even if the library is in C.

---

**Q9.** A Cython kernel that you decorated with `@cython.boundscheck(False)` will:

- A) Run slower because the compiler has fewer optimisation opportunities.
- B) Run *faster* because the per-access bounds checks are omitted. The cost: an out-of-bounds index reads from undefined memory, producing garbage values or a segfault. The discipline: enable boundscheck while writing and testing, disable it for the production-tight version *after* tests pass.
- C) Refuse to accept a NumPy array.
- D) Automatically release the GIL.

---

**Q10.** The four-way benchmark on a 1D convolution (Lecture 3) showed NumPy ~5–10x faster than the tight Cython kernel. The reason is:

- A) Cython is not actually fast; the benchmark was rigged.
- B) NumPy uses hand-tuned SIMD intrinsics (NEON on ARM, AVX-512 on x86) and, for kernel sizes above ~30, switches to FFT-based convolution (O(N log N) instead of O(N×K)). The Cython auto-vectoriser is conservative; hand-tuned intrinsics are not. The takeaway: for standard linear-algebra-shaped kernels, NumPy is hard to beat. Cython's win is on non-standard kernels (data-dependent branching, short-circuit logic, problem-specific data structures) where NumPy has no tuned routine.
- C) The benchmark was on the wrong CPU.
- D) NumPy uses ctypes internally and is therefore subject to libffi overhead.

---

## Answer key

<details>
<summary>Reveal</summary>

1. **B** — Always set argtypes/restype; default coercion silently corrupts on non-trivial signatures. Lecture 2 §3.1.
2. **B** — API mode is build-time-compiled and ~10x faster per call; ABI mode is libffi-based, ctypes-equivalent. Lecture 2 §§4, 5.
3. **B** — Untyped Cython is ~Python speed. The speedup comes from *types*. Lecture 3 §§2.1, 2.2.
4. **B** — Buffer-protocol producer, dtype=float64, C-contiguous. Lecture 3 §3.
5. **B** — Release GIL; C-only code inside; enables thread-level parallelism. Lecture 3 §2.4; Lecture 1 §4.
6. **B** — ~1–3 µs per call; the fix is batching. Lecture 2 §3.3.
7. **B** — Release and restore the GIL around pure-C work. Lecture 1 §4.
8. **B** — cffi API mode for the wrapper case; cryptography is the precedent. Lecture 2 §5; the cryptography FAQ.
9. **B** — Faster, at the cost of safety. Use after testing. Lecture 3 §2.4; SOLUTIONS Exercise 3.
10. **B** — Hand-tuned SIMD + algorithmic switch (FFT for big kernels). Lecture 3 §6.

</details>

## Self-reflection

If you got 9 or 10 right: you have the model. The mini-project will push the discipline on a real kernel; the questions there are the same shape as the ones here, applied to a problem you pick.

If you got 7 or 8 right: the gap is usually in one of two places — (a) the ctypes-vs-cffi-vs-Cython tradeoff (Q2, Q8) or (b) the Cython directive details (Q5, Q9). Re-read Lecture 2 §§4–5 and Lecture 3 §§2.3–2.4 before Thursday.

If you got 6 or fewer right: re-read all three lectures end-to-end before starting the mini-project. The mini-project will not converge without the mental model the lectures build. The investment is ~4 hours; it returns the rest of the week's work.
