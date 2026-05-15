# Lecture 02 — Packaging End to End with TestPyPI

> *Python packaging in 2026 is dramatically simpler than Python packaging in 2018. The legacy `setup.py`-based world is gone for new projects. The modern stack is two files (`pyproject.toml` and one source layout), two commands (`python -m build` and `twine upload --repository testpypi`), and a small ecosystem of build backends that all read from the same configuration. This lecture walks the full pipeline — from an empty directory to a successful `pip install --index-url https://test.pypi.org/simple/ cc-yourhandle-yourpkg` against a clean virtual environment on a different machine. The pipeline takes about an hour the first time and twenty minutes every subsequent time.*

## 1. The minimum viable package

The minimum viable Python package is a directory containing:

```
your-package/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/
    └── your_package/
        ├── __init__.py
        └── py.typed
```

That is it. No `setup.py`. No `setup.cfg`. No `MANIFEST.in` unless you are shipping non-Python files. No `requirements.txt`. The `pyproject.toml` is the single source of truth.

We use the `src/` layout (the source code lives under `src/your_package/`, not `your_package/` at the top level). This is the strongly recommended modern layout per the [PyPA packaging guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/). The reason: the `src/` layout prevents a common bug where `import your_package` resolves to the local working directory's source instead of the installed package, masking install-failure bugs until production. With `src/`, you cannot accidentally import the non-installed version.

## 2. The `pyproject.toml`

This is the file the entire packaging ecosystem reads. It has two required sections — `[build-system]` (defined by **PEP 518**) and `[project]` (defined by **PEP 621**) — plus optional backend-specific sections.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cc-jdoe-blurperf"
version = "0.1.0"
description = "Perf-tuned 2D gaussian blur for uint8 RGB images."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
    { name = "Jane Doe", email = "jane@example.com" },
]
keywords = ["image-processing", "blur", "performance"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Multimedia :: Graphics",
    "Topic :: Scientific/Engineering :: Image Processing",
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
benchmarks = [
    "scipy>=1.10",
    "memray>=1.10",
    "psutil>=5.9",
]

[project.urls]
Homepage = "https://github.com/jdoe/cc-jdoe-blurperf"
Repository = "https://github.com/jdoe/cc-jdoe-blurperf"
Issues = "https://github.com/jdoe/cc-jdoe-blurperf/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/cc_jdoe_blurperf"]
```

Annotated line by line:

- **`[build-system]`** is the only section `pip` reads before installing anything. It tells pip what to install in an isolated build environment in order to build your package. Here we use [hatchling](https://hatch.pypa.io/), the build backend recommended by the PyPA for new projects. Alternatives include `setuptools` (if you have C extensions and want the path of least resistance), `flit-core` (if you want even less ceremony for pure-Python packages), and `scikit-build-core` (for CMake-based builds).
- **`name`** is the distribution name on the index. Hyphens-allowed; lowercase strongly preferred. Once published to PyPI it is taken forever. On TestPyPI it persists until pruned. Use the `cc-<handle>-<kernel>` convention from `resources.md` to avoid collisions.
- **`version`** follows **PEP 440**. Valid: `0.1.0`, `0.1.0a1`, `0.1.0rc1`, `1.0.0`, `1.0.0.post1`, `1.0.0.dev1`. Invalid: `0.1.0-alpha`, `v0.1.0`, `0.1`. The capstone starts at `0.1.0`. If you reupload after fixing something, bump to `0.1.1` — PyPI/TestPyPI refuse to overwrite an existing version, on purpose.
- **`description`** is one line, shown on the PyPI page summary and in `pip search` output.
- **`readme`** points to a markdown file; PyPI renders it as the long description. Make this good; it is the marketing copy a hiring manager reads.
- **`requires-python`** is a **PEP 508** constraint. `>=3.11` is reasonable for capstones; many features of W11 require this minimum.
- **`license`** can be a text label or a file reference. PyPI is moving toward [PEP 639](https://peps.python.org/pep-0639/) SPDX expressions; for now, the `{ text = "MIT" }` form is universally supported.
- **`classifiers`** is a list from <https://pypi.org/classifiers/>. The interesting one for the capstone is `Typing :: Typed` — it signals to the index that the package ships type information, paired with the `py.typed` marker file we discuss below.
- **`dependencies`** are runtime requirements; **`optional-dependencies`** are install-extras you can request with `pip install your-pkg[dev]`. Keep runtime dependencies minimal — every dependency is one more thing the user must install and one more thing that might break.
- **`[project.urls]`** are rendered as sidebar links on the PyPI page. Including a Homepage and Repository link is good practice.
- **`[tool.hatch.build.targets.wheel]`** is hatchling-specific. It tells hatchling to include the directory `src/cc_jdoe_blurperf/` (note: underscores, the *import* name) as the wheel contents. Other backends use different keys; consult their docs.

## 3. The `py.typed` marker

**PEP 561** specifies that a package distributes type information by including an empty file named `py.typed` at the root of the importable package. Without it, downstream `mypy` does not see your type hints — even if they are in the source — because PEP 561 is opt-in.

```
src/cc_jdoe_blurperf/
├── __init__.py
├── py.typed        # empty file, just the existence matters
└── _core.py
```

```python
# src/cc_jdoe_blurperf/__init__.py
from cc_jdoe_blurperf._core import blur

__all__ = ["blur"]
__version__ = "0.1.0"
```

```python
# src/cc_jdoe_blurperf/_core.py
import numpy as np


def blur(image: np.ndarray, sigma: float) -> np.ndarray:
    """Apply a 2D gaussian blur to an RGB uint8 image."""
    # ... implementation ...
    return image
```

Hatchling automatically includes `py.typed` in the wheel if it is present in the source layout. Some backends require an explicit include in `[tool.<backend>.build]`; check the backend's documentation.

## 4. Building the distribution

```bash
python -m pip install --upgrade build
python -m build
```

This produces two artefacts in `dist/`:

```
dist/
├── cc_jdoe_blurperf-0.1.0.tar.gz       # sdist (source distribution)
└── cc_jdoe_blurperf-0.1.0-py3-none-any.whl   # wheel (binary distribution)
```

The **sdist** is a tarball of your source. Anyone can rebuild from it. It is the canonical form of a distribution and is required for PyPI/TestPyPI uploads.

The **wheel** is a zip file containing the already-installed layout. `pip` prefers wheels because they install without running build steps; for a pure-Python package the wheel is just the `.py` files plus metadata. For a package with a C extension, the wheel contains the compiled `.so`/`.pyd` and is platform-specific (filename like `cc_jdoe_imageperf-0.1.0-cp313-cp313-macosx_14_0_arm64.whl`).

The capstone may ship only the sdist if the C-extension wheel matrix is too much for one week — `pip install` will fall back to building from the sdist on installation, which works as long as the user has a C toolchain. State this explicitly in the package README.

## 5. Validating the build before upload

```bash
python -m pip install --upgrade twine
twine check dist/*
```

`twine check` validates the README rendering and metadata. A failure here will cause the upload to succeed but render badly on TestPyPI; catch it before upload.

Optional but recommended: install into a fresh venv and run the test suite:

```bash
python -m venv /tmp/cap-test
source /tmp/cap-test/bin/activate
pip install dist/cc_jdoe_blurperf-0.1.0-py3-none-any.whl[dev,benchmarks]
pytest
deactivate
rm -rf /tmp/cap-test
```

If `pytest` fails in the fresh venv but passes in your development venv, you have a missing dependency or a missing file. Fix it before uploading.

## 6. Registering on TestPyPI

1. Go to <https://test.pypi.org/account/register/>. Register. Confirm your email.
2. Enable 2FA. TestPyPI requires it for upload as of 2024.
3. Generate an API token at <https://test.pypi.org/manage/account/token/>. For the first upload, the token must be account-scoped (you cannot scope to a project that does not exist yet). Save the token in a password manager.
4. Configure `twine` to read the token. The convention is `~/.pypirc`:

   ```ini
   [distutils]
   index-servers =
       testpypi
       pypi

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-<your-token-here>

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-<your-other-token-here>
   ```

   The username is the literal string `__token__`. The password is the entire token starting with `pypi-`. The file mode should be `0600` (`chmod 600 ~/.pypirc`).

5. Alternative for CI or paranoid security: pass the token via the `TWINE_PASSWORD` environment variable and never write it to disk.

## 7. Uploading

```bash
twine upload --repository testpypi dist/*
```

You will see progress for each file. Successful output:

```
Uploading distributions to https://test.pypi.org/legacy/
Uploading cc_jdoe_blurperf-0.1.0-py3-none-any.whl
100% --------------------------------- ... kB/... kB
Uploading cc_jdoe_blurperf-0.1.0.tar.gz
100% --------------------------------- ... kB/... kB

View at:
https://test.pypi.org/project/cc-jdoe-blurperf/0.1.0/
```

Open the URL. Verify the README renders. Verify the classifiers are correct. Verify the version is what you expected. Verify the file list contains both the wheel and the sdist.

After the first successful upload, go back to <https://test.pypi.org/manage/account/token/> and create a *project-scoped* token. Replace the account-scoped one in `.pypirc`. Account-scoped tokens are dangerous — they grant upload permission to every project you own.

## 8. Verifying the install from a clean machine

This is the step that catches every bug your local development environment hides. Use a fresh venv, ideally on a different machine:

```bash
python -m venv /tmp/clean-install
source /tmp/clean-install/bin/activate

pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    cc-jdoe-blurperf
```

The `--extra-index-url` is required because TestPyPI does not mirror PyPI. Your `numpy` dependency lives on real PyPI; without the extra index, the install will fail with "no matching distribution found for numpy."

Now run the smoke test:

```python
python -c "import cc_jdoe_blurperf; print(cc_jdoe_blurperf.__version__)"
python -c "import numpy as np; from cc_jdoe_blurperf import blur; print(blur(np.zeros((100,100,3), np.uint8), 1.0).shape)"
```

If both succeed, you have a working public package. Congratulations.

If either fails, the failure is usually one of:

- **Module not found.** The wheel did not include the package directory. Check `[tool.hatch.build.targets.wheel].packages` (or your backend's equivalent).
- **`py.typed` missing in installed location.** mypy will complain. Check the package source has the marker file.
- **Wrong import name.** The *distribution* name is `cc-jdoe-blurperf`; the *import* name is `cc_jdoe_blurperf`. Hyphens become underscores. This is `pip`/PyPI convention and is not configurable.
- **Version mismatch.** Your `__version__` and `pyproject.toml`'s `version` disagreed. Set one, derive the other (hatchling has a `version` source for this; see [Hatch versioning](https://hatch.pypa.io/latest/version/)).

## 9. The wheel matrix question

For a pure-Python capstone, you ship one wheel: `cc_jdoe_blurperf-0.1.0-py3-none-any.whl`. The `none-any` means "no Python ABI, no platform" — installable everywhere.

For a capstone with a C extension, the wheel is platform-specific. The full matrix is `(Python version) x (OS) x (arch)` and explodes quickly. Production packages use [cibuildwheel](https://cibuildwheel.readthedocs.io/) in CI to build all 30+ wheels automatically. For the capstone, ship:

- One wheel for your development machine, *or*
- The sdist alone, and let pip build from source on the user's machine.

Document which you chose in the package README. State the supported platforms explicitly.

## 10. Versioning, bumping, and reuploading

PyPI and TestPyPI **refuse to overwrite an existing version**. This is a deliberate design choice: once a version is on the index, it stays. Bug in `0.1.0`? Ship `0.1.1`. PEP 440 versions sort, and `pip` will pick the highest version that matches the user's constraint.

The pre-release suffixes are useful for the capstone:

- `0.1.0a1` (alpha 1) — "I am still developing this."
- `0.1.0b1` (beta 1) — "feature-complete, debugging."
- `0.1.0rc1` (release candidate 1) — "I think this is it, last chance to catch a bug."
- `0.1.0` (final) — "this is the release."

`pip` does not install pre-releases by default; users must opt in with `pip install --pre`. This is useful: you can upload `0.1.0rc1` to TestPyPI for your own testing without polluting `pip install cc-jdoe-blurperf`'s default behaviour.

The capstone should ship one stable `0.1.0` after walking through one or two `0.1.0a1`-`0.1.0rc1` pre-releases as you debug the pipeline.

## 11. The `LICENSE` file

A package without a license is "all rights reserved" by default. This is hostile to your users; they cannot legally redistribute or modify your code. Pick a permissive license — MIT, BSD-3-Clause, Apache-2.0 — and copy the canonical text into a `LICENSE` file at the repo root. <https://choosealicense.com/> is the standard reference.

The MIT text is short (about 20 lines), grants broad permissions, and is the most common in the Python ecosystem. The capstone defaults to MIT unless you have a strong reason otherwise.

## 12. The full Friday checklist

By the end of Friday:

- [ ] `pyproject.toml` exists with `[build-system]`, `[project]`, and at least `name`, `version`, `description`, `readme`, `requires-python`, `license`, `authors`, `dependencies`.
- [ ] `README.md` exists and renders well.
- [ ] `LICENSE` exists.
- [ ] `src/your_package/__init__.py` and `src/your_package/py.typed` exist.
- [ ] `python -m build` succeeds and produces both an sdist and a wheel in `dist/`.
- [ ] `twine check dist/*` passes.
- [ ] You have a TestPyPI account with an API token in `~/.pypirc`.

Saturday: upload, verify on a clean venv, write the report.

## 13. Common pitfalls

- **Forgetting `--extra-index-url`.** TestPyPI cannot install your package because it cannot find `numpy`. Always pass both index URLs when installing capstone packages.
- **Naming collisions on TestPyPI.** Even if no real package with that name exists on real PyPI, TestPyPI might have one. Pick a unique enough name (the `cc-<handle>-` prefix helps).
- **`pyproject.toml` typos.** Indentation does not matter in TOML, but key names do. `requires-python` is hyphenated. `requires_python` will be silently ignored.
- **Forgetting to bump the version.** Trying to re-upload `0.1.0` after a fix produces `HTTPError: 400 Bad Request from https://test.pypi.org/legacy/`. Bump to `0.1.1` and try again.
- **`twine` reads the wrong section.** Pass `--repository testpypi` explicitly. Without it, `twine` defaults to real PyPI and you will accidentally publish a capstone-quality package to the real index. (TestPyPI uploads can be deleted; real PyPI uploads cannot.)
- **Missing `MANIFEST.in` for C source.** If you ship a C extension as sdist, the `.c` file must be in the tarball. Hatchling includes everything under the package directory by default; setuptools requires a `MANIFEST.in` line like `include src/your_package/*.c`. Verify by extracting the tarball: `tar -tzf dist/your-pkg-0.1.0.tar.gz | grep \\.c$`.

## 14. References

- [The Python Packaging User Guide](https://packaging.python.org/).
- [PEP 517](https://peps.python.org/pep-0517/), [PEP 518](https://peps.python.org/pep-0518/), [PEP 621](https://peps.python.org/pep-0621/), [PEP 660](https://peps.python.org/pep-0660/), [PEP 440](https://peps.python.org/pep-0440/), [PEP 561](https://peps.python.org/pep-0561/).
- [Hatchling documentation](https://hatch.pypa.io/latest/).
- [TestPyPI](https://test.pypi.org/).
- Brett Cannon, "Setting up Python on a Mac in 2024", and various PyCon packaging talks.
