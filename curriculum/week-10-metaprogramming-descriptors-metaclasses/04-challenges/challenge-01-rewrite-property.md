# Challenge 1 — Rewrite `property`, `classmethod`, `staticmethod`, `cached_property` and compare against CPython

**Estimated time:** 4–5 hours
**Difficulty:** moderate
**Prerequisites:** Lecture 2 (descriptors); Exercise 3 (you have the skeletons in hand)

## Why this challenge exists

You have, in Exercise 3, a working implementation of each of the four canonical descriptors. The exercise stopped at "it appears to work." This challenge asks the next question: **does it actually match the built-in?** And — when it does not — why not?

The CPython implementations are in C. You cannot directly compare your Python source to theirs line-for-line. What you *can* do is run a comprehensive behavioural test suite — `inspect.getmembers`, MRO walking, pickling, `repr()`, `dir()`, type-checker output — and find the cases where your pure-Python version diverges. There are about half a dozen real divergences. Find them. Document them.

## The setup

Take your Exercise 3 solutions. Put each of `Property`, `ClassMethod`, `StaticMethod`, `CachedProperty` in a single module, `pure_descriptors.py`. Write a second module, `comparison.py`, that imports both your pure-Python versions and the stdlib versions:

```python
from pure_descriptors import Property, ClassMethod, StaticMethod, CachedProperty
from functools import cached_property as stdlib_cached
import builtins
stdlib_property = builtins.property
stdlib_classmethod = builtins.classmethod
stdlib_staticmethod = builtins.staticmethod
```

For each of the four pairs, write a *parallel test*:

```python
def test_property_pair() -> None:
    """Define one class with our Property and one with stdlib property.
    Verify identical behaviour across the test cases below."""
    ...
```

## The test matrix

For each pair, exercise:

1. **Basic get/set/delete** — define a class with a private `_x` and a `Property` over it; verify get, set, delete all work; verify exceptions on missing fget/fset/fdel.
2. **`inspect.getmembers(cls)`** — does the descriptor appear? Same way for both?
3. **`isinstance(cls.attr, property)`** — does your `Property` register as a `property`? (Hint: it does not. Why is this important for libraries that introspect.)
4. **`dir(instance)`** — does the attribute show up in `dir`?
5. **`repr(cls.attr)`** — what does the descriptor print? Stdlib prints `<property object at 0x...>`; what does yours print? Should it match?
6. **Pickling** — `pickle.dumps(instance)` of a class with the descriptor. Does it work? Stdlib `property` is not pickleable directly (the descriptor is, but the bound method retrieved through it is not); document the behaviour for yours.
7. **Subclassing the descriptor** — `class TypedProperty(Property): ...` overrides `__set__` to add type-checking. Does the `@x.setter` chaining still produce a `TypedProperty`? (Hint: it does, because `type(self)` was used in the chaining methods. Verify.)
8. **`@classmethod` and inheritance** — does your `ClassMethod` correctly pass `cls` as the *subclass* when called on a subclass? Verify with a two-level hierarchy.
9. **`staticmethod` callability before Python 3.10** — staticmethod became directly callable in Python 3.10. Verify yours is. (Stdlib's became callable in 3.10; before, only the descriptor protocol worked.)
10. **`cached_property` with `__slots__`** — verify both implementations fail the same way when `__slots__` excludes `__dict__`. Document the failure mode for each.

Write the tests as a single `pytest` file or as plain `assert`-based functions. Either works. The grading rubric below assumes 10 tests.

## The divergence list

You will find several divergences. Some are intentional (your version is a teaching tool, not production code). Some are bugs you should fix. Document each in a `divergences.md` file with this template:

```markdown
## Divergence N: [short title]

**Stdlib behaviour:** ...
**Your behaviour:** ...
**Is this a bug?:** Yes / No / Depends
**Why:** ...
**Fix (if applicable):** ...
```

Expected divergences (do not just copy these — *find them yourself*; this list is for grading):

- `isinstance(MyClass.attr, builtins.property)` returns `False` for your `Property`. This is intentional but worth noting.
- `repr(MyClass.attr)` differs. Probably not a bug; the stdlib repr is implementation-defined.
- Stdlib `cached_property` has a thread-safety lock that yours does not. Real bug under multithreading.
- Stdlib `property` has special handling for `__doc__` inheritance that yours may miss.
- Stdlib `staticmethod` and `classmethod` participate in the `__wrapped__` protocol; yours probably does not.

## Reference reading

Before you call this done, read the actual CPython source:

- **`Objects/descrobject.c`** — <https://github.com/python/cpython/blob/main/Objects/descrobject.c>. The C implementation of `property` and the descriptor machinery. About 1,200 lines.
- **`Objects/funcobject.c`** — <https://github.com/python/cpython/blob/main/Objects/funcobject.c>. Where `function.__get__` (the thing that turns a function into a bound method) is defined.
- **`Lib/functools.py`** — search for `class cached_property`. The Python version, with the threading lock.

Even at the C level, the shape of the code matches Hettinger's HowTo's Python equivalents. The divergences you find should be either (a) thread-safety, (b) wrapper-protocol cooperation, or (c) repr cosmetics. If you find one outside those three categories, you have probably found a real bug in your own code.

## Grading rubric

| Criterion | Points |
|-----------|-------:|
| All four pure-Python descriptors in a single module, type-hinted | 10 |
| Parallel test for each pair (10 test scenarios across 4 pairs) | 30 |
| `divergences.md` with at least 5 documented divergences | 20 |
| At least one divergence labelled as a *real* bug (not just cosmetic) and *fixed* in your `pure_descriptors.py` | 15 |
| Discussion of why `isinstance(MyClass.attr, builtins.property)` is `False` and what that costs you | 10 |
| Thread-safety analysis of your `CachedProperty` (compare to `functools.cached_property` lock) | 15 |
| **Total** | **100** |

## Deliverable

A folder containing:

- `pure_descriptors.py` (your four descriptors; ~250 lines; `python3 -m py_compile` clean)
- `comparison.py` or `test_descriptors.py` (the test suite; ~300 lines)
- `divergences.md` (5+ documented divergences; ~500 words)
- `README.md` (~200 words; what you found, what surprised you)

## Stretch

- Reimplement `__slots__` as a Python-level descriptor (the `slot_descriptor` C type, in Python). Hettinger's HowTo has a skeleton.
- Reimplement `functools.partialmethod` (which is a descriptor) and verify against stdlib.
- Read `Lib/types.py` for `DynamicClassAttribute`, the descriptor that lets you intercept attribute access on a class differently from access on an instance. Implement an equivalent.
