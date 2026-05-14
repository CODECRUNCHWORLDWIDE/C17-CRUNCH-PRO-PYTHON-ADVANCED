# Week 9 — Quiz

Ten questions. Lectures closed.

---

**Q1.** PEP 517 ("A build-system independent format for source trees") defines:

- A) A YAML-based configuration file that replaces `setup.py`.
- B) A standard *interface* (a Python module with hook functions like `build_wheel`, `build_sdist`) that any build backend implements, allowing `pip` to invoke arbitrary backends — setuptools, hatchling, flit-core, poetry-core, uv_build — through one protocol. Brett Cannon and Nathaniel Smith authored it in 2015.
- C) The wheel binary format, with the `.whl` filename convention.
- D) The trusted-publishing OIDC protocol for PyPI.

---

**Q2.** The `[build-system]` table in `pyproject.toml` (PEP 518) requires:

- A) `version` and `description`.
- B) `requires` (a list of PEP 508 dependency specifiers for the build environment) and `build-backend` (a dotted Python module path that `pip` imports to get the PEP 517 hooks). The `requires` list is installed into an *isolated* environment before the backend is invoked.
- C) A `setup.py` next to it.
- D) An entry under `[project.scripts]`.

---

**Q3.** PEP 621 ("Storing project metadata in pyproject.toml") defines:

- A) The interface that build backends must implement.
- B) The structure of the `[project]` table — name, version, description, readme, requires-python, license, authors, classifiers, dependencies, optional-dependencies, scripts, urls. Standardised in 2020 across backends so the same metadata table works with setuptools, hatchling, flit-core, etc.
- C) The wheel filename convention.
- D) Trusted publishing.

---

**Q4.** A wheel filename `mypkg-0.1.0-cp313-cp313-manylinux_2_28_x86_64.whl` says:

- A) Built with CPython 3.13; ABI matches CPython 3.13's; runs on any Linux x86_64 with glibc 2.28 or newer (CentOS 8 / Debian 10 / Ubuntu 20.04 baseline).
- B) Built with PyPy 3.13.
- C) Pure-Python, works anywhere.
- D) The filename is invalid; manylinux tags do not use underscores.

---

**Q5.** `manylinux_2_28` (PEP 600) means:

- A) Built on a 2028-vintage Linux distro.
- B) The wheel was built inside a manylinux Docker image whose glibc is 2.28, so the wheel works on any Linux x86_64 system with glibc 2.28 or newer. The "_2_28" encodes the *minimum* glibc version — newer systems are fine; older are not.
- C) The wheel has 28 dependencies.
- D) The wheel is restricted to Linux distros from 2028.

---

**Q6.** A *lockfile* (`uv.lock`, `poetry.lock`, `pip-tools` `requirements.lock`) records:

- A) Only the direct dependencies declared in `pyproject.toml`.
- B) The full resolved dependency tree — every direct *and* transitive dependency, pinned by version *and* hash, across every platform you support. The point: reproducible installs. Different from `[project.dependencies]` in `pyproject.toml`, which states pins for direct deps only.
- C) The build backend's internal state.
- D) The OIDC token used by trusted publishing.

---

**Q7.** Trusted publishing (PEP 740, PyPI's OIDC-based authentication):

- A) Uses a long-lived API token stored in GitHub Actions secrets.
- B) Configures PyPI to trust a specific GitHub Actions workflow on a specific repo; the workflow uses GitHub's OIDC identity to request a *short-lived* token from PyPI at publish time. No long-lived secret is stored anywhere. Setup via <https://pypi.org/manage/account/publishing/>.
- C) Requires you to sign every release with a GPG key.
- D) Only works for projects with paid PyPI accounts.

---

**Q8.** PEP 660 ("Editable installs for pyproject.toml based builds") adds:

- A) The `[project]` table.
- B) Two hooks to the PEP 517 interface (`build_editable` and `get_requires_for_build_editable`) so `pip install -e .` works for any PEP 517 backend that implements them. As of 2026, all major backends (setuptools, hatchling, flit-core, pdm-backend, poetry-core) do.
- C) Support for static type checking.
- D) The manylinux platform tag scheme.

---

**Q9.** When choosing a build backend for a *new pure-Python* project in 2026, the modern default is:

- A) setuptools (always).
- B) hatchling — fast, strict about standards, PyPA-blessed, simple `[tool.hatch.*]` config. Setuptools remains the right answer for *native-extension* projects; hatchling is the default for pure-Python.
- C) poetry-core (because poetry has the most users).
- D) uv_build (the latest tool).

---

**Q10.** The recommended versioning strategy for a new library is:

- A) Hand-write `__version__` literals in every module.
- B) SemVer (MAJOR.MINOR.PATCH) derived from git tags via `setuptools_scm` or `hatch-vcs`. Combined with `dynamic = ["version"]` in `[project]`, this eliminates the "I forgot to bump the version" bug. CalVer is the right answer for "ships on a schedule, no API stability claim" (Ubuntu, pip itself, cibuildwheel).
- C) CalVer always; SemVer is obsolete.
- D) Use the current date as the version on every commit.

---

## Answer key

<details>
<summary>Reveal</summary>

1. **B** — PEP 517 is the build-system interface (Lecture 1 §2). The standard that decoupled `pip` from any specific backend.
2. **B** — `[build-system]` requires `requires` and `build-backend` (Lecture 1 §3; PEP 518).
3. **B** — PEP 621 defines the `[project]` table (Lecture 1 §4).
4. **A** — Wheel-tag decomposition: `cp313` Python tag = CPython 3.13; same again for ABI; `manylinux_2_28_x86_64` platform (Lecture 3 §1; PEP 425).
5. **B** — manylinux_2_28 = "Linux with glibc >= 2.28" per PEP 600 (Lecture 3 §3).
6. **B** — Lockfile vs. pinning: lockfile pins transitive deps with hashes (Lecture 3 §6).
7. **B** — Trusted publishing via OIDC; no stored secret (Lecture 3 §8 Path 2; PEP 740).
8. **B** — PEP 660 hooks for editable installs (Lecture 1 §5).
9. **B** — hatchling is the modern pure-Python default (Lecture 2 §3, §11).
10. **B** — SemVer + setuptools_scm/hatch-vcs is the default (Lecture 3 §7).

</details>

## Self-reflection

If you got 9 or 10 right: you have the model. The mini-project will exercise the discipline on a real package.

If you got 7 or 8 right: the gap is usually in the PEP numbers (Q1, Q3, Q8) or the platform-tag mechanics (Q4, Q5). Re-read Lecture 1 §§2–5 and Lecture 3 §§1–3 before Thursday.

If you got 6 or fewer right: re-read all three lectures end-to-end before starting the mini-project. The mini-project flow has many moving parts (pyproject.toml, build backend, wheel artifact, trusted publishing, GitHub Actions); without the mental model from the lectures, debugging the CI workflow will be a slog. The investment is ~3 hours of re-reading; it returns the rest of the week's work.
