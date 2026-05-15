"""
Mini-project test suite — one suite, four implementations, all pass.

This file imports the four versions of the User model from benchmark.py
and runs the same nine tests against each. Pass criterion is documented
in the mini-project README; in short, every implementation must behave
identically from the caller's perspective.

Run:
    python3 test_all.py

The script returns exit code 0 on full pass, 1 on any failure. The output
labels each test by mechanism and by case number; failures print the
mismatch.

Citations:
    - PEP 487  — https://peps.python.org/pep-0487/
    - PEP 557  — https://peps.python.org/pep-0557/
    - Descriptor HowTo — https://docs.python.org/3/howto/descriptor.html
    - Data model — https://docs.python.org/3/reference/datamodel.html

Compile-check:
    python3 -m py_compile test_all.py
"""

import sys
from typing import Any, Callable

from benchmark import (
    UserDecorator,
    UserInitSubclass,
    UserDescriptor,
    UserMetaclass,
    ModelInitSubclass,
    ModelDescriptor,
    ModelMetaclass,
    StringField,
    IntField,
    _FieldSpec,
    validated_model,
)


PASS: int = 0
FAIL: int = 0


def check(label: str, predicate: Callable[[], Any], expected: Any = True) -> None:
    """Run a no-arg predicate; mark pass/fail; log."""
    global PASS, FAIL
    try:
        result: Any = predicate()
    except BaseException as exc:  # noqa: BLE001
        print(f"  FAIL: {label}: raised {type(exc).__name__}: {exc}")
        FAIL += 1
        return
    if result == expected:
        print(f"  pass: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}: got {result!r}, expected {expected!r}")
        FAIL += 1


def check_raises(label: str, predicate: Callable[[], Any], exc_type: type) -> None:
    """Run a no-arg predicate; pass only if it raises exc_type."""
    global PASS, FAIL
    try:
        predicate()
    except exc_type:
        print(f"  pass: {label}")
        PASS += 1
    except BaseException as exc:  # noqa: BLE001
        print(
            f"  FAIL: {label}: raised wrong type "
            f"{type(exc).__name__} (wanted {exc_type.__name__}): {exc}"
        )
        FAIL += 1
    else:
        print(f"  FAIL: {label}: did not raise")
        FAIL += 1


def section(title: str) -> None:
    print()
    print(f"=== {title} ===")


def run_basic_tests(label: str, cls: type) -> None:
    """Tests 1-7 from the README spec, against any of the four classes."""

    section(f"Basic tests — {label}")

    # Test 1: happy path
    check(
        "happy path: u.name",
        lambda: cls(name="alice", age=30).name,
        "alice",
    )
    check(
        "happy path: u.age",
        lambda: cls(name="alice", age=30).age,
        30,
    )

    # Test 2: missing field
    check_raises(
        "missing field",
        lambda: cls(name="alice"),
        TypeError,
    )

    # Test 3: type error
    check_raises(
        "type error on name",
        lambda: cls(name=123, age=30),
        TypeError,
    )

    # Test 4: out of range
    check_raises(
        "negative age",
        lambda: cls(name="alice", age=-1),
        ValueError,
    )
    check_raises(
        "age above max",
        lambda: cls(name="alice", age=200),
        ValueError,
    )

    # Test 5: string too long
    check_raises(
        "name too long",
        lambda: cls(name="x" * 1000, age=30),
        ValueError,
    )

    # Test 6: repr
    check(
        "repr shape",
        lambda: repr(cls(name="alice", age=30)),
        f"{cls.__name__}(name='alice', age=30)",
    )

    # Test 7: to_dict
    check(
        "to_dict",
        lambda: cls(name="alice", age=30).to_dict(),
        {"name": "alice", "age": 30},
    )

    # Test 9 (introspection)
    check(
        "_fields tuple",
        lambda: cls._fields,
        ("name", "age"),
    )


def run_inheritance_tests() -> None:
    """Test 8: inheritance. Each mechanism is tested separately because the
    'how' differs significantly across them."""

    section("Inheritance — Decorator (re-decoration required)")

    @validated_model
    class AdminDecorator(UserDecorator):
        # The decorator does not re-run; we have to override __field_specs__.
        __field_specs__ = {
            "name": _FieldSpec(str, max_length=50),
            "age": _FieldSpec(int, min_value=0, max_value=150),
            "role": _FieldSpec(str, max_length=20),
        }

    check(
        "decorator subclass: name",
        lambda: AdminDecorator(name="bob", age=40, role="root").name,
        "bob",
    )
    check(
        "decorator subclass: role",
        lambda: AdminDecorator(name="bob", age=40, role="root").role,
        "root",
    )

    section("Inheritance — InitSubclass (natural)")

    class AdminInitSubclass(UserInitSubclass):
        __field_specs__ = {
            "role": _FieldSpec(str, max_length=20),
        }

    check(
        "init_subclass subclass: name (inherited spec)",
        lambda: AdminInitSubclass(name="bob", age=40, role="root").name,
        "bob",
    )
    check(
        "init_subclass subclass: role",
        lambda: AdminInitSubclass(name="bob", age=40, role="root").role,
        "root",
    )
    check(
        "init_subclass subclass: _fields includes inherited",
        lambda: AdminInitSubclass._fields,
        ("name", "age", "role"),
    )

    section("Inheritance — Descriptor (natural)")

    class AdminDescriptor(UserDescriptor):
        role = StringField(max_length=20)

    check(
        "descriptor subclass: name",
        lambda: AdminDescriptor(name="bob", age=40, role="root").name,
        "bob",
    )
    check(
        "descriptor subclass: role",
        lambda: AdminDescriptor(name="bob", age=40, role="root").role,
        "root",
    )
    check_raises(
        "descriptor subclass: role too long",
        lambda: AdminDescriptor(name="bob", age=40, role="x" * 100),
        ValueError,
    )
    check(
        "descriptor subclass: _fields",
        lambda: AdminDescriptor._fields,
        ("name", "age", "role"),
    )

    section("Inheritance — Metaclass (works; conflicts under mixing)")

    class AdminMetaclass(UserMetaclass):
        __field_specs__ = {
            "role": _FieldSpec(str, max_length=20),
        }

    check(
        "metaclass subclass: name",
        lambda: AdminMetaclass(name="bob", age=40, role="root").name,
        "bob",
    )
    check(
        "metaclass subclass: role",
        lambda: AdminMetaclass(name="bob", age=40, role="root").role,
        "root",
    )
    check(
        "metaclass subclass: _fields",
        lambda: AdminMetaclass._fields,
        ("name", "age", "role"),
    )


def run_no_shared_state_tests() -> None:
    """Catches the most common descriptor bug — class-shared instance state."""

    section("No-shared-state tests — Descriptor")

    u1 = UserDescriptor(name="alice", age=30)
    u2 = UserDescriptor(name="bob", age=40)
    check("two instances: u1.name", lambda: u1.name, "alice")
    check("two instances: u2.name", lambda: u2.name, "bob")
    check("two instances: u1.age", lambda: u1.age, 30)
    check("two instances: u2.age", lambda: u2.age, 40)
    u1.age = 31
    check("after mutation: u1.age", lambda: u1.age, 31)
    check("after mutation: u2.age unchanged", lambda: u2.age, 40)


def main() -> int:
    """Run the suite. Exit code 0 on full pass."""
    for label, cls in [
        ("Decorator", UserDecorator),
        ("InitSubclass", UserInitSubclass),
        ("Descriptor", UserDescriptor),
        ("Metaclass", UserMetaclass),
    ]:
        run_basic_tests(label, cls)

    run_inheritance_tests()
    run_no_shared_state_tests()

    print()
    print("=" * 50)
    print(f"PASS: {PASS}   FAIL: {FAIL}")
    print("=" * 50)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
