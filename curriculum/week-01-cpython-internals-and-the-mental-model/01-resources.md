# Week 1 — Resources

Every resource here is **free** and **publicly accessible**.

## Primary sources

- **CPython on GitHub** — the implementation. Open this in a tab.
  <https://github.com/python/cpython>
- **CPython Developer's Guide** — the official docs for working ON Python (not just IN Python).
  <https://devguide.python.org/>
- **Python Language Reference** — the language itself, separate from the implementation.
  <https://docs.python.org/3/reference/>
- **dis — module documentation**:
  <https://docs.python.org/3/library/dis.html>
- **ast — module documentation**:
  <https://docs.python.org/3/library/ast.html>
- **tokenize — module documentation**:
  <https://docs.python.org/3/library/tokenize.html>

## The PEPs you should read this week

- **PEP 3147 — PYC repository directory** — why `.pyc` files live in `__pycache__/`:
  <https://peps.python.org/pep-3147/>
- **PEP 626 — Precise line numbers for debugging** — context for bytecode line tables:
  <https://peps.python.org/pep-0626/>
- **PEP 659 — Specializing adaptive interpreter** — the 3.11+ speedups, the most readable PEP on internals:
  <https://peps.python.org/pep-0659/>
- **PEP 657 — Include fine-grained error locations** — the "improved error messages" you've enjoyed since 3.11:
  <https://peps.python.org/pep-0657/>

## Free books and write-ups

- **"CPython Internals" by Anthony Shaw** — the book is paid, but the free article series on Real Python is excellent:
  <https://realpython.com/cpython-source-code-guide/>
- **The Python Language Reference (free, official)**:
  <https://docs.python.org/3/reference/index.html>
- **"How CPython implements and uses bloom filters for string interning"** — Artem Golubin:
  <https://rushter.com/blog/python-strings-and-memory/>
- **"What is the meaning of 'invalidating' a stack frame in CPython?"** — StackOverflow accepted answer (canonical):
  <https://stackoverflow.com/questions/tagged/cpython>

## Open-source projects to read (in this order)

1. **`Lib/dis.py`** — the disassembler is pure Python. Read it. Understand how `dis(func)` works under the hood:
  <https://github.com/python/cpython/blob/main/Lib/dis.py>
2. **`Lib/ast.py`** — the AST helpers, also pure Python:
  <https://github.com/python/cpython/blob/main/Lib/ast.py>
3. **`Python/ceval.c`** — the evaluation loop. Don't try to read it all; find one opcode case and read just that:
  <https://github.com/python/cpython/blob/main/Python/ceval.c>
4. **`Objects/longobject.c`** — how `int` is implemented:
  <https://github.com/python/cpython/blob/main/Objects/longobject.c>

## Other Python implementations

- **PyPy** — the JIT-compiled Python. Mostly compatible with CPython.
  <https://pypy.org/>
- **MicroPython** — minimal Python for microcontrollers (~256KB ROM):
  <https://micropython.org/>
- **GraalPy** — Python on Oracle's GraalVM. Faster on some workloads.
  <https://www.graalvm.org/python/>
- **RustPython** — Python interpreter written in Rust. Educational; not production-ready:
  <https://rustpython.github.io/>
- **Pyston** — fork of CPython with performance optimizations:
  <https://github.com/pyston/pyston>

## Videos (free)

- **"Python's bytecode" — Anthony Shaw, PyCon US**: <https://www.youtube.com/results?search_query=anthony+shaw+cpython+bytecode>
- **"PyCon 2023 — Inside CPython 3.11's frame stack" — Mark Shannon**: search YouTube for "Mark Shannon CPython"

## Tools you'll use

- `python -m dis <file>` — disassemble a whole file
- `python -m ast <file>` — dump the AST
- `python -m tokenize <file>` — tokenize a file
- `python -X dev script.py` — Python's "developer mode": stricter warnings, better diagnostics
- `python -c "import sys; print(sys.version_info)"` — interpreter version detail

## Glossary

| Term | One-line definition |
|------|---------------------|
| **CPython** | The reference C-language implementation of the Python language |
| **Bytecode** | The intermediate instructions CPython actually executes |
| **`.pyc`** | A file containing pre-compiled bytecode and a magic number identifying the Python version |
| **`ceval`** | `Python/ceval.c` — the main interpreter loop |
| **GIL** | Global Interpreter Lock; the mutex preventing concurrent bytecode execution |
| **AST** | Abstract Syntax Tree — the structured representation of code between parsing and bytecode generation |
| **Code object** | A Python `code` object: bytecode + constants + variable names + filename + first-line-number |
| **Magic number** | First 4 bytes of a `.pyc`; identifies which Python version compiled it |
| **CPython devguide** | <https://devguide.python.org> — for people working ON Python |
