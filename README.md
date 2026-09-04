# C17 · Crunch Pro — Python Advanced

> A 12-week open-source course on the parts of Python that separate "I write Python at work" from "people in my org ask *me* before changing the runtime." CPython internals, async, performance, C extensions, type theory, and the security parts everyone skips. The expert tier.

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built in the open](https://img.shields.io/badge/built-in%20the%20open-B98F3E.svg)](https://github.com/CODE-CRUNCH-CLUB)

This is the highest-level Python track in the Code Crunch curriculum. It assumes you have completed **C1** and at least one of **C5** (Data Science) or **C16** (Web Backend), or have equivalent professional Python experience. C17 takes you from "competent Python developer" to "open-source maintainer caliber."

If you don't yet know what the GIL is, why `list.append` is `O(1)` amortized, or what a `__slots__` declaration costs you, this track is in your future, not your present. Do C1 + C5/C16 first.

---

## What you will be able to do at the end of 12 weeks

- **Read** CPython source code without being intimidated and trace what happens between `x = []` in your code and a `PyListObject` in memory.
- **Profile** real Python code with `cProfile`, `py-spy`, `austin`, and `scalene`. Find a real bottleneck. Fix it. Measure the win.
- **Write** async Python that you trust: not just `async def`-and-hope, but actual mental models for the event loop, task lifetimes, cancellation, structured concurrency, and back-pressure.
- **Wrap** a C library with `ctypes`, `cffi`, and `Cython` — and know when each is the right choice.
- **Use** advanced typing — generics, `Protocol`, `TypeVar`, `ParamSpec`, `TypeGuard`, `assert_type`, structural typing — to make your APIs self-documenting.
- **Reason** about memory: reference counting vs. cycle collection, `gc.get_referrers`, why `__slots__` matters, when generators leak.
- **Train** a small neural network with PyTorch from a blank file, including a custom `nn.Module`, a training loop, gradient debugging, and a saved checkpoint.
- **Audit** Python code for the security failures most developers ship: pickle, YAML, eval, SSRF, ReDoS, prototype pollution analogues, dependency confusion.
- **Contribute** a non-trivial PR to a real open-source Python project.

---

## Standards & equivalency

> C17 stands in for the object-oriented half of a university's second programming course, taught in one language and pushed down into the runtime underneath it.

**University equivalent.** Programming II / Object-Oriented Programming — `COP 3337`, `CS 106B`, `CS 61B`, `EECS 280`. Coverage: partial.

Partial is meant literally, and it is one gap rather than a general thinness. C17 teaches the design ideas that course is built on — what a class instance actually holds and costs, inheritance and subclass customisation, programming to an interface, exceptions and what a failing operation promises its caller, unit tests, and the first serious multi-file program that another person can install and run. It teaches all of that in Python. What it does not teach is a statically typed language and a compiler that enforces generics before the program runs. C17 touches typing only where packaging and tooling need it — `py.typed`, `mypy` and `pyright` cooperation, PEP 484 / 585 / 604 / 695 in the capstone — so that row is marked `lighter` below and is recorded in the ledger's `stillToAdd`. If your course grades a statically typed language, take [C9 · Crunch Sharp](https://github.com/CODECRUNCHWORLDWIDE/C9-CRUNCH-SHARP) instead; it carries the same ledger entry at full coverage.

C17 carries no credit, no transcript entry, no accreditation and no proctored exam. The equivalence is one of **content and skill**: the outcomes below are taught here at the same depth or deeper, and each one is assessed. What a registrar records is not something an open repository can give you.

| University outcome | Where this course teaches it | Depth |
| --- | --- | --- |
| Design classes with encapsulation: know what an instance holds, what it costs, and how an attribute access actually resolves | [Week 02](curriculum/week-02-refcounting-gc-memory/) and [Week 10](curriculum/week-10-metaprogramming-descriptors-metaclasses/) | deeper |
| Use inheritance and polymorphism, including cooperative `super()` and the failure modes of multiple inheritance | [Week 10](curriculum/week-10-metaprogramming-descriptors-metaclasses/) | same |
| Program to an interface: state the protocol an object must satisfy, then write interchangeable implementations against it | [Week 04](curriculum/week-04-asyncio-first-principles/) and [Week 06](curriculum/week-06-threads-processes/) | same |
| Raise, propagate and handle exceptions, and design what a failing operation promises its caller | [Week 05](curriculum/week-05-structured-concurrency/) | deeper |
| Reason about object lifetime and dynamic memory: when storage is allocated, who owns it, and when it is released | [Week 02](curriculum/week-02-refcounting-gc-memory/) | deeper |
| Use generics and a type system enforced before the program runs | [Week 10](curriculum/week-10-metaprogramming-descriptors-metaclasses/) and [Week 12](curriculum/week-12-capstone-perf-tuned-python-project/) | lighter |
| Write unit tests for your own code and run them from the command line | [Week 03](curriculum/week-03-bytecode-stack-machine-gil/), [Week 04](curriculum/week-04-asyncio-first-principles/), [Week 06](curriculum/week-06-threads-processes/) and [Week 09](curriculum/week-09-packaging-and-distribution/) | same |
| Debug and measure a program systematically, with tools, rather than by inspection and guessing | [Week 07](curriculum/week-07-profiling-like-its-your-job/) | deeper |
| Compile and link a multi-file program, and reason about what crosses the boundary between separately built units | [Week 08](curriculum/week-08-c-extensions-ctypes-cffi-cython/) | same |
| Deliver the first serious multi-file program: a package layout, a build, and an artefact a stranger can install and run | [Week 09](curriculum/week-09-packaging-and-distribution/) and [Week 12](curriculum/week-12-capstone-perf-tuned-python-project/) | deeper |

Every row points at a week that **assigns work** on that outcome — an exercise, a challenge, a quiz item, homework or the mini-project — not a week that only mentions it. The one `lighter` row is the declared gap and is the same gap the ledger records.

**The industry bar.** What an employer expects of somebody paid to write Python at this level, and where C17 makes the learner do it.

| What the job expects | Where this course does it |
| --- | --- |
| Work lands as a commit in a repository you own, not a file on your desktop | every mini-project specifies the repository by name and what must be in it — for example [`curriculum/week-04-asyncio-first-principles/mini-project/README.md`](curriculum/week-04-asyncio-first-principles/mini-project/README.md) |
| You read code you did not write and form a judgement on it | [`curriculum/week-10-metaprogramming-descriptors-metaclasses/challenges/challenge-02-pep487-archeology.md`](curriculum/week-10-metaprogramming-descriptors-metaclasses/challenges/challenge-02-pep487-archeology.md), where the deliverable is a memo on a real library's migration diff, and [`curriculum/week-01-cpython-internals-and-the-mental-model/challenges/challenge-02-find-a-builtin.md`](curriculum/week-01-cpython-internals-and-the-mental-model/challenges/challenge-02-find-a-builtin.md) |
| Tests exist, and the command to run them is written down | the acceptance checklists in the Week 03, 04, 06 and 09 mini-projects — `pytest tests/` on named CPython versions, for example [`curriculum/week-06-threads-processes/mini-project/README.md`](curriculum/week-06-threads-processes/mini-project/README.md) |
| Dependencies are isolated per project | [`curriculum/week-09-packaging-and-distribution/challenges/challenge-01-multi-backend-comparison.md`](curriculum/week-09-packaging-and-distribution/challenges/challenge-01-multi-backend-comparison.md) — build in one environment, install into a fresh one, prove it works there |
| A linter and a type checker, configured where the rest of the project is configured | [`curriculum/week-09-packaging-and-distribution/lecture-notes/01-peps-and-pyproject-toml.md`](curriculum/week-09-packaging-and-distribution/lecture-notes/01-peps-and-pyproject-toml.md) — `[tool.ruff]`, `[tool.mypy]` and `[tool.pytest.ini_options]` in one `pyproject.toml` |
| A pipeline that runs on a push, not on your laptop | [`curriculum/week-09-packaging-and-distribution/mini-project/README.md`](curriculum/week-09-packaging-and-distribution/mini-project/README.md) — a `.github/workflows/publish.yml` that publishes on a tag with no token stored anywhere |
| You diagnose from what the tools actually print | [`curriculum/week-07-profiling-like-its-your-job/exercises/SOLUTIONS.md`](curriculum/week-07-profiling-like-its-your-job/exercises/SOLUTIONS.md) — `cProfile` tables captured from a real run, on stated hardware and a stated CPython build. C17 carries no `Common bugs to catch` blocks quoting tracebacks; what it has instead is a named failure-mode section per topic and the real output of `dis`, `cProfile`, `py-spy` and `scalene` to read it against |
| The output is portfolio-grade: it runs from a clean clone by following the README | [`curriculum/week-12-capstone-perf-tuned-python-project/challenges/challenge-02-reproducibility-audit.md`](curriculum/week-12-capstone-perf-tuned-python-project/challenges/challenge-02-reproducibility-audit.md) — hand the benchmark to a peer, watch them fail, close every gap |
| The practice is named, not implied | the `## Standards this week meets` block in all twelve week READMEs |

**Beyond both bars.** Clearing the two floors is entry, not success. Open any of these and check in under a minute.

| What we add | Which bar it beats | Where it lives |
| --- | --- | --- |
| Every quiz publishes its full answer key with the reasoning and the CPython source file behind each answer, folded under the questions — nothing is withheld until a deadline | both | [`curriculum/week-05-structured-concurrency/quiz.md`](curriculum/week-05-structured-concurrency/quiz.md) |
| Weeks 7 to 12 publish a worked solutions document for every exercise, including the numbers the learner should see and the wrong reading they should avoid | both | [`curriculum/week-07-profiling-like-its-your-job/exercises/SOLUTIONS.md`](curriculum/week-07-profiling-like-its-your-job/exercises/SOLUTIONS.md) |
| Three weeks sit inside the interpreter itself — build CPython from source, read the evaluation loop in `Python/ceval.c`, watch PEP 659 specialise an opcode and then deoptimise it | university | [`curriculum/week-03-bytecode-stack-machine-gil/lecture-notes/01-the-evaluation-loop-deep-dive.md`](curriculum/week-03-bytecode-stack-machine-gil/lecture-notes/01-the-evaluation-loop-deep-dive.md) |
| Every concurrency claim is settled by measurement, not assertion: one workload implemented five ways, run on two CPython builds, reduced to a table and a decision tree a teammate can use | both | [`curriculum/week-11-concurrency-models-compared/mini-project/decision-tree.md`](curriculum/week-11-concurrency-models-compared/mini-project/decision-tree.md) |
| A code-reading assignment whose deliverable is a memo rather than a program — what a real library changed when PEP 487 landed, and why one major project chose not to | industry | [`curriculum/week-10-metaprogramming-descriptors-metaclasses/challenges/challenge-02-pep487-archeology.md`](curriculum/week-10-metaprogramming-descriptors-metaclasses/challenges/challenge-02-pep487-archeology.md) |
| The course teaches against the free-threaded build and subinterpreters — PEP 703, PEP 684, PEP 734 — and asks the learner to audit their own dependencies on `python3.13t` | university | [`curriculum/week-11-concurrency-models-compared/challenges/challenge-01-free-threaded-audit.md`](curriculum/week-11-concurrency-models-compared/challenges/challenge-01-free-threaded-audit.md) |
| The learner finishes holding a package published to TestPyPI and a benchmark report written to be reproduced — hardware, seed, warm-up, median and interval all stated — not a grade only a registrar can see | both | [`curriculum/week-12-capstone-perf-tuned-python-project/lecture-notes/03-the-benchmark-report-as-deliverable.md`](curriculum/week-12-capstone-perf-tuned-python-project/lecture-notes/03-the-benchmark-report-as-deliverable.md) |

**Gaps we declare.** One against the outcome set: static typing and compile-time enforcement, as recorded in the ledger — C17 uses type hints and type checkers as tooling but never teaches a compiled type system, and a course that grades generics in Java or C++ is not covered here. Three against our own surpass rule, stated so nobody discovers them later: worked solutions are published for the Weeks 7 to 12 exercises only, and Weeks 1 to 6 carry an exercise index with no separate answer document; the homework problems have no published answers in any week; and C17 ships no collapsible `Under the hood` blocks, because at this level the internals are the lesson rather than an aside — they are the body text of every lecture note.

---

## Prerequisites

You should be able to do **everything** in C1 weeks 1–15, plus at least one of:

- C5 (Data Science) — all units, plus comfort with NumPy and pandas.
- C16 (Web Backend) — at least through Week 8 (async).

If you're self-taught and don't know whether you qualify: take the [diagnostic quiz](curriculum/diagnostic-quiz.md). If you score 18+/25 you're ready. Below 14, do more C1/C5/C16 first.

---

## What this course is NOT

- **Not a tutorial.** Every week assumes you can self-direct. We point you at primary sources (PEPs, CPython source, official docs) and assume you'll read them.
- **Not academic.** This is engineer-grade, not researcher-grade. We don't prove things; we measure them.
- **Not Python 2.** Python 3.11 minimum. Many lessons require 3.12 or 3.13 features.
- **Not a framework course.** We touch Django, FastAPI, PyTorch, NumPy but always as context for a language/runtime point — not to teach the framework.

---

## Weekly breakdown

| Phase | Weeks | Outcome |
|-------|-------|---------|
| **Phase 1 — The Python Runtime** | 01 – 03 | Read CPython source, understand bytecode, the GIL, memory |
| **Phase 2 — Concurrency** | 04 – 06 | asyncio, threads, processes, the right tool for each |
| **Phase 3 — Performance & Native Code** | 07 – 09 | Profiling, vectorization, Cython, ctypes, free-threaded Python |
| **Phase 4 — Frontier Topics** | 10 – 12 | Advanced typing, PyTorch, Python security, capstone |

See [`curriculum/SYLLABUS.md`](curriculum/SYLLABUS.md) for the full week-by-week plan.

---

## How to start

1. Take the [diagnostic quiz](curriculum/diagnostic-quiz.md). If you pass, proceed.
2. Open [`curriculum/SYLLABUS.md`](curriculum/SYLLABUS.md). Read it in full.
3. Go to [`curriculum/week-01-cpython-internals-and-the-mental-model/`](curriculum/week-01-cpython-internals-and-the-mental-model/).
4. Follow the standard Code Crunch order: README → resources → lectures in order → exercises → challenges → quiz → homework → mini-project. The order is intentional; don't skip ahead.

---

## What you ship

The capstone is your **first non-trivial open-source contribution**. By Week 11 you'll have selected an OSS Python project you actually use (yours or someone else's) and identified a real issue to fix. Week 12 you submit the PR. The grade is the merged PR, not just attendance.

If you've never contributed to OSS before: this course exists in part to remove that mystery. We walk through the etiquette, the workflow, and the failure modes so the first PR isn't the hardest.

---

## Tools we use

| Tool | Role |
|------|------|
| **CPython 3.13+** | The reference implementation, the source we read |
| **dis** | Built-in bytecode disassembler |
| **cProfile / py-spy / scalene / austin** | Profilers (sampling and deterministic) |
| **asyncio** | The async standard library |
| **trio / anyio** | Structured concurrency — we touch trio for its better mental model |
| **Cython** | C-level Python extensions |
| **cffi** | C foreign function interface |
| **ctypes** | Stdlib equivalent (we compare/contrast) |
| **mypy / pyright** | Type checkers |
| **PyTorch** | Deep learning |
| **bandit / semgrep / pip-audit** | Python security scanners |
| **gh** | GitHub CLI for OSS contribution workflow |

Everything is open-source. No paid IDEs, no commercial linters.

---

## License

GPL-3.0. See [LICENSE](LICENSE).

---

## Next track

There isn't one. After C17, you continue your learning by:

- **Contributing to OSS Python projects** monthly.
- **Reading PEPs as they land** — <https://peps.python.org/>
- **Following the python-dev mailing list / Discourse**:  <https://discuss.python.org/>
- **Specializing further** in your domain — distributed systems, compilers, ML systems, security research, whatever drew you to C17 in the first place.

We can't teach you what's not yet known. But by the end of C17, you'll be one of the people who *figure out* what's not yet known.

---

*C17 is part of the Code Crunch open-source curriculum.* [Master catalog ↗](../MASTER-CURRICULUM.md)
