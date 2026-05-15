# Exercise Solutions — Week 12

These solutions cover the four exercises in this folder. Each section gives the expected output, the reasoning, and the common gotchas. Reading the solutions before attempting the exercises is permitted but defeats the purpose; you learn more by failing first.

---

## Exercise 01 — The naive baseline and the profile

### Expected output (shape)

```
Median wall-clock over 5 runs: 250-450 ms
                                (exact number depends on hardware; a
                                 2025-class laptop should land in this
                                 range for n=50,000 pixels at sigma=2.0)

cProfile top-10 (cumulative):
         3 function calls in 0.351 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.351    0.351    0.351    0.351 ...:blur_naive
        1    0.000    0.000    0.000    0.000 ...:make_kernel_1d
        1    0.000    0.000    0.000    0.000 builtins:max/min
```

The exact format varies by Python version (3.11 vs 3.13 cProfile differ slightly in column widths) and the per-call costs are platform-dependent.

### The hot path

The cProfile output for the naive baseline shows essentially all of the wall-clock charged to `blur_naive`. The nested `for j in range(-radius, radius + 1)` loop is the inner hot path; the *per-pixel* cost is dominated by:

1. `kernel[j + radius]` — a Python list `__getitem__`, which is `~80 ns` per call.
2. `row[src_i]` — another list `__getitem__`.
3. `acc += k * v` — a Python `BINARY_OP` for the multiply followed by an in-place add.
4. `int(round(acc))` — two Python function calls.

For `n=50,000` pixels and a 13-tap kernel, the inner body runs roughly `50,000 * 13 = 650,000` times. At a few hundred nanoseconds per inner iteration, the wall-clock floor is in the 100–300 ms range.

### What the cProfile output does *not* tell you

`cProfile` is a deterministic call-counting profiler. It attributes time to function calls. A nested `for` loop inside one function shows up as one fat line — you cannot tell from cProfile alone which *line* inside `blur_naive` is the hottest. For line-level attribution you need `line_profiler` (third-party, `pip install line_profiler`, the `@profile` decorator) or `py-spy --output flamegraph.svg`.

For this exercise, the function-level attribution is enough — the hot path is obviously the inner loop because there is only one. For larger projects, line-level matters.

### Common gotcha

If you ran the exercise inside an IDE that is also CPU-active, your numbers will be 2-3x slower. Close the IDE, run from a plain terminal.

---

## Exercise 02 — The tier ladder walkthrough

### Expected output (shape, on a 2025-class laptop)

```
Workload: n=50000 pixels, sigma=2.0
Kernel size: 13 taps

Correctness checks (atol=2 grey-levels):
  [Tier 0 (self)] OK: max grey-level difference = 0
  [Tier 1] OK: max grey-level difference = 0
  [Tier 2] OK: max grey-level difference = 1
  [Tier 3] OK: max grey-level difference = 1

Wall-clock (median of 5 runs, milliseconds):
  Tier 0 (naive loop):         350.21 ms   (  1.00x)
  Tier 1 (builtin sum):        130.45 ms   (  2.68x)
  Tier 2 (numpy.convolve):       3.42 ms   (102.40x)
  Tier 3 (scipy.convolve1d):     1.80 ms   (194.56x)
```

Your exact numbers will differ by a factor of 2-3 either way; the *shape* should hold:

- Tier 0: hundreds of ms.
- Tier 1: roughly 2-3x faster than Tier 0.
- Tier 2: roughly 50-150x faster than Tier 0.
- Tier 3: roughly 100-300x faster than Tier 0.

### Why Tier 1 only buys 2-3x

Tier 1 replaces `for j in range(...)` with `sum(k * v for k, v in zip(kernel_slice, row_slice))`. The `sum` builtin iterates in C; `zip` iterates in C. But the generator expression still produces Python `float` objects and the multiplication still goes through `PyNumber_Multiply`. The C-level iteration is faster than Python bytecode iteration but the per-element arithmetic is the same.

The takeaway: builtins help when the inner work is *primitive* and *type-homogeneous*. Here the work is "multiply two floats and accumulate"; Python's number machinery is the bottleneck, not the loop machinery.

### Why Tier 2 buys 50-150x

`np.convolve` accepts the row and the kernel as NumPy arrays and runs the convolution as a single C call. The arithmetic happens on `float32` machine values (4 bytes each, native double-precision floats are 8 bytes; `float32` is faster on most hardware because of SIMD). The entire inner loop is one well-vectorised C function with bounds checking out of the hot path.

The cost: we now allocate a `float32` array of size `n` (twice the byte-count of the original `uint8` array but eight times the byte-count of a single-precision representation). For `n=50,000` this is 200 KB — negligible. For a 2D `2000 x 2000 x 3` image it would be 48 MB instead of 12 MB, which is noticeable but not crushing.

### Why Tier 3 (SciPy) sometimes buys little over Tier 2

`scipy.ndimage.convolve1d` has tighter bounds-handling code for the `mode='constant'` case and slightly less Python-level dispatch overhead than `np.convolve`. For a 1D blur on a single row, the difference is typically a factor of 2. For 2D, where `convolve1d` runs across an axis of a 2D array, the difference is larger because `np.convolve` would force you to loop in Python over rows.

### What if Tier 2 gives correctness diffs > atol?

Look at the boundary handling. `np.convolve(arr, k, mode='same')` uses *implicit* zero-padding; the Tier 0 implementation uses *explicit* zero-padding by ignoring out-of-range indices. The two should agree, but if you accidentally set `mode='full'` or `mode='valid'` in Tier 2, you will get output of different length.

For Tier 3, `mode='constant'` with `cval=0.0` matches the Tier 0 convention. `mode='nearest'` or `mode='reflect'` will give different boundary pixels.

### What if the speedup is much smaller than expected?

- Are you running under a slow Python build (debug build, `--with-pydebug`)? `python -c "import sys; print(sys.flags)"` — if `debug` is `1`, the interpreter is much slower.
- Are you on battery power? Most laptops throttle the CPU on battery. Plug in.
- Are you running other CPU-heavy processes? Close them. `top` / `Activity Monitor` will show you.
- Is your NumPy linked against a slow BLAS? `np.show_config()` should mention OpenBLAS or MKL. If it mentions only `np_internal_blas`, you have a slow build; reinstall via `pip install --upgrade numpy`.

---

## Exercise 03 — Generate a packaging skeleton

### Expected output (shape)

```
Generated skeleton at: /var/folders/.../tmp.../cc-student-demo
pyproject.toml parsed; [project].name = cc-student-demo
Layout validated: src/cc_student_demo/{__init__.py, py.typed}

Directory tree:
  LICENSE (1106 bytes)
  README.md (266 bytes)
  pyproject.toml (738 bytes)
  src/cc_student_demo/__init__.py (255 bytes)
  src/cc_student_demo/py.typed (0 bytes)
```

(Sizes are approximate; small string-substitution changes will shift them by a few bytes.)

### Why the `src/` layout

If the package directory sits at the project root (`./cc_student_demo/`) rather than under `src/`, then `python -c "import cc_student_demo"` from the project root will succeed even if you have never run `pip install -e .`. This *seems* convenient — until your tests pass locally but fail in CI because CI does run the install and discovers the wheel is broken.

With `src/`, the only way to `import cc_student_demo` is to install the package. Tests *cannot* accidentally pass against the un-installed source. This is the strongly recommended modern layout per <https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/>.

### Why the empty `py.typed`

**PEP 561** says: "Packages should distribute type information by adding a file `py.typed` to the package root directory." The file is empty. Its existence is the entire signal. Without it, downstream `mypy` ignores your type hints — even if they are correct, even if they are exhaustive — because PEP 561 is opt-in to prevent libraries from accidentally claiming type-correctness they have not committed to.

### Common gotchas

- Hyphens in distribution names, underscores in import names. `cc-student-demo` is the PyPI name. `cc_student_demo` is the Python identifier. Hyphens are illegal in Python identifiers; pip handles the conversion automatically.
- `[tool.hatch.build.targets.wheel].packages` must point to `src/<import_name>`, not `<distribution_name>`. Get this wrong and the wheel will be empty.
- TOML strings are double-quoted. Single quotes are *not* valid TOML for keys — they are only valid for "literal strings" with different escaping rules. The template uses double quotes throughout.

---

## Exercise 04 — TestPyPI dry run

### Expected output (shape)

```
=== Good case ===
findings: CLEAN

=== Bad case ===
  - missing [build-system] table (PEP 518)
  - [project].description missing
  - [project].readme missing
  - [project].requires-python missing
  - [project].name 'Bad Name With Spaces' fails distribution-name policy
  - [project].version '1.0-alpha' is not PEP 440
  - [project].authors empty or missing (recommended)
  - [project].license missing (recommended)
  - [project].classifiers missing (recommended)

=== PEP 440 spot checks ===
  '0.1.0'             predicted=True  expected=True   OK
  '1.0.0a1'           predicted=True  expected=True   OK
  '1.0.0rc1'          predicted=True  expected=True   OK
  '1.0.0.post1'       predicted=True  expected=True   OK
  '1.0.0.dev1'        predicted=True  expected=True   OK
  '1.0.0-alpha'       predicted=False expected=False  OK
  'v1.0.0'            predicted=False expected=False  OK
  '1.0'               predicted=True  expected=True   OK

=== Distribution-name spot checks ===
  'cc-jdoe-blurperf'         predicted=True  expected=True   OK
  'cc_jdoe_blurperf'         predicted=True  expected=True   OK
  'Bad Name'                 predicted=False expected=False  OK
  '-leading-hyphen'          predicted=False expected=False  OK
  '1numeric-start-ok'        predicted=True  expected=True   OK
  'dots.are.ok'              predicted=True  expected=True   OK
```

### Why this linter is "best-effort"

The full PEP 440 grammar includes:

- Epoch segments (`1!1.0.0` — used by Twisted, OpenCV, and a handful of other packages with non-sortable historical versions).
- Local versions (`1.0.0+local.identifier` — used for internal builds).
- "Equivalent" pre-release spellings (`1.0a1` vs `1.0.0a1` vs `1.0a.1`).

Our regex covers the common case. The full grammar is implemented in `packaging.version.Version` — install with `pip install packaging` and use `Version("1.0.0a1")` for the canonical check. `twine check` uses this internally.

### Why we lint distribution names

PyPI rejects uploads with invalid distribution names with a generic 400 error and a message that does not always identify the violation clearly. Catching the violation pre-upload saves a round trip.

A subtler problem: PyPI *normalises* names per [PEP 503](https://peps.python.org/pep-0503/) — `Cc-JDoe-BlurPerf`, `cc_jdoe_blurperf`, `cc.jdoe.blurperf` all resolve to the same project. The first uploader of any of these spellings claims the namespace. The capstone-naming convention (`cc-<handle>-<kernel>` all lowercase) avoids any ambiguity.

### When `twine check` adds value

`twine check` validates the *long description* — your README — for restructuredtext/markdown rendering errors. The most common failure is "long_description has syntax errors in markup and would not be rendered on PyPI." This happens when you use a `text/markdown` `description-content-type` but include unbalanced backticks or malformed table syntax.

The static linter in this exercise does not catch this. `twine check` does. Run both.

### What this exercise does *not* do

It does not connect to TestPyPI. It does not need a token. It does not upload anything. It is purely local. The point is to internalise the validation flow so that when you do upload, the upload step is the only non-local action — every other failure mode has already been caught.

---

## On dependencies for these exercises

- Exercise 01: stdlib only.
- Exercise 02: NumPy and SciPy. Skipped gracefully if missing.
- Exercise 03: stdlib only.
- Exercise 04: stdlib only; `twine` and `build` are optional and detected at runtime.

If `pip install numpy scipy` fails on your machine, you are running into a Python-on-this-platform problem. The most common cause is running the system Python 3.9 or 3.10 on macOS; install Python 3.13 from <https://www.python.org/downloads/> or use `uv python install 3.13` and create a venv from that. Do not `sudo pip install` into the system Python.

---

## Looking ahead to the capstone

The four exercises in this folder are the four phases of the capstone in miniature:

1. Baseline + profile (Exercise 01) → Monday of the capstone.
2. Tier-ladder walkthrough (Exercise 02) → Tuesday and Wednesday.
3. Packaging skeleton (Exercise 03) → Thursday and Friday.
4. Upload validation (Exercise 04) → Saturday.

If you have completed all four exercises and the outputs match the expected shapes, you are ready for `mini-project/`. If any exercise failed, fix that one first — the capstone reuses the same tools.
