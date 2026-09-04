# Week 6 — Quiz

Ten questions. Lectures closed.

---

**Q1.** The GIL-release test asks:

- A) "Is your Python version 3.13 or newer?"
- B) "Does the slowest operation in your code hold the GIL?" If yes, threading does not parallelise it on default CPython. If no, threading parallelises it up to N cores.
- C) "Is `sys._is_gil_enabled()` True?"
- D) "Did you compile CPython with `--disable-gil`?"

<details>
<summary>Answer</summary>

**B** — the GIL-release test. The whole decision rests on this one question. Cite Lecture 1 §3. Pure-Python loops hold the GIL; `socket.recv`, `hashlib.update`, NumPy BLAS calls, `bz2`/`lzma` decompress all release it.

</details>

---

**Q2.** A function that calls `requests.get(url).content` and then does `json.loads(body)`. Under `ThreadPoolExecutor(max_workers=16)` on default CPython 3.13, threading helps with:

- A) Both the HTTP fetch and the JSON parse: both release the GIL.
- B) The HTTP fetch (socket recv releases the GIL); the JSON parse runs under the GIL and serialises across threads.
- C) Neither: the GIL serialises both.
- D) The JSON parse only: requests is a pure-Python library that holds the GIL.

<details>
<summary>Answer</summary>

**B** — the half-and-half case. Requests is GIL-releasing in its hot path (socket recv); JSON parsing in CPython is not. Threading scales the fetch, serialises the parse. The mixed workload benefits, but not as much as a pure IO workload. Cite `Modules/socketmodule.c` (Py_BEGIN_ALLOW_THREADS around `recv`) and `Modules/_json.c` (no GIL release).

</details>

---

**Q3.** On default CPython 3.13 (with GIL), `ProcessPoolExecutor(max_workers=4)` running 1_000_000 trivial tasks (each: `x -> x * 2`) wall-clocks at:

- A) ~0.1s — process pool is always faster.
- B) ~0.5s — limited by `os.cpu_count()` and the work itself.
- C) 10+ seconds — the per-task pickle round-trip + IPC overhead dwarfs the work, by orders of magnitude.
- D) Identical to serial because the GIL serialises subprocesses too.

<details>
<summary>Answer</summary>

**C** — the pickle tax. A million pickle round-trips at ~50–100μs each is 50–100 seconds. The work is negligible by comparison. The fix is `chunksize`. Cite Lecture 2 §6 Failure Mode 1. Also Lecture 2 §2 cost model.

</details>

---

**Q4.** The `if __name__ == "__main__":` guard is required for `multiprocessing` when:

- A) Only on Windows.
- B) Only when using `multiprocessing.Pool`, not `ProcessPoolExecutor`.
- C) Whenever the start method is `spawn` or `forkserver` (i.e., always on macOS and Windows, and on Linux when explicitly selected). Without it, each worker re-imports `__main__` and recursively spawns more workers.
- D) Never — it is a stylistic convention.

<details>
<summary>Answer</summary>

**C** — start-method dependent. `fork` does not need the guard (the child inherits the parent's state, including the already-imported `__main__`). `spawn` and `forkserver` do, because the child re-imports `__main__`. The convention is to always use the guard for portability. Cite Lecture 2 §3 and `Lib/multiprocessing/context.py`.

</details>

---

**Q5.** PEP 703 (Gross 2023) is implementable with acceptably small single-threaded slowdown because of:

- A) A redesign of the bytecode interpreter to use lock-free queues.
- B) **Biased reference counting**: objects are biased toward their creating thread; cross-thread access pays an upfront conversion cost; common-case refcount updates stay non-atomic.
- C) Static analysis at compile time that detects and removes refcount operations on local variables.
- D) A garbage-collection pass that runs every 5 ms to coalesce refcount updates.

<details>
<summary>Answer</summary>

**B** — biased reference counting. The keystone trick. Without it, the slowdown from atomic refcount updates would be 1.5–2× on single-threaded code (Gross's measurements echo Hastings's 2017 Gilectomy numbers). The PEP 703 §5.1 description is dense but worth reading. Cite Lecture 3 §5.

</details>

---

**Q6.** On the free-threaded build (`python3.13t`), `sys._is_gil_enabled()` returns:

- A) Always `False`.
- B) Always `True`.
- C) `False` by default, but `True` after importing a C extension that has not been marked free-threaded-compatible (the runtime re-enables the GIL to preserve compatibility).
- D) Raises `AttributeError`; the function only exists on default CPython.

<details>
<summary>Answer</summary>

**C** — dynamic. The default for a 3.13t binary is GIL-disabled, but loading a non-compatible C extension causes the runtime to re-enable the GIL (with a warning). `sys._is_gil_enabled()` reflects the live state, not the build configuration. To check the build, use `sysconfig.get_config_var('Py_GIL_DISABLED')`. Cite Lecture 3 §3.

</details>

---

**Q7.** The `loky` backend for `joblib.Parallel` provides three production advantages over `multiprocessing.Pool`:

- A) GPU support, network-distributed workers, and built-in monitoring dashboard.
- B) Reusable executor (workers persist across `Parallel` calls), `cloudpickle` for closures/lambdas, robust exception forwarding with the original traceback.
- C) Faster pickle, lower memory per worker, and automatic compilation to C.
- D) The same exact features as `multiprocessing.Pool` but with a shorter name.

<details>
<summary>Answer</summary>

**B** — the production advantages. Reusable executor: `get_reusable_executor()` keeps workers alive across calls, amortising the spawn cost. cloudpickle: handles lambdas, closures, partials, locally-defined classes — none of which the stdlib `pickle` can handle. Robust exception forwarding: the original exception with the original traceback survives the pickle round-trip. Cite Lecture 2 §4 and the loky README.

</details>

---

**Q8.** `asyncio.loop.run_in_executor(executor, fn, *args)` is the:

- A) Synchronous version of `asyncio.gather`.
- B) Function used to start the event loop on a background thread.
- C) Asyncio-to-blocking bridge: it submits `fn(*args)` to a `ThreadPoolExecutor` (or any `concurrent.futures.Executor`) and returns an awaitable that completes when the call finishes. The event loop is free to run other coroutines in the meantime.
- D) The 3.13 replacement for `asyncio.to_thread`.

<details>
<summary>Answer</summary>

**C** — the bridge. `loop.run_in_executor` is `Lib/asyncio/base_events.py:BaseEventLoop.run_in_executor`. It calls `executor.submit(fn, *args)`, wraps the resulting `concurrent.futures.Future` in `asyncio.futures.wrap_future`, and returns it. The event loop is free to run other coroutines while waiting. Cite Lecture 2 §8.

</details>

---

**Q9.** On a 4-core Linux machine running default CPython 3.13 with `fork` start method, calling `ProcessPoolExecutor(max_workers=4)` from a parent process that has a `ThreadPoolExecutor` already running its workers is:

- A) Safe and recommended.
- B) Unsafe (POSIX): only the calling thread survives `fork()` in the child. The child inherits any held locks but no thread to release them. Pre-existing background threads vanish. Switch the start method to `forkserver` or `spawn`.
- C) Identical to using `spawn`: the runtime handles the thread cleanup automatically.
- D) Faster than `forkserver` because the threads provide additional parallelism.

<details>
<summary>Answer</summary>

**B** — POSIX undefined behaviour. The `fork()` syscall duplicates only the calling thread; pre-existing threads are gone in the child but any locks they held are still flagged as held. Subsequent attempts to acquire those locks deadlock forever. On macOS this same issue caused the 3.8 default-start-method change. The fix is `forkserver` or `spawn`. Cite Lecture 2 §3.

</details>

---

**Q10.** A canonical 2026 decision tree for "I have a CPU-bound workload that processes 10 GB of pure-Python objects across 1000 tasks of ~200 ms each":

- A) `ThreadPoolExecutor` on default 3.13 — easiest API.
- B) `asyncio.gather` — handles the scale.
- C) `ProcessPoolExecutor` (with `forkserver` on Linux or `spawn` on macOS) sized to `os.cpu_count()` — true parallelism on N cores; the per-task work (200ms) easily amortises the per-task pickle cost (~1ms). Or `ThreadPoolExecutor` on `python3.13t` (free-threaded) for the same parallelism without the pickle cost, if the workload's C extensions are free-threaded-compatible.
- D) A single-threaded loop — concurrency cannot help CPU-bound work.

<details>
<summary>Answer</summary>

**C** — the decision tree application. 200ms tasks easily amortise process-pool overhead. Pure-Python excludes the GIL-releasing-thread-pool fast path on default CPython. The 3.13t alternative is mentioned because it is a real option in 2026 for free-threaded-compatible C extensions; for a pure-Python workload, both routes parallelise. Cite Lecture 1 §10, Lecture 2 §10, Lecture 3 §9.

</details>

If 9+: ship homework. 7–8: re-read Lectures 1 and 2. <7: re-read all three.

---
