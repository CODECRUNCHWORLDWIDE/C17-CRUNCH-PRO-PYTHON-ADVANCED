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


---

<!-- CCWW:AUTO-INDEX:START — generated by scripts/restructure_course_repos.py; edit ABOVE this marker -->

## Course at a glance

| Section | Count |
| --- | --- |
| Curriculum entries | 14 |
| Projects | 0 |
| Past sessions | 0 |

## Curriculum

- [SYLLABUS](curriculum/SYLLABUS.md)
- [diagnostic quiz](curriculum/diagnostic-quiz.md)
- [week 01 cpython internals and the mental model](curriculum/week-01-cpython-internals-and-the-mental-model/README.md)
- [week 02 refcounting gc memory](curriculum/week-02-refcounting-gc-memory/README.md)
- [week 03 bytecode stack machine gil](curriculum/week-03-bytecode-stack-machine-gil/README.md)
- [week 04 asyncio first principles](curriculum/week-04-asyncio-first-principles/README.md)
- [week 05 structured concurrency](curriculum/week-05-structured-concurrency/README.md)
- [week 06 threads processes](curriculum/week-06-threads-processes/README.md)
- [week 07 profiling like its your job](curriculum/week-07-profiling-like-its-your-job/README.md)
- [week 08 c extensions ctypes cffi cython](curriculum/week-08-c-extensions-ctypes-cffi-cython/README.md)
- [week 09 packaging and distribution](curriculum/week-09-packaging-and-distribution/README.md)
- [week 10 metaprogramming descriptors metaclasses](curriculum/week-10-metaprogramming-descriptors-metaclasses/README.md)
- [week 11 concurrency models compared](curriculum/week-11-concurrency-models-compared/README.md)
- [week 12 capstone perf tuned python project](curriculum/week-12-capstone-perf-tuned-python-project/README.md)

## In this course

- **Community** — [community/](community/)
- **Curriculum** — [curriculum/](curriculum/)
- **Projects** — [projects/](projects/)
- **Resources** — [resources/](resources/)
- **Past sessions** — [past-sessions/](past-sessions/)

<!-- CCWW:AUTO-INDEX:END -->
