# Lecture 2 — `LOAD_FAST` vs. `LOAD_GLOBAL`, and the Specializing Adaptive Interpreter (PEP 659)

> **Duration:** ~1.75 hours. **Outcome:** You can predict, for any name reference in Python source, which opcode the compiler will emit; you can compare the per-instruction cost of `LOAD_FAST` and `LOAD_GLOBAL` in nanoseconds; and you can describe PEP 659's specialization machine — including warm-up, guard checks, and deoptimization — in terms a colleague unfamiliar with it can follow.

## 1. The classification problem the compiler solves

When Python source code references a name — `print(x)` — the compiler must decide, **at compile time**, which of several scopes the name belongs to. The decision determines which opcode is emitted:

| Scope classification | Opcode emitted | Resolution mechanism |
|----------------------|----------------|----------------------|
| Local (function-scope, assigned somewhere in the function) | `LOAD_FAST` | Index into `frame->localsplus` |
| Free (closure variable from enclosing function) | `LOAD_DEREF` | Indirect through a cell object |
| Cell (local that is captured by an inner function) | `LOAD_DEREF` | Same cell mechanism |
| Global (module-scope or imported name) | `LOAD_GLOBAL` | Hash-table lookup in `f_globals`, fallback to `f_builtins` |
| Class-body attribute (in a class statement) | `LOAD_NAME` | Tries locals dict, then globals, then builtins |

The classifier runs in the compiler — `Python/symtable.c` and `Python/compile.c` — long before bytecode runs. By the time you see the disassembly, the choice is already baked in.

The rule for local-vs-global, simplified: **if the function body assigns to a name anywhere (and that assignment is not preceded by `global` or `nonlocal`), the name is local for the whole function.** That is why this surprises beginners:

```python
x = 10
def f():
    print(x)   # NameError: cannot access local variable 'x' where it is not associated with a value
    x = 20
```

The assignment `x = 20` makes `x` local **for the entire function**, including the earlier `print(x)`. The compiler emitted `LOAD_FAST 'x'`, the local was uninitialized at that point, and the runtime raised. This is not a runtime decision; it is a compile-time scope classification.

## 2. Why `LOAD_FAST` is fast

From Lecture 1: `LOAD_FAST oparg` is

```c
inst(LOAD_FAST, (-- value)) {
    value = GETLOCAL(oparg);
    assert(value != NULL);
    Py_INCREF(value);
}
```

Three operations: one array load, one refcount bump, one stack push. The oparg is a **small integer index** computed by the compiler — `f.__code__.co_varnames` lists the locals in order, and the oparg is the position. There is no string lookup, no hash, no dict probe. The cost on modern x86-64 is roughly **1–3 nanoseconds**.

## 3. Why `LOAD_GLOBAL` is slow (and what PEP 659 does about it)

`LOAD_GLOBAL` has to find the name's value at runtime. The slow path, in `Python/bytecodes.c`:

```c
inst(LOAD_GLOBAL, (-- res[1 + (oparg & 1)])) {
    // ... adaptive trigger check ...

    PyObject *name = GETITEM(FRAME_CO_NAMES, oparg >> 1);
    PyObject *v = PyDict_GetItemWithError(GLOBALS(), name);
    if (v == NULL) {
        if (_PyErr_Occurred(tstate)) goto error;
        v = PyDict_GetItemWithError(BUILTINS(), name);
        if (v == NULL) {
            // raise NameError
            goto error;
        }
    }
    Py_INCREF(v);
    res[0] = v;
}
```

(Simplified; the real handler also handles `LOAD_GLOBAL`'s `pushnull` flag for method-style calls.)

Two dict lookups in the worst case: `f_globals` first, then `f_builtins`. Each dict lookup is a hash computation plus an array probe plus a string equality check. On built-in names like `print`, both lookups happen because `print` lives in builtins.

In nanoseconds, a generic `LOAD_GLOBAL` is roughly **30–60 ns** — an order of magnitude slower than `LOAD_FAST`. The micro-optimization "rebind global functions to locals" inside hot loops works for exactly this reason:

```python
# Before: print is LOAD_GLOBAL each time
def hot_loop(items):
    for item in items:
        print(item)

# After: print is LOAD_FAST each time
def hot_loop(items):
    _print = print
    for item in items:
        _print(item)
```

In adaptive-era CPython (3.11+), the gap is much smaller in practice because of **specialization** — which is the rest of this lecture.

## 4. PEP 659 in one screen

**PEP 659 — Specializing Adaptive Interpreter** (Shannon, 2021; landed in 3.11) introduced a form of profile-guided opcode rewriting that runs **inside the interpreter loop, with no separate JIT compiler.** The mechanics:

1. Every "adaptive" opcode (those that have specialized variants) tracks a **warm-up counter** in its inline cache slots.
2. On each execution, the counter decrements. When it crosses zero, the **specializer** (`Python/specialize.c`) examines the current operands and rewrites the opcode **in place** to a type-specialized variant.
3. The specialized variant has a **guard**: it checks at runtime that its precondition still holds (e.g., that both operands are still `int`). If the guard passes, it does the fast path. If it fails, it **deoptimizes** — rewrites itself back to the generic opcode.

The result: hot code paths converge to specialized opcodes that are nearly as efficient as a static-typed VM. Cold code paths cost the same as the pre-adaptive interpreter. There is no JIT in the sense of generating machine code (until 3.13's experimental copy-and-patch JIT, which is a separate story); there is only opcode-level type specialization.

The full opcode list with specialized variants is in `Include/internal/pycore_opcode_metadata.h`. The most consequential families:

| Generic opcode | Specialized variants |
|----------------|----------------------|
| `LOAD_GLOBAL` | `LOAD_GLOBAL_MODULE`, `LOAD_GLOBAL_BUILTIN` |
| `LOAD_ATTR` | `LOAD_ATTR_INSTANCE_VALUE`, `LOAD_ATTR_MODULE`, `LOAD_ATTR_SLOT`, `LOAD_ATTR_CLASS`, `LOAD_ATTR_PROPERTY`, `LOAD_ATTR_METHOD_*` (many) |
| `STORE_ATTR` | `STORE_ATTR_INSTANCE_VALUE`, `STORE_ATTR_SLOT`, `STORE_ATTR_WITH_HINT` |
| `BINARY_OP` | `BINARY_OP_ADD_INT`, `BINARY_OP_ADD_FLOAT`, `BINARY_OP_ADD_UNICODE`, `BINARY_OP_MULTIPLY_INT`, `BINARY_OP_MULTIPLY_FLOAT`, `BINARY_OP_SUBTRACT_INT`, ... |
| `BINARY_SUBSCR` | `BINARY_SUBSCR_LIST_INT`, `BINARY_SUBSCR_TUPLE_INT`, `BINARY_SUBSCR_DICT`, `BINARY_SUBSCR_STR_INT`, `BINARY_SUBSCR_GETITEM` |
| `CALL` | `CALL_PY_EXACT_ARGS`, `CALL_BOUND_METHOD_EXACT_ARGS`, `CALL_BUILTIN_O`, `CALL_BUILTIN_FAST`, `CALL_TYPE_1`, `CALL_ISINSTANCE`, `CALL_LEN`, ... |
| `FOR_ITER` | `FOR_ITER_LIST`, `FOR_ITER_TUPLE`, `FOR_ITER_RANGE`, `FOR_ITER_GEN` |
| `SEND` / `YIELD_VALUE` | various coroutine specializations |

When you read `Python/bytecodes.c`, the family is declared explicitly:

```c
family(LOAD_GLOBAL, INLINE_CACHE_ENTRIES_LOAD_GLOBAL) = {
    LOAD_GLOBAL_MODULE,
    LOAD_GLOBAL_BUILTIN,
};
```

That declaration tells the codegen: these three opcodes share inline-cache layout and form a specialization family.

## 5. Walkthrough: `LOAD_GLOBAL_MODULE` and `LOAD_GLOBAL_BUILTIN`

`LOAD_GLOBAL` has two specialized variants:

- **`LOAD_GLOBAL_MODULE`** — the name was found in `f_globals`. The inline cache stores the **module's dict version** (`ma_version_tag`, a monotonically increasing counter on every dict) and the **index in the module dict's table**. On execution: check the version (cheap), index into the table (cheap), push. No hash lookup.
- **`LOAD_GLOBAL_BUILTIN`** — the name was not in `f_globals` but was in `f_builtins`. The cache stores **both** dict version tags (we must guarantee `f_globals` didn't gain the name) and the index in builtins. On execution: check both versions, index, push.

From `Python/bytecodes.c` (paraphrased; check the file for live source):

```c
inst(LOAD_GLOBAL_MODULE, (unused/1, version/1, index/1 -- res[1 + (oparg & 1)])) {
    DEOPT_IF(!PyDict_CheckExact(GLOBALS()));
    PyDictObject *dict = (PyDictObject *)GLOBALS();
    DEOPT_IF(dict->ma_keys->dk_version != version);
    assert(DK_IS_UNICODE(dict->ma_keys));
    PyDictUnicodeEntry *entries = DK_UNICODE_ENTRIES(dict->ma_keys);
    res[0] = entries[index].me_value;
    DEOPT_IF(res[0] == NULL);
    Py_INCREF(res[0]);
}
```

The two `DEOPT_IF` calls are the **guards**. If either fails — globals is no longer a plain dict, or its version changed (someone added/removed a key) — control falls back to the generic `LOAD_GLOBAL`. The opcode itself is rewritten to generic in place, so subsequent executions don't keep deopting.

In nanoseconds, **`LOAD_GLOBAL_BUILTIN` is roughly 5–8 ns**, vs. 30–60 ns for unspecialized `LOAD_GLOBAL`. That is the win.

## 6. Walkthrough: `BINARY_OP` → `BINARY_OP_ADD_INT`

The numerical specializations are the cleanest case to study. From `Python/bytecodes.c`:

```c
inst(BINARY_OP_ADD_INT, (left, right -- res)) {
    DEOPT_IF(!PyLong_CheckExact(left));
    DEOPT_IF(!PyLong_CheckExact(right));
    STAT_INC(BINARY_OP, hit);
    res = _PyLong_Add((PyLongObject *)left, (PyLongObject *)right);
    Py_DECREF(left);
    Py_DECREF(right);
    if (res == NULL) goto pop_2_error;
}
```

Two type checks (cheap pointer comparisons against the canonical `PyLong_Type` after the `_CheckExact` macro expands), one direct call to `_PyLong_Add`, two decrefs. Compare to the slow path:

```c
inst(BINARY_OP, (lhs, rhs -- res)) {
    // ... adaptive trigger check ...
    res = _PyEval_BinaryOps[oparg](lhs, rhs);
    if (res == NULL) goto pop_2_error;
}
```

Where `_PyEval_BinaryOps[0]` is `PyNumber_Add`, which does:

1. Look up `lhs->ob_type->tp_as_number->nb_add` (slot lookup).
2. Call it. It may return `NotImplemented`.
3. If `NotImplemented`, look up `rhs->ob_type->tp_as_number->nb_add` (the right-hand `__radd__` path).
4. Call that. If `NotImplemented`, look up sequence concatenation.
5. If still no match, raise `TypeError`.

Even when both operands are `int`, the slow path runs through all that protocol scaffolding. The specialized path skips all of it because the **guard already proved both operands are `int`**.

A rough microbenchmark on a 2026-vintage laptop (Apple M3 / Intel 13th-gen, Python 3.13):

```
BINARY_OP (generic, two ints):                ~12 ns / op
BINARY_OP_ADD_INT (specialized, two ints):    ~2.5 ns / op
```

A **~5× win** on a hot integer add. We measure this in Exercise 2.

## 7. The warm-up counter

How does the runtime know when to specialize? An **adaptive counter** in the inline cache slots. Roughly (the constants change between releases; check `Python/specialize.c`):

- Every adaptive opcode starts with `ADAPTIVE_WARMUP_VALUE` in its counter (currently 52, encoded as a 16-bit value with some low bits reserved for backoff state).
- On each execution, `DECREMENT_ADAPTIVE_COUNTER` decrements.
- When the counter reaches zero, the specializer runs. It examines the actual operand types, picks a specialization, and rewrites the opcode in place.
- If specialization fails (e.g., types don't match any known specialization), the counter is reset to `ADAPTIVE_BACKOFF_VALUE` with exponential backoff up to a maximum, so we don't retry forever.

The 52-iteration warm-up is the reason adaptive specialization doesn't slow down **cold** code. Functions called once never specialize, so they don't pay any specialization cost. Hot loops cross the threshold quickly and benefit from then on.

To **force** specialization for an exercise, you simply call the function in a loop:

```python
def add(a, b):
    return a + b

for _ in range(100):     # well above the 52 threshold
    add(3, 4)

import dis
dis.dis(add, adaptive=True, show_caches=True)
# now BINARY_OP has been rewritten to BINARY_OP_ADD_INT
```

## 8. Deoptimization

What if the types change? Consider:

```python
def add(a, b):
    return a + b

for _ in range(100):
    add(3, 4)         # specialize to BINARY_OP_ADD_INT

add("a", "b")         # guard fails: not both ints!
```

What happens:

1. `BINARY_OP_ADD_INT` runs.
2. `DEOPT_IF(!PyLong_CheckExact(left))` triggers — `left` is a `str`, not a `long`.
3. The deopt macro: decrement instruction pointer (so we re-execute), rewrite the opcode back to generic `BINARY_OP`, jump to the generic handler.
4. The generic handler runs `PyNumber_Add`, which calls `str.__add__`, which works.
5. Now the opcode is generic again. On further executions, the adaptive counter ticks again — if the workload is now mostly strings, it may re-specialize to `BINARY_OP_ADD_UNICODE`.

This is a **single-call-site adaptive system**. Each opcode at each bytecode offset has its own counter, its own specialization, its own deopt state. If your function is monomorphic per call site (same types every time), you win big. If it is polymorphic (types change every call), you stay on the generic path. There is no JIT to re-compile; there is only the in-place opcode rewriting.

## 9. Reading specialized disassembly

`dis.dis(func, adaptive=True, show_caches=True)` shows the post-specialization opcodes plus cache slots. The two flags are independent:

- `adaptive=True` — show the currently-rewritten opcode (e.g., `BINARY_OP_ADD_INT` instead of the original `BINARY_OP`).
- `show_caches=True` — show the inline-cache `_Py_CODEUNIT` slots as `CACHE` lines.

Example after warming up `add(int, int)`:

```
  2           RESUME                   0
  3           LOAD_FAST                0 (a)
              LOAD_FAST                1 (b)
              BINARY_OP_ADD_INT        0 (+)
              CACHE                    0 (counter: 53)
              CACHE                    0 (lhs_type_version: ...)
              CACHE                    0 (...)
              CACHE                    0 (...)
              CACHE                    0 (...)
              RETURN_VALUE
```

The counter is now well above zero (indicating we are in the "hit" zone, not the "warm-up" zone). The version tags encode the `int` type's identity.

## 10. The cost of polymorphism

Specialization rewards monomorphism — call sites that see one consistent type. Polymorphic call sites — where types vary — pay extra: every type change causes a deopt cycle, and the adaptive counter ticks back up before another attempt.

In practice this is rarely a problem because most Python code is naturally monomorphic at the per-call-site level. But it does mean:

- **A function called with mixed types may show the generic opcode in disassembly**, even after many calls. The counter has been reset by repeated guard failures, so specialization keeps backing off.
- **Switching types at a call site has a measurable cost** — small, but real. The first `add("a","b")` after thousands of `add(int,int)` calls is briefly slower than steady-state.

For the realistic workloads PEP 659 targets, this is the right tradeoff. The Python community traded a tiny polymorphism tax for a substantial monomorphism win.

## 11. The interaction with monitoring

`sys.monitoring` (PEP 669) installs instrumentation by rewriting opcodes to instrumented variants (`INSTRUMENTED_LOAD_GLOBAL`, etc.). When monitoring is active for a frame, specialization may be **disabled** for instrumented opcodes — because the instrumentation must intercept every dispatch, and a specialized opcode might skip the instrumentation point.

The practical consequence: a `sys.monitoring`-enabled tracer slows down execution measurably (typically 20–80%), and **`sys.settrace` slows it down dramatically more** (often 5–10×). The difference is precisely that `sys.monitoring` is designed to be turned on and off per-event-type per-tool, with minimal disruption to specialization; `sys.settrace` forces global per-line instrumentation that defeats most of the adaptive machine.

This will matter directly when you build the Week 3 mini-project: choose `sys.monitoring` if you have 3.12+ (you do — the prerequisites require it).

## 12. What you should be able to do now

- Predict the opcode for any name reference in a given function: `LOAD_FAST` / `LOAD_DEREF` / `LOAD_GLOBAL` / `LOAD_NAME`.
- Warm up a function with a hot loop and verify, via `dis.dis(..., adaptive=True)`, that the expected specialization happened.
- Predict, given a function and a workload, whether a given call site will specialize and to which variant.
- Read a `Python/bytecodes.c` entry for a specialized opcode and identify (a) the guards, (b) the fast-path body, (c) the deopt fall-through.
- Estimate the cost difference between a generic and a specialized variant of `LOAD_GLOBAL` and `BINARY_OP` to within a factor of 2.

Move on to Lecture 3, where the question becomes: now that we know one thread is fast, what happens when we add a second thread?
