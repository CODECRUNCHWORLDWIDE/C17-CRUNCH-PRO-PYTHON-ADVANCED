# Week 1 — CPython Internals and the Mental Model

> *What is `python`? Where does it live? What happens between the moment you press Enter and the moment your script prints?*

Welcome to C17. Week 1 is a tour of the runtime you've been using for years without thinking about. By Sunday you will be able to:

- Tell someone, in three sentences, what `python` actually *is* (which artifact, which language, which interpreter).
- Open the CPython repository and find your way around without panicking.
- Disassemble any Python expression to its bytecode and read it line by line.
- Explain the compilation pipeline from source to bytecode to execution.
- Read a `.pyc` file's magic number and understand why it changes per Python release.

This week is light on code and heavy on reading. That's deliberate. The rest of C17 builds on a correct mental model of the runtime — if you skip that, every later week will be a leaky abstraction.

---

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish** between Python (the language), CPython (the reference implementation), and other Python implementations (PyPy, MicroPython, GraalPy, RustPython).
- **Locate** the CPython source tree on GitHub and find the file responsible for any given feature (the parser, the compiler, the evaluation loop, the GC, an individual builtin).
- **Trace** a Python expression from source text → tokens → AST → bytecode → execution, using only stdlib tools (`tokenize`, `ast`, `dis`).
- **Read** a `.pyc` file: identify the magic number, the source modification timestamp, the marshalled code object.
- **Run** Python in non-default modes: `python -O`, `python -i`, `python -c`, `python -m`, `python -X dev`, and explain what each does.
- **Find and apply** at least one performance fix at the bytecode level — for instance, the difference between `LOAD_FAST` and `LOAD_GLOBAL`.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | Past the outcome set: a second programming course stops at “the compiler produces an executable”. This week opens the interpreter instead — source to tokens to AST to bytecode — and then builds it from source. |
| Industry | Find, by file and line, the code responsible for one behaviour in a codebase of millions of lines you have never opened, before you change anything in it. |
| Beyond the bar | It asks the learner to compile the interpreter they have been running for years, then locate the C function behind `sum` — `challenges/challenge-01-build-cpython-from-source.md` |


---

## Prerequisites

You've taken the [diagnostic quiz](../diagnostic-quiz.md) and scored ≥18/25. If not, do C16 first.

## Topics covered

- Python the language vs. CPython the implementation
- The CPython repo tour: `Python/`, `Objects/`, `Modules/`, `Include/`, `Parser/`
- Other implementations: PyPy, MicroPython, GraalPy, RustPython, Pyston
- The execution pipeline: source → tokens → AST → bytecode → `ceval.c`
- `dis` module: disassembling functions, modules, lambdas, and code objects
- Bytecode you'll see most often: `LOAD_FAST`, `LOAD_GLOBAL`, `LOAD_CONST`, `STORE_FAST`, `BINARY_OP`, `CALL`, `RETURN_VALUE`
- The `code` object: `co_code`, `co_consts`, `co_varnames`, `co_names`
- `.pyc` files: magic numbers, the cache hierarchy, when Python re-compiles
- `sys.flags`, `PYTHONOPTIMIZE`, the difference between `-O` and `-OO`
- The build steps: how to build CPython yourself from source (we do this Thursday)

---

## Weekly schedule

| Day       | Focus                                    | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Language vs implementation; CPython repo |    2h    |    1h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5h      |
| Tuesday   | Tokens, AST, the compilation pipeline    |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | Bytecode and `dis`                       |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Thursday  | Building CPython from source             |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | `.pyc` files, magic numbers              |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Saturday  | Mini-project deep work                   |    0h    |    0h     |     0h     |    0h     |   1h     |     3h       |    0h      |     4h      |
| Sunday    | Quiz, review, polish                     |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                          | **6h**   | **8h**    | **4h**     | **3h**    | **6h**   | **7h**       | **2h**     | **36h**     |

---

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Curated readings, PEPs, CPython devguide |
| [lecture-notes/01-language-vs-implementation.md](./lecture-notes/01-language-vs-implementation.md) | Python vs CPython, the implementation landscape |
| [lecture-notes/02-the-compilation-pipeline.md](./lecture-notes/02-the-compilation-pipeline.md) | Source → AST → bytecode |
| [lecture-notes/03-reading-bytecode.md](./lecture-notes/03-reading-bytecode.md) | `dis`, the `code` object, why `LOAD_FAST` beats `LOAD_GLOBAL` |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-tokenize-and-ast.py](./exercises/exercise-01-tokenize-and-ast.py) | Tokenize and AST-dump real Python code |
| [exercises/exercise-02-disassemble.py](./exercises/exercise-02-disassemble.py) | Disassemble five expressions and explain each opcode |
| [exercises/exercise-03-pyc-reader.py](./exercises/exercise-03-pyc-reader.py) | Read and decode a `.pyc` file |
| [challenges/README.md](./challenges/README.md) | Index of weekly challenges |
| [challenges/challenge-01-build-cpython-from-source.md](./challenges/challenge-01-build-cpython-from-source.md) | Compile CPython on your machine |
| [challenges/challenge-02-find-a-builtin.md](./challenges/challenge-02-find-a-builtin.md) | Locate the C implementation of `sum`, `len`, `print` |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems |
| [mini-project/README.md](./mini-project/README.md) | The "Python Explainer" mini-project |

---

## Stretch goals

- Read the [CPython Developer's Guide](https://devguide.python.org/) cover to cover.
- Watch [Anthony Shaw's PyCon talk on CPython internals](https://www.youtube.com/results?search_query=anthony+shaw+cpython+internals) — pick the most recent year.
- Browse `Python/ceval.c` and find the case statement for any single opcode of your choice. Read it. Don't worry about understanding *everything*; understanding *one thing* is the goal.

---

## Up next

[Week 2 — The Object Model: Refcounting, GC, Memory](../week-02-object-model-refcounting-gc-memory/) — once your mini-project is on GitHub.
