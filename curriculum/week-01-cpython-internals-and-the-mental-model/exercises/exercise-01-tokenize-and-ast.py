"""
Exercise 1 — Tokenize and AST

For each of the five SOURCE strings below, your job is to:

1. Print the token stream.
2. Print the AST (using ast.dump with indent=2).
3. Add a comment under each one in your own words explaining ONE
   interesting thing about the result.

Estimated time: 30 minutes.

Run with: python exercise-01-tokenize-and-ast.py

Acceptance criteria:
- All five blocks produce output.
- You've added a comment after each block explaining what surprised
  you or what the tokenizer / parser is preserving that you didn't
  expect.
"""

from __future__ import annotations

import ast
import io
import tokenize

SOURCES = [
    "x = 1 + 2",
    "def f(x): return x * 2",
    "async def g(): await h()",
    "[x ** 2 for x in range(10) if x % 2]",
    "match command:\n    case 'start':\n        run()\n    case _:\n        pass",
]


def show_tokens(src: str) -> None:
    print("--- TOKENS ---")
    for tok in tokenize.tokenize(io.BytesIO(src.encode()).readline):
        # `type` is an int; tok_name maps it to a readable string.
        kind = tokenize.tok_name.get(tok.type, str(tok.type))
        print(f"  {kind:<12} {tok.string!r:<20} {tok.start}-{tok.end}")


def show_ast(src: str) -> None:
    print("--- AST ---")
    tree = ast.parse(src)
    print(ast.dump(tree, indent=2))


def main() -> None:
    for i, src in enumerate(SOURCES, start=1):
        print(f"\n========== SOURCE {i} ==========")
        print(src)
        print()
        show_tokens(src)
        print()
        show_ast(src)

        # TODO: write a 1-sentence comment after each run explaining what
        # surprised you or what you noticed about the tokenizer/parser output.
        # Examples:
        # - "The `async` keyword shows up as a NAME token, but the AST distinguishes it via AsyncFunctionDef."
        # - "List comprehensions become a ListComp node containing a `generators` list — you can see the structure clearly."


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# REFLECTION (delete this and write your own)
# -----------------------------------------------------------------------------
# After running, write a few sentences in your repo's notes/exercise-01.md
# answering:
#
# - Which token type surprised you?
# - Which AST node name was new to you?
# - For the match statement, what's the AST node type for `case 'start'`?
#   Was it what you expected?
#
# -----------------------------------------------------------------------------
