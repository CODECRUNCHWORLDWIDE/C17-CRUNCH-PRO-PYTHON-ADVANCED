"""
Exercise 2 — Disassemble five code shapes

For each function defined below, run `dis.dis(...)` on it. Then, for each
function, write a sentence under it stating:

  - the number of bytecode instructions
  - the opcode you'd not seen before
  - one optimization the compiler did or didn't do

Estimated time: 35 minutes.

Run with: python exercise-02-disassemble.py
"""

from __future__ import annotations

import dis


# ----- 1. Constant folding -----
def constant_math() -> int:
    """Does the compiler fold this at compile time?"""
    return 2 * 3 + 4


# YOUR NOTE:
# (e.g. "Folded to a single LOAD_CONST 10 — no runtime arithmetic.")


# ----- 2. LOAD_FAST vs LOAD_GLOBAL -----
def uses_global() -> int:
    return len([1, 2, 3])


def uses_local() -> int:
    _len = len  # bind to local
    return _len([1, 2, 3])


# YOUR NOTE:
# (Look at LOAD_GLOBAL vs LOAD_FAST in the two functions.)


# ----- 3. List comprehension vs for-loop -----
def with_for_loop() -> list[int]:
    out = []
    for i in range(5):
        out.append(i * i)
    return out


def with_comprehension() -> list[int]:
    return [i * i for i in range(5)]


# YOUR NOTE:
# (Comprehensions are not always shorter in bytecode. Compare.)


# ----- 4. Generator vs list comprehension -----
def generator_expr():
    return sum(i * i for i in range(5))


def list_then_sum():
    return sum([i * i for i in range(5)])


# YOUR NOTE:
# (Look at MAKE_FUNCTION vs LIST_APPEND etc.)


# ----- 5. f-string vs format -----
def with_fstring(name: str) -> str:
    return f"Hello, {name}!"


def with_format(name: str) -> str:
    return "Hello, {}!".format(name)


# YOUR NOTE:
# (FORMAT_VALUE vs CALL on a method-bound str.format.)


# -----------------------------------------------------------------------------
def main() -> None:
    funcs = [
        constant_math,
        uses_global,
        uses_local,
        with_for_loop,
        with_comprehension,
        generator_expr,
        list_then_sum,
        with_fstring,
        with_format,
    ]
    for fn in funcs:
        print(f"\n========== {fn.__name__} ==========")
        dis.dis(fn)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# WHAT TO PRODUCE
# -----------------------------------------------------------------------------
# When you're done, commit this file + a markdown note `notes/exercise-02.md`
# that includes, per function:
#
# - The full dis output (paste it).
# - Your one-sentence observation.
#
# Acceptance: 9 functions disassembled, 9 sentences. Total writeup ~1 page.
# -----------------------------------------------------------------------------
