# Week 10 — Homework

Six problems. Roughly seven hours total. Each problem has a specific deliverable (code, memo, or both). Number every file with the problem number; submit as a folder.

Compile-check every Python file before submitting:

```bash
python3 -m py_compile *.py
```

A file that does not compile is graded as zero for that problem.

---

## Problem 1 — `@frozen_model` (~1h)

Write a class decorator `@frozen_model` that turns annotated attributes into read-only after `__init__` returns. After construction, any attempt to set an attribute should raise `AttributeError("frozen instance")`.

```python
@frozen_model
class Point:
    x: int
    y: int

p = Point(x=3, y=4)
p.x  # 3
p.y = 5  # AttributeError: frozen instance
```

Use a flag (`object.__setattr__(self, "_frozen", True)` at end of `__init__`) and override `__setattr__` to consult the flag. Type hints on every function. Compare to `dataclasses.dataclass(frozen=True)`: how does its implementation differ? Write one paragraph in a header comment.

**Deliverable:** `problem-01-frozen-model.py` (~80 lines).

---

## Problem 2 — Plugin registry with `__init_subclass__` (~1h)

Build a `Codec` base class. Subclasses self-register under a string `format=` keyword. Provide a class method `Codec.get(name: str) -> type[Codec]` that returns the registered codec for that name, raising `LookupError` if unregistered.

```python
class Codec:
    @classmethod
    def get(cls, name: str) -> type[Codec]: ...
    def encode(self, data: str) -> bytes: ...
    def decode(self, raw: bytes) -> str: ...

class Base64Codec(Codec, format="base64"):
    def encode(self, data: str) -> bytes: ...
    def decode(self, raw: bytes) -> str: ...

class HexCodec(Codec, format="hex"):
    def encode(self, data: str) -> bytes: ...
    def decode(self, raw: bytes) -> str: ...

assert Codec.get("base64") is Base64Codec
```

Implement two real codecs (base64 and hex; use the stdlib `base64` module). Test that registering twice under the same name raises. Test that `Codec.get("nonsense")` raises `LookupError`.

**Deliverable:** `problem-02-codec-registry.py` (~100 lines).

---

## Problem 3 — Descriptor: `BoundedInt` (~1.5h)

Write a data descriptor `BoundedInt(min_value: int, max_value: int)`. It validates on `__set__`, stores in `instance.__dict__[self._name]`, and uses `__set_name__` to learn its attribute name.

Then write a `Sensor` class that uses three `BoundedInt` descriptors (`temperature: -100..200`, `humidity: 0..100`, `pressure: 0..2000`) and demonstrate:

- assignment of valid values works
- assignment of out-of-range values raises `ValueError`
- assignment of non-`int` values raises `TypeError`
- `inspect.getmembers(Sensor, predicate=lambda x: isinstance(x, BoundedInt))` returns all three descriptors with their names
- two `Sensor` instances do not share state (this is the test that catches the most common descriptor bug)

**Deliverable:** `problem-03-bounded-int.py` (~120 lines).

---

## Problem 4 — `OrderedClassMembers` metaclass (~1h)

In Python 3.7+, ordinary `dict` preserves insertion order, so this is *almost* a no-op — but the exercise is to write the metaclass and feel the difference between "this would have been hard before 3.7" and "this is now trivial."

Write a metaclass `OrderedClassMembers` that:

- Uses `__prepare__` to return a plain `dict` (which already preserves order in 3.7+).
- In `__new__`, attaches `cls._declaration_order: tuple[str, ...]` to the class — the names of every attribute defined in the class body, in declaration order.

Demonstrate on a 5-field class. Print `MyClass._declaration_order`.

Add a short comment block (~10 lines) explaining what would have been needed *before* Python 3.7 (`collections.OrderedDict`) and why this metaclass is mostly historical now.

**Deliverable:** `problem-04-ordered-members.py` (~70 lines).

---

## Problem 5 — `ValidatedModel` four ways: a comparison table (~1.5h)

You will build all four versions of the validated-model library in the mini-project. This homework problem is a *scaffold* for that mini-project.

Build four small versions of `ValidatedModel` — one per mechanism — each with the same minimal feature set:

- A `Model` (or `@validated_model`) construct
- Two field types: `name: str` (max 50 chars) and `age: int` (between 0 and 150)
- A `__repr__`

Each version should be 40–80 lines. Put each in its own file:

- `problem-05a-decorator.py`
- `problem-05b-init-subclass.py`
- `problem-05c-descriptor.py`
- `problem-05d-metaclass.py`

Then write `problem-05-comparison.md` (~400 words) that fills in this table:

| Mechanism | Lines of code | Cooperates with mypy out of the box? | Handles inheritance? | Metaclass-conflict risk? | Recommended for |
|-----------|--------------:|--------------------------------------|----------------------|--------------------------|-----------------|
| Class decorator | | | | | |
| `__init_subclass__` | | | | | |
| Descriptors | | | | | |
| Metaclass | | | | | |

**Deliverable:** four `.py` files plus the comparison markdown.

---

## Problem 6 — `dataclass_transform` annotation (~1h)

Take the `@validated_model` decorator from Problem 5a. Add `@typing.dataclass_transform()` to it (one decorator on the decorator). Then write a `test_typing.py` file with five `User(...)` call-sites — two correct, three with errors a type checker should catch:

```python
# correct
User(name="alice", age=30)
User(name="bob", age=40)

# type errors
User(name=123, age=30)        # name: expected str
User(age=30)                  # missing name
User(name="x", age=30, q=1)   # extra arg
```

Run mypy (`pip install mypy && mypy test_typing.py`) and pyright (`pip install pyright && pyright test_typing.py`). Compare:

- Which errors does mypy catch with `dataclass_transform`?
- Which does pyright catch?
- Which does neither catch?
- If you remove `@dataclass_transform`, what changes?

Write `problem-06-type-checker-cooperation.md` (~500 words) summarising findings. Cite PEP 681 specifically; quote the relevant rule from the spec.

**Deliverable:** `problem-06-validated.py` (the decorator with `dataclass_transform`), `problem-06-test_typing.py` (the five call-sites), and the markdown memo.

---

## Submission

Submit the following layout:

```text
hw10-yourname/
├── problem-01-frozen-model.py
├── problem-02-codec-registry.py
├── problem-03-bounded-int.py
├── problem-04-ordered-members.py
├── problem-05a-decorator.py
├── problem-05b-init-subclass.py
├── problem-05c-descriptor.py
├── problem-05d-metaclass.py
├── problem-05-comparison.md
├── problem-06-validated.py
├── problem-06-test_typing.py
├── problem-06-type-checker-cooperation.md
└── README.md          (~100 words; what you learned)
```

Compile-check passes (`python3 -m py_compile *.py`) and grade rubric below.

## Grading rubric

| Criterion | Points |
|-----------|-------:|
| Problem 1 — `@frozen_model` works; comparison to `dataclass(frozen=True)` | 15 |
| Problem 2 — registry pattern with two real codecs, double-registration test, lookup test | 15 |
| Problem 3 — `BoundedInt` correctly stores in `instance.__dict__`; the no-shared-state test passes | 15 |
| Problem 4 — `OrderedClassMembers` works; historical note included | 10 |
| Problem 5 — four implementations exist; comparison table fully filled in | 25 |
| Problem 6 — type-checker results documented for both mypy and pyright | 15 |
| **All `.py` files compile-clean** | **5** |
| **Total** | **100** |

## A note on type hints

Every function and method in every submitted `.py` file should have type hints on parameters and return type. This is consistent with the rest of C17. Code without type hints loses 1 point per missing annotation, capped at 10 points total.
