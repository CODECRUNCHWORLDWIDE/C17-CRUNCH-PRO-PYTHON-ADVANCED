# Week 2 — The Object Model: Refcounting, GC, Memory

> *Every assignment in Python is a pointer-copy with a refcount bump. Every `del`, every function return, every name going out of scope decrements a refcount. If you can hold that picture clearly, you understand 80% of CPython's memory behavior.*

Welcome to Week 2 of **C17 · Crunch Pro Python Advanced**. Week 1 mapped the runtime and the compilation pipeline. This week we go down to the object level: how CPython tracks objects in memory, when memory is freed, what `__slots__` does, why the cyclic garbage collector exists, and how to actually measure memory in real programs.

By Sunday you'll have used `tracemalloc`, `objgraph`, and `memray` against real code; you'll have detected a memory leak; and you'll understand why generators sometimes hold memory you didn't expect.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** how CPython's reference counting works at the level of `Py_INCREF` / `Py_DECREF`, including when each fires from your Python code.
- **Distinguish** reference cycles from non-cycles, and explain why refcounting alone isn't enough.
- **Read** `sys.getrefcount` output without being fooled by the off-by-some count (`getrefcount` itself bumps the count).
- **Use** `__slots__` to reduce per-instance memory, and articulate what you give up.
- **Detect** a memory leak using `tracemalloc` (stdlib, no install) and `memray` (community, the modern choice).
- **Visualize** an object graph with `objgraph` to find what's keeping a leaking object alive.
- **Recognize** the canonical leak patterns: long-lived caches, module-level lists, generators that pin closures.
- **Reason** about `weakref` — when it solves a problem, when it just defers one.
- **Tour** the cyclic garbage collector's three generations and explain why they exist.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | `EECS 280` — Reason about object lifetime and dynamic memory: when storage is allocated, who owns it, when it is released, and what one instance of a class costs. |
| Industry | Take a service whose resident memory grows overnight, reproduce the growth deterministically, and name the file and line that is holding the objects alive. |
| Beyond the bar | The leak hunt runs against a real codebase with `tracemalloc`, `memray` and `objgraph`, and the deliverable is the evidence rather than the patch — `challenges/challenge-01-hunt-a-leak.md` |


## Prerequisites

- **C17 Week 1** completed.
- Comfort with C concepts at the *reading* level — you don't have to write C this week, but you should not panic at a `Py_DECREF` macro.

## Topics covered

- CPython's `PyObject` struct: refcount + type pointer + payload
- The `Py_INCREF` / `Py_DECREF` discipline as the foundation
- Where reference counts come from in your Python code (the implicit `INCREF` on every name binding)
- Why the count isn't always what you expect (small-int caching, interned strings, the `+3` from `sys.getrefcount`)
- The cyclic garbage collector: why it exists, how it finds cycles, the three generations
- `gc.get_objects`, `gc.get_referrers`, `gc.collect`, `gc.disable`
- `__slots__`: the memory win, the features lost
- `weakref` and `WeakValueDictionary` — the cache-without-keeping-alive pattern
- `tracemalloc` — the stdlib leak hunter
- `memray` — the modern, open-source flamegraph-producing leak hunter
- `objgraph` — visualize what's keeping an object alive
- Common leak patterns: bound methods in callbacks, frame retention in tracebacks, generator-closure retention
- The 3.13 free-threaded build's refcounting wrinkles (the "biased reference counting" preview)

## Weekly schedule (~36h intensive)

| Day       | Focus                                            | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The PyObject struct + refcounting                | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | Cycles + the generational GC                     | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0h         | 6.5h        |
| Wednesday | `__slots__`, `weakref`, caching without leaking  | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 7h          |
| Thursday  | Tooling tour: `tracemalloc`, `memray`, `objgraph` | 0h       | 1.5h      | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6.5h        |
| Friday    | Mini-project deep work                           | 0h       | 1h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6h          |
| Saturday  | Mini-project polish                              | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                | 0h       | 0h        | 0h         | 0.5h      | 0h       | 0h           | 0h         | 0.5h        |
| **Total** |                                                  | **6h**   | **8h**    | **4h**     | **3h**    | **6h**   | **7h**       | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Curated readings + CPython source pointers |
| [lecture-notes/01-the-pyobject-struct-and-refcounts.md](./lecture-notes/01-the-pyobject-struct-and-refcounts.md) | The struct, INCREF/DECREF, where refcounts come from |
| [lecture-notes/02-cycles-and-the-generational-gc.md](./lecture-notes/02-cycles-and-the-generational-gc.md) | Why refcounting isn't enough; the GC's job |
| [lecture-notes/03-slots-weakref-and-tooling.md](./lecture-notes/03-slots-weakref-and-tooling.md) | `__slots__`, `weakref`, `tracemalloc`, `memray` |
| [exercises/README.md](./exercises/README.md) | Index |
| [exercises/exercise-01-trace-refcounts.py](./exercises/exercise-01-trace-refcounts.py) | Watch refcounts move |
| [exercises/exercise-02-build-a-cycle.py](./exercises/exercise-02-build-a-cycle.py) | Build, detect, break a cycle |
| [exercises/exercise-03-slots-comparison.py](./exercises/exercise-03-slots-comparison.py) | Measure the `__slots__` memory win |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-hunt-a-leak.md](./challenges/challenge-01-hunt-a-leak.md) | Real leak in a real codebase |
| [challenges/challenge-02-cache-without-keeping-alive.md](./challenges/challenge-02-cache-without-keeping-alive.md) | Design a leak-free cache |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~6h) |
| [mini-project/README.md](./mini-project/README.md) | Detect a leak in a small OSS project |

## Stretch

- Read `Include/object.h` from the CPython source — find the `PyObject` struct, read the comments. <https://github.com/python/cpython/blob/main/Include/object.h>
- Read `Modules/gcmodule.c` and find the function that runs a generational sweep.
- Read PEP 442 — the safe-object-finalization PEP that fixed Python 3's cyclic-`__del__` story.

## Up next

[Week 3 — Bytecode, the Stack Machine, and the GIL](../week-03-bytecode-stack-machine-gil/).
