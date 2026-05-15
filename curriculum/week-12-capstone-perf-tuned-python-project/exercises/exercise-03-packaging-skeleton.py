"""Exercise 03 — Generate a packaging skeleton.

Goal: programmatically generate the minimum-viable `pyproject.toml` plus
`src/` layout for a capstone package, write it to a temporary directory,
verify it parses with `tomllib`, and (optionally) verify that
`python -m build` succeeds against it.

The script does not require network access. It does not upload anywhere.
It is a *dry run* of Friday's packaging work, so you understand what the
files look like before you fill them in for your own kernel.

Run:
    python3 exercise-03-packaging-skeleton.py

References:
    - PEP 517, PEP 518, PEP 621.
    - https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
"""

from __future__ import annotations

import os
import sys
import tempfile
import tomllib
from pathlib import Path


PYPROJECT_TEMPLATE: str = '''\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{distribution_name}"
version = "{version}"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = {{ text = "MIT" }}
authors = [
    {{ name = "{author_name}", email = "{author_email}" }},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "numpy>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://example.invalid/{distribution_name}"

[tool.hatch.build.targets.wheel]
packages = ["src/{import_name}"]
'''

README_TEMPLATE: str = '''\
# {distribution_name}

{description}

## Installation

```bash
pip install --index-url https://test.pypi.org/simple/ \\
            --extra-index-url https://pypi.org/simple/ \\
            {distribution_name}
```

## Usage

```python
from {import_name} import hello
print(hello())
```

## License

MIT
'''

INIT_TEMPLATE: str = '''\
"""{distribution_name} — generated skeleton."""

from __future__ import annotations

__version__: str = "{version}"
__all__: list[str] = ["hello"]


def hello() -> str:
    """Return a greeting. Used by tests to verify the package installed."""
    return "Hello from {distribution_name} {version}"
'''

LICENSE_TEMPLATE: str = '''\
MIT License

Copyright (c) 2026 {author_name}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
'''


def generate_skeleton(
    parent: Path,
    distribution_name: str,
    import_name: str,
    version: str,
    description: str,
    author_name: str,
    author_email: str,
) -> Path:
    """Generate the package skeleton under `parent`. Return the project root."""
    root: Path = parent / distribution_name
    root.mkdir()

    fields: dict[str, str] = {
        "distribution_name": distribution_name,
        "import_name": import_name,
        "version": version,
        "description": description,
        "author_name": author_name,
        "author_email": author_email,
    }

    (root / "pyproject.toml").write_text(PYPROJECT_TEMPLATE.format(**fields))
    (root / "README.md").write_text(README_TEMPLATE.format(**fields))
    (root / "LICENSE").write_text(LICENSE_TEMPLATE.format(**fields))

    pkg_dir: Path = root / "src" / import_name
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text(INIT_TEMPLATE.format(**fields))
    (pkg_dir / "py.typed").write_text("")  # PEP 561 marker

    return root


def validate_pyproject(root: Path) -> dict[str, object]:
    """Parse pyproject.toml and assert the required sections are present."""
    with (root / "pyproject.toml").open("rb") as f:
        data: dict[str, object] = tomllib.load(f)
    assert "build-system" in data, "missing [build-system]"
    assert "project" in data, "missing [project]"
    project: dict[str, object] = data["project"]  # type: ignore[assignment]
    for key in ("name", "version", "description", "readme", "requires-python"):
        assert key in project, f"missing [project].{key}"
    return data


def validate_layout(root: Path, import_name: str) -> None:
    """Assert the src/-layout is correct."""
    pkg_dir: Path = root / "src" / import_name
    assert pkg_dir.is_dir(), f"package directory {pkg_dir} missing"
    assert (pkg_dir / "__init__.py").is_file(), "__init__.py missing"
    assert (pkg_dir / "py.typed").is_file(), "py.typed missing (PEP 561)"
    assert (root / "README.md").is_file(), "README.md missing"
    assert (root / "LICENSE").is_file(), "LICENSE missing"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        parent: Path = Path(tmp)
        root: Path = generate_skeleton(
            parent=parent,
            distribution_name="cc-student-demo",
            import_name="cc_student_demo",
            version="0.1.0",
            description="A demo skeleton generated by C17 W12 exercise 03.",
            author_name="Capstone Student",
            author_email="student@example.invalid",
        )
        print(f"Generated skeleton at: {root}")

        data: dict[str, object] = validate_pyproject(root)
        print(f"pyproject.toml parsed; [project].name = "
              f"{data['project']['name']}")  # type: ignore[index]
        validate_layout(root, "cc_student_demo")
        print("Layout validated: src/cc_student_demo/{__init__.py, py.typed}")

        # Print the tree for the report.
        print("\nDirectory tree:")
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel: str = str(p.relative_to(root))
                size: int = p.stat().st_size
                print(f"  {rel} ({size} bytes)")

        # OPTIONAL: invoke `python -m build` to verify the toolchain works.
        # We do not run this by default because it requires `build` to be
        # installed and we do not want to break the exercise for students
        # who have not yet pip-installed it. Uncomment to try:
        #
        # import subprocess
        # try:
        #     subprocess.run(
        #         [sys.executable, "-m", "build", "--sdist", "--wheel",
        #          "--outdir", str(root / "dist"), str(root)],
        #         check=True,
        #     )
        #     print("\nBuild OK; check dist/.")
        # except (subprocess.CalledProcessError, FileNotFoundError) as e:
        #     print(f"\nBuild skipped or failed: {e}")
        #     print("To enable: pip install build")

    # tmpdir is auto-cleaned. The point of the exercise is to read the
    # files before they disappear; if you want to keep the output, change
    # `parent` above to a real path.


if __name__ == "__main__":
    sys.exit(main())
