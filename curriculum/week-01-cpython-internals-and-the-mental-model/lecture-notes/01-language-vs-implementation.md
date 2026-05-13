# Lecture 1 — Language vs Implementation

> **Outcome:** You can answer "what is Python?" in three sentences, name three Python implementations besides CPython, and find your way around the CPython source tree without panicking.

## 1. Python ≠ CPython

When a teacher says "Python," they usually mean three different things, sometimes at the same time:

1. **The Python language** — the *specification* of syntax, semantics, and the standard library. Defined by the [Python Language Reference](https://docs.python.org/3/reference/) plus the body of accepted [PEPs](https://peps.python.org/).
2. **A Python implementation** — a program that *runs* code conforming to the spec.
3. **The interpreter executable on your machine** — almost always `/usr/bin/python` (or similar), which is almost always the CPython implementation.

**CPython** is the *reference implementation*: the version everyone else's behavior is measured against. Written in C (mostly) and Python (the standard library). Maintained by the Python core team. When the docs and the implementation disagree, the docs usually update to match CPython.

The distinction matters because:

- A line of Python code that runs on CPython might run differently on PyPy or MicroPython (rare, but it happens).
- The GIL is a property of *CPython*, not of *Python*. PyPy has one too; some research forks don't.
- Performance characteristics are properties of an implementation, not of the language. "Python is slow" is short for "CPython is slower than C on this workload, but PyPy might be 5× faster."

When you write `python my_script.py`, you're invoking *one specific implementation* (almost always CPython). C17 is mostly about CPython — that's what 95%+ of real Python jobs deploy.

---

## 2. The Python implementation landscape (2026)

| Implementation | Language | Sweet spot | Production-ready? |
|----------------|----------|------------|---|
| **CPython** | C + Python | Default. Maximum library compatibility. | ✅ |
| **PyPy** | RPython (a Python subset) | Long-running CPU-bound pure-Python code | ✅ for compatible workloads |
| **MicroPython** | C | Microcontrollers (≥16KB RAM, ≥256KB ROM) | ✅ for hardware |
| **GraalPy** | Java / GraalVM | JVM interop, polyglot apps | ✅ in many setups |
| **RustPython** | Rust | Educational; sandboxed environments | 🚧 |
| **Pyston** | C (fork of CPython) | CPython-compatible speedup attempts | 🚧 (maintenance-mode in 2026) |
| **CinderX** (Meta) | C (fork of CPython) | Meta's internal optimizations | Internal use; partly open-sourced |

For C17 you'll spend ~98% of your time with CPython. We'll discuss PyPy and free-threaded CPython in Week 3 (the GIL week).

---

## 3. A guided tour of the CPython repository

Open <https://github.com/python/cpython> in another tab. The directory layout looks like this (top-level, with the meaningful entries):

```
cpython/
├── Doc/          ← the official docs (in reStructuredText; what docs.python.org renders)
├── Include/      ← public C API header files (Python.h and friends)
├── Lib/          ← the standard library WRITTEN IN PYTHON
├── Modules/      ← standard library modules written in C
├── Objects/      ← C source for built-in object types (int, list, dict, …)
├── Parser/       ← the parser (currently PEG-based; PEP 617)
├── Python/       ← the heart: ceval.c, compile.c, errors.c, the import system
├── Tools/        ← helper scripts for the core devs
├── configure*    ← autoconf entry points (Unix build)
├── PCbuild/      ← Windows build files
└── PCBuild/, PC/ ← Windows-specific bits
```

You only need to know **four** of these well enough to navigate them:

### `Lib/` — pure-Python stdlib

This is where everything in `import xxx` that isn't a C module lives. Examples:

- `Lib/dis.py` — the disassembler. You'll read this in Lecture 3.
- `Lib/asyncio/` — the entire `asyncio` package.
- `Lib/json/` — the JSON encoder/decoder (with a C accelerator in `Modules/_jsonmodule.c`).
- `Lib/typing.py` — the typing module.

When you `import asyncio`, Python finds and runs `Lib/asyncio/__init__.py`. You can `cat` it on your machine right now:

```bash
python -c "import asyncio; print(asyncio.__file__)"
```

That prints the path to the file CPython is actually running. You can `open` it in your editor. Reading the stdlib is one of the fastest ways to become a better Python programmer.

### `Objects/` — built-in types in C

| File | What's in it |
|------|--------------|
| `longobject.c` | `int` (Python ints; arbitrary precision) |
| `listobject.c` | `list` |
| `dictobject.c` | `dict` (the hash table) |
| `unicodeobject.c` | `str` |
| `tupleobject.c` | `tuple` |
| `setobject.c` | `set` and `frozenset` |
| `bytesobject.c` | `bytes` |
| `genobject.c` | generators and async generators |
| `funcobject.c` | functions and lambdas |
| `typeobject.c` | the type/metaclass machinery |

When someone says "Python's `int` is implemented as a variable-length C array," they mean: see `Objects/longobject.c`.

### `Python/` — the interpreter loop

| File | What's in it |
|------|--------------|
| `ceval.c` | the main bytecode evaluation loop ("CEVAL" = "C eval") |
| `compile.c` | AST → bytecode |
| `import.c` | the import system |
| `errors.c` | exception machinery |
| `pyhash.c` | the hash randomization implementation |
| `pylifecycle.c` | interpreter startup and shutdown |
| `pythonrun.c` | running a file or string |

`ceval.c` is the heart of CPython. It's a massive `switch` statement over the bytecode instructions. Don't try to read all of it. Find one opcode (say, `BINARY_OP`) and read just that case. That's the lecture for today.

### `Modules/` — C extensions in the stdlib

| File | What it provides |
|------|------------------|
| `_jsonmodule.c` | C accelerator for `json` |
| `_pickle.c` | C accelerator for `pickle` |
| `_io/` | the IO stack |
| `_threadmodule.c` | the `threading` primitives |
| `_asynciomodule.c` | C-level helpers for `asyncio` (Task, Future) |
| `_sqlite/` | the `sqlite3` package |

When a stdlib module has a leading underscore version (e.g. `_json`), it's the C-implemented fast path. The pure-Python version in `Lib/json/` calls into it.

---

## 4. Finding a feature in CPython source

A useful skill: "I want to know how Python implements **X**. Where do I look?"

| Question | Where to look |
|----------|---------------|
| How is `len(...)` implemented? | `Python/bltinmodule.c` for the builtin, then `tp_size` slot on each type in `Objects/*.c` |
| What does `list.append` actually do? | `Objects/listobject.c`, search for `app1` |
| How does `import x` work? | `Python/import.c` and `Lib/importlib/_bootstrap.py` |
| How is the GIL implemented? | `Python/ceval_gil.c` |
| How does Python parse my code? | `Parser/` (PEG grammar in `Grammar/python.gram`) |
| What does `async def` desugar to? | `Python/compile.c` (search for `async`) |
| How are integers stored? | `Objects/longobject.c` |

The GitHub search box (`/` key) is your friend. Pro tip: when you find the file, click the line number to get a permalink you can share or bookmark.

---

## 5. The "Python is just a wrapper" mental shift

Here's the shift Week 1 wants you to make:

- Your `.py` file is text.
- `python` is a C program that reads that text and *executes some interpretation of it*.
- That interpretation involves compiling your source to bytecode, then running that bytecode on a stack machine.
- Everything you can do in Python — every list comprehension, every `async def`, every metaclass — is ultimately a sequence of low-level operations on the interpreter's stack and a small set of object types in C.

You don't need to know C to think this way. You just need to be willing to occasionally peek at the C and not be intimidated.

In Week 2 we'll go down to the object level (refcounts, GC, memory). In Week 3 we'll go down to the evaluation loop (the GIL, free-threading). For now, getting the macro picture right is enough.

---

## 6. Self-check

Without re-reading:

1. What is the difference between "Python" and "CPython"?
2. Name three other Python implementations.
3. In which top-level directory of the CPython repo would you find `Lib/asyncio/__init__.py`?
4. In which directory would you find the C implementation of `int`?
5. What is `Python/ceval.c`?
6. You want to know how `dict.items()` is implemented. Where do you start?

---

## Further reading

- **CPython Developer's Guide — Source tour**: <https://devguide.python.org/internals/exploring/>
- **Python Language Reference**: <https://docs.python.org/3/reference/>
- **Anthony Shaw, "Your Guide to the CPython Source Code"** (Real Python, free):
  <https://realpython.com/cpython-source-code-guide/>

Next: [Lecture 2 — The Compilation Pipeline](./02-the-compilation-pipeline.md).
