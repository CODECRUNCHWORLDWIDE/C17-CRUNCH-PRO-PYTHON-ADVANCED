"""
Mini-project benchmark — measure the four mechanisms head-to-head.

This file is a starting point. It implements all four versions of the
validated-model library at production-quality, runs a timeit/tracemalloc
comparison, and prints a table. Your job is to read the four implementations,
modify or replace them, and ensure the benchmark still passes.

Run:
    python3 benchmark.py

Compile-check:
    python3 -m py_compile benchmark.py

The four versions in this file:
    1. validated_model (class decorator)
    2. Model + __init_subclass__
    3. Model + descriptors
    4. Model + metaclass

All four expose the same public API: a Model-like construct with declarative
StringField/IntField attributes, __init__/__repr__/_fields/to_dict.

Citations:
    - PEP 487  — https://peps.python.org/pep-0487/
    - PEP 557  — https://peps.python.org/pep-0557/
    - PEP 681  — https://peps.python.org/pep-0681/
    - Descriptor HowTo — https://docs.python.org/3/howto/descriptor.html
    - Data model — https://docs.python.org/3/reference/datamodel.html
"""

from __future__ import annotations

import timeit
import tracemalloc
from typing import Any, ClassVar


# ---------------------------------------------------------------------------
# Version 1 — class decorator
# ---------------------------------------------------------------------------


def _validate_str(name: str, value: Any, max_length: int) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name!r}: expected str, got {type(value).__name__}")
    if len(value) > max_length:
        raise ValueError(f"{name!r}: too long (> {max_length})")


def _validate_int(name: str, value: Any, min_value: int, max_value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name!r}: expected int, got {type(value).__name__}")
    if value < min_value:
        raise ValueError(f"{name!r}: < min ({min_value})")
    if value > max_value:
        raise ValueError(f"{name!r}: > max ({max_value})")


class _FieldSpec:
    """A field declaration carried by the decorator/init_subclass implementations."""

    def __init__(
        self,
        type_: type,
        max_length: int = 256,
        min_value: int = 0,
        max_value: int = 2 ** 31 - 1,
    ) -> None:
        self.type_: type = type_
        self.max_length: int = max_length
        self.min_value: int = min_value
        self.max_value: int = max_value

    def validate(self, name: str, value: Any) -> None:
        if self.type_ is str:
            _validate_str(name, value, self.max_length)
        elif self.type_ is int:
            _validate_int(name, value, self.min_value, self.max_value)
        else:
            raise TypeError(f"unsupported field type: {self.type_!r}")


def validated_model(cls: type) -> type:
    """Class decorator. Reads __field_specs__ from the class body."""
    specs: dict[str, _FieldSpec] = dict(getattr(cls, "__field_specs__", {}))
    field_names: tuple[str, ...] = tuple(specs.keys())

    def __init__(self: Any, **kwargs: Any) -> None:
        missing: list[str] = [n for n in field_names if n not in kwargs]
        if missing:
            raise TypeError(f"{cls.__name__}: missing arguments: {missing!r}")
        extras: list[str] = [k for k in kwargs if k not in specs]
        if extras:
            raise TypeError(f"{cls.__name__}: unexpected arguments: {extras!r}")
        for name in field_names:
            value: Any = kwargs[name]
            specs[name].validate(name, value)
            setattr(self, name, value)

    def __repr__(self: Any) -> str:
        parts: list[str] = [f"{n}={getattr(self, n)!r}" for n in field_names]
        return f"{cls.__name__}({', '.join(parts)})"

    def to_dict(self: Any) -> dict[str, Any]:
        return {n: getattr(self, n) for n in field_names}

    cls.__init__ = __init__       # type: ignore[method-assign]
    cls.__repr__ = __repr__       # type: ignore[method-assign]
    cls.to_dict = to_dict         # type: ignore[attr-defined]
    cls._fields = field_names     # type: ignore[attr-defined]
    return cls


# ---------------------------------------------------------------------------
# Version 2 — Model base with __init_subclass__
# ---------------------------------------------------------------------------


class ModelInitSubclass:
    """Version 2: inherit and declare __field_specs__; base picks them up."""

    _fields: ClassVar[tuple[str, ...]] = ()
    _specs: ClassVar[dict[str, _FieldSpec]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Merge inherited specs with newly declared ones.
        inherited: dict[str, _FieldSpec] = {}
        for base in reversed(cls.__mro__[1:]):
            inherited.update(getattr(base, "_specs", {}))
        new: dict[str, _FieldSpec] = dict(getattr(cls, "__field_specs__", {}))
        inherited.update(new)
        cls._specs = inherited
        cls._fields = tuple(inherited.keys())

    def __init__(self, **kwargs: Any) -> None:
        specs: dict[str, _FieldSpec] = type(self)._specs
        field_names: tuple[str, ...] = type(self)._fields
        missing: list[str] = [n for n in field_names if n not in kwargs]
        if missing:
            raise TypeError(f"{type(self).__name__}: missing arguments: {missing!r}")
        extras: list[str] = [k for k in kwargs if k not in specs]
        if extras:
            raise TypeError(f"{type(self).__name__}: unexpected arguments: {extras!r}")
        for name in field_names:
            value: Any = kwargs[name]
            specs[name].validate(name, value)
            setattr(self, name, value)

    def __repr__(self) -> str:
        parts: list[str] = [f"{n}={getattr(self, n)!r}" for n in type(self)._fields]
        return f"{type(self).__name__}({', '.join(parts)})"

    def to_dict(self) -> dict[str, Any]:
        return {n: getattr(self, n) for n in type(self)._fields}


# ---------------------------------------------------------------------------
# Version 3 — Model base with descriptors
# ---------------------------------------------------------------------------


class Field:
    """Base data descriptor. Subclasses override .validate."""

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
        self.max_length: int = max_length

    def validate(self, value: Any) -> None:
        _validate_str(self._name, value, self.max_length)


class IntField(Field):
    def __init__(self, min_value: int = 0, max_value: int = 2 ** 31 - 1) -> None:
        super().__init__()
        self.min_value: int = min_value
        self.max_value: int = max_value

    def validate(self, value: Any) -> None:
        _validate_int(self._name, value, self.min_value, self.max_value)


class ModelDescriptor:
    """Version 3: inherit; declare class-level Field descriptors."""

    _fields: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        names: list[str] = []
        for klass in reversed(cls.__mro__):
            for attr_name, attr_value in vars(klass).items():
                if isinstance(attr_value, Field) and attr_name not in names:
                    names.append(attr_name)
        cls._fields = tuple(names)

    def __init__(self, **kwargs: Any) -> None:
        names: tuple[str, ...] = type(self)._fields
        missing: list[str] = [n for n in names if n not in kwargs]
        if missing:
            raise TypeError(f"{type(self).__name__}: missing arguments: {missing!r}")
        extras: list[str] = [k for k in kwargs if k not in names]
        if extras:
            raise TypeError(f"{type(self).__name__}: unexpected arguments: {extras!r}")
        for name in names:
            setattr(self, name, kwargs[name])  # routes through descriptor __set__

    def __repr__(self) -> str:
        parts: list[str] = [f"{n}={getattr(self, n)!r}" for n in type(self)._fields]
        return f"{type(self).__name__}({', '.join(parts)})"

    def to_dict(self) -> dict[str, Any]:
        return {n: getattr(self, n) for n in type(self)._fields}


# ---------------------------------------------------------------------------
# Version 4 — Model with a metaclass
# ---------------------------------------------------------------------------


class ModelMeta(type):
    """Metaclass that harvests __field_specs__ from the namespace."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        # Merge inherited specs with newly declared ones.
        inherited: dict[str, _FieldSpec] = {}
        for base in reversed(bases):
            inherited.update(getattr(base, "_specs", {}))
        new: dict[str, _FieldSpec] = dict(namespace.get("__field_specs__", {}))
        inherited.update(new)
        namespace["_specs"] = inherited
        namespace["_fields"] = tuple(inherited.keys())
        return super().__new__(mcs, name, bases, namespace)


class ModelMetaclass(metaclass=ModelMeta):
    """Version 4: declare __field_specs__; the metaclass harvests."""

    _fields: ClassVar[tuple[str, ...]] = ()
    _specs: ClassVar[dict[str, _FieldSpec]] = {}

    def __init__(self, **kwargs: Any) -> None:
        specs: dict[str, _FieldSpec] = type(self)._specs
        field_names: tuple[str, ...] = type(self)._fields
        missing: list[str] = [n for n in field_names if n not in kwargs]
        if missing:
            raise TypeError(f"{type(self).__name__}: missing arguments: {missing!r}")
        extras: list[str] = [k for k in kwargs if k not in specs]
        if extras:
            raise TypeError(f"{type(self).__name__}: unexpected arguments: {extras!r}")
        for name in field_names:
            value: Any = kwargs[name]
            specs[name].validate(name, value)
            setattr(self, name, value)

    def __repr__(self) -> str:
        parts: list[str] = [f"{n}={getattr(self, n)!r}" for n in type(self)._fields]
        return f"{type(self).__name__}({', '.join(parts)})"

    def to_dict(self) -> dict[str, Any]:
        return {n: getattr(self, n) for n in type(self)._fields}


# ---------------------------------------------------------------------------
# Concrete classes — one per mechanism, identical shape
# ---------------------------------------------------------------------------


@validated_model
class UserDecorator:
    __field_specs__ = {
        "name": _FieldSpec(str, max_length=50),
        "age": _FieldSpec(int, min_value=0, max_value=150),
    }


class UserInitSubclass(ModelInitSubclass):
    __field_specs__ = {
        "name": _FieldSpec(str, max_length=50),
        "age": _FieldSpec(int, min_value=0, max_value=150),
    }


class UserDescriptor(ModelDescriptor):
    name = StringField(max_length=50)
    age = IntField(min_value=0, max_value=150)


class UserMetaclass(ModelMetaclass):
    __field_specs__ = {
        "name": _FieldSpec(str, max_length=50),
        "age": _FieldSpec(int, min_value=0, max_value=150),
    }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def bench_instance_creation(cls: type, iterations: int) -> float:
    """Return microseconds per instance creation."""
    timer = timeit.Timer(
        stmt="cls(name='alice', age=30)",
        globals={"cls": cls},
    )
    total: float = timer.timeit(number=iterations)
    return (total / iterations) * 1_000_000


def bench_attribute_set(cls: type, iterations: int) -> float:
    """Return microseconds per attribute set."""
    instance = cls(name="alice", age=30)
    timer = timeit.Timer(
        stmt="instance.age = 50",
        globals={"instance": instance},
    )
    total: float = timer.timeit(number=iterations)
    return (total / iterations) * 1_000_000


def bench_memory_per_instance(cls: type, count: int) -> float:
    """Return bytes per instance via tracemalloc."""
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    instances: list[Any] = [cls(name=f"u{i:04d}", age=i % 100) for i in range(count)]
    after = tracemalloc.take_snapshot()
    diff = after.compare_to(before, "filename")
    total_bytes: int = sum(d.size_diff for d in diff)
    tracemalloc.stop()
    _ = instances  # keep alive until snapshot was taken
    return total_bytes / count


def main() -> None:
    """Run the benchmark across all four implementations."""
    print("Validated-model library benchmark")
    print("=" * 70)
    print(f"{'metric':<28}{'Decorator':>12}{'InitSubcls':>12}"
          f"{'Descriptor':>12}{'Metaclass':>12}")
    print("-" * 70)

    classes: dict[str, type] = {
        "Decorator": UserDecorator,
        "InitSubclass": UserInitSubclass,
        "Descriptor": UserDescriptor,
        "Metaclass": UserMetaclass,
    }

    # instance creation
    create_times: dict[str, float] = {
        label: bench_instance_creation(cls, 10_000) for label, cls in classes.items()
    }
    print(
        f"{'instance create (microsec)':<28}"
        f"{create_times['Decorator']:>12.3f}"
        f"{create_times['InitSubclass']:>12.3f}"
        f"{create_times['Descriptor']:>12.3f}"
        f"{create_times['Metaclass']:>12.3f}"
    )

    # attribute set
    set_times: dict[str, float] = {
        label: bench_attribute_set(cls, 100_000) for label, cls in classes.items()
    }
    print(
        f"{'attribute set (microsec)':<28}"
        f"{set_times['Decorator']:>12.3f}"
        f"{set_times['InitSubclass']:>12.3f}"
        f"{set_times['Descriptor']:>12.3f}"
        f"{set_times['Metaclass']:>12.3f}"
    )

    # memory per instance
    mem: dict[str, float] = {
        label: bench_memory_per_instance(cls, 2_000) for label, cls in classes.items()
    }
    print(
        f"{'bytes per instance':<28}"
        f"{mem['Decorator']:>12.1f}"
        f"{mem['InitSubclass']:>12.1f}"
        f"{mem['Descriptor']:>12.1f}"
        f"{mem['Metaclass']:>12.1f}"
    )

    print("-" * 70)
    print("Interpretation: the differences are typically within 2x for "
          "instance creation,")
    print("close to identical for attribute set (descriptor has slight overhead "
          "from __set__),")
    print("and within ~15% for memory per instance. For most applications "
          "this is noise.")
    print("The cost that does matter is type-checker friction (Metaclass loses "
          "without PEP 681)")
    print("and inheritance ergonomics (Decorator loses without re-decoration).")


if __name__ == "__main__":
    main()
