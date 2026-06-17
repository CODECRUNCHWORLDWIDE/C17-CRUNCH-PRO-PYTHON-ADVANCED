"""
Exercise 4 — Metaclass basics, resolution order, and the metaclass conflict.

Goal: write a small metaclass; observe __new__ / __init__ / __call__ firing
order; trigger a metaclass conflict on multiple inheritance and resolve it
with a combined metaclass.

Topics:
    - type.__new__ vs. type.__init__.
    - __call__ on the metaclass intercepting class-level instantiation.
    - metaclass conflict on multiple inheritance and how to resolve it.

Cite:
    - PEP 3115 — https://peps.python.org/pep-3115/
    - Data model section 3.3.3 — https://docs.python.org/3/reference/datamodel.html#customizing-class-creation
    - Lib/abc.py (ABCMeta) — https://github.com/python/cpython/blob/main/Lib/abc.py
    - Lib/enum.py (EnumType) — https://github.com/python/cpython/blob/main/Lib/enum.py

Run:
    python3 exercise-04-metaclass-basics.py

Compile-check:
    python3 -m py_compile exercise-04-metaclass-basics.py
"""

from __future__ import annotations

from typing import Any


class TracingMeta(type):
    """A metaclass that prints each step of class and instance creation."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        print(f"  TracingMeta.__new__({name!r}, bases={[b.__name__ for b in bases]})")
        cls = super().__new__(mcs, name, bases, namespace)
        return cls

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        print(f"  TracingMeta.__init__({name!r})")
        super().__init__(name, bases, namespace)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        print(f"  TracingMeta.__call__({cls.__name__}, args={args}, kwargs={kwargs})")
        return super().__call__(*args, **kwargs)


class SingletonMeta(type):
    """A metaclass that returns the same instance across all calls."""

    _instances: dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]


def section(title: str) -> None:
    print()
    print(f"=== {title} ===")


def main() -> None:
    """Walk the metaclass lifecycle."""

    section("Class creation with TracingMeta")

    class Foo(metaclass=TracingMeta):
        x: int = 1

        def method(self) -> int:
            return self.x

    section("Instance creation with TracingMeta")
    f = Foo()
    print(f"  f.method() = {f.method()}")

    section("type(Foo) and type(type(Foo))")
    print(f"  type(Foo) = {type(Foo).__name__}")
    print(f"  type(type(Foo)) = {type(type(Foo)).__name__}")
    print(f"  type(Foo).__mro__ = {[t.__name__ for t in type(Foo).__mro__]}")

    section("SingletonMeta")

    class Config(metaclass=SingletonMeta):
        def __init__(self) -> None:
            self.created_at: str = "now"

    c1 = Config()
    c2 = Config()
    print(f"  c1 is c2 = {c1 is c2}")
    print(f"  id(c1) == id(c2) = {id(c1) == id(c2)}")

    section("Metaclass conflict")

    class MetaA(type):
        pass

    class MetaB(type):
        pass

    class A(metaclass=MetaA):
        pass

    class B(metaclass=MetaB):
        pass

    print("  attempting class C(A, B): with no combined metaclass...")
    try:
        # We construct the class dynamically because the static form
        # raises at class-statement evaluation, which would abort main().
        type("C", (A, B), {})
    except TypeError as exc:
        print(f"  TypeError: {exc}")

    section("Resolving the conflict with a combined metaclass")

    class MetaAB(MetaA, MetaB):
        pass

    C = type.__call__(MetaAB, "C", (A, B), {})
    print(f"  resolved: type(C) = {type(C).__name__}")
    print(f"  resolved: MRO of type(C) = {[t.__name__ for t in type(C).__mro__]}")


if __name__ == "__main__":
    main()
