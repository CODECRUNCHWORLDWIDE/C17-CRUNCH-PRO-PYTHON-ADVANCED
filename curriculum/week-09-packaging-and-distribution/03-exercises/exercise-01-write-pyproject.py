"""
Exercise 1 — Parse, validate, and emit a pyproject.toml metadata report.

Goal: build the muscle of reading pyproject.toml. You will parse the
sample file shipped in this directory, validate it against PEP 518 + 621
required fields, and emit a human-readable report that names every
backend, every dependency, every entry point, every classifier.

You will also generate a new pyproject.toml from a template, parameterised
by the package name and a few metadata bits. The generated file must parse
back to the same in-memory representation (round-trip property).

References:
  - PEP 517: <https://peps.python.org/pep-0517/>
  - PEP 518: <https://peps.python.org/pep-0518/>
  - PEP 621: <https://peps.python.org/pep-0621/>
  - tomllib: <https://docs.python.org/3/library/tomllib.html>
  - packaging.python.org pyproject.toml spec:
      <https://packaging.python.org/en/latest/specifications/pyproject-toml/>

Run:
  python3 exercise-01-write-pyproject.py exercise-01-sample-pyproject.toml

Validate:
  python3 -m py_compile exercise-01-write-pyproject.py
  python3 -c "import tomllib; tomllib.load(open('exercise-01-sample-pyproject.toml','rb'))"
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any


# PEP 621-required fields (the minimum a valid [project] table must have).
# Source: <https://peps.python.org/pep-0621/#name> and #version.
PEP_621_REQUIRED: frozenset[str] = frozenset({"name"})

# PEP 621-recommended (not required but every published package should set them).
PEP_621_RECOMMENDED: frozenset[str] = frozenset({
    "version",
    "description",
    "readme",
    "requires-python",
    "license",
    "authors",
    "classifiers",
    "dependencies",
    "urls",
})

# Known PEP 517 build backends with their `build-backend` identifiers.
# Source: each backend's documentation.
KNOWN_BACKENDS: dict[str, str] = {
    "setuptools.build_meta": "setuptools",
    "setuptools.build_meta:__legacy__": "setuptools (legacy)",
    "hatchling.build": "hatchling",
    "flit_core.buildapi": "flit-core",
    "pdm.backend": "pdm-backend",
    "poetry.core.masonry.api": "poetry-core",
    "uv_build": "uv_build",
    "maturin": "maturin",
    "scikit_build_core.build": "scikit-build-core",
    "mesonpy": "meson-python",
}


def parse_pyproject(path: Path) -> dict[str, Any]:
    """Read a pyproject.toml from disk; return the parsed dict.

    Uses tomllib (stdlib since 3.11). Raises FileNotFoundError or
    tomllib.TOMLDecodeError on failure.
    """
    with open(path, "rb") as f:
        return tomllib.load(f)


def validate_build_system(toml: dict[str, Any]) -> list[str]:
    """Validate the [build-system] table per PEP 518.

    Returns a list of human-readable validation findings (empty if valid).
    """
    findings: list[str] = []
    bs = toml.get("build-system")
    if bs is None:
        findings.append("[build-system] missing — required by PEP 518.")
        return findings
    if not isinstance(bs, dict):
        findings.append("[build-system] must be a table.")
        return findings
    if "requires" not in bs:
        findings.append("[build-system].requires missing — required by PEP 518.")
    elif not isinstance(bs["requires"], list):
        findings.append("[build-system].requires must be a list of strings.")
    if "build-backend" not in bs:
        findings.append(
            "[build-system].build-backend missing — required by PEP 517 "
            "(may be omitted for legacy setuptools only)."
        )
    return findings


def validate_project(toml: dict[str, Any]) -> list[str]:
    """Validate the [project] table per PEP 621.

    Returns a list of human-readable validation findings (empty if valid).
    """
    findings: list[str] = []
    proj = toml.get("project")
    if proj is None:
        findings.append("[project] missing — required by PEP 621.")
        return findings
    if not isinstance(proj, dict):
        findings.append("[project] must be a table.")
        return findings
    dyn = set(proj.get("dynamic", []))
    for required in PEP_621_REQUIRED:
        if required not in proj and required not in dyn:
            findings.append(
                f"[project].{required} missing and not in dynamic — "
                f"required by PEP 621."
            )
    if "version" not in proj and "version" not in dyn:
        findings.append(
            "[project].version missing — must be present or listed in "
            "[project].dynamic (e.g. derived from setuptools_scm or hatch-vcs)."
        )
    for recommended in PEP_621_RECOMMENDED:
        if recommended in proj or recommended in dyn:
            continue
        findings.append(
            f"[project].{recommended} not set — recommended for any "
            f"published package."
        )
    return findings


def identify_backend(toml: dict[str, Any]) -> str:
    """Return a human-readable build backend identifier."""
    bs = toml.get("build-system", {})
    backend_id = bs.get("build-backend", "<unset>")
    return KNOWN_BACKENDS.get(backend_id, f"{backend_id} (unknown)")


def summarise_project(toml: dict[str, Any]) -> dict[str, Any]:
    """Produce a structured summary of the [project] table for the report."""
    proj = toml.get("project", {})
    summary: dict[str, Any] = {
        "name": proj.get("name", "<unset>"),
        "version": proj.get("version", "<dynamic>" if "version" in proj.get("dynamic", []) else "<unset>"),
        "description": proj.get("description", "<unset>"),
        "requires-python": proj.get("requires-python", "<unset>"),
        "license": proj.get("license", "<unset>"),
        "n_authors": len(proj.get("authors", [])),
        "n_classifiers": len(proj.get("classifiers", [])),
        "n_dependencies": len(proj.get("dependencies", [])),
        "n_extras": len(proj.get("optional-dependencies", {})),
        "n_scripts": len(proj.get("scripts", {})),
        "n_gui_scripts": len(proj.get("gui-scripts", {})),
        "n_entry_point_groups": len(proj.get("entry-points", {})),
        "n_urls": len(proj.get("urls", {})),
        "dynamic": list(proj.get("dynamic", [])),
    }
    return summary


def emit_report(path: Path, toml: dict[str, Any]) -> None:
    """Print a human-readable report on the parsed pyproject.toml."""
    print(f"=== Report on {path} ===\n")
    print(f"Build backend:  {identify_backend(toml)}")
    bs = toml.get("build-system", {})
    print(f"Build requires: {bs.get('requires', [])}")
    print()

    summary = summarise_project(toml)
    print("Project metadata:")
    print(f"  name              : {summary['name']}")
    print(f"  version           : {summary['version']}")
    print(f"  description       : {summary['description']}")
    print(f"  requires-python   : {summary['requires-python']}")
    print(f"  license           : {summary['license']}")
    print(f"  n_authors         : {summary['n_authors']}")
    print(f"  n_classifiers     : {summary['n_classifiers']}")
    print(f"  n_dependencies    : {summary['n_dependencies']}")
    print(f"  n_extras          : {summary['n_extras']}")
    print(f"  n_scripts         : {summary['n_scripts']}")
    print(f"  n_entry_point_grp : {summary['n_entry_point_groups']}")
    print(f"  n_urls            : {summary['n_urls']}")
    print(f"  dynamic           : {summary['dynamic']}")
    print()

    proj = toml.get("project", {})
    if proj.get("dependencies"):
        print("Runtime dependencies (PEP 508):")
        for dep in proj["dependencies"]:
            print(f"  - {dep}")
        print()
    if proj.get("optional-dependencies"):
        print("Extras (optional-dependencies):")
        for extra, deps in proj["optional-dependencies"].items():
            print(f"  [{extra}]")
            for dep in deps:
                print(f"    - {dep}")
        print()
    if proj.get("scripts"):
        print("Console scripts (project.scripts):")
        for name, target in proj["scripts"].items():
            print(f"  {name}  ->  {target}")
        print()
    if proj.get("urls"):
        print("URLs (project.urls):")
        for label, url in proj["urls"].items():
            print(f"  {label:<14}  {url}")
        print()

    findings_bs = validate_build_system(toml)
    findings_pr = validate_project(toml)
    findings = findings_bs + findings_pr
    if findings:
        print("Validation findings:")
        for finding in findings:
            print(f"  - {finding}")
    else:
        print("Validation: clean — no missing required or recommended fields.")
    print()

    tool_tables = sorted(toml.get("tool", {}).keys())
    if tool_tables:
        print(f"[tool.*] tables present: {', '.join(tool_tables)}")
    print()


def render_pyproject_template(
    name: str,
    description: str,
    author_name: str,
    author_email: str,
    backend: str = "hatchling",
) -> str:
    """Render a fresh pyproject.toml from a template.

    Supports backend in {"hatchling", "setuptools", "flit"}.
    """
    if backend == "hatchling":
        build_system = (
            '[build-system]\n'
            'requires = ["hatchling >= 1.27", "hatch-vcs >= 0.4"]\n'
            'build-backend = "hatchling.build"\n'
        )
        tool_table = (
            '\n[tool.hatch.version]\n'
            'source = "vcs"\n\n'
            '[tool.hatch.build.targets.wheel]\n'
            f'packages = ["src/{name}"]\n'
        )
    elif backend == "setuptools":
        build_system = (
            '[build-system]\n'
            'requires = ["setuptools >= 67", "setuptools_scm[toml] >= 8"]\n'
            'build-backend = "setuptools.build_meta"\n'
        )
        tool_table = (
            '\n[tool.setuptools_scm]\n'
            f'write_to = "src/{name}/_version.py"\n\n'
            '[tool.setuptools.packages.find]\n'
            'where = ["src"]\n'
        )
    elif backend == "flit":
        build_system = (
            '[build-system]\n'
            'requires = ["flit-core >= 3.10"]\n'
            'build-backend = "flit_core.buildapi"\n'
        )
        tool_table = (
            f'\n[tool.flit.module]\n'
            f'name = "{name}"\n'
        )
    else:
        raise ValueError(f"Unknown backend: {backend}. Expected hatchling, setuptools, or flit.")

    project_table = (
        '\n[project]\n'
        f'name = "{name}"\n'
        'dynamic = ["version"]\n'
        f'description = "{description}"\n'
        'readme = "README.md"\n'
        'requires-python = ">= 3.11"\n'
        'license = "MIT"\n'
        'authors = [\n'
        f'    {{ name = "{author_name}", email = "{author_email}" }},\n'
        ']\n'
        'classifiers = [\n'
        '    "Development Status :: 3 - Alpha",\n'
        '    "Intended Audience :: Developers",\n'
        '    "License :: OSI Approved :: MIT License",\n'
        '    "Operating System :: OS Independent",\n'
        '    "Programming Language :: Python :: 3",\n'
        '    "Programming Language :: Python :: 3.11",\n'
        '    "Programming Language :: Python :: 3.12",\n'
        '    "Programming Language :: Python :: 3.13",\n'
        ']\n'
        'dependencies = []\n'
    )

    extras_table = (
        '\n[project.optional-dependencies]\n'
        'test = ["pytest >= 7", "pytest-cov >= 5"]\n'
        'dev = ["ruff >= 0.5", "mypy >= 1.10"]\n'
    )

    urls_table = (
        '\n[project.urls]\n'
        f'Homepage = "https://github.com/example/{name}"\n'
        f'Issues = "https://github.com/example/{name}/issues"\n'
    )

    return build_system + project_table + extras_table + urls_table + tool_table


def round_trip_check(rendered: str) -> bool:
    """Parse the rendered TOML and verify it loads without error."""
    try:
        tomllib.loads(rendered)
        return True
    except tomllib.TOMLDecodeError as exc:
        print(f"Round-trip parse failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    """Entry point. Parse args, run the appropriate sub-command."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_report = sub.add_parser("report", help="Parse and report on a pyproject.toml.")
    p_report.add_argument("path", type=Path)

    p_gen = sub.add_parser("gen", help="Generate a pyproject.toml from a template.")
    p_gen.add_argument("--name", required=True)
    p_gen.add_argument("--description", default="A new Python project.")
    p_gen.add_argument("--author-name", default="Anonymous")
    p_gen.add_argument("--author-email", default="anon@example.org")
    p_gen.add_argument(
        "--backend",
        choices=("hatchling", "setuptools", "flit"),
        default="hatchling",
    )

    # Default: if no subcommand, treat first positional as the report target.
    parser.add_argument("default_path", nargs="?", type=Path)
    args = parser.parse_args()

    if args.cmd == "gen":
        rendered = render_pyproject_template(
            name=args.name,
            description=args.description,
            author_name=args.author_name,
            author_email=args.author_email,
            backend=args.backend,
        )
        print(rendered)
        if not round_trip_check(rendered):
            return 1
        return 0

    if args.cmd == "report":
        target = args.path
    elif args.default_path is not None:
        target = args.default_path
    else:
        target = Path(__file__).parent / "exercise-01-sample-pyproject.toml"

    if not target.exists():
        print(f"File not found: {target}", file=sys.stderr)
        return 1

    toml = parse_pyproject(target)
    emit_report(target, toml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
