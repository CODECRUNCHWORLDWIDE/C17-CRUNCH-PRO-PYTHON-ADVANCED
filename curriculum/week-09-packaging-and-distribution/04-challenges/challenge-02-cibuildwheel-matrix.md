# Challenge 2 — `cibuildwheel` on a tiny C-extension package

**Estimated time:** 3–4 hours, of which most is waiting on CI. **Outcome:** A GitHub Actions workflow that uses `cibuildwheel` to produce platform-specific wheels for a tiny native package, covering at least three platforms (Linux x86_64, macOS arm64, Windows x86_64) and at least three Python versions (3.11, 3.12, 3.13). You will inspect every produced wheel's filename, verify the `auditwheel show` output for the Linux ones, and write a 300-word note on what `cibuildwheel` actually did.

## The package

Use the tiniest possible native package — Week 8's `sum_squares` C kernel exposed via `ctypes`, *or* a five-line Cython extension. The point is not the kernel; the point is exercising the wheel-building matrix. Suggested shape:

```
mywheel-demo/
├── pyproject.toml
├── README.md
├── src/
│   └── mywheel_demo/
│       ├── __init__.py
│       └── _kernel.pyx       # Cython source; or kernel.c for setuptools-Extension
└── tests/
    └── test_kernel.py
```

The `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools >= 67", "cython >= 3.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mywheel-demo"
version = "0.0.1"
description = "Tiny native package for cibuildwheel exercise."
requires-python = ">= 3.11"
license = "MIT"

[tool.setuptools.packages.find]
where = ["src"]

[tool.cibuildwheel]
# Build for these CPython versions (matches your test matrix).
build = ["cp311-*", "cp312-*", "cp313-*"]
# Skip the 32-bit Linux builds (manylinux_2_28 i686 is increasingly niche).
skip = ["*-musllinux_*", "*-win32", "*-manylinux_i686"]
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

And the GitHub Actions workflow:

```yaml
# .github/workflows/wheels.yml
name: wheels

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build_wheels:
    name: Build on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-14, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/cibuildwheel@v2.20.0
      - uses: actions/upload-artifact@v4
        with:
          name: cibw-wheels-${{ matrix.os }}-${{ strategy.job-index }}
          path: ./wheelhouse/*.whl
```

## Step-by-step

1. **Write the package.** A `_kernel.pyx` (or `.c`) with one function (`sum_squares` from Week 8 works). A `setup.py` is not required if you use `[tool.setuptools.ext-modules]` in `pyproject.toml`, but a small `setup.py` declaring the Cython `Extension` is the path of least resistance for now (setuptools's `pyproject.toml`-native ext-modules support is still maturing in 2026).

2. **Test `cibuildwheel` locally on your own platform.** `pip install cibuildwheel`; `python -m cibuildwheel --output-dir wheelhouse` builds wheels for the current platform. On macOS arm64, you get `cp311-cp313` wheels for arm64. The whole local build should take 3–5 minutes.

3. **Run the GitHub Actions workflow.** Push a tag (`v0.0.1`); the workflow runs. Three jobs in parallel (Ubuntu, macOS 14 = arm64, Windows). Each takes 5–15 minutes. Total wall time ~15 minutes.

4. **Inspect every produced wheel.** The `wheelhouse/` artifacts you download from the workflow should contain wheels like:

   ```
   mywheel_demo-0.0.1-cp311-cp311-manylinux_2_28_x86_64.whl
   mywheel_demo-0.0.1-cp312-cp312-manylinux_2_28_x86_64.whl
   mywheel_demo-0.0.1-cp313-cp313-manylinux_2_28_x86_64.whl
   mywheel_demo-0.0.1-cp311-cp311-macosx_11_0_arm64.whl
   mywheel_demo-0.0.1-cp312-cp312-macosx_11_0_arm64.whl
   mywheel_demo-0.0.1-cp313-cp313-macosx_11_0_arm64.whl
   mywheel_demo-0.0.1-cp311-cp311-win_amd64.whl
   mywheel_demo-0.0.1-cp312-cp312-win_amd64.whl
   mywheel_demo-0.0.1-cp313-cp313-win_amd64.whl
   ```

   Nine wheels for the 3 platforms × 3 Pythons matrix. Each filename encodes the python tag, ABI tag, and platform tag per PEP 425.

5. **Run `auditwheel show` on the Linux wheels.** On a Linux machine (or in a manylinux Docker container):

   ```bash
   docker run --rm -v "$PWD:/io" quay.io/pypa/manylinux_2_28_x86_64 \
     auditwheel show /io/mywheel_demo-0.0.1-cp313-cp313-manylinux_2_28_x86_64.whl
   ```

   Expected output:

   ```
   mywheel_demo-0.0.1-cp313-cp313-manylinux_2_28_x86_64.whl is consistent with the
   following platform tag: "manylinux_2_28_x86_64".

   The wheel references external versioned symbols in these system-provided
   shared libraries: libc.so.6 with versions {'GLIBC_2.2.5', 'GLIBC_2.14'}, ...

   This constrains the platform tag to "manylinux_2_28_x86_64".
   ```

   The `auditwheel show` output names every shared library the wheel links against. For a manylinux_2_28 wheel, the libraries must all be in the manylinux policy whitelist (libc, libpthread, libm, libdl, librt, ...) — if any are not, `auditwheel repair` would bundle them into the wheel, and the wheel's tag would be downgraded if it could not satisfy the policy.

6. **Install one wheel per platform and run the test.** On Linux x86_64: `pip install mywheel_demo-0.0.1-cp313-cp313-manylinux_2_28_x86_64.whl` should succeed and `import mywheel_demo` should work. Repeat on macOS arm64 and Windows.

7. **Write a 300-word note (`NOTES.md`).** Cover:

   - What `cibuildwheel` did under the hood (Docker for Linux, native for macOS and Windows).
   - The matrix you built: list every wheel produced.
   - One observation from `auditwheel show` — what library did your wheel actually depend on?
   - The CI wall time (cold cache vs. warm cache, if you did multiple runs).
   - One thing that surprised you. (Common: the Linux wheels are larger than the macOS ones because of static-link of the C runtime in some cases.)

## Acceptance

- [ ] The package builds cleanly on at least one local platform (your machine).
- [ ] The GitHub Actions workflow runs end-to-end with green for at least three platforms.
- [ ] Wheels for at least nine combinations (3 platforms × 3 Pythons) are uploaded as artifacts.
- [ ] `auditwheel show` output captured for at least one Linux wheel.
- [ ] One successful `pip install` + `import` per platform (on a machine you have access to).
- [ ] `NOTES.md` of ~300 words.
- [ ] `pyproject.toml` parses (verify with `tomllib.load`).

## What you should find

- **Linux wheels carry the `manylinux_2_28` tag** — cibuildwheel ran inside the manylinux2_28 Docker container, then post-processed with `auditwheel`. Without the post-processing, the wheels would be tagged `linux_x86_64` and would be rejected by PyPI.
- **macOS wheels are universal-ish but actually single-arch.** The matrix builds an arm64 wheel on macos-14 and an x86_64 wheel on macos-13 (or a `macosx_*_universal2` wheel if you opt into it). Pick one.
- **Windows wheels are tagged `win_amd64` without post-processing.** Windows does not have an `auditwheel` equivalent because Windows DLL handling is fundamentally different (DLLs are typically system-resident or installed via separate redistributables).
- **The CI run takes 10–15 minutes for a tiny package.** Most of the time is in cibuildwheel's setup (downloading the manylinux Docker image, installing Cython in the build env, the per-Python rebuild loop). A larger project does not take proportionally longer for the wheel-building step; the dominating cost is per-Python rebuild.

## Notes

- **`cibuildwheel` is the only sane way to build Linux wheels.** Doing it by hand with Docker is educational; doing it for nine combinations every release is not. Use cibuildwheel.
- **The `manylinux_2_28` baseline is the right default in 2026.** Older baselines (`manylinux2014`, `manylinux_2_17`) cover more systems but are increasingly irrelevant. The PyPA `manylinux` README has the up-to-date guidance: <https://github.com/pypa/manylinux>.
- **Test on the actual target platform.** Building a wheel that *imports* in CI does not prove it works in the real world. Where possible, have a test step that runs the test suite against the built wheel on each platform.
- **`auditwheel show` is your first-line diagnostic** for "why is my Linux wheel not installable." It tells you exactly which libraries the wheel needs and whether they conform to the manylinux policy.

## Reading

- The `cibuildwheel` documentation: <https://cibuildwheel.pypa.io/>. ~30 minutes.
- The `manylinux` README: <https://github.com/pypa/manylinux>. ~15 minutes.
- The `auditwheel` README and the `show` command docs: <https://github.com/pypa/auditwheel>. ~15 minutes.
- PEP 600 (the manylinux policy): <https://peps.python.org/pep-0600/>. ~30 minutes.
- The release workflow of any active C-extension project: `pydantic`, `cryptography`, `numpy`. Look at `.github/workflows/wheels.yml` or equivalent.
