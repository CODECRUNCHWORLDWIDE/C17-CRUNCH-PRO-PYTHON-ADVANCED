"""
Exercise 1 - CPU-bound work: thread pool vs. process pool vs. 3.13t threads

Goal: prove in code that for a PURE-PYTHON CPU kernel:

  (a) a ThreadPoolExecutor on default CPython 3.13 buys you NOTHING
      versus serial - the GIL serialises every bytecode operation;
  (b) a ProcessPoolExecutor scales near-linearly with cores - at the
      cost of process-spawn time and pickle round-trip per task;
  (c) on the free-threaded build (3.13t) a ThreadPoolExecutor scales
      ALMOST EXACTLY like the process pool but without the pickle tax;
  (d) tiny tasks expose the overhead of both pools; the process pool
      is dramatically worse for sub-millisecond work.

The kernel is a pure-Python primality counter. We deliberately do NOT
use a C-extension that releases the GIL; that would distort the test.
The point is to see what happens to PURE PYTHON code under each primitive.

Estimated time: 45 minutes.

Run with:   python exercise-01-CPU-bound-with-multiprocessing.py
            (then, if available)
            python3.13t exercise-01-CPU-bound-with-multiprocessing.py

Requires:   Python 3.11+ (concurrent.futures shipped 3.2, but we use
            features through 3.11 for parity with the rest of the course).

Acceptance criteria:
- Script runs end-to-end on default CPython 3.13.
- The ordering of timings matches:
    serial < ThreadPoolExecutor (default 3.13 with GIL) ~ same
    ProcessPoolExecutor (large tasks) << serial
    ProcessPoolExecutor (tiny tasks) >> serial   (the pickle tax)
- If you run it on 3.13t (free-threaded), the ThreadPoolExecutor row
  for large tasks should approach the ProcessPoolExecutor row.

Reading before / during:
- Lecture 1 sections 3 (the GIL-release test), 5 (max_workers).
- Lecture 2 section 2 (the cost model), section 6 (failure modes).
- Lecture 3 section 8 (measuring the win properly).
- CPython Lib/concurrent/futures/thread.py and process.py.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Callable, List, Tuple


# -----------------------------------------------------------------------------
# The kernel: a pure-Python CPU loop. Counts primes up to n. No C extensions
# in the hot path. The GIL is held for every iteration on default CPython.
# -----------------------------------------------------------------------------


def count_primes_up_to(n: int) -> int:
    """Count primes in [2, n). Pure-Python. Trial division up to sqrt(k)."""
    total = 0
    for k in range(2, n):
        is_p = True
        if k > 2 and k % 2 == 0:
            is_p = False
        else:
            d = 3
            while d * d <= k:
                if k % d == 0:
                    is_p = False
                    break
                d += 2
        if is_p:
            total += 1
    return total


# -----------------------------------------------------------------------------
# A tiny kernel - used to demonstrate the per-task overhead of the process
# pool. For tasks this small, the pickle round-trip dwarfs the work.
# -----------------------------------------------------------------------------


def tiny_kernel(x: int) -> int:
    """Trivial work. Returns x squared. ~100 ns of actual computation."""
    return x * x


# -----------------------------------------------------------------------------
# Driver helpers.
# -----------------------------------------------------------------------------


def time_call(label: str, fn: Callable[[], object]) -> Tuple[str, float]:
    """Run fn once, return (label, elapsed_seconds). Print the line."""
    t0 = time.perf_counter()
    result = fn()
    dt = time.perf_counter() - t0
    # Print a stable, table-friendly line.
    print(f"  {label:<50s}  {dt:8.3f}s  (result={result!r:.40s})")
    return label, dt


def serial(fn: Callable[[int], int], inputs: List[int]) -> List[int]:
    return [fn(x) for x in inputs]


def threads(fn: Callable[[int], int], inputs: List[int], workers: int) -> List[int]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, inputs))


def processes(fn: Callable[[int], int], inputs: List[int], workers: int) -> List[int]:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, inputs))


def processes_chunked(
    fn: Callable[[int], int], inputs: List[int], workers: int, chunksize: int
) -> List[int]:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, inputs, chunksize=chunksize))


# -----------------------------------------------------------------------------
# Scenario 1 - the LARGE-task benchmark. We run count_primes_up_to(80_000)
# four times. On a 4-core box, the process pool should be ~3-4x faster than
# serial; the thread pool on default 3.13 should be the same as serial
# (within noise); on 3.13t the thread pool should match the process pool.
# -----------------------------------------------------------------------------


def scenario_large_tasks() -> None:
    print("==== Scenario 1: 4 large CPU tasks (count_primes_up_to(80_000)) ====")
    inputs = [80_000] * 4
    rows: List[Tuple[str, float]] = []
    rows.append(time_call("serial", lambda: serial(count_primes_up_to, inputs)))
    rows.append(time_call("threads (4)", lambda: threads(count_primes_up_to, inputs, 4)))
    rows.append(time_call("processes (4)", lambda: processes(count_primes_up_to, inputs, 4)))
    # Compute speedups against serial.
    serial_t = rows[0][1]
    print()
    print("  speedup vs serial:")
    for label, dt in rows:
        speedup = serial_t / dt if dt > 0 else float("inf")
        print(f"    {label:<50s}  {speedup:5.2f}x")
    print()


# -----------------------------------------------------------------------------
# Scenario 2 - the TINY-task benchmark. We run tiny_kernel(x) 10_000 times.
# Serial is the fastest because there is no overhead. The thread pool is
# slower because of the queue.put / queue.get per task. The process pool
# is dramatically slower because every task pays a pickle round-trip.
# Chunked processes recover, because each pickle pays for many tasks.
# -----------------------------------------------------------------------------


def scenario_tiny_tasks() -> None:
    print("==== Scenario 2: 10_000 tiny tasks (x -> x*x) ====")
    inputs = list(range(10_000))
    rows: List[Tuple[str, float]] = []
    rows.append(time_call("serial", lambda: serial(tiny_kernel, inputs)))
    rows.append(time_call("threads (4)", lambda: threads(tiny_kernel, inputs, 4)))
    rows.append(time_call("processes (4)", lambda: processes(tiny_kernel, inputs, 4)))
    rows.append(
        time_call(
            "processes (4) chunksize=500",
            lambda: processes_chunked(tiny_kernel, inputs, 4, 500),
        )
    )
    serial_t = rows[0][1]
    print()
    print("  speedup vs serial (note: <1.0x is a SLOWDOWN):")
    for label, dt in rows:
        speedup = serial_t / dt if dt > 0 else float("inf")
        print(f"    {label:<50s}  {speedup:5.2f}x")
    print()


# -----------------------------------------------------------------------------
# Scenario 3 - scaling sweep. We run count_primes_up_to(40_000) with
# N workers for N in {1, 2, 4, 8}, both threads and processes. On default
# 3.13 the threads row is FLAT (no scaling). On 3.13t the threads row
# matches the processes row.
# -----------------------------------------------------------------------------


def scenario_scaling_sweep() -> None:
    print("==== Scenario 3: scaling sweep (count_primes_up_to(40_000) x N) ====")
    print(f"  os.cpu_count() = {os.cpu_count()}")
    sizes = (1, 2, 4, 8)
    print(f"  {'workers':<10s}  {'threads(s)':>12s}  {'processes(s)':>14s}")
    for n in sizes:
        inputs = [40_000] * n
        t0 = time.perf_counter()
        threads(count_primes_up_to, inputs, n)
        dt_t = time.perf_counter() - t0
        t0 = time.perf_counter()
        processes(count_primes_up_to, inputs, n)
        dt_p = time.perf_counter() - t0
        print(f"  {n:<10d}  {dt_t:12.3f}  {dt_p:14.3f}")
    print()


# -----------------------------------------------------------------------------
# Scenario 4 - report the runtime configuration. This is the single most
# important line of output to capture in your notes.md - it tells you which
# build of Python you are running and whether the GIL is currently enabled.
# -----------------------------------------------------------------------------


def scenario_runtime_report() -> None:
    print("==== Runtime configuration ====")
    import sysconfig

    py_version = sys.version.split()[0]
    impl = sys.implementation.name
    cpu = os.cpu_count()
    # sys._is_gil_enabled() exists on 3.13+. Be defensive.
    gil_enabled: object
    if hasattr(sys, "_is_gil_enabled"):
        try:
            gil_enabled = sys._is_gil_enabled()  # type: ignore[attr-defined]
        except Exception as exc:
            gil_enabled = f"<error: {exc!r}>"
    else:
        gil_enabled = "(API not present; pre-3.13)"
    py_gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    print(f"  Python implementation : {impl}")
    print(f"  Python version        : {py_version}")
    print(f"  os.cpu_count()        : {cpu}")
    print(f"  sys._is_gil_enabled() : {gil_enabled}")
    print(f"  Py_GIL_DISABLED build : {py_gil_disabled!r}")
    print()


# -----------------------------------------------------------------------------
# Main entry point. Order matters: report runtime first, then run scenarios.
# Each scenario prints its own header.
# -----------------------------------------------------------------------------


def main() -> None:
    scenario_runtime_report()
    scenario_large_tasks()
    scenario_tiny_tasks()
    scenario_scaling_sweep()
    print("Done. See REFLECTION section at the bottom of the file.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer. "
            f"You are on {sys.version.split()[0]}."
        )
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (default CPython 3.13, 4-core laptop)
# -----------------------------------------------------------------------------
# ==== Runtime configuration ====
#   Python implementation : cpython
#   Python version        : 3.13.0
#   os.cpu_count()        : 8
#   sys._is_gil_enabled() : True
#   Py_GIL_DISABLED build : 0
#
# ==== Scenario 1: 4 large CPU tasks (count_primes_up_to(80_000)) ====
#   serial                                                3.2s
#   threads (4)                                           3.3s
#   processes (4)                                         0.9s
#
#   speedup vs serial:
#     serial                                              1.00x
#     threads (4)                                         0.97x        <-- GIL serialised the threads
#     processes (4)                                       3.55x        <-- near-linear on 4 cores
#
# ==== Scenario 2: 10_000 tiny tasks (x -> x*x) ====
#   serial                                                0.003s
#   threads (4)                                           0.080s       <-- queue overhead
#   processes (4)                                         8.5s         <-- pickle tax per task
#   processes (4) chunksize=500                           0.15s        <-- amortised
#
#   speedup vs serial (note: <1.0x is a SLOWDOWN):
#     serial                                              1.00x
#     threads (4)                                         0.04x        <-- SLOWDOWN
#     processes (4)                                       0.0004x      <-- catastrophic SLOWDOWN
#     processes (4) chunksize=500                         0.02x        <-- still slower than serial
#
# ==== Scenario 3: scaling sweep ====
#   os.cpu_count() = 8
#   workers     threads(s)    processes(s)
#   1           0.81          1.05
#   2           1.65          1.10
#   4           3.30          1.15        <-- threads scale LINEARLY in wall-clock (worse)
#   8           6.60          1.55        <-- processes scale FLAT (better)
#
# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (free-threaded 3.13t, same hardware)
# -----------------------------------------------------------------------------
# Scenario 1 will show:
#   threads (4)   ~ 0.95s   (matches processes; ~3.5x speedup)
# Scenario 3 will show:
#   workers     threads(s)
#   1           0.85
#   2           0.90
#   4           1.10
#   8           1.50         <-- threads now scale FLAT, like processes
#
# Scenario 2 (tiny tasks) is mostly unchanged: the overhead is the queue,
# not the GIL.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. In Scenario 1, why does the thread-pool row on default 3.13 take
#    APPROXIMATELY THE SAME wall-clock as serial? Answer: the GIL serialises
#    the kernel. Two threads run alternating slices of bytecode; the total
#    work is unchanged. Cite Python/ceval_gil.c:take_gil for the mutex and
#    Python/ceval.c (search for `eval_breaker`) for the periodic drop.
#
# 2. In Scenario 2, why is the process pool 1000x SLOWER than serial for
#    tiny tasks? Answer: every task is a pickle round-trip (~50us each way
#    in the steady state, plus IPC and dispatch). For a task that does ~100ns
#    of work, the overhead is 1000x the work. Cite
#    Lib/concurrent/futures/process.py - the _CallItem / _ResultItem dance.
#
# 3. The `chunksize=500` row recovers most of the loss. Why? Answer: 500
#    inputs are pickled and sent as one batch. The pickle cost is amortised
#    over 500 tasks. The per-task overhead is now (50us) / 500 = 100ns,
#    competitive with the work itself. This is the entire reason
#    pool.map has a `chunksize` argument.
#
# 4. Run on 3.13t (free-threaded). What changes for Scenario 1? Answer:
#    the thread row now scales like the process row, because the GIL is gone.
#    The pure-Python CPU kernel runs in parallel on the 4 worker threads.
#
# 5. What changes for Scenario 2 on 3.13t? Answer: very little. The
#    bottleneck for tiny tasks is the work-item queue (a Python-level
#    queue.SimpleQueue), not the GIL. Even without serialisation, the
#    queue.put / get pair is the overhead. The chunked process row is
#    still the fastest "pool" option; serial is still the absolute winner.
#
# 6. (Stretch) Replace count_primes_up_to with a NumPy kernel like
#    `np.fft.fft(np.random.random(1_000_000)).sum()`. Re-run Scenario 1.
#    Threads (default 3.13) should NOW give a speedup, because NumPy
#    releases the GIL inside the FFT. This is the GIL-RELEASE TEST in
#    action. Cite numpy/core/src/multiarray/ ... wherever FFT lives in
#    your installed numpy version.
#
# 7. (Stretch) Add a row that uses joblib(loky):
#       from joblib import Parallel, delayed
#       Parallel(n_jobs=4)(delayed(count_primes_up_to)(n) for n in inputs)
#    Time it. Compare to the ProcessPoolExecutor row. On a warm pool
#    (reused executor), loky is comparable; on a cold pool, the first
#    invocation pays the warm-up cost. The mini-project will have you
#    do this systematically.
# -----------------------------------------------------------------------------
