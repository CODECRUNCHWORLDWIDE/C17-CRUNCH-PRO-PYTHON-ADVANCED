# Week 9 — Homework

Six problems, ~7 hours total. Commit each as you finish.

---

## Problem 1 — Read four `pyproject.toml` files in production (60 min)

Open these four production `pyproject.toml` files and read them line by line:

1. `httpx` — pure-Python, hatchling: <https://github.com/encode/httpx/blob/master/pyproject.toml>
2. `pip` — the installer itself, setuptools + setuptools_scm: <https://github.com/pypa/pip/blob/main/pyproject.toml>
3. `attrs` — Hynek Schlawack's, hatchling, well-commented: <https://github.com/python-attrs/attrs/blob/main/pyproject.toml>
4. `numpy` — non-trivial native extension, meson-python backend: <https://github.com/numpy/numpy/blob/main/pyproject.toml>

For each file, identify:

- The build backend (the `build-backend` value).
- Whether `version` is static or `dynamic`.
- The Python version range (`requires-python`).
- The number of runtime dependencies vs. extras.
- One thing you would do differently in your own project.

Write a `reading.md` with one paragraph per project (~150 words each).

**Acceptance:**
- `reading.md` with four sections, one per project, ~150 words each.
- A final two-sentence observation: across these four, what is the *commonality* (the pattern they all follow) and what is the *variation* (one thing they differ on).
- Each section names the backend and at least three specific lines from the file.

---

## Problem 2 — Write a complete `pyproject.toml` from scratch (45 min)

Pick a hypothetical pure-Python library — a small CLI utility, a data-validation helper, a tiny ORM, anything you could write in 100 lines. Write its full `pyproject.toml` from scratch.

Required sections:
- `[build-system]` using hatchling.
- `[project]` with every field from PEP 621 you would include for a real release. Cover `name`, `version` (or dynamic), `description`, `readme`, `requires-python`, `license`, `authors`, `keywords`, `classifiers`, `dependencies`.
- `[project.optional-dependencies]` with at least a `test` extra.
- `[project.scripts]` with one entry point.
- `[project.urls]` with `Homepage`, `Issues`, and `Documentation` at minimum.
- `[tool.hatch.*]` for the backend config (version source, wheel target).
- `[tool.ruff]` and `[tool.mypy]` if you would use those linters.

Validate it parses: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.

**Acceptance:**
- `pyproject.toml` of 50–100 lines, parses cleanly.
- A `WHY.md` of ~250 words explaining each non-trivial choice (which backend? which classifiers? what extras? why those URLs?).
- A run of `python -m build` against the file produces a wheel (you may need to also stub out a `src/<pkgname>/__init__.py`).

---

## Problem 3 — Build, audit, and inspect a wheel (60 min)

Take any small Python file (or use the package from Problem 2) and produce both a wheel and an sdist from it. Then:

1. Run `python -m build`. Capture the full output.
2. List the wheel contents: `unzip -l dist/*.whl`. Capture the listing.
3. Extract and read `METADATA`, `WHEEL`, and `RECORD` from the wheel's `dist-info/`. Save them as `metadata.txt`, `wheel.txt`, `record.txt`.
4. List the sdist contents: `tar -tzf dist/*.tar.gz`. Capture the listing.
5. Install the wheel in a fresh venv: `python3 -m venv /tmp/v; /tmp/v/bin/pip install dist/*.whl; /tmp/v/bin/python -c "import yourpkg; print('ok')"`. Capture the output.

**Acceptance:**
- `build-output.txt`, `wheel-contents.txt`, `metadata.txt`, `wheel.txt`, `record.txt`, `sdist-contents.txt`, `install-output.txt` all in your portfolio.
- A `notes.md` of ~200 words explaining what each `dist-info/` file does:
  - `METADATA` — what is in it; cite Metadata-Version 2.3 / 2.4.
  - `WHEEL` — the `Generator`, `Root-Is-Purelib`, `Tag` lines.
  - `RECORD` — what the sha256 + size columns mean.

---

## Problem 4 — Set up trusted publishing on TestPyPI (90 min)

You will publish a real package to TestPyPI using trusted publishing. The package can be Problem 2's library (preferred — you already wrote the pyproject.toml) or any other small pure-Python library you own.

Steps:

1. Create a TestPyPI account at <https://test.pypi.org/account/register/>. Enable 2FA.
2. Push your project to a new GitHub repo (public or private, your call).
3. On TestPyPI, register a **Pending Publisher** for your project at <https://test.pypi.org/manage/account/publishing/>. Fill in owner, repository, workflow filename (`publish.yml`), environment name (`testpypi`).
4. Create a GitHub Environment named `testpypi` in your repo (Settings → Environments → New Environment).
5. Commit `.github/workflows/publish.yml`. Use the reference workflow from `exercises/exercise-03-publish.yml` as a starting point; trim to TestPyPI-only.
6. Tag a release: `git tag v0.0.1 && git push --tags`.
7. Verify the workflow runs to green and the package appears on TestPyPI.
8. In a fresh venv on your laptop: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ <your-package-name>`. Verify it installs and the entry point works.

**Acceptance:**
- The TestPyPI URL of your published package (e.g., `https://test.pypi.org/project/yourpkg/`).
- A screenshot or copy-paste of the successful GitHub Actions run.
- A `publish-notes.md` of ~250 words covering: what you registered on TestPyPI, what permissions your workflow needed (`id-token: write`), what surprised you about the flow.

If this proves to be the most fiddly step of homework, that is expected — trusted publishing has many small configuration items that must all match. Worth the effort: you will repeat this flow for every future project. After the first time, it takes 15 minutes.

---

## Problem 5 — Compare two locking tools on the same project (60 min)

Take a `pyproject.toml` with at least 3 runtime dependencies and at least 1 extras group. Produce a lockfile two ways:

**Way 1: `uv`.**

```bash
pip install uv
uv lock
```

This produces `uv.lock`. Inspect it.

**Way 2: `pip-tools`.**

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file requirements.lock pyproject.toml
```

This produces `requirements.lock` (a `requirements.txt`-style file with sha256 hashes).

Inspect both. Note:

- Total file size in lines.
- Total number of pinned packages (including transitives).
- Format: TOML (`uv.lock`) vs. pip-format (`requirements.lock`).
- Cross-platform handling: does the lockfile pin different wheels for different platforms? (Uv does this; pip-tools does not, by default.)
- Hash inclusion: does every pin include a sha256?

**Acceptance:**
- Both lockfiles committed.
- A `locking-comparison.md` of ~300 words with:
  - A table of size, package count, format, cross-platform support, hash inclusion.
  - One paragraph on which tool you would use for an application repo and why.
  - One paragraph on whether you would ship a lockfile *as part of a library* (hint: no — libraries pin loosely in `[project.dependencies]` and let consumers lock).
  - A pointer to PEP 751 (the provisional standardised lockfile format): <https://peps.python.org/pep-0751/>.

---

## Problem 6 — Read PEP 517 and PEP 621 end-to-end (90 min)

Read these two PEPs in full and write a structured study note for each:

- PEP 517: <https://peps.python.org/pep-0517/>
- PEP 621: <https://peps.python.org/pep-0621/>

Format each note (~400 words per PEP):

1. **Motivation.** What problem was the author solving? Cite the PEP's "Rationale" or "Motivation" section.
2. **The core proposal.** In your own words, what does the PEP standardise? (For 517: the hooks. For 621: the field set in `[project]`.)
3. **Open questions.** What does the PEP *not* specify? (For 517: backend-specific behaviour. For 621: tool-specific behaviour under `[tool.*]`.)
4. **Adoption.** Which backends/tools implement this PEP, as of early 2026? Cite at least three.
5. **One thing you learned.** A detail you did not know before; why it matters.

**Acceptance:**
- `pep-517-notes.md` and `pep-621-notes.md`, ~400 words each, covering all five sections.
- Cite specific section numbers or quotes from the PEP texts.

This is the reading-intensive problem. It is the *most valuable* problem of the week if you are going to maintain Python packages in the long term. The 90 minutes pays back across years.

---

## Submission

Commit all files under `c17-week-09-homework/` in your portfolio repo. Expected shape:

```
c17-week-09-homework/
  reading.md                       # Problem 1: 4 production pyproject.toml read-throughs
  problem-2/
    pyproject.toml                 # Problem 2: a full hand-written one
    WHY.md
  problem-3/
    build-output.txt
    wheel-contents.txt
    metadata.txt
    wheel.txt
    record.txt
    sdist-contents.txt
    install-output.txt
    notes.md
  problem-4/
    testpypi-url.md                # the URL of your TestPyPI package
    workflow-run-screenshot.png    # (or copy-paste)
    publish-notes.md
  problem-5/
    uv.lock
    requirements.lock
    locking-comparison.md
  problem-6/
    pep-517-notes.md
    pep-621-notes.md
```

If Problem 4 (trusted publishing) is blocked on PyPI's email-verification delay or on your GitHub Actions environment, ship Problems 1–3 and 5–6 by the end of Sunday and tackle Problem 4 the following weekend. The minimum bar is Problems 1, 2, 3, 4 (best-effort; partial credit for a documented blocker), and one of 5 or 6.

## Rubric

| Criterion | Excellent (5) | Adequate (3) | Below (1) |
|-----------|---------------|--------------|-----------|
| **Real-project reading depth** (P1) | Four files read; commonalities and variations called out; specific lines cited | Files read; superficial observations | Skimmed; no specific citations |
| **`pyproject.toml` craft** (P2) | All required sections; every choice justified in WHY.md; parses cleanly; produces a wheel | Most sections; some choices unexplained | Missing sections; parse errors |
| **Wheel inspection depth** (P3) | All seven outputs captured; notes.md explains each `dist-info/` file accurately | Outputs captured; notes are mechanical | Some outputs missing; notes vague |
| **Trusted publishing** (P4) | Published to TestPyPI; CI green; publish-notes covers permissions and pitfalls | Set up but blocked at one step (documented); notes present | Did not start |
| **Locking comparison** (P5) | Both lockfiles; tabulated comparison; informed application-vs-library guidance | Both lockfiles; surface comparison | One lockfile; vague guidance |
| **PEP reading** (P6) | Both PEPs read end-to-end; 400-word notes each with all five sections; specific quotes | One PEP read carefully; one skimmed | Skimmed both; vague notes |

Self-grade. The artifacts are what matters.

## Reading

- Lectures 1, 2, 3 (all of them; the homework draws from all three).
- The packaging.python.org tutorial: <https://packaging.python.org/en/latest/tutorials/packaging-projects/>.
- The PyPI trusted publishing docs: <https://docs.pypi.org/trusted-publishers/>.
- PEP 517, 518, 621, 660 (linked from resources.md).

## Notes

- **Trusted publishing is the load-bearing problem.** Problems 1–3 build the model; Problem 4 makes it real. If you do nothing else, do Problem 4.
- **Lock files are application-level.** Do not ship `uv.lock` or `requirements.lock` as part of a library distribution. Consumers will lock for themselves.
- **Read the PEPs.** Every senior Python engineer has read PEP 517 and PEP 621. The investment is small; the lifetime payoff is large.
- **`python3 -m py_compile` is your fastest sanity check.** Run it on every `.py` you produce. The pyproject.toml equivalent: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.
