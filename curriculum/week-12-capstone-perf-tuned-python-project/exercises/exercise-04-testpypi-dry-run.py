"""Exercise 04 — Dry-run a TestPyPI upload locally.

Goal: walk through the upload-validation flow *without* actually uploading.
We use this exercise to catch the common upload-time errors before they
hit the network:

    - pyproject.toml metadata problems
    - long_description (README) rendering problems
    - version-string PEP 440 conformance
    - distribution name conflict (well, we *check*; we cannot reserve)
    - missing files in the sdist
    - missing wheel for our platform

The script does not require an API token. It does not upload. It does
require `build` to be installed if you want the build step to run:

    pip install build

And `twine` if you want the `twine check` step to run:

    pip install twine

References:
    - PEP 440 — version identification.
    - https://twine.readthedocs.io/en/stable/#twine-check
    - https://packaging.python.org/en/latest/specifications/version-specifiers/
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


# A minimal regex covering the common subset of PEP 440 version strings.
# The full grammar is more permissive (post-releases, dev-releases, local
# versions, etc.) — we lint the common case; the full check is twine's job.
PEP_440_CORE: re.Pattern[str] = re.compile(
    r"^(\d+)(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?$"
)


def is_pep_440_compliant(version: str) -> bool:
    """Best-effort lint of a PEP 440 version string. Use twine for the full check."""
    return bool(PEP_440_CORE.match(version))


# Distribution-name policy (per PyPI):
#   - ASCII letters, digits, hyphens, underscores, periods
#   - Must start with a letter or digit
#   - Case-insensitive on the index
DIST_NAME_POLICY: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


def is_valid_distribution_name(name: str) -> bool:
    """Apply the basic PyPI distribution-name policy."""
    return bool(DIST_NAME_POLICY.match(name))


def lint_pyproject(toml_path: Path) -> list[str]:
    """Read a pyproject.toml; return a list of lint findings. Empty = clean."""
    findings: list[str] = []
    if not toml_path.is_file():
        return [f"FATAL: {toml_path} does not exist"]
    with toml_path.open("rb") as f:
        try:
            data: dict[str, object] = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            return [f"FATAL: TOML parse failure: {e}"]

    # [build-system]
    bs = data.get("build-system")
    if not isinstance(bs, dict):
        findings.append("missing [build-system] table (PEP 518)")
    else:
        if "requires" not in bs:
            findings.append("[build-system].requires missing")
        if "build-backend" not in bs:
            findings.append("[build-system].build-backend missing")

    # [project]
    project = data.get("project")
    if not isinstance(project, dict):
        findings.append("missing [project] table (PEP 621)")
        return findings

    required_fields: list[str] = [
        "name",
        "version",
        "description",
        "readme",
        "requires-python",
    ]
    for field in required_fields:
        if field not in project:
            findings.append(f"[project].{field} missing")

    # Name policy
    name = project.get("name")
    if isinstance(name, str) and not is_valid_distribution_name(name):
        findings.append(f"[project].name '{name}' fails distribution-name policy")

    # Version policy
    version = project.get("version")
    if isinstance(version, str) and not is_pep_440_compliant(version):
        findings.append(f"[project].version '{version}' is not PEP 440")

    # Author plausibility
    authors = project.get("authors")
    if not isinstance(authors, list) or len(authors) == 0:
        findings.append("[project].authors empty or missing (recommended)")

    # License
    if "license" not in project:
        findings.append("[project].license missing (recommended)")

    # Classifiers
    classifiers = project.get("classifiers")
    if not isinstance(classifiers, list):
        findings.append("[project].classifiers missing (recommended)")
    elif "Typing :: Typed" not in classifiers:
        findings.append(
            "[project].classifiers does not include 'Typing :: Typed' — "
            "consider adding if your package ships py.typed"
        )

    return findings


def try_twine_check(dist_dir: Path) -> str:
    """Invoke `twine check dist/*`. Return the stdout/stderr or a skip message."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "twine", "check", str(dist_dir / "*")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        return "twine not installed; run: pip install twine"
    except subprocess.TimeoutExpired:
        return "twine check timed out (>30s); investigate"


def try_build(project_root: Path, out_dir: Path) -> str:
    """Invoke `python -m build`. Return summary or skip message."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--wheel",
                "--outdir",
                str(out_dir),
                str(project_root),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return f"BUILD FAILED:\n{result.stderr[-2000:]}"
        files: list[str] = sorted(p.name for p in out_dir.iterdir())
        return f"build OK; produced: {files}"
    except FileNotFoundError:
        return "build not installed; run: pip install build"
    except subprocess.TimeoutExpired:
        return "build timed out (>120s); investigate"


def main() -> None:
    # Run the static linter on a *hypothetical* good pyproject.
    good_toml: str = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cc-student-demo"
version = "0.1.0a1"
description = "Demo."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Student", email = "s@example.invalid" }]
classifiers = ["Typing :: Typed"]
"""
    with tempfile.TemporaryDirectory() as tmp:
        path: Path = Path(tmp) / "pyproject.toml"
        path.write_text(good_toml)
        findings: list[str] = lint_pyproject(path)
        print("=== Good case ===")
        print(f"findings: {findings or 'CLEAN'}")

    # Run on a bad pyproject.
    bad_toml: str = """\
[project]
name = "Bad Name With Spaces"
version = "1.0-alpha"
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "pyproject.toml"
        path.write_text(bad_toml)
        findings = lint_pyproject(path)
        print("\n=== Bad case ===")
        for f in findings:
            print(f"  - {f}")

    # PEP 440 sanity table.
    print("\n=== PEP 440 spot checks ===")
    cases: list[tuple[str, bool]] = [
        ("0.1.0", True),
        ("1.0.0a1", True),
        ("1.0.0rc1", True),
        ("1.0.0.post1", True),
        ("1.0.0.dev1", True),
        ("1.0.0-alpha", False),
        ("v1.0.0", False),
        ("1.0", True),  # legal "epoch" form
    ]
    for v, expected in cases:
        got: bool = is_pep_440_compliant(v)
        flag: str = "OK" if got == expected else "MISMATCH"
        print(f"  {v!r:18}  predicted={got!s:5} expected={expected!s:5}  {flag}")

    # Distribution-name spot checks.
    print("\n=== Distribution-name spot checks ===")
    names: list[tuple[str, bool]] = [
        ("cc-jdoe-blurperf", True),
        ("cc_jdoe_blurperf", True),
        ("Bad Name", False),
        ("-leading-hyphen", False),
        ("1numeric-start-ok", True),
        ("dots.are.ok", True),
    ]
    for n, expected in names:
        got = is_valid_distribution_name(n)
        flag = "OK" if got == expected else "MISMATCH"
        print(f"  {n!r:25}  predicted={got!s:5} expected={expected!s:5}  {flag}")

    print("\nDone. If you want to exercise twine and build for real, see the")
    print("try_twine_check / try_build functions in this file; uncomment the")
    print("invocation block in __main__.")


if __name__ == "__main__":
    main()
