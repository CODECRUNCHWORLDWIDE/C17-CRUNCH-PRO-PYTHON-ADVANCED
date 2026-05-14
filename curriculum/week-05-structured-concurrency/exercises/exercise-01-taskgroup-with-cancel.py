"""
Exercise 1 - TaskGroup with external cancellation

Goal: confirm in code that asyncio.TaskGroup propagates cancellation in
      exactly the way Lecture 1 described. We run a TaskGroup with three
      children. From a fourth, independent task we call .cancel() on one of
      the children mid-flight, and observe:

        (a) the cancelled child's `finally` runs;
        (b) the OTHER two children continue normally - this is NOT a sibling
            cancellation because a manual .cancel() of a single Task is not
            the same thing as a child RAISING. The group only cascades on
            an unhandled non-CancelledError exception in a child;
        (c) on exit, the TaskGroup does NOT raise an ExceptionGroup -
            because no child raised an unhandled error;
        (d) the cancelled child's done state is `cancelled() == True`.

That last point is the load-bearing observation. Read the asyncio docs on
TaskGroup carefully: "if any of the tasks in the group fails with an
exception other than asyncio.CancelledError, the remaining tasks in the
group will be cancelled." Plain CancelledError on a single child does not
trigger the cascade. (Otherwise structured timeouts could not coexist with
TaskGroup at all.)

We then run a second scenario where one child RAISES (not just cancels)
and verify the cascade *does* fire and an ExceptionGroup surfaces.

Estimated time: 45 minutes.

Run with:   python exercise-01-taskgroup-with-cancel.py
Requires:   Python 3.11+ (TaskGroup, ExceptionGroup, except*).

Acceptance criteria:
- Script runs end-to-end, prints two scenario traces.
- You can articulate the THREE rules:
    1. A child cancelled via task.cancel() does NOT cascade to siblings.
    2. A child raising an unhandled non-CancelledError DOES cascade.
    3. In both cases, the cancelled child's `finally` block runs.
- You can point to `Lib/asyncio/taskgroups.py:_on_task_done` and explain
  the `if task.cancelled(): return` branch and what it means.

Reading before / during:
- Lecture 1 sections 3 (the _on_task_done logic) and 8 (rules table).
- CPython Lib/asyncio/taskgroups.py:
  https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py
- asyncio TaskGroup docs:
  https://docs.python.org/3/library/asyncio-task.html#task-groups
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import List

# -----------------------------------------------------------------------------
# Instrumentation. We log to a list AND to stdout so the trace is captured.
# -----------------------------------------------------------------------------

_log: List[str] = []
_t0: float = 0.0


def _log_line(msg: str) -> None:
    t = time.monotonic() - _t0
    line = f"[{t:6.3f}s] {msg}"
    _log.append(line)
    print(line, flush=True)


# -----------------------------------------------------------------------------
# The well-behaved worker. Sleeps. Logs on entry, exit, cancellation, and in
# its finally block. Returns its name when it completes.
# -----------------------------------------------------------------------------


async def well_behaved(name: str, seconds: float) -> str:
    _log_line(f"{name}: started, will sleep {seconds}s")
    try:
        await asyncio.sleep(seconds)
        _log_line(f"{name}: woke up cleanly, returning")
        return name
    except asyncio.CancelledError:
        _log_line(f"{name}: CANCELLED (mid-sleep)")
        raise
    finally:
        _log_line(f"{name}: finally block running")


async def fails_after(name: str, delay: float, exc: Exception) -> str:
    _log_line(f"{name}: started, will fail in {delay}s with {type(exc).__name__}")
    try:
        await asyncio.sleep(delay)
        _log_line(f"{name}: raising {type(exc).__name__}({exc!s})")
        raise exc
    finally:
        _log_line(f"{name}: finally block running")


# -----------------------------------------------------------------------------
# Scenario 1: external .cancel() on ONE child of a TaskGroup.
#
# We open a TaskGroup with three children A, B, C. From a fourth task
# (the "killer") that lives OUTSIDE the group, we wait briefly, then call
# B.cancel(). We expect: B is cancelled (its finally runs), A and C are
# unaffected, the group exits normally.
# -----------------------------------------------------------------------------


async def killer(target: asyncio.Task, after: float) -> None:
    """Wait `after` seconds, then cancel `target`."""
    _log_line(f"killer: waiting {after}s before cancelling {target.get_name()!r}")
    await asyncio.sleep(after)
    _log_line(f"killer: calling target.cancel() on {target.get_name()!r}")
    target.cancel()


async def scenario_external_cancel() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 1: external cancel of ONE child ====")
    # Hold a reference to the to-be-cancelled task. We capture it from the
    # return value of tg.create_task, which is a real asyncio.Task.
    b_task: asyncio.Task[str] | None = None
    killer_task: asyncio.Task[None] | None = None
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(well_behaved("A", 0.20), name="A")
            b_task = tg.create_task(well_behaved("B", 0.20), name="B")
            tg.create_task(well_behaved("C", 0.20), name="C")
            # The killer lives OUTSIDE the group on purpose - if it lived
            # INSIDE, the group would also wait for it (which is fine) but
            # we want to emphasise that the cancel call comes from a peer.
            assert b_task is not None
            killer_task = asyncio.create_task(killer(b_task, 0.05), name="killer")
        _log_line("scenario 1: TaskGroup exited NORMALLY (no ExceptionGroup raised)")
    except* asyncio.CancelledError as eg:
        # We do not expect this branch to fire. If it does, our model is
        # wrong; investigate.
        _log_line(f"scenario 1: UNEXPECTED ExceptionGroup of CancelledError: {eg!r}")
    # Wait for the orphan killer task to finish (it has nothing to do at
    # this point, but it is good hygiene to await it).
    if killer_task is not None:
        await killer_task

    assert b_task is not None
    _log_line(f"scenario 1: B.cancelled() = {b_task.cancelled()}")
    _log_line(f"scenario 1: B.done()      = {b_task.done()}")


# -----------------------------------------------------------------------------
# Scenario 2: a child of the TaskGroup RAISES. The full cancel cascade
# should fire, and an ExceptionGroup should surface on __aexit__.
# -----------------------------------------------------------------------------


async def scenario_internal_raise() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 2: child RAISES, cascade fires ====")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(well_behaved("A", 0.20), name="A")
            tg.create_task(fails_after("B", 0.05, ValueError("B blew up")), name="B")
            tg.create_task(well_behaved("C", 0.20), name="C")
        _log_line("scenario 2: TaskGroup exited normally (UNEXPECTED!)")
    except* ValueError as eg:
        names = [str(e) for e in eg.exceptions]
        _log_line(f"scenario 2: caught ExceptionGroup of ValueErrors: {names}")
    _log_line("scenario 2: done")


# -----------------------------------------------------------------------------
# Scenario 3: the cancelled child's CancelledError surfaces. To see this we
# create a Task OUTSIDE the group, cancel it, and await it; the task itself
# raises CancelledError. Contrast with Scenario 1 where the cancellation was
# absorbed by the TaskGroup (which does NOT re-raise a CancelledError for a
# single externally-cancelled child).
# -----------------------------------------------------------------------------


async def scenario_standalone_cancel() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 3: standalone task cancelled, sees its own CancelledError ====")
    t = asyncio.create_task(well_behaved("X", 0.20), name="X")
    await asyncio.sleep(0.05)
    _log_line("scenario 3: cancelling X")
    t.cancel()
    try:
        await t
        _log_line("scenario 3: X finished without raising (unexpected!)")
    except asyncio.CancelledError:
        _log_line("scenario 3: caught CancelledError from awaiting X")
    _log_line(f"scenario 3: X.cancelled() = {t.cancelled()}")


# -----------------------------------------------------------------------------
# Scenario 4 (deeper): a child of the TaskGroup is cancelled AND then
# the group also has a separate child that raises. The group should still
# fire the cascade, and the ExceptionGroup contains the raised exception.
# The cancelled child is NOT contributed to the group as an error.
# -----------------------------------------------------------------------------


async def scenario_cancel_and_raise() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 4: child cancelled AND another child raises ====")
    b_task: asyncio.Task[str] | None = None
    killer_task: asyncio.Task[None] | None = None
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(well_behaved("A", 0.30), name="A")
            b_task = tg.create_task(well_behaved("B", 0.30), name="B")
            tg.create_task(fails_after("D", 0.10, RuntimeError("D blew up")), name="D")
            assert b_task is not None
            killer_task = asyncio.create_task(killer(b_task, 0.05), name="killer")
    except* RuntimeError as eg:
        msgs = [str(e) for e in eg.exceptions]
        _log_line(f"scenario 4: caught RuntimeErrors: {msgs}")
    except* asyncio.CancelledError as eg:
        msgs = [type(e).__name__ for e in eg.exceptions]
        _log_line(f"scenario 4: caught CancelledErrors (UNEXPECTED): {msgs}")
    if killer_task is not None:
        await killer_task
    assert b_task is not None
    _log_line(f"scenario 4: B.cancelled() = {b_task.cancelled()}")


# -----------------------------------------------------------------------------
# Main: run all four scenarios and print a closing summary.
# -----------------------------------------------------------------------------


async def main() -> None:
    await scenario_external_cancel()
    print()
    await scenario_internal_raise()
    print()
    await scenario_standalone_cancel()
    print()
    await scenario_cancel_and_raise()
    print()
    print("Done. Re-read the [B: finally block running] lines and verify the rules.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer (TaskGroup, "
            "ExceptionGroup, except*). "
            f"You are on {sys.version.split()[0]}."
        )
    asyncio.run(main())


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (timings approximate)
# -----------------------------------------------------------------------------
# [ 0.000s] ==== Scenario 1: external cancel of ONE child ====
# [ 0.000s] A: started, will sleep 0.2s
# [ 0.000s] B: started, will sleep 0.2s
# [ 0.000s] C: started, will sleep 0.2s
# [ 0.000s] killer: waiting 0.05s before cancelling 'B'
# [ 0.050s] killer: calling target.cancel() on 'B'
# [ 0.050s] B: CANCELLED (mid-sleep)
# [ 0.050s] B: finally block running
# [ 0.200s] A: woke up cleanly, returning
# [ 0.200s] A: finally block running
# [ 0.200s] C: woke up cleanly, returning
# [ 0.200s] C: finally block running
# [ 0.200s] scenario 1: TaskGroup exited NORMALLY (no ExceptionGroup raised)
# [ 0.200s] scenario 1: B.cancelled() = True
# [ 0.200s] scenario 1: B.done()      = True
#
# [ 0.000s] ==== Scenario 2: child RAISES, cascade fires ====
# [ 0.000s] A: started, will sleep 0.2s
# [ 0.000s] B: started, will fail in 0.05s with ValueError
# [ 0.000s] C: started, will sleep 0.2s
# [ 0.050s] B: raising ValueError(B blew up)
# [ 0.050s] B: finally block running
# [ 0.050s] A: CANCELLED (mid-sleep)
# [ 0.050s] A: finally block running
# [ 0.050s] C: CANCELLED (mid-sleep)
# [ 0.050s] C: finally block running
# [ 0.050s] scenario 2: caught ExceptionGroup of ValueErrors: ['B blew up']
# [ 0.050s] scenario 2: done
#
# [ 0.000s] ==== Scenario 3: standalone task cancelled, sees its own CancelledError ====
# [ 0.000s] X: started, will sleep 0.2s
# [ 0.050s] scenario 3: cancelling X
# [ 0.050s] X: CANCELLED (mid-sleep)
# [ 0.050s] X: finally block running
# [ 0.050s] scenario 3: caught CancelledError from awaiting X
# [ 0.050s] scenario 3: X.cancelled() = True
#
# [ 0.000s] ==== Scenario 4: child cancelled AND another child raises ====
# [ 0.000s] A: started, will sleep 0.3s
# [ 0.000s] B: started, will sleep 0.3s
# [ 0.000s] D: started, will fail in 0.1s with RuntimeError
# [ 0.000s] killer: waiting 0.05s before cancelling 'B'
# [ 0.050s] killer: calling target.cancel() on 'B'
# [ 0.050s] B: CANCELLED (mid-sleep)
# [ 0.050s] B: finally block running
# [ 0.100s] D: raising RuntimeError(D blew up)
# [ 0.100s] D: finally block running
# [ 0.100s] A: CANCELLED (mid-sleep)
# [ 0.100s] A: finally block running
# [ 0.100s] scenario 4: caught RuntimeErrors: ['D blew up']
# [ 0.100s] scenario 4: B.cancelled() = True
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Scenario 1: why did A and C run to completion despite B being cancelled?
#    Answer: a single .cancel() on a child does not raise out of the group;
#    the child terminates with cancelled() == True and `_on_task_done` sees
#    `task.cancelled()` and returns early without invoking `_abort`. Read
#    Lib/asyncio/taskgroups.py:_on_task_done, the very first non-`discard` line.
#
# 2. Scenario 2: how is `except* ValueError` matching even though the raised
#    exception was a single ValueError? Answer: the TaskGroup wraps every
#    collected error in a BaseExceptionGroup on the way out (PEP 654 §2.5).
#    Even one error becomes a one-element group.
#
# 3. Scenario 4: why is B not contributed to the ExceptionGroup? Answer:
#    `_on_task_done` skips cancelled tasks. The ExceptionGroup contains only
#    the *unhandled non-CancelledError* exceptions. B's cancellation runs
#    its finally and is otherwise invisible to the group's error accounting.
#
# 4. (Stretch) Modify Scenario 1 so the killer cancels B with a custom
#    message: `target.cancel("test reason")`. Confirm that inside B the
#    exception args reflect this message: `except CancelledError as e:
#    print(e.args)`. (3.9+ supports the message argument.)
#
# 5. (Stretch) Add a fifth scenario where the WHOLE async function
#    `scenario_external_cancel` is cancelled from outside (the equivalent
#    of Ctrl-C on the program). Verify the TaskGroup propagates that
#    cancellation to every child. Use `asyncio.timeout(0.02)` around the
#    `async with` to force the cancel.
# -----------------------------------------------------------------------------
