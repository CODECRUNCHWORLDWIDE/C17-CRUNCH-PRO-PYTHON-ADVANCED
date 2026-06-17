# Challenge 01 — End-to-End Rehearsal (one-day dry run)

## Why this challenge exists

The capstone has six load-bearing steps: pick a kernel, write the baseline, profile, optimise, package, upload. The single most common capstone failure is discovering on Saturday that one of those six steps has a problem you have never encountered before. The fix is a *rehearsal* — walk the full pipeline once, end to end, on a problem so small that it cannot consume the day.

This challenge is that rehearsal. The problem is a 50-line script. The deliverable is a working TestPyPI upload. Budget: 4–6 hours. Outcome: when Monday's real capstone starts, every step of the pipeline is already on your laptop's muscle memory.

## The rehearsal kernel

We use the smallest plausible kernel: **a function that returns the SHA-256 hash of a bytes input, with a comparison against the stdlib `hashlib.sha256` as the reference, with a measurement of throughput on a 1 MB input.**

Why this kernel:

- The implementation is trivial (one stdlib call wraps the function).
- The benchmark is trivial (one `time.perf_counter` block).
- The interesting question is not "can I make this faster" (you cannot beat OpenSSL's SHA-256) but "can I package and publish it correctly."
- The naive baseline (a pure-Python SHA-256 implementation, which exists in <https://en.wikipedia.org/wiki/SHA-2#Pseudocode>) provides a real but uninteresting speedup figure for the report, so you can practise reporting numbers.

You will not ship this package as your capstone. You will publish it as a *rehearsal*, then unpublish (or just leave it; TestPyPI does not promise persistence and it cannot interfere with your real capstone).

## The full task

### Step 1: Set up the project (30 minutes)

```bash
mkdir cc-<your-handle>-shabench && cd cc-<your-handle>-shabench
python3.13 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip build twine pytest
```

Create the directory structure from Lecture 02:

```
cc-<your-handle>-shabench/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── cc_<your_handle>_shabench/
│       ├── __init__.py
│       ├── py.typed
│       └── _core.py
└── tests/
    └── test_smoke.py
```

### Step 2: Write the package (30 minutes)

`src/cc_<your_handle>_shabench/_core.py`:

```python
"""Tiny SHA-256 benchmark module — rehearsal package for the C17 capstone."""

from __future__ import annotations

import hashlib
import time


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of `data`. Wraps hashlib."""
    return hashlib.sha256(data).hexdigest()


def benchmark(data: bytes, runs: int = 5) -> dict[str, float]:
    """Run sha256_hex `runs` times. Return median wall-clock and throughput."""
    times: list[float] = []
    for _ in range(runs):
        t0: float = time.perf_counter()
        _ = sha256_hex(data)
        times.append(time.perf_counter() - t0)
    times.sort()
    median: float = times[len(times) // 2]
    mb_per_s: float = (len(data) / median) / 1_000_000.0
    return {"median_seconds": median, "throughput_mb_per_s": mb_per_s}
```

`src/cc_<your_handle>_shabench/__init__.py`:

```python
"""cc-<your-handle>-shabench: rehearsal package."""

from cc_<your_handle>_shabench._core import benchmark, sha256_hex

__version__ = "0.1.0"
__all__ = ["benchmark", "sha256_hex"]
```

`tests/test_smoke.py`:

```python
from cc_<your_handle>_shabench import sha256_hex, benchmark


def test_known_vector() -> None:
    # SHA-256 of empty string is e3b0c44...
    assert sha256_hex(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_benchmark_returns_floats() -> None:
    result: dict[str, float] = benchmark(b"x" * 1024, runs=3)
    assert "median_seconds" in result
    assert result["median_seconds"] > 0
    assert result["throughput_mb_per_s"] > 0
```

### Step 3: Write the pyproject.toml (30 minutes)

Use the template from Lecture 02. Critical: substitute *your* handle everywhere, and set `version = "0.1.0a1"` so it is clearly a pre-release.

### Step 4: Local install and test (15 minutes)

```bash
pip install -e .[dev] 2>&1 | tail -5
pytest -v
```

If `pip install -e .` fails, look at the build backend configuration. Common cause: `[tool.hatch.build.targets.wheel].packages = ["src/cc_<wrong_name>"]`.

### Step 5: Build (15 minutes)

```bash
python -m build
ls -lh dist/
```

You should see:

```
cc_<your_handle>_shabench-0.1.0a1-py3-none-any.whl
cc_<your_handle>_shabench-0.1.0a1.tar.gz
```

If either is missing, the build failed silently — read the `build` output and fix.

### Step 6: Static check (5 minutes)

```bash
twine check dist/*
```

Expected: `PASSED` for both files. If the README is malformed, fix it.

### Step 7: Verify the wheel contents (10 minutes)

```bash
unzip -l dist/cc_<your_handle>_shabench-0.1.0a1-py3-none-any.whl
```

Expected to include `cc_<your_handle>_shabench/__init__.py`, `cc_<your_handle>_shabench/_core.py`, `cc_<your_handle>_shabench/py.typed`, and a `cc_<your_handle>_shabench-0.1.0a1.dist-info/` metadata directory containing `METADATA`, `WHEEL`, and `RECORD`.

If `py.typed` is missing from the wheel, your build backend did not pick it up. For hatchling, ensure the file is present in the source tree before `python -m build` — hatchling includes everything under the packages directory by default.

### Step 8: Sign up for TestPyPI (20 minutes)

If you have not already:

1. Register at <https://test.pypi.org/account/register/>.
2. Confirm your email.
3. Enable 2FA (TestPyPI requires it for upload).
4. Generate an account-scoped API token.
5. Save the token to `~/.pypirc` (mode `0600`).

### Step 9: Upload (5 minutes)

```bash
twine upload --repository testpypi dist/*
```

Expected output: progress bars, a URL printed at the end. Visit the URL. Verify the README renders.

### Step 10: Install from TestPyPI on a fresh venv (15 minutes)

```bash
deactivate
python3.13 -m venv /tmp/cap-rehearsal-test
source /tmp/cap-rehearsal-test/bin/activate

pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    cc-<your-handle>-shabench

python -c "from cc_<your_handle>_shabench import sha256_hex; print(sha256_hex(b''))"
```

If this prints the all-zeros SHA-256 hex, you have a working public package. Congratulations — the rehearsal is done.

### Step 11: Write a one-page report (60 minutes)

The rehearsal report is a half-scale version of the real capstone report. Use the template from `mini-project/REPORT.template.md`. Fill in:

- The trivial speedup (CPython `hashlib.sha256` over a pure-Python implementation if you wrote one; "not pursued" if you did not).
- The methodology (median of N runs, hardware, Python version).
- The reproduction instructions.

The point of writing the rehearsal report is to discover any gaps in the template *before* you fill in the real one. Common gaps you might find:

- The template asks for "thermal throttling status" and you do not know how to check.
- The template asks for "memory peak" and you do not know which tool to use.
- The template asks for "confidence interval" and you have not implemented the bootstrap.

Fix the gaps in your tooling now, not on Saturday.

### Step 12: Optionally delete the rehearsal package (5 minutes)

Go to <https://test.pypi.org/manage/project/cc-<your-handle>-shabench/> and use the "Delete" option. You may also leave it — TestPyPI does not promise persistence and the rehearsal package is harmless. The real capstone uses a *different* distribution name.

## Acceptance criteria

You have completed Challenge 01 when:

- [ ] The rehearsal package is installable from TestPyPI on a fresh venv.
- [ ] `pytest` passes against the installed package.
- [ ] You have written a one-page report following the REPORT template.
- [ ] You can articulate, in writing, what was the slowest step in the pipeline for you — and have a plan to make that step faster during the real capstone.

## Why the slowest step matters

The slowest step in the rehearsal is the slowest step in the real capstone, multiplied by however many times bigger the real kernel is. If you spent 90 minutes wrestling with `pyproject.toml` because hatchling's documentation surprised you, expect to spend 90 minutes wrestling with `pyproject.toml` during the real capstone unless you fix the underlying confusion now. If you spent 60 minutes fighting 2FA on TestPyPI because you lost your authenticator-app seed, fix that now.

The rehearsal exists so the failure modes are cheap. The capstone exists so the deliverable is real. Do not skip the rehearsal.

## Time estimate summary

| Step                       | Estimated time |
|----------------------------|---------------:|
| Project setup              |         30 min |
| Write package              |         30 min |
| Write pyproject.toml       |         30 min |
| Local install and test     |         15 min |
| Build                      |         15 min |
| Static check               |          5 min |
| Verify wheel contents      |         10 min |
| TestPyPI signup            |         20 min |
| Upload                     |          5 min |
| Verify fresh-venv install  |         15 min |
| Write report               |         60 min |
| Optional cleanup           |          5 min |
| **Total**                  |    ~4 hours    |

If your total exceeds 6 hours, identify which step blew up and write it down. That is the most valuable artefact of the rehearsal — a list of the steps that cost you more than expected.

## References

- Lecture 02 of this week.
- [PyPA Packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/).
- [TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/).
- [hatchling docs](https://hatch.pypa.io/latest/).
