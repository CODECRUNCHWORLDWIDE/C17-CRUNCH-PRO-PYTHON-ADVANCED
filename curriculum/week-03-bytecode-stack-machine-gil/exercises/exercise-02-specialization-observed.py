"""
Exercise 2 - Specialization observed

Goal: observe PEP 659 adaptive specialization at runtime. Watch a generic
BINARY_OP get rewritten to BINARY_OP_ADD_INT after warm-up, then watch it
deoptimize back to generic when the operand type changes.

Estimated time: 40 minutes.

Run with:   python exercise-02-specialization-observed.py
Requires:   Python 3.11+ (dis.dis adaptive=True and show_caches=True).

Acceptance criteria:
- You have run the script and observed the three states printed:
    (a) cold:        BINARY_OP                     (unspecialized)
    (b) warm:        BINARY_OP_ADD_INT             (specialized to ints)
    (c) deoptimized: BINARY_OP                     (back to generic after a
                                                    string operand triggered
                                                    a guard miss)
- You have committed your stdout to notes/exercise-02-output.md.
- You can explain to a peer the role of the adaptive counter in the inline
  cache slots.

References:
- PEP 659: https://peps.python.org/pep-0659/
- Python/specialize.c (_Py_Specialize_BinaryOp):
  https://github.com/python/cpython/blob/main/Python/specialize.c
- Python/bytecodes.c (BINARY_OP family):
  https://github.com/python/cpython/blob/main/Python/bytecodes.c
"""

from __future__ import annotations

import dis
import io
import sys
import time


# -----------------------------------------------------------------------------
# The function whose BINARY_OP we will warm up
# -----------------------------------------------------------------------------

def add(a, b):
    return a + b


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def disassemble(func, *, adaptive: bool) -> str:
    """Capture dis.dis output to a string."""
    buf = io.StringIO()
    dis.dis(func, file=buf, adaptive=adaptive, show_caches=True)
    return buf.getvalue()


def find_binary_op_line(disasm: str) -> str:
    """Return the first line that mentions BINARY_OP (specialized or not)."""
    for line in disasm.splitlines():
        if "BINARY_OP" in line and "CACHE" not in line:
            return line.strip()
    return "<no BINARY_OP found>"


def warm_up(func, *, iterations: int, lhs, rhs) -> None:
    """Call func enough times for PEP 659 to specialize the call site."""
    # The warm-up threshold is roughly 52 iterations in CPython 3.13 (see
    # ADAPTIVE_WARMUP_VALUE in Python/specialize.c). 200 is comfortable
    # head-room.
    for _ in range(iterations):
        func(lhs, rhs)


def time_calls(func, *, iterations: int, lhs, rhs) -> float:
    """Return ns/op for one tight inner loop of `iterations` calls."""
    start = time.perf_counter_ns()
    for _ in range(iterations):
        func(lhs, rhs)
    elapsed_ns = time.perf_counter_ns() - start
    return elapsed_ns / iterations


# -----------------------------------------------------------------------------
# The experiment
# -----------------------------------------------------------------------------

def main() -> None:
    print(f"Python: {sys.version.split()[0]}")
    print()

    # --------- Stage 1: cold ---------
    print("Stage 1 - COLD (no calls yet, opcode is generic BINARY_OP)")
    cold = disassemble(add, adaptive=True)
    print(f"  observed: {find_binary_op_line(cold)}")
    # TODO: predict what you expect to see here. It should be plain BINARY_OP.
    print()

    # --------- Stage 2: warm with ints ---------
    print("Stage 2 - WARM (200 int+int calls, opcode should specialize)")
    warm_up(add, iterations=200, lhs=3, rhs=4)
    warm = disassemble(add, adaptive=True)
    print(f"  observed: {find_binary_op_line(warm)}")
    # TODO: predict. After warm-up you should see BINARY_OP_ADD_INT.
    print()

    # --------- Stage 3: deoptimize with a string ---------
    print("Stage 3 - DEOPT (one str+str call triggers the int-type guard)")
    add("hello", "world")          # str+str -> the int guard misses, deopt
    deopt = disassemble(add, adaptive=True)
    print(f"  observed: {find_binary_op_line(deopt)}")
    # TODO: predict. After the guard miss the opcode is rewritten back to
    # generic BINARY_OP. (It may also subsequently re-specialize to
    # BINARY_OP_ADD_UNICODE if you keep calling with strings.)
    print()

    # --------- Stage 4: re-warm with strings ---------
    print("Stage 4 - RE-WARM with str+str (200 calls, may pick up unicode variant)")
    warm_up(add, iterations=200, lhs="a", rhs="b")
    rewarm = disassemble(add, adaptive=True)
    print(f"  observed: {find_binary_op_line(rewarm)}")
    print()

    # --------- Stage 5: a micro-measurement ---------
    print("Stage 5 - micro-benchmark (ns/op on int+int)")
    # Refresh the function to a fresh, cold add for a clean comparison.
    fresh_globals = {"__name__": "fresh"}
    exec("def add(a, b):\n    return a + b\n", fresh_globals)
    add_fresh = fresh_globals["add"]

    # Take one timing while it's still cold.
    cold_ns_per_op = time_calls(add_fresh, iterations=1_000_000, lhs=3, rhs=4)
    print(f"  first   1M calls (warming up midway): {cold_ns_per_op:6.2f} ns/op")

    # Take another - by now the call site is firmly specialized.
    warm_ns_per_op = time_calls(add_fresh, iterations=1_000_000, lhs=3, rhs=4)
    print(f"  second  1M calls (fully specialized): {warm_ns_per_op:6.2f} ns/op")

    # Take a polymorphic-stress timing to show the cost of repeated deopt.
    def poly_run(n):
        s = 0
        for i in range(n):
            if i % 2 == 0:
                s = add_fresh(1, 2)
            else:
                s = add_fresh("a", "b")
        return s

    poly_start = time.perf_counter_ns()
    poly_run(1_000_000)
    poly_ns = (time.perf_counter_ns() - poly_start) / 1_000_000
    print(f"  polymorphic (alternating int/str):     {poly_ns:6.2f} ns/op")

    print()
    print("Notes:")
    print("- Stage 2 should show BINARY_OP_ADD_INT.")
    print("- Stage 3 should show BINARY_OP (deoptimized).")
    print("- The 'warm' ns/op should be roughly 3-5x faster than the polymorphic case.")


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11+ (dis show_caches/adaptive). "
            f"You are on {sys.version.split()[0]}."
        )
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (approximate; numbers vary by machine)
# -----------------------------------------------------------------------------
# Stage 1 - COLD ...
#   observed: 16 BINARY_OP                0 (+)
#
# Stage 2 - WARM ...
#   observed: 16 BINARY_OP_ADD_INT        0 (+)
#
# Stage 3 - DEOPT ...
#   observed: 16 BINARY_OP                0 (+)
#
# Stage 4 - RE-WARM with str+str ...
#   observed: 16 BINARY_OP_ADD_UNICODE    0 (+)
#
# Stage 5 - micro-benchmark (ns/op on int+int)
#   first   1M calls (warming up midway):   ~12 ns/op
#   second  1M calls (fully specialized):    ~3 ns/op
#   polymorphic (alternating int/str):      ~30 ns/op
#
# Hardware in the comments above was an M3 MacBook running CPython 3.13.
# Your numbers will differ; the *ratios* should be similar.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Why does PEP 659 wait ~52 iterations before specializing?
#    Answer: most functions are called once. Specializing on the first call
#    would waste work and pessimize cold paths. The warm-up counter lets the
#    runtime distinguish "code that runs" from "code that runs A LOT."
#
# 2. What does the inline cache after BINARY_OP_ADD_INT actually store?
#    Hint: read Python/bytecodes.c, "inst(BINARY_OP_ADD_INT, ...)" - it does
#    not need stored state beyond the counter, because the type check is
#    cheap. Other specializations (LOAD_ATTR_INSTANCE_VALUE) store more.
#
# 3. The polymorphic case ran ~10x slower than the monomorphic one. What
#    fraction of that is the actual computation (a slot lookup + a function
#    call) versus the bytecode-level deopt overhead?
#    Hint: a deopt rewrites one byte in the bytecode array and goes through
#    the generic dispatch. The cost is dominated by the type-protocol
#    fallback in PyNumber_Add, not the rewrite itself.
#
# 4. (Stretch) Disassemble a list-comprehension. Find the BINARY_SUBSCR
#    inside. Predict which specialization it gets after warm-up. Verify.
# -----------------------------------------------------------------------------
