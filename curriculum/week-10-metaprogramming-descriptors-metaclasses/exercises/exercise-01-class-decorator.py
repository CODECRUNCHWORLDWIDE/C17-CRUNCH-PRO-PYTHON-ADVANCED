"""
Exercise 1 — Write @validated_model from scratch as a class decorator.

Goal: build the simplest of the four implementations. Read the class's
__annotations__, generate an __init__ that validates, generate a __repr__,
return the (mutated) class. About 80 lines.

Steps:
    1. Implement validated_model(cls) using the spec in the docstring.
    2. Run this file. It exercises the decorator on three example classes.
    3. Compare the runtime errors with the comments alongside each test case.
    4. Read SOLUTIONS.md for the reference implementation and discussion.

Cite:
    - PEP 557 (dataclasses) — https://peps.python.org/pep-0557/
    - dataclasses source — Lib/dataclasses.py, function _process_class
    - PEP 681 (dataclass_transform) — https://peps.python.org/pep-0681/

Run:
    python3 exercise-01-class-decorator.py

Compile-check (no execution):
    python3 -m py_compile exercise-01-class-decorator.py
"""

from typing import Any, Callable, TypeVar

T = TypeVar("T", bound=type)


def validated_model(cls: T) -> T:
    """Decorate a class so that instances validate annotated fields.

    The decorator:
        - Reads cls.__annotations__ to discover the declared fields.
        - Generates an __init__(self, **kwargs) that requires every annotated
          field as a keyword argument, type-checks it against the annotation,
          and applies a small set of built-in validators (int >= 0, str <= 256
          characters) consistent with the lecture's spec.
        - Generates a __repr__(self) that prints the field values.
        - Attaches a class-level _fields tuple for introspection.
        - Returns the same class object (so isinstance and type-checker
          inference both keep working).

    Bugs to avoid:
        - Returning a new class (breaks isinstance for existing references).
        - Mutating annotations (the dict you read is shared; do not write to it).
        - Failing to raise on missing kwargs (silently leaves attributes unset).
        - Failing to raise on extra kwargs (silently accepts misspelt fields;
          the reference accepts this for simplicity, but mark it as a TODO).
    """
    annotations: dict[str, type] = dict(getattr(cls, "__annotations__", {}))
    field_names: list[str] = list(annotations.keys())

    def __init__(self: Any, **kwargs: Any) -> None:
        missing: list[str] = [n for n in field_names if n not in kwargs]
        if missing:
            raise TypeError(
                f"{cls.__name__}: missing required arguments: {missing!r}"
            )
        extras: list[str] = [k for k in kwargs if k not in annotations]
        if extras:
            raise TypeError(
                f"{cls.__name__}: unexpected arguments: {extras!r}"
            )
        for name in field_names:
            value: Any = kwargs[name]
            expected: type = annotations[name]
            if not isinstance(value, expected):
                raise TypeError(
                    f"{cls.__name__}.{name}: expected {expected.__name__}, "
                    f"got {type(value).__name__}"
                )
            if expected is int and value < 0:
                raise ValueError(f"{cls.__name__}.{name}: must be >= 0")
            if expected is str and len(value) > 256:
                raise ValueError(
                    f"{cls.__name__}.{name}: must be <= 256 characters"
                )
            setattr(self, name, value)

    def __repr__(self: Any) -> str:
        parts: list[str] = [f"{n}={getattr(self, n)!r}" for n in field_names]
        return f"{cls.__name__}({', '.join(parts)})"

    cls.__init__ = __init__  # type: ignore[method-assign]
    cls.__repr__ = __repr__  # type: ignore[method-assign]
    cls._fields = tuple(field_names)  # type: ignore[attr-defined]
    return cls


def expect(label: str, predicate: Callable[[], None]) -> None:
    """Run a callable and report whether it raised, and how."""
    try:
        predicate()
    except (TypeError, ValueError) as exc:
        print(f"  {label}: raised {type(exc).__name__}: {exc}")
    else:
        print(f"  {label}: returned normally")


def main() -> None:
    """Drive the decorator against three example classes."""

    @validated_model
    class User:
        name: str
        age: int

    @validated_model
    class Product:
        sku: str
        price: int

    @validated_model
    class Empty:
        pass

    # --- happy paths ---
    print("happy paths:")
    u = User(name="alice", age=30)
    print(f"  {u!r}")
    p = Product(sku="abc-123", price=499)
    print(f"  {p!r}")
    e = Empty()
    print(f"  {e!r}")

    # --- validation failures ---
    print("validation failures:")
    expect(
        "User(missing age)",
        lambda: User(name="bob"),  # type: ignore[call-arg]
    )
    expect(
        "User(extra kwarg)",
        lambda: User(name="bob", age=20, role="admin"),  # type: ignore[call-arg]
    )
    expect(
        "User(wrong type)",
        lambda: User(name=123, age=30),  # type: ignore[arg-type]
    )
    expect(
        "User(negative age)",
        lambda: User(name="carol", age=-1),
    )
    expect(
        "Product(too-long sku)",
        lambda: Product(sku="x" * 300, price=10),
    )

    # --- introspection ---
    print("introspection:")
    print(f"  User._fields = {User._fields}")  # type: ignore[attr-defined]
    print(f"  Product._fields = {Product._fields}")  # type: ignore[attr-defined]
    print(f"  isinstance(u, User) = {isinstance(u, User)}")


if __name__ == "__main__":
    main()
