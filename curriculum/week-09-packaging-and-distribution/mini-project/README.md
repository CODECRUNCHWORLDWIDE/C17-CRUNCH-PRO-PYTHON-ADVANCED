# Mini-Project — Ship a Real Package to TestPyPI, End-to-End

> Write a real (small) Python library. Write its `pyproject.toml`. Build it. Publish to TestPyPI via GitHub Actions OIDC trusted publishing — *with no API token stored anywhere*. Install it from TestPyPI into a fresh venv. Demonstrate the full release ritual is one command: `git tag vX.Y.Z && git push --tags`. Write a 700-word memo on the choices you made and what you learned.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-09-package-<yourhandle>` containing:

1. **`README.md`** — what the library does, how to install (from TestPyPI), how to use. ~200 words.
2. **`MEMO.md`** — **the load-bearing artifact**. 600–900 words. Sections below.
3. **`pyproject.toml`** — the complete declarative configuration. PEP 517 / 518 / 621 compliant.
4. **`src/<yourpkgname>/`** — the package source. 50–150 lines total. Type hints on every function.
5. **`tests/`** — at least one `pytest` test for each public function. Doesn't have to be exhaustive; has to verify the wheel can be installed and used.
6. **`LICENSE`** — MIT, Apache-2.0, GPL-3.0-or-later, your choice. SPDX expression in `pyproject.toml` must match.
7. **`CHANGELOG.md`** — at least entries for `0.0.1` (initial release).
8. **`.github/workflows/publish.yml`** — the CI workflow for trusted publishing to TestPyPI.
9. **A pushed `v0.0.1` tag**, a green workflow run, and the resulting TestPyPI page.

The TestPyPI URL is what you point at when an interviewer asks "show me a package you shipped."

## Picking the library

The library must be:

- **Small.** 50–150 lines of source. This is not a "ship a real library to PyPI" exercise; it is a "ship the *infrastructure* for a library" exercise. A 50-line library exercises the whole flow.
- **Pure Python.** No native extensions for this mini-project. (Native extensions are Challenge 2 / Week 10.)
- **A unique name on TestPyPI.** Check <https://test.pypi.org/project/<your-candidate-name>/> first. If it 404s, you can claim it. If someone else has it, pick a different name.
- **Worth a 50-line README.** Some thing you can describe in a paragraph. Not "test123."

### Suggested libraries

If you do not have a project idea, pick one of these:

- **`text-stats-<handle>`** — count words, sentences, paragraphs, average word length, Flesch reading ease score for a string. Reads from stdin or a file. CLI: `text-stats <file>`.
- **`color-tools-<handle>`** — convert between RGB, HSL, HEX, named colors. Library + CLI. Use only `colorsys` (stdlib).
- **`csv-pivot-<handle>`** — a `csv pivot` CLI that does grouped sums/means over a CSV. Uses `csv` (stdlib) and `argparse`.
- **`semver-bump-<handle>`** — a tiny `semver-bump <current-version> <patch|minor|major>` CLI. Uses `re` (stdlib). No PyPI deps.
- **`http-ping-<handle>`** — a `http-ping <url>` CLI that does GET and prints the status code, timing, and a few headers. Uses `urllib.request` (stdlib).
- **`md-headings-<handle>`** — extract the heading tree from a markdown file. CLI prints them. No deps.

Pick one. Spend 30 minutes writing it. Spend the other 6 hours on packaging it.

## Step-by-step

### Thursday (~2 h)

1. **Create the TestPyPI account** (15 min). <https://test.pypi.org/account/register/>. Verify email. Enable 2FA (use TOTP via Google Authenticator or 1Password). Note: TestPyPI and PyPI are *separate* accounts; you may want to set up PyPI too while you are at it.

2. **Pick the library name** (5 min). Append your handle to avoid conflicts: `text-stats-jeansteph`, etc. Check <https://test.pypi.org/project/<name>/> returns 404.

3. **Write the package** (45 min). Single module under `src/<pkgname>/__init__.py`. One `cli.py` if you want a CLI entry point. Tests in `tests/`. Type hints everywhere.

4. **Write the `pyproject.toml`** (30 min). Use `mini-project/sample-pyproject.toml` as a starting point. Fill in your name, your handle, your description.

5. **Build locally** (15 min). `pip install build`; `python -m build`; verify `dist/*.whl` and `dist/*.tar.gz` exist; install the wheel in a fresh venv and run the test suite + CLI entry point.

### Friday (~3 h)

6. **Push to GitHub** (15 min). Create a new public repo at `github.com/<youruser>/<pkgname>`. Push your project.

7. **Register the Pending Publisher on TestPyPI** (15 min). <https://test.pypi.org/manage/account/publishing/>. Fill in:
   - PyPI Project Name: your package name
   - Owner: your GitHub username
   - Repository name: the repo name
   - Workflow filename: `publish.yml`
   - Environment name: `testpypi`

8. **Create the GitHub Environment** (5 min). In your repo Settings → Environments → New Environment → name `testpypi`. Leave secrets and approval rules empty for now.

9. **Write `.github/workflows/publish.yml`** (45 min). Use `exercises/exercise-03-publish.yml` as a starting point; trim to TestPyPI-only (remove the `publish-pypi` and `github-release` jobs for now). The workflow must include `permissions: id-token: write` and use `pypa/gh-action-pypi-publish@release/v1`.

10. **Tag and push** (5 min). `git tag v0.0.1 && git push --tags`. Watch the workflow run.

11. **Debug the CI** (~60 min). It will fail at least once; this is normal. Common failures:
    - `id-token: write` missing → add to workflow `permissions`.
    - Environment name mismatch → check TestPyPI Pending Publisher config matches workflow `environment: { name: ... }`.
    - Workflow filename mismatch → ensure file is named exactly `publish.yml` (TestPyPI's registration is filename-strict).
    - Workflow file not on `main` → trusted publishing requires the workflow to be on the default branch.

12. **Verify the upload** (15 min). Once green, visit `https://test.pypi.org/project/<yourpkg>/`. Verify the version, description, and authors render correctly. Install in a fresh venv:

    ```bash
    python3 -m venv /tmp/v
    /tmp/v/bin/pip install --index-url https://test.pypi.org/simple/ \
        --extra-index-url https://pypi.org/simple/ \
        <yourpkg>
    /tmp/v/bin/python -c "import <yourpkg>; print(<yourpkg>.__version__)"
    ```

    The `--extra-index-url` is so transitive deps install from real PyPI.

### Saturday (~2 h)

13. **Iterate on a second release** (30 min). Make a small change to the package; bump to `v0.0.2`; tag and push; verify the workflow publishes the new version to TestPyPI. The point: prove the release ritual is `git tag vX.Y.Z && git push --tags`.

14. **Write `MEMO.md`** (60 min). 600–900 words. Sections below.

15. **Polish** (30 min). README links to TestPyPI. CHANGELOG entries for 0.0.1 and 0.0.2. Run `python3 -m py_compile` on every `.py`. Verify `pyproject.toml` parses with `tomllib`. Push final commit.

## The memo

`MEMO.md`. 600–900 words. Six sections.

### Section 1 — The library and what it does (~75 words)

In two sentences: what does the library do? Then state the version (`0.0.2`), the line count, and the test count.

### Section 2 — The pyproject.toml choices (~150 words)

For each of the following, state your choice and one-sentence rationale:

- **Build backend.** hatchling, setuptools, flit-core? Cite Lecture 2 §11.
- **Versioning.** Static (`version = "0.0.2"` in pyproject.toml), `setuptools_scm`/`hatch-vcs` (dynamic), or CalVer?
- **License.** MIT / Apache-2.0 / GPL? Why?
- **Python version range.** `>= 3.11` or wider?
- **Dependencies.** What did you depend on? Why not more / fewer?

### Section 3 — The publish flow (~150 words)

Walk through what your CI workflow does, step by step. Mention:

- The trigger (push of `v*` tag).
- The build job (`python -m build`).
- The publish job and trusted publishing (`pypa/gh-action-pypi-publish`).
- The required permissions (`id-token: write`).
- The GitHub Environment binding.

Include one observation about what surprised you in the trusted-publishing setup. (Common: how strict the field-matching is between PyPI's Pending Publisher and the workflow.)

### Section 4 — One CI failure and how you debugged it (~100 words)

Pick the worst failure your CI workflow produced and explain (a) what the error was, (b) what you initially thought caused it, (c) what actually caused it, (d) the fix. The CI debugging discipline is what you want documented; the next person who hits the same error reads this paragraph and saves 30 minutes.

### Section 5 — Install verification (~75 words)

Paste the `pip install --index-url https://test.pypi.org/simple/ ...` command and the verification output (the version printed, the entry point invoked). One sentence on what would be different if you had published to *production* PyPI instead of TestPyPI.

### Section 6 — What you would do for v1.0 (~150 words)

If this library reached `1.0.0` and you committed to long-term support, what would change? Pick at least two of:

- **Lockfile.** Add `uv.lock` to the repo for reproducible CI. (Note: lockfile is for the *app/CI* shape of the project, not the published library itself.)
- **`cibuildwheel`** for if you added a native module.
- **Production PyPI** publish path with the parallel Pending Publisher.
- **`pre-commit` hooks** for `ruff`, `mypy`, `pyproject.toml` validation.
- **`pytest` + `coverage` + `mypy` in CI** running on every PR, not just on tags.
- **Trusted publishing for production PyPI** alongside the TestPyPI path.
- **`hatch matrix`** or `tox` or `nox` for testing across Python versions (3.11 / 3.12 / 3.13).
- **A docs site** via `mkdocs` or `sphinx`, deployed to ReadTheDocs.

Close with one sentence about what surprised you about packaging Python in 2026.

## Acceptance criteria

- [ ] Public GitHub repo (with the workflow runs visible).
- [ ] `pyproject.toml` parses (`python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`).
- [ ] At least two version tags pushed (`v0.0.1` and `v0.0.2`), both with green workflow runs.
- [ ] The package is live at `https://test.pypi.org/project/<yourpkg>/`. The page shows the correct version, description, and authors.
- [ ] A fresh-venv `pip install` from TestPyPI succeeds; the package can be imported and (if applicable) its CLI invoked.
- [ ] The workflow uses **trusted publishing** (PEP 740) — `id-token: write` permission, `pypa/gh-action-pypi-publish`, *no PyPI API token stored as a GitHub Actions secret*.
- [ ] `MEMO.md` exists, is 600–900 words, has all six sections.
- [ ] All Python files have type hints. `python3 -m py_compile` passes on every `.py`.
- [ ] `CHANGELOG.md` has entries for at least two releases.
- [ ] The README has a one-line install command pointing at TestPyPI.

## Common pitfalls

- **Skipping the GitHub Environment.** The workflow's `environment: { name: testpypi }` references a GitHub Environment that you must create separately in Settings → Environments. If it does not exist, the workflow run is queued forever waiting for an environment that does not exist.
- **Workflow not on the default branch.** Trusted publishing requires the workflow file to be present on the default branch (usually `main`). If you developed the workflow on a feature branch, merge it to `main` first.
- **Email verification delay.** TestPyPI's signup email can take up to an hour. Start the signup as soon as you start the mini-project.
- **2FA setup.** PyPI and TestPyPI both require 2FA for project ownership. Set it up early.
- **Forgetting `--extra-index-url`** when installing from TestPyPI. Many of your transitive deps (e.g., `pytest` if you put it in your runtime deps by mistake) will not be on TestPyPI and the install will fail to resolve. `--extra-index-url https://pypi.org/simple/` lets pip fall back to production PyPI for transitives.
- **Reusing a TestPyPI version number.** Once you upload `0.0.1`, you cannot re-upload `0.0.1` with new contents (PyPI rejects duplicate version uploads). Always bump the version for a new upload. This is the same rule on production PyPI; learn the discipline here.
- **Workflow filename mismatch.** The Pending Publisher form on TestPyPI is filename-strict. If you registered `publish.yml` and your file is `release.yml`, the OIDC handshake fails. Match exactly.

## Why this matters

The mini-project is the **artifact** for Week 9 and one of the most important artifacts of the C17 curriculum. Every senior Python interview asks some version of "have you shipped a package to PyPI?" Most candidates have not. The candidates who do well point at a public TestPyPI (or PyPI) page, a green CI workflow, and a 700-word memo demonstrating that they understand *every* moving part — the PEP 517 backend, the wheel format, the manylinux baseline (even if they did not exercise it this week), the lockfile distinction, the trusted publishing flow.

The flow you set up this week is the flow you reuse for every future project. The 7-hour investment is paid back the first time you publish a real library, and again every time after.

The mini-project does not require you to publish a *useful* library. It requires you to publish *the infrastructure* a useful library would publish through. That is the unit of work.

## Reading

- All three Week 9 lectures, end-to-end. Treat them as reference.
- The PyPI Trusted Publishing docs: <https://docs.pypi.org/trusted-publishers/>. Essential for Friday's setup steps.
- The PyPA tutorial, "Packaging Python Projects": <https://packaging.python.org/en/latest/tutorials/packaging-projects/>. Mirrors what you will do; their worked example uses flit-core, which is also a valid backend choice.
- The `pypa/gh-action-pypi-publish` README: <https://github.com/pypa/gh-action-pypi-publish>. The action that does the heavy lifting.
- PEP 740 (trusted publishing spec): <https://peps.python.org/pep-0740/>. Read once for the protocol details.

Good shipping.
