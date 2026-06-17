# Challenge 1 — Free-Threaded Build Audit

> Time budget: 90 minutes. Equipment: a machine running Linux, macOS, or Windows; `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`) or the ability to download CPython binaries from python.org.

## The setup

The free-threaded build of Python 3.13 (PEP 703) is shipped alongside the stock build. You can install it in 30 seconds with `uv python install 3.13t`. The `t` suffix is the canonical version tag for the free-threaded ABI (the wheel tag is `cp313t-cp313t`). The two builds coexist; you select one or the other by binary path or by `uv run --python 3.13t script.py`.

This challenge asks you to install the build, rerun the Week 11 benchmarks against it, and document any C-extension breakage you encounter.

## The task

1. **Install the free-threaded build.** Use `uv python install 3.13t` or download from <https://www.python.org/downloads/> (the "Python 3.13 free-threaded" installer). Verify with `python3.13t -c 'import sys; print(sys.flags.gil)'`. The output should be `0` (zero means GIL disabled). On the stock build, the output is `1` or the attribute does not exist.

2. **Rerun Exercise 1 on both builds.** Capture the output of `python3 exercise-01-thread-vs-asyncio.py` on the stock 3.13 and on 3.13t. The expected difference is workload B (pure-Python sum-of-squares): on stock, threads ~ 1.0x speedup; on free-threaded, threads ~ 6-7x speedup.

3. **Rerun Exercise 2 on both builds.** Capture the output of the GIL-release audit. On the free-threaded build, every "HOLDS" verdict should become "RELEASES" — there is no GIL to hold.

4. **Audit a non-stdlib import.** Pick a library you use in production (NumPy, pandas, polars, scikit-learn, fastapi, pydantic, requests, httpx, sqlalchemy, your own). Install it on 3.13t (`uv pip install --python 3.13t numpy`, etc.). Try to import it. Note any of three outcomes:
    - **Imports cleanly with no warning**: the library has been audited and declared free-threading-safe via `Py_mod_gil = Py_MOD_GIL_NOT_USED`.
    - **Imports with a warning**: `RuntimeWarning: The global interpreter lock (GIL) has been enabled to load module 'X'`. The library was not declared safe; CPython re-enables the GIL for safety. Performance regresses; everything still works.
    - **Fails to import or to install**: there are no free-threading wheels on PyPI for this library yet; the wheel tag `cp313t` is absent.

5. **Find one library on PyPI that does not yet have free-threading wheels.** Document the project name and the issue number tracking free-threading support. Check the issue tracker. The PyPI page for any project lists available wheels; filter by tag and look for `cp313t`.

6. **Read PEP 703 §"Performance"** (<https://peps.python.org/pep-0703/#performance>) and document the single-threaded regression for your specific Python version. The PEP cites pyperformance numbers; quote the relevant number and the workload it applies to.

## Deliverable

A markdown file `challenge-01-results.md` in your homework directory with:

- The output of Exercise 1 on stock 3.13.
- The output of Exercise 1 on 3.13t. Compare side by side.
- The output of Exercise 2 on stock 3.13.
- The output of Exercise 2 on 3.13t. Note which rows changed verdict.
- A short report (3-5 paragraphs) on the third-party library you audited: what worked, what warned, what failed.
- The PyPI project you found without free-threading wheels: name, issue number, your estimate of when it will be ready.
- The single-threaded regression number from PEP 703 §"Performance," with the workload context.
- One sentence: given the audit, would you switch your production service to the free-threaded build today?

## Grading rubric

- **Installation succeeded, both builds run** (20%).
- **Exercise 1 and 2 outputs captured on both builds with the workload-B speedup visibly different** (30%).
- **Third-party library audit, with concrete evidence (the warning text or the install error)** (30%).
- **PEP 703 performance number cited correctly with workload context** (10%).
- **The "would you switch today" sentence is defended in two more sentences with concrete reasoning** (10%).

## Hints

- The free-threaded build is binary-incompatible with stock wheels. You will install separate wheels for every dependency. Use a fresh virtualenv (`uv venv --python 3.13t`).
- On macOS, the free-threaded installer is a separate `.pkg`. The `python3.13t` binary ends up at `/Library/Frameworks/Python.framework/Versions/3.13t/bin/python3.13t`.
- On Windows, the free-threaded build is an opt-in choice in the official installer (a checkbox during install).
- If a library fails to install with "no matching wheel," check whether the library has a sdist (source distribution). You may be able to compile it from source on 3.13t, but the compile may fail if the C code is not free-threading-safe.
- The Faster CPython tracking page (<https://faster-cpython.github.io/>) maintains a rolling list of free-threading-compatible major packages.

## What you should take away

The two questions this challenge answers:

1. **Is the free-threaded build real?** Yes. The performance numbers from Exercise 1 demonstrate it. Workload B's threading column went from "no speedup" to "linear speedup with cores." That is the single most consequential change to CPython since the Python 2 to Python 3 transition, and you measured it on your laptop.

2. **Is it usable in production?** Depends on your dependencies. The audit you did in step 4 is the audit your operations team would have to do for every library in your service's dependency tree. For most projects in 2026, the answer is "not quite yet — the long tail of small C extensions is still being updated, and the single-threaded regression is still meaningful." For projects that are heavily CPU-bound and run on a closed dependency set, the answer is "yes, now."

The pattern for the next 18 months: dual-build CI (test on both stock and 3.13t), single-build production (stock until the regression closes and the audit completes), opportunistic adoption for CPU-bound services that can be isolated.

## References

- **PEP 703** — Making the GIL optional. <https://peps.python.org/pep-0703/>. Sam Gross, 2023.
- **Faster CPython status** — <https://faster-cpython.github.io/>. The implementation team's rolling updates.
- **`uv` documentation** — <https://docs.astral.sh/uv/>. The Astral installer; how to install 3.13t with one command.
- **Sam Gross, "Per-Interpreter GIL and Beyond"** (PyCon 2023) — search YouTube. The reference talk.
- **`Py_mod_gil` and `Py_MOD_GIL_NOT_USED`** — <https://docs.python.org/3/c-api/module.html#c.Py_mod_gil>. The C-API contract for declaring a module free-threading-safe.

## Worked example: an audit you can do today

To make the task concrete, here is a sketch of the audit one of the curriculum authors did against NumPy 2.1 in early 2026. It is included here as a template, not as a substitute for your own audit.

### Step 1: install the build

```bash
uv python install 3.13t
uv venv --python 3.13t free-threaded-env
source free-threaded-env/bin/activate
python --version  # Python 3.13.2 (free-threaded build)
python -c "import sys; print(sys.flags.gil)"  # 0
```

The `sys.flags.gil` returning 0 is the proof. On the stock build, `sys.flags.gil` is 1 (or the attribute does not exist on older versions).

### Step 2: install the dependency under audit

```bash
pip install numpy
# Reads from PyPI. If a cp313t wheel exists, pip installs it.
# If not, pip falls back to sdist and compiles from source.
python -c "import numpy; print(numpy.__version__)"
```

The interesting case is when pip emits a warning like:

```
RuntimeWarning: The global interpreter lock (GIL) has been enabled to load
module 'numpy._core._multiarray_umath'. This module has not declared support
for the free-threaded build (Py_mod_gil = Py_MOD_GIL_NOT_USED is missing).
Performance and parallelism may be reduced. To silence this warning and
opt out of free-threading for this module, set PYTHON_GIL=1.
```

NumPy 2.1+ declares itself free-threading-safe, so this warning does not appear. NumPy 1.x and many smaller libraries still trigger it as of mid-2026. Watching the warnings during a fresh `pip install` of your dependency tree is the fastest way to inventory your audit work.

### Step 3: measure single-threaded regression

```bash
# On the stock build:
python -c "
import time
start = time.perf_counter()
total = 0
for i in range(10_000_000):
    total += i * i
print(f'stock: {time.perf_counter() - start:.3f}s, sum={total}')
"

# On the free-threaded build (same command, different interpreter):
python -c "
import time
start = time.perf_counter()
total = 0
for i in range(10_000_000):
    total += i * i
print(f'3.13t: {time.perf_counter() - start:.3f}s, sum={total}')
"
```

The reference measurement on a 2025-class laptop: stock 0.61 seconds, 3.13t 0.78 seconds, a 28% regression. PEP 703 documents the regression target as "no worse than 15% on pyperformance"; the loop above is hostile to the optimisations (no function calls, no dict access) so it shows a larger gap than the geometric mean of the benchmark suite. The Faster CPython team's tracking page reports the current geomean.

### Step 4: measure multi-threaded speedup on a CPU-bound workload

The same script, parallelised with `ThreadPoolExecutor`:

```python
import time
from concurrent.futures import ThreadPoolExecutor


def work(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total


N: int = 1_000_000
WORKERS: int = 8

start: float = time.perf_counter()
with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    results: list[int] = list(executor.map(work, [N] * WORKERS))
elapsed: float = time.perf_counter() - start
print(f"threaded: {elapsed:.3f}s, total={sum(results)}")
```

On the stock build, the elapsed time is roughly `WORKERS * (N * one_iteration_ns)` — the GIL serialises everything; threads do not help. On 3.13t, the elapsed time approaches `N * one_iteration_ns / min(WORKERS, cpu_count)` — threads scale. The ratio between the two is the headline PEP 703 win.

### Step 5: catalogue the third-party library state

Make a table. Three columns: library, version, audit status. Audit status is one of: `safe` (the module declares `Py_MOD_GIL_NOT_USED`), `warned` (loads but triggers the GIL-re-enabled warning), `unbuilt` (no cp313t wheel exists). The reference table for a small data-science stack in May 2026 looks roughly like this:

| Library | Version | Audit |
|---------|---------|-------|
| numpy | 2.1+ | safe |
| scipy | 1.13+ | safe |
| pandas | 2.2+ | safe |
| polars | 1.0+ | safe |
| matplotlib | 3.9+ | warned (Tk/Qt backends) |
| pillow | 10.4+ | safe |
| lxml | 5.2 | unbuilt as of Q1 2026 |
| psycopg2-binary | 2.9 | warned |
| cryptography | 43+ | safe |

The table tells you which of your dependencies need attention. The "unbuilt" rows are the blockers. The "warned" rows are usable but slower than they could be. The "safe" rows are the ones you can rely on.

This pattern — install on the free-threaded build, watch the warnings, build a table — is the standard audit pattern in 2026. Several teams have automated it; see the `pyodide-free-threaded` and `astral-uv-audit` projects for examples. Doing the audit manually for a small project takes 30-60 minutes; for a large project with hundreds of transitive dependencies, the automated tooling is necessary.

### What changes when the build becomes default

When 3.15 (or 3.16) makes the free-threaded build default, the audit shifts from "what works on the opt-in build" to "what *breaks* on the new default." The warnings move from advisory to active; the unbuilt cells become installation failures. The Python steering council has stated explicitly that the transition will not happen until the audit completion is high enough to make this transition painless — that is the gating criterion. Watching the `cp313t` wheel coverage on PyPI is the leading indicator. The PyPI free-threading dashboard at <https://hugovk.github.io/free-threaded-wheels/> tracks this; the percentage of the top-1000 packages with free-threading wheels was about 25% in early 2026 and has been climbing about 3 percentage points per month.

### Reading the audit's politics

The audit is also a chance to engage with the broader Python ecosystem. The `Py_mod_gil` declaration is a *contract*: the C extension author asserts that their code is thread-safe in the absence of the GIL. Some declarations have been retracted when bugs were found (see the `numpy` 2.0.1 emergency patch in November 2024 for a known example). The status of any given library is fluid; an annual re-audit is the right cadence for production projects.

The fact that this audit is *necessary* — that the language cannot guarantee thread-safety for its own ecosystem without per-library opt-in — is the engineering cost of free-threading. PEP 703 acknowledges this cost in its "Backwards Compatibility" section. The cost is real; the benefit (true thread parallelism on Python code) is also real. The audit is the bridge between them.
