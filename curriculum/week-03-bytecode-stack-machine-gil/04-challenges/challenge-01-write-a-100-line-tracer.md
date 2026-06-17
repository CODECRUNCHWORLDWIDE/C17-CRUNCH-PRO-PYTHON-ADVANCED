# Challenge 1 — Write a 100-line bytecode tracer in one timed sitting

**Time:** ~90 minutes, in one continuous block. Set a timer.
**Difficulty:** Medium.
**Prerequisite:** Exercise 1 done, both lectures read.

## The brief

Build a working bytecode tracer in **at most 100 lines of Python** (including imports and the demo `if __name__ == "__main__":` block, excluding blank lines and comments). It must:

1. Accept a target callable (function or method).
2. Print every executed instruction during one invocation of that callable, including instructions inside any Python function it calls.
3. For each instruction: print the **qualified function name**, the **byte offset**, the **opcode mnemonic**, and the **oparg** (decimal).
4. Indent the trace by call depth — so a tracer of `f` that calls `g` shows `g`'s opcodes indented one level deeper than `f`'s.
5. Print a summary line at the end: total instructions executed, total Python frames entered.

Use **`sys.monitoring`** (PEP 669), not `sys.settrace`. The 3.12+ API is the modern path; `sys.settrace` would force per-line global instrumentation that interacts poorly with PEP 659 specialization.

## Acceptance criteria

- [ ] Source file is named `tracer.py`, ≤100 non-blank non-comment lines (use `cloc tracer.py` or `grep -cv '^\s*\(#\|$\)' tracer.py` to verify).
- [ ] Imports only from the standard library.
- [ ] Runs as `python tracer.py` and traces a small built-in demo function.
- [ ] Trace output shows correct depth indentation across at least one inner call.
- [ ] Trace output includes the oparg.
- [ ] Summary at the end reports total instructions and total frames.
- [ ] Tear-down is clean: the script does not leak the monitoring tool id when run twice in the same process.

## Time budget (suggested)

| Phase | Time |
|-------|------|
| Read Exercise 1's solution carefully **once**, then close it | 5 min |
| Sketch the API on paper (function signatures, event handlers) | 10 min |
| Implement `PY_START`/`PY_RETURN` for depth tracking | 15 min |
| Implement `INSTRUCTION` for opcode printing | 20 min |
| Make the demo work end-to-end | 15 min |
| Trim to ≤100 lines | 10 min |
| Final test, fix the tear-down bug you certainly have | 15 min |
| **Total** | **~90 min** |

## What to expect (gotchas in advance)

1. **`set_local_events` requires a code object, not a function.** You will pass `func.__code__`.
2. **Inner calls need their own `set_local_events` invocation,** OR you switch to `set_events` (global). Decide which up front — `set_events` is simpler for this challenge.
3. **`sys.monitoring.events.PY_START` fires before the first instruction.** Its callback signature is `(code, instruction_offset)` — the offset will be the start of the first opcode, typically 0. Use it to push a depth-tracking stack entry.
4. **`PY_RETURN`'s signature is `(code, instruction_offset, retval)`.** It fires before the return value is given to the caller. Use it to pop the depth stack.
5. **`sys.monitoring.DISABLE` is a sentinel** — if you return it from a callback, you turn that event off **at that location for that code object forever**. Useful for "trace this once and stop"; **not** what you want for a normal trace, where you should return `None`.
6. **Calling `sys.monitoring.use_tool_id` twice with the same id raises `ValueError`** — your tear-down must call `free_tool_id`, and your setup should try a `free_tool_id` first (catching the `ValueError` if the id was never allocated).

## Hints

<details>
<summary>Hint 1 - skeleton</summary>

```python
import sys, dis

TOOL_ID = sys.monitoring.PROFILER_ID

def install(events_to_listen_for, callbacks):
    sys.monitoring.use_tool_id(TOOL_ID, "tracer")
    sys.monitoring.set_events(TOOL_ID, events_to_listen_for)
    for event, cb in callbacks.items():
        sys.monitoring.register_callback(TOOL_ID, event, cb)

def uninstall():
    sys.monitoring.set_events(TOOL_ID, 0)
    sys.monitoring.free_tool_id(TOOL_ID)
```

</details>

<details>
<summary>Hint 2 - depth tracking</summary>

Keep a module-level `depth = 0`. Bump on `PY_START`, decrement on `PY_RETURN`. Indent your output by `"  " * depth`.

</details>

<details>
<summary>Hint 3 - resolving opcode + oparg</summary>

```python
code_bytes = code.co_code
opcode = code_bytes[offset]
oparg  = code_bytes[offset + 1]
name   = dis.opname[opcode]
```

You do not need to skip inline-cache slots. `sys.monitoring` already fires once per *real* instruction, never on cache bytes.

</details>

## Stretch (only if you finished in under 60 min)

- Add a `--filter regex` flag that traces only frames whose `co_qualname` matches the regex.
- Implement the same in ≤100 lines using `sys.settrace`. Document the differences in fidelity and overhead in `settrace-vs-monitoring.md`.
- Add a `--stack-effect` flag that uses `dis.stack_effect(opcode, oparg)` to also print the net stack effect of each instruction (positive = pushes, negative = pops).

## Submission

Commit `tracer.py` plus a short `notes.md` (~150 words):

1. What was hard?
2. What did you simplify out?
3. What would you build next if you had another hour?

## Why this matters

The mini-project (the same tracer, but written to be reused and documented) takes 4–6 hours. Doing the same work under a 90-minute time-box first **forces you to commit to a design** before second-guessing. Senior engineers write a working version first and refine; junior engineers polish features that will not survive contact with the demo. Build the muscle.
