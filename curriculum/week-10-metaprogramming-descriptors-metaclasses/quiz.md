# Week 10 — Quiz

Ten multiple-choice questions. Each question has exactly one correct answer. Pick the best answer; "best" is judged by the lecture material and the cited PEPs. Aim for nine or ten correct on the first pass; if you score below seven, re-read the corresponding lecture section before moving on. Answers are at the bottom; do not peek.

---

**Q1.** Which PEP introduced `__init_subclass__` and `__set_name__`?

a) PEP 484
b) PEP 487
c) PEP 557
d) PEP 612

---

**Q2.** Which of the following is a **data descriptor**?

a) A class that defines only `__get__`.
b) A class that defines `__get__` and `__set__`.
c) Any function defined inside a class.
d) `staticmethod`.

---

**Q3.** The precedence order Python uses when resolving `instance.attr` is:

a) instance `__dict__` > data descriptor > non-data descriptor > class attribute
b) data descriptor > instance `__dict__` > non-data descriptor > class attribute
c) class attribute > instance `__dict__` > descriptor
d) data descriptor > non-data descriptor > instance `__dict__` > class attribute

---

**Q4.** What does `class Foo(Bar, plugin="mine"): pass` do with the `plugin="mine"` keyword?

a) Raises `SyntaxError` — keyword arguments are not allowed on `class` statements.
b) Passes `plugin="mine"` to `Bar.__init_subclass__`.
c) Sets `Foo.plugin = "mine"` as a class attribute.
d) Passes `plugin="mine"` to `Foo.__init__`.

---

**Q5.** `functools.cached_property` writes its result into `instance.__dict__` on first access. This means it is **incompatible with**:

a) `__slots__` (when `__dict__` is not in the slots list).
b) Subclassing.
c) Use on instances of an abstract base class.
d) `@classmethod`.

---

**Q6.** Which of these is **not** a legitimate use case for a metaclass in 2026?

a) Customising the namespace during class-body execution via `__prepare__`.
b) Overriding `__instancecheck__` for virtual-subclass registries (e.g. `abc.ABCMeta`).
c) Registering subclasses into a global registry.
d) Customising instance construction via `__call__` (e.g. singleton patterns).

---

**Q7.** When a class decorator returns a *different* class than the one passed in, which of the following is most likely to break?

a) `isinstance` checks made against references captured before decoration.
b) The class's `__name__` attribute.
c) Decorator stacking.
d) The decorator's own re-entrancy.

---

**Q8.** PEP 681 (`typing.dataclass_transform`) was introduced to:

a) Replace `@dataclass` with a type-checker-only construct.
b) Let arbitrary class decorators and metaclasses tell type checkers "I behave like `@dataclass`."
c) Add runtime type checking to `@dataclass`.
d) Deprecate `@dataclass` in favour of a new typing construct.

---

**Q9.** A `__init_subclass__` that does *not* call `super().__init_subclass__(**kwargs)` will:

a) Raise `TypeError` at class definition time.
b) Run only on direct subclasses, not on subclasses of subclasses.
c) Silently break cooperative multiple inheritance — any sibling `__init_subclass__` further up the MRO will not fire.
d) Cause the class to fail to compile.

---

**Q10.** Hettinger's "Descriptor HowTo Guide" includes pure-Python equivalents of all of the following **except**:

a) `property`
b) `classmethod`
c) `staticmethod`
d) `dataclass`

---

## Answers

1. **b** — PEP 487 (Martin Teichmann, 2016, merged in Python 3.6).
2. **b** — A data descriptor defines `__set__` and/or `__delete__` (typically in addition to `__get__`). Functions and `staticmethod` are non-data descriptors.
3. **b** — Data descriptor > instance `__dict__` > non-data descriptor > class attribute. This precedence is what makes `@property` (data descriptor) "win" against an instance attribute of the same name while a regular method (non-data descriptor) "loses."
4. **b** — Extra keyword arguments in the class statement are forwarded to `__init_subclass__` (and to the metaclass's `__new__`/`__init__`). This was added by PEP 487.
5. **a** — `cached_property` writes to `instance.__dict__`. Classes with `__slots__` and no `"__dict__"` entry have no per-instance dict, so the write fails with `AttributeError`. Adding `"__dict__"` to `__slots__` resolves it but defeats the purpose of slots.
6. **c** — Subclass registration is a textbook `__init_subclass__` use case as of PEP 487. The other three (a, b, d) are legitimate metaclass-only patterns.
7. **a** — If `Foo = my_decorator(Foo)` returns a new class, any code that captured `Foo` before decoration holds a reference to the *old* class. `isinstance(x, original_Foo)` will be False for instances of the new class. This is the canonical class-decorator bug.
8. **b** — PEP 681's `dataclass_transform` is a hint to type checkers that a particular decorator or metaclass synthesises an `__init__` from class annotations, like `@dataclass`. It is the bridge that makes `pydantic`'s metaclass-based design cooperate with mypy and pyright.
9. **c** — The chain breaks. Any sibling `__init_subclass__` further up the MRO (e.g. a mixin) will not fire. This is the most common `__init_subclass__` bug and it is silent — the only symptom is that some inherited behaviour does not happen.
10. **d** — The HowTo includes pure-Python equivalents of `property`, `classmethod`, `staticmethod`, `functools.cached_property`, and `__slots__`. It does *not* include `dataclass`, which is a class decorator rather than a descriptor.

---

## Scoring

| Score | Interpretation |
|------:|----------------|
| 10 | You have internalised the data model. Move to the homework. |
| 8–9 | Re-read whichever section your misses came from. |
| 5–7 | Re-read Lectures 1 and 2 carefully. The mini-project will be harder than necessary otherwise. |
| ≤ 4 | Set aside three more hours for the lectures and the Hettinger HowTo before attempting the mini-project. |
