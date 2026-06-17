# Week 9 — Resources

All free. Free + open tools only. Citations are PyPA documentation `main` branch and PEPs at their canonical `peps.python.org` URLs unless noted.

## Required PEPs (read at least once this week)

| PEP | Title | URL | Why |
|-----|-------|-----|-----|
| **PEP 517** | A build-system independent format for source trees | <https://peps.python.org/pep-0517/> | The interface every backend implements. Brett Cannon, Nathaniel Smith, 2015. ~30 min read. |
| **PEP 518** | Specifying minimum build system requirements | <https://peps.python.org/pep-0518/> | The `[build-system]` table; isolated build environments. Brett Cannon et al., 2016. ~20 min. |
| **PEP 621** | Storing project metadata in pyproject.toml | <https://peps.python.org/pep-0621/> | The `[project]` table. The reference for every metadata field. Brett Cannon, Dustin Ingram, Pradyun Gedam, 2020. ~25 min. |
| **PEP 660** | Editable installs for pyproject.toml based builds | <https://peps.python.org/pep-0660/> | Why `pip install -e .` works in 2026. Stefan Hoelzl, Brett Cannon, 2021. ~20 min. |
| **PEP 427** | The Wheel Binary Package Format | <https://peps.python.org/pep-0427/> | The `.whl` filename and ZIP structure. Daniel Holth, 2012. ~15 min. |
| **PEP 425** | Compatibility Tags for Built Distributions | <https://peps.python.org/pep-0425/> | `cp313-cp313-manylinux_2_28_x86_64`: each tag dissected. Daniel Holth, 2012. ~15 min. |
| **PEP 600** | Future 'manylinux' Platform Tags | <https://peps.python.org/pep-0600/> | The perennial manylinux policy; `manylinux_2_28` and beyond. Nathaniel Smith, 2019. ~30 min. |

Strongly recommended:

| PEP | Title | URL | Why |
|-----|-------|-----|-----|
| **PEP 440** | Version Identification and Dependency Specification | <https://peps.python.org/pep-0440/> | The version-string grammar (`1.2.3.post1.dev0`, `~=1.2`). The reference. ~30 min. |
| **PEP 508** | Dependency specification for Python Software Packages | <https://peps.python.org/pep-0508/> | The `requirements.txt` grammar. `httpx[http2]>=0.27; python_version>="3.10"`. ~15 min. |
| **PEP 639** | Improving License Clarity with Better Package Metadata | <https://peps.python.org/pep-0639/> | The modern `license` field using SPDX expressions. Adopted late 2024. ~20 min. |
| **PEP 740** | Index support for digital attestations | <https://peps.python.org/pep-0740/> | The standard underlying trusted publishing; PyPI's OIDC contract. 2024. ~25 min. |
| **PEP 751** | A file format to record Python dependencies for installation reproducibility | <https://peps.python.org/pep-0751/> | The provisional standardised lockfile format. Replaces `uv.lock` / `poetry.lock` eventually. Brett Cannon et al., 2024. ~25 min. |
| **PEP 723** | Inline script metadata | <https://peps.python.org/pep-0723/> | Per-script dependencies embedded in a `# /// script` block. The `uv run` story. ~10 min. |

Of interest, not required:

| PEP | Title | URL | Why |
|-----|-------|-----|-----|
| **PEP 656** | Platform Tag for Linux Distributions Using Musl | <https://peps.python.org/pep-0656/> | musllinux wheels (Alpine Linux). ~15 min. |
| **PEP 711** | PyBI: a standard format for distributing Python Binaries | <https://peps.python.org/pep-0711/> | Distributing the *interpreter* as a wheel-like artifact. Nathaniel Smith. ~20 min. |
| **PEP 668** | Marking Python base environments as "externally managed" | <https://peps.python.org/pep-0668/> | Why `pip install` outside a venv breaks on Debian 12 / Ubuntu 23.04+. ~10 min. |

## PyPA — Python Packaging Authority

| What | Where |
|------|-------|
| **PyPA home** | <https://www.pypa.io/> |
| **packaging.python.org** (the user guide) | <https://packaging.python.org/> |
| **Packaging tutorial** ("Packaging Python Projects") | <https://packaging.python.org/en/latest/tutorials/packaging-projects/> |
| **Glossary** (read once; the canonical definitions) | <https://packaging.python.org/en/latest/glossary/> |
| **Specifications** (PEPs grouped by topic) | <https://packaging.python.org/en/latest/specifications/> |
| **Discussions** | <https://discuss.python.org/c/packaging/14> |

## `pyproject.toml` reference

| Topic | Reference |
|-------|-----------|
| **`pyproject.toml` schema** | <https://packaging.python.org/en/latest/specifications/pyproject-toml/> |
| **`[build-system]` table** | PEP 518 + <https://packaging.python.org/en/latest/specifications/declaring-build-dependencies/> |
| **`[project]` table** | PEP 621 + <https://packaging.python.org/en/latest/specifications/pyproject-toml/#declaring-project-metadata-the-project-table> |
| **`dynamic` fields** | PEP 621 §"Dynamic" + the relevant backend docs |
| **`[project.scripts]` and `[project.gui-scripts]`** | PEP 621 §"Entry points" |
| **`[project.entry-points]`** | <https://packaging.python.org/en/latest/specifications/entry-points/> |
| **`[project.optional-dependencies]`** (extras) | PEP 621 §"optional-dependencies" |
| **TOML spec** (the language `pyproject.toml` is written in) | <https://toml.io/en/v1.0.0> |
| **`tomllib`** (stdlib TOML parser since 3.11) | <https://docs.python.org/3/library/tomllib.html> |

## Build backends

`setuptools` is the historical default and the only backend that handles arbitrary C extensions out of the box. Hatchling is the modern default for pure-Python. The others fill specific niches.

### setuptools

- **Home**: <https://setuptools.pypa.io/>
- **`pyproject.toml` reference**: <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html>
- **`Extension` class** (the C extension declaration): <https://setuptools.pypa.io/en/latest/userguide/ext_modules.html>
- **`setuptools_scm`** (version from git tags): <https://setuptools-scm.readthedocs.io/>
- **Repository**: <https://github.com/pypa/setuptools>
- **When to pick**: existing projects; any project with C/C++ extensions; you want the maximum-flexibility backend.

### hatchling

- **Home**: <https://hatch.pypa.io/latest/>
- **Build backend specifically**: <https://hatch.pypa.io/latest/build/>
- **Config reference**: <https://hatch.pypa.io/latest/config/build/>
- **Repository**: <https://github.com/pypa/hatch>
- **When to pick**: new pure-Python projects; you want the strictest standards adherence and the fastest builds.

### flit-core

- **Home**: <https://flit.pypa.io/>
- **Repository**: <https://github.com/pypa/flit>
- **Config reference**: <https://flit.pypa.io/en/stable/pyproject_toml.html>
- **When to pick**: single-module pure-Python packages; you want the smallest possible backend.

### pdm-backend

- **Home**: <https://backend.pdm-project.org/>
- **Repository**: <https://github.com/pdm-project/pdm-backend>
- **When to pick**: you already use `pdm` for project management; broadly hatchling-equivalent for the build step.

### poetry-core

- **Home**: <https://python-poetry.org/docs/pyproject/>
- **Repository**: <https://github.com/python-poetry/poetry-core>
- **When to pick**: existing poetry projects. Note: poetry's `[tool.poetry]` table is *not* PEP 621 (poetry predates the standard); newer poetry versions support PEP 621 but adoption is gradual.

### uv_build

- **Home**: <https://docs.astral.sh/uv/concepts/build-backend/>
- **Repository**: <https://github.com/astral-sh/uv>
- **When to pick**: you are all-in on `uv` and want a single-binary workflow. Alpha as of early 2026; expect rough edges.

## Tooling — frontends and the build step

| Tool | Role | URL |
|------|------|-----|
| **`pip`** | The reference installer | <https://pip.pypa.io/> |
| **`build` (pypa/build)** | The reference frontend for invoking PEP 517 backends | <https://build.pypa.io/> |
| **`uv`** | Astral's fast Rust-based pip/build/installer/resolver replacement | <https://docs.astral.sh/uv/> |
| **`hatch`** | Hatchling's frontend; project lifecycle (envs, build, publish) | <https://hatch.pypa.io/latest/> |
| **`pdm`** | Frost Ming's project manager | <https://pdm-project.org/> |
| **`poetry`** | Sébastien Eustace's project manager | <https://python-poetry.org/> |
| **`twine`** | The legacy upload tool (still widely used) | <https://twine.readthedocs.io/> |
| **`cibuildwheel`** | Multi-platform wheel-building CI tool; the canonical "wheels for everything" tool | <https://cibuildwheel.pypa.io/> |
| **`auditwheel`** | Wheel post-processor for Linux: verifies manylinux compliance, bundles dependent `.so` files | <https://github.com/pypa/auditwheel> |
| **`delocate`** | The macOS equivalent of `auditwheel` (Matthew Brett) | <https://github.com/matthew-brett/delocate> |
| **`pip-tools`** | The `pip-compile` and `pip-sync` tools for requirements pinning | <https://pip-tools.readthedocs.io/> |
| **`check-wheel-contents`** | Linter for wheel contents (does it have what you think? does it leak files?) | <https://github.com/jwodder/check-wheel-contents> |
| **`pkginfo`** | A library for reading wheel/sdist metadata | <https://pypi.org/project/pkginfo/> |

## manylinux

| What | Where |
|------|-------|
| **`pypa/manylinux` repository** (the policies, the build images, the README) | <https://github.com/pypa/manylinux> |
| **Docker images on Quay** | <https://quay.io/organization/pypa> |
| **Docker images on GHCR** | `ghcr.io/pypa/manylinux2_28_x86_64`, `ghcr.io/pypa/manylinux2_28_aarch64`, etc. |
| **`pypa/musllinux`** (Alpine-based; PEP 656) | <https://github.com/pypa/musllinux> |
| **`auditwheel show` documentation** | <https://github.com/pypa/auditwheel#auditwheel-show> |
| **The manylinux policy table** | <https://github.com/pypa/manylinux#docker-images> |

The canonical command:

```bash
docker run --rm -v "$PWD:/io" quay.io/pypa/manylinux_2_28_x86_64 \
  /opt/python/cp313-cp313/bin/pip wheel /io --wheel-dir /io/dist
# then on the host:
auditwheel show dist/*-cp313-cp313-linux_x86_64.whl
auditwheel repair dist/*-cp313-cp313-linux_x86_64.whl --plat manylinux_2_28_x86_64 -w dist/
```

## Trusted Publishing — PyPI OIDC

| What | Where |
|------|-------|
| **PyPI Trusted Publishers docs** | <https://docs.pypi.org/trusted-publishers/> |
| **`pypa/gh-action-pypi-publish`** (the GitHub Action) | <https://github.com/pypa/gh-action-pypi-publish> |
| **PEP 740** (the underlying spec) | <https://peps.python.org/pep-0740/> |
| **PyPI's pending publisher flow** | <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/> |
| **TestPyPI** | <https://test.pypi.org/> |

## Lockfile tools

| Tool | Lockfile | URL |
|------|----------|-----|
| **`uv`** | `uv.lock` | <https://docs.astral.sh/uv/concepts/projects/sync/> |
| **`poetry`** | `poetry.lock` | <https://python-poetry.org/docs/basic-usage/#installing-dependencies> |
| **`pdm`** | `pdm.lock` | <https://pdm-project.org/latest/usage/lockfile/> |
| **`pip-tools`** | `requirements.txt` (with hashes) via `pip-compile --generate-hashes` | <https://pip-tools.readthedocs.io/> |
| **PEP 751 / `pylock.toml`** (provisional) | Standardised lockfile (future) | <https://peps.python.org/pep-0751/> |

## Versioning

| Scheme | URL |
|--------|-----|
| **Semantic Versioning** | <https://semver.org/> |
| **Calendar Versioning** | <https://calver.org/> |
| **`setuptools_scm`** (version from git tags) | <https://setuptools-scm.readthedocs.io/> |
| **`hatch-vcs`** (the hatch equivalent of `setuptools_scm`) | <https://github.com/ofek/hatch-vcs> |
| **PEP 440** (the version-string grammar) | <https://peps.python.org/pep-0440/> |

## Background reading

- **The PyPA tutorial, "Packaging Python Projects"** — the canonical end-to-end walkthrough. ~40 minutes. <https://packaging.python.org/en/latest/tutorials/packaging-projects/>.
- **Brett Cannon, "Python's path forward on packaging" (PyCon US 2024)** — annual state-of-packaging talk. Search YouTube. ~45 minutes. Free.
- **Pradyun Gedam, "Python packaging in 2024"** — companion talk. Search YouTube. ~30 minutes.
- **Ofek Lev, "Hatch: a modern Python project manager"** — the hatch author's introductory talk. Search YouTube. ~30 minutes.
- **Frost Ming, "PDM design and architecture"** — the pdm author's design talk. Search YouTube. ~25 minutes.
- **Charlie Marsh, "Introducing uv"** (Astral, 2024) — the uv launch presentation. <https://astral.sh/blog/uv>. ~10 minutes to read; talks on YouTube. Free.
- **Nathaniel Smith, "Why I wrote PEP 600"** — the manylinux author's blog. Search "vorpus.org manylinux". Free.
- **Hynek Schlawack, "Python packaging in 2024 done right"** — an opinionated guide from a respected maintainer. <https://hynek.me/articles/python-packaging/>. Free.
- **Itamar Turner-Trauring, "Pinning vs. locking: a tutorial"** — the clearest writeup of the distinction. <https://pythonspeed.com/articles/lockfile-pinning/>. Free.

## Example projects to read

| Project | Why | URL |
|---------|-----|-----|
| **`numpy`** | Non-trivial native extension; meson-python backend (uses pyproject.toml + meson) | <https://github.com/numpy/numpy/blob/main/pyproject.toml> |
| **`pip`** | The installer itself; setuptools + setuptools_scm | <https://github.com/pypa/pip/blob/main/pyproject.toml> |
| **`httpx`** | Pure-Python; hatchling | <https://github.com/encode/httpx/blob/master/pyproject.toml> |
| **`rich`** | Pure-Python; poetry-core | <https://github.com/Textualize/rich/blob/master/pyproject.toml> |
| **`pydantic`** | Hybrid (Rust core via maturin); hatchling for the Python side | <https://github.com/pydantic/pydantic/blob/main/pyproject.toml> |
| **`cryptography`** | Rust + setuptools-rust; manylinux wheels via cibuildwheel | <https://github.com/pyca/cryptography/blob/main/pyproject.toml> |
| **`structlog`** | Pure-Python; hatchling; well-commented `pyproject.toml` | <https://github.com/hynek/structlog/blob/main/pyproject.toml> |
| **`flit`** | The flit-core author's own project | <https://github.com/pypa/flit/blob/main/pyproject.toml> |
| **`attrs`** | Hynek Schlawack's; hatchling; impeccable metadata | <https://github.com/python-attrs/attrs/blob/main/pyproject.toml> |
| **`uv`** | Astral's project; uv_build (eats its own dog food) | <https://github.com/astral-sh/uv/blob/main/pyproject.toml> |

## Optional installs (all pip-installable, all free)

| Tool | Install | Used in |
|------|---------|---------|
| `build` (pypa/build) | `pip install build` | Exercise 2; mini-project |
| `hatch` | `pip install hatch` | Lecture 2; Exercise 2; Challenge 1 |
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Throughout; lockfile generation |
| `twine` | `pip install twine` | Lecture 3; mini-project |
| `cibuildwheel` | `pip install cibuildwheel` | Challenge 2; mini-project (CI step) |
| `auditwheel` | `pip install auditwheel` (Linux only; the wheel command itself runs on Linux) | Challenge 2 |
| `pip-tools` | `pip install pip-tools` | Lecture 3 (lockfile demo) |
| `pkginfo` | `pip install pkginfo` | Exercise 2 (wheel inspection) |
| `check-wheel-contents` | `pip install check-wheel-contents` | Mini-project (wheel lint) |
| `setuptools_scm` | `pip install setuptools_scm` | Lecture 3; mini-project |
| `hatch-vcs` | `pip install hatch-vcs` | Lecture 2 (alternative to setuptools_scm) |

You also need:

- **A TestPyPI account** at <https://test.pypi.org/account/register/>. Free. Register early; the email verification can take an hour.
- **A GitHub account and a public (or private) repo** for the mini-project's CI workflow.
- **Docker (optional)** for the manylinux exercise. Docker Desktop on macOS/Windows; the docker package on Linux.

## Glossary

| Term | Definition |
|------|------------|
| **Build backend** | The code that knows how to turn your source tree into a wheel. setuptools, hatchling, flit-core, etc. Selected via `[build-system]` in `pyproject.toml`. PEP 517. |
| **Build frontend** | The tool that invokes the backend. `pip` (when installing from source), `python -m build`, `uv build`, `hatch build`. |
| **sdist** | Source distribution: a `.tar.gz` of the source tree plus a `PKG-INFO`. The fallback when no wheel matches. |
| **wheel** | Binary distribution format: a `.whl` (which is a ZIP). Installs without running user code. PEP 427. |
| **Platform tag** | The `manylinux_2_28_x86_64`, `macosx_11_0_arm64`, `win_amd64`, `none-any` suffix on a wheel filename. PEP 425. |
| **`manylinux`** | A family of platform tags for "Linux wheels that work on many distros." `manylinux_2_28` = "glibc >= 2.28." PEP 600. |
| **`auditwheel`** | The Linux wheel post-processor: verifies manylinux compliance, bundles dependent `.so` files into the wheel. |
| **`delocate`** | The macOS analogue of `auditwheel`. |
| **`cibuildwheel`** | The PyPA tool for building wheels for all platforms × Python versions in CI. |
| **PEP 517** | The build-system interface. Defines how `pip` invokes a backend. |
| **PEP 518** | The `[build-system]` table; the rule that builds run in an isolated environment. |
| **PEP 621** | The `[project]` table; the metadata fields (name, version, dependencies, ...). |
| **PEP 660** | Editable installs (`pip install -e .`) in the PEP 517 world. |
| **TOML** | The configuration language `pyproject.toml` is written in. Tom Preston-Werner, 2013. v1.0 spec at <https://toml.io/>. Parsed via `tomllib` since Python 3.11. |
| **Trusted publishing** | PyPI's OIDC-based authentication for CI workflows. No long-lived API token. PEP 740. |
| **TestPyPI** | The staging instance of PyPI at `test.pypi.org`. Separate account, separate index. Used to verify a publish flow before going to production PyPI. |
| **CalVer** | Calendar versioning: `2026.5.14`, `2026.04.0`. Common for "shipped on a schedule" projects. |
| **SemVer** | Semantic versioning: `MAJOR.MINOR.PATCH`. The default for libraries. <https://semver.org/>. |
| **`setuptools_scm`** | A setuptools plugin that derives the package version from git tags. Eliminates the version literal. |
| **Pinning** | Specifying a version range or exact version for direct dependencies. `requests >= 2.31`. |
| **Locking** | Recording the resolved version *and hash* of every transitive dependency, for fully reproducible installs. `uv.lock`, `poetry.lock`. |
| **PEP 751** | The (provisional) standardised lockfile format. `pylock.toml`. |
| **Extras (optional dependencies)** | A named group of dependencies activated by `pip install pkg[extra]`. Declared in `[project.optional-dependencies]`. |
| **Entry point** | A named callable a package registers for plugin discovery (`[project.entry-points."myapp.plugins"]`) or for installing a CLI command (`[project.scripts]`). |
| **`dynamic`** | The PEP 621 list of metadata fields the backend will fill in. Required when, e.g., `version` comes from `setuptools_scm`. |

---

*Broken link? Open an issue.*
