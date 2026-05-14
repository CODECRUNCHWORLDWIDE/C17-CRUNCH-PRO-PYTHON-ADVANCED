"""
Exercise 3 - Bounded queue, producer/consumer fan-out, back-pressure

Goal: see back-pressure in action. We run one producer that wants to push
      items as fast as it can, and N slow consumers that pull from a
      Queue(maxsize=K). We instrument every put and get and we PRINT the
      queue depth at each step. The output should show the producer
      stalling on `.put()` whenever the queue is full.

We then run the same producer/consumers without bounding the queue
(maxsize=0, i.e. unbounded) and verify that the queue depth grows
unboundedly until the producer finishes - the canonical anti-pattern.

We also demonstrate:
  - Queue.shutdown() (3.13+): the producer signals end-of-stream cleanly.
  - The TaskGroup-wrapped pipeline shape from Lecture 3 sec 7.
  - The "slow sink" failure mode and how back-pressure absorbs it.

Estimated time: 45 minutes.

Run with:   python exercise-03-bounded-queue-fan-out.py
Requires:   Python 3.13+ for Queue.shutdown(); 3.11+ otherwise (we feature-
            detect and fall back to a sentinel).

Acceptance criteria:
- Script runs end-to-end and prints both scenarios.
- You can articulate THREE facts:
    1. With Queue(maxsize=K), the producer's `put` parks when the queue
       has K items in it. The producer's wall-clock time is determined by
       the SLOWEST consumer, not by its own production rate.
    2. With Queue(maxsize=0), the queue depth grows without bound. The
       producer's wall-clock time equals its own production rate.
    3. The producer and the consumers can be co-located under a single
       TaskGroup. End-of-stream is signalled by Queue.shutdown() (3.13+)
       or by a sentinel item.

Reading before / during:
- Lecture 3 sections 2, 3, 6, 7, 8.
- CPython Lib/asyncio/queues.py:
  https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py
- Python 3.13 What's New, asyncio.Queue.shutdown:
  https://docs.python.org/3/whatsnew/3.13.html#asyncio
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import List, Optional

# -----------------------------------------------------------------------------
# Feature detection: Queue.shutdown is 3.13+.
# -----------------------------------------------------------------------------

HAS_QUEUE_SHUTDOWN = hasattr(asyncio.Queue, "shutdown")
_SENTINEL = object()                    # used pre-3.13


_log: List[str] = []
_t0: float = 0.0


def _log_line(msg: str) -> None:
    t = time.monotonic() - _t0
    line = f"[{t:6.3f}s] {msg}"
    _log.append(line)
    print(line, flush=True)


# -----------------------------------------------------------------------------
# Producer: emits N items as fast as it can. Logs the queue depth at each
# put. Calls .shutdown() on completion (3.13+) or puts N_CONSUMERS sentinels.
# -----------------------------------------------------------------------------


async def producer(
    name: str,
    queue: asyncio.Queue,
    n_items: int,
    n_consumers: int,
) -> None:
    _log_line(f"{name}: starting, will emit {n_items} items")
    for i in range(n_items):
        before_put = time.monotonic()
        await queue.put(i)
        wait = time.monotonic() - before_put
        # only log wait times that are above a noise threshold to keep
        # the trace readable.
        marker = f"  (waited {wait*1000:5.1f}ms)" if wait > 0.0005 else ""
        _log_line(f"{name}: put({i:3d})  qsize={queue.qsize():3d}{marker}")
    _log_line(f"{name}: finished producing")
    if HAS_QUEUE_SHUTDOWN:
        queue.shutdown()
        _log_line(f"{name}: called queue.shutdown()")
    else:
        for _ in range(n_consumers):
            await queue.put(_SENTINEL)
        _log_line(f"{name}: pushed {n_consumers} sentinels (pre-3.13)")


# -----------------------------------------------------------------------------
# Consumer: pulls items and "processes" them by sleeping `work_seconds`.
# Logs the queue depth at each get. Returns when shutdown is observed.
# -----------------------------------------------------------------------------


async def consumer(name: str, queue: asyncio.Queue, work_seconds: float) -> None:
    _log_line(f"{name}: starting, work={work_seconds*1000:.0f}ms/item")
    processed = 0
    while True:
        try:
            item = await queue.get()
        except asyncio.QueueShutDown:                    # 3.13+
            _log_line(f"{name}: QueueShutDown, exiting after {processed} items")
            return
        if item is _SENTINEL:                            # pre-3.13
            _log_line(f"{name}: sentinel, exiting after {processed} items")
            queue.task_done()
            return
        try:
            await asyncio.sleep(work_seconds)
            processed += 1
            if processed % 5 == 0 or queue.qsize() == 0:
                _log_line(
                    f"{name}: got({item:3d}) qsize={queue.qsize():3d} "
                    f"processed={processed}"
                )
        finally:
            queue.task_done()


# -----------------------------------------------------------------------------
# Scenario A: BOUNDED queue. The producer is fast (≈0ms between puts);
# the 4 consumers are slow (50ms per item). With maxsize=5, the producer
# parks on `put` once the queue has 5 items in it - back-pressure.
# -----------------------------------------------------------------------------


async def scenario_bounded() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario A: BOUNDED queue (maxsize=5) ====")
    _log_line("expectation: producer parks on put() once qsize hits 5")
    _log_line("              wall-clock determined by SLOWEST consumer")
    queue: asyncio.Queue = asyncio.Queue(maxsize=5)
    n_items = 30
    n_consumers = 4
    async with asyncio.TaskGroup() as tg:
        for i in range(n_consumers):
            tg.create_task(
                consumer(f"C{i}", queue, work_seconds=0.05),
                name=f"C{i}",
            )
        tg.create_task(
            producer("P", queue, n_items=n_items, n_consumers=n_consumers),
            name="P",
        )
    elapsed = time.monotonic() - _t0
    expected_min = n_items * 0.05 / n_consumers
    _log_line(
        f"scenario A done in {elapsed*1000:5.0f}ms "
        f"(expected ~{expected_min*1000:.0f}ms: {n_items} items / {n_consumers} consumers)"
    )


# -----------------------------------------------------------------------------
# Scenario B: UNBOUNDED queue. The producer is fast; the consumers are slow.
# With maxsize=0 the queue grows without bound. The producer finishes in
# the time it takes to enqueue 30 items (effectively zero).
# -----------------------------------------------------------------------------


async def scenario_unbounded() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario B: UNBOUNDED queue (maxsize=0) ====")
    _log_line("expectation: producer races to completion; queue grows to 30")
    _log_line("              (this is the canonical fan-out bug at small scale)")
    queue: asyncio.Queue = asyncio.Queue(maxsize=0)
    n_items = 30
    n_consumers = 4
    async with asyncio.TaskGroup() as tg:
        for i in range(n_consumers):
            tg.create_task(
                consumer(f"C{i}", queue, work_seconds=0.05),
                name=f"C{i}",
            )
        tg.create_task(
            producer("P", queue, n_items=n_items, n_consumers=n_consumers),
            name="P",
        )
    elapsed = time.monotonic() - _t0
    _log_line(f"scenario B done in {elapsed*1000:5.0f}ms")


# -----------------------------------------------------------------------------
# Scenario C: "Slow sink" failure mode. We add a downstream sink queue
# that suddenly slows down at item 10. With maxsize=3 on the sink, the
# back-pressure cascades back through the workers to the producer.
# -----------------------------------------------------------------------------


async def slow_sink(sink: asyncio.Queue, n_items: int) -> None:
    """Drains the sink queue. Sleeps 10ms per item normally; sleeps 200ms
    after item 10 (simulates a sudden slowdown)."""
    _log_line("sink: starting")
    drained = 0
    while drained < n_items:
        try:
            item = await sink.get()
        except asyncio.QueueShutDown:
            _log_line(f"sink: shutdown, drained {drained}")
            return
        if item is _SENTINEL:
            _log_line(f"sink: sentinel, drained {drained}")
            return
        delay = 0.20 if drained > 10 else 0.01
        await asyncio.sleep(delay)
        drained += 1
        if drained == 10:
            _log_line("sink: slowing down to 200ms/item from now on")
        sink.task_done()
    _log_line(f"sink: drained all {drained}")


async def worker_with_sink(
    name: str,
    frontier: asyncio.Queue,
    sink: asyncio.Queue,
    work_seconds: float,
) -> None:
    _log_line(f"{name}: starting")
    while True:
        try:
            item = await frontier.get()
        except asyncio.QueueShutDown:
            _log_line(f"{name}: frontier shutdown, exiting")
            return
        if item is _SENTINEL:
            frontier.task_done()
            _log_line(f"{name}: sentinel, exiting")
            return
        try:
            await asyncio.sleep(work_seconds)
            # Push to sink. This is where back-pressure happens.
            before_put = time.monotonic()
            await sink.put(item)
            wait = time.monotonic() - before_put
            if wait > 0.005:
                _log_line(f"{name}: sink.put({item}) waited {wait*1000:.0f}ms")
        finally:
            frontier.task_done()


async def scenario_slow_sink() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario C: slow sink, back-pressure cascade ====")
    n_items = 20
    n_workers = 4
    frontier: asyncio.Queue = asyncio.Queue(maxsize=5)
    sink: asyncio.Queue = asyncio.Queue(maxsize=3)
    async with asyncio.TaskGroup() as tg:
        # Sink writer (1).
        tg.create_task(slow_sink(sink, n_items=n_items), name="sink")
        # Workers (N).
        for i in range(n_workers):
            tg.create_task(
                worker_with_sink(f"W{i}", frontier, sink, work_seconds=0.01),
                name=f"W{i}",
            )
        # Producer.
        tg.create_task(
            producer("P", frontier, n_items=n_items, n_consumers=n_workers),
            name="P",
        )
        # Watch sink drain. Wait for it; then shut down sink so the writer
        # exits. We embed this in the same TaskGroup as a small monitor.
        async def monitor():
            while True:
                await asyncio.sleep(0.10)
                _log_line(
                    f"monitor: frontier.qsize()={frontier.qsize():2d} "
                    f"sink.qsize()={sink.qsize():2d}"
                )
                # Stop monitoring once everything has drained.
                if frontier.qsize() == 0 and sink.qsize() == 0:
                    # Race-prone but sufficient as a stop signal for the demo.
                    await asyncio.sleep(0.20)
                    if HAS_QUEUE_SHUTDOWN:
                        try:
                            sink.shutdown()
                        except Exception:
                            pass
                    else:
                        try:
                            sink.put_nowait(_SENTINEL)
                        except asyncio.QueueFull:
                            pass
                    return
        tg.create_task(monitor(), name="monitor")
    elapsed = time.monotonic() - _t0
    _log_line(f"scenario C done in {elapsed*1000:5.0f}ms")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


async def main() -> None:
    await scenario_bounded()
    print()
    await scenario_unbounded()
    print()
    await scenario_slow_sink()
    print()
    print("Done. Compare the producer wait times across scenarios A and B.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer (TaskGroup). "
            f"You are on {sys.version.split()[0]}. "
            f"Queue.shutdown() requires 3.13+ "
            f"({'available' if HAS_QUEUE_SHUTDOWN else 'not available'})."
        )
    if not HAS_QUEUE_SHUTDOWN:
        print(
            f"NOTE: Python {sys.version.split()[0]} does not have "
            "asyncio.Queue.shutdown(); falling back to sentinel-based shutdown.",
            flush=True,
        )
    asyncio.run(main())


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (Scenario A excerpt; timings approximate)
# -----------------------------------------------------------------------------
# [ 0.000s] ==== Scenario A: BOUNDED queue (maxsize=5) ====
# [ 0.000s] expectation: producer parks on put() once qsize hits 5
# [ 0.000s] P: starting, will emit 30 items
# [ 0.000s] P: put(  0)  qsize=  1
# [ 0.000s] P: put(  1)  qsize=  2
# [ 0.000s] P: put(  2)  qsize=  3
# [ 0.000s] P: put(  3)  qsize=  4
# [ 0.000s] P: put(  4)  qsize=  5
# [ 0.050s] P: put(  5)  qsize=  5  (waited  50.0ms)    <-- producer parked
# [ 0.050s] P: put(  6)  qsize=  5  (waited   0.1ms)
# ...
# (every fifth put has a ~50ms wait, because that is how long a consumer
#  takes to free a slot)
# [ 0.375s] scenario A done in   375ms (expected ~375ms: 30 items / 4 consumers)
#
# Scenario B excerpt:
# [ 0.000s] ==== Scenario B: UNBOUNDED queue (maxsize=0) ====
# [ 0.000s] P: put(  0)  qsize=  1
# [ 0.000s] P: put(  1)  qsize=  2
# ...
# [ 0.001s] P: put( 29)  qsize= 30
# [ 0.001s] P: finished producing
# (producer finished in ~1ms because puts never park; total wall-clock
#  is then bounded by the slowest consumer drainage, ~375ms)
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. In Scenario A, why is the producer's wall-clock time approximately
#    n_items * work_seconds / n_consumers? Answer: the producer's
#    throughput is capped by the rate at which consumers free queue slots,
#    which is n_consumers per work_seconds. Back-pressure works.
#
# 2. In Scenario B, after the producer finishes at t=0.001s, what is the
#    state of the queue? Answer: 30 items sitting in memory. The producer
#    is done; the consumers still have all the work in front of them.
#    For 30 items this is harmless; for 30 million it is OOM.
#
# 3. In Scenario C, find a log line where a worker's `sink.put` waited
#    a long time. What was happening in the sink at that moment? Answer:
#    the slow_sink had moved past item 10 and is now sleeping 200ms per
#    item. The sink queue (maxsize=3) is full. Workers park on
#    sink.put. The frontier fills up. The producer parks on frontier.put.
#    The whole pipeline is in lock-step with the slowest stage.
#
# 4. (Stretch) Re-run Scenario A with maxsize=1, maxsize=10, maxsize=100.
#    How does the producer-wait pattern change? Why is maxsize=1 nearly
#    identical to maxsize=K-greater-than-N_CONSUMERS in this case?
#    (Hint: with maxsize=1 every put parks after the first; with
#    maxsize=N_CONSUMERS the consumers always have one item each and the
#    queue acts as a 1-slot buffer.)
#
# 5. (Stretch) Replace one consumer with a faster consumer (work=0.01s)
#    and another with a slower one (work=0.20s). Watch the qsize. Which
#    consumer gets more items, and why? (Answer: faster one. asyncio's
#    Queue is FIFO with FIFO-fair wakeup, so the consumer that finishes
#    first re-enters the get-park-deque first.)
#
# 6. (Stretch) Replace the explicit consumer loop with an `async for`
#    over an adapter that yields from the queue (you will need to write
#    a small async generator that wraps `queue.get`). Confirm the same
#    behavior. Note the cleanup gotcha around `aclose`.
# -----------------------------------------------------------------------------
