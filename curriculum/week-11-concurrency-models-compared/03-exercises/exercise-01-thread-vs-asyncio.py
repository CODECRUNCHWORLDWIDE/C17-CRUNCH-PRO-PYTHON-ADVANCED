"""Exercise 1 — Threads vs Asyncio: predict, then measure.

Three workloads. Two concurrency strategies. A serial baseline. The point is
not the speedup numbers (they vary by machine) but the *shape* of the table.
Run this on your laptop. Predict the column ordering for each workload row
*before* you look at the numbers. Then run it.

Workloads:
    A. SHA-256 of a 1 MB buffer, 64 iterations.
       hashlib releases the GIL for buffers >= 2 KB. Threads should scale.
    B. Sum range(100_000) in pure Python, 64 iterations.
       Pure Python; no C-extension call releases the GIL. Threads should not scale.
    C. time.sleep(0.01) for the threaded/serial paths;
       asyncio.sleep(0.01) for the async path; 64 iterations.
       Blocking syscall releases the GIL. Both strategies should scale.

Strategies:
    1. Serial loop.
    2. ThreadPoolExecutor(max_workers=8).
    3. asyncio.gather over 64 coroutines (only for workloads B and C; A is
       a sync function and would block the loop if naively awaited).

The reference output table for an 8-core 2025 laptop, stock 3.13:

    workload          serial   threads(8)   asyncio
    A (SHA-256)       1.00x    ~7.0x        skipped
    B (pure-CPU)      1.00x    ~1.0x        n/a (blocks loop)
    C (sleep)         1.00x    ~8.0x        ~8.0x

Your numbers will differ. The shape will not. Three columns means three modes:
    - threads win when the work releases the GIL,
    - asyncio wins when the work is sleep-shaped and there are many tasks,
    - both stall on pure-Python CPU on the stock build.

Cite: PEP 703 (the future where row B's "threads" column scales),
      PEP 3148 (concurrent.futures),
      PEP 492 (async/await).

Run with `python3 exercise-01-thread-vs-asyncio.py`.
Compile-check: `python3 -m py_compile exercise-01-thread-vs-asyncio.py`.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

ITERATIONS: int = 64
SLEEP_SECONDS: float = 0.01
BUFFER_SIZE: int = 1024 * 1024  # 1 MB
RANGE_SIZE: int = 100_000


def sha256_one(buf: bytes) -> bytes:
    """Workload A: SHA-256 over a buffer. Releases GIL inside hashlib for large buffers."""
    return hashlib.sha256(buf).digest()


def pure_cpu_one(n: int) -> int:
    """Workload B: pure-Python loop. Does not release the GIL."""
    total: int = 0
    for i in range(n):
        total += i * i
    return total


def sync_sleep_one(seconds: float) -> str:
    """Workload C (sync): blocking sleep. Releases the GIL inside time.sleep."""
    time.sleep(seconds)
    return "slept"


async def async_sleep_one(seconds: float) -> str:
    """Workload C (async): asyncio.sleep. Yields to the loop."""
    await asyncio.sleep(seconds)
    return "slept"


async def async_pure_cpu_one(n: int) -> int:
    """Workload B (async): pure-Python loop inside a coroutine.

    No await. Will block the loop. Included to demonstrate the failure mode.
    """
    total: int = 0
    for i in range(n):
        total += i * i
    return total


def run_serial(fn: Callable[[object], object], inputs: list[object]) -> list[object]:
    """The baseline. One thread, one task at a time."""
    return [fn(x) for x in inputs]


def run_threaded(fn: Callable[[object], object], inputs: list[object], max_workers: int = 8) -> list[object]:
    """ThreadPoolExecutor. The cooperative-via-kernel-preemption path."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fn, inputs))


async def run_async(coros: list) -> list[object]:
    """asyncio.gather over a list of coroutines."""
    return list(await asyncio.gather(*coros))


def time_block(label: str, fn: Callable[[], object]) -> float:
    """Run fn() once, return elapsed seconds, print a labelled line."""
    start: float = time.perf_counter()
    fn()
    elapsed: float = time.perf_counter() - start
    print(f"  {label:30s} {elapsed*1000:8.2f} ms")
    return elapsed


def benchmark_workload_a() -> None:
    """SHA-256 of a 1 MB buffer, 64 iterations. Expects threads to scale."""
    print("\nWorkload A: SHA-256 of 1 MB buffer x 64 (GIL released by hashlib)")
    buffers: list[bytes] = [b"\xab" * BUFFER_SIZE for _ in range(ITERATIONS)]
    serial: float = time_block("serial", lambda: run_serial(sha256_one, buffers))
    threaded: float = time_block("threads(8)", lambda: run_threaded(sha256_one, buffers, 8))
    print(f"  speedup: threads/serial = {serial/threaded:.2f}x")


def benchmark_workload_b() -> None:
    """Pure-Python sum-of-squares x 64. Expects threads NOT to scale (GIL)."""
    print("\nWorkload B: pure-Python sum-of-squares x 64 (GIL held)")
    inputs: list[int] = [RANGE_SIZE] * ITERATIONS
    serial: float = time_block("serial", lambda: run_serial(pure_cpu_one, inputs))
    threaded: float = time_block("threads(8)", lambda: run_threaded(pure_cpu_one, inputs, 8))
    print(f"  speedup: threads/serial = {serial/threaded:.2f}x (expect ~1.0 on stock 3.13)")


def benchmark_workload_c() -> None:
    """time.sleep(0.01) x 64. Expects threads AND asyncio to scale."""
    print("\nWorkload C: time.sleep(0.01) x 64 (GIL released; I/O-shaped)")
    inputs: list[float] = [SLEEP_SECONDS] * ITERATIONS
    serial: float = time_block("serial", lambda: run_serial(sync_sleep_one, inputs))
    threaded: float = time_block("threads(8)", lambda: run_threaded(sync_sleep_one, inputs, 8))
    coros: list = [async_sleep_one(SLEEP_SECONDS) for _ in range(ITERATIONS)]
    async_time: float = time_block("asyncio.gather", lambda: asyncio.run(run_async(coros)))
    print(
        f"  speedup: threads/serial = {serial/threaded:.2f}x, asyncio/serial = {serial/async_time:.2f}x"
    )


def main() -> None:
    print(f"Iterations per workload: {ITERATIONS}")
    print(f"Thread pool size: 8")
    print(f"Python build: {'free-threaded' if not __import__('sys').flags.gil else 'stock (GIL on)'}")
    benchmark_workload_a()
    benchmark_workload_b()
    benchmark_workload_c()
    print(
        "\nIf workload B's threads column is ~1.0x, you are on the stock build."
        "\nIf it is ~7x, you are on the free-threaded build. Either way, the shape"
        "\nof the table is the lecture: threads win when the GIL releases, asyncio"
        "\nwins when the work is sleep-shaped, neither helps on pure-CPU on stock."
    )


if __name__ == "__main__":
    main()
