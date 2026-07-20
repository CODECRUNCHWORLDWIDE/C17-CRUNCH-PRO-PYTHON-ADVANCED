# Exercises — Solutions and Notes

The exercises this week are mostly **harness scripts** that drive real packaging tools. The "solution" is the script doing the right thing on real inputs, not a single magic number. Below: the expected behaviour for each exercise, common errors, and the reasoning.

---

## Exercise 1 — Parse and emit a pyproject.toml metadata report

### Expected output (report mode)

Running `python3 exercise-01-write-pyproject.py exercise-01-sample-pyproject.toml` should produce roughly:

```
=== Report on exercise-01-sample-pyproject.toml ===

Build backend:  hatchling
Build requires: ['hatchling >= 1.27', 'hatch-vcs >= 0.4']

Project metadata:
  name              : convoltools
  version           : <dynamic>
  description       : 1D convolution kernels for time-series data.
  requires-python   : >= 3.11
  license           : MIT
  n_authors         : 2
  n_classifiers     : 11
  n_dependencies    : 2
  n_extras          : 3
  n_scripts         : 1
  n_entry_point_grp : 1
  n_urls            : 5
  dynamic           : ['version']

Runtime dependencies (PEP 508):
  - numpy >= 1.26
  - typing-extensions >= 4.7; python_version < '3.12'

Extras (optional-dependencies):
  [test]
    - pytest >= 7.0
    - pytest-cov >= 5.0
    - hypothesis >= 6.100
  ...

Validation: clean — no missing required or recommended fields.

[tool.*] tables present: hatch, mypy, pytest, ruff
```

Validation should report **clean**. If you see findings like "[project].version missing" but the sample uses `dynamic = ["version"]`, you have a logic bug — the validator must treat `dynamic` as "this field will be filled in by the backend."

### Common errors

- **`tomllib.TOMLDecodeError`** — the sample file is malformed. Re-run `python3 -c "import tomllib; tomllib.load(open('exercise-01-sample-pyproject.toml','rb'))"` to localise the parse failure. The most common cause: a trailing comma in an inline table or array, which TOML 1.0 forbids in some positions.
- **`KeyError: 'project'`** — the file has no `[project]` table. This is a PEP 621 violation; the validator should catch it and report it.
- **`ValueError: Unknown backend`** — your `KNOWN_BACKENDS` dict is missing an entry. Add the build-backend identifier (the string after `build-backend = "..."`) to the dict.

### Generation mode

`python3 exercise-01-write-pyproject.py gen --name foopkg --description "A new pkg" --author-name "Ada" --author-email "ada@example.org" --backend hatchling`

should print a `pyproject.toml` whose top is:

```
[build-system]
requires = ["hatchling >= 1.27", "hatch-vcs >= 0.4"]
build-backend = "hatchling.build"

[project]
name = "foopkg"
dynamic = ["version"]
description = "A new pkg"
...
```

The round-trip check (parse the generated string, verify it loads without error) must pass. If you see "Round-trip parse failed" it means your template has a TOML syntax error — usually a missing quote or an unescaped newline in a string.

### Reasoning

The PEP 621 required fields are precisely **name** (and either `version` or `version in dynamic`). Everything else is optional. The PEP recommends `description`, `readme`, `requires-python`, and `license` for any published package; PyPI's quality lints catch these too.

The "dynamic" list is the contract between the static `pyproject.toml` and the build backend: it says "the backend will fill in these fields at build time" so that tools reading the static file know not to expect them. The pattern `dynamic = ["version"]` plus a backend-specific version source (`setuptools_scm`, `hatch-vcs`) is the modern default.

Cite Lecture 1 §4 (PEP 621 walkthrough) and the packaging.python.org pyproject.toml specification: <https://packaging.python.org/en/latest/specifications/pyproject-toml/>.

---

## Exercise 2 — Build and inspect a wheel

### Expected output

The script lays down a 30-line package, invokes `python -m build`, and inspects the wheel. Expected output (abridged):

```
[setup] writing sample package to /tmp/mypkg-build-XXX/project
[build] running: python -m build  (cwd=/tmp/mypkg-build-XXX/project)
[build] * Creating venv isolated environment...
[build] * Installing packages in isolated environment:
[build]   - hatchling >= 1.27
[build] * Getting build dependencies for sdist...
[build] * Building sdist...
[build] * Building wheel from sdist
[build] Successfully built mypkg_exercise-0.1.0.tar.gz and mypkg_exercise-0.1.0-py3-none-any.whl

=== Wheel report: mypkg_exercise-0.1.0-py3-none-any.whl ===

Filename parts (PEP 425/427):
  name         : mypkg_exercise
  version      : 0.1.0
  python_tag   : py3
  abi_tag      : none
  platform_tag : any

  Interpretation: pure-Python wheel; installs on any Python 3.x on any platform.

Wheel contents (5 entries):
  [pkg]      mypkg_exercise/__init__.py                                     199 bytes
  [pkg]      mypkg_exercise/cli.py                                          445 bytes
  [dist-info] mypkg_exercise-0.1.0.dist-info/METADATA                       512 bytes
  [dist-info] mypkg_exercise-0.1.0.dist-info/WHEEL                           91 bytes
  [dist-info] mypkg_exercise-0.1.0.dist-info/RECORD                         310 bytes

--- mypkg_exercise-0.1.0.dist-info/METADATA ---
  Metadata-Version: 2.3
  Name: mypkg-exercise
  Version: 0.1.0
  Summary: A 30-line example package for Week 9 Exercise 2.
  ...

--- mypkg_exercise-0.1.0.dist-info/WHEEL ---
  Wheel-Version: 1.0
  Generator: hatchling 1.27.0
  Root-Is-Purelib: true
  Tag: py3-none-any

[verify] creating venv at /tmp/mypkg-build-XXX/verify-venv
[verify] installing wheel: mypkg_exercise-0.1.0-py3-none-any.whl
[verify] running entry point: mypkg-cli World
[verify] stdout: 'Hello, World!'
[verify] round-trip install + invoke: OK

Done. Exercise 2 complete.
```

### What to look for

- **Wheel tag `py3-none-any`.** A pure-Python wheel. Pure Python means no `.so`/`.pyd` files; PEP 425 says `none-any` is the maximally portable tag.
- **`Root-Is-Purelib: true`** in the WHEEL file. This tells `pip` to install everything into `site-packages` (the "purelib" directory); a non-purelib wheel goes into a platform-specific location.
- **The `mypkg-cli` entry point**. The build step creates a script in `dist-info/entry_points.txt`; the install step (in the verify venv) materialises it as an executable in `bin/` (or `Scripts/` on Windows).
- **The verify round-trip prints `Hello, World!`**. If it does not, the entry point did not get installed correctly — usually a mismatch between `[project.scripts]` and the actual module path.

### Common errors

- **`RuntimeError: `python -m build` failed`** — you need `pip install build` first. The script does not pre-install it (because installing into the running interpreter has side effects); run `pip install build hatchling` and try again.
- **`No wheel produced in dist/`** — the build silently failed. Read the stderr output the script captured. Common causes: a bad `pyproject.toml` (run `tomllib.load` on it to check); a backend not installed in the isolated env (rare; pip will usually fetch it).
- **`mypkg-cli` not found in `bin/`** — the entry point did not install. Check the wheel's `dist-info/entry_points.txt`; should contain `[console_scripts]\nmypkg-cli = mypkg_exercise.cli:main\n`.
- **macOS-specific: `pip install` from a temp venv fails because the temp venv's `pip` is too old.** Workaround: `pip install --upgrade pip` in the venv before installing the wheel. The exercise script does not do this; you may need to patch it on first run.

### Reasoning

This exercise is the "anatomy of a wheel" lesson. Reading METADATA, RECORD, and WHEEL teaches you to debug `pip install` failures: when a user reports "the package installs but the CLI does not work," the first place you look is the wheel's `entry_points.txt`. When a user reports "the package will not install on macOS," you check the wheel's platform tag (should it be `any`? should it be `macosx_11_0_arm64`? was a Linux-tagged wheel uploaded by mistake?).

Cite Lecture 3 §§1–2 (wheel format; sdists) and PEP 427.

---

## Exercise 3 — Walk the publish flow

### Expected output

This exercise is a *tutorial script*, not a "does the right thing on inputs" script. It prints:

1. The local publish sequence (steps 1–6), each with an explanation.
2. A reference `~/.pypirc` template for the legacy token path.
3. The trusted publishing setup steps (8 items).
4. A workflow-file validation report against `exercise-03-publish.yml`.
5. A summary.

The workflow validation must report **clean** for the reference `exercise-03-publish.yml`. The five rules it checks:

1. The workflow triggers on tag push (`tags: ["v*"]`).
2. It requests `id-token: write` permission.
3. It uses `pypa/gh-action-pypi-publish`.
4. It runs `python -m build` (or `uv build` or `hatch build`).
5. It uses GitHub `environment:` blocks.

If any check fails, the script prints the finding and exits with code 1 from `validate_workflow`. The reference workflow shipped in the exercises directory passes all five.

### Common learner mistakes (when adapting for the mini-project)

- **Forgetting `permissions: id-token: write`.** Without it, the OIDC token request returns 403; the workflow fails the upload step. The error message from `gh-action-pypi-publish` will mention "missing id-token" — a clear pointer.
- **The Pending Publisher fields on PyPI do not match the workflow exactly.** Owner, repository, workflow filename, and environment name must match character-for-character. If you renamed the workflow from `publish.yml` to `release.yml`, update PyPI too.
- **The Environment in GitHub Settings does not exist.** If `environment: { name: pypi }` references an environment that was never created in Settings -> Environments, the workflow run starts but blocks waiting for an environment that does not exist. Create the environment first (it can be empty — no secrets needed for trusted publishing).
- **TestPyPI's token from `~/.pypirc` does not match PyPI's.** They are separate accounts with separate tokens. Generate one for each. Some learners attempt to use a PyPI token to upload to TestPyPI; it fails authentication.

### Reasoning

The script is the "without uploading anything, prove I understand the flow" exercise. The publish flow has many moving parts (GitHub OIDC, PyPI's trust registry, the action, the environment, the workflow trigger); validating the YAML and printing the commands separately is the cheapest way to assert "you have the model" without consuming a real PyPI namespace.

Cite Lecture 3 §§8–10 (publishing paths; trusted publishing; the full pipeline) and the PyPI trusted publishing docs: <https://docs.pypi.org/trusted-publishers/>.

---

## Cross-exercise notes

- **`tomllib` is your friend.** Stdlib since 3.11. Parse-checking a `pyproject.toml` is one line: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`. Use it on every TOML file you touch this week.
- **Run `python3 -m py_compile <file>.py` after every edit.** It is faster than `mypy` and catches every syntax error. The mini-project rubric explicitly checks this.
- **`python -m build` is the canonical frontend.** `uv build` and `hatch build` are alternatives that work too; the exercise scripts use `python -m build` because it is the lowest common denominator and works in any environment with `pip install build`.
- **Read each exercise's docstring before reading the code.** Each `.py` file has a header that names the references, the run command, the validate command, and the goal. The code below is the implementation; the docstring is the spec.

## Reading

- Lecture 1 (PEPs + pyproject.toml anatomy) — re-read §§4 and 6 if any of Exercise 1's validation logic is unclear.
- Lecture 2 (build backends) — re-read §§3 and 9 if Exercise 2's wheel contents differ from the expected output.
- Lecture 3 (wheels, manylinux, locking, publishing) — re-read §§1, 8, and 9 if any of Exercise 3's validation rules are unclear.
- The packaging.python.org `pyproject.toml` specification: <https://packaging.python.org/en/latest/specifications/pyproject-toml/>.
- The `tomllib` documentation: <https://docs.python.org/3/library/tomllib.html>.
