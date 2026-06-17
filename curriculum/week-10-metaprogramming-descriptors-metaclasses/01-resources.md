# Week 10 — Resources

All free. All authoritative. The four most important entries are PEP 487, the Descriptor HowTo, the data-model reference, and Hettinger's "Class Development Toolkit" talk. Read those first; the rest is supporting cast.

## Primary sources (read first)

### The PEPs

- **PEP 487 — Simpler customisation of class creation** (Martin Teichmann, accepted 2016, merged Python 3.6). The PEP that retired most metaclass use cases. Defines `__init_subclass__` and `__set_name__`. <https://peps.python.org/pep-0487/>. Read end-to-end once; about 4,000 words. The rationale section alone is worth the time.
- **PEP 3115 — Metaclasses in Python 3000** (Talin, accepted 2007, merged Python 3.0). The keyword-argument metaclass syntax (`class Foo(Base, metaclass=Meta):`). <https://peps.python.org/pep-3115/>. About 2,000 words.
- **PEP 560 — Core support for typing module and generic types** (Ivan Levkivskyi, accepted 2017, merged Python 3.7). `__class_getitem__` and `__mro_entries__`. The reason `List[int]` works without a metaclass. <https://peps.python.org/pep-0560/>. About 3,000 words.
- **PEP 681 — Data class transforms** (Erik De Bonte, Eric Traut, accepted 2022, available Python 3.11). `typing.dataclass_transform`. The way you tell mypy and pyright that your class decorator behaves like `@dataclass`. <https://peps.python.org/pep-0681/>. About 4,500 words. The relevant reading once you start caring about type-checker cooperation.
- **PEP 252 — Making types look more like classes** (Guido van Rossum, 2001). The PEP that introduced descriptors. Mostly of historical interest, but it spells out the design rationale. <https://peps.python.org/pep-0252/>.

### The data model reference

- **The Python language reference, chapter 3 — Data model** — <https://docs.python.org/3/reference/datamodel.html>. The official source.
  - **3.3.2 — Customising attribute access** — `__getattr__`, `__getattribute__`, `__setattr__`, `__delattr__`.
  - **3.3.2.4 — Implementing descriptors** — the descriptor protocol in five paragraphs. <https://docs.python.org/3/reference/datamodel.html#implementing-descriptors>.
  - **3.3.2.5 — Invoking descriptors** — the precedence rules (data descriptor > instance dict > non-data descriptor).
  - **3.3.3 — Customising class creation** — `__init_subclass__`, `__set_name__`, metaclasses, `__prepare__`. <https://docs.python.org/3/reference/datamodel.html#customizing-class-creation>.
- Re-read these sections after the lecture, not before. They are dense; they make sense once you have written the code.

### The Descriptor HowTo Guide

- **"Descriptor HowTo Guide"** by Raymond Hettinger. <https://docs.python.org/3/howto/descriptor.html>. About 9,000 words, with code. The canonical reference. Read twice: once before the descriptor lecture, once after. The HowTo includes Python-equivalent implementations of `property`, `classmethod`, `staticmethod`, `__slots__`, and `functools.cached_property` — these are gold for the exercises.

## Reference implementations (read after you have written your own)

- **`Lib/dataclasses.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/dataclasses.py>. About 1,400 lines. The reference implementation of "a class decorator that does something non-trivial." Focus on `_process_class` (~200 lines) and `_create_fn` (~30 lines). After reading the HowTo's `property` equivalent, this is the next-deepest stdlib example.
- **`Lib/types.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/types.py>. Has the `DynamicClassAttribute` descriptor and the `MappingProxyType`. Read for the `__set_name__` examples.
- **`Lib/functools.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/functools.py>. Search for `cached_property`. About 50 lines, descriptor-implemented. Re-implement it from scratch as Exercise 3.
- **`Lib/abc.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/abc.py>. The `ABCMeta` metaclass; the canonical legitimate metaclass use case. About 200 lines of Python (with a C accelerator).
- **`Lib/enum.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/enum.py>. The other canonical legitimate metaclass use case. `EnumType` (formerly `EnumMeta`) plus `_EnumDict` (a custom namespace returned by `__prepare__`). About 2,000 lines; the most production-grade metaclass in the stdlib.
- **`Lib/typing.py` in CPython** — <https://github.com/python/cpython/blob/main/Lib/typing.py>. The `Generic` machinery; PEP 560 in practice. Search for `__class_getitem__`.

## Third-party libraries (production-grade examples)

- **`attrs`** — <https://www.attrs.org/>. The mature, production-grade alternative to `dataclasses`. `@attrs.define` is a class decorator. Source: <https://github.com/python-attrs/attrs/tree/main/src/attr>. Compare its design to `dataclasses`. Documentation: <https://www.attrs.org/en/stable/>.
- **`pydantic` v2** — <https://docs.pydantic.dev/>. Uses a metaclass (`ModelMetaclass`) plus `dataclass_transform` for type-checker support. Source: <https://github.com/pydantic/pydantic/blob/main/pydantic/_internal/_model_construction.py>. The reference for "production-grade metaclass that cooperates with type checkers."
- **`sqlalchemy`** — <https://www.sqlalchemy.org/>. Used a metaclass throughout v1.x; v2.0 introduced declarative-base class decorators in 2023. Source: <https://github.com/sqlalchemy/sqlalchemy/tree/main/lib/sqlalchemy/orm>. The reference for "library that survived the transition from metaclass to PEP 487-style." Documentation: <https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html>.
- **`django.db.models`** — <https://github.com/django/django/blob/main/django/db/models/base.py>. Django still uses a metaclass (`ModelBase`); the reference for "we have considered the alternatives and our migration cost is too high." Worth reading for the inverse argument.

## Free talks (watch one)

- **Raymond Hettinger — "Class Development Toolkit"** (PyCon 2013) — <https://www.youtube.com/watch?v=HTLu2DFOdTg>. About 60 minutes. The canonical Hettinger talk on properties, descriptors, and `super()`. The reference talk for the descriptor protocol. Free on YouTube. Highest-priority watch.
- **Raymond Hettinger — "Modern Python Dictionaries"** (PyCon 2017) — <https://www.youtube.com/watch?v=npw4s1QTmPg>. About 50 minutes. The `__dict__` internals that descriptors live on top of. Free.
- **David Beazley — "Python 3 Metaprogramming"** (PyCon 2013) — <https://www.youtube.com/watch?v=sPiWg5jSoZI>. About three hours; the deepest free metaprogramming talk on the internet. Skim with a notebook. Free.
- **James Powell — "So you want to be a Python expert?"** (PyData Seattle 2017) — <https://www.youtube.com/watch?v=cKPlPJyQrt4>. About two hours; covers descriptors, decorators, metaclasses, and the data model. Free.
- **Brett Cannon — "How Python Was Shaped By Leaky Abstractions"** (PyCon 2024) — <https://www.youtube.com/results?search_query=brett+cannon+leaky+abstractions+pycon>. About 30 minutes. Why the language is the way it is. Free.

## Books (if you have one already; nothing to buy)

- **"Fluent Python"** by Luciano Ramalho, 2nd edition, O'Reilly 2022. Chapters 23 ("Attribute Descriptors") and 24 ("Class Metaprogramming") are the textbook-quality reference. If your university or local library has access; do not buy unless you want to keep it.
- **"Python Cookbook"** by David Beazley and Brian K. Jones, 3rd edition, O'Reilly 2013. Chapter 9 ("Metaprogramming"). Older, but still correct.

## Blogs and articles

- **"A Guide to Python's Magic Methods"** by Rafe Kettler (2012, periodically updated) — <https://rszalski.github.io/magicmethods/>. Free, comprehensive, covers `__init_subclass__` and the descriptor protocol. Cross-reference for the HowTo.
- **"Python's Metaclasses"** by Eli Bendersky (2017) — <https://eli.thegreenplace.net/2011/08/14/python-metaclasses-by-example>. The most-linked beginner explanation; somewhat dated on PEP 487, otherwise correct.
- **"Decoupling decorators from classes"** by Hynek Schlawack (2017) — <https://hynek.me/articles/decorators/>. The author of `attrs` on why class decorators beat the metaclass approach he started with.
- **"What's the difference between `@staticmethod` and `@classmethod`?"** — Stack Overflow's top answer (Mike Driscoll, 2011) is correct and concise. Verify against the HowTo's implementations. <https://stackoverflow.com/questions/136097/>.

## Tooling

- **`mypy`** — <https://mypy-lang.org/>. Install: `pip install mypy`. The static type checker that recognises `@dataclass`, `__init_subclass__`, and (via PEP 681) any `dataclass_transform`-decorated class decorator.
- **`pyright`** — <https://github.com/microsoft/pyright>. Install: `pip install pyright`. Microsoft's faster, stricter alternative; also handles `dataclass_transform`. Used by VS Code via Pylance.
- **`pdbpp`** — <https://pypi.org/project/pdbpp/`. Drop-in replacement for `pdb`; the right interactive tool when descriptors do not behave as expected. Free.
- **`tracemalloc`** — stdlib, <https://docs.python.org/3/library/tracemalloc.html>. The benchmark in this week's mini-project measures per-instance memory via `tracemalloc`. No install.
- **`timeit`** — stdlib, <https://docs.python.org/3/library/timeit.html>. The benchmark also measures class-creation and instance-creation time via `timeit`. No install.
- **`dis`** — stdlib, <https://docs.python.org/3/library/dis.html>. The disassembler. Useful for verifying that the four implementations compile to comparable bytecode for attribute access. No install.
- **`inspect`** — stdlib, <https://docs.python.org/3/library/inspect.html>. `inspect.signature`, `inspect.getmembers`. The descriptor protocol shows up here.

## Diagnosis cookbook (when something goes wrong)

| Symptom | Likely cause | Reference |
|---------|--------------|-----------|
| Descriptor's `_name` is wrong | Forgot `__set_name__`; named manually | HowTo §"Pure Python Equivalent" |
| Class decorator broke `isinstance` | Returned a new class instead of mutating | `dataclasses._process_class` |
| `TypeError: metaclass conflict` | Two parent classes have unrelated metaclasses | Data model §3.3.3.2 |
| `__init_subclass__` not called | Forgot to pass `**kwargs` through `super()` | PEP 487 §"Subclass init" |
| `@property` works but type checker complains | Property is a data descriptor; mypy needs explicit typing | mypy docs §"Properties" |
| `cached_property` clobbered by `__slots__` | `cached_property` writes to instance `__dict__`; `__slots__` removes it | HowTo §"Cached property" |
| Metaclass `__call__` runs but `__init__` does not | `__call__` did not invoke `__init__` | PEP 3115 |
| `__set_name__` called twice | Class assignment, then setattr; happens with `dataclasses.field` | Data model §3.3.3.6 |
| `__init_subclass__` runs on the base class | It does not, unless the base subclasses something that defines it | PEP 487 rationale |
| Pyright says "unknown member" on dynamic attribute | Type checkers do not run your metaclass | PEP 681 |

## Standards-citation cheat sheet (for the quiz)

| Construct | PEP | Year | Author |
|-----------|----:|-----:|--------|
| `__metaclass__` keyword syntax (class statement) | 3115 | 2007 | Talin |
| `__init_subclass__`, `__set_name__` | 487 | 2016 | Martin Teichmann |
| `__class_getitem__`, `__mro_entries__` | 560 | 2017 | Ivan Levkivskyi |
| `typing.dataclass_transform` | 681 | 2022 | Erik De Bonte, Eric Traut |
| `dataclasses.dataclass` | 557 | 2017 | Eric V. Smith |

## Anti-resources (do not learn from these)

- **Any Python-2 metaclass tutorial.** The `__metaclass__ = ...` class-body attribute does not exist in Python 3. PEP 3115 retired it. If a tutorial uses that syntax, close the tab.
- **Stack Overflow answers from 2010–2014 on `__metaclass__`.** Most predate PEP 487. They give correct Python-2 advice that is wrong in 2026.
- **"Why metaclasses are the most powerful feature in Python."** The framing is right but the conclusion is wrong; in 2026 the most powerful feature you can wield is *the discipline not to reach for metaclasses*. PEP 487 made this true.

## Where to ask questions

- **`#python` on Libera.Chat IRC** — historical, still active.
- **The Python Discord** — <https://pythondiscord.com/>. Active, helpful, moderated.
- **`r/learnpython`** — for "I have a class decorator and it does X, why?"
- **`r/python`** — for "I have an opinion about descriptors."
- **The Python forum** — <https://discuss.python.org/>. Where the PEP authors hang out. Read more than you post.
