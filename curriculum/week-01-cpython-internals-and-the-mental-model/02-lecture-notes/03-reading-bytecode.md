# Lecture 3 — Reading Bytecode

> **Outcome:** You can disassemble any Python expression, identify each opcode, and read it well enough to spot performance pitfalls (like the `LOAD_FAST` / `LOAD_GLOBAL` distinction).

In Lecture 2 we traced source → tokens → AST → bytecode. Now we look at *the bytecode itself* — what it looks like, how to read it, what it tells you.

The official reference is the [`dis` module docs](https://docs.python.org/3/library/dis.html). Keep that open in a tab.

> **Note on Python versions.** Bytecode is *not* stable across Python releases. Opcodes are added, removed, and renamed. This lecture targets Python 3.12 / 3.13. Examples on older versions may look different.

---

## 1. Disassembling

The simplest case:

```python
>>> import dis
>>> dis.dis("x = 1 + 2")
```

Output:

```
  1           RESUME                   0
              LOAD_CONST               0 (3)
              STORE_NAME               0 (x)
              LOAD_CONST               1 (None)
              RETURN_VALUE
```

Read it left to right:

| Column | Meaning |
|--------|---------|
| `1` | Source line number this instruction came from |
| `RESUME` | The opcode (instruction name) |
| `0` | The operand (integer argument; meaning depends on opcode) |
| `(3)` | Annotated meaning, when `dis` can resolve it |

That's all there is to it. Bytecode is a sequence of `(opcode, operand)` pairs. CPython's evaluation loop reads them and performs the action.

Notice: `1 + 2` became `LOAD_CONST 0 (3)`. The compiler **constant-folded** the addition at compile time. No runtime arithmetic happens.

---

## 2. The stack machine

CPython is a **stack-based virtual machine**. Most opcodes:

- pop one or more values off a stack,
- compute something,
- push the result back.

A useful mental model: imagine a vertical stack of Tupperware lids. `LOAD_*` adds a lid on top. `STORE_*` removes one. `BINARY_OP` pops two, places one.

Let's trace `x + 1`:

```python
>>> def f(x):
...     return x + 1
>>> dis.dis(f)
```

```
  2           RESUME                   0

  3           LOAD_FAST                0 (x)
              LOAD_CONST               1 (1)
              BINARY_OP                0 (+)
              RETURN_VALUE
```

Trace the stack:

| After instruction | Stack (top right) |
|-------------------|-------------------|
| `RESUME` | `[]` |
| `LOAD_FAST 0 (x)` | `[<value of x>]` |
| `LOAD_CONST 1 (1)` | `[<value of x>, 1]` |
| `BINARY_OP 0 (+)` | `[<value of x> + 1]` |
| `RETURN_VALUE` | (returns top, stack empty) |

This is the model. Once you have it, every other opcode is just "what does this one push or pop?"

---

## 3. The opcodes you'll see most

You don't need to memorize the full opcode list (it's a few hundred). Master these ~15 and you can read 95% of bytecode you'll encounter:

### Loads — putting values on the stack

| Opcode | Pushes |
|--------|--------|
| `LOAD_FAST` | local variable by index |
| `LOAD_GLOBAL` | global variable by name |
| `LOAD_DEREF` | closure variable |
| `LOAD_CONST` | constant from `co_consts` |
| `LOAD_ATTR` | attribute access (`obj.attr` after `obj` is on stack) |

### Stores

| Opcode | Pops |
|--------|------|
| `STORE_FAST` | top value, save to local variable |
| `STORE_GLOBAL` | top value, save to globals |
| `STORE_ATTR` | TOS2 = TOS.attr ; pops 2 |
| `STORE_NAME` | name-based store (used at module level) |

### Computation

| Opcode | Effect |
|--------|--------|
| `BINARY_OP` | pop two, push result; operand encodes the op (+, -, *, …) |
| `COMPARE_OP` | pop two, push bool; operand encodes the comparison (<, ==, …) |
| `UNARY_NOT` | pop, push `not TOS` |

### Control flow

| Opcode | Effect |
|--------|--------|
| `RETURN_VALUE` | pop TOS, return it |
| `POP_JUMP_IF_FALSE` | pop, jump to offset if it was falsy |
| `JUMP_FORWARD` | unconditional jump |
| `RAISE_VARARGS` | raise an exception |

### Function/method calls

| Opcode | Effect |
|--------|--------|
| `CALL` | call a callable; operand is arg count |
| `KW_NAMES` | provides keyword arg names for the next `CALL` |

### Iteration

| Opcode | Effect |
|--------|--------|
| `GET_ITER` | `iter(TOS)` |
| `FOR_ITER` | pull one value or jump if exhausted |

### Misc you'll see often

| Opcode | Effect |
|--------|--------|
| `RESUME` | function entry; required since 3.11 |
| `POP_TOP` | discard top of stack |
| `COPY` | duplicate (or copy nth) on top |
| `MAKE_FUNCTION` | construct a function from a code object |

If you can read those, you can read almost any bytecode.

---

## 4. The `LOAD_FAST` vs `LOAD_GLOBAL` performance lesson

This is the most-cited Python micro-optimization, and it's a great way to lock in the bytecode mental model.

Consider:

```python
def f1():
    s = 0
    for i in range(10_000):
        s = s + i
    return s

def f2():
    s = 0
    r = range            # bind to local
    for i in r(10_000):
        s = s + i
    return s
```

`f2` is faster than `f1`. By how much depends on Python version (less in 3.12+ thanks to specialization), but the principle holds. Why?

Disassemble:

```python
>>> dis.dis(f1)
…
              LOAD_GLOBAL              1 (range)   ← global lookup
              PUSH_NULL
              LOAD_CONST               1 (10000)
              CALL                     1
…

>>> dis.dis(f2)
…
              LOAD_FAST                1 (r)       ← local index lookup
              PUSH_NULL
              LOAD_CONST               2 (10000)
              CALL                     1
…
```

`LOAD_GLOBAL`:

- Look up `"range"` in `globals()` (a dict).
- If not found, look up in `builtins`.

`LOAD_FAST`:

- Index into a C array on the frame.
- One pointer dereference.

The latter is ~5-50× faster in a tight loop. For most code this is irrelevant — your bottleneck is elsewhere. But knowing the bytecode level lets you reason about *why*, not just *that*.

> **Modern caveat:** in Python 3.11+, the specializing adaptive interpreter rewrites `LOAD_GLOBAL` to a faster `LOAD_GLOBAL_BUILTIN` after observing that `range` always resolves to the builtin. That closes much of the gap. But it's still a small win, and the mental model is the same.

---

## 5. The `code` object up close

Disassembling shows you the bytecode. But the `code` object holds more:

```python
>>> def add(x, y=2):
...     return x + y + 10
>>> code = add.__code__
>>> code.co_code
b'\x97\x00|\x00|\x01z\x00\x00\x00d\x01z\x00\x00\x00S\x00'
>>> code.co_consts
(None, 10)
>>> code.co_varnames
('x', 'y')
>>> code.co_names
()
>>> code.co_argcount
2
>>> code.co_filename
'<stdin>'
>>> code.co_firstlineno
1
```

That's the actual data backing a function. The `co_code` field is the raw bytecode as `bytes`. `dis` parses it for you.

You can construct a code object by hand with `types.CodeType(...)` — almost never necessary, but liberating to know you can.

---

## 6. Line number information

Python tracks "which source line did each bytecode instruction come from?" so tracebacks and debuggers work. Pre-3.11 this was a packed table called `co_lnotab`. Since 3.11 (PEP 626) it's `co_linetable`, which is richer — it can map any *byte offset* of a single line back to the column range. That's how 3.11+ shows you the exact ^^^^ underline in error messages.

You usually don't read these tables directly. `dis.findlinestarts(code)` gives you the offsets at which a new line starts, if you need them.

---

## 7. Reading bytecode for real bugs

Two real-world cases where reading bytecode pays off.

### Case A: the for-loop "off by one"

```python
def slow_sum(xs):
    total = 0
    for x in xs:
        total = total + x
    return total

def fast_sum(xs):
    return sum(xs)
```

`fast_sum` is much faster than `slow_sum` because `sum` is a C function. But also:

```python
>>> dis.dis(slow_sum)
```

You'll see `LOAD_FAST total`, `LOAD_FAST x`, `BINARY_OP +`, `STORE_FAST total` running once per element. Each iteration is ~6–8 bytecode ops. C's loop in `sum` is ~10–100× faster *per element*.

The lesson isn't "rewrite everything in C." It's "if a builtin or stdlib function does what you want, use it; you're getting a C loop for free."

### Case B: `dict.get` with a default

```python
def with_get(d, key):
    return d.get(key, "default")

def with_check(d, key):
    if key in d:
        return d[key]
    return "default"
```

Run `dis.dis` on both. Notice `with_check` does the hash lookup *twice* — once for `in`, once for `[]`. `with_get` does one C-side lookup. The "Pythonic" way isn't just prettier; it's faster.

---

## 8. Tools that consume bytecode

- **`coverage.py`** — uses `sys.settrace`/`sys.monitoring` to record which bytecodes execute.
- **`hypothesis`** — uses bytecode internals for some shrinking strategies.
- **JIT projects** (PyPy, Pyston, Cinder) — operate at this level.
- **Linters and security scanners** — sometimes use bytecode features (more commonly the AST).

You don't need to write any of these in C17. But knowing they exist demystifies them.

---

## 9. Common pitfalls

1. **"Bytecode is stable."** It is not. Don't pickle bytecode and expect it to work across Python versions.
2. **"Faster bytecode = faster code."** Often, but the CPython evaluation loop has so many specialization, caching, and JIT-like behaviors that microbenchmark differences can be illusory. Always measure.
3. **"All Python implementations have the same bytecode."** They do not. PyPy has its own. MicroPython's is different. Even within CPython, `3.11.4` and `3.13.0` differ.
4. **"`dis` works for any code."** Mostly. But code from `eval()` strings, C-implemented builtins (`len`, `print`), and certain metaprogramming may not disassemble cleanly.

---

## 10. Self-check

- What does it mean to call CPython a "stack-based virtual machine"?
- What's the difference between `LOAD_FAST` and `LOAD_GLOBAL`? Which is faster, and why?
- Where on the code object can you find the literal constants used by the function?
- Why is `1 + 2` compiled to `LOAD_CONST 3` instead of two loads and a `BINARY_OP`?
- What is the `RESUME` opcode for?

---

## Further reading

- **`dis` module documentation**: <https://docs.python.org/3/library/dis.html>
- **PEP 659 — Specializing adaptive interpreter**: <https://peps.python.org/pep-0659/>
- **CPython source — `Python/bytecodes.c`** (the source of truth for what each opcode does):
  <https://github.com/python/cpython/blob/main/Python/bytecodes.c>
- **"How does the CPython compiler work?"** — Anthony Shaw, Real Python:
  <https://realpython.com/cpython-compiler/>

---

That's the end of Lecture 3. Take the [quiz](../05-quiz.md), then start on the [mini-project](../07-mini-project/00-overview.md).
