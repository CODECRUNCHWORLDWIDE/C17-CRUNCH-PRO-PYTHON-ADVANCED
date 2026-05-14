# Lecture 1 — Threading and the GIL, Revisited

> **Duration:** ~2 hours. **Outcome:** You can apply the GIL-release test to any piece of Python code in five seconds and predict whether `threading.Thread` will give you parallelism, concurrency, or neither; you can write a `ThreadPoolExecutor` example without looking at the docs; you can read `Lib/concurrent/futures/thread.py` end-to-end; you can defend the use of threads in a 2026 Python codebase or argue against them, with numbers.

## 1. What changed since Week 3

Week 3 introduced the GIL at the level of the interpreter: the mutex in `Python/ceval_gil.c`, the eval-breaker mechanism, the `take_gil` / `drop_gil` pair, the `gilstate_t` per-thread structure, the 5-millisecond switching interval (`sys.setswitchinterval`). You learned what the GIL *is* and what it *protects* — namely, the atomicity of single bytecode operations on object refcounts and dict lookups. You learned PEP 703 at the level of "what the patch does to CPython."

This lecture is the practitioner's complement. You will not write a single line of C this week. You *will* be writing a lot of `import threading` and `from concurrent.futures import ThreadPoolExecutor`, and you need a reliable mental model for what each line costs and what it buys you. The model is built from one rule, three primitives, and one diagnostic test.

The rule: **the GIL serialises Python bytecode**. Inside a single CPython process, only one OS thread executes Python bytecode at a time. This is the entire reason threading does not give you CPU parallelism on default CPython. It is also the entire reason threading *does* give you IO concurrency: while one thread is blocked in a `recv()` syscall, the GIL is released; another thread can be running bytecode; when the blocked thread's data arrives, it reacquires the GIL and resumes.

The three primitives: `threading.Thread`, `threading.Lock` (and friends), and `concurrent.futures.ThreadPoolExecutor`. The first two are the low-level surface; the third is the modern, idiomatic wrapper. We will cover all three but we will *use* the executor.

The diagnostic test — call it the **GIL-release test**: take the operation that dominates your code's runtime and ask, "during this operation, is the GIL held?" If yes, threading buys you nothing on default CPython 3.13. If no, threading buys you proportional speedup up to N cores (modulo overhead). That is the whole decision, compressed to one question.

## 2. The three primitives, mechanically

`threading.Thread`:

```python
import threading

def worker(name: str) -> None:
    print(f"hello from {name}")

t = threading.Thread(target=worker, args=("A",), name="A")
t.start()
t.join()
```

`Thread.start()` calls `_thread.start_new_thread(self.run, ())` (`Lib/threading.py`, around line 1010 in 3.13). `_thread.start_new_thread` is implemented in `Modules/_threadmodule.c` and creates a real OS thread — `pthread_create` on POSIX, `_beginthreadex` on Windows. The new thread acquires the GIL (`PyGILState_Ensure`) before running any Python code. The cost of `Thread.start()` is dominated by the OS thread-creation syscall (~50–200 microseconds on Linux; ~1–5 ms on Windows) and the GIL handoff.

`Thread.join()` waits for the thread to finish. It is the moral equivalent of `await`-ing a task in asyncio, except blocking — the calling thread holds the GIL on its own behalf, and waits on a condition variable that the dying thread signals.

`threading.Lock`:

```python
lock = threading.Lock()
with lock:
    # critical section
    counter += 1
```

`Lock` is a thin wrapper around the OS's mutex (`pthread_mutex_t` on POSIX). `with lock:` calls `acquire()`; the exit calls `release()`. The cost is ~50 ns uncontended, ~1 microsecond contended (one context switch).

A common confusion: `threading.Lock` does *not* protect Python object state in the way a Java `synchronized` block does. It protects only the critical section it wraps. The GIL is the thing that protects Python object internals (refcount manipulations, dict-resize coherence) from corruption. If you do `counter += 1` without a lock, you will not corrupt memory — but you will lose updates, because `counter += 1` is three bytecode operations (`LOAD_FAST counter`, `LOAD_CONST 1`, `BINARY_ADD`, `STORE_FAST counter`) and the GIL can switch *between* them. This is the canonical "lost-update bug" and the only reason application code needs locks at all on default CPython.

`concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor

def square(x: int) -> int:
    return x * x

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(square, range(10)))
# results == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

The executor owns a fixed-size pool of `Thread` objects. `submit(fn, *args)` enqueues a work item; one of the worker threads pulls it from the queue, calls `fn(*args)`, and stores the result in a `Future`. The caller can `future.result()` (block) or `future.add_done_callback(fn)` (non-block). `map(fn, iterable)` is sugar for `[submit(fn, x) for x in iterable]` plus an iterator that yields results in submission order.

The executor implementation is in `Lib/concurrent/futures/thread.py`. The file is ~250 lines. The interesting parts:

- `_worker(executor_reference, work_queue, ...)` is the worker thread's loop (~40 lines from the top of the file). Pulls a `_WorkItem` from the queue; runs it; stores the result. Detects executor shutdown via a weak reference.
- `_adjust_thread_count` is called on every `submit` until the pool is full. Workers are created lazily; an idle pool holds no threads. (3.9+ behaviour.)
- `submit` constructs a `_WorkItem(future, fn, args, kwargs)`, puts it on `self._work_queue`, and calls `_adjust_thread_count`. Returns the future.

Read this file. Lecture 1 wants you to recognise every line.

## 3. The GIL-release test, applied

Here is the diagnostic in action. For each of the following snippets, I will state whether threading helps.

**Case 1: pure-Python CPU loop.**

```python
def is_prime(n: int) -> bool:
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True
```

The hot loop is integer arithmetic in pure Python bytecode. The GIL is held throughout. Threading *does not help*. Two threads on this loop run at one-thread speed, plus context-switch overhead. The default CPython answer is `ProcessPoolExecutor`; the 3.13t answer is `ThreadPoolExecutor`.

**Case 2: HTTP fetch with `requests`.**

```python
import requests
def fetch(url: str) -> bytes:
    return requests.get(url).content
```

`requests` internally calls `socket.recv` in `urllib3`. `socket.recv` is implemented in `Modules/socketmodule.c`; the recv loop drops the GIL (`Py_BEGIN_ALLOW_THREADS` wraps the actual syscall). Threading *helps*. Sixteen threads fetching sixteen URLs in parallel approach 16× speedup on a slow remote (limited by the remote's response time, not by Python).

**Case 3: hash computation.**

```python
import hashlib
def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
```

`hashlib.sha256().update(b)` is implemented in `Modules/_hashopenssl.c` (or `_sha256module.c` for the pure-C fallback). The update function drops the GIL inside the OpenSSL call. Threading *helps* — provided the chunks are large enough that the GIL-released CPU time per chunk is significant. (Below 4KB per `update`, the GIL acquisition overhead can dominate.)

**Case 4: JSON parsing.**

```python
import json
def parse(data: bytes) -> dict:
    return json.loads(data)
```

CPython's `json.loads` is implemented partly in `_json.c`. It does *not* currently release the GIL during parsing. (It is implemented in C, but it runs under the GIL because it allocates Python objects continuously and would have to drop-and-reacquire on every allocation.) Threading *does not help*. Same answer as Case 1: process pool, or 3.13t.

**Case 5: NumPy matrix multiplication.**

```python
import numpy as np
def matmul(a, b):
    return a @ b
```

NumPy's `@` (`np.matmul`) calls into BLAS. The BLAS call drops the GIL. Threading *helps*. Bonus: BLAS itself is multi-threaded, so even a single Python thread saturates many CPU cores. Combining threading with BLAS multi-threading can over-subscribe; use `threadpoolctl` to coordinate.

The pattern. **If the dominant operation is implemented in a C extension that drops the GIL, threading is the right answer.** If the dominant operation is pure-Python or a C extension that does not drop the GIL, threading is the wrong answer on default CPython 3.13.

The free-threaded build (3.13t) changes Case 1 and Case 4: threading now scales pure-Python code too. Lecture 3 has the numbers.

## 4. The `ThreadPoolExecutor` patterns

Three idioms cover 95% of production use.

**Idiom A: `map` for fan-out with ordered results.**

```python
with ThreadPoolExecutor(max_workers=8) as pool:
    for url, result in zip(urls, pool.map(fetch, urls)):
        process(url, result)
```

`pool.map` returns an iterator. Results are yielded in the order URLs were submitted, not the order they completed. This blocks: if URL 0 is the slowest, you wait for it before any other result is yielded. Use only when ordered output is required.

**Idiom B: `submit` plus `as_completed` for streaming.**

```python
from concurrent.futures import as_completed

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):
        url = futures[future]
        try:
            result = future.result()
        except Exception as exc:
            print(f"{url}: {exc}")
        else:
            process(url, result)
```

`as_completed` yields futures in completion order. The dict-keyed-by-future trick recovers the input URL once the future is done; `as_completed` itself does not carry that information. This is the right shape when you want to start processing the fast results before the slow ones finish.

**Idiom C: `submit` plus `wait(FIRST_COMPLETED)` for first-success.**

```python
from concurrent.futures import wait, FIRST_COMPLETED

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fetch, mirror_url) for mirror_url in mirrors]
    done, not_done = wait(futures, return_when=FIRST_COMPLETED)
    result = next(iter(done)).result()
    for f in not_done:
        f.cancel()
```

The "try multiple mirrors, take the first to respond" pattern. Note: `Future.cancel()` only works if the work item has not yet started — once the worker thread picks it up, `cancel` is a no-op. You cannot forcibly stop a running thread in Python (because the GIL holder cannot be safely interrupted in C-level extensions). This is a fundamental limitation; the only escape is to use processes (where you can `kill()`) or asyncio (where cancel is exception-based and cooperative).

## 5. `max_workers`: choosing N

The single most-asked question about `ThreadPoolExecutor` is "what should `max_workers` be?" The PEP 3148 default (3.8+) is `min(32, os.cpu_count() + 4)`. That is a defensible starting point for mixed workloads but not always right.

Rules of thumb:

- **Pure IO-bound** (HTTP, DB queries with negligible client-side parse): `max_workers` ≈ the maximum concurrency your downstream tolerates. For HTTP to a single host, often 8–16. For HTTP to many hosts, often 64–128. The upper bound is set by the file-descriptor table (`ulimit -n`) and the downstream's politeness rules, not by your CPU count.
- **GIL-releasing CPU work** (NumPy, hashing): `max_workers` ≈ `os.cpu_count()`. More threads than cores wastes context switches.
- **Mixed (some IO, some pure-Python CPU)**: `max_workers` ≈ 2× to 4× `os.cpu_count()`. The IO phases overlap; the CPU phases serialise on the GIL but at least one thread is doing useful work at all times.

Measure, then choose. There is no general answer because the workload shape determines the answer. The mini-project will have you run a sweep across `max_workers ∈ {1, 2, 4, 8, 16, 32, 64}` for each workload and pick from the curve.

## 6. The cost model

Per-thread costs (typical, default CPython 3.13, Linux):

| Cost                                           | Magnitude        |
|------------------------------------------------|------------------|
| `Thread.start()`: OS thread creation           | 50–200 μs        |
| Per-thread memory (stack + Python frame)       | ~8 MB virtual, ~50 KB resident |
| Context switch (thread-to-thread within process) | 1–5 μs        |
| GIL acquisition (uncontended)                  | <100 ns          |
| GIL handoff under contention                   | 1–10 μs          |
| `Lock` acquire (uncontended)                   | ~50 ns           |
| `Lock` acquire (contended, one switch)         | 1–5 μs           |
| `queue.Queue.put` / `get` (used by executor)   | 1–10 μs          |

Comparison numbers (from asyncio):

| Cost                                           | Magnitude        |
|------------------------------------------------|------------------|
| `asyncio.create_task` (no OS thread)           | 1–5 μs           |
| Per-task memory                                | ~5 KB            |
| Coroutine context switch (cooperative)         | <1 μs            |

asyncio is two to three orders of magnitude cheaper per unit of concurrency. This is the empirical reason async beats threads for ten-thousand-connection scenarios. Threads are cheap enough to be the right answer up to a few hundred concurrent units of IO; past that, async is the only sane choice (modulo `select`/`poll` constraints).

## 7. What the GIL protects, what it does not

A subtle point we revisited in Week 3 but worth re-stating here in the threading context: **the GIL does not protect your application's invariants. It protects the interpreter's internal state.**

What is safe under the GIL with no application-level lock:

- A single bytecode operation. `x = y` is one bytecode; threads cannot interleave inside it.
- `dict[key] = value` (single bytecode, hash + insert is one C function).
- `list.append(x)` (single bytecode, slot-write under `PyListObject` invariants).
- `dict.pop(key, default)` (single C function; the read-and-remove is atomic at the C level).

What is *not* safe:

- `x += 1` (three bytecodes; the GIL can switch between LOAD and STORE).
- `cache[key] = compute(key)` (two operations: dict lookup followed by store; another thread can populate `cache[key]` between them; this is the canonical "thundering herd" cache-stampede shape).
- `if key not in d: d[key] = ...` (the same two-step race).
- Any read-modify-write across multiple bytecode operations.

The fix is `threading.Lock`. Use it. Do not assume the GIL is enough.

On the **free-threaded build**, the GIL is gone but PEP 703 introduces *per-object locks* on `dict`, `list`, and `set`. The atomic operations above remain atomic. The non-atomic ones remain non-atomic. The free-threaded build does not change what your code must lock; it only changes how the runtime enforces structural invariants of built-in containers. The decision to write `with lock:` is unchanged.

## 8. Reading `Lib/concurrent/futures/thread.py`

Open the file: <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/thread.py>. We will trace one `submit` + `result` round-trip.

```python
# class ThreadPoolExecutor:
def submit(self, fn, /, *args, **kwargs):
    with self._shutdown_lock, _global_shutdown_lock:
        if self._broken:
            raise BrokenThreadPool(self._broken)
        # ... shutdown checks ...
        f = _base.Future()
        w = _WorkItem(f, fn, args, kwargs)
        self._work_queue.put(w)
        self._adjust_thread_count()
        return f
```

The flow: construct a `Future` and a `_WorkItem` that wraps `(future, fn, args, kwargs)`. Put the work item on `self._work_queue` (a `queue.SimpleQueue`). Adjust the thread count: if the pool is below `max_workers`, start a new worker.

`_adjust_thread_count` creates a `threading.Thread(target=_worker, args=(...))` and calls `start()`. The worker's loop:

```python
def _worker(executor_reference, work_queue, initializer, initargs):
    # ... initializer call ...
    try:
        while True:
            work_item = work_queue.get(block=True)
            if work_item is not None:
                work_item.run()
                del work_item
                # ... ref-check for shutdown ...
                continue
            # received None: shutdown sentinel
            executor = executor_reference()
            if _shutdown or executor is None or executor._shutdown:
                # ... post a None back to wake other workers ...
                return
            del executor
    except BaseException:
        _base.LOGGER.critical('Exception in worker', exc_info=True)
```

The worker pulls work items off the queue, runs them, deletes the reference (so the caller's args can be GC'd), and loops. Shutdown is signalled by putting `None` on the queue.

`_WorkItem.run`:

```python
class _WorkItem:
    # ... __init__ stores future, fn, args, kwargs ...
    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return
        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as exc:
            self.future.set_exception(exc)
            self = None
        else:
            self.future.set_result(result)
```

`set_running_or_notify_cancel` transitions the future from `PENDING` to `RUNNING` *unless* the future was cancelled before the worker picked it up, in which case it transitions to `CANCELLED` and returns False (so the worker skips). Then the work is run. Any exception (including `BaseException`, deliberately) is caught and stored on the future via `set_exception`; the caller's `future.result()` will re-raise it.

This is the entirety of `ThreadPoolExecutor`. The implementation is small because the GIL handles all the cross-thread coordination of the futures themselves — `Future.set_result` is a method call that writes a field under a Condition variable; no application code needs to lock anything around the futures.

## 9. When threads are still the right answer in 2026

Given asyncio's existence, and given the free-threaded build's existence, when do you reach for `threading` or `ThreadPoolExecutor` in 2026?

The four good reasons:

1. **A blocking library you cannot or will not async-port.** `psycopg2` (synchronous Postgres driver), `pyodbc`, `boto3`, the synchronous Snowflake connector, every internal RPC client your company ships in sync-only form. `ThreadPoolExecutor` wrapped in `loop.run_in_executor` is the production bridge.
2. **A C extension that drops the GIL.** `hashlib`, `bz2`, `lzma`, NumPy, `Pillow`'s decode paths, `scipy.linalg`. Threading scales these near-linearly with cores.
3. **Mixed CPU/IO at modest scale.** A worker that does a network fetch then a quick parse then a write. Sixteen of these in a thread pool, with `max_workers=16`, is a perfectly reasonable production design. The CPU phases serialise on the GIL but each is short.
4. **The 3.13 free-threaded build, for pure-Python parallelism without process overhead.** Subject to ecosystem maturity (Lecture 3); compelling for some workloads in 2026, dominant by 2028 likely.

The bad reasons:

- **"I don't want to learn asyncio."** Then learn asyncio. The colored-function tax is real, but for greenfield IO-bound code, asyncio is the right answer.
- **"I want CPU parallelism."** On default 3.13: use a process pool. On 3.13t: threads work.
- **"It's the same API across CPU and IO."** It is not. Threads serialise on the GIL for pure-Python CPU; processes pay a pickle tax for arguments. The unified API illusion is `concurrent.futures.Executor`; the cost models are wildly different.

## 10. The takeaway

The GIL-release test is the entire mental model:

> *During the slowest operation in this code, is the GIL held?*

If yes, threading does not parallelise it on default CPython 3.13. If no, threading parallelises it up to N cores.

Pure-Python loops, regex, JSON parsing: GIL held. Process pool, or 3.13t threads.

HTTP, file IO, BLAS, hashing, compression: GIL released. Thread pool works.

Mixed: thread pool, sized to whichever phase dominates. Or async with `run_in_executor` for the blocking parts.

That decision tree, applied honestly with measurements, makes 95% of the threads-vs-processes-vs-async questions answer themselves. The exercises this week force you to apply it. The mini-project forces you to measure it.

---

## Exercises tied to this lecture

- `exercises/exercise-01-CPU-bound-with-multiprocessing.py` — the negative result (threads do not help for pure-Python CPU work) and the positive (a process pool does). Run it now.
- `exercises/exercise-03-mixed-with-threadpool.py` — the affirmative case (threading shines for fetch-then-parse). Run after Lecture 1.

## Source references

- `Lib/threading.py:Thread.start` — <https://github.com/python/cpython/blob/main/Lib/threading.py>
- `Lib/concurrent/futures/_base.py:Future` — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/_base.py>
- `Lib/concurrent/futures/thread.py:ThreadPoolExecutor` — <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/thread.py>
- `Python/ceval_gil.c` — <https://github.com/python/cpython/blob/main/Python/ceval_gil.c>
- `Modules/_threadmodule.c` — <https://github.com/python/cpython/blob/main/Modules/_threadmodule.c>
- PEP 3148 — <https://peps.python.org/pep-3148/>
- PEP 703 — <https://peps.python.org/pep-0703/>
