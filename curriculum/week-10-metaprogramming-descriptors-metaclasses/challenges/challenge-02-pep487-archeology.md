# Challenge 2 — PEP 487 archaeology: find a library that migrated from metaclass to `__init_subclass__`

**Estimated time:** 3–4 hours
**Difficulty:** moderate (the work is reading code, not writing it)
**Prerequisites:** Lectures 1 and 3 (PEP 487 motivation and metaclass mechanics)

## Why this challenge exists

PEP 487 landed in Python 3.6 in late 2016. Several major libraries that had used metaclasses for subclass-customisation switched to `__init_subclass__` in the following two years. The migration diffs are public on GitHub. Reading one such diff in your own words is the most efficient way to internalise *what the PEP actually changed in practice* — not just what the PEP text says.

This is a code-reading challenge, not a code-writing challenge. The deliverable is a memo.

## The task

Pick one of the following libraries (or any other major library that did the same migration; document the alternative if you pick one not on the list):

- **`pluggy`** — pytest's plugin manager. Migrated parts of its hook-registration mechanism after PEP 487. <https://github.com/pytest-dev/pluggy>.
- **`marshmallow`** — schema serialisation. Used a `SchemaMeta` metaclass in v2; v3 reduced its scope. <https://github.com/marshmallow-code/marshmallow>.
- **`attrs`** — class-creation tooling. Documents its design choices against metaclasses explicitly. <https://github.com/python-attrs/attrs>. (For `attrs`, the relevant migration is from `@attr.s` (which was always a decorator) to `@attr.define`'s richer machinery — read the changelog.)
- **`sqlalchemy`** — v2.0 (released 2023) introduced `DeclarativeBase` and `Mapped[]` typing that lean on PEP 487-style machinery; v1.x used `DeclarativeMeta`. <https://github.com/sqlalchemy/sqlalchemy>.
- **`zope.interface`** — older, pre-PEP 487 metaclass-heavy. Some replaced patterns. <https://github.com/zopefoundation/zope.interface>.
- **`django`** — `django.db.models.base.ModelBase`. Django did *not* migrate. Document why (this is an inverse case study and a valid choice for this challenge — see below).

## What the memo should contain

A ~1,200-word memo, structured as follows:

### Section 1: The library and what it does (~150 words)

One-paragraph summary of what the library is for and how a user uses it. Pretend the reader has not heard of it.

### Section 2: The pre-migration design (~300 words)

What did the metaclass do? Quote the metaclass `__new__` (or `__init__`, or `__prepare__`) in its 2015–2017 form, with citation to a specific commit on GitHub. Explain in your own words what it accomplished.

### Section 3: The post-migration design (~300 words)

What does the same code look like today (or in the post-migration version)? Cite the commit or PR that did the migration. Show the equivalent `__init_subclass__` or class-decorator code.

### Section 4: What changed in practice (~300 words)

Answer these specific questions:

- Did the library shed the metaclass entirely, or did it retain a metaclass for *some* reasons while moving *other* logic to `__init_subclass__`?
- Did the migration break the public API? (Almost certainly yes in some way — what was the deprecation path?)
- Did the migration improve type-checker cooperation? (Often yes — quote the maintainer's commit message if possible.)
- Did the migration introduce any bugs that subsequent commits fixed?

### Section 5: The lesson (~150 words)

In one paragraph: what does this migration teach you about *when* to use a metaclass and *when* to use `__init_subclass__`? Specifically, what kind of work was the metaclass doing that `__init_subclass__` could replace, and what kind of work (if any) had to stay in a metaclass?

## Tools

- **`git log`** on the cloned library — search for "PEP 487", "init_subclass", "init subclass", "metaclass" in commit messages and CHANGELOG.
- **GitHub blame view** — for any line in the current source, see the commit that introduced it.
- **`gh search prs`** — search the library's pull request history.

## The Django inverse case study (alternative)

If you pick Django, the memo's shape is different. Django did *not* migrate `ModelBase` to `__init_subclass__`. The reasons are documented in mailing-list discussions (`django-developers`) and in core-team commit messages. The memo should answer:

- Why did Django keep its metaclass?
- What features does `ModelBase` provide that `__init_subclass__` cannot? (Hint: `Meta` inner-class processing; `_meta` attribute synthesis; the migration cost itself.)
- Is the decision likely to change in the future? Why or why not?

This is a legitimate and interesting alternative because **the absence of a migration is also data**. Not every library should migrate just because PEP 487 exists.

## Grading rubric

| Criterion | Points |
|-----------|-------:|
| Library chosen and justified | 10 |
| Pre-migration code quoted with commit citation | 20 |
| Post-migration code quoted with PR citation | 20 |
| Answers to all four questions in Section 4 | 30 |
| The lesson section is specific (not generic) | 20 |
| **Total** | **100** |

## Reference reading

- **PEP 487 rationale** — <https://peps.python.org/pep-0487/#rationale>. Read this first; the migrations you read about will mirror the motivation here.
- **PEP 557 rationale** — <https://peps.python.org/pep-0557/#rationale>. Why `dataclass` was a decorator. Adjacent motivation.
- **"Modern Python: Start using attrs"** — Hynek Schlawack on the design tradeoffs of `attrs`. <https://hynek.me/articles/attrs/>.
- **"SQLAlchemy 2.0 — Mappings and Mapped Classes"** — <https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html>. The v2 migration story for declarative models.

## Deliverable

A single Markdown file `pep487-archeology.md` of approximately 1,200 words. No code beyond the quoted snippets (which should be small, with line-range citations).
