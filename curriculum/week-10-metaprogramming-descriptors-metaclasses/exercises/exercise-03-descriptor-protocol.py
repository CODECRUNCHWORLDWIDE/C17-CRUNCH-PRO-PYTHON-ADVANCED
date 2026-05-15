"""
Exercise 3 — Reimplement property, classmethod, staticmethod, cached_property
            from scratch as Python descriptors.

Goal: build pure-Python equivalents of the four canonical descriptors. Verify
behaviour matches the built-ins. Read Hettinger's HowTo before you start.

Citations:
    - Descriptor HowTo Guide — https://docs.python.org/3/howto/descriptor.html
    - Data model section 3.3.2.4 (descriptors) — https://docs.python.org/3/reference/datamodel.html#implementing-descriptors
    - Lib/functools.py (cached_property) — https://github.com/python/cpython/blob/main/Lib/functools.py

Run:
    python3 exercise-03-descriptor-protocol.py

Compile-check:
    python3 -m py_compile exercise-03-descriptor-protocol.py
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable


class Property:
    """Pure-Python property. Data descriptor (defines __set__)."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any, Any], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        doc: str | None = None,
    ) -> None:
        self.fget: Callable[[Any], Any] | None = fget
        self.fset: Callable[[Any, Any], None] | None = fset
        self.fdel: Callable[[Any], None] | None = fdel
        self.__doc__: str | None = doc or (fget.__doc__ if fget else None)
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


class ClassMethod:
    """Pure-Python classmethod. Non-data descriptor (only __get__)."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func: Callable[..., Any] = func

    def __set_name__(self, owner: type, name: str) -> None:
        self._name: str = name

    def __get__(self, instance: Any, owner: type | None = None) -> Callable[..., Any]:
        if owner is None:
            owner = type(instance)
        return partial(self.func, owner)


class StaticMethod:
    """Pure-Python staticmethod. Non-data descriptor (only __get__)."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func: Callable[..., Any] = func

    def __set_name__(self, owner: type, name: str) -> None:
        self._name: str = name

    def __get__(self, instance: Any, owner: type | None = None) -> Callable[..., Any]:
        return self.func


class CachedProperty:
    """Pure-Python cached_property.

    Non-data descriptor that writes the computed value into instance.__dict__
    on first access; the instance dict then shadows the descriptor on
    subsequent access, so the function runs exactly once per instance.
    """

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self.func: Callable[[Any], Any] = func
        self.__doc__: str | None = func.__doc__
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        if not self._name:
            self._name = name
        elif self._name != name:
            raise TypeError(
                f"CachedProperty assigned to two names: "
                f"{self._name!r} and {name!r}"
            )

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        if self._name not in instance.__dict__:
            instance.__dict__[self._name] = self.func(instance)
        return instance.__dict__[self._name]


def main() -> None:
    """Exercise each descriptor and compare to the stdlib equivalents."""

    # --- Property ---
    class Celsius:
        def __init__(self, value: float) -> None:
            self._value: float = value

        @Property
        def value(self) -> float:
            return self._value

        @value.setter
        def value(self, new: float) -> None:
            if new < -273.15:
                raise ValueError("below absolute zero")
            self._value = new

    c = Celsius(25.0)
    print("Property:")
    print(f"  c.value = {c.value}")
    c.value = 30.0
    print(f"  after set, c.value = {c.value}")
    try:
        c.value = -300.0
    except ValueError as exc:
        print(f"  guard caught: {exc}")

    # --- ClassMethod ---
    class Counter:
        count: int = 0

        @ClassMethod
        def bump(cls) -> int:
            cls.count += 1
            return cls.count

    print("ClassMethod:")
    print(f"  bump -> {Counter.bump()}")
    print(f"  bump -> {Counter.bump()}")
    print(f"  Counter.count = {Counter.count}")

    # --- StaticMethod ---
    class MathUtils:
        @StaticMethod
        def square(x: int) -> int:
            return x * x

    print("StaticMethod:")
    print(f"  MathUtils.square(7) = {MathUtils.square(7)}")
    inst = MathUtils()
    print(f"  inst.square(8) = {inst.square(8)}")

    # --- CachedProperty ---
    class Expensive:
        def __init__(self, base: int) -> None:
            self.base: int = base
            self.calls: int = 0

        @CachedProperty
        def computed(self) -> int:
            self.calls += 1
            return self.base ** 2

    e = Expensive(5)
    print("CachedProperty:")
    print(f"  first access: {e.computed} (calls={e.calls})")
    print(f"  second access: {e.computed} (calls={e.calls})")
    print(f"  third access: {e.computed} (calls={e.calls})")
    # __dict__ now contains the cached value:
    print(f"  'computed' in e.__dict__ = {'computed' in e.__dict__}")


if __name__ == "__main__":
    main()
