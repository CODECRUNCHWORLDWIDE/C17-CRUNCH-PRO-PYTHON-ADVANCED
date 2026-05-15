# Lecture 2 — Multiprocessing and the Pickling Tax

> The third model. The model that actually parallelises Python CPU work on the stock GIL'd build. The model that comes with the highest fixed cost — process startup, pickling on every cross-boundary call, N copies of imports in memory — and the model that is, despite all of that, the right answer for a large class of real workloads. This lecture is about *when* the pickling tax pays off and *when* it does not. Like every concurrency decision: measure, do not speculate.

## The mental model

A **process** is an OS-level isolation boundary. Each process has its own virtual address space, its own file descriptors, its own Python interpreter, its own GIL. Two Python processes cannot share Python objects directly; they communicate by IPC — pipes, sockets, shared memory regions, or the file system. The `multiprocessing` module wraps this with a Python-friendly API: `Process`, `Pool`, `Queue`, `Pipe`, `Manager`, `shared_memory`. The `concurrent.futures.ProcessPoolExecutor` wraps `multiprocessing.Pool` with the same `Executor` interface you used for threads.

The key fact: each child process is, effectively, an independent Python program. It has its own `sys.modules`, its own globals, its own GIL. If you have 8 cores and 8 workers, you have 8 GILs that can hold independent locks on 8 independent interpreters and execute 8 streams of Python bytecode simultaneously. This is genuine parallelism — the kind threads cannot deliver on the stock build.

The cost: every piece of data that crosses a process boundary must be **serialised** (pickled into bytes on the sender side, unpickled into a Python object on the receiver side). This is the pickling tax. It is real, it is measurable, and on workloads where the per-task data volume is large and the per-task compute is small, it dominates the runtime.

## Start methods: fork, spawn, forkserver

Before any code runs, you must understand how the child processes are created. There are three start methods.

**`fork`**. The Linux default historically (and still the default on Linux through 3.13, though 3.14 is moving it). The parent process calls `os.fork()`; the kernel creates a copy of the parent's address space using copy-on-write semantics. The child inherits *everything* — all module state, all open file descriptors, all threads (but only the calling thread continues running in the child; all other threads are silently dropped on `fork`, which is one reason `fork` is being deprecated in 3.14). The advantage: very fast startup (microseconds), no re-importing of modules. The cost: any threading-related state, any lock held by a non-calling thread, any in-flight I/O operation, and any C-library state can be in an inconsistent state in the child. macOS has reported `fork`+exec hangs in Objective-C/CoreFoundation code for years; this is why macOS defaulted to `spawn` in 3.8.

**`spawn`**. The Windows default; the macOS default since 3.8; expected Linux default starting 3.14. The parent process launches a fresh Python interpreter (`subprocess.Popen` of `python -c '...'` under the hood). The child re-imports the main module, re-imports any module the worker function depends on, and only then starts executing work. The advantage: the child has a clean, predictable state. The cost: startup is slow — 50–300 milliseconds depending on the size of your import graph. The first task you submit to a `ProcessPoolExecutor` includes the spawn cost; subsequent tasks reuse the worker.

**`forkserver`**. The middle ground. Available on Linux/macOS, not Windows. The first time a worker is needed, Python creates a "fork server" process — a fresh interpreter that does nothing but wait for fork requests. Subsequent workers are forked from the fork server, which is in a known clean state. Startup is faster than `spawn` (microseconds for fork, no module re-imports) and cleaner than `fork` (the fork server is single-threaded and has no in-flight state). The cost: the fork server itself takes a few hundred milliseconds to start, and you pay that cost once per process pool.

The right choice in 2026:

```python
import multiprocessing as mp


def configure_start_method() -> None:
    # The right default for new code. Forces consistency across Linux, macOS, Windows.
    # Trade: 50-300ms startup cost per worker on first use.
    mp.set_start_method("spawn", force=True)
```

Set the start method at the top of your `if __name__ == "__main__":` block. Setting it inside a function or after a `Process` has been created raises a `RuntimeError`.

The `if __name__ == "__main__":` guard is not optional with `spawn` and `forkserver`. The child re-imports the main module; without the guard, the child would re-execute everything at the top level of `main.py`, including creating more child processes, ad infinitum. The guard is the boundary between "code that runs in the parent" and "code that runs in every worker."

## ProcessPoolExecutor in 2026

The same `Executor` interface as `ThreadPoolExecutor`. Swap the constructor, swap the import, change nothing else (at least at the call site).

```python
from concurrent.futures import ProcessPoolExecutor
from typing import Callable


def cpu_bound_work(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total


def run_processed(fn: Callable[[int], int], inputs: list[int], max_workers: int) -> list[int]:
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fn, inputs))


if __name__ == "__main__":
    results: list[int] = run_processed(cpu_bound_work, [100_000] * 8, max_workers=8)
```

What happens, step by step:

1. The `with` block enters, the executor allocates a pool of 8 worker processes. On `spawn`, this takes 200–800 ms total (parallelised across workers).
2. `executor.map` chunks the input list (default chunksize=1, but tunable) and sends chunks to workers via a `multiprocessing.Queue`. The queue is implemented with a pipe and a background thread on each side.
3. Each chunk is **pickled** before it crosses the queue. `pickle.dumps(([100_000],))` for a small int argument is about 30 bytes and takes 2 microseconds. For larger arguments (a NumPy array, a 10 MB string), pickling can take milliseconds.
4. The worker receives the pickle bytes, **unpickles** them into Python objects, calls `cpu_bound_work`, gets the result, **pickles** the result, sends it back.
5. The main thread receives the pickled result, **unpickles** it, yields it from `executor.map`.

There are four pickle operations per task: dump args (parent), load args (worker), dump result (worker), load result (parent). On small arguments this is a hundred microseconds total. On large arguments this can be tens of milliseconds. **This is the pickling tax**.

## The pickling tax, quantified

A worked example. The workload: each task takes a 1 MB bytes buffer, runs SHA-256 over it, returns the 32-byte hash. SHA-256 of 1 MB takes about 4 ms on a 2025-class laptop with hashlib's optimised C implementation. The pickle cost: `pickle.dumps(1 MB bytes)` is about 1.5 ms (pickle uses memcpy underneath; bytes pickle fast). `pickle.loads(1 MB bytes)` is about 1 ms. Total pickle overhead per task: 1.5 + 1 + tiny + tiny ≈ 2.5 ms.

The arithmetic: each task does 4 ms of useful work and incurs 2.5 ms of pickle tax. Speedup vs. serial is bounded by `compute / (compute + tax)` ≈ `4 / (4 + 2.5)` = 0.62 per task — but the compute is parallelised across N workers while the tax is paid in series on the parent. The actual speedup on 8 workers is roughly `8 * 4 / (8 * 4 + 8 * 2.5)` only if the pickling on the parent and worker can overlap perfectly with the compute on other workers, which it cannot in pure Python because the parent's pickling holds the GIL.

The reasonable estimate: for this workload, multiprocessing gives a 3-4x speedup on 8 workers — not the theoretical 8x. The remaining 4-5x is pickle tax and queue overhead. We measure this in Exercise 3 and the mini-project benchmark.

The way to spot a pickle-tax-dominated workload: small per-task compute (microseconds), large per-task data (megabytes). The way to fix it:

1. **Bigger chunksizes**. Pass `chunksize=100` to `executor.map`. Now the per-pickle overhead is amortised across 100 work items.
2. **Shared memory**. Use `multiprocessing.shared_memory.SharedMemory` to allocate a buffer once and pass the *name* of the buffer (a tiny string) instead of the buffer itself.
3. **A different model**. If the per-task compute is microseconds and you have millions of tasks, multiprocessing is the wrong tool. Use NumPy (vectorise everything in one process) or a thread pool on the free-threaded build.

## `multiprocessing.shared_memory` — the escape hatch

Added in 3.8. Lets you allocate a chunk of memory that is mapped into multiple processes' address spaces. The processes coordinate via the *name* of the shared memory segment, which is a short string.

```python
from multiprocessing import shared_memory
import numpy as np
from typing import Tuple


def create_shared_array(size: int) -> Tuple[shared_memory.SharedMemory, np.ndarray]:
    shm: shared_memory.SharedMemory = shared_memory.SharedMemory(create=True, size=size * 8)
    array: np.ndarray = np.ndarray((size,), dtype=np.float64, buffer=shm.buf)
    return shm, array


def attach_shared_array(name: str, size: int) -> Tuple[shared_memory.SharedMemory, np.ndarray]:
    shm: shared_memory.SharedMemory = shared_memory.SharedMemory(name=name)
    array: np.ndarray = np.ndarray((size,), dtype=np.float64, buffer=shm.buf)
    return shm, array
```

The parent process creates the segment, gets back a name, passes the name (a string of about 14 characters on Linux) to each worker. Each worker attaches to the segment, reads/writes the array, detaches. No pickling of the array contents at any point.

The caveats:

1. **Shared memory has no Python object semantics**. You write bytes, you read bytes. NumPy arrays work because they are layouts over a bytes buffer; arbitrary Python objects do not work.
2. **No automatic cleanup on crash**. If the parent dies without calling `shm.unlink()`, the segment leaks. On Linux it lives in `/dev/shm` until the system reboots. Use `try: ... finally: shm.unlink()` patterns.
3. **Synchronisation is your problem**. Shared memory does not provide locks. Use `multiprocessing.Lock` or `multiprocessing.Semaphore` if multiple workers might write the same region.
4. **On Windows, the shared-memory name is process-tree-local**. The escape hatch is less useful for cross-machine coordination; it is purely an intra-host optimisation.

For NumPy arrays specifically, the right pattern in 2026 is: parent allocates `shared_memory.SharedMemory`, parent creates a NumPy view over the buffer, parent fills the array, parent passes `(name, shape, dtype)` to each worker, each worker attaches and creates its own view. The data is never copied; the only cross-process communication is the small tuple `(name, shape, dtype)`.

## `multiprocessing.Manager` — the slow but flexible alternative

If you cannot fit your data into a flat bytes layout (a list of strings of variable length, a nested dict, a Python object graph), `shared_memory` does not work. The fallback is `multiprocessing.Manager`, which spawns a separate "manager" process that owns the data; other processes communicate with the manager via a socket; the manager pickles on every access.

```python
from multiprocessing import Manager
from typing import Any


def with_managed_dict() -> dict[str, Any]:
    with Manager() as manager:
        shared_dict: dict[str, Any] = manager.dict()  # type: ignore[assignment]
        shared_dict["counter"] = 0
        # Workers can mutate shared_dict by name.
        return dict(shared_dict)
```

The Manager is convenient and slow. Every `shared_dict["key"]` access is a round-trip to the manager process: pickle the key, send over a socket, manager unpickles, manager reads, manager pickles the value, sends back, caller unpickles. A single access is about 100-200 microseconds. For a tight loop, this is unacceptable.

The rule: `Manager` is for low-traffic shared state (a small dict that workers occasionally write to, a counter). `shared_memory` is for high-traffic shared state (a 100 MB NumPy array that every worker reads from on every iteration).

## What can be pickled, what cannot

`pickle` handles most standard types: ints, floats, strings, bytes, lists, tuples, dicts, sets, dataclasses, classes defined at module level, functions defined at module level.

`pickle` cannot handle:

- **Lambdas and inner functions**. `lambda x: x * 2` cannot be pickled. The error is `PicklingError: Can't pickle <function <lambda>>`.
- **Closures**. A function defined inside another function cannot be pickled because pickle stores the function by qualified name and a closure has no module-level name.
- **Open file objects**. They cannot be re-opened in the child cleanly.
- **Threads, locks, semaphores, condition variables**. These are OS-level resources tied to the parent.
- **Generator objects**. The execution state of a generator is not picklable.
- **Database connections, sockets, file descriptors in general**. Tied to the parent process's OS state.

The error you will see most often is `_pickle.PicklingError: Can't pickle <function <lambda>>: attribute lookup <lambda> on __main__ failed`. The fix is to define the function at module level (top of the file, outside any class or function), and pass its name. `functools.partial` is picklable; lambdas are not.

For complex pickling needs, use `cloudpickle` (a third-party library; `pip install cloudpickle`) which handles lambdas, closures, and dynamically-defined classes by inlining their bytecode. The `multiprocessing` stdlib does not use `cloudpickle` by default; `joblib` and `ray` and `dask` all do. If you find yourself fighting pickle errors, switching to `joblib.Parallel` (which uses `cloudpickle`) is often the fastest path forward.

## When multiprocessing wins, when it loses

**Multiprocessing wins** when:

1. The workload is CPU-bound and pure Python (the GIL would serialise threads).
2. The per-task data volume is small relative to the per-task compute (the pickle tax is amortised).
3. The total wall-clock work exceeds the worker-startup cost (50–300 ms on `spawn`, microseconds on `fork`).
4. The task function is module-level and pickle-friendly.
5. You have multiple cores (verify with `os.cpu_count()`).

**Multiprocessing loses** when:

1. The workload is I/O-bound. Threads or asyncio give the same parallelism with lower fixed cost.
2. The per-task data is large (>1 MB) and the per-task compute is small (<10 ms). The pickle tax dominates.
3. The total wall-clock work is shorter than the worker-startup cost. You spend more time spawning than computing.
4. The task function involves closures or lambdas you cannot easily lift to module scope.
5. The shared state is large and frequently modified (Manager round-trips kill you).
6. You are on a free-threaded build and a thread pool would work without the pickling.

The decision tree, condensed:

| Workload shape | Best model on stock 3.13 | Best model on free-threaded 3.13 |
|----------------|---------------------------|-----------------------------------|
| I/O-bound, <100 in-flight | Threads | Threads |
| I/O-bound, >100 in-flight | Asyncio | Asyncio |
| CPU-bound, pure Python | Multiprocessing | Threads |
| CPU-bound, NumPy/hashlib/zlib | Threads | Threads |
| Mixed (some I/O, some CPU) | Asyncio + `to_thread` for CPU | Asyncio + `to_thread` for CPU |
| Subinterpreter-shareable data | Subinterpreters (3.13+) | Subinterpreters (3.13+) |

Lecture 3 covers the bottom two rows: PEP 703 (the free-threaded build) and PEP 684 / PEP 734 (subinterpreters). The middle three rows are this week's bread and butter.

## The benchmark you will run on Wednesday

Exercise 3 measures the pickling tax for three argument shapes:

- **A: scalar int**. The argument is `42`. `pickle.dumps(42)` is 4 bytes, ~1 microsecond. The pickle tax is ~4 microseconds round-trip.
- **B: 1 MB bytes**. `pickle.dumps(b"\x00" * (1024 * 1024))` is ~1 MB + header. About 1.5 ms.
- **C: 10,000-element list of dicts**. Nested object graph. About 5 ms each direction.

You will run each shape with serial, `ThreadPoolExecutor(8)`, and `ProcessPoolExecutor(8)`. The predicted results:

| Shape | Serial | Threads | Processes | Pickle tax % of process time |
|-------|-------:|--------:|----------:|-----------------------------:|
| A (scalar) | 1.0x | ~1.0x | ~0.3x (overhead dominates) | 95% |
| B (1 MB bytes) | 1.0x | ~1.0x | ~3-4x | 40% |
| C (10k dicts) | 1.0x | ~1.0x | ~1.0-1.5x | 70% |

The "Processes" column is slower than serial for the scalar case because the overhead of crossing the process boundary dwarfs the computation. This is the trap. Measure first, parallelise second.

## Further reading

- **PEP 3148** — `concurrent.futures`. <https://peps.python.org/pep-3148/>. Brian Quinlan, 2009.
- **`multiprocessing` docs** — <https://docs.python.org/3/library/multiprocessing.html>. Especially the "Contexts and start methods" section.
- **`multiprocessing.shared_memory` docs** — <https://docs.python.org/3/library/multiprocessing.shared_memory.html>.
- **`pickle` docs** — <https://docs.python.org/3/library/pickle.html>. Especially the "What can be pickled" section.
- **`cloudpickle`** — <https://github.com/cloudpipe/cloudpickle>. The escape hatch for lambdas and closures.
- **`joblib`** — <https://joblib.readthedocs.io/>. The high-level alternative; uses `cloudpickle` and `memmap` for NumPy.
- **"High Performance Python"** by Gorelick and Ozsvald, chapters 9-10. The textbook reference for `multiprocessing`.

## Appendix A: the lifecycle of one multiprocessing task

Run this through your head before you submit your next `ProcessPoolExecutor.map` call. The lifecycle is more elaborate than for threads, and understanding it is the difference between "this is slower than I expected" and "this is exactly as slow as I expected."

1. **Parent calls `executor.map(fn, inputs)`.** The map call returns immediately with an iterator; no work has happened yet. The first `next()` on the iterator triggers the rest.
2. **Parent pickles the first chunk.** `pickle.dumps(chunk)` produces a bytes blob. This runs on the parent's main thread, holding the parent's GIL.
3. **Parent puts the pickled chunk on the cross-process queue.** The queue is implemented with a pair of pipes (Unix domain sockets on macOS, anonymous pipes on Linux, named pipes on Windows). The blob is written to the pipe in a single `write()` syscall if it fits, or chunked across multiple syscalls if it does not.
4. **A worker process reads from the pipe.** The worker is blocked on a `read()` syscall against its end of the pipe. The kernel notifies the worker; the worker receives the bytes.
5. **Worker unpickles.** `pickle.loads(blob)` reconstructs the Python objects in the worker's address space. This work holds the worker's GIL.
6. **Worker calls `fn(*args)`.** The actual computation. Holds the worker's GIL (or releases it for the I/O / C-extension calls within `fn`).
7. **Worker pickles the result.** Same as step 5 in reverse.
8. **Worker writes the result blob to the back-channel pipe.** Same as step 3 in reverse.
9. **Parent reads the result from the back-channel pipe.** Parent's GIL.
10. **Parent unpickles the result.** Parent's GIL. The result is yielded from the `map` iterator.

The pickle work (steps 2, 5, 7, 10) runs in series on a single thread — there are two pickles per side, but those two are serialised on each side's GIL. The compute (step 6) runs in parallel across workers. The total wall-clock is roughly `max(parent_pickle_time, worker_compute_time / N_workers) + N_workers * per_task_queue_overhead`. The "pickle tax" is the parent's pickle time; if that exceeds the parallelised compute, the whole thing is slower than serial.

## Appendix B: the chunksize knob

The `chunksize` argument to `executor.map` controls how many input items are bundled into a single pickle. The default is 1: every input is pickled and sent independently. For 10,000 inputs and a 0.1 ms pickle cost each, that is 1 second of pure pickle time on the parent — independent of the compute time.

`chunksize=100` reduces the pickle count by 100x: 100 pickles of 100 inputs each, ~10 ms of parent pickle time. The downside: load imbalance. If one chunk's items are slower than another's, the worker holding the slow chunk finishes late while other workers idle.

The right rule of thumb: `chunksize = max(1, total_items // (n_workers * 4))`. The `* 4` ensures each worker handles roughly four chunks over the run, which is enough to amortise pickle overhead while still allowing the pool to rebalance if some chunks are slower than others. The `concurrent.futures.ProcessPoolExecutor` actually uses this heuristic internally (since 3.5) if you do not pass `chunksize`.

The `multiprocessing.Pool.map` method does *not* use this heuristic by default; it uses `chunksize=1`. If you are reading older code that uses `Pool` directly, the chunksize is probably wrong; pass it explicitly.

## Appendix C: when fork is the silent failure

`fork()` is fast (microseconds) and inherits all parent state. The inheritance is the problem.

Suppose the parent has a `threading.Lock` and the lock is held by a *background* thread (not the calling thread) at the moment of `fork()`. The child inherits the lock object in its "held" state, but the holder thread does not exist in the child (only the calling thread continues post-fork). The lock is now held by a non-existent thread; any attempt to acquire it in the child deadlocks.

This is the canonical "macOS fork hang" — Objective-C frameworks, CoreFoundation, libdispatch, and several Python C extensions hold internal locks across operations, and forking while one of those locks is held leads to permanently stuck child processes. macOS 10.13 (2017) explicitly added a hardening check that crashes the child if it detects an Objective-C runtime call post-fork; the symptom is `objc[12345]: +[__NSCFConstantString initialize] may have been in progress in another thread when fork() was called.`

The fix: do not use `fork`. Use `spawn` or `forkserver`. The two fast-startup variants of `forkserver` mitigate the cost by forking from a single-threaded clean interpreter rather than from your application's current state. The Python 3.14 default change (Linux moving from `fork` to `forkserver`) is the consequence of years of these reports.

If you must use `fork` — for legacy code, or for very-tight startup requirements on Linux — wrap the fork call in `os.register_at_fork(before=..., after_in_child=..., after_in_parent=...)`. The `before` hook can release threading locks; the `after_in_child` hook can reinitialise state. The stdlib's `multiprocessing` does this for its internal locks; third-party libraries often do not.

## Appendix D: `os.set_blocking` and the back-channel

A subtle multiprocessing failure: a worker writes a very large result to the back-channel pipe; the pipe's kernel buffer fills; the worker blocks on the `write()` syscall waiting for the parent to drain the pipe. Meanwhile the parent is busy doing pickle work for the *next* task and is not reading. The parent and the worker can deadlock on each other.

The standard library's `multiprocessing.Queue` and the `concurrent.futures.ProcessPoolExecutor` handle this by having a background thread on each side that drains the pipe into a Python-level buffer. The deadlock is averted because the kernel buffer is always being read. But on Windows, where this dance is implemented differently (using overlapped IO), the symptom can still manifest as inexplicable hangs under heavy load.

The mitigation: keep your result objects small. If your worker function returns a 100 MB array, that array crosses the back-channel; the deadlock window is real. Return a path to a file the worker wrote to, or use `shared_memory`, or return a handle to a `SharedMemoryManager`-allocated buffer. The principle: large data should travel via shared memory or the filesystem; only small data should travel via pickle.
