"""
Exercise 2 — Build and inspect a wheel.

Goal: drive the build process from Python (rather than from `python -m
build` directly), then inspect the produced wheel without unzipping it.
You will read the wheel's METADATA, RECORD, and WHEEL files and report
their contents. By the end you can answer "what is in a wheel" without
guessing.

The flow:
  1. Set up a tiny package source tree (src/mypkg_exercise/...) on disk.
  2. Invoke `python -m build` as a subprocess against that source tree.
  3. Find the produced wheel in dist/.
  4. Open the wheel as a ZIP and inspect its contents.
  5. Print METADATA, the RECORD listing, the WHEEL header.

References:
  - PEP 427 (wheel format): <https://peps.python.org/pep-0427/>
  - PEP 425 (compatibility tags): <https://peps.python.org/pep-0425/>
  - python-build (the `python -m build` tool): <https://build.pypa.io/>
  - zipfile docs: <https://docs.python.org/3/library/zipfile.html>

Run:
  python3 exercise-02-build-and-inspect.py

Validate:
  python3 -m py_compile exercise-02-build-and-inspect.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path
from typing import Iterator


def write_sample_package(root: Path) -> None:
    """Lay down a tiny but complete src-layout package on disk.

    Files: pyproject.toml (we copy the canonical one from this directory),
    README.md, LICENSE, src/mypkg_exercise/__init__.py,
    src/mypkg_exercise/cli.py.
    """
    pyproject_src = Path(__file__).parent / "exercise-02-mypkg-pyproject.toml"
    if not pyproject_src.exists():
        raise FileNotFoundError(
            f"Expected {pyproject_src} alongside this script. "
            "It must be present for the build to have valid metadata."
        )
    shutil.copy(pyproject_src, root / "pyproject.toml")

    (root / "README.md").write_text(
        "# mypkg-exercise\n\n"
        "Example package for Week 9 Exercise 2.\n"
    )
    (root / "LICENSE").write_text(
        "MIT License\n\nCopyright (c) 2026 Code Crunch Worldwide\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy "
        "of this software and associated documentation files (the \"Software\"), to deal "
        "in the Software without restriction...\n"
    )

    pkg_dir = root / "src" / "mypkg_exercise"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text(
        textwrap.dedent(
            '''\
            """mypkg_exercise — a 30-line example package."""

            from __future__ import annotations

            __all__ = ["greet"]


            def greet(name: str) -> str:
                """Return a greeting for `name`."""
                return f"Hello, {name}!"
            '''
        )
    )
    (pkg_dir / "cli.py").write_text(
        textwrap.dedent(
            '''\
            """CLI entry point for mypkg-cli."""

            from __future__ import annotations

            import sys

            from mypkg_exercise import greet


            def main() -> int:
                """The mypkg-cli entry point. `mypkg-cli <name>` prints a greeting."""
                if len(sys.argv) < 2:
                    print("usage: mypkg-cli <name>", file=sys.stderr)
                    return 1
                print(greet(sys.argv[1]))
                return 0
            '''
        )
    )


def run_build(project_root: Path) -> Path:
    """Invoke `python -m build` against the given project root.

    Returns the path to the produced wheel (the .whl, not the .tar.gz).
    Raises subprocess.CalledProcessError if the build fails.
    """
    print(f"[build] running: python -m build  (cwd={project_root})")
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[build] STDOUT:\n" + result.stdout)
        print("[build] STDERR:\n" + result.stderr)
        raise RuntimeError(
            f"`python -m build` failed with exit code {result.returncode}. "
            "Ensure `pip install build` has been run."
        )
    # Print the last 10 lines of build output so the student sees something.
    for line in result.stdout.splitlines()[-10:]:
        print(f"[build] {line}")

    dist_dir = project_root / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"No wheel produced in {dist_dir}.")
    return wheels[0]


def list_wheel_contents(wheel_path: Path) -> list[zipfile.ZipInfo]:
    """Return the ZipInfo list for a wheel."""
    with zipfile.ZipFile(wheel_path) as zf:
        return list(zf.infolist())


def read_wheel_file(wheel_path: Path, member: str) -> str:
    """Read one named file from inside a wheel."""
    with zipfile.ZipFile(wheel_path) as zf:
        return zf.read(member).decode("utf-8")


def parse_wheel_filename(wheel_path: Path) -> dict[str, str]:
    """Parse a wheel filename per PEP 425.

    Returns dict with keys: name, version, python_tag, abi_tag, platform_tag.

    Cite: <https://peps.python.org/pep-0427/#file-name-convention>
          <https://peps.python.org/pep-0425/>
    """
    stem = wheel_path.stem  # strip .whl
    parts = stem.split("-")
    # The build tag is optional. Required parts: name, version, python, abi, platform.
    if len(parts) == 5:
        name, version, python_tag, abi_tag, platform_tag = parts
    elif len(parts) == 6:
        name, version, _build, python_tag, abi_tag, platform_tag = parts
    else:
        raise ValueError(
            f"Wheel filename has {len(parts)} parts; expected 5 or 6. "
            f"Stem: {stem}"
        )
    return {
        "name": name,
        "version": version,
        "python_tag": python_tag,
        "abi_tag": abi_tag,
        "platform_tag": platform_tag,
    }


def iter_dist_info(wheel_path: Path) -> Iterator[str]:
    """Yield the .dist-info paths from a wheel."""
    with zipfile.ZipFile(wheel_path) as zf:
        for member in zf.namelist():
            if ".dist-info/" in member:
                yield member


def report_wheel(wheel_path: Path) -> None:
    """Emit a human-readable report on the wheel."""
    print()
    print(f"=== Wheel report: {wheel_path.name} ===\n")

    parsed = parse_wheel_filename(wheel_path)
    print("Filename parts (PEP 425/427):")
    for key, val in parsed.items():
        print(f"  {key:<13}: {val}")
    print()
    if parsed["python_tag"] == "py3" and parsed["abi_tag"] == "none" and parsed["platform_tag"] == "any":
        print("  Interpretation: pure-Python wheel; installs on any Python 3.x on any platform.")
    else:
        print(f"  Interpretation: platform-tagged wheel. Will install only on")
        print(f"  Python interpreters matching python_tag={parsed['python_tag']}")
        print(f"  with ABI {parsed['abi_tag']} on platform {parsed['platform_tag']}.")
    print()

    contents = list_wheel_contents(wheel_path)
    print(f"Wheel contents ({len(contents)} entries):")
    for info in contents:
        marker = "  [dist-info] " if ".dist-info/" in info.filename else "  [pkg]      "
        print(f"{marker}{info.filename:<60} {info.file_size:>8} bytes")
    print()

    dist_info_dirs = sorted({m.split("/")[0] for m in iter_dist_info(wheel_path)})
    if dist_info_dirs:
        dist_info = dist_info_dirs[0]
        print(f"--- {dist_info}/METADATA ---")
        try:
            metadata = read_wheel_file(wheel_path, f"{dist_info}/METADATA")
            for line in metadata.splitlines()[:30]:
                print(f"  {line}")
            print()
        except KeyError:
            print("  (METADATA not found in wheel)")

        print(f"--- {dist_info}/WHEEL ---")
        try:
            wheel_header = read_wheel_file(wheel_path, f"{dist_info}/WHEEL")
            for line in wheel_header.splitlines():
                print(f"  {line}")
            print()
        except KeyError:
            print("  (WHEEL not found in wheel)")

        record_path = f"{dist_info}/RECORD"
        try:
            record = read_wheel_file(wheel_path, record_path)
            print(f"--- {record_path} ---")
            for line in record.splitlines()[:10]:
                # Each RECORD line: filename,sha256=<digest>,<size>
                print(f"  {line}")
            print()
        except KeyError:
            pass


def verify_install_round_trip(wheel_path: Path, venv_dir: Path) -> None:
    """Create a fresh venv, install the wheel, run the entry point, verify.

    The venv is created at venv_dir. The wheel is installed via
    `pip install`. The entry point `mypkg-cli` is invoked and its output
    is verified.
    """
    print(f"[verify] creating venv at {venv_dir}")
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )
    bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    pip = bin_dir / ("pip.exe" if os.name == "nt" else "pip")

    print(f"[verify] installing wheel: {wheel_path.name}")
    subprocess.run(
        [str(pip), "install", str(wheel_path)],
        check=True,
        capture_output=True,
    )

    cli = bin_dir / ("mypkg-cli.exe" if os.name == "nt" else "mypkg-cli")
    print(f"[verify] running entry point: {cli.name} World")
    result = subprocess.run(
        [str(cli), "World"],
        capture_output=True,
        text=True,
    )
    print(f"[verify] stdout: {result.stdout.strip()!r}")
    expected = "Hello, World!"
    if result.stdout.strip() != expected:
        raise RuntimeError(
            f"Entry point output {result.stdout.strip()!r} != expected {expected!r}"
        )
    print("[verify] round-trip install + invoke: OK")


def main() -> int:
    """Drive the exercise end-to-end."""
    with tempfile.TemporaryDirectory(prefix="mypkg-build-") as tmp:
        project_root = Path(tmp) / "project"
        project_root.mkdir()
        print(f"[setup] writing sample package to {project_root}")
        write_sample_package(project_root)

        try:
            wheel_path = run_build(project_root)
        except (RuntimeError, FileNotFoundError) as exc:
            print(f"\nBuild failed: {exc}", file=sys.stderr)
            print(
                "\nTroubleshooting:\n"
                "  - Run `pip install build` to install the PEP 517 frontend.\n"
                "  - Run `pip install hatchling` (or let pip auto-fetch it).\n"
                "  - Check your network connection (pip needs PyPI for the\n"
                "    isolated build env).\n",
                file=sys.stderr,
            )
            return 1

        report_wheel(wheel_path)

        venv_dir = Path(tmp) / "verify-venv"
        try:
            verify_install_round_trip(wheel_path, venv_dir)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            print(f"\nVerification failed: {exc}", file=sys.stderr)
            return 1

    print("\nDone. Exercise 2 complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
