# Week 11 — Quiz

Ten multiple-choice questions. The first eight are about the four models you compared; the last two are about the PEPs. Answers (with reasoning) are at the bottom; do not scroll until you have committed to an answer.

---

## Q1. Which of the following stdlib calls does **not** release the GIL on a stock CPython 3.13 build?

A. `time.sleep(1.0)`
B. `hashlib.sha256(b"\x00" * (1024 * 1024)).digest()`
C. `json.loads(big_json_string)`
D. `socket.recv(4096)`

<details>
<summary>Answer</summary>

— **C. `json.loads`**

`time.sleep`, `socket.recv`, and `hashlib.sha256` on large buffers all release the GIL via `Py_BEGIN_ALLOW_THREADS`. `json.loads` is C-accelerated but does **not** release the GIL — the per-call cost would dominate, and the json parsing is too tightly interleaved with Python object creation. This is the rule that catches everyone. Cite the C-API docs on `Py_BEGIN_ALLOW_THREADS`: <https://docs.python.org/3/c-api/init.html#c.Py_BEGIN_ALLOW_THREADS>.

</details>

---

## Q2. You have a workload that makes 5,000 concurrent HTTPS requests to a service. The per-request work is roughly 1 ms of CPU (parsing the response) and 200 ms of network wait. Which model has the lowest fixed cost on the stock build of 3.13?

A. `ThreadPoolExecutor(max_workers=5000)`.
B. `asyncio.gather` over 5,000 coroutines using `httpx.AsyncClient`.
C. `ProcessPoolExecutor(max_workers=5000)`.
D. A serial loop, since the GIL would block parallelism anyway.

<details>
<summary>Answer</summary>

— **B. asyncio.gather**

5,000 threads is achievable but expensive: each thread is ~64 KB of stack, total ~320 MB just for stacks. 5,000 coroutines are about 5 MB of task structures. The OS context-switch cost on threads dwarfs the loop-level cost on coroutines at this scale. Multiprocessing is the wrong tool for I/O-bound work. Serial would take 5000 × 0.2 s = 1000 seconds. Cite PEP 3156 and the C10K problem.

</details>

---

## Q3. The pickling tax in `ProcessPoolExecutor` is most likely to dominate when:

A. The argument is a 10 MB NumPy array and the work is a 100 ms FFT.
B. The argument is a single int and the work is a 1 second pure-Python loop.
C. The argument is a 5 MB JSON document and the work is 0.1 ms of validation.
D. There is no argument and the work is a 10 second `time.sleep`.

<details>
<summary>Answer</summary>

— **C. 5 MB JSON document with 0.1 ms work**

Pickle cost is roughly proportional to data size; compute is independent. When `pickle_cost >> compute_cost`, the tax dominates. A 5 MB JSON document pickles in ~10 ms each direction; 0.1 ms of compute cannot pay for 20 ms of pickle round-trip. A, B, and D all have compute much larger than pickle.

</details>

---

## Q4. Inside a coroutine, you call `requests.get("https://example.com")` (the synchronous library). What is the observable effect on the event loop?

A. The loop schedules the request on a thread pool automatically.
B. The loop logs a `RuntimeError: cannot call sync function from coroutine`.
C. The loop blocks for the duration of the request; no other coroutine progresses.
D. The loop transparently rewrites the call to use `httpx.AsyncClient`.

<details>
<summary>Answer</summary>

— **C. The loop blocks for the duration**

Asyncio has no mechanism to detect synchronous code inside a coroutine. The loop runs the coroutine and the coroutine never yields. Every other coroutine waits until `requests.get` returns. This is the canonical blocked-loop bug. The fix is `await asyncio.to_thread(requests.get, url)` or `await httpx.AsyncClient().get(url)`.

</details>

---

## Q5. Which start method for `multiprocessing` is the default on Linux through Python 3.13?

A. `spawn`.
B. `fork`.
C. `forkserver`.
D. There is no default; the user must always set one explicitly.

<details>
<summary>Answer</summary>

— **B. fork**

Linux defaulted to `fork` historically; the default is being changed to `forkserver` in 3.14 (PEP 700-adjacent discussion; the change has been telegraphed in the docs for several releases). macOS defaulted to `spawn` in 3.8 because of CoreFoundation-related fork issues. Windows has always defaulted to `spawn` because there is no `fork` on Windows. Cite the `multiprocessing` docs §"Contexts and start methods."

</details>

---

## Q6. PEP 703 (the free-threaded build) changes which of the following on the stock build?

A. The default value of `sys.setswitchinterval`.
B. The semantics of `threading.Lock.acquire`.
C. Nothing — PEP 703 is an opt-in build, not a change to the stock build.
D. The default thread-pool size of `ThreadPoolExecutor`.

<details>
<summary>Answer</summary>

— **C. Nothing**

PEP 703 introduces a *separate build* of CPython selected at compile time with `--disable-gil`. The stock GIL'd build is unchanged. The free-threaded build has a different ABI (`cp313t`) and requires either declared-safe C extensions or `PYTHON_GIL=0` to load unmarked extensions. Cite PEP 703 §"Build Configuration."

</details>

---

## Q7. Two subinterpreters in the same process want to share a `dict`. What does the `interpreters` module (PEP 734) actually let you pass through an `interpreters.Queue`?

A. Any Python object, by deep copy.
B. Any pickleable Python object, via implicit pickle round-trip.
C. Only "shareable" types: `bytes`, `str`, `int`, `float`, `bool`, `None`, and tuples/lists of these.
D. Only `bytes` and `int`.

<details>
<summary>Answer</summary>

— **C. Shareable types only**

PEP 734 §"Shareable Types" lists `bytes`, `str`, `int`, `float`, `bool`, `None`, `tuple`, `list`, and `memoryview` (for the bytes case). Arbitrary objects cannot cross; the design constraint is that the receiving subinterpreter must be able to materialise the object in its own type system, which restricts to immutable primitives. Cite PEP 734.

</details>

---

## Q8. You have a CPU-bound NumPy workload (matrix multiplication on 10,000 × 10,000 float64 arrays). Which model gives true parallelism on stock 3.13?

A. `ThreadPoolExecutor`, because NumPy's BLAS calls release the GIL.
B. `asyncio.gather`, because asyncio is the modern concurrency primitive.
C. Nothing on stock 3.13; you need the free-threaded build to parallelise CPU work.
D. `ProcessPoolExecutor` only, because NumPy holds the GIL.

<details>
<summary>Answer</summary>

— **A. ThreadPoolExecutor**

NumPy releases the GIL inside its BLAS calls (`np.dot`, `np.matmul`, most ufuncs on arrays larger than the SIMD threshold). Threads execute the C-level BLAS code in parallel on multiple cores. `ProcessPoolExecutor` also gives parallelism but pays the pickling tax for the input/output arrays (substantial for 10k × 10k float64 = 800 MB). Threads are the right tool. Cite the NumPy docs on GIL release.

</details>

---

## Q9. `asyncio.TaskGroup` (3.11+, PEP 654) differs from `asyncio.gather` in which way?

A. `TaskGroup` runs tasks in parallel threads; `gather` runs them serially.
B. `TaskGroup` cancels sibling tasks when any task raises and surfaces an `ExceptionGroup`; `gather` does not by default.
C. `TaskGroup` is slower because it adds locking; `gather` is faster.
D. `TaskGroup` works only on the free-threaded build; `gather` works on both.

<details>
<summary>Answer</summary>

— **B. TaskGroup cancels siblings on failure**

`asyncio.TaskGroup` was added in 3.11 (PEP 654 dependency). Its key feature is automatic cancellation of all sibling tasks if any one raises, and surfacing the result as an `ExceptionGroup`. `asyncio.gather` requires you to set `return_exceptions=True` and inspect each result for the failure mode. Cite the asyncio docs §"Task Groups" and PEP 654.

</details>

---

## Q10. Which PEP defines the `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` C-API contract for releasing the GIL inside a C extension?

A. PEP 703.
B. PEP 3148.
C. PEP 384 (the limited API).
D. None of these — the contract predates the PEP process and is defined in the C-API reference.

<details>
<summary>Answer</summary>

— **D. None of these**

The C-API contract for releasing the GIL predates the PEP process. It is documented in the C-API reference at <https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock>. The macros `Py_BEGIN_ALLOW_THREADS` and `Py_END_ALLOW_THREADS` have been stable since CPython 1.4 (1996). PEP 703 modifies the *semantics* of when the GIL is released (by removing it on the free-threaded build) but does not redefine the macros. PEP 3148 is `concurrent.futures`; PEP 384 is the limited API.

---

</details>

---

## Self-grade

- 9–10 correct: you have the four-model decision tree internalised. Move on.
- 6–8 correct: re-read Lecture 1 on GIL release rules and Lecture 2 on the pickling tax. Run Exercise 2 if you have not.
- 0–5 correct: re-watch Sam Gross's PyCon 2023 talk, re-read Lectures 1 and 2, and run all four exercises before proceeding to the mini-project.

## Extension: open-ended questions for discussion

These are not on the quiz, but a study group should be able to answer each in 2-3 sentences with reference to a primary source.

### EQ1. Why did Sam Gross's `nogil` approach succeed where Larry Hastings's "Gilectomy" failed?

The short answer: biased reference counting. Hastings's approach made every reference-count operation atomic, which added a few nanoseconds of overhead per operation and totalled to a 30% single-threaded regression. Gross's biased reference counting keeps refcount operations on the owner thread non-atomic (cheap) and uses atomics only for cross-thread refcount changes (rare). The single-threaded regression dropped to ~15%, which the steering council deemed acceptable. Reference: PEP 703 §"Biased Reference Counting" with a citation to the original 1995 paper by Choi and Lee.

### EQ2. Asyncio uses a single thread but achieves "concurrency" — what does the word mean in that context?

Concurrency means "the *appearance* of parallel progress on multiple tasks." Asyncio achieves this by interleaving task execution at `await` points; from the outside, it looks like multiple tasks are making progress because no single task blocks the loop. It is *not* parallelism (multiple things actually happening at the same instant); it is concurrency (multiple things in flight at the same wall-clock time). Rob Pike's 2012 talk "Concurrency is not Parallelism" is the canonical reference.

### EQ3. Why does `pickle` fail on lambdas?

The pickle module stores callables by their qualified name (`module.qualname`) and resolves them on the receiving side via `import`. A lambda has no module-level name — it is created anonymously inside whatever scope it was defined in — so there is no name to resolve. The receiving process cannot reconstruct it. The `cloudpickle` library works around this by inlining the function's bytecode as part of the pickle, but the stdlib's pickle does not. Reference: pickle docs §"What can be pickled and unpickled?"

### EQ4. When would you choose `forkserver` over `spawn` on Linux?

When you want spawn's clean-interpreter semantics (avoiding the inherited-lock and inherited-thread issues of `fork`) but without paying the ~250 ms re-import cost per worker. The forkserver process starts once (~250 ms), is single-threaded and clean, and subsequent worker creations fork from it (microseconds). For a long-running service that occasionally spins up new workers, forkserver is the sweet spot. For Windows, `forkserver` does not exist; `spawn` is the only option.

### EQ5. The free-threaded build will probably default in 3.15 or 3.16. What should a library author do today?

Two actions. First, mark the library's C extension as free-threading-safe by setting `Py_mod_gil = Py_MOD_GIL_NOT_USED` in the module init function — *after* auditing the code for thread-safety. Second, ship a `cp313t` wheel alongside the `cp313` wheel on PyPI; the `cibuildwheel` tool can build both in CI. The two together signal to users that the library is ready for the free-threaded build. Reference: the Faster CPython porting guide.

### EQ6. Why does Django still use a metaclass for its ORM models in 2026, when PEP 487 made it (mostly) unnecessary?

Migration cost. Django's metaclass-based `Model` class has been in production for 20 years; thousands of downstream codebases depend on its exact behaviour. A migration to PEP 487 hooks would be source-compatible for most uses but would break the rare users who themselves subclass `ModelBase`. The Django team has decided the migration is not worth the cost. The lesson generalises: PEP 487 made metaclasses unnecessary for new code; it does not make existing metaclass-using code obsolete.

These six questions are the bridge from "I read the lectures" to "I could give this lecture." If you cannot answer one of them from memory, the relevant lecture material has not landed yet — re-read.
