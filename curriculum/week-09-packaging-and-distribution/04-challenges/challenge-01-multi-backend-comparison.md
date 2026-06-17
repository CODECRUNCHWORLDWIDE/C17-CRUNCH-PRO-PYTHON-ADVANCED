# Challenge 1 — Same package, three backends, head-to-head

**Estimated time:** 2–3 hours. **Outcome:** A side-by-side comparison report of three build backends — setuptools, hatchling, flit-core — producing the same wheel from the same package. You will measure build time, wheel content, metadata fidelity, and developer-ergonomics deltas, then write an opinionated 400-word memo on which backend you would choose for a new pure-Python project and why.

## The setup

Take any small pure-Python package — the `mypkg-exercise` from Exercise 2 is the obvious starting point, or write a fresh 50-line library. It must be single-module-or-small, src-layout, pure Python (no C extensions), and have at least one `[project.scripts]` entry point so the entry-point handling differs visibly between backends.

For each of three backends, you will produce:

- A `pyproject.toml` configured for that backend.
- A built wheel and sdist.
- A capture of `time python -m build` showing wall time.
- A capture of `unzip -l <wheel>` and the wheel's `dist-info/METADATA`.

## Step-by-step

1. **Set up three branches or three subdirectories.** `comparison/setuptools/`, `comparison/hatchling/`, `comparison/flit/`. Each has the same source code under `src/mypkg/` and a backend-specific `pyproject.toml`.

2. **Write the three `pyproject.toml` files.** The `[project]` table is identical (PEP 621 is the point); only `[build-system]` and the backend-specific `[tool.*]` tables differ. Lecture 2 §§2, 3, 4 has the templates.

3. **Build each three times.** First build is cold (pip downloads the backend); second and third builds use the wheel cache. Capture `time` for all three. Report cold-vs-warm.

   ```bash
   $ rm -rf dist/ ~/.cache/pip/wheels   # cold cache
   $ time python -m build
   ...
   real    0m6.2s

   $ rm -rf dist/                       # warm cache
   $ time python -m build
   ...
   real    0m2.8s
   ```

4. **Compare the wheel contents.** For each of the three wheels:

   ```bash
   unzip -l mypkg-0.1.0-py3-none-any.whl
   unzip -p mypkg-0.1.0-py3-none-any.whl mypkg-0.1.0.dist-info/METADATA
   unzip -p mypkg-0.1.0-py3-none-any.whl mypkg-0.1.0.dist-info/WHEEL
   ```

   Note the differences: WHEEL `Generator:` line will name the backend; METADATA may differ in field ordering and whitespace; RECORD will have slightly different file lists if the backend includes/excludes different metadata files.

5. **Compare the sdist contents.** Same drill with `tar -tzf` instead of `unzip -l`. The sdist file list is where backends differ most — what they include by default, what they require you to opt in to.

6. **Install each wheel in a fresh venv and verify the entry point.**

   ```bash
   python3 -m venv /tmp/venv-setuptools
   /tmp/venv-setuptools/bin/pip install dist/*.whl
   /tmp/venv-setuptools/bin/mypkg-cli World
   ```

   Repeat for hatchling and flit. They should all produce the same output. (If they do not, you have a bug in one backend's entry-point configuration.)

7. **Write the memo (`MEMO.md`, ~400 words).** Six paragraphs:

   - **§1 — The package and the goal (~50 words)**. What package, why this comparison.
   - **§2 — Build-time numbers (~75 words)**. The cold and warm times in a table; one observation about why the differences are what they are. (Hint: hatchling and flit are smaller backends, so the isolated-env install is faster; setuptools is the largest backend.)
   - **§3 — Wheel content differences (~75 words)**. List the differences you found in METADATA, RECORD, WHEEL. Most should be cosmetic; flag any that are not.
   - **§4 — Configuration ergonomics (~75 words)**. How many lines of TOML did each backend need? Which had the most surprising defaults? Which required the least documentation lookup?
   - **§5 — Verdict (~75 words)**. For a *new pure-Python* project starting today, which backend would you pick? Justify in three sentences. Cite Lecture 2 §11.
   - **§6 — When you would pick differently (~50 words)**. What about the project would make you change your answer? (Hint: native extensions push you to setuptools; a single-module utility could go to flit-core; an existing setuptools project stays on setuptools.)

## Acceptance

- [ ] Three `pyproject.toml` files committed, one per backend.
- [ ] Three `dist/` directories (or one with subdirectories per backend) containing the wheel + sdist for each.
- [ ] A `bench.txt` (or section of MEMO.md) with the `time` output captured for each build, cold and warm.
- [ ] At least one `pip install` + entry-point verification per backend, output captured.
- [ ] `MEMO.md` of 350–500 words covering the six sections.
- [ ] All `pyproject.toml` files parse: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.

## What you should find

The expected high-level results (on a 2024 M2 MacBook; your numbers will vary):

- **Cold build times**: setuptools ~7 s, hatchling ~3 s, flit-core ~2 s. Setuptools is slower because the package is larger to download into the isolated build env.
- **Warm build times**: setuptools ~3 s, hatchling ~1.5 s, flit-core ~1 s. The gap narrows but persists; setuptools's runtime is heavier.
- **Wheel size**: nearly identical (within bytes). The wheels contain the same source files. The difference is in the dist-info metadata files.
- **METADATA differences**: cosmetic. All three produce a `Metadata-Version: 2.3` (or 2.4 for newer backends) file with the PEP 621 fields. Field ordering may vary; line endings may vary; the *content* is the same.
- **WHEEL header differences**: the `Generator:` line names the backend.
- **RECORD differences**: minor — slightly different sets of metadata files included (e.g., setuptools might include a `top_level.txt`; hatchling typically does not).
- **Configuration line counts**: roughly setuptools 30, hatchling 22, flit-core 15. Flit is intentionally minimal.

The judgement section. Hatchling is the modern default for new pure-Python projects; it is fast, strict, PyPA-blessed. Setuptools is the right answer for native extensions and for projects with substantial pre-2021 history. Flit-core is the right answer for "this is a one-module utility; I want the smallest config that works."

## Reading

- Lecture 2 (the entire lecture; the head-to-head section is §9).
- The setuptools `pyproject.toml` reference: <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html>.
- The hatchling config reference: <https://hatch.pypa.io/latest/config/build/>.
- The flit-core config reference: <https://flit.pypa.io/en/stable/pyproject_toml.html>.

## Notes

- **Backend-specific defaults can bite you.** For instance: hatchling's default is to *exclude* files not under `[tool.hatch.build.targets.wheel].packages`; setuptools's default is to *include* anything in `src/` (with `find_packages`). If you see "package files missing from the wheel" with one backend, check the include/exclude defaults.
- **PEP 621 portability is the win.** The `[project]` table is identical across all three backends. The differences are in `[build-system]` (six lines) and `[tool.X.*]` (a few lines per backend). Moving between backends is cheap — the metadata travels.
- **Do not switch backends without a reason.** The challenge demonstrates that all three work; in practice you pick one, document why, and stick with it. Churn is a cost.
