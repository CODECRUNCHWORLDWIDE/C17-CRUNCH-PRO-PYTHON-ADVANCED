# Challenge 2 — Find a builtin

**Time estimate:** ~60 minutes.

## Problem statement

For each of the following builtins, find:

1. The C source file and line range where the builtin is defined.
2. The corresponding documentation in `Doc/`.
3. (Bonus) one CPython optimization specific to it (e.g. small-int caching, string interning, fast-path code, etc.).

Builtins to locate:

- `len`
- `sum`
- `print`
- `range` (the type, not just the call)
- `isinstance`

## Acceptance criteria

- [ ] A file `notes/challenge-02-builtins.md` exists.
- [ ] For each of the 5 builtins, the file contains:
  - A direct GitHub permalink to the C definition (use `y` on a GitHub line to get a permanent URL).
  - A short (2–3 sentence) summary of where the function lives and how it's wired into Python's builtins table.
- [ ] At least 2 of the 5 entries include an "optimization specific to this" paragraph (e.g. `range` uses a small struct, not a list; small integers are cached in CPython).

## Hints

<details>
<summary>Where to start</summary>

`Python/bltinmodule.c` is where most simple builtins are registered. Search GitHub for `builtin_len_impl` and you'll find `len`. Search for `builtin_sum` and you'll find `sum`. From there you can trace into `Objects/...` for type-specific behavior.

```
https://github.com/python/cpython/tree/main/Python/bltinmodule.c
```

</details>

<details>
<summary>The `range` type</summary>

`range` is a type, not just a function. The implementation is `Objects/rangeobject.c`. The trick: `range(1, 1000)` doesn't allocate 1000 ints. It stores `start`, `stop`, `step`, and computes elements lazily. That's the optimization.

</details>

<details>
<summary>`isinstance` and its fast paths</summary>

`isinstance(x, y)` is in `Python/bltinmodule.c` as `builtin_isinstance_impl`. But there are *many* fast paths: when `y` is a single type (not a tuple), when both arguments are exact built-in types, etc. Find at least one of these.

</details>

## Why this matters

Every Python developer eventually needs to answer "why is this thing slow?" or "why does this thing behave this way?". Knowing how to navigate the source means you can answer those questions yourself instead of asking a forum and waiting.

This challenge is also a great pre-game for Week 12 (the OSS contribution capstone) — once you can find a builtin, you can find the bug or feature you want to work on.

## Submission

Commit `notes/challenge-02-builtins.md`. Include the permalinks; future you will thank you.
