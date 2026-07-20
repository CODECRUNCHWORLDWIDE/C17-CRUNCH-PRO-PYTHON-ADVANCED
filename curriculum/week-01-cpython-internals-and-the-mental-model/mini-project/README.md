# Mini-Project — The Python Explainer

> Build a CLI tool, `pyexplain`, that takes any `.py` file and produces a side-by-side report of its tokens, AST, and bytecode.

This is the practical synthesis of the whole week. By implementing it, you'll touch each of the stdlib modules you met in lecture (`tokenize`, `ast`, `dis`, `marshal`, optionally `symtable`), build a real CLI you can keep using forever, and exit Week 1 with a finished tool you can show someone.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

---

## What you will build

A CLI tool named `pyexplain` that:

1. Takes a `.py` file as input.
2. Produces a Markdown (or plain-text, your choice) report with at least four sections:
   - The source code (with line numbers).
   - The token stream.
   - The AST dump.
   - The bytecode disassembly.
3. Saves the report next to the source as `<source>.explained.md`.
4. Supports a `--bytecode-only`, `--ast-only`, or `--tokens-only` flag for slicing.
5. Handles syntax errors gracefully (prints the error, doesn't crash).
6. Is packaged as a real Python project — `pyproject.toml`, `src/pyexplain/`, installable with `pip install -e .`.

---

## Acceptance criteria

- [ ] A new public GitHub repo `c17-week-01-pyexplain-<yourhandle>`.
- [ ] `pip install -e .` from a fresh clone works.
- [ ] After install, `pyexplain --help` shows the CLI flags.
- [ ] `pyexplain examples/sample.py` produces `examples/sample.py.explained.md`.
- [ ] The output Markdown contains all four sections (source, tokens, AST, bytecode), each clearly headed.
- [ ] `--bytecode-only`, `--ast-only`, `--tokens-only` work and emit only that section.
- [ ] A `tests/` directory contains at least four pytest tests covering: success on a valid file, graceful failure on a syntax error, the `--bytecode-only` flag, and the `--ast-only` flag.
- [ ] `python -m pytest -q` passes on a fresh clone.
- [ ] `README.md` includes setup, usage examples, screenshots/asciinema (optional), and a "Why I built this" section.

---

## Suggested layout

```
pyexplain/
├── pyproject.toml
├── README.md
├── src/
│   └── pyexplain/
│       ├── __init__.py
│       ├── cli.py            ← argparse, entry point
│       ├── tokens.py         ← wraps tokenize
│       ├── ast_renderer.py   ← wraps ast.dump
│       ├── bytecode.py       ← wraps dis
│       └── report.py         ← stitches the four sections into Markdown
├── examples/
│   └── sample.py             ← something interesting to feed it
└── tests/
    ├── test_cli.py
    ├── test_tokens.py
    ├── test_ast.py
    └── test_bytecode.py
```

---

## Suggested order of operations

### Phase 1 — Setup (45 min)

1. Make repo, venv, `pyproject.toml`. Pin Python ≥3.11 and use `setuptools` or `hatchling` as the build backend (your choice).
2. Add an entry point so `pyexplain` is a CLI command after `pip install -e .`:

   ```toml
   [project.scripts]
   pyexplain = "pyexplain.cli:main"
   ```

3. Create the `src/pyexplain/` package with empty modules. First commit.

### Phase 2 — Tokens, AST, bytecode wrappers (2 h)

Each in its own module, each ~30 lines:

- `tokens.py`: function `render_tokens(source: str) -> str` that returns a markdown table of tokens.
- `ast_renderer.py`: function `render_ast(source: str) -> str` that returns a fenced code block of `ast.dump(...)` output.
- `bytecode.py`: function `render_bytecode(source: str) -> str` that uses `dis.Bytecode(compile(source, "<demo>", "exec"))` and renders each instruction in a markdown table.

Each function should accept any failure mode (syntax error → returns a `<error>` block; not crash).

### Phase 3 — Report assembler + CLI (1.5 h)

- `report.py`: function `build_report(source: str, *, sections: list[str]) -> str` that calls the renderers and stitches them with `## Section` headers.
- `cli.py`: argparse parsing, file I/O, calling the renderer, writing the output file.

### Phase 4 — Tests (1.5 h)

Four `pytest` test files. Use `tmp_path` fixtures. Don't shell out — call `pyexplain.cli.main(args)` directly.

### Phase 5 — Polish (1 h)

- Write the README. Setup, example invocation, screenshot of the output, "Why I built this" reflection.
- Commit example file. Commit example output.
- Push to GitHub.

---

## Stretch goals

- Add `--symtable` to include `symtable.symtable(source, ...)` output.
- Add `--compare <other.py>` that runs both files through the pipeline and produces a diff.
- Make the output renderable as syntax-highlighted HTML using `pygments` (free, MIT-licensed).
- Publish `pyexplain` to PyPI under your own name. (Strongly recommended for anyone serious about OSS — gets you over the publishing hump.)
- Add a `--watch` mode that re-runs whenever the source file changes (use `watchfiles` or stdlib `os.stat` polling).

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| It runs | 25% | `pip install -e .`, `pyexplain --help`, `pyexplain sample.py` all work on a fresh clone |
| Code clarity | 20% | Each module has one job, ≤80 lines |
| Tests | 20% | Coverage ≥80%, including a syntax-error case |
| Report quality | 15% | The output Markdown is something you'd actually read |
| README | 10% | Someone can install and use without asking you a question |
| Stretch | 10% | Any one of the stretch goals delivered |

---

## Why this matters

You'll have a tool you can keep using for the rest of your career. The first time you wonder "how does Python compile this?", you'll reach for your own `pyexplain` and get the answer in 2 seconds. That's the kind of leverage Week 1 is supposed to build.

The capstone (Week 12) revisits some of this: many open-source bugs in interpreters are debugged by exactly this kind of side-by-side rendering. You're learning the workflow now.

---

## Submission

Commit, push, share the URL.
