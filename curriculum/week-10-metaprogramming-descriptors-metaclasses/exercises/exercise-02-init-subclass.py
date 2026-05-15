"""
Exercise 2 — Use __init_subclass__ for plugin-style subclass registration.

Goal: build a base class that auto-registers every subclass into a global
registry keyed by a 'plugin_name' keyword passed in the class statement.
Demonstrate __set_name__ on a label descriptor that learns its own attribute
name at class-creation time. About 90 lines.

Topics:
    - __init_subclass__(cls, **kwargs) signature and the cooperative
      super().__init_subclass__(**kwargs) call.
    - Extra keyword arguments in the class statement
      (class Foo(Base, plugin_name="my-plugin"): ...).
    - __set_name__(self, owner, name) for descriptors that need to know their
      attribute name.

Cite:
    - PEP 487 — https://peps.python.org/pep-0487/
    - Data model section 3.3.3 — https://docs.python.org/3/reference/datamodel.html#customizing-class-creation

Run:
    python3 exercise-02-init-subclass.py

Compile-check:
    python3 -m py_compile exercise-02-init-subclass.py
"""

from __future__ import annotations

from typing import Any, ClassVar


class Label:
    """A tiny descriptor that learns its own attribute name via __set_name__."""

    def __init__(self, prefix: str = "") -> None:
        self.prefix: str = prefix
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type | None = None) -> str:
        if instance is None:
            return f"<Label name={self._name!r} prefix={self.prefix!r}>"
        return f"{self.prefix}{self._name}"


class Plugin:
    """Base class that registers every subclass under a 'plugin_name' kwarg."""

    _registry: ClassVar[dict[str, type[Plugin]]] = {}

    def __init_subclass__(cls, *, plugin_name: str | None = None, **kwargs: Any) -> None:
        # Always forward; cooperative multiple inheritance depends on it.
        super().__init_subclass__(**kwargs)
        if plugin_name is None:
            raise TypeError(
                f"{cls.__name__}: must provide plugin_name= keyword argument"
            )
        if plugin_name in Plugin._registry:
            existing: type[Plugin] = Plugin._registry[plugin_name]
            raise ValueError(
                f"plugin_name {plugin_name!r} already registered by "
                f"{existing.__name__}"
            )
        Plugin._registry[plugin_name] = cls
        cls.plugin_name = plugin_name  # type: ignore[attr-defined]


def expect_typeerror(label: str, factory: Any) -> None:
    """Run a no-arg factory and report whether it raised TypeError."""
    try:
        factory()
    except TypeError as exc:
        print(f"  {label}: raised TypeError: {exc}")
    except ValueError as exc:
        print(f"  {label}: raised ValueError: {exc}")
    else:
        print(f"  {label}: returned normally")


def main() -> None:
    """Demonstrate subclass registration and __set_name__."""

    class JsonExporter(Plugin, plugin_name="json"):
        label = Label(prefix="json:")

        def export(self, data: Any) -> str:
            return f"json export of {data!r}"

    class CsvExporter(Plugin, plugin_name="csv"):
        label = Label(prefix="csv:")
        header = Label(prefix="hdr:")

        def export(self, data: Any) -> str:
            return f"csv export of {data!r}"

    # --- registry contents ---
    print("registry:")
    for name, cls in sorted(Plugin._registry.items()):
        print(f"  {name!r:>10} -> {cls.__name__}")

    # --- __set_name__ assigned correctly ---
    j = JsonExporter()
    c = CsvExporter()
    print("descriptor names:")
    print(f"  JsonExporter.label = {j.label}")           # 'json:label'
    print(f"  CsvExporter.label  = {c.label}")           # 'csv:label'
    print(f"  CsvExporter.header = {c.header}")          # 'hdr:header'

    # --- duplicate registration is rejected ---
    print("error paths:")

    def define_duplicate() -> None:
        class DupExporter(Plugin, plugin_name="json"):
            pass

    expect_typeerror("duplicate plugin_name", define_duplicate)

    def define_missing() -> None:
        class Anonymous(Plugin):  # forgot plugin_name=
            pass

    expect_typeerror("missing plugin_name", define_missing)

    # --- cooperative __init_subclass__ with extra mixin ---
    class CountingMixin:
        _count: ClassVar[int] = 0

        def __init_subclass__(cls, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            CountingMixin._count += 1

    class XmlExporter(CountingMixin, Plugin, plugin_name="xml"):
        pass

    print("cooperative chain:")
    print(f"  CountingMixin._count after XmlExporter = {CountingMixin._count}")
    print(f"  XmlExporter.plugin_name = {XmlExporter.plugin_name}")


if __name__ == "__main__":
    main()
