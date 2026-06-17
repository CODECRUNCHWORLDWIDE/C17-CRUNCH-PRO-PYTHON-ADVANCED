"""Exercise 4 — Reproduce and fix the blocked event loop.

The canonical asyncio bug: a single coroutine forgets to await on a slow
operation and blocks the loop. While the bad coroutine runs, no other
coroutine makes progress. From the outside the program looks "asyncio"
(it imports asyncio, it uses async def) but it has the throughput of a
single synchronous thread.

This exercise reproduces the bug three ways and shows three fixes.

The bug:
    A. time.sleep inside a coroutine (the textbook example).
    B. requests.get inside a coroutine (the real-world example;
       simulated here with time.sleep so the file has no dependencies).
    C. CPU-bound loop inside a coroutine (the silent example;
       no syscall, no warning, just no progress).

The fixes:
    1. await asyncio.sleep instead of time.sleep   (for A).
    2. await asyncio.to_thread(blocking_fn, ...)   (for B).
    3. await loop.run_in_executor(pool, cpu_fn)    (for C).

The diagnostic: asyncio.run(main(), debug=True) emits a "Executing <Task ...>
took 0.103 seconds" warning whenever a single callback exceeds 100 ms. Turn
this on whenever you suspect a blocked-loop bug.

Cite: PEP 3156 (asyncio), PEP 492 (async/await), PEP 654 (ExceptionGroup);
      asyncio docs: https://docs.python.org/3/library/asyncio.html
      asyncio.run debug mode: https://docs.python.org/3/library/asyncio-dev.html

Run with `python3 exercise-04-asyncio-blocking-event-loop.py`.
Compile-check: `python3 -m py_compile exercise-04-asyncio-blocking-event-loop.py`.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable

TASK_COUNT: int = 10
SLOW_DURATION: float = 0.1  # 100 ms; long enough to trigger the slow-callback warning


# --- The bug variants. ---


async def bad_a_sync_sleep() -> str:
    """BUG A: time.sleep inside a coroutine. Blocks the loop for 100 ms."""
    time.sleep(SLOW_DURATION)
    return "bad_a"


async def bad_b_blocking_io() -> str:
    """BUG B: a blocking I/O call inside a coroutine. Same shape as B."""
    # Stand-in for requests.get(...) or socket.recv. Blocks the loop.
    time.sleep(SLOW_DURATION)
    return "bad_b"


async def bad_c_cpu_loop() -> str:
    """BUG C: a pure-CPU loop inside a coroutine. No syscall, no warning."""
    total: int = 0
    # ~100 ms of pure Python on a 2025 laptop.
    for i in range(2_000_000):
        total += i * i
    return f"bad_c {total % 1000}"


# --- The fix variants. ---


async def good_a_async_sleep() -> str:
    """FIX A: await asyncio.sleep. Yields to the loop properly."""
    await asyncio.sleep(SLOW_DURATION)
    return "good_a"


def _blocking_io_sync() -> str:
    time.sleep(SLOW_DURATION)
    return "good_b"


async def good_b_to_thread() -> str:
    """FIX B: run the blocking call in a thread via asyncio.to_thread."""
    return await asyncio.to_thread(_blocking_io_sync)


def _cpu_loop_sync() -> str:
    total: int = 0
    for i in range(2_000_000):
        total += i * i
    return f"good_c {total % 1000}"


async def good_c_run_in_executor(executor: ThreadPoolExecutor) -> str:
    """FIX C: hand the CPU work to a thread pool via loop.run_in_executor."""
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _cpu_loop_sync)


# --- Driver. ---


async def fanout(coros: list[Awaitable[str]]) -> list[str]:
    async with asyncio.TaskGroup() as tg:
        tasks: list[asyncio.Task[str]] = [tg.create_task(c) for c in coros]
    return [t.result() for t in tasks]


def time_fanout(label: str, coro_factory) -> float:
    start: float = time.perf_counter()
    asyncio.run(fanout([coro_factory() for _ in range(TASK_COUNT)]))
    elapsed: float = time.perf_counter() - start
    expected_serial: float = SLOW_DURATION * TASK_COUNT
    parallelism: float = expected_serial / elapsed
    print(
        f"  {label:35s} elapsed={elapsed*1000:7.1f}ms  "
        f"parallelism={parallelism:4.2f}x  "
        f"({'BLOCKED LOOP' if parallelism < 1.5 else 'parallel'})"
    )
    return elapsed


def time_fanout_with_executor(label: str, executor: ThreadPoolExecutor) -> float:
    start: float = time.perf_counter()
    asyncio.run(fanout([good_c_run_in_executor(executor) for _ in range(TASK_COUNT)]))
    elapsed: float = time.perf_counter() - start
    expected_serial: float = SLOW_DURATION * TASK_COUNT
    parallelism: float = expected_serial / elapsed
    print(
        f"  {label:35s} elapsed={elapsed*1000:7.1f}ms  "
        f"parallelism={parallelism:4.2f}x  "
        f"({'BLOCKED LOOP' if parallelism < 1.5 else 'parallel'})"
    )
    return elapsed


def main() -> None:
    print(f"Task count: {TASK_COUNT}  Slow duration per task: {SLOW_DURATION*1000:.0f}ms")
    print(f"Expected serial wall time: {TASK_COUNT * SLOW_DURATION * 1000:.0f}ms")
    print()
    print("Bug variants (expected ~serial because the loop is blocked):")
    time_fanout("bad_a (time.sleep inside coroutine)", bad_a_sync_sleep)
    time_fanout("bad_b (blocking I/O inside coroutine)", bad_b_blocking_io)
    time_fanout("bad_c (CPU loop inside coroutine)", bad_c_cpu_loop)
    print()
    print("Fix variants (expected ~parallel: 5-10x speedup over serial):")
    time_fanout("good_a (await asyncio.sleep)", good_a_async_sleep)
    time_fanout("good_b (await asyncio.to_thread)", good_b_to_thread)
    with ThreadPoolExecutor(max_workers=8) as executor:
        time_fanout_with_executor("good_c (loop.run_in_executor + thread pool)", executor)
    print()
    print(
        "Diagnosis: set PYTHONASYNCIODEBUG=1 or pass asyncio.run(main(),"
        " debug=True) to make the loop log a 'slow callback' warning whenever"
        " a single callback takes more than 100 ms. That is the single most"
        " useful asyncio diagnostic in 2026."
    )


if __name__ == "__main__":
    main()
