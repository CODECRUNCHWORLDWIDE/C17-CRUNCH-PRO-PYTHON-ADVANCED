"""
Exercise 1 - A toy single-threaded event loop

Goal: build a runnable, ~120-line event loop with a Future, a Task, a sleep,
      and a run_until_complete - all from scratch, no `import asyncio`. Run
      two coroutines concurrently. Confirm the wall-clock add up correctly.

This is the seed of the Week-4 mini-project. Get the bones right here and
the project becomes "polish + tests + gather + TaskGroup."

Estimated time: 90 minutes.

Run with:   python exercise-01-toy-event-loop.py
Requires:   Python 3.11+  (we use ExceptionGroup in error reporting only;
            the core would run on 3.7+).

Acceptance criteria:
- Script runs without modification, prints a deterministic two-coroutine race.
- Wall-clock time for `main()` is ~max(0.10, 0.05) = 0.10s, not 0.15s.
- You can answer: "where does control return to the loop after `await sleep`?"
- You can extend `sleep` to support sleep(0) as a fairness checkpoint.

Reading before / during:
- PEP 492, "Coroutines with async and await syntax":
  https://peps.python.org/pep-0492/
- PEP 380, "Syntax for delegating to a subgenerator" (yield from):
  https://peps.python.org/pep-0380/
- CPython Lib/asyncio/base_events.py, function _run_once (~line 1900 in 3.13):
  https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py
- CPython Lib/asyncio/tasks.py, class Task.__step (~line 230 in 3.13):
  https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py
- CPython Lib/asyncio/futures.py, class Future (~line 50 in 3.13):
  https://github.com/python/cpython/blob/main/Lib/asyncio/futures.py
"""

from __future__ import annotations

import collections
import heapq
import time
from typing import Any, Callable, Deque, List, Optional


# -----------------------------------------------------------------------------
# Future: a value-or-exception cell with done-callbacks.
#
# State machine: PENDING -> {FINISHED, CANCELLED}. Once terminal, immutable.
# `__await__` is the awaitable bridge: yield self while pending; return result.
# -----------------------------------------------------------------------------

class Future:
    """A toy of asyncio.Future. ~40 lines."""

    __slots__ = (
        "_loop", "_state", "_result", "_exception", "_callbacks",
        "_asyncio_future_blocking",
    )

    def __init__(self, loop: "EventLoop") -> None:
        self._loop = loop
        self._state = "PENDING"
        self._result: Any = None
        self._exception: Optional[BaseException] = None
        self._callbacks: List[Callable[["Future"], None]] = []
        # The marker the Task driver reads to confirm "yes I yielded a future
        # I want you to wait on." Cite Lib/asyncio/futures.py.
        self._asyncio_future_blocking = False

    def done(self) -> bool:
        return self._state != "PENDING"

    def cancelled(self) -> bool:
        return self._state == "CANCELLED"

    def result(self) -> Any:
        if self._state == "CANCELLED":
            raise CancelledError("Future was cancelled")
        if self._state == "PENDING":
            raise RuntimeError("Result is not ready")
        if self._exception is not None:
            raise self._exception
        return self._result

    def set_result(self, value: Any) -> None:
        if self._state != "PENDING":
            raise RuntimeError(f"Future is {self._state}, cannot set_result")
        self._result = value
        self._state = "FINISHED"
        self._schedule_callbacks()

    def set_exception(self, exc: BaseException) -> None:
        if self._state != "PENDING":
            raise RuntimeError(f"Future is {self._state}, cannot set_exception")
        self._exception = exc
        self._state = "FINISHED"
        self._schedule_callbacks()

    def cancel(self) -> bool:
        if self._state != "PENDING":
            return False
        self._state = "CANCELLED"
        self._schedule_callbacks()
        return True

    def add_done_callback(self, cb: Callable[["Future"], None]) -> None:
        if self._state != "PENDING":
            # Already done: schedule the callback for the next loop iteration.
            self._loop.call_soon(cb, self)
        else:
            self._callbacks.append(cb)

    def _schedule_callbacks(self) -> None:
        callbacks, self._callbacks = self._callbacks, []
        for cb in callbacks:
            self._loop.call_soon(cb, self)

    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True
            yield self                  # the loop driver sees this
        if not self.done():
            raise RuntimeError("await did not resume on a done future")
        return self.result()


class CancelledError(BaseException):
    """Mirrors asyncio.CancelledError - inherits from BaseException so it
    is not swallowed by `except Exception`. Matches stdlib (3.8+)."""


# -----------------------------------------------------------------------------
# Handle / TimerHandle: units of scheduled work.
# -----------------------------------------------------------------------------

class Handle:
    __slots__ = ("_callback", "_args", "_cancelled")

    def __init__(self, callback: Callable[..., Any], args: tuple) -> None:
        self._callback = callback
        self._args = args
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if not self._cancelled:
            self._callback(*self._args)


class TimerHandle(Handle):
    __slots__ = ("_deadline",)

    def __init__(self, callback, args, deadline: float) -> None:
        super().__init__(callback, args)
        self._deadline = deadline

    def __lt__(self, other: "TimerHandle") -> bool:
        return self._deadline < other._deadline


# -----------------------------------------------------------------------------
# EventLoop: runnable deque + timer min-heap + one-step driver.
#
# We omit the I/O selector entirely - this loop is sleep-and-callback only.
# Exercise 2 adds I/O via aiohttp on top of the real asyncio. The mini-project
# adds I/O on top of the loop you are reading now.
# -----------------------------------------------------------------------------

class EventLoop:
    def __init__(self) -> None:
        self._ready: Deque[Handle] = collections.deque()
        self._scheduled: List[TimerHandle] = []
        self._running = False
        self._stopping = False

    def time(self) -> float:
        return time.monotonic()

    def create_future(self) -> Future:
        return Future(self)

    def call_soon(self, callback: Callable[..., Any], *args: Any) -> Handle:
        h = Handle(callback, args)
        self._ready.append(h)
        return h

    def call_later(
        self, delay: float, callback: Callable[..., Any], *args: Any
    ) -> TimerHandle:
        deadline = self.time() + max(0.0, delay)
        h = TimerHandle(callback, args, deadline)
        heapq.heappush(self._scheduled, h)
        return h

    def stop(self) -> None:
        self._stopping = True

    def _run_once(self) -> None:
        # Phase 1: drain expired timers.
        now = self.time()
        sched = self._scheduled
        while sched and sched[0]._deadline <= now:
            handle = heapq.heappop(sched)
            self._ready.append(handle)

        # Phase 2: if we have nothing to do but a future timer exists, idle.
        if not self._ready:
            if sched:
                wait_for = max(0.0, sched[0]._deadline - now)
                time.sleep(wait_for)
                return                  # let the next iteration drain
            # Nothing ready, no timer: stop (a real loop would block in select).
            self._stopping = True
            return

        # Phase 3: drain the runnable queue exactly once.
        ntodo = len(self._ready)
        for _ in range(ntodo):
            handle = self._ready.popleft()
            handle.run()

    def run_until_complete(self, coro_or_future: Any) -> Any:
        if isinstance(coro_or_future, Future):
            future = coro_or_future
        else:
            future = Task(coro_or_future, self)

        future.add_done_callback(lambda _f: self.stop())
        self._running = True
        self._stopping = False
        try:
            while not self._stopping:
                self._run_once()
        finally:
            self._running = False
        return future.result()


# -----------------------------------------------------------------------------
# Task: drives a coroutine to completion against the loop.
# -----------------------------------------------------------------------------

class Task(Future):
    __slots__ = ("_coro", "_fut_waiter")

    def __init__(self, coro, loop: EventLoop) -> None:
        super().__init__(loop)
        self._coro = coro
        self._fut_waiter: Optional[Future] = None
        loop.call_soon(self._step)

    def _step(self, _previous: Optional[Future] = None) -> None:
        exc: Optional[BaseException] = None
        if _previous is not None:
            if _previous.cancelled():
                exc = CancelledError()
            else:
                # Future has a result (possibly an exception).
                e = _previous._exception
                if e is not None:
                    exc = e
        self._fut_waiter = None

        try:
            if exc is None:
                result = self._coro.send(None)
            else:
                result = self._coro.throw(exc)
        except StopIteration as stop:
            # Coroutine finished cleanly.
            self.set_result(stop.value)
            return
        except CancelledError:
            super().cancel()
            return
        except BaseException as e:
            self.set_exception(e)
            return

        # The coroutine yielded. By asyncio convention it's a Future-like.
        if isinstance(result, Future):
            if not result._asyncio_future_blocking:
                self.set_exception(
                    RuntimeError(
                        f"yielded future {result!r} did not set "
                        "_asyncio_future_blocking"
                    )
                )
                return
            result._asyncio_future_blocking = False
            self._fut_waiter = result
            result.add_done_callback(self._step)
        elif result is None:
            # Bare `yield` (e.g., from a sleep(0)). Re-schedule next tick.
            self._loop.call_soon(self._step)
        else:
            self.set_exception(
                RuntimeError(f"Task got bad yield: {result!r}")
            )


# -----------------------------------------------------------------------------
# sleep: schedule a callback for `now + delay`, await the future it completes.
# -----------------------------------------------------------------------------

def sleep(seconds: float, result: Any = None) -> Future:
    """Suspend the current task for `seconds`. Returns a Future to await.

    Real asyncio.sleep is a coroutine. Here we return the future directly so
    callers do `await sleep(0.1)` - the awaitable protocol does the rest.
    """
    loop = _current_loop
    if loop is None:
        raise RuntimeError("sleep called outside of a running loop")
    future = loop.create_future()
    loop.call_later(seconds, future.set_result, result)
    return future


# Single-loop registry. Real asyncio uses a thread-local and a policy.
_current_loop: Optional[EventLoop] = None


def run(coro) -> Any:
    """The entry point. Mirrors asyncio.run."""
    global _current_loop
    if _current_loop is not None:
        raise RuntimeError("nested run() not supported in this toy")
    loop = EventLoop()
    _current_loop = loop
    try:
        return loop.run_until_complete(coro)
    finally:
        _current_loop = None


# -----------------------------------------------------------------------------
# Demo: two coroutines racing to a finish. The whole point of the toy.
# -----------------------------------------------------------------------------

async def worker(name: str, seconds: float) -> str:
    t0 = _current_loop.time()
    print(f"  [{t0:6.3f}] {name}: starting, will sleep {seconds:.3f}s")
    await sleep(seconds)
    t1 = _current_loop.time()
    print(f"  [{t1:6.3f}] {name}: done after {t1 - t0:.3f}s")
    return name


async def main() -> str:
    """Kick two workers off concurrently, wait for both."""
    t_a = Task(worker("A", 0.10), _current_loop)
    t_b = Task(worker("B", 0.05), _current_loop)
    a = await t_a
    b = await t_b
    return f"{a} and {b} both finished"


def demo() -> None:
    print(f"--- Toy event loop demo ---")
    print(f"Two workers, sleeps 0.10s and 0.05s.")
    print(f"Wall-clock should be ~0.10s (concurrent), not 0.15s (serial).")
    print()
    t0 = time.monotonic()
    result = run(main())
    elapsed = time.monotonic() - t0
    print()
    print(f"Result:  {result!r}")
    print(f"Elapsed: {elapsed:.3f}s")
    print()
    assert elapsed < 0.13, (
        f"Workers ran serially ({elapsed:.3f}s) - check the Task scheduling"
    )


if __name__ == "__main__":
    demo()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT
# -----------------------------------------------------------------------------
# --- Toy event loop demo ---
# Two workers, sleeps 0.10s and 0.05s.
# Wall-clock should be ~0.10s (concurrent), not 0.15s (serial).
#
#   [ 0.000] A: starting, will sleep 0.100s
#   [ 0.000] B: starting, will sleep 0.050s
#   [ 0.050] B: done after 0.050s
#   [ 0.100] A: done after 0.100s
#
# Result:  'A and B both finished'
# Elapsed: 0.101s
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Trace the exact moment control returns to the loop in `worker(...)`.
#    Answer: inside `sleep(seconds)`, the returned Future is awaited; its
#    __await__ yields `self` (the future). The yield exits the await
#    expression, exits worker(), exits coro.send(None), and lands in
#    Task._step which registers `self._step` as a done-callback on the
#    future, sets _fut_waiter, and returns. Control is now back inside
#    EventLoop._run_once, draining the next ready handle.
#
# 2. Why is the wall-clock 0.10s and not 0.15s?
#    Answer: both workers entered their sleeps before either timer fired.
#    The timers overlap on the wall-clock. A's deadline is t=0.10 and B's
#    is t=0.05; B completes first, then A. The sleeps share time.
#
# 3. What happens if you replace `sleep(0.10)` with `time.sleep(0.10)` in
#    worker("A", ...)?
#    Answer: time.sleep blocks the only thread, freezing the entire loop
#    for 100ms. B's timer fires no callbacks during that time. Wall-clock
#    becomes 0.15s. This is the canonical "do not call blocking code from
#    async" failure mode.
#
# 4. (Stretch) Add a `gather(*coros)` helper that runs N coroutines, returns
#    a Future that completes when all do. ~25 lines. See lecture 3 §3.
#
# 5. (Stretch) Add I/O: register a TCP socket with selectors.DefaultSelector
#    inside _run_once, complete a Future when the fd is readable. ~40 lines
#    more. The mini-project does this.
#
# 6. (Stretch) Add proper cancellation: `task.cancel()` cancels the
#    _fut_waiter, throws CancelledError into the coroutine on next step.
#    The skeleton above does NOT cancel the underlying timer - find the bug
#    and fix it. Hint: TimerHandle.cancel() exists, no one calls it.
# -----------------------------------------------------------------------------
