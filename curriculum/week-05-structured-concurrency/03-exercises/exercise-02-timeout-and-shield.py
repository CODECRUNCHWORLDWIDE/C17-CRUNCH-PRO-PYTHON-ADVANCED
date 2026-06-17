"""
Exercise 2 - asyncio.timeout, asyncio.shield, and the cancelling counter

Goal: confirm in code the exact semantics of:

    1. asyncio.timeout(s) - the 3.11+ context manager. Fires .cancel() on
       the current task at deadline; on __aexit__, calls task.uncancel()
       to absorb its own cancel; re-raises TimeoutError to the caller.

    2. asyncio.shield(coro) - protects the INNER coroutine from outer
       cancellation. The outer awaiter raises CancelledError; the inner
       task continues to run on the loop.

    3. Task.cancelling() / Task.uncancel() - the integer counter that
       lets nested timeouts compose. Pre-3.11 this did not exist and
       nested wait_for races could "steal" each other's timeouts.

We run four scenarios. Each prints the value of `current_task().cancelling()`
at key checkpoints so you can SEE the counter move.

Estimated time: 45 minutes.

Run with:   python exercise-02-timeout-and-shield.py
Requires:   Python 3.11+ (asyncio.timeout, Task.uncancel, Task.cancelling).

Acceptance criteria:
- Script runs end-to-end, prints four scenario traces.
- You can articulate THREE facts:
    1. Inside `async with asyncio.timeout(5):`, the task's `cancelling()`
       counter is 0 until the deadline fires. After the deadline fires the
       counter is >= 1. After __aexit__ runs, the counter is back to its
       pre-block value (the timeout absorbs its own cancel via uncancel).
    2. asyncio.shield does NOT cancel the inner task when the outer is
       cancelled. The inner task survives; you can verify by inspecting
       its `.done()` state after the outer raises.
    3. asyncio.timeout raises TimeoutError to the caller, NOT CancelledError.
       The CancelledError is converted in `Timeout.__aexit__` after the
       uncancel call.
- You can read Lib/asyncio/timeouts.py:_on_timeout and Timeout.__aexit__
  and identify the role of every line.

Reading before / during:
- Lecture 2 sections 3-6.
- CPython Lib/asyncio/timeouts.py:
  https://github.com/python/cpython/blob/main/Lib/asyncio/timeouts.py
- CPython Lib/asyncio/tasks.py (shield, Task.uncancel):
  https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import List

_log: List[str] = []
_t0: float = 0.0


def _log_line(msg: str) -> None:
    t = time.monotonic() - _t0
    line = f"[{t:6.3f}s] {msg}"
    _log.append(line)
    print(line, flush=True)


def _counter() -> int:
    """Return the current task's pending-cancellation count, or -1 if no task."""
    t = asyncio.current_task()
    if t is None:
        return -1
    return t.cancelling()


# -----------------------------------------------------------------------------
# Scenario 1: a single asyncio.timeout that does NOT expire. The block
# completes cleanly; the counter never moves; no exception is raised.
# -----------------------------------------------------------------------------


async def scenario_no_expiry() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 1: asyncio.timeout, deadline NOT reached ====")
    _log_line(f"before timeout block: cancelling()={_counter()}")
    async with asyncio.timeout(0.50):
        _log_line(f"inside timeout block, before sleep: cancelling()={_counter()}")
        await asyncio.sleep(0.10)
        _log_line(f"inside timeout block, after sleep: cancelling()={_counter()}")
    _log_line(f"after timeout block: cancelling()={_counter()}")


# -----------------------------------------------------------------------------
# Scenario 2: a single asyncio.timeout that DOES expire. The block is
# cancelled at the deadline; the counter goes to 1; __aexit__ calls
# uncancel() returning it to 0; TimeoutError is raised to the caller.
# -----------------------------------------------------------------------------


async def scenario_expires() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 2: asyncio.timeout, deadline REACHED ====")
    _log_line(f"before timeout block: cancelling()={_counter()}")
    try:
        async with asyncio.timeout(0.05):
            _log_line(f"inside timeout block, before sleep: cancelling()={_counter()}")
            try:
                await asyncio.sleep(0.50)
            except asyncio.CancelledError:
                _log_line(
                    f"inner caught CancelledError. cancelling()={_counter()} "
                    f"(should be >= 1; the timeout has issued its cancel)"
                )
                raise
        _log_line("scenario 2: did NOT raise (unexpected!)")
    except TimeoutError:
        # Note: not CancelledError. The conversion happens in Timeout.__aexit__.
        _log_line(
            f"caller saw TimeoutError. cancelling()={_counter()} "
            f"(should be 0; the timeout absorbed its own cancel)"
        )


# -----------------------------------------------------------------------------
# Scenario 3: nested asyncio.timeout blocks. The INNER deadline fires
# first; only it raises TimeoutError; the outer block sees TimeoutError as
# an ordinary exception (not its own cancellation) and propagates it.
#
# Verify: at no point does a stray CancelledError leak. The counter on the
# task should be back to 0 at the end of the outer block.
# -----------------------------------------------------------------------------


async def scenario_nested() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 3: nested asyncio.timeout ====")
    _log_line(f"before outer: cancelling()={_counter()}")
    try:
        async with asyncio.timeout(1.0):                # OUTER: 1.0s
            _log_line(f"inside outer, before inner: cancelling()={_counter()}")
            try:
                async with asyncio.timeout(0.05):       # INNER: 0.05s
                    _log_line(f"inside inner, before sleep: cancelling()={_counter()}")
                    await asyncio.sleep(0.50)
                _log_line("inside outer, inner did NOT raise (unexpected!)")
            except TimeoutError:
                _log_line(
                    f"inside outer, caught INNER TimeoutError. "
                    f"cancelling()={_counter()} (should be 0)"
                )
            _log_line(f"inside outer, after inner block: cancelling()={_counter()}")
            await asyncio.sleep(0.05)
            _log_line(f"inside outer, after extra sleep: cancelling()={_counter()}")
    except TimeoutError:
        _log_line("outer also raised TimeoutError (unexpected for these timings!)")
    _log_line(f"after outer: cancelling()={_counter()}")


# -----------------------------------------------------------------------------
# Scenario 4: asyncio.shield protects an inner task from outer cancellation.
# We wrap a 0.5s sleep in a shield, then time out the outer at 0.05s. The
# outer raises TimeoutError, but the inner task continues running. We then
# await the inner task and verify it eventually completes successfully.
# -----------------------------------------------------------------------------


async def critical_write(name: str, seconds: float) -> str:
    _log_line(f"{name}: critical_write started, will take {seconds}s")
    try:
        await asyncio.sleep(seconds)
        _log_line(f"{name}: critical_write completed cleanly")
        return f"{name}-result"
    except asyncio.CancelledError:
        _log_line(f"{name}: critical_write CANCELLED (UNEXPECTED in shield case)")
        raise
    finally:
        _log_line(f"{name}: critical_write finally block")


async def scenario_shield() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 4: asyncio.shield around a critical region ====")
    # We use ensure_future so we keep an outer reference to the inner task.
    # That way we can re-await it after the shield raises.
    inner_task: asyncio.Task[str] = asyncio.ensure_future(critical_write("W", 0.20))
    try:
        async with asyncio.timeout(0.05):
            _log_line("entering shield(inner_task)")
            await asyncio.shield(inner_task)
        _log_line("shield returned (unexpected!)")
    except TimeoutError:
        _log_line(
            f"caller saw TimeoutError from the outer timeout. "
            f"inner_task.done()={inner_task.done()} (should be False)"
        )
    # Now wait for the inner task to actually finish.
    _log_line("now awaiting inner_task directly...")
    try:
        result = await asyncio.wait_for(inner_task, timeout=1.0)
        _log_line(f"inner_task result: {result!r} (the critical write completed)")
    except (TimeoutError, asyncio.CancelledError) as e:
        _log_line(f"inner_task failed: {type(e).__name__} (unexpected!)")


# -----------------------------------------------------------------------------
# Scenario 5: shield does NOT protect from a cancel on the INNER task
# directly. If you call inner_task.cancel(), the inner is cancelled
# regardless of whether anything is shielding the outer awaiter.
# -----------------------------------------------------------------------------


async def scenario_shield_inner_cancel() -> None:
    global _t0
    _t0 = time.monotonic()
    _log_line("==== Scenario 5: shield, but inner is cancelled directly ====")
    inner_task: asyncio.Task[str] = asyncio.ensure_future(critical_write("Z", 0.30))
    # Cancel the inner directly after 50ms.
    async def killer():
        await asyncio.sleep(0.05)
        _log_line("killer: cancelling inner_task DIRECTLY")
        inner_task.cancel()
    asyncio.create_task(killer())
    try:
        result = await asyncio.shield(inner_task)
        _log_line(f"unexpected: got result {result!r}")
    except asyncio.CancelledError:
        _log_line("caught CancelledError from shield (inner was cancelled directly)")
    _log_line(f"inner_task.cancelled() = {inner_task.cancelled()}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


async def main() -> None:
    await scenario_no_expiry()
    print()
    await scenario_expires()
    print()
    await scenario_nested()
    print()
    await scenario_shield()
    print()
    await scenario_shield_inner_cancel()
    print()
    print("Done. Re-read the cancelling()=... lines and verify the counter discipline.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer "
            "(asyncio.timeout, Task.uncancel, Task.cancelling). "
            f"You are on {sys.version.split()[0]}."
        )
    asyncio.run(main())


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (timings approximate)
# -----------------------------------------------------------------------------
# [ 0.000s] ==== Scenario 1: asyncio.timeout, deadline NOT reached ====
# [ 0.000s] before timeout block: cancelling()=0
# [ 0.000s] inside timeout block, before sleep: cancelling()=0
# [ 0.100s] inside timeout block, after sleep: cancelling()=0
# [ 0.100s] after timeout block: cancelling()=0
#
# [ 0.000s] ==== Scenario 2: asyncio.timeout, deadline REACHED ====
# [ 0.000s] before timeout block: cancelling()=0
# [ 0.000s] inside timeout block, before sleep: cancelling()=0
# [ 0.050s] inner caught CancelledError. cancelling()=1 (should be >= 1; the timeout has issued its cancel)
# [ 0.050s] caller saw TimeoutError. cancelling()=0 (should be 0; the timeout absorbed its own cancel)
#
# [ 0.000s] ==== Scenario 3: nested asyncio.timeout ====
# [ 0.000s] before outer: cancelling()=0
# [ 0.000s] inside outer, before inner: cancelling()=0
# [ 0.000s] inside inner, before sleep: cancelling()=0
# [ 0.050s] inside outer, caught INNER TimeoutError. cancelling()=0 (should be 0)
# [ 0.050s] inside outer, after inner block: cancelling()=0
# [ 0.100s] inside outer, after extra sleep: cancelling()=0
# [ 0.100s] after outer: cancelling()=0
#
# [ 0.000s] ==== Scenario 4: asyncio.shield around a critical region ====
# [ 0.000s] W: critical_write started, will take 0.2s
# [ 0.000s] entering shield(inner_task)
# [ 0.050s] caller saw TimeoutError from the outer timeout. inner_task.done()=False (should be False)
# [ 0.050s] now awaiting inner_task directly...
# [ 0.200s] W: critical_write completed cleanly
# [ 0.200s] W: critical_write finally block
# [ 0.200s] inner_task result: 'W-result' (the critical write completed)
#
# [ 0.000s] ==== Scenario 5: shield, but inner is cancelled directly ====
# [ 0.000s] Z: critical_write started, will take 0.3s
# [ 0.050s] killer: cancelling inner_task DIRECTLY
# [ 0.050s] Z: critical_write CANCELLED (UNEXPECTED in shield case)
# [ 0.050s] Z: critical_write finally block
# [ 0.050s] caught CancelledError from shield (inner was cancelled directly)
# [ 0.050s] inner_task.cancelled() = True
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Scenario 2: why is the inner CancelledError seen at cancelling()=1,
#    but the OUTER caller sees TimeoutError at cancelling()=0? Answer:
#    asyncio.timeout's __aexit__ calls self._task.uncancel() before
#    re-raising as TimeoutError. The uncancel decrements the counter back
#    to 0. Read Lib/asyncio/timeouts.py:Timeout.__aexit__ for the exact
#    predicate `self._task.uncancel() <= self._cancelling`.
#
# 2. Scenario 3: how does the outer timeout know NOT to convert its
#    perfectly-fine TimeoutError-from-inner into its own TimeoutError?
#    Answer: the outer's __aexit__ is entered with exc_type == TimeoutError,
#    not CancelledError. The outer's `et is exceptions.CancelledError` check
#    is False. The outer does nothing and lets the inner TimeoutError
#    propagate unchanged.
#
# 3. Scenario 4: why does the inner_task survive when the outer timeout
#    fires? Answer: asyncio.shield decouples the outer await from the
#    inner task. When the outer task is cancelled, the shield's
#    _outer_done_callback removes the link, but the inner task is still
#    scheduled on the loop and runs to completion. Read
#    Lib/asyncio/tasks.py:shield for the two-callback wiring.
#
# 4. Scenario 5: shield is one-directional. It protects from cancellation
#    of the AWAITER, not of the inner task itself. If you want a truly
#    uninterruptible critical region, you need a different pattern entirely
#    (typically: do the work in a finally block, run the critical work in
#    a separate non-cancellable Task and never expose its cancellation).
#
# 5. (Stretch) Reproduce Scenario 2 on Python 3.10 (without asyncio.timeout)
#    using asyncio.wait_for. Confirm the older API is functionally similar
#    but does not interact correctly with nested timeouts. Read
#    Lib/asyncio/tasks.py:wait_for for the 3.11 reimplementation that
#    closes the race documented in bpo-32751.
#
# 6. (Stretch) Add a scenario where you nest THREE asyncio.timeout blocks
#    (deadlines 0.05s, 0.02s, 0.10s) and trace the counter at every nesting
#    level. The innermost expires first; verify each outer sees only the
#    propagating TimeoutError, never a stray CancelledError.
# -----------------------------------------------------------------------------
