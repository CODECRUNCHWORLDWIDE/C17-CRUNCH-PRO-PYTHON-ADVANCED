# Week 10 Mini-Project — The validated-model library, four ways

> *The deliverable for this week is one library specified four times, plus a benchmark, plus a one-page decision tree you would hand a junior teammate. The library is small enough (~80–120 lines per implementation) that the engineering content is not "I built a thing" — it is "I picked one of four ways to build the thing and I can defend my pick." The decision tree is the artefact. The benchmark is the evidence. The four implementations are the proof that you walked the ladder.*

## What you ship

A folder called `validated_models/` containing:

```text
validated_models/
├── README.md             # 700 words; what you built, what you found, which you recommend
├── decorator_impl.py     # version 1 — class decorator                  (~100 lines)
├── init_subclass_impl.py # version 2 — __init_subclass__ + __set_name__ (~110 lines)
├── descriptor_impl.py    # version 3 — full descriptor protocol         (~130 lines)
├── metaclass_impl.py     # version 4 — metaclass                        (~120 lines)
├── benchmark.py          # timeit/tracemalloc comparison                (~200 lines)
├── benchmark-results.md  # the numbers; one chart or one table          (~150 words)
├── decision-tree.md      # your own version; one page                   (~400 words)
└── test_all.py           # the same test suite passes against all four  (~150 lines)
```

Compile-check every Python file before submitting:

```bash
python3 -m py_compile validated_models/*.py
```

Run the test suite against all four implementations:

```bash
python3 -m pytest validated_models/test_all.py -v
# or, without pytest:
python3 validated_models/test_all.py
```

All four implementations must pass the same test cases.

## The library specification

Each implementation provides:

- A way to declare a "model" class (either via decorator, base class, or metaclass).
- Two field types — `StringField(max_length: int)` and `IntField(min_value: int, max_value: int)`. Both validate on assignment.
- A keyword-only `__init__` that requires every declared field, type-checks each value, and runs the field-specific validator.
- A `__repr__` that prints the field values.
- A `to_dict() -> dict[str, Any]` method that returns a plain dict.
- A `_fields` class attribute (a tuple of field names) for introspection.

The four implementations differ in *how* they achieve this. The behaviour should be indistinguishable from the caller's perspective when the model is well-formed; the differences show up in (a) cooperation with inheritance, (b) cooperation with type checkers, (c) cost.

## The test suite

`test_all.py` runs the *same* nine tests against each of the four implementations. The test cases:

1. **Happy path:** `User(name="alice", age=30)` succeeds; `u.name == "alice"`, `u.age == 30`.
2. **Missing field:** `User(name="alice")` raises `TypeError`.
3. **Type error:** `User(name=123, age=30)` raises `TypeError`.
4. **Out-of-range:** `User(name="alice", age=-1)` raises `ValueError`.
5. **String too long:** `User(name="x" * 1000, age=30)` raises `ValueError`.
6. **Repr:** `repr(User(name="alice", age=30)) == "User(name='alice', age=30)"`.
7. **to_dict:** `User(name="alice", age=30).to_dict() == {"name": "alice", "age": 30}`.
8. **Inheritance:** an `Admin(User)` subclass with an added `role: StringField(max_length=20)` field validates `role` the same way `User` validates `name`. **Implementations that cannot do this gracefully should be marked in their docstrings.**
9. **Introspection:** `User._fields == ("name", "age")` (or a deterministic ordering).

The fact that test 8 is harder for some implementations than for others is the lesson. Document the difficulty in each implementation's docstring.

## The benchmark

`benchmark.py` measures four quantities for each implementation:

1. **Class-definition time** — `timeit.timeit("class C(...): ...")` over 1,000 iterations.
2. **Instance-creation time** — `timeit.timeit("C(name='x', age=30)")` over 100,000 iterations.
3. **Attribute-set time** — `timeit.timeit("instance.age = 50", setup=...)` over 1,000,000 iterations.
4. **Memory per instance** — `tracemalloc.take_snapshot()` before and after creating 10,000 instances.

Print a table:

```text
                    Decorator   InitSubclass   Descriptor   Metaclass
class creation (μs)     0.X         0.X            0.X         0.X
instance create (μs)    0.X         0.X            0.X         0.X
attribute set (μs)      0.X         0.X            0.X         0.X
bytes per instance      0.X         0.X            0.X         0.X
```

Then write `benchmark-results.md` with the actual numbers from your machine, your interpretation, and the answer to: **"do the differences matter at scale, or are they noise?"** (Hint: for most applications they are noise. The interesting question is *which* applications, exactly, are not most applications.)

## The decision tree

`decision-tree.md` is the deliverable that ties everything together. It is a *short* document — about 400 words and one ASCII flowchart. The flowchart looks something like:

```text
                          Start: I want a class with declarative fields.
                                            │
                       ┌────────────────────┴───────────────────┐
                  Consumer marks                          Base class with
                  the class?                              many subclasses?
                       │                                          │
                      Yes                                        Yes
                       │                                          │
                Class decorator                          __init_subclass__
                       │                                          │
                       │                                          │
              Need fields with                         Need fields with
              their own behaviour                      their own behaviour
              (validation, caching,                    (validation, caching,
              ORM columns)?                            ORM columns)?
                       │                                          │
                      Yes                                        Yes
                       │                                          │
                       └─────────────────┬───────────────────────┘
                                         │
                                    Descriptors
                                         │
                                         │
                            Need __prepare__,
                            __call__ interception,
                            or __instancecheck__?
                                         │
                                        Yes
                                         │
                                    Metaclass
                                         │
                                        else
                                         │
                                    Stay where you are
```

Plus prose: when do you actually reach for each? Reference the four implementations you built; cite specific lines where the difference matters.

There is a reference decision tree in this folder at `../decision-tree.md` (yes — there is one at the week level too; the one in the mini-project folder is *yours*, the one a level up is the reference for grading). **Do not read the reference until you have written yours.**

## The 700-word memo (in the mini-project README)

The portfolio artefact. Cover:

- What you built.
- The most surprising thing you learned (in two sentences).
- Which implementation you would reach for first, and why.
- One example from your own (or a hypothetical) codebase where you would pick a *different* implementation.
- One thing about Python's data model that you understand now that you did not understand a week ago.

About 700 words. No bullet-list filler.

## Grading rubric

| Criterion | Points |
|-----------|-------:|
| All four implementations exist, compile-clean, and pass the test suite | 25 |
| Test 8 (inheritance) explicitly tested for all four; difficulty documented in docstrings | 15 |
| Benchmark runs cleanly and produces a table | 10 |
| `benchmark-results.md` interprets the numbers, not just reports them | 10 |
| Decision tree is your own (clear from the writing); not a paraphrase of the reference | 15 |
| The 700-word memo is specific (not generic; references your own code) | 15 |
| Code quality: type hints on every function; docstrings on every public function | 10 |
| **Total** | **100** |

## Reference reading before you start

- **Lecture 1** of this week — for the class decorator and `__init_subclass__` mechanics.
- **Lecture 2** — for the descriptor protocol.
- **Lecture 3** — for the metaclass story and the conditions under which one is justified.
- **Exercise 3** — your starting point for the descriptor implementation (you already wrote `Property`).
- **Exercise 4** — your starting point for the metaclass implementation.

The exercise versions are *teaching* implementations. The mini-project's versions should be *production-quality* — error messages clear, validation thorough, introspection complete.

## A note on what "production-quality" means here

You are not shipping this library on PyPI. "Production-quality" here means:

- Every error message is actionable. `TypeError("name: expected str, got int")` is actionable. `TypeError("type mismatch")` is not.
- Every public function has a type-hinted signature.
- Every public function has a one-line docstring.
- The code reads top-to-bottom; no function is defined after its first call site.
- The code does not catch and silently swallow exceptions.

These are the four traits that distinguish a teaching example from a library you would let someone else maintain.

## Common pitfalls

**Pitfall 1: the decorator version returns a subclass.** Then `isinstance` breaks for any reference captured before decoration. The reference returns the same class object.

**Pitfall 2: the `__init_subclass__` version stores fields on the *base* class.** Then every subclass shares fields. Store on `cls`, not on `Model`.

**Pitfall 3: the descriptor version stores values on the descriptor.** Then every instance shares state. Store in `instance.__dict__[self._name]`.

**Pitfall 4: the metaclass version's `__new__` does not call `super().__new__`.** Then no class object is actually created. The `class C(Model): ...` statement silently produces `None`.

**Pitfall 5: forgetting `super().__init_subclass__(**kwargs)`.** Silent bug; only manifests when someone tries to mix your `Model` with another `__init_subclass__`-using base.

Each of these is in your test suite if you wrote the suite right. If your test suite catches them, you have the right test suite.

## When you are done

Run the benchmark, look at the numbers, and ask yourself: **for the *kind* of code I actually write, do these differences matter?** The honest answer for most engineers is "no." That is the discipline this week was trying to instil.

Then re-read the reference decision tree (`../decision-tree.md`) and compare to your own. Where they differ, ask why. The answer is sometimes "the reference is right and I was wrong"; the answer is sometimes "I had a context the reference does not." Both are learning.
