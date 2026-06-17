# Exercises — Solutions and Discussion

The four exercises this week form a ladder. Exercise 1 is a class decorator; Exercise 2 is `__init_subclass__` plus `__set_name__`; Exercise 3 is the full descriptor protocol; Exercise 4 is metaclasses. Read each solution after attempting the exercise. The point is not "did your code match mine character-for-character" — most working solutions will differ in detail — but "do you see the same shape, and do you understand the failure modes the reference catches."

Compile-check every solution before reading:

```bash
python3 -m py_compile exercise-01-class-decorator.py
python3 -m py_compile exercise-02-init-subclass.py
python3 -m py_compile exercise-03-descriptor-protocol.py
python3 -m py_compile exercise-04-metaclass-basics.py
```

All four are expected to pass on Python 3.11+.

## Exercise 1 — Class decorator

The reference implementation is in the exercise file itself (the body of `validated_model`). The full implementation is about 35 lines of substance; the rest is the test harness.

### Expected output

```text
happy paths:
  User(name='alice', age=30)
  Product(sku='abc-123', price=499)
  Empty()
validation failures:
  User(missing age): raised TypeError: User: missing required arguments: ['age']
  User(extra kwarg): raised TypeError: User: unexpected arguments: ['role']
  User(wrong type): raised TypeError: User.name: expected str, got int
  User(negative age): raised ValueError: User.carol... must be >= 0
  Product(too-long sku): raised ValueError: Product.sku: must be <= 256 characters
introspection:
  User._fields = ('name', 'age')
  Product._fields = ('sku', 'price')
  isinstance(u, User) = True
```

(The exact wording of error messages will match the implementation; the *shape* — TypeError on type mismatches, ValueError on constraint violations — should match.)

### Discussion

**Why the decorator mutates `cls.__init__` instead of returning a subclass.** Returning a subclass (`return type(cls.__name__, (cls,), {"__init__": ...})`) appears to work but breaks `isinstance` for any code that captured a reference to the pre-decoration class. The decorator should be transparent — same identity in, same identity out.

**Why type checkers tolerate this decorator silently.** mypy and pyright see `validated_model(User)` as `Callable[[type[User]], type[User]]` — they trust the type variable `T`. They do not, however, verify that the synthesised `__init__` accepts exactly the annotated fields. If you want the type checker to verify call sites, decorate `validated_model` itself with `@typing.dataclass_transform()` (PEP 681); the checker will then validate `User(name="alice", age=30)` against the `User` annotations.

**Why we reject extra kwargs.** Real-world validated-model libraries differ on this. `dataclasses` rejects (`TypeError: __init__() got an unexpected keyword argument`). Pydantic v1 silently ignored by default; v2 rejects unless `model_config = {"extra": "allow"}`. The reference rejects because silent acceptance hides typos. Mark this as a TODO if you want to make it configurable.

**The dict-copying line.** `annotations: dict[str, type] = dict(getattr(cls, "__annotations__", {}))` copies the annotation dict. Without the `dict(...)`, mutations to `annotations` would leak back to `cls.__annotations__` — though the reference does not mutate it, the discipline is to copy on read so future maintainers cannot accidentally introduce a leak.

## Exercise 2 — `__init_subclass__` and `__set_name__`

### Expected output

```text
registry:
       'csv' -> CsvExporter
       'json' -> JsonExporter
       'xml' -> XmlExporter
descriptor names:
  JsonExporter.label = json:label
  CsvExporter.label  = csv:label
  CsvExporter.header = hdr:header
error paths:
  duplicate plugin_name: raised ValueError: plugin_name 'json' already registered by JsonExporter
  missing plugin_name: raised TypeError: Anonymous: must provide plugin_name= keyword argument
cooperative chain:
  CountingMixin._count after XmlExporter = 1
  XmlExporter.plugin_name = xml
```

### Discussion

**Why `super().__init_subclass__(**kwargs)` is the first line.** The pattern is "consume the kwargs you care about, forward the rest." If `Plugin.__init_subclass__` is the *last* in the MRO chain (between the subclass and `object`), then forwarding to `super()` is harmless — `object.__init_subclass__` accepts no kwargs and would raise if given any. By calling `super()` *first* and forwarding only `**kwargs` (without `plugin_name`), we let any intermediate mixin react before `Plugin` consumes its kwarg.

**Why the duplicate-detection check matters.** Plugin registries with duplicate keys silently lose one of the implementations. The class statement is the right place to catch this — at import time, not at runtime. This is exactly the kind of "fail at class creation" check that `__init_subclass__` is best at.

**Why `Label` is intentionally simple.** It is a non-data descriptor (no `__set__`). It works as a label generator only — read-only data flowing from the class to instances. The `__set_name__` is the key feature; without it, the descriptor would not know its own name and `f"{self.prefix}{self._name}"` would produce `"json:"` instead of `"json:label"`.

**Cooperative `__init_subclass__` and MRO.** When `XmlExporter(CountingMixin, Plugin, plugin_name="xml")` is created, Python computes the MRO: `[XmlExporter, CountingMixin, Plugin, object]`. The `__init_subclass__` of `XmlExporter`'s *parent* chain fires — `super(XmlExporter).__init_subclass__(...)` resolves to `CountingMixin.__init_subclass__`. `CountingMixin` forwards to `super()`, which lands at `Plugin.__init_subclass__`. `Plugin` consumes `plugin_name` and forwards remaining kwargs (none) to `object.__init_subclass__`. The full chain runs.

## Exercise 3 — Descriptor protocol

### Expected output

```text
Property:
  c.value = 25.0
  after set, c.value = 30.0
  guard caught: below absolute zero
ClassMethod:
  bump -> 1
  bump -> 2
  Counter.count = 2
StaticMethod:
  MathUtils.square(7) = 49
  inst.square(8) = 64
CachedProperty:
  first access: 25 (calls=1)
  second access: 25 (calls=1)
  third access: 25 (calls=1)
  'computed' in e.__dict__ = True
```

### Discussion

**Property and the `getter/setter/deleter` trio.** Each of these returns a *new* `Property` with one attribute swapped. The pattern preserves the doc string, the other accessors, and identity-of-shape — the class definition reads naturally because Python's decorator syntax handles the re-assignment. If you wrote them as in-place mutators (`self.fset = fset; return self`) the syntax would still work, but you would lose the immutability guarantee Hettinger's HowTo emphasises.

**ClassMethod and `partial`.** `functools.partial(self.func, owner)` is the simplest way to bind the class as the first argument. The CPython C implementation builds a `MethodType` more directly; functionally equivalent. The unbound method (call directly on the class) and bound method (call on an instance) both behave identically because `__get__` ignores the `instance` argument.

**StaticMethod is the simplest descriptor.** Just returns the function. The `__get__` exists only because, without it, accessing `MathUtils.square` would return the `StaticMethod` instance, not a callable. The descriptor protocol provides the unwrapping.

**CachedProperty and the `__dict__` shadowing trick.** First access: `__get__` runs, computes, writes `instance.__dict__["computed"] = value`. Second access: the precedence rule says "instance `__dict__` beats non-data descriptor", so the cached value is returned without calling `__get__`. This is why `'computed' in e.__dict__` becomes True after first access.

**Why `cached_property` is incompatible with `__slots__`.** A class with `__slots__ = ("base", "calls")` and no `"__dict__"` in slots has no per-instance dict. `instance.__dict__[self._name] = value` raises `AttributeError`. Either include `"__dict__"` in `__slots__` or use a regular `Property` with explicit caching.

**Why the `__set_name__` check on CachedProperty raises if reassigned.** A `CachedProperty` instance stores `self._name`. If you assigned the *same instance* to two attribute names on the same class, the cache lookup would use whichever name was set last, and the other access path would compute every time. The check catches the mistake at class-creation time. CPython's `functools.cached_property` has the same check.

## Exercise 4 — Metaclass basics

### Expected output (abridged; ordering of TracingMeta lines may vary slightly)

```text
=== Class creation with TracingMeta ===
  TracingMeta.__new__('Foo', bases=[])
  TracingMeta.__init__('Foo')

=== Instance creation with TracingMeta ===
  TracingMeta.__call__(Foo, args=(), kwargs={})
  f.method() = 1

=== type(Foo) and type(type(Foo)) ===
  type(Foo) = TracingMeta
  type(type(Foo)) = type
  type(Foo).__mro__ = ['TracingMeta', 'type', 'object']

=== SingletonMeta ===
  c1 is c2 = True
  id(c1) == id(c2) = True

=== Metaclass conflict ===
  attempting class C(A, B): with no combined metaclass...
  TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases

=== Resolving the conflict with a combined metaclass ===
  resolved: type(C) = MetaAB
  resolved: MRO of type(C) = ['MetaAB', 'MetaA', 'MetaB', 'type', 'object']
```

### Discussion

**`__new__` runs once at class creation; `__init__` runs once at class creation; `__call__` runs once per instance creation.** Newcomers conflate these. The lifecycle is clear in the trace: define `Foo` → metaclass `__new__` and `__init__` fire. Call `Foo()` → metaclass `__call__` fires.

**Why `type(type(Foo)) == type`.** This is the recursion's base case. Every class has a metaclass; the metaclass of the metaclass is `type` itself. `type(type)` is `type`. The recursion terminates one level up from any user class.

**SingletonMeta and `__call__`.** Overriding `__call__` is the right way to intercept instance creation when you want a singleton semantically — `Config()` and `Config()` return the same object, transparently. A class decorator can do this too, but a metaclass makes the singleton-ness *part of the class's identity* and survives subclassing more naturally.

**Why the metaclass conflict happens.** `MetaA` and `MetaB` are unrelated subclasses of `type`. Python cannot pick which to use for `C`, so it refuses. The resolution — a `MetaAB` that inherits from both — is correct *if* both metaclasses are cooperative (i.e., they call `super().__new__` correctly). If they are not (e.g., one always returns a specific kind of class object), the conflict cannot be resolved without modifying one of the metaclasses.

**`type.__call__(MetaAB, ...)` is the explicit form.** Calling a metaclass directly is the same as calling `type` directly with the metaclass as first argument. We use this form to avoid raising the metaclass conflict at class-statement evaluation (which would abort `main()`); a normal `class C(A, B, metaclass=MetaAB): pass` would also work but introduces a SyntaxError surface if you fat-finger it.

## Common bugs across all four exercises

**1. Forgetting `__set_name__`.** Symptom: the descriptor's `_name` is empty or wrong. Two descriptors collide on `instance.__dict__[""]`. Fix: implement `__set_name__(self, owner, name)`.

**2. Forgetting `super().__init_subclass__(**kwargs)`.** Symptom: silent — the next mixin's `__init_subclass__` never fires. Visible only when a third party tries to mix your class with theirs. Fix: always call super(), always forward kwargs.

**3. Mutating `cls.__dict__` from `__init_subclass__` in a way that breaks future subclasses.** Symptom: subclass appears to inherit a stale value. Fix: write to `cls.__dict__` only, never to a parent's dict; let subclasses compute their own values.

**4. Storing per-instance state on the descriptor.** Symptom: all instances share the same value. Fix: always write to `instance.__dict__[self._name]`, never to `self.<something>` from `__set__`.

**5. Using `__init__` instead of `__new__` in a metaclass.** Symptom: changes to namespace do not appear on the class. Fix: do the class-mutation work in `__new__`, before `super().__new__` returns the constructed class — or do it on `cls` in `__init__` knowing the class already exists.

Discussion ends. Move to the challenges.
