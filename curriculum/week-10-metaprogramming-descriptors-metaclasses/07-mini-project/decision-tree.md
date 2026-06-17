# The reference decision tree

> *Read after you have written your own version. Comparing where the trees agree and where they disagree is the point.*

## The tree

```text
                            Question 1
                  Does the consumer mark specific
                  classes with the transformation?
                  (Examples: @dataclass, @attrs.define,
                  @functools.total_ordering)
                            │
                  ┌─────────┴──────────┐
                 Yes                   No
                  │                    │
            Class decorator       ── continue to Q2 ──
            (PEP 557 / PEP 681)
            cost: lowest
            tooling: highest
                                       │
                                Question 2
                                Is the transformation applied
                                to every subclass of a base
                                class you own?
                                (Examples: ORM Model, Plugin,
                                Validated base, EventEmitter)
                                       │
                              ┌────────┴────────┐
                             Yes                No
                              │                 │
                  __init_subclass__       ── continue to Q3 ──
                  + __set_name__ for any
                  attribute that needs
                  to know its name
                  (PEP 487)
                  cost: low
                  tooling: high
                                                │
                                       Question 3
                                       Is the work per-attribute,
                                       parameterised, reusable
                                       across multiple classes?
                                       (Examples: ORM Column,
                                       Validating Field,
                                       Cached attribute,
                                       Slot-backed attribute)
                                                │
                                       ┌────────┴────────┐
                                      Yes                No
                                       │                 │
                            Descriptors                ── continue to Q4 ──
                            (often combined with
                            __init_subclass__ for
                            owner-class registration)
                            cost: medium
                            tooling: medium
                                                          │
                                                 Question 4
                                                 Do you need any of:
                                                 - __prepare__ (custom
                                                   class-body namespace)
                                                 - __call__ on the metaclass
                                                   (intercept instance creation)
                                                 - __instancecheck__ /
                                                   __subclasscheck__
                                                   (custom isinstance)
                                                          │
                                                ┌─────────┴────────┐
                                               Yes                 No
                                                │                  │
                                          Metaclass            ⚠ stop ⚠
                                          (PEP 3115)           You do not need
                                          cost: highest        metaprogramming
                                          tooling: lowest      for this.
                                          accept metaclass     A plain class
                                          conflict tax         with __init__ is
                                                               the right answer.
```

## The tree in prose

You walk this tree top-to-bottom. The first "yes" wins. If you reach Question 4 and the answer is "no", you do not need any of the four mechanisms.

### Question 1: Does the consumer mark specific classes?

The signature: the user writes `@my_decorator` above their class. Examples in the ecosystem: `@dataclass`, `@dataclasses.dataclass(frozen=True)`, `@attrs.define`, `@functools.total_ordering`, `@runtime_checkable` (for Protocols).

If **yes**, use a class decorator. This is the cheapest path. It composes with other decorators. It cooperates with type checkers (use `@typing.dataclass_transform()` if your decorator synthesises `__init__`). It does not introduce a metaclass conflict.

Why not always pick this? Two reasons:

1. The user has to remember to apply it on every subclass. The decorator does not run automatically on subclasses. If your problem is "I want this to apply to every subclass of `Model`," a decorator is the wrong tool.
2. The decorator runs once, at decoration time. It cannot react to later changes (a base class that gains new fields after subclasses are decorated).

### Question 2: Is it about every subclass of a base class you own?

The signature: you ship a `Plugin` base class (or `Model`, or `Validator`, or `Codec`) and you want every user-written subclass of it to be transformed automatically.

If **yes**, use `__init_subclass__` on the base class. Combine with `__set_name__` if your fields are descriptors that need to know their own names (which they almost always do).

PEP 487 was added to the language explicitly for this case. Before 2016, this required a metaclass. After 2016, it does not. The migration is real: `marshmallow`, `pluggy`, parts of `sqlalchemy`, and others all simplified after 3.6 was widely available.

Why not always pick this? Two reasons:

1. If the transformation needs to happen on a class you do not control, you cannot ask the user to inherit from your base. A decorator is the right answer there.
2. If the transformation is parameterised per-attribute (some fields are strings with max-length, some are integers with ranges), the `__init_subclass__` body becomes a big `if`-tree. A descriptor is the right answer there.

### Question 3: Is the per-attribute work reusable?

The signature: you want to write `class User(Model): name = StringField(max_length=50); email = EmailField()`. Each field has its own validation logic, parameterised at the *call site* where the field is declared.

If **yes**, use descriptors. The descriptor protocol exists for exactly this purpose. The combination of `__set_name__`, `__get__`, `__set__` gives you a complete unit of behaviour.

Combine with `__init_subclass__` on the model base if you also want auto-registration or auto-generation of `__init__`. The two are not mutually exclusive; most real ORM/validation libraries use both.

Why not always pick this? Two reasons:

1. Descriptors are more code than a class decorator for the same simple case. If your validation is "type-check on assignment, no per-field parameters," a decorator is faster to write and read.
2. Descriptors live on the *class*, not on instances. They cannot easily implement instance-level dynamic field discovery (e.g., "user adds a new field at runtime"). A `__getattr__` override is the answer there.

### Question 4: Do you need `__prepare__`, `__call__`, or `__instancecheck__`?

The signature: one of the following is true:

- **`__prepare__`** — you need to detect duplicate names *during* class-body execution, or you need the class-body namespace to be a custom dict. `enum.EnumType` does this to catch duplicate enum members and to track ordering before 3.7's order-preserving dicts.
- **`__call__`** — you need to intercept *instance* creation. Singletons (return the same instance every time). Factory dispatch (return different concrete classes based on arguments). Pooling (return a recycled instance from a freelist).
- **`__instancecheck__`** / **`__subclasscheck__`** — you need `isinstance(x, YourClass)` to consult something other than `type(x).__mro__`. `abc.ABCMeta` does this for virtual subclass registration.

If **yes** to any, use a metaclass. There is no other mechanism that provides these hooks. Accept the costs:

- **Metaclass conflict** under multiple inheritance. The user has to define a combined metaclass to mix your class with another metaclass-using class.
- **Type-checker friction**. mypy and pyright do not run your metaclass. Use `@typing.dataclass_transform()` if your metaclass synthesises `__init__`; otherwise, write a plugin or stubs.
- **Less code is more legible**. A metaclass is the right tool for a small, well-defined set of jobs. If you find yourself writing more than 200 lines of metaclass, ask whether `__init_subclass__` plus a class decorator could replace it.

If **no**, you do not need metaprogramming. Write a plain class. Be embarrassed by how plain it is. It is correct.

## Worked examples by industry

**`@dataclass`** — class decorator. The transformation is per-class; the user marks each class. No subclassing involvement. No metaclass.

**`pydantic.BaseModel`** — metaclass + `__init_subclass__` + descriptors + `dataclass_transform`. The transformation is per-subclass, the fields are parameterised descriptors, the type-checker bridge is critical for usability. This is the rare case where the full machinery is justified. Pydantic v2 covers it.

**SQLAlchemy `DeclarativeBase`** — descriptors (`Column`, `Mapped[]`) + `__init_subclass__` (for table registration in v2). Migration from v1's `DeclarativeMeta` metaclass is documented at <https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html>.

**`abc.ABC`** — metaclass (`ABCMeta`). Justified by `__instancecheck__` override for virtual-subclass registration.

**`enum.Enum`** — metaclass (`EnumType`). Justified by `__prepare__` (duplicate detection) and `__call__` (member lookup).

**`functools.cached_property`** — descriptor. Justified by per-attribute caching behaviour.

**Django models** — metaclass (`ModelBase`). Could be `__init_subclass__` in a greenfield design; Django keeps the metaclass for migration-cost reasons and because `Meta` inner-class processing benefits from `__prepare__`-adjacent control. A reasonable judgement.

**`pytest.fixture`** — function decorator (not class decorator). Not on this tree because pytest fixtures are not class transformations.

## When in doubt

Pick one rung lower than your instinct.

You almost never need a metaclass when you think you do. You sometimes need a descriptor when you think you need a decorator. You frequently can use `__init_subclass__` when the textbook says metaclass. The pre-PEP-487 textbooks are misleading on this point; the migration history of the major libraries (Section "Worked examples by industry" above) is the corrective.

If after working through this tree you still believe a metaclass is the right answer, you may be right. Cite which of the three hooks (`__prepare__`, `__call__`, `__instancecheck__`) you need. If you cannot, you do not need a metaclass.
