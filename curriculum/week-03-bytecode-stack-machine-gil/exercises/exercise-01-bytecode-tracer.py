"""
Exercise 1 - Bytecode tracer

Goal: install a sys.monitoring callback that fires on every executed
instruction in a target function, and print one line per opcode showing the
opcode name, instruction offset, and the function it ran in.

This is the seed of the Week-3 mini-project. Get the bones right here and
the project becomes 80% scaffolding plus stack-effect rendering.

Estimated time: 45 minutes.

Run with:   python exercise-01-bytecode-tracer.py
Requires:   Python 3.12+  (sys.monitoring lands in 3.12 via PEP 669).

Acceptance criteria:
- The script runs without modification and prints a trace of `target()`.
- You can answer: "What does each opcode do to the value stack?" for
  every line in the output.
- You can extend `pretty()` to also print the oparg value.

Important reading before / during:
- PEP 669, "Low Impact Monitoring for CPython":
  https://peps.python.org/pep-0669/
- sys.monitoring docs:
  https://docs.python.org/3/library/sys.monitoring.html
- dis module docs (for opcode name resolution):
  https://docs.python.org/3/library/dis.html
"""

from __future__ import annotations

import dis
import sys


# -----------------------------------------------------------------------------
# The target function. Trace this.
# -----------------------------------------------------------------------------

def target(a: int, b: int) -> int:
    """A small function whose every opcode we want to print."""
    x = a + b
    y = x * 2
    return y


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def opcode_name(opcode: int) -> str:
    """Resolve a numeric opcode byte to its name (e.g. 83 -> 'LOAD_FAST')."""
    # dis.opname is a list indexed by opcode number, since Python 3.x forever.
    if 0 <= opcode < len(dis.opname):
        return dis.opname[opcode]
    return f"<unknown opcode {opcode}>"


def pretty(code, instruction_offset: int) -> str:
    """Format one trace line.

    code:               types.CodeType of the function that just executed.
    instruction_offset: the byte offset of the just-executed instruction,
                        as reported by sys.monitoring.
    """
    # The bytecode array lives in code.co_code. Each instruction is at least
    # one 2-byte _Py_CODEUNIT; specialized opcodes are followed by inline-cache
    # CODEUNITs that are NOT separately executed. Reading co_code[offset]
    # gives us the opcode byte.
    opcode = code.co_code[instruction_offset]
    name = opcode_name(opcode)
    # TODO (stretch): also read the oparg byte at offset+1 and append it.
    return f"  {code.co_qualname:<30} @0x{instruction_offset:04x}  {name}"


# -----------------------------------------------------------------------------
# The tracer
# -----------------------------------------------------------------------------

# sys.monitoring tools each register under a tool id (0..5).  Pick an unused
# slot.  DEBUGGER_ID is reserved for debuggers, PROFILER_ID for profilers.
TOOL_ID = sys.monitoring.DEBUGGER_ID
TOOL_NAME = "c17-week03-tracer"


def install_tracer(target_code) -> None:
    """Install a per-code-object instruction-level monitoring hook."""

    # Register the tool. Calling free_tool_id first lets us re-run cleanly.
    try:
        sys.monitoring.free_tool_id(TOOL_ID)
    except ValueError:
        pass
    sys.monitoring.use_tool_id(TOOL_ID, TOOL_NAME)

    # Enable the INSTRUCTION event. PEP 669 distinguishes:
    #   PY_START / PY_RESUME / PY_RETURN / PY_YIELD - frame-level events
    #   LINE                                        - one event per source line
    #   INSTRUCTION                                 - one event per opcode
    #   RAISE / EXCEPTION_HANDLED                   - exception flow
    # INSTRUCTION is the fine-grained event we want for a bytecode tracer.
    events = sys.monitoring.events
    sys.monitoring.set_local_events(TOOL_ID, target_code, events.INSTRUCTION)

    # Register the callback. The signature for INSTRUCTION is:
    #   callback(code: CodeType, instruction_offset: int) -> object | DISABLE
    # Returning sys.monitoring.DISABLE turns off the event for that location
    # forever; returning anything else (including None) keeps it enabled.
    def on_instruction(code, instruction_offset):
        print(pretty(code, instruction_offset))

    sys.monitoring.register_callback(
        TOOL_ID,
        events.INSTRUCTION,
        on_instruction,
    )


def uninstall_tracer(target_code) -> None:
    """Tear down the monitoring hook. Always do this when you're done."""
    events = sys.monitoring.events
    sys.monitoring.set_local_events(TOOL_ID, target_code, 0)
    sys.monitoring.register_callback(TOOL_ID, events.INSTRUCTION, None)
    sys.monitoring.free_tool_id(TOOL_ID)


# -----------------------------------------------------------------------------
# Main: trace one call to target(2, 3)
# -----------------------------------------------------------------------------

def main() -> None:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Tracing target({2!r}, {3!r}) ...")
    print()

    install_tracer(target.__code__)
    try:
        result = target(2, 3)
    finally:
        uninstall_tracer(target.__code__)

    print()
    print(f"target returned: {result}")
    print()
    print("Compare to the static disassembly:")
    print()
    dis.dis(target)


if __name__ == "__main__":
    if sys.version_info < (3, 12):
        sys.exit(
            "This exercise requires Python 3.12 or newer (sys.monitoring is "
            f"PEP 669; landed in 3.12). You are on {sys.version.split()[0]}."
        )
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (approximate; opcode set varies slightly by Python version)
# -----------------------------------------------------------------------------
# On Python 3.13 with default flags:
#
#   target                         @0x0000  RESUME
#   target                         @0x0002  LOAD_FAST
#   target                         @0x0004  LOAD_FAST
#   target                         @0x0006  BINARY_OP
#   target                         @0x0010  STORE_FAST
#   target                         @0x0012  LOAD_FAST
#   target                         @0x0014  LOAD_CONST
#   target                         @0x0016  BINARY_OP
#   target                         @0x0020  STORE_FAST
#   target                         @0x0022  LOAD_FAST
#   target                         @0x0024  RETURN_VALUE
#
# Note the *gaps* in offsets (e.g. 0x0006 -> 0x0010). Those gaps are the
# inline-cache slots that follow BINARY_OP. The tracer is *not* called on
# cache slots - they are payload, not instructions. This is one of the
# correctness properties of sys.monitoring that you would have to handle by
# hand in a sys.settrace-based tracer.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. What advantage does sys.monitoring have over sys.settrace for this task?
#    Answer: it is per-code-object, per-event-type; settrace forces a global,
#    per-line hook that defeats PEP 659 specialization.
#
# 2. Why does the offset jump from 0x0006 to 0x0010 (a gap of 10) between the
#    BINARY_OP and the next instruction?
#    Answer: BINARY_OP is followed by 5 inline-cache CODEUNITs (10 bytes).
#    The next instruction lives after the caches.
#
# 3. If you wanted to also see *line* changes, which event would you enable?
#    Answer: sys.monitoring.events.LINE, with a callback signature
#    (code, line_number) -> object | DISABLE.
#
# 4. (Stretch) Modify pretty() to also print the oparg. Hint: it lives at
#    code.co_code[instruction_offset + 1].
#
# 5. (Stretch) Add a depth counter that increments on PY_START and decrements
#    on PY_RETURN, then indent the output by depth. This gives a "call tree
#    plus opcode trace" - a useful shape for the mini-project.
# -----------------------------------------------------------------------------
