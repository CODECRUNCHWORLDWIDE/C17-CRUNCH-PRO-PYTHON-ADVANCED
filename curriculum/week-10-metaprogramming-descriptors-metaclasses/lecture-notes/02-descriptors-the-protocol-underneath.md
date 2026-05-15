# Lecture 2 — Descriptors: the protocol underneath

> *Everything you have used in Python — `@property`, `@classmethod`, `@staticmethod`, `functools.cached_property`, `inspect.signature`, every ORM column you have ever declared, every `__slots__` member, every bound method — is a descriptor. The descriptor protocol is the single most under-documented yet load-bearing feature of the Python data model. Raymond Hettinger's "Descriptor HowTo Guide" (free, official, at <https://docs.python.org/3/howto/descriptor.html>) is the canonical reference, and the only one you really need. This lecture is a guided tour of the same material, with the validated-model library as the running example, and with an emphasis on the precedence rules that determine when a descriptor wins over the instance `__dict__` and when it loses.*

## Why this lecture exists

You can write Python for ten years and never write a descriptor of your own. You will write descriptors *transitively* every day — every `@property` you decorate, every `dataclasses.field()` you call, every SQLAlchemy `Column` you declare. The protocol is the substrate of normal Python; the visible decorators and field types are just the friendly faces on top.

The reason to learn the protocol explicitly is the rare day when the friendly face is not enough. You want a property that caches on first access (`cached_property`); you want an attribute that is read-only after first assignment; you want an attribute whose value differs per subclass; you want an ORM column that knows its name and table. Each of these is a descriptor with a small twist. The protocol is small enough — three methods (`__get__`, `__set__`, `__delete__`) plus the PEP 487 hook (`__set_name__`) — that learning it once pays back forever.

## The protocol in four signatures

A descriptor is any object whose class defines one or more of:

```python
class Descriptor:
    def __get__(self, instance: Any, owner: type | None = None) -> Any: ...
    def __set__(self, instance: Any, value: Any) -> None: ...
    def __delete__(self, instance: Any) -> None: ...
    def __set_name__(self, owner: type, name: str) -> None: ...
```

That is the entire protocol. Four methods, four signatures. The first three are the descriptor machinery proper; the fourth is the PEP 487 addition that lets the descriptor learn its own attribute name.

There are two flavours of descriptor, and the distinction matters for the precedence rules:

- **Non-data descriptor** — defines only `__get__`. Examples: functions (every function is a non-data descriptor; `function.__get__` returns a bound method when you access it through an instance).
- **Data descriptor** — defines `__set__` and/or `__delete__` (and usually `__get__`). Examples: `property`, `member_descriptor` (the thing `__slots__` produces), every ORM column type.

The reason the distinction matters: **data descriptors take precedence over instance `__dict__`. Non-data descriptors do not.** That is the rule that explains most descriptor-related surprises.

## The precedence rules

When Python evaluates `instance.attr`, it walks a precise sequence. Roughly (the precise spec is in `object.__getattribute__`):

1. Look up `attr` in `type(instance).__mro__`. If found and the value is a **data descriptor**, call its `__get__` and return.
2. Look up `attr` in `instance.__dict__`. If found, return the value.
3. Look up `attr` in `type(instance).__mro__` again. If found (it will be — we found it in step 1, just not as a data descriptor), and the value is a **non-data descriptor**, call its `__get__` and return.
4. Otherwise, return the raw class attribute, or raise `AttributeError`.

The two-pass MRO walk is the implementation detail; the conceptual rule is: **data descriptor > instance dict > non-data descriptor > class attribute**.

This is why `@property` (a data descriptor) "wins" against an instance attribute of the same name, while an ordinary method (a non-data descriptor) "loses" to an instance attribute. If you ever wondered why you can shadow a method on a per-instance basis (`obj.method = lambda: ...`) but not a property, this is the answer.

## Worked example: `property` from scratch

The classic exercise. Here is `property`, reimplemented in pure Python (this is, with minor changes, what Hettinger's HowTo gives):

```python
from __future__ import annotations
from typing import Any, Callable


class Property:
    """Pure-Python property. Equivalent to the C implementation in CPython."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any, Any], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        doc: str | None = None,
    ) -> None:
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc or (fget.__doc__ if fget else None)
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        if self.fget is None:
            raise AttributeError(f"property {self._name!r} has no getter")
        return self.fget(instance)

    def __set__(self, instance: Any, value: Any) -> None:
        if self.fset is None:
            raise AttributeError(f"property {self._name!r} has no setter")
        self.fset(instance, value)

    def __delete__(self, instance: Any) -> None:
        if self.fdel is None:
            raise AttributeError(f"property {self._name!r} has no deleter")
        self.fdel(instance)

    def getter(self, fget: Callable[[Any], Any]) -> Property:
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset: Callable[[Any, Any], None]) -> Property:
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel: Callable[[Any], None]) -> Property:
        return type(self)(self.fget, self.fset, fdel, self.__doc__)
```

About fifty lines. The whole thing. The C implementation in CPython is faster but semantically identical. Use this for:

```python
class C:
    @Property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, value: int) -> None:
        if value < 0:
            raise ValueError("x must be non-negative")
        self._x = value
```

The `@x.setter` trick works because `Property.setter` returns a new `Property` with the setter swapped in; the new one is assigned to `x`, replacing the previous one. Each `Property.setter` call creates a new descriptor and the decorator syntax wires up the assignment. Hettinger calls this "the canonical Python decorator pattern" and it is.

## Worked example: `classmethod` and `staticmethod` from scratch

```python
class ClassMethod:
    """Pure-Python classmethod."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Callable[..., Any]:
        if owner is None:
            owner = type(instance)
        # Bind the class (not the instance) as the first argument.
        from functools import partial
        return partial(self.func, owner)


class StaticMethod:
    """Pure-Python staticmethod."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Callable[..., Any]:
        # Return the function unchanged. No binding.
        return self.func
```

These are both non-data descriptors (only `__get__`). The difference: `ClassMethod.__get__` binds the *owner* (the class) as the first argument; `StaticMethod.__get__` does no binding at all. That is the entire definition of classmethod and staticmethod. Forty lines together.

The fact that an ordinary `def` inside a class body becomes a bound method when accessed through an instance is the same machinery: `function.__get__(instance, owner)` returns `MethodType(function, instance)`. The function object is a non-data descriptor. There is no special case for methods. The protocol *is* the mechanism.

## Worked example: `cached_property` from scratch

`functools.cached_property` (added in Python 3.8) is a particularly clean teaching example. It is a data descriptor *if* you read the source, but functionally it is a "compute once, then shadow itself with the result in `instance.__dict__`" trick. The HowTo's implementation:

```python
class CachedProperty:
    """Pure-Python cached_property. Equivalent to functools.cached_property."""

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self.func = func
        self.__doc__ = func.__doc__
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        if not self._name:
            self._name = name
        elif self._name != name:
            raise TypeError(
                f"Cannot assign the same cached_property to two different names "
                f"({self._name!r} and {name!r})"
            )

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        # Compute, then write into instance.__dict__ so the descriptor
        # is shadowed on subsequent access.
        value = self.func(instance)
        instance.__dict__[self._name] = value
        return value
```

`CachedProperty` is a **non-data descriptor** (only `__get__`). On first access, it computes and writes into `instance.__dict__`. On subsequent access, the precedence rule says "instance dict beats non-data descriptor", so the cached value is returned without going through `__get__`. That is the whole trick.

Two important corollaries:

- **`cached_property` is incompatible with `__slots__`.** `__slots__` removes `instance.__dict__`. The descriptor cannot write to a dict that does not exist. `AttributeError: 'C' object has no attribute '__dict__'`. The fix is to use a regular `property` plus an explicit `_cache` slot, or to add `__dict__` back to `__slots__`.
- **`cached_property` cannot be reused under two names.** The `__set_name__` check catches the case where the same descriptor object is assigned to two attributes on the same class. The name has to be unique because the cache writes to `instance.__dict__[self._name]`. The CPython implementation has the same check.

## Worked example: `@validated_model`, version 3 — full descriptors

Back to the running example. The third version uses one descriptor per field type:

```python
from __future__ import annotations
from typing import Any


class Field:
    """Base validating descriptor."""

    def __init__(self) -> None:
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        try:
            return instance.__dict__[self._name]
        except KeyError as exc:
            raise AttributeError(self._name) from exc

    def __set__(self, instance: Any, value: Any) -> None:
        self.validate(value)
        instance.__dict__[self._name] = value

    def validate(self, value: Any) -> None:
        raise NotImplementedError


class StringField(Field):
    def __init__(self, max_length: int = 256) -> None:
        super().__init__()
        self.max_length = max_length

    def validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{self._name!r}: expected str, got {type(value).__name__}")
        if len(value) > self.max_length:
            raise ValueError(f"{self._name!r}: too long (> {self.max_length})")


class IntField(Field):
    def __init__(self, min_value: int = 0, max_value: int | None = None) -> None:
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> None:
        if not isinstance(value, int):
            raise TypeError(f"{self._name!r}: expected int, got {type(value).__name__}")
        if value < self.min_value:
            raise ValueError(f"{self._name!r}: < min ({self.min_value})")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self._name!r}: > max ({self.max_value})")


class Model:
    def __init__(self, **kwargs: Any) -> None:
        for name, value in kwargs.items():
            setattr(self, name, value)  # routes through descriptor __set__

    def __repr__(self) -> str:
        fields = [k for k in type(self).__dict__ if isinstance(type(self).__dict__[k], Field)]
        parts = [f"{n}={getattr(self, n)!r}" for n in fields]
        return f"{type(self).__name__}({', '.join(parts)})"


class User(Model):
    name = StringField(max_length=50)
    age = IntField(min_value=0, max_value=150)


u = User(name="alice", age=30)
u.name  # "alice"
u.age = 200  # ValueError: age: > max (150)
```

About a hundred lines. The descriptor version is more powerful than the decorator version because each descriptor can hold its own configuration (`max_length=50`, `min_value=0, max_value=150`). The decorator version had to encode field-specific configuration in a separate dict; the descriptor version puts the configuration where the field is declared, which is where it belongs.

This is, give or take, what every ORM does. SQLAlchemy's `Column` is a descriptor (with a lot of additional machinery for SQL generation). Django's model fields are descriptors. Pydantic v1's fields were descriptors. The pattern is industry standard.

## When to reach for a descriptor

The rule of thumb: **descriptors are right when the per-attribute behaviour is itself reusable**. `StringField(max_length=50)` is a unit of behaviour you would use on a dozen models. `@property` works for one-off computed attributes; a descriptor works for a family of attributes that share a pattern (validation, persistence, lazy loading).

Three concrete signals that a descriptor is the right choice:

1. **You want the same attribute behaviour on multiple classes.** A descriptor is a class; you instantiate it as many times as you have attributes. A `@property` is per-class.
2. **You want the attribute behaviour to be parameterised.** `StringField(max_length=50)` vs. `StringField(max_length=200)` is one descriptor class, two configurations. The decorator version cannot easily do this.
3. **You want to integrate with `inspect`, `dataclasses`, or similar introspection tools.** Descriptors are discoverable via `inspect.getmembers(cls, predicate=...)`. The decorator version's modifications are invisible.

If none of these signals are present, you probably want a `@property` or a class decorator.

## Common bugs and how to avoid them

**Bug 1: `__set_name__` forgotten.** The descriptor does not know its name, so `instance.__dict__[self._name]` writes to `instance.__dict__[""]`, which collides across all descriptors on the class. Fix: implement `__set_name__`. Test it: declare two descriptors on the same class and verify they read/write to distinct dict entries.

**Bug 2: descriptor stored on the instance, not the class.** Descriptors only fire when they are on the *class*, not on the instance. Writing `instance.field = StringField()` inside `__init__` does not work as a descriptor — the descriptor protocol checks `type(instance).__mro__`, not `instance.__dict__`. Fix: declare the descriptor at class scope.

**Bug 3: descriptor mutating class-level state from `__set__`.** If `Field.__set__` writes to `self.value = ...` (on the descriptor itself, not on `instance.__dict__`), the value is shared across all instances. This is a classic bug; you set `u1.name = "alice"`, then `u2.name` is also `"alice"`. Fix: always write to `instance.__dict__[self._name]`, never to `self.<anything>` from `__set__`.

**Bug 4: descriptor stored in `instance.__dict__` under its own name.** If you write `instance.__dict__[self._name] = value` for a non-data descriptor, you have just shadowed the descriptor (because the precedence rule favours `instance.__dict__` over non-data descriptors). This is sometimes intentional (`cached_property` relies on this). When it is not intentional, it is a bug. Fix: use a data descriptor (define `__set__`) if you want to keep going through the descriptor on every access.

**Bug 5: non-data descriptor used where you wanted a data descriptor.** If you define only `__get__`, the descriptor loses to `instance.__dict__`. If a caller writes `instance.attr = something`, the assignment goes to `instance.__dict__` and the descriptor's `__get__` is never called again. This is the most subtle of the five bugs. Fix: add `__set__` (and possibly `__delete__`) to upgrade to a data descriptor.

## The `__slots__` interaction

`__slots__` works because `slot_descriptor` (the C-level type) is a data descriptor. When you declare `class C: __slots__ = ("x", "y")`, CPython creates a `member_descriptor` for each name in `__slots__` and installs them on the class. The descriptor's `__get__` reads from a fixed offset in the instance (not from `instance.__dict__`, which does not exist); `__set__` writes to the same offset.

This explains the otherwise-mysterious rule that `__slots__` and `__dict__` are mutually exclusive: a class with `__slots__` has no `__dict__` by default, so descriptors that rely on `instance.__dict__` (like `cached_property`) do not work. If you need both, you include `"__dict__"` in `__slots__` explicitly.

## The `inspect` interaction

`inspect.signature(SomeClass)` works because `SomeClass.__init__` is a function, functions are non-data descriptors, accessing `SomeClass.__init__` goes through `__get__`, and `inspect.signature` reads the resulting function's annotations and defaults. This is one of the cleaner uses of the protocol you may not have noticed.

`inspect.getmembers(cls)` walks the class's namespace and, for each entry, checks if it is a descriptor. If you want to filter to only the descriptors that match a predicate (say, only the `Field` descriptors in a model):

```python
import inspect

fields = [
    (name, value)
    for name, value in inspect.getmembers(User)
    if isinstance(value, Field)
]
```

This is one of the cleanest ways to enumerate a model's fields from outside the model.

## Reading

- **"Descriptor HowTo Guide"** — <https://docs.python.org/3/howto/descriptor.html>. Hettinger. Read end-to-end. Twice if you have not. Once before writing your first descriptor, once after.
- **Data model §3.3.2.4 and §3.3.2.5** — <https://docs.python.org/3/reference/datamodel.html#implementing-descriptors>. The official spec, more terse than the HowTo.
- **`functools.cached_property` source** — <https://github.com/python/cpython/blob/main/Lib/functools.py>. About 50 lines. Compare to the version we wrote above.
- **PEP 252** — <https://peps.python.org/pep-0252/>. Guido's original descriptor PEP, 2001. Mostly historical.

## What to take away from this lecture

1. **Every dotted attribute access goes through the descriptor protocol.** `@property`, `@classmethod`, `@staticmethod`, bound methods, `__slots__`, `cached_property` — all descriptors. The protocol is the substrate.
2. **The precedence rule is data descriptor > instance dict > non-data descriptor.** This is the rule that explains every descriptor surprise.
3. **`__set_name__` is required for any descriptor that needs to know its own name.** Forgetting it is the most common descriptor bug. PEP 487 made it easy; the easy thing is also the correct thing.

Tomorrow: the top of the ladder. Metaclasses, when to use them (rarely), and when not to (almost always).
