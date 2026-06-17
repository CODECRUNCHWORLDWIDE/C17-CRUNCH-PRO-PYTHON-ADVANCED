"""
Exercise 3 — Walk the publish flow (dry-run; validate the workflow).

Goal: without uploading anything, demonstrate that you understand the
publish flow end-to-end. The script does three things:

  1. Prints every command in the standard publish sequence, with a
     one-line explanation of what each command does. This is the "show
     me the commands" reference for the mini-project.

  2. Validates the reference GitHub Actions workflow YAML
     (exercise-03-publish.yml) — checks that the required triggers,
     permissions, and `pypa/gh-action-pypi-publish` action are present.
     Uses PyYAML if available; falls back to a regex-based check.

  3. Prints a checklist of one-time setup steps on the PyPI side
     (Trusted Publisher registration), with the URL for each step.

References:
  - PyPI Trusted Publishers: <https://docs.pypi.org/trusted-publishers/>
  - PEP 740: <https://peps.python.org/pep-0740/>
  - pypa/gh-action-pypi-publish: <https://github.com/pypa/gh-action-pypi-publish>
  - twine: <https://twine.readthedocs.io/>

Run:
  python3 exercise-03-publish-flow.py

Validate:
  python3 -m py_compile exercise-03-publish-flow.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# The canonical publish sequence as a list of (command, explanation) pairs.
# The commands are what a developer would run on a local machine to
# publish manually (Path 1 from Lecture 3). The CI workflow automates the
# same sequence with trusted publishing replacing the API token.
PUBLISH_COMMANDS: list[tuple[str, str]] = [
    (
        "python -m pip install --upgrade pip build twine",
        "Install the PEP 517 frontend (build) and the legacy uploader (twine). "
        "uv and hatch are alternatives.",
    ),
    (
        "python -m build",
        "Run the configured build backend (PEP 517 hook build_wheel + build_sdist). "
        "Produces dist/*.whl and dist/*.tar.gz.",
    ),
    (
        "twine check dist/*",
        "Validate the produced metadata (PKG-INFO and METADATA) before upload. "
        "Catches mistakes early — PyPI's rejection messages are sparse.",
    ),
    (
        "twine upload --repository testpypi dist/*",
        "Upload to TestPyPI first. Requires a TestPyPI API token in "
        "~/.pypirc or TWINE_USERNAME=__token__ + TWINE_PASSWORD=<token>.",
    ),
    (
        "python -m pip install --index-url https://test.pypi.org/simple/ "
        "--extra-index-url https://pypi.org/simple/ <package-name>",
        "Verify the TestPyPI upload installs cleanly in a fresh venv. "
        "The extra-index-url is so transitive deps install from real PyPI.",
    ),
    (
        "twine upload dist/*",
        "Once TestPyPI is verified, upload to production PyPI. Same token "
        "shape but a PyPI (not TestPyPI) token.",
    ),
]


# One-time PyPI-side setup steps for trusted publishing.
TRUSTED_PUBLISHING_STEPS: list[tuple[str, str]] = [
    (
        "Register a PyPI account",
        "https://pypi.org/account/register/  (and separately for TestPyPI: "
        "https://test.pypi.org/account/register/). They are independent accounts.",
    ),
    (
        "Enable 2FA on both accounts",
        "Required by PyPI as of 2024 for any account that owns a project. "
        "Use a hardware key (YubiKey) or TOTP. See "
        "https://pypi.org/help/#two-factor-authentication",
    ),
    (
        "Create a 'Pending Publisher' on PyPI",
        "https://pypi.org/manage/account/publishing/ — fill in owner, "
        "repository, workflow filename, environment name. The first time "
        "the workflow runs, PyPI 'claims' the project.",
    ),
    (
        "Create a parallel 'Pending Publisher' on TestPyPI",
        "https://test.pypi.org/manage/account/publishing/ — same form, "
        "environment name typically 'testpypi'.",
    ),
    (
        "Create two GitHub Environments in your repository",
        "Settings -> Environments -> New Environment. Names: 'pypi' and "
        "'testpypi'. Optional: add a manual approval requirement for the "
        "'pypi' environment.",
    ),
    (
        "Commit .github/workflows/publish.yml",
        "Use exercise-03-publish.yml in this directory as the reference. "
        "Adjust the project name and the environments to match your setup.",
    ),
    (
        "Push a tag like v0.1.0",
        "`git tag v0.1.0 && git push --tags`. The workflow triggers; CI "
        "builds and publishes; no token was ever stored.",
    ),
]


def print_publish_sequence() -> None:
    """Print the canonical local publish sequence with explanations."""
    print("=" * 72)
    print("Local publish sequence (Path 1: twine + API token)")
    print("=" * 72)
    for i, (cmd, why) in enumerate(PUBLISH_COMMANDS, start=1):
        print(f"\nStep {i}.")
        print(f"  $ {cmd}")
        for line in wrap_explanation(why, width=68, indent="    "):
            print(line)
    print()


def print_trusted_publishing_setup() -> None:
    """Print the one-time setup for trusted publishing."""
    print("=" * 72)
    print("Trusted publishing setup (Path 2: PEP 740 OIDC; recommended)")
    print("=" * 72)
    for i, (step, detail) in enumerate(TRUSTED_PUBLISHING_STEPS, start=1):
        print(f"\nStep {i}. {step}")
        for line in wrap_explanation(detail, width=68, indent="    "):
            print(line)
    print()


def wrap_explanation(text: str, width: int = 68, indent: str = "    ") -> list[str]:
    """Word-wrap a long explanation string, indenting each line."""
    words = text.split()
    lines: list[str] = []
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width + len(indent):
            lines.append(current.rstrip())
            current = indent + word
        else:
            current = current + (" " if current.strip() else "") + word
    if current.strip():
        lines.append(current.rstrip())
    return lines


def validate_workflow(yaml_path: Path) -> list[str]:
    """Validate the reference workflow YAML against required structure.

    Returns a list of findings. Empty list means clean.
    """
    findings: list[str] = []
    if not yaml_path.exists():
        findings.append(f"Workflow file not found: {yaml_path}")
        return findings

    text = yaml_path.read_text()

    # The validation rules below are regex-based for portability (no PyYAML
    # dependency). A production validator would parse the YAML; this is
    # sufficient for the exercise.

    # Rule 1: must trigger on tag push.
    if not re.search(r"tags:\s*\[\s*\"v\*\"\s*\]", text) and "tags:" not in text:
        findings.append(
            "Workflow does not trigger on tag push (looking for 'tags: [\"v*\"]')."
        )

    # Rule 2: must request id-token: write somewhere (OIDC permission).
    if "id-token: write" not in text:
        findings.append(
            "Workflow does not request `id-token: write` permission — "
            "required for trusted publishing OIDC flow."
        )

    # Rule 3: must use the pypa/gh-action-pypi-publish action.
    if "pypa/gh-action-pypi-publish" not in text:
        findings.append(
            "Workflow does not use `pypa/gh-action-pypi-publish` — "
            "the canonical action for trusted publishing."
        )

    # Rule 4: must have a build step that calls `python -m build` or equivalent.
    if "python -m build" not in text and "uv build" not in text and "hatch build" not in text:
        findings.append(
            "Workflow does not appear to call `python -m build`, `uv build`, "
            "or `hatch build`. Trusted publishing needs distributions to upload."
        )

    # Rule 5: should have an environment: block (the GitHub Environment).
    if re.search(r"environment:\s*\n\s+name:", text) is None:
        findings.append(
            "Workflow does not use `environment:` blocks. Trusted publishing "
            "is most secure when scoped to a specific GitHub Environment."
        )

    return findings


def print_workflow_validation(yaml_path: Path) -> None:
    """Print the workflow validation report."""
    print("=" * 72)
    print(f"Workflow validation: {yaml_path.name}")
    print("=" * 72)
    findings = validate_workflow(yaml_path)
    if not findings:
        print("\nWorkflow validation: clean — all required elements present.")
    else:
        print("\nValidation findings:")
        for finding in findings:
            print(f"  - {finding}")
    print()


def show_pypirc_template() -> None:
    """Print a reference ~/.pypirc for the legacy token path."""
    print("=" * 72)
    print("Reference ~/.pypirc (for Path 1, the legacy token upload)")
    print("=" * 72)
    print(
        "\n  [distutils]\n"
        "  index-servers =\n"
        "      pypi\n"
        "      testpypi\n\n"
        "  [pypi]\n"
        "    username = __token__\n"
        "    password = pypi-<your-PyPI-token-here>\n\n"
        "  [testpypi]\n"
        "    repository = https://test.pypi.org/legacy/\n"
        "    username = __token__\n"
        "    password = pypi-<your-TestPyPI-token-here>\n"
    )
    print(
        "  Generate tokens at:\n"
        "    https://pypi.org/manage/account/token/\n"
        "    https://test.pypi.org/manage/account/token/\n"
    )
    print(
        "  Note: tokens are project-scopable. Always scope a CI token to "
        "one project.\n"
    )


def main() -> int:
    """Walk the entire publish flow as a tutorial."""
    print_publish_sequence()
    show_pypirc_template()
    print_trusted_publishing_setup()

    workflow_path = Path(__file__).parent / "exercise-03-publish.yml"
    print_workflow_validation(workflow_path)

    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(
        "\n  The local flow (twine + token) works but stores a long-lived\n"
        "  secret. The CI flow (trusted publishing) uses GitHub's OIDC\n"
        "  identity to authenticate per-run, with no stored token.\n"
        "\n  For the mini-project, set up trusted publishing on TestPyPI\n"
        "  first. Verify the workflow runs end-to-end. Then, after a real\n"
        "  PyPI account is ready, set up the production publisher.\n"
        "\n  This script makes no network calls. It is a tutorial + a\n"
        "  workflow linter. No package was published in the making of\n"
        "  this output.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
