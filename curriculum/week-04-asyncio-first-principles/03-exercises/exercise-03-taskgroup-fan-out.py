"""
Exercise 3 - asyncio.TaskGroup fan-out and ExceptionGroup

Goal: watch what TaskGroup actually does when one child fails. The promise
      is "structured concurrency": when child B raises, children A and C are
      cancelled, their finally-blocks run, the group waits for all of them,
      then re-raises an ExceptionGroup with every collected error.

Compare to asyncio.gather, where the same scenario leaves you with surviving
tasks that you must remember to cancel manually, and which - by default -
raises only the FIRST exception, swallowing the others.

This is the single most important change to asyncio between 3.10 and 3.11:
the PEP 654 / TaskGroup model is what every new asyncio program should use.

Estimated time: 45 minutes.

Run with:   python exercise-03-taskgroup-fan-out.py
Requires:   Python 3.11+  (TaskGroup, ExceptionGroup, except*).

Acceptance criteria:
- Script runs without modification, prints both the TaskGroup behavior and
  the legacy gather() behavior side by side.
- You can articulate the THREE differences:
    (a) gather's default is fail-first; TaskGroup waits for cancellation.
    (b) gather raises ONE error; TaskGroup raises a group of ALL of them.
    (c) gather leaks unfinished tasks on early failure; TaskGroup does not.
- You can use `except* SomeError` correctly and explain what it catches.

Reading before / during:
- PEP 654, "Exception Groups and except*":
  https://peps.python.org/pep-0654/
- asyncio Task Groups:
  https://docs.python.org/3/library/asyncio-task.html#task-groups
- Nathaniel J. Smith, "Notes on structured concurrency" (the philosophy):
  https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/
- CPython Lib/asyncio/taskgroups.py (the implementation):
  https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import List


# -----------------------------------------------------------------------------
# The three workers. A and C are well-behaved sleepers; B fails after a short
# delay. We instrument every worker so we can SEE when the cancellations land.
# -----------------------------------------------------------------------------

_log: List[str] = []
_t0 = 0.0


def _log_line(msg: str) -> None:
    t = time.monotonic() - _t0
    line = f"[{t:6.3f}s] {msg}"
    _log.append(line)
    print(line, flush=True)


async def well_behaved(name: str, seconds: float) -> str:
    """Sleep, then return. With try/finally so we can observe cancellation."""
    _log_line(f"{name}: started, will sleep {seconds}s")
    try:
        await asyncio.sleep(seconds)
        _log_line(f"{name}: woke up cleanly, returning")
        return name
    except asyncio.CancelledError:
        _log_line(f"{name}: CANCELLED (mid-sleep)")
        raise
    finally:
        _log_line(f"{name}: finally block running cleanup")


async def fails_after(name: str, delay: float, exc: Exception) -> str:
    """Sleep `delay` then raise `exc`. Used to provoke group cancellation."""
    _log_line(f"{name}: started, will fail in {delay}s with {type(exc).__name__}")
    await asyncio.sleep(delay)
    _log_line(f"{name}: raising {type(exc).__name__}({exc!s})")
    raise exc


async def also_fails_after(name: str, delay: float, exc: Exception) -> str:
    """A second simultaneous failure - to show TaskGroup collects BOTH."""
    return await fails_after(name, delay, exc)


# -----------------------------------------------------------------------------
# Scenario 1: asyncio.TaskGroup with three children, one fails.
# -----------------------------------------------------------------------------

async def scenario_taskgroup() -> None:
    """One TaskGroup, three children. Child B raises after 0.05s."""
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 1: asyncio.TaskGroup ====")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(well_behaved("A", 0.20), name="A")
            tg.create_task(fails_after("B", 0.05, ValueError("B blew up")), name="B")
            tg.create_task(well_behaved("C", 0.30), name="C")
        # If we get here, no errors. We will NOT get here in this scenario.
        _log_line("TaskGroup completed normally (unexpected!)")
    except* ValueError as eg:
        # PEP 654: except* matches by exception type *inside* the group,
        # leaves other types as a residual group that propagates if uncaught.
        _log_line(f"caught ExceptionGroup of ValueErrors: {[str(e) for e in eg.exceptions]}")
    _log_line("scenario_taskgroup: after the async with")


# -----------------------------------------------------------------------------
# Scenario 2: TaskGroup with TWO simultaneously-failing children. Both errors
# survive into the ExceptionGroup. gather() would have lost one.
# -----------------------------------------------------------------------------

async def scenario_taskgroup_multi() -> None:
    """Two simultaneous failures + one well-behaved. Verify NO error is lost."""
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 2: TaskGroup with two simultaneous failures ====")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(well_behaved("A", 0.20), name="A")
            tg.create_task(fails_after("B", 0.05, ValueError("B blew up")), name="B")
            tg.create_task(also_fails_after("D", 0.05, TypeError("D blew up too")), name="D")
    except* ValueError as eg:
        _log_line(f"caught ValueErrors:  {[str(e) for e in eg.exceptions]}")
    except* TypeError as eg:
        _log_line(f"caught TypeErrors:   {[str(e) for e in eg.exceptions]}")
    _log_line("scenario_taskgroup_multi: after the async with")


# -----------------------------------------------------------------------------
# Scenario 3: legacy asyncio.gather with the same set of children. Watch:
# (a) only the FIRST raised exception bubbles out; the other is swallowed.
# (b) the well-behaved sibling A still gets its `finally` block run only
#     because we explicitly catch and cancel - if we forgot to cancel, A
#     would leak.
# -----------------------------------------------------------------------------

async def scenario_gather() -> None:
    """Same three children, via gather. Note the missing error."""
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 3: asyncio.gather (legacy) ====")
    coros = [
        well_behaved("A", 0.20),
        fails_after("B", 0.05, ValueError("B blew up")),
        also_fails_after("D", 0.05, TypeError("D blew up too")),
    ]
    try:
        await asyncio.gather(*coros)
    except (ValueError, TypeError) as e:
        # gather raises EXACTLY ONE exception (the first one received).
        # The other is dropped on the floor.
        _log_line(f"caught a single exception: {type(e).__name__}({e!s})")
        _log_line("the OTHER exception (the one we didn't catch) is gone forever.")
    _log_line("scenario_gather: after the gather")


# -----------------------------------------------------------------------------
# Scenario 4: gather with return_exceptions=True - the "give me everything"
# mode. Errors are returned as values in the result list, not raised. No
# cancellation happens. All tasks run to completion. Sometimes that's what
# you want; usually it isn't.
# -----------------------------------------------------------------------------

async def scenario_gather_return_exceptions() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 4: gather(return_exceptions=True) ====")
    coros = [
        well_behaved("A", 0.20),
        fails_after("B", 0.05, ValueError("B blew up")),
        also_fails_after("D", 0.05, TypeError("D blew up too")),
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)
    _log_line("gather returned a list (no raise). Items:")
    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            _log_line(f"  [{i}] EXCEPTION {type(r).__name__}({r!s})")
        else:
            _log_line(f"  [{i}] OK {r!r}")
    _log_line("scenario_gather_return_exceptions: after the gather")


# -----------------------------------------------------------------------------
# Main: run all four scenarios. Verify the comparative behavior.
# -----------------------------------------------------------------------------

async def main() -> None:
    await scenario_taskgroup()
    print()
    await scenario_taskgroup_multi()
    print()
    await scenario_gather()
    print()
    await scenario_gather_return_exceptions()
    print()
    print("Done. Read the [A: finally block running cleanup] lines carefully.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer (TaskGroup, "
            "ExceptionGroup, except*). "
            f"You are on {sys.version.split()[0]}."
        )
    asyncio.run(main())


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (timings are approximate)
# -----------------------------------------------------------------------------
# [ 0.000s] ==== Scenario 1: asyncio.TaskGroup ====
# [ 0.000s] A: started, will sleep 0.2s
# [ 0.000s] B: started, will fail in 0.05s with ValueError
# [ 0.000s] C: started, will sleep 0.3s
# [ 0.050s] B: raising ValueError(B blew up)
# [ 0.050s] A: CANCELLED (mid-sleep)
# [ 0.050s] A: finally block running cleanup
# [ 0.050s] C: CANCELLED (mid-sleep)
# [ 0.050s] C: finally block running cleanup
# [ 0.050s] caught ExceptionGroup of ValueErrors: ['B blew up']
# [ 0.050s] scenario_taskgroup: after the async with
#
# [ 0.000s] ==== Scenario 2: TaskGroup with two simultaneous failures ====
# [ 0.000s] A: started, will sleep 0.2s
# [ 0.000s] B: started, will fail in 0.05s with ValueError
# [ 0.000s] D: started, will fail in 0.05s with TypeError
# [ 0.050s] B: raising ValueError(B blew up)
# [ 0.050s] D: raising TypeError(D blew up too)
# [ 0.050s] A: CANCELLED (mid-sleep)
# [ 0.050s] A: finally block running cleanup
# [ 0.050s] caught ValueErrors:  ['B blew up']
# [ 0.050s] caught TypeErrors:   ['D blew up too']
# [ 0.050s] scenario_taskgroup_multi: after the async with
#
# [ 0.000s] ==== Scenario 3: asyncio.gather (legacy) ====
# [ 0.000s] A: started, will sleep 0.2s
# [ 0.000s] B: started, will fail in 0.05s with ValueError
# [ 0.000s] D: started, will fail in 0.05s with TypeError
# [ 0.050s] B: raising ValueError(B blew up)
# [ 0.050s] D: raising TypeError(D blew up too)
# [ 0.050s] caught a single exception: ValueError(B blew up)
# [ 0.050s] the OTHER exception (the one we didn't catch) is gone forever.
# [ 0.050s] scenario_gather: after the gather
#
#   ^^^ Notice: A's finally block did not run in scenario 3. A is now a leaked
#       Task running in the background. gather did NOT cancel it for us. This
#       is a real bug shape in pre-3.11 asyncio code.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. In Scenario 1, at what wall-clock time does A's finally block run?
#    Answer: ~0.05s, the same instant B raises. TaskGroup observes B's
#    failure, calls _abort, which cancels each pending child, which throws
#    CancelledError into A's current await. A's finally runs immediately.
#
# 2. In Scenario 3, A is still running after the except clause. How would
#    you observe this? Hint: asyncio.all_tasks() returns the set of all
#    pending tasks in the current loop.
#
# 3. Why does `except* ValueError` work in Scenario 2 even though the group
#    also contains a TypeError? Answer: PEP 654 specifies that except*
#    splits the group: it catches all matching members, re-raises the rest
#    as a new (smaller) ExceptionGroup. If the rest is uncaught, it
#    propagates upward.
#
# 4. Why does Scenario 4 (`return_exceptions=True`) take 0.30s (long) and
#    not 0.05s? Answer: because gather does NOT cancel siblings in that
#    mode. C and A are allowed to run to completion. The "give me
#    everything" mode pays full wall-clock cost.
#
# 5. (Stretch) Replace asyncio.TaskGroup with a Trio nursery (you'll need
#    `pip install trio`). Trio invented this pattern. Compare the cancel
#    semantics; they are very similar.
#
# 6. (Stretch) Write a function `run_all(*coros)` that has the TaskGroup
#    semantics but a flatter API: `await run_all(coro1(), coro2(), ...)`.
#    Useful when the `async with` block is too verbose for inline use.
# -----------------------------------------------------------------------------
