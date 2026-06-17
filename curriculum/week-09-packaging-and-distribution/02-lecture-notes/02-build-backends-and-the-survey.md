# Lecture 2 — Build Backends: The Survey, the Trade-offs, the Choice

> **Duration:** ~2 hours. **Outcome:** You can name six PEP 517 build backends and articulate the niche each one occupies. You can write the `[build-system]` and backend-specific tables for setuptools and hatchling. You can switch a project from one backend to the other in under ten minutes. You can pick a backend for a new project on first principles.

## 1. The cast

PEP 517 (Lecture 1) is the interface. Every build backend implements that interface. As of early 2026, the backends in active use are, in rough order of market share for new projects:

1. **`setuptools`** — the historical default. Sole backend for the entire pre-PEP-517 era. Still the *only* common backend that handles arbitrary C/C++ extensions out of the box.
2. **`hatchling`** — the modern default for pure-Python. Backend of the `hatch` project manager. Ofek Lev, 2021.
3. **`flit-core`** — the smallest backend. Single-module packages with no machinery. Thomas Kluyver, 2015 (pre-dates PEP 517; was the prototype that informed it).
4. **`pdm-backend`** — backend of `pdm` (Python Development Master). Frost Ming, 2020. Broadly hatchling-equivalent for the build step; `pdm` adds environment and dep management.
5. **`poetry-core`** — backend of `poetry`. Sébastien Eustace, 2018. Predates PEP 621 by two years and has a non-standard `[tool.poetry]` metadata table; newer versions support PEP 621.
6. **`uv_build`** — Astral's backend, bundled with `uv`. Alpha as of early 2026; the future for projects all-in on `uv`.

Adjacent, niche but important:

- **`maturin`** — backend for Rust extensions (PyO3-based). Build `pyproject.toml`-managed Rust crates as Python wheels. <https://www.maturin.rs/>.
- **`setuptools-rust`** — setuptools plugin for Rust extensions. The older approach. <https://github.com/PyO3/setuptools-rust>.
- **`scikit-build-core`** — backend for CMake-based C/C++ projects. <https://scikit-build-core.readthedocs.io/>.
- **`meson-python`** — backend for Meson-based C/C++ projects. Used by NumPy and SciPy. <https://meson-python.readthedocs.io/>.
- **`pybind11`** as a build helper (works through setuptools or scikit-build-core).

We will cover the six main backends in this lecture and point at the adjacents for the cases where they are the right answer.

## 2. setuptools — the historical default

setuptools is the original. Phillip J. Eby wrote it in 2004 as `setuptools` to extend `distutils` (the long-deprecated stdlib packaging module, removed in Python 3.12). Every modern packaging idea — entry points, declarative metadata, the egg format, the wheel format (designed to replace the egg), `easy_install` (designed to be replaced by `pip`) — passed through setuptools first.

In 2026 setuptools is a PEP 517 backend like any other. Its `build-backend` is `setuptools.build_meta`. The `pyproject.toml` shape:

```toml
[build-system]
requires = ["setuptools >= 67", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mypkg"
version = "0.1.0"
description = "..."
# ... PEP 621 fields ...

[tool.setuptools]
# Backend-specific options.

[tool.setuptools.packages.find]
# Tell setuptools where to find packages. `find` is the autodiscovery mode.
where = ["src"]

[tool.setuptools.package-data]
# Non-Python files to include.
"mypkg" = ["*.json", "data/*.csv"]

[tool.setuptools.dynamic]
# When `dynamic = [...]` is set in [project], this populates it.
version = { attr = "mypkg.__version__" }
# Or:
# version = { file = "VERSION" }
# readme = { file = "README.md", content-type = "text/markdown" }
```

The strengths of setuptools:

- **C/C++ extensions.** The `Extension` and `setup()` API for declaring native modules predates everything else and is still the most expressive. NumPy's old (pre-meson) build, scipy's old build, lxml, psycopg2, gevent — all setuptools. Cython integrates via `cythonize()` in a `setup.py`.
- **Maturity.** Twenty years of edge cases handled. Every weird corner of the Python ecosystem — namespace packages, deprecated 2.x quirks, weird file layouts — has a setuptools workaround.
- **Ubiquity.** Every Python installation has setuptools installed (because pip depends on it). The build environment will have it without effort.

The weaknesses:

- **`setup.py` is allowed but deprecated.** setuptools supports a `setup.py` *or* a fully declarative `pyproject.toml`; the latter is now the recommended path. Many old projects still ship `setup.py` and read like they were written in 2014; new projects should not.
- **Configuration is split across three files.** Modern setuptools can put everything in `pyproject.toml`, but the older `setup.cfg` form is still around and many tutorials show it. Pick one form and stick to it.
- **The plugin model has churn.** `setuptools_scm` (version from VCS), `wheel` (the wheel builder, now bundled), `setuptools-rust` — each is a separate plugin with its own version compatibility window. Hatchling integrates more of this into the backend itself.
- **It is *very* large.** The setuptools distribution is several megabytes; build environments are correspondingly heavy.

When to pick setuptools:

- Your project has C/C++/Fortran extensions (or Cython modules) and you want the most-trodden path.
- You are maintaining an existing setuptools project and have no specific reason to migrate.
- You want the maximum-flexibility backend; you have unusual requirements that other backends do not handle.

## 3. hatchling — the modern default for pure-Python

Hatchling is the build backend; `hatch` is the project manager built on top of it. Both are by Ofek Lev (also the author of `tox-conda`, `hatchling` started as a build backend for `hatch`; PyPA adopted both in 2022). The repository: <https://github.com/pypa/hatch>. Docs: <https://hatch.pypa.io/>.

The thesis is small. Hatchling is what you get when you start from a clean slate, design only for the PEP 517/518/621/660 world, do not have to support pre-2017 idioms, and prioritise speed and standards-adherence over flexibility.

The `pyproject.toml` shape:

```toml
[build-system]
requires = ["hatchling >= 1.27"]
build-backend = "hatchling.build"

[project]
name = "mypkg"
version = "0.1.0"
description = "..."
# ... PEP 621 fields ...

[tool.hatch.build.targets.wheel]
packages = ["src/mypkg"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]
```

That is the entire backend config for a pure-Python project. Compare to setuptools: hatchling does not need a `packages.find` directive for src-layout — it autodetects; it does not need a separate `wheel` package in `requires` — wheel-building is part of hatchling; it does not need a `[tool.setuptools.dynamic]` table — the dynamic-version flow goes through `hatch-vcs` (covered in Lecture 3).

The strengths:

- **Speed.** Hatchling's build is measurably faster than setuptools's, especially for many-file packages. The startup cost is lower; the file-discovery is simpler.
- **Standards-strict.** Hatchling validates PEP 621 metadata and refuses ill-formed input. Setuptools is more permissive (it has to be, for backward compatibility); hatchling raises early.
- **Plugins via `hatch_build`.** A custom hook for build-time code generation is one Python file in the project (`hatch_build.py`) that implements one or two methods. Compared to setuptools's `cmdclass` plumbing, this is clean.
- **First-class editable installs.** PEP 660 support is excellent; the `dev-mode-dirs` knob is well-documented.
- **PyPA-blessed.** PyPA endorses hatch (alongside setuptools, flit, and pdm) in its tutorial. Not a small thing — it means the long-term-support story is clear.

The weaknesses:

- **C extension support is limited.** Hatchling has a `[tool.hatch.build.targets.wheel.shared-data]` and some build-target plumbing, but for arbitrary C/C++ compilation you reach for setuptools or scikit-build-core. Hatchling is for pure-Python (and pure-Python-plus-Rust-via-maturin, where maturin is the backend).
- **Newer.** "Newer" is a weakness only in that some long-tail tooling assumes setuptools; in 2026, this is mostly resolved.

When to pick hatchling:

- A new pure-Python project. Hatchling is the modern default.
- You want strict standards-adherence and fast builds.
- You will use `hatch` for environment management (the matrix tester, the version bumper).

## 4. flit-core — the smallest backend

flit-core is the build backend extracted from `flit` (Thomas Kluyver, 2015). The full `flit` package is a project manager (build + publish); `flit-core` is just the backend.

The `pyproject.toml`:

```toml
[build-system]
requires = ["flit-core >= 3.10"]
build-backend = "flit_core.buildapi"

[project]
name = "mypkg"
version = "0.1.0"
description = "..."
# ... PEP 621 fields ...

[tool.flit.module]
name = "mypkg"
```

That is *almost* the entire config. Flit is intentionally minimal — designed for "one Python module per package; if your package needs more, use hatchling or setuptools." It uses the package's `__version__` attribute if `version` is in `dynamic`, and it auto-detects the module from the project name.

The strengths:

- **Minimal.** The smallest backend; the smallest `pyproject.toml`; the smallest configuration surface.
- **Stable.** Flit-core 3.x has been stable for years; the API has not churned.
- **Good citizen.** Strictly PEP 517/518/621-compliant. No surprises.

The weaknesses:

- **Single-module focus.** Flit really wants you to have `mypkg.py` or `mypkg/__init__.py` and nothing more elaborate. Multi-module packages work but are not the design centre.
- **No C extensions.** Pure Python only.

When to pick flit-core:

- A tiny single-module library. A 100-line utility that you happen to want on PyPI.
- You want the smallest possible `pyproject.toml` and the fewest moving parts.
- You are following the PyPA tutorial; the tutorial uses flit-core for its worked example.

## 5. pdm-backend — `pdm`'s native backend

`pdm` is Frost Ming's project manager (rough equivalents: `poetry`, `hatch`). Its backend `pdm-backend` is what `pdm` uses by default. The `pyproject.toml`:

```toml
[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[project]
name = "mypkg"
version = "0.1.0"
description = "..."
# ... PEP 621 fields ...

[tool.pdm]
distribution = true

[tool.pdm.build]
includes = ["src/mypkg"]
```

Pdm-backend is broadly hatchling-equivalent for the build itself. The reason to pick it is *adjacent tooling*: `pdm` has a powerful lockfile (`pdm.lock`), a script runner, an environment manager, and a plugin ecosystem.

When to pick pdm-backend:

- You already use `pdm`. The pdm-pdm-backend integration is the smoothest.
- You like pdm's lockfile (it predates `uv.lock` and was a model for it).

## 6. poetry-core — the elephant

Poetry (Sébastien Eustace, 2018) is the longest-running modern project manager. Its market share is substantial — many open-source projects use poetry. The backend is `poetry-core`; the `pyproject.toml`:

```toml
[build-system]
requires = ["poetry-core >= 1.9"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "mypkg"
version = "0.1.0"
description = "..."
authors = ["Ada Lovelace <ada@example.org>"]

[tool.poetry.dependencies]
python = "^3.11"
numpy = "^1.26"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
```

Note the **`[tool.poetry]` table** — it is *not* PEP 621. Poetry predates PEP 621 by two years and invented its own (incompatible) metadata format. Newer poetry versions support PEP 621 via `[project]` (in addition to `[tool.poetry]`), but adoption is gradual; you will encounter both forms in the wild.

The Poetry deps grammar (`numpy = "^1.26"`, the caret notation) is not PEP 508. It is a poetry-specific shorthand that approximates PEP 440 specifiers. The caret `^1.26` is roughly `>=1.26, <2.0`. There are also tilde, `>=`, `<`, and exact-pin forms. The poetry deps grammar is documented at <https://python-poetry.org/docs/dependency-specification/>.

The strengths:

- **Mature lockfile.** `poetry.lock` was the first widely-used Python lockfile. Battle-tested.
- **Project manager integration.** `poetry install`, `poetry add`, `poetry update`, `poetry publish` — a coherent workflow.
- **Large user base.** Lots of community knowledge; many tutorials assume poetry.

The weaknesses:

- **Non-PEP-621 metadata.** A poetry project's `pyproject.toml` is non-portable; if you switch off poetry, you rewrite the metadata table. (Recent versions support PEP 621, but the older form is still ubiquitous.)
- **Custom deps grammar.** The caret/tilde shorthands diverge from PEP 508. Some tools that read PEP 508 specifiers cannot read `[tool.poetry.dependencies]`.
- **Slower than hatch/pdm/uv.** Poetry's resolver was historically slow; recent versions improved but `uv` is faster.

When to pick poetry-core:

- Existing poetry project. Stay on it.
- You want poetry's project manager and lockfile and you are willing to live with the non-PEP-621 table.
- New projects: probably not the right choice in 2026; hatch or `uv` is the modern equivalent.

## 7. uv_build — the future for `uv` projects

`uv` (Astral, 2024) is Charlie Marsh's Rust-based replacement for pip, pip-tools, twine, venv, and pyenv all rolled into one binary. As of early 2026 it has rapidly become the fastest installer/resolver in the ecosystem. `uv_build` is the build backend bundled with `uv`; it implements PEP 517/518/621/660.

The `pyproject.toml`:

```toml
[build-system]
requires = ["uv_build >= 0.5"]
build-backend = "uv_build"

[project]
name = "mypkg"
version = "0.1.0"
description = "..."
# ... PEP 621 fields ...

[tool.uv]
# uv-specific config.
```

As of early 2026, `uv_build` is **alpha**. The Astral team's posture is that it is usable for testing but not yet recommended as the default. The defaults will likely flip in 2026 once it stabilises.

When to pick uv_build today (Q1 2026):

- You are an early adopter willing to file issues.
- Your project is simple enough that the rough edges will not bite you.

When to pick `uv` the project manager (independent of `uv_build`):

- *Now*, for everything. `uv` as installer/resolver/runner is excellent regardless of which build backend you choose. You can `uv build` a hatchling-backed project; `uv` invokes hatchling correctly.

## 8. Adjacent: maturin, scikit-build-core, meson-python

For Rust extensions, **`maturin`** is the canonical backend. <https://www.maturin.rs/>. The `pyproject.toml`:

```toml
[build-system]
requires = ["maturin >= 1.5"]
build-backend = "maturin"

[project]
name = "mypkg"
# ... PEP 621 ...

[tool.maturin]
features = ["pyo3/extension-module"]
```

This is the path PyO3-based Rust projects take. `cryptography` and `pydantic` (the v2 Rust core) use maturin.

For CMake-based C/C++ projects, **`scikit-build-core`** is the modern path. <https://scikit-build-core.readthedocs.io/>. The `pyproject.toml`:

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
# ... PEP 621 ...

[tool.scikit-build]
cmake.minimum-version = "3.18"
```

For Meson-based projects (NumPy, SciPy, scikit-image), **`meson-python`** is the backend. <https://meson-python.readthedocs.io/>.

These three are the right answer when your project's native code already has a CMake/Meson/Cargo build system; the Python wrapper layer is a thin shim and the heavy lifting is in the native build. Picking one of these over setuptools means leaning on the native build system rather than fighting it.

## 9. Head-to-head: setuptools vs. hatchling on the worked example

Take the same hypothetical pure-Python library, `mypkg` v0.1.0, with one module (`src/mypkg/__init__.py`), a `README.md`, and a `LICENSE`. Build it with both backends.

### setuptools version

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools >= 67", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mypkg"
version = "0.1.0"
description = "Demo package for build-backend comparison."
readme = "README.md"
requires-python = ">= 3.11"
license = "MIT"
authors = [{ name = "Ada Lovelace", email = "ada@example.org" }]

[tool.setuptools.packages.find]
where = ["src"]
```

Build:

```bash
$ python -m build
* Creating venv isolated environment...
* Installing packages in isolated environment:
  - setuptools >= 67
  - wheel
* Getting build dependencies for sdist...
running egg_info
...
* Building sdist...
Successfully built mypkg-0.1.0.tar.gz
* Building wheel from sdist
...
Successfully built mypkg-0.1.0-py3-none-any.whl
```

Time on a 2024 M2 MacBook: ~6 seconds (first run; subsequent runs ~3 seconds with cache).

### hatchling version

`pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mypkg"
version = "0.1.0"
description = "Demo package for build-backend comparison."
readme = "README.md"
requires-python = ">= 3.11"
license = "MIT"
authors = [{ name = "Ada Lovelace", email = "ada@example.org" }]

[tool.hatch.build.targets.wheel]
packages = ["src/mypkg"]
```

Build:

```bash
$ python -m build
* Creating venv isolated environment...
* Installing packages in isolated environment:
  - hatchling
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
* Creating venv isolated environment...
* Installing packages in isolated environment:
  - hatchling
* Getting build dependencies for wheel...
* Building wheel...
Successfully built mypkg-0.1.0.tar.gz and mypkg-0.1.0-py3-none-any.whl
```

Time on the same machine: ~3 seconds (first run; ~1.5 seconds cached).

### The diff

Both produce a `mypkg-0.1.0-py3-none-any.whl` and `mypkg-0.1.0.tar.gz`. The wheel contents are nearly identical — the same `mypkg/__init__.py`, the same `mypkg-0.1.0.dist-info/METADATA` with the same PEP 621-derived fields. The differences:

- The setuptools wheel has a `mypkg-0.1.0.dist-info/RECORD` line for `setuptools-generated-installer-shim` (irrelevant). Hatchling's is cleaner.
- The setuptools `METADATA` includes `Generator: setuptools (67.x)`; hatchling's includes `Generator: hatchling (1.27.0)`. Cosmetic.
- The hatchling sdist is ~10% smaller (cleaner glob defaults; fewer "platform-specific cruft" files).
- The hatchling build is ~2x faster on the cold path and ~1.5x faster cached.

For a pure-Python single-module package, the choice is mostly aesthetic. For a C-extension package, only setuptools is realistically in scope. For a large multi-target project, hatchling's strictness pays off in catching metadata errors at build time rather than at install time.

## 10. Switching backends

Switching is a seven-line diff in `pyproject.toml`. To migrate from setuptools to hatchling:

```diff
 [build-system]
-requires = ["setuptools >= 67", "wheel"]
-build-backend = "setuptools.build_meta"
+requires = ["hatchling"]
+build-backend = "hatchling.build"

 [project]
 # ... PEP 621 fields unchanged ...

-[tool.setuptools.packages.find]
-where = ["src"]
+[tool.hatch.build.targets.wheel]
+packages = ["src/mypkg"]
```

`python -m build` again; verify the resulting wheel installs and imports correctly. That is the entire migration for a pure-Python project. Where setuptools-specific features were in use (entry-point group definitions, custom command classes, weird MANIFEST.in patterns), those need their hatchling equivalents — but for a vanilla project, it is a coffee-break change.

The reverse (hatchling → setuptools) is similar, with the addition of any `[tool.setuptools.*]` you need. Setuptools is more permissive about discovery; you can often omit the `[tool.setuptools.packages.find]` if your layout is conventional.

For projects with native extensions, switching *away from* setuptools is not a coffee-break change — the C-extension declaration syntax differs between setuptools (`Extension(...)` in `setup.py` or `[tool.setuptools.ext-modules]` in `pyproject.toml`) and scikit-build-core / meson-python / maturin. Plan a half-day at least.

## 11. The decision matrix

| If your project... | Pick |
|--------------------|------|
| Is a new pure-Python library | **hatchling** |
| Has C/C++ extensions you compile from `setup.py` | **setuptools** |
| Has a CMake or Meson build already | **scikit-build-core** or **meson-python** |
| Is a Rust extension via PyO3 | **maturin** |
| Is a one-module utility | **flit-core** |
| Is an existing setuptools project with no specific reason to migrate | stay on **setuptools** |
| Is an existing poetry project, deep into poetry tooling | stay on **poetry-core** |
| Is greenfield and you want to be on the absolute frontier | **uv_build** (alpha; expect bugs) |

The discipline: **pick once, document why, do not switch without a reason.** Backend churn is a real cost — every contributor who clones your repo has to learn the backend. Pick the one that fits, stick with it, only switch when the pain of the current choice exceeds the cost of the switch.

## 12. Reading

- The PyPA "Tool recommendations" page: <https://packaging.python.org/en/latest/guides/tool-recommendations/>. ~10 minutes. The official "here is what to pick" guide.
- Hatchling configuration reference: <https://hatch.pypa.io/latest/config/build/>. ~25 minutes.
- Setuptools `pyproject.toml` reference: <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html>. ~20 minutes.
- Flit-core docs: <https://flit.pypa.io/en/stable/pyproject_toml.html>. ~10 minutes.
- Ofek Lev, "Hatch: a modern Python project manager." YouTube. ~30 minutes.
- Hynek Schlawack, "Python packaging in 2024 done right" — the opinionated guide. <https://hynek.me/articles/python-packaging/>. ~20 minutes.
- Pick one example project from the resources.md list (`httpx`, `attrs`, `numpy`, `pip`) and read its `pyproject.toml` end-to-end. Identify the backend, every PEP 517/518/621 field, and every backend-specific table.
