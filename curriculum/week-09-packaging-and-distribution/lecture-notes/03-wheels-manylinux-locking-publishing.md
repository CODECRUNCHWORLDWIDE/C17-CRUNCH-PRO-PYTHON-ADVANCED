# Lecture 3 — Wheels, manylinux, Locking, and Publishing

> **Duration:** ~2 hours. **Outcome:** You can read a wheel filename and predict where it installs. You can build a manylinux wheel locally (with Docker) or in CI (with cibuildwheel). You can explain the difference between pinning and locking and produce a lockfile from a `pyproject.toml`. You can set up trusted publishing to PyPI from a GitHub Actions workflow, with no API token stored anywhere. You have, by the end of the lecture, an entire publish pipeline mapped out.

## 1. The wheel format

A wheel (PEP 427, Daniel Holth 2012: <https://peps.python.org/pep-0427/>) is the binary distribution format for Python packages. Mechanically it is a ZIP file with a `.whl` extension. Inside, two top-level directories:

```
mypkg-0.1.0-py3-none-any.whl
├── mypkg/                          # the package source
│   ├── __init__.py
│   └── module.py
└── mypkg-0.1.0.dist-info/          # the metadata
    ├── METADATA                    # PEP 621-derived; what shows on PyPI
    ├── RECORD                      # list of every file + sha256
    ├── WHEEL                       # wheel format version, generator
    └── entry_points.txt            # [project.scripts] etc.
```

The contract: `pip install mypkg-0.1.0-py3-none-any.whl` *extracts* the ZIP into `site-packages`. No user code runs at install time (unlike sdist, which runs the build backend). This is the property that makes wheels safe to cache, distribute, and pre-build in CI.

The filename is structured. PEP 425 (compatibility tags, Daniel Holth 2012: <https://peps.python.org/pep-0425/>) defines the format:

```
{distribution}-{version}(-{build-tag})?-{python-tag}-{abi-tag}-{platform-tag}.whl
```

`mypkg-0.1.0-py3-none-any.whl`:

- **`mypkg`** — the distribution name (case-normalised per PEP 503).
- **`0.1.0`** — the version (PEP 440).
- *(no build tag in this example)*
- **`py3`** — the Python implementation tag. `py3` = "any Python 3.x"; `cp313` = "CPython 3.13 specifically"; `pp310` = "PyPy 3.10."
- **`none`** — the ABI tag. `none` = "no ABI dependency" (pure-Python). `cp313` = "matches CPython 3.13's ABI" (a built extension). `abi3` = "stable ABI, PEP 384" (any 3.x).
- **`any`** — the platform tag. `any` = "any platform" (pure Python). `manylinux_2_28_x86_64`, `macosx_11_0_arm64`, `win_amd64` for native code.

A pure-Python wheel is `py3-none-any`: works on every Python 3.x on every platform. A CPython 3.13 native wheel for Linux x86_64 is `cp313-cp313-manylinux_2_28_x86_64`: only works on CPython 3.13 on a Linux x86_64 with glibc 2.28+. The wheel filename *is* the compatibility check; `pip` reads it, compares against the local interpreter, and installs only matching wheels.

Inspect a wheel:

```bash
$ unzip -l mypkg-0.1.0-py3-none-any.whl
Archive:  mypkg-0.1.0-py3-none-any.whl
  Length      Date    Time    Name
---------  ---------- -----   ----
      127  2026-05-14 10:12   mypkg/__init__.py
      243  2026-05-14 10:12   mypkg/module.py
      512  2026-05-14 10:12   mypkg-0.1.0.dist-info/METADATA
       95  2026-05-14 10:12   mypkg-0.1.0.dist-info/WHEEL
      271  2026-05-14 10:12   mypkg-0.1.0.dist-info/RECORD

$ unzip -p mypkg-0.1.0-py3-none-any.whl mypkg-0.1.0.dist-info/METADATA
Metadata-Version: 2.3
Name: mypkg
Version: 0.1.0
Summary: Demo package.
Author-email: Ada Lovelace <ada@example.org>
Requires-Python: >=3.11
License-Expression: MIT
Requires-Dist: numpy>=1.26
...
```

The `METADATA` file is the PEP 621 metadata serialised in `Metadata-Version 2.3` (RFC822-style key-value plus a trailing description). This is what PyPI parses to populate the project page; this is what `pip show mypkg` reads after install.

## 2. sdists

A source distribution (sdist) is `mypkg-0.1.0.tar.gz`: a gzipped tarball of the source needed to build a wheel. The contents:

```
mypkg-0.1.0/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── mypkg/
│       ├── __init__.py
│       └── module.py
└── PKG-INFO                # the metadata, same format as the wheel METADATA
```

The rules: an sdist *must* be installable by `pip` invoking the PEP 517 build backend. The backend reads the sdist, runs `build_wheel`, produces a wheel, and `pip` installs the wheel. This is the fallback when no pre-built wheel matches the user's platform.

The convention since 2018: **always upload both sdist and wheel.** Wheels are what most users install (fast, no build step); sdists are what archivists, downstream packagers (Debian, Conda), researchers, and security auditors need. The PyPA tooling makes both by default: `python -m build` produces both.

A common failure mode: shipping a wheel without an sdist. The wheel works for the matching platforms; users on platforms you did not build for see a confusing error from `pip` ("no matching distribution found"). If you had also shipped an sdist, `pip` would have fallen back to building from source. Sdist coverage is your fallback policy.

## 3. Platform tags and manylinux

The platform tag is where the wheels-vs-platforms story gets interesting.

For a pure-Python wheel, the tag is `any`. Trivially portable. Done.

For a wheel with native code, the tag has to encode *which compiled environment the wheel is compatible with*. The naive approach: tag the wheel with the build environment's specifics (`linux_x86_64_glibc_2.39`, where 2.39 is the glibc version on the build machine). Pip on a different machine with glibc 2.31 sees the tag, fails the match, refuses to install. Correct, but useless — nobody can install your wheel unless they have the exact same glibc.

The 2014 solution was `manylinux1` (PEP 513, Robert McGibbon, Nathaniel Smith): "Linux wheels that work on many distros." The idea: define a *baseline* of an old Linux distro's glibc and libstdc++, build inside a Docker image with that baseline, and any wheel built that way works on any Linux distro at-or-newer-than the baseline. `manylinux1` was CentOS 5; `manylinux2010` was CentOS 6; `manylinux2014` was CentOS 7. Each had a fixed baseline.

PEP 600 (Nathaniel Smith, 2019: <https://peps.python.org/pep-0600/>) replaced the per-distro tags with a *perennial* policy: `manylinux_<glibc_major>_<glibc_minor>_<arch>`. `manylinux_2_28_x86_64` = "any Linux x86_64 with glibc >= 2.28" (CentOS 8 / RHEL 8 / Debian 10 baseline). `manylinux_2_34_x86_64` = "glibc >= 2.34" (Ubuntu 22.04 baseline). The PEP defines the policy generically; the PyPA `manylinux` repository maintains Docker images for the active baselines.

As of early 2026, the relevant baselines are:

- **`manylinux_2_28`** (CentOS 8 / RHEL 8 / Debian 10 / Ubuntu 20.04) — the broadest current target. Works on almost every Linux system in production use. Docker image: `quay.io/pypa/manylinux_2_28_x86_64`, `_aarch64`.
- **`manylinux_2_34`** (RHEL 9 / Ubuntu 22.04) — narrower; newer libc features available. Docker image: `quay.io/pypa/manylinux_2_34_x86_64`, `_aarch64`.
- **`musllinux_1_2`** (Alpine Linux baseline; PEP 656) — for musl-libc Linux. Smaller but important: many Docker container builds use Alpine. Docker image: `quay.io/pypa/musllinux_1_2_x86_64`.

For macOS, the tags are:

- **`macosx_11_0_arm64`** (Apple Silicon; macOS 11+).
- **`macosx_10_15_x86_64`** (Intel Mac; macOS 10.15+).
- **`macosx_11_0_universal2`** (single wheel with both arm64 and x86_64 binaries; double the size, single install).

For Windows:

- **`win_amd64`** (x86_64).
- **`win_arm64`** (ARM, increasingly relevant with Surface Pro X / Windows-on-ARM).

The naming is unforgiving. A wheel mistakenly tagged `linux_x86_64` (the bare platform tag, with no `manylinux` prefix) is *rejected* by PyPI's upload — PyPI requires the manylinux-style tag for Linux wheels, because the bare tag's portability claim is too weak. PyPI will accept `manylinux_2_28_x86_64` but not `linux_x86_64`.

## 4. Building manylinux wheels: the Docker dance

The canonical way to build a manylinux wheel:

```bash
docker run --rm -v "$PWD:/io" quay.io/pypa/manylinux_2_28_x86_64 \
  bash -c '
    /opt/python/cp313-cp313/bin/pip wheel /io --wheel-dir /tmp/wheels
    auditwheel repair /tmp/wheels/*.whl --plat manylinux_2_28_x86_64 -w /io/dist/
  '
```

Step by step:

1. **`docker run --rm -v "$PWD:/io" quay.io/pypa/manylinux_2_28_x86_64`** — start a container from the manylinux image. The image has multiple Python installations (`/opt/python/cp310-cp310`, `cp311-cp311`, ..., `cp313-cp313`), a CentOS 8-baseline glibc, gcc, and `auditwheel` pre-installed. The `-v "$PWD:/io"` mount makes your project visible inside the container.

2. **`pip wheel /io --wheel-dir /tmp/wheels`** — build a wheel for the project using one of the container's Python installations. Inside the container, your wheel will get tagged with the linux_x86_64 bare platform tag (because the build environment is `linux_x86_64`).

3. **`auditwheel repair`** — the magic step. `auditwheel` reads the wheel, finds every shared library it depends on, *bundles* those libraries into the wheel, *rewrites* the dynamic linker rpath/runpath to find the bundled libraries first, and *retags* the wheel as `manylinux_2_28_x86_64` if every bundled library satisfies the manylinux policy. The output is a wheel that has no external dependencies beyond the manylinux baseline.

The result: a `dist/mypkg-0.1.0-cp313-cp313-manylinux_2_28_x86_64.whl` that installs cleanly on any Linux x86_64 with glibc 2.28+. Tested against the manylinux policy. Ready for PyPI.

The same flow for aarch64 (ARM64 Linux):

```bash
docker run --rm --platform=linux/arm64 -v "$PWD:/io" \
  quay.io/pypa/manylinux_2_28_aarch64 \
  bash -c '...'
```

Note `--platform=linux/arm64` if you are on an x86_64 host (Docker emulates via qemu, which is slow but works).

For macOS, the equivalent of `auditwheel` is **`delocate`** (Matthew Brett: <https://github.com/matthew-brett/delocate>):

```bash
pip wheel . --wheel-dir dist
delocate-wheel -v dist/*.whl  # bundles dylibs; rewrites @rpath
```

For Windows, there is no equivalent tool — Windows DLLs are typically system-resident and you do not bundle them. The wheel is tagged `win_amd64` directly.

## 5. `cibuildwheel`: the multi-platform wheel-building CI tool

Doing the Docker dance by hand is tedious. Doing it for {Linux x86_64, Linux aarch64, macOS x86_64, macOS arm64, Windows x86_64, Windows arm64} × {Python 3.10, 3.11, 3.12, 3.13} is 24 wheels per release. This is what `cibuildwheel` exists for.

`cibuildwheel` (PyPA, 2018+: <https://cibuildwheel.pypa.io/>) is a CI-side tool that, in a single workflow job, builds wheels for an entire platform/Python matrix. It runs the manylinux Docker images, calls `auditwheel` / `delocate`, and emits a `wheelhouse/` directory of properly-tagged wheels.

Configured in `pyproject.toml`:

```toml
[tool.cibuildwheel]
build = ["cp310-*", "cp311-*", "cp312-*", "cp313-*"]
skip = ["*-musllinux_*", "*-win32"]
test-requires = "pytest"
test-command = "pytest {project}/tests"

[tool.cibuildwheel.linux]
manylinux-x86_64-image = "manylinux_2_28"
manylinux-aarch64-image = "manylinux_2_28"

[tool.cibuildwheel.macos]
archs = ["x86_64", "arm64"]

[tool.cibuildwheel.windows]
archs = ["AMD64"]
```

And invoked from GitHub Actions:

```yaml
# .github/workflows/wheels.yml
name: build-wheels

on:
  push:
    tags: ["v*"]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-13, macos-14, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Build wheels
        uses: pypa/cibuildwheel@v2.20.0

      - uses: actions/upload-artifact@v4
        with:
          name: cibw-wheels-${{ matrix.os }}-${{ strategy.job-index }}
          path: ./wheelhouse/*.whl
```

The matrix runs four GitHub Actions jobs in parallel (Ubuntu, two macOS — Intel and Apple Silicon — and Windows). Each job builds wheels for every Python in its `build` filter. The output is uploaded as job artifacts and then collected and published to PyPI in a later job.

Time to first wheel on a fresh repo: about 15 minutes to write the config, ~30 minutes for the first CI run, and from then on a `git tag v0.1.0 && git push --tags` is the entire release ritual.

## 6. Pinning vs. locking

Now switch gears. The wheels-and-platforms story is the *production output*. The pinning-vs-locking story is *how you control what your project consumes*.

The distinction.

**Pinning** is what you put in `pyproject.toml`'s `[project].dependencies`:

```toml
dependencies = [
    "numpy >= 1.26",
    "httpx >= 0.27",
]
```

These are *version ranges* for *direct* dependencies. They are what a downstream user sees. They are intentionally loose so that `pip install mypkg` works across a range of NumPy/httpx versions.

**Locking** is what you put in a *lockfile*. A lockfile records the *exact* version *and hash* of every direct *and transitive* dependency, on every platform you support, at one moment in time. A `uv.lock`:

```toml
# uv.lock - auto-generated; do not edit by hand.
version = 1
requires-python = ">=3.11"

[[package]]
name = "numpy"
version = "1.26.4"
sdist = { name = "numpy-1.26.4.tar.gz", hash = "sha256:..." }
wheels = [
    { name = "numpy-1.26.4-cp313-cp313-manylinux_2_28_x86_64.whl", hash = "sha256:..." },
    { name = "numpy-1.26.4-cp313-cp313-macosx_11_0_arm64.whl", hash = "sha256:..." },
    # ... 30+ more wheels for the matrix ...
]

[[package]]
name = "httpx"
version = "0.27.2"
sdist = { name = "httpx-0.27.2.tar.gz", hash = "sha256:..." }
wheels = [
    { name = "httpx-0.27.2-py3-none-any.whl", hash = "sha256:..." },
]
dependencies = [
    "anyio",
    "certifi",
    "httpcore",
    "idna",
    "sniffio",
]
# ... entries for anyio, certifi, httpcore, idna, sniffio ...
```

Every package, every version, every wheel hash. Restoring from this lockfile produces *exactly* the same dependency tree on every machine, every time. `uv sync` (or `pip install --require-hashes`) reads the lockfile and installs precisely those wheels.

Why two layers?

- **Pins (in `pyproject.toml`)** are for *downstream consumers*. A user who installs your library wants a working install; they don't care which exact NumPy version, as long as it is compatible. Pins give them flexibility.
- **Locks (in `uv.lock`)** are for *you*. Your CI, your developers, your production deploys all want *the exact same dependency tree*. Locks give you reproducibility.

The two coexist. Your library ships with `pyproject.toml` containing pins. Your application's repo ships with `pyproject.toml` *plus* `uv.lock`. The application's CI installs from `uv.lock` for reproducibility; the library's distribution does not use a lockfile (downstream consumers do not want your locked transitives).

**The default-wrong pattern**: shipping a `requirements.txt` with exact pins (`numpy==1.26.4`) for a *library*. This makes the library brittle (every minor numpy update can conflict with your pin) and is the wrong shape — applications pin transitively, libraries pin loosely.

The tools:

- **`uv.lock`** (Astral, 2024). Single file, multi-platform, fast resolution. The modern default.
- **`poetry.lock`** (poetry, 2018). Mature, single-platform per lockfile, slower resolution.
- **`pdm.lock`** (pdm, 2020). Single file, multi-platform.
- **`requirements.txt` via `pip-compile --generate-hashes`** (pip-tools, 2015). The OG; produces a `requirements.txt` with hashes that `pip install --require-hashes` validates.

PEP 751 (provisional, 2024: <https://peps.python.org/pep-0751/>) proposes a *standard* `pylock.toml` format. As of early 2026 it is provisional; `uv.lock` and `poetry.lock` are the dominant lockfile formats and they are not interchangeable.

Generating `uv.lock`:

```bash
uv lock    # reads pyproject.toml, resolves, writes uv.lock
uv sync    # reads uv.lock, installs into the venv
```

Generating `requirements.txt` with hashes (for projects not yet on `uv`):

```bash
pip-compile --generate-hashes -o requirements.lock pyproject.toml
pip install --require-hashes -r requirements.lock
```

The discipline: **applications lock; libraries pin loosely.** Always.

## 7. Versioning

Three strategies:

**SemVer** (<https://semver.org/>) — `MAJOR.MINOR.PATCH`. Bump MAJOR on breaking API changes, MINOR on additions, PATCH on backward-compatible fixes. The default for libraries with consumers. The discipline: every breaking change moves the major number; every release-with-no-API-change is a patch. Consumers can specify `requests >= 2, < 3` and trust that the upper bound is meaningful.

**CalVer** (<https://calver.org/>) — calendar-based: `YYYY.MM.DD`, `YYYY.MM`, `YY.MAJOR.MINOR`. Right for "we ship on a schedule and do not promise API stability." Ubuntu (`24.04`), Twisted (`24.7.0`), `pip` itself (`24.0`), `cibuildwheel`. The discipline: do not pretend to SemVer if you do not maintain the API contract.

**`setuptools_scm` (or `hatch-vcs`)** — derive the version from `git describe --tags`. The version literal does not exist in the source; the build backend reads git at build time. Eliminates the "I forgot to bump `__version__`" bug class. The version on `main` is something like `0.3.2.dev10+g3a4b5c6` (the next post-tag version, plus the dev counter, plus the short hash); the version on a `v0.3.2` tag is exactly `0.3.2`.

In `pyproject.toml` with setuptools:

```toml
[build-system]
requires = ["setuptools >= 67", "setuptools_scm[toml] >= 8"]
build-backend = "setuptools.build_meta"

[project]
name = "mypkg"
dynamic = ["version"]
# ...

[tool.setuptools_scm]
write_to = "src/mypkg/_version.py"   # optional; writes the version to a file
```

With hatchling:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs >= 0.4"]
build-backend = "hatchling.build"

[project]
name = "mypkg"
dynamic = ["version"]
# ...

[tool.hatch.version]
source = "vcs"
```

The release flow becomes: `git tag v0.3.2 && git push --tags`. The CI builds the wheel; the wheel's version is `0.3.2`; PyPI accepts it. No version literal ever changed by hand.

Recommendation for new projects: **SemVer + `setuptools_scm` (or `hatch-vcs`)**. The clear default.

## 8. Publishing — three paths

Once you have a wheel and an sdist, you upload them to PyPI (or TestPyPI). Three paths.

### Path 1: `twine` with an API token (the legacy path)

```bash
python -m build              # produces dist/*.whl and dist/*.tar.gz
twine upload dist/*          # uploads to PyPI
twine upload --repository testpypi dist/*  # uploads to TestPyPI
```

`twine` reads credentials from `~/.pypirc` or from `TWINE_USERNAME` / `TWINE_PASSWORD` environment variables. The "username" for token auth is `__token__`; the "password" is the API token string from <https://pypi.org/manage/account/token/>.

In CI:

```yaml
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: twine upload dist/*
```

The downsides:

- **Long-lived secret stored in CI.** If your repo's secrets are leaked (compromised account, misconfigured action, accidental log), the token is in the wild.
- **Token rotation is manual.** Every 12 months (or after any incident) you regenerate the token and update GitHub Actions secrets.
- **Scope is per-project at best.** PyPI tokens can be scoped to a single project, but the secret is still a secret.

Path 1 is what every project did from 2016 to 2023. It still works. It is no longer the recommended default.

### Path 2: Trusted publishing (the recommended path)

Trusted publishing (PEP 740, 2024: <https://peps.python.org/pep-0740/>; PyPI docs: <https://docs.pypi.org/trusted-publishers/>) is the OIDC-based replacement for API tokens.

The flow:

1. **Configure PyPI to trust a specific GitHub Actions workflow.** On <https://pypi.org/manage/account/publishing/>, register a "Trusted Publisher" tied to your GitHub repo and workflow file (e.g., `owner: example-org`, `repository: mypkg`, `workflow: publish.yml`, `environment: pypi`).

2. **In the GitHub Actions workflow**, request an OIDC token from GitHub's identity provider. The `pypa/gh-action-pypi-publish` action does this transparently.

3. **The action presents the OIDC token to PyPI.** PyPI verifies the token's claims (repo, workflow, environment) against its Trusted Publisher config. If they match, PyPI mints a short-lived API token (valid for ~15 minutes) and uses it for the upload.

4. **The short-lived token expires.** No long-lived secret exists anywhere.

The workflow:

```yaml
# .github/workflows/publish.yml
name: publish

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/mypkg
    permissions:
      id-token: write  # required for OIDC

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Build
        run: |
          python -m pip install build
          python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # No `with:` block needed. Trusted publishing is automatic.
```

The two important lines:

- **`permissions: id-token: write`** — grants the workflow permission to mint an OIDC token. Required for trusted publishing.
- **`uses: pypa/gh-action-pypi-publish@release/v1`** — the canonical action. It detects the OIDC environment and uses trusted publishing automatically; falls back to API token if `password: ${{ secrets.PYPI_API_TOKEN }}` is set.

The configuration on PyPI's side is a five-minute web-form fill at <https://pypi.org/manage/account/publishing/>. After that: no secret, no rotation, no leak risk.

This is the default for new projects in 2026. The PyPA tutorial uses it. The mini-project uses it.

### Path 3: `uv publish` and `hatch publish`

Both `uv` and `hatch` have their own `publish` subcommands that wrap one of the above paths:

```bash
uv publish              # uploads dist/* to PyPI
uv publish --publish-url https://test.pypi.org/legacy/  # to TestPyPI
hatch publish           # equivalent
```

These read API tokens from environment variables (`UV_PUBLISH_TOKEN`, `HATCH_INDEX_AUTH`) or from the `~/.pypirc` file. They are convenient for manual publishes from a developer machine. In CI you still want trusted publishing via `pypa/gh-action-pypi-publish` for the no-token property.

## 9. TestPyPI

TestPyPI (<https://test.pypi.org/>) is a separate instance of PyPI used for testing the publish flow. It has:

- A *separate account database*. You register on test.pypi.org independently of pypi.org.
- A *separate package namespace*. The name `mypkg` on TestPyPI is not the same as `mypkg` on PyPI.
- A *separate trusted-publishers config*. You set up trusted publishing on TestPyPI independently.
- A *grace policy*. Old uploads on TestPyPI may be pruned after some time. Do not rely on it as a permanent index.

The flow: publish to TestPyPI first. Verify the package page renders correctly, the metadata is right, the wheel installs cleanly in a fresh venv. Then publish to PyPI.

In CI, run trusted publishing to TestPyPI on every push to `main`, and to PyPI on every `v*` tag. Two trusted publishers, two PyPI accounts, two workflows.

## 10. The full pipeline, end to end

Putting it all together for a hypothetical pure-Python library `mypkg`:

```yaml
# .github/workflows/release.yml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # needed for setuptools_scm to see all tags

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Build sdist and wheel
        run: |
          python -m pip install build
          python -m build

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/p/mypkg
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/mypkg
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Three jobs:

1. **`build`** — build sdist and wheel. Upload as artifact.
2. **`publish-testpypi`** — download artifact, publish to TestPyPI via OIDC.
3. **`publish-pypi`** — download artifact, publish to PyPI via OIDC. Runs after TestPyPI succeeds.

For a project with native extensions, add a `build-wheels` job that calls `cibuildwheel` and uploads its `wheelhouse/` as the artifact, instead of (or in addition to) the simple `python -m build`.

This is the modern release pipeline. ~50 lines of YAML. No long-lived secrets. Reproducible. Auditable. The release ritual is `git tag v0.1.0 && git push --tags`; the workflow does the rest.

## 11. The mental model

You hold this in your head:

- **Source tree** + **`pyproject.toml`** → backend → **wheel + sdist** → PyPI → users' `pip install`.
- The standards (517/518/621/660) define the boundaries between source and backend.
- The platform tag in the wheel filename gates `pip install` per-machine.
- `manylinux` is the policy that lets one wheel install on many Linux distros.
- The lockfile (separate from `pyproject.toml`) records the resolved dep tree for reproducible installs.
- Trusted publishing replaces API tokens with OIDC; no secret stored.

That is the whole story. The mini-project drills it on a real package.

## 12. Reading

- PEP 427 (wheel format): <https://peps.python.org/pep-0427/>. ~15 minutes.
- PEP 425 (compatibility tags): <https://peps.python.org/pep-0425/>. ~15 minutes.
- PEP 600 (manylinux policy): <https://peps.python.org/pep-0600/>. ~30 minutes.
- PEP 740 (trusted publishing spec): <https://peps.python.org/pep-0740/>. ~25 minutes.
- The `pypa/manylinux` README: <https://github.com/pypa/manylinux>. ~15 minutes.
- The PyPA tutorial, "Packaging Python Projects" — the publish section: <https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives>. ~10 minutes.
- The PyPI trusted publishing docs: <https://docs.pypi.org/trusted-publishers/>. ~20 minutes.
- The cibuildwheel docs: <https://cibuildwheel.pypa.io/>. ~30 minutes.
- Pick one `cibuildwheel`-using project (cryptography, pydantic-core, numpy) and read its release workflow in `.github/workflows/`. ~20 minutes.
