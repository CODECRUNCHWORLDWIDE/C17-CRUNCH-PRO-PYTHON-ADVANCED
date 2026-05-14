# Week 9 — Packaging and Distribution

> *Three years ago, "publishing a Python package" meant `python setup.py sdist upload`, a `MANIFEST.in` you copy-pasted from someone else's project, a `setup.cfg` you tolerated, and a smoke-test on a borrowed PyPI account. The artifact you produced — an sdist, maybe a single platform-tagged wheel — landed somewhere on `pypi.org` and you hoped for the best. In 2026 that whole flow is gone. The replacement is a single `pyproject.toml`, a declarative build system selected via PEP 517 / 518 / 660, a wheel built against the `manylinux_2_28` policy (PEP 600), an `uv.lock` (or `poetry.lock`) that pins every transitive dependency by hash, and a publish step that uses GitHub Actions' OIDC token to authenticate to PyPI with **no API key stored anywhere** (PEP 740 attestations; "trusted publishing"). This week you learn the modern path end-to-end: you write a real package, you choose a build backend (and you can explain why you picked it instead of the other six), you build a wheel and an sdist, you push to TestPyPI, you install in a clean venv, and you set up GitHub Actions to do it for you on every git tag. The artifact you ship at the end of this week is a published package — actually on TestPyPI, actually installable — plus a 700-word memo on the choices you made.*

Welcome to Week 9 of **C17 · Crunch Pro Python Advanced**. Week 8 left you fluent in three native-extension paths (`ctypes`, `cffi`, `Cython`) and one judgement: pick the path that matches your constraints. This week is the *distribution* side of the same problem. A C extension you cannot ship is a C extension that runs on exactly one developer's laptop. The packaging story is the difference between a `kernel.so` that exists in your `~/projects` and a `pip install yourpkg` that works for every user on every platform you targeted.

The thesis is small: **the packaging ecosystem in 2026 is, for the first time, coherent.** A single declarative file (`pyproject.toml`, defined across PEPs 517, 518, 621, and 660) is the source of truth. Multiple build backends compete to read that file — `setuptools`, `hatchling`, `flit-core`, `pdm-backend`, `poetry-core`, `uv_build` — but the *interface* between them and `pip`/`uv`/`build` is standardised. You can change backends by editing seven lines of TOML. You can lift a project from `setuptools` to `hatchling` in an afternoon. The corollary is large: **the packaging ecosystem before 2021 was incoherent**, and a great deal of folk knowledge ("you have to have a `setup.py`", "you need a `MANIFEST.in`", "you upload with `twine`") is stale. This week sweeps it out.

The standards are the spine. **PEP 517** (Brett Cannon, Nathaniel Smith, 2015) defines the build-system interface — the protocol by which `pip` or `uv` invokes whatever build backend you chose to produce a wheel. **PEP 518** (Brett Cannon et al., 2016) defines the `[build-system]` table in `pyproject.toml` and the requirement that build backends be installed in an isolated environment, not the project's runtime environment. **PEP 621** (Brett Cannon, Dustin Ingram, Pradyun Gedam, 2020) defines the `[project]` table: name, version, dependencies, `description`, `authors`, classifiers, all the metadata that used to live in `setup.cfg`. **PEP 660** (Stefan Hoelzl, Brett Cannon, 2021) defines editable installs (`pip install -e .`) in the PEP 517 world — the standard that made `pip install -e .` work without `setup.py develop`. Together these four PEPs are the bedrock. Memorise their numbers; the rest is mechanics.

The build backends are the choice. **setuptools** (the historical default; the only path before PEP 517) supports `pyproject.toml` since 2021 and is the right answer for "I have an existing project and do not want to switch" or "my project includes C extensions." **hatchling** (Ofek Lev, 2021; the build backend of `hatch`) is the modern default for pure-Python projects: fast, minimal, strict about the standards. **flit-core** (Thomas Kluyver, 2015) is the smallest possible backend — write a `pyproject.toml`, one module, done; suitable for tiny libraries. **pdm-backend** (Frost Ming, 2020) is `pdm`'s native backend; broadly equivalent to hatchling. **poetry-core** (the build backend of poetry) is the right answer if you already use poetry. **uv_build** (Astral, late 2024; alpha as of early 2026) is the build backend bundled with `uv`; the future for the `uv` ecosystem, not yet the default. We will, this week, compare hatchling and setuptools head-to-head on the worked example, and survey the others in Lecture 2.

The artifacts are wheels and sdists. **A wheel** (PEP 427; "Daniel Holth, 2012") is the binary distribution format: a ZIP file with `.whl` extension, named `pkgname-1.2.3-py3-none-any.whl` (or with platform tags for native extensions, `pkgname-1.2.3-cp313-cp313-manylinux_2_28_x86_64.whl`). It installs without running any user code at install time. **An sdist** (source distribution; a tarball, `pkgname-1.2.3.tar.gz`) contains the source files needed to *build* a wheel; `pip install` will fall back to building from sdist if no wheel matches your platform. The convention since 2018: always ship both. Wheels are what most users install; sdists are the source-of-truth and what archive/research/audit consumers need.

The platform story is **manylinux** (PEP 600, "Nathaniel Smith, 2019"). A wheel with native code has a "platform tag" — `linux_x86_64` is too restrictive (which glibc? which libstdc++?), so PyPA defined the *manylinux* tag family. `manylinux_2_28_x86_64` means "Linux x86_64 with glibc 2.28 or newer" (CentOS 8 / RHEL 8 baseline; current as of 2026). You build inside a manylinux Docker image (provided by `pypa/manylinux` on Docker Hub and GHCR), audit the wheel with `auditwheel`, and the result is portable to any Linux distro newer than the policy baseline. macOS has its own family (`macosx_11_0_arm64`, `macosx_10_15_x86_64`). Windows has `win_amd64` and `win_arm64`. We will, this week, **build manylinux wheels locally with `cibuildwheel`** and verify them with `auditwheel show`. The full PEP 600 path is more than one week's work; the introduction is enough to read it.

The locking story is **`uv.lock` / `poetry.lock` / `pip-tools` `requirements.lock`**. There is a fundamental distinction between *pinning* (the developer's local `requirements.txt` has versions, but transitives float) and *locking* (every transitive is pinned by version *and hash*, on every platform you support; the resolution is fully reproducible). PEP 751 (Brett Cannon et al., 2024; provisional as of early 2026) proposes a standardised `pylock.toml` format; in practice `uv.lock` and `poetry.lock` are the dominant lockfile formats today, and they are not interchangeable. We will write a `pyproject.toml` whose dependencies are declared in PEP 621 syntax, and an `uv.lock` produced from it. We will *not* ship `requirements.txt`.

The publishing story has three modes. **Mode 1** (legacy, still common): use `twine` with an API token from your PyPI account, stored as a GitHub Actions secret. Works; brittle (token rotation, scope, leak risk). **Mode 2** (modern, the recommended path): **trusted publishing** via PEP 740. Configure PyPI to trust a specific GitHub Actions workflow on a specific repository. The workflow uses GitHub's OIDC identity to request a short-lived token from PyPI at publish time. *No long-lived secret is stored anywhere.* This is the default for new projects in 2026; the `pypa/gh-action-pypi-publish` action handles it. **Mode 3** (the toolchain-native option): `uv publish` or `hatch publish` invokes Mode 1 or Mode 2 depending on configuration. We will set up Mode 2 in the mini-project.

The versioning story is short. **CalVer** (calendar-based: `2026.5.14`, `2026.04.0`) is right for "shipped on a schedule, no API stability claim" — e.g., Ubuntu, `pip` itself, `cibuildwheel`. **SemVer** (semantic: `MAJOR.MINOR.PATCH`, `2.3.1`) is right for libraries with consumers depending on the public API — bump major on breaking changes, minor on additions, patch on fixes. **`setuptools_scm`** (Ronny Pfannschmidt, 2010) derives the version from git tags automatically; the package version is `git describe`-derived; no `__version__` literal anywhere in the source. We will use `setuptools_scm` in the worked example because it eliminates a class of bugs (the version literal that nobody updates).

The deliverable for the week is a **published TestPyPI package**. You write a small library — a 50–150 line single-module package; a CLI utility, a helper library, a data-format parser, anything trivial — you write its `pyproject.toml`, you build with `python -m build`, you upload to TestPyPI with `twine` or `uv publish`, you install in a clean venv to verify, and you set up a GitHub Actions workflow that builds and publishes on every `v*.*.*` git tag using trusted publishing. The artifact in your portfolio is a TestPyPI URL plus a 700-word memo on the choices you made: which backend, what versioning scheme, why locked instead of pinned, what your CI does.

## Learning objectives

By the end of this week, you will be able to:

- **Cite** PEP 517 / 518 / 621 / 660 by number and explain what each one defines. Read the full text of each at least once (PEP 517: <https://peps.python.org/pep-0517/>; PEP 518: <https://peps.python.org/pep-0518/>; PEP 621: <https://peps.python.org/pep-0621/>; PEP 660: <https://peps.python.org/pep-0660/>).
- **Write** a complete `pyproject.toml` from scratch: `[build-system]`, `[project]`, `[project.optional-dependencies]`, `[project.scripts]`, `[project.urls]`, and a backend-specific table (`[tool.hatch.*]` or `[tool.setuptools.*]`). Validate it parses (`python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`).
- **Distinguish** the build backends — setuptools, hatchling, flit-core, pdm-backend, poetry-core, uv_build — on first principles: what each one is good at, what its TOML looks like, and when to pick which. Cite the relevant docs.
- **Build** a wheel and an sdist with `python -m build` (or `uv build` or `hatch build`). Verify the wheel installs cleanly in a fresh `python3 -m venv` and that the imports work.
- **Articulate** the wheel filename convention: `name-version-pythontag-abitag-platformtag.whl`. Read a wheel filename and predict where it installs. Cite PEP 427 (<https://peps.python.org/pep-0427/>) and PEP 425 (<https://peps.python.org/pep-0425/>).
- **Explain** the manylinux story: PEP 600, the `manylinux_2_28` baseline, the `pypa/manylinux` Docker images, the role of `auditwheel`. Build a manylinux wheel locally using `cibuildwheel` or by running `pypa/manylinux` directly. Repository: <https://github.com/pypa/manylinux>.
- **Compare** pinning versus locking. Generate an `uv.lock` from a `pyproject.toml`. Articulate why a lockfile is required for reproducible builds and what shipping `requirements.txt` instead loses.
- **Publish** a package to TestPyPI via two paths: (a) `python -m build && twine upload --repository testpypi dist/*` with an API token, and (b) trusted publishing via GitHub Actions OIDC with `pypa/gh-action-pypi-publish`. Document the trusted-publishing setup at <https://docs.pypi.org/trusted-publishers/>.
- **Choose** a versioning strategy (CalVer / SemVer / `setuptools_scm`) and articulate the trade-offs in two sentences. Cite <https://semver.org/> and <https://calver.org/>.
- **Read** a `pyproject.toml` from a major OSS project (`numpy`, `pip`, `httpx`) and identify every section, every directive, and every PEP it derives from.
- **Diagnose** the canonical packaging failures: (1) editable install fails because backend does not support PEP 660; (2) wheel is "platform-specific" (`linux_x86_64`) but should be `none-any` because it is pure Python; (3) manylinux wheel was built outside the docker image and gets rejected by `auditwheel`; (4) `pip install` fails because a transitive dep had a new major version that broke compatibility (the lockfile would have caught it).

## Prerequisites

- **C17 Weeks 1–8** completed. In particular: Week 8 (you have a `.so` and you want to ship it — this is the week you do); Week 7 (the profiling discipline carries over: measure your CI build time, do not just "ship faster builds" without numbers).
- **Python 3.11+ (3.13 preferred).** `tomllib` is in the stdlib since 3.11 (we will use it for parsing `pyproject.toml` in the exercises).
- **`pip`, `build`, and either `uv` or `hatch`.** Install: `pip install build hatch`. Install `uv` per <https://docs.astral.sh/uv/getting-started/installation/>.
- **`twine`** for the legacy upload path: `pip install twine`. Optional if you only ever use `uv publish` or trusted publishing.
- **A TestPyPI account** at <https://test.pypi.org/account/register/>. *Different from your PyPI account; register both, they are unrelated.*
- **A GitHub account and a GitHub repository** for the mini-project (the trusted-publishing flow requires GitHub Actions).
- **Docker (optional)** for the manylinux exercise; the manylinux Docker image is the canonical way to build Linux wheels. macOS users can skip the Docker step and rely on `cibuildwheel` in CI.
- **A C compiler** (Week 8 prerequisite) if you want to extend the worked example to include a native module.

## Topics covered

- **The standards** — PEP 517 (build-system interface), 518 (the `[build-system]` table; isolated builds), 621 (the `[project]` table; metadata), 660 (editable installs). Read each once.
- **`pyproject.toml` as the single source of truth** — every modern project has one file. `setup.py` is optional; `setup.cfg` is optional; `MANIFEST.in` is optional in most backends. Everything declarative is in `pyproject.toml`.
- **Build-backend survey** — setuptools, hatchling, flit-core, pdm-backend, poetry-core, uv_build. One paragraph each. Worked example uses hatchling for pure-Python and setuptools for native-extension paths.
- **Wheels vs. sdists** — the two artifact types, their roles, when each is built. Wheel filename convention. Inspecting a wheel with `unzip -l`.
- **Platform tags and manylinux** — PEP 425 (compatibility tags), PEP 427 (wheel format), PEP 600 (the perennial manylinux policy). The `manylinux_2_28` baseline. Building wheels inside `quay.io/pypa/manylinux2_28_x86_64`.
- **`auditwheel` and `delocate`** — wheel post-processing: `auditwheel show` to see what library a wheel needs, `auditwheel repair` to bundle them. `delocate` for macOS.
- **`cibuildwheel`** — the canonical multi-platform wheel-building CI tool. <https://github.com/pypa/cibuildwheel>. Build wheels for Linux × {x86_64, aarch64}, macOS × {x86_64, arm64}, Windows × {x86_64, arm64}, Python 3.10–3.13, all from one GitHub Actions workflow.
- **Pinning vs. locking** — `pip-tools` (`pip-compile`), `uv.lock`, `poetry.lock`. Why every production project needs a lockfile. PEP 751 (provisional, the future standard).
- **Publishing** — `twine` (the legacy path); `uv publish`, `hatch publish` (the toolchain-native paths); trusted publishing via PEP 740 OIDC (the recommended path for new projects).
- **TestPyPI vs. PyPI** — what differs (a separate index for testing; different account; not promoted to PyPI; eventual deletion of old uploads), what is the same (the wire protocol, the wheel format, the auth flow).
- **Versioning strategies** — CalVer, SemVer, `setuptools_scm`. The trade-offs. The default recommendation for libraries (SemVer with `setuptools_scm` for derivation).
- **The full CI flow** — GitHub Actions workflow that on every `v*.*.*` tag: checks out, builds wheels via `cibuildwheel`, runs the test suite, publishes via trusted publishing, attaches the artifacts to a GitHub Release.

## Weekly schedule (~33h intensive)

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | PEPs 517/518/621/660; `pyproject.toml` anatomy              | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | Build-backend survey; hatchling vs. setuptools head-to-head | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Wednesday | Wheels, sdists, platform tags, manylinux                    | 2h       | 1.5h      | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 6.5h        |
| Thursday  | Locking, publishing, trusted publishing; mini-project kickoff | 0h     | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Friday    | Mini-project: build the package; write the pyproject.toml   | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Saturday  | Mini-project: TestPyPI upload; CI workflow; verify install  | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                            | 0h       | 0h        | 0h         | 0.5h      | 1h       | 0h           | 0h         | 1.5h        |
| **Total** |                                                             | **6h**   | **4.5h**  | **3h**     | **3h**    | **7h**   | **7h**       | **2.5h**   | **33h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | PEP indices, packaging.python.org, manylinux GitHub, build-backend docs, trusted publishing docs |
| [lecture-notes/01-peps-and-pyproject-toml.md](./lecture-notes/01-peps-and-pyproject-toml.md) | PEP 517/518/621/660 walkthrough; anatomy of pyproject.toml; the `[build-system]` and `[project]` tables |
| [lecture-notes/02-build-backends-and-the-survey.md](./lecture-notes/02-build-backends-and-the-survey.md) | setuptools, hatchling, flit-core, pdm-backend, poetry-core, uv_build; how to pick |
| [lecture-notes/03-wheels-manylinux-locking-publishing.md](./lecture-notes/03-wheels-manylinux-locking-publishing.md) | Wheel format; platform tags; manylinux_2_28; `cibuildwheel`; locking; trusted publishing |
| [exercises/exercise-01-write-pyproject.py](./exercises/exercise-01-write-pyproject.py) | Parse and validate a pyproject.toml; emit a metadata report; generate one from a template |
| [exercises/exercise-01-sample-pyproject.toml](./exercises/exercise-01-sample-pyproject.toml) | The sample TOML for Exercise 1 |
| [exercises/exercise-02-build-and-inspect.py](./exercises/exercise-02-build-and-inspect.py) | Programmatically invoke `python -m build`; inspect the resulting wheel; print the metadata |
| [exercises/exercise-02-mypkg-pyproject.toml](./exercises/exercise-02-mypkg-pyproject.toml) | A complete pyproject.toml for a 30-line example package |
| [exercises/exercise-03-publish-flow.py](./exercises/exercise-03-publish-flow.py) | Walk the TestPyPI publish flow (dry-run; print every command and what it does); validate the GitHub Actions workflow |
| [exercises/exercise-03-publish.yml](./exercises/exercise-03-publish.yml) | The reference GitHub Actions workflow for trusted publishing |
| [exercises/SOLUTIONS.md](./exercises/SOLUTIONS.md) | Expected outputs, common errors, the reasoning behind the templates |
| [challenges/challenge-01-multi-backend-comparison.md](./challenges/challenge-01-multi-backend-comparison.md) | Build the same package with three backends; compare wheel content, metadata, build time |
| [challenges/challenge-02-cibuildwheel-matrix.md](./challenges/challenge-02-cibuildwheel-matrix.md) | Set up cibuildwheel for a tiny C-extension package; produce wheels for the 3×4 platform/Python matrix |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~7h) |
| [mini-project/README.md](./mini-project/README.md) | Ship a real package to TestPyPI end-to-end; trusted publishing CI; install in a clean venv |
| [mini-project/sample-pyproject.toml](./mini-project/sample-pyproject.toml) | The starter pyproject.toml for the mini-project |

## Stretch

- Read [PEP 517](https://peps.python.org/pep-0517/) end-to-end (~30 minutes). The interface PEP. Brett Cannon, Nathaniel Smith. The defining doc for "what a build backend must do."
- Read [PEP 621](https://peps.python.org/pep-0621/) end-to-end (~25 minutes). Every field in the `[project]` table. The reference you go back to when you forget what `dynamic` means.
- Read [PEP 660](https://peps.python.org/pep-0660/) end-to-end (~20 minutes). Editable installs. Why `pip install -e .` works without `setup.py develop`.
- Read [PEP 600](https://peps.python.org/pep-0600/) end-to-end (~30 minutes). The "perennial" manylinux specification. The replacement for the long line of `manylinux1`, `manylinux2010`, `manylinux2014`.
- Read the [packaging.python.org tutorial: "Packaging Python Projects"](https://packaging.python.org/en/latest/tutorials/packaging-projects/) — the canonical end-to-end walkthrough. ~40 minutes. The official PyPA tutorial; updated for the modern stack.
- Read the [hatch documentation](https://hatch.pypa.io/) — at least the "Quickstart" and "Configuration" pages. ~30 minutes. Hatch is hatchling's frontend; understanding both is a 30-minute investment.
- Read [`numpy`'s `pyproject.toml`](https://github.com/numpy/numpy/blob/main/pyproject.toml) — about 200 lines. The reference for "non-trivial native-extension `pyproject.toml`." Identify the build backend, the C-extension declarations, the version source. ~20 minutes.
- Read [`pip`'s own `pyproject.toml`](https://github.com/pypa/pip/blob/main/pyproject.toml) — pip uses `setuptools` and `setuptools_scm`. The reference for "self-referential": the tool that installs packages is itself a package. ~15 minutes.
- Read the [PyPI Trusted Publishing docs](https://docs.pypi.org/trusted-publishers/) end-to-end (~20 minutes). The defining reference for setting up OIDC publishing.
- Watch one talk from [PyCon 2024 on packaging](https://www.youtube.com/c/PyCon2024). Brett Cannon's and Pradyun Gedam's annual "state of packaging" updates are the canonical reference for "what changed this year." ~45 minutes.

## Up next

[Week 10 — Testing, Tox, and CI](../week-10-testing-tox-and-ci/) — You shipped a package this week. Next week we make sure it does not break. `pytest`'s plugin model. `tox` (and its modern alternative, `nox`) for cross-version testing. Coverage. Property-based testing with `hypothesis`. Mutation testing. The CI matrix you wire your GitHub Actions to. Everything that goes into "I trust this 1.0 release."
