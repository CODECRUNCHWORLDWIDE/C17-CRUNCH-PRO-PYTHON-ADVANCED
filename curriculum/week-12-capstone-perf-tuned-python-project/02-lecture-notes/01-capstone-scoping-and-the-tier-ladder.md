# Lecture 01 — Capstone Scoping and the Tier Ladder

> *The single most common failure mode of a perf-tuning project is not under-optimisation. It is over-scoping. The engineer picks a problem too large, profiles for a day, optimises for a day, tries to parallelise on a day they should have spent packaging, and discovers on the morning of the deadline that the deliverable does not yet install on a clean machine. The fix is structural: pick a kernel small enough that the entire pipeline — baseline, profile, optimise, parallelise, package, publish, report — fits the week. Then walk the tier ladder. Then ship.*

## 1. What "scoping" actually means

Scoping is the discipline of writing down, on Monday, three documents:

1. **The kernel description.** One paragraph. What is the input? What is the output? What is the correctness oracle (the function that decides whether your fast version produces the right answer)?
2. **The success criteria.** One paragraph. What number do you have to beat? Against what baseline? On what hardware?
3. **The non-goals.** One paragraph. What are you explicitly *not* going to do this week? (Cross-platform wheels for every Python version. A GPU backend. A web UI. A Rust rewrite. A new sampling algorithm in the literature.)

The non-goals paragraph is the most important. The senior engineer's skill is not technique selection; it is technique *omission*. If your capstone has nine of the W1–W11 techniques and is missing one because it would not have helped, that is a stronger deliverable than a capstone with all eleven applied indiscriminately. The reviewer reading your report wants to see judgement, not exhaustiveness.

### A worked example: the gaussian blur

- **Kernel description.** Input: a NumPy array of shape `(H, W, 3)`, dtype `uint8`, representing an RGB image. Sigma is a positive float. Kernel size is `2 * ceil(3 * sigma) + 1`. Output: a NumPy array of the same shape and dtype, with each pixel replaced by the weighted average of its neighbours under a 2D gaussian kernel of standard deviation sigma. Correctness oracle: `numpy.testing.assert_allclose(my_result, scipy.ndimage.gaussian_filter(image, sigma=sigma, axes=(0, 1)), atol=1)` — within one grey-level of the reference SciPy implementation, which is itself a well-tested C kernel.
- **Success criteria.** On a `2000 x 2000 x 3` test image with sigma=2.0 on the reference hardware (Apple M3 Pro, 8 GB free RAM, Python 3.13.0, macOS 14.4): naive triple-nested Python `for` loop establishes the baseline of approximately 90 seconds. The capstone must beat the baseline by at least `100x` and reach at least 80% of SciPy's own performance. Memory peak must remain under `2x` the input image size.
- **Non-goals.** Cross-platform wheel matrix (one wheel for the author's platform is acceptable for TestPyPI). GPU acceleration (CUDA, Metal). Anti-aliased boundary handling beyond zero-padding. Floating-point output (we stay in `uint8`). Anisotropic gaussians (single sigma scalar only). Cython (we use either NumPy or a hand-written C extension; no third intermediate language).

That is the scope. About four hundred words. Everything else flows from it.

## 2. The tier ladder

Once the scope is fixed, the optimisation work is structured. Walk the tiers in order, measure at every step, stop when you have hit the success criteria. **Do not skip tiers** — if NumPy gets you 99% of the way there, do not write a C extension to chase the last 1%; the reviewer will subtract points for the unjustified complexity. **Do not skip steps within a tier** — if you do not profile after each change, you cannot say which change caused the speedup.

### Tier 0 — The naive baseline

Write the slowest correct version of the kernel first, on purpose. The naive baseline serves three roles: (a) it is the correctness reference for every subsequent version; (b) it is the speedup denominator for the report; (c) it tells you, when you profile it, where the time actually goes.

For the gaussian blur, the naive baseline is the triple-nested Python loop:

```python
def blur_naive(image: np.ndarray, sigma: float) -> np.ndarray:
    h, w, c = image.shape
    k = make_kernel(sigma)
    radius = k.shape[0] // 2
    out = np.zeros_like(image)
    for y in range(radius, h - radius):
        for x in range(radius, w - radius):
            for ch in range(c):
                acc = 0.0
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        acc += k[dy + radius, dx + radius] * image[y + dy, x + dx, ch]
                out[y, x, ch] = int(acc)
    return out
```

This is approximately 90 seconds on the reference hardware for a 2000x2000 image. It is correct (assuming `make_kernel` returns a normalised gaussian) and it is the slowest possible Python version short of obviously gratuitous overhead (writing to a list and converting back, recreating the kernel inside the loop, etc.). The job of the baseline is to be *easy to verify correct*, not to be representative of what a beginner would write.

### Tier 1 — Algorithmic improvement

Before reaching for tools, look at the algorithm. The gaussian kernel is separable: a 2D gaussian convolution is mathematically equivalent to a 1D gaussian convolution along the rows followed by a 1D gaussian convolution along the columns. This reduces the per-pixel cost from `O(k^2)` to `O(2k)`. For sigma=2.0, k=13, that is `169` operations versus `26` — about a `6.5x` algorithmic speedup before we have changed a single library call.

```python
def blur_separable(image: np.ndarray, sigma: float) -> np.ndarray:
    k1d = make_kernel_1d(sigma)
    radius = k1d.shape[0] // 2
    # ... 1D pass along x ...
    # ... 1D pass along y ...
```

Algorithmic improvements are the cheapest speedups available. They cost no extra dependencies, no extra build steps, no extra C, no extra processes. The discipline of the perf-tuner is to look at the algorithm *first*. Read the literature. Read `scipy.ndimage.gaussian_filter` — its docstring tells you it uses the separable form. The separable trick for gaussians has been known since the 1960s; pretending you would not have known it is dishonest.

### Tier 2 — Vectorisation (NumPy, stdlib)

The hot path of the separable form is still a Python loop over rows, then a Python loop over columns. NumPy can turn each into a single ufunc call.

```python
from scipy.signal import convolve

def blur_numpy(image: np.ndarray, sigma: float) -> np.ndarray:
    k1d = make_kernel_1d(sigma)
    # Convolve along axis 1, then axis 0
    pass1 = np.apply_along_axis(lambda r: np.convolve(r, k1d, mode='same'), 1, image.astype(np.float32))
    pass2 = np.apply_along_axis(lambda r: np.convolve(r, k1d, mode='same'), 0, pass1)
    return np.clip(pass2, 0, 255).astype(np.uint8)
```

The `np.apply_along_axis` is still iterating in Python (one loop per row, one per column), but each row-call is now a C-implemented `np.convolve` that releases the GIL. On the reference hardware: approximately 1.2 seconds. The speedup from Tier 1 is roughly `12x`, the cumulative speedup from Tier 0 is roughly `75x`. We have not written a single line of non-Python code yet.

A genuinely vectorised version (no Python loop at all) uses `scipy.signal.convolve` directly with a 2D kernel constructed as the outer product of two 1D kernels, or `scipy.ndimage.convolve1d` along each axis:

```python
from scipy.ndimage import convolve1d

def blur_numpy_full(image: np.ndarray, sigma: float) -> np.ndarray:
    k1d = make_kernel_1d(sigma)
    img = image.astype(np.float32)
    img = convolve1d(img, k1d, axis=1, mode='constant')
    img = convolve1d(img, k1d, axis=0, mode='constant')
    return np.clip(img, 0, 255).astype(np.uint8)
```

Approximately 200 ms. Cumulative speedup roughly `450x`. We are now within `2x` of SciPy's own `gaussian_filter`, because we *are* essentially calling SciPy. This is fine. The capstone is allowed to use SciPy. The capstone is graded on whether you understood the tier ladder, not on whether you reinvented every wheel.

### Tier 3 — C extension where it earns its keep

After Tier 2 the speedups available from Tiers 3 and 4 are smaller and have higher complexity costs. The decision to climb to Tier 3 should be deliberate.

For the gaussian blur, a hand-written C extension can beat NumPy for small kernels because of fixed-cost overhead per `convolve1d` call (a few microseconds for allocation, dispatch, and validation). On a 2000x2000 image with k=13 the overhead is amortised; on a `100 x 100` image called 400 times in a row, it dominates. If your capstone's success criteria include "small-image throughput" or "low-latency single-image processing," then Tier 3 is justified. If it does not, skip Tier 3 and document the decision in REPORT.md.

When Tier 3 *is* justified, the structure is the one from Week 8:

```c
static PyObject *blur_c(PyObject *self, PyObject *args) {
    PyArrayObject *img_arr;
    PyArrayObject *k_arr;
    if (!PyArg_ParseTuple(args, "O!O!", &PyArray_Type, &img_arr, &PyArray_Type, &k_arr)) {
        return NULL;
    }
    // Validate shapes and dtype...
    PyArrayObject *out = (PyArrayObject *)PyArray_NewLikeArray(img_arr, NPY_CORDER, NULL, 0);
    if (out == NULL) return NULL;

    Py_BEGIN_ALLOW_THREADS
    // The hot loop, in C, with the GIL released.
    convolve_1d_uint8(PyArray_DATA(img_arr), PyArray_DATA(k_arr), PyArray_DATA(out), /* ... */);
    Py_END_ALLOW_THREADS

    return (PyObject *)out;
}
```

The `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` pair is load-bearing for Tier 4 — without it, threading will not scale because the C code will hold the GIL.

Reach for **PEP 489** multi-phase initialisation if you want subinterpreter compatibility. For a capstone, single-phase init is fine and shorter; document the trade-off in REPORT.md.

### Tier 4 — Parallelisation

The decision tree is from Week 11:

| Workload character                                       | Model on stock 3.13           | Model on free-threaded 3.13   |
|-----------------------------------------------------------|-------------------------------|-------------------------------|
| I/O-bound (network, disk, sleep)                          | threads or asyncio            | threads or asyncio            |
| CPU-bound, pure Python                                    | multiprocessing               | threads                       |
| CPU-bound, dominated by GIL-releasing C extension         | threads                       | threads                       |
| CPU-bound, large inputs (the pickling tax matters)        | multiprocessing + shared_memory or subinterpreters | threads |
| High-concurrency I/O (10k+ in flight)                     | asyncio                       | asyncio                       |

The gaussian blur after Tier 3 is "CPU-bound, dominated by GIL-releasing C extension" — the convolve loop is in C with the GIL released. **Threads** are the right choice for fanning out across multiple images. A `ThreadPoolExecutor` with `os.cpu_count()` workers will scale near-linearly on the convolution itself.

```python
from concurrent.futures import ThreadPoolExecutor

def blur_batch(images: list[np.ndarray], sigma: float) -> list[np.ndarray]:
    with ThreadPoolExecutor() as pool:
        return list(pool.map(lambda img: blur_c(img, sigma), images))
```

This is the simplest possible Tier 4. It is also, for this workload, the most correct one. Skip the complexity of multiprocessing because we do not need to escape the GIL — the C extension already did.

### Stopping the ladder

You stop walking the ladder when you have hit the success criteria. For the gaussian-blur worked example:

- Tier 0: 90 seconds.
- Tier 1 (separable): 14 seconds. `6.5x`.
- Tier 2 (NumPy/SciPy): 200 ms. Cumulative `450x`.
- Tier 3 (C extension): 80 ms. Cumulative `1125x`. **Reach for this only if Tier 2 did not meet your criteria.**
- Tier 4 (ThreadPoolExecutor on batches): scales to N images in `~80 ms each` instead of `~80 * N ms` total.

The success criteria were `100x` and 80% of SciPy. Tier 2 alone hits both. Tier 3 is optional and the report should say so. Tier 4 is justified by the batch use case stated in the kernel description; if the kernel is "blur one image" then Tier 4 is unjustified and should be cut.

## 3. The discipline of skipping

The hardest part of the tier ladder is not climbing it. It is *not climbing* it. A capstone that skips Tier 3 because Tier 2 was sufficient is a *better* capstone than one that wrote a C extension to chase a 2x improvement on top of an already-acceptable Tier 2. Hiring managers reading your REPORT.md are looking for one specific signal: did the candidate know when to stop?

The way to signal this is to write the skipped tier into the report explicitly. A paragraph headed "Tier 3 (C extension): not pursued. Tier 2 met the success criteria. The Tier 3 trade-off — adding C compilation to the build pipeline, restricting the wheel matrix, increasing the maintenance burden, and producing an estimated additional `2.5x` based on the NumPy overhead profile — was not justified for the stated workload." That paragraph is worth more than a working C extension.

## 4. Per-prior-week reminders

This lecture stays at the architecture level. The implementation reminders, one per prior week:

- **W1 (CPython internals).** Understand what `np.ndarray` actually is at the C level — it is a `PyObject` with a header followed by a contiguous buffer. The buffer is what you operate on in C.
- **W2 (memory).** A 2000x2000x3 `uint8` image is 12 MB. Float32 is 48 MB. Watch for accidental upcasting; `image * 1.0` creates a float64 array and quadruples memory.
- **W3 (bytecode).** `dis.dis(blur_naive)` shows you the `FOR_ITER`, `BINARY_OP`, `STORE_SUBSCR` opcodes. The triple-nested loop generates an enormous bytecode stream relative to one NumPy call.
- **W4 (asyncio).** Not relevant here — there is no I/O.
- **W5 (structured concurrency).** Not relevant here either. If your kernel had I/O, `TaskGroup` would be the right primitive.
- **W6 (threads vs processes).** Threads on stock CPython for GIL-releasing C, as discussed.
- **W7 (profiling).** Run `cProfile` on the naive baseline. The hot line will be the innermost `acc += k[dy + radius, dx + radius] * image[y + dy, x + dx, ch]`. Confirm it accounts for >90% of wall time before doing anything else.
- **W8 (C extensions).** If you reach Tier 3, this is your reference. Multi-phase init, `Py_BEGIN_ALLOW_THREADS`, NumPy's [C-API](https://numpy.org/doc/stable/reference/c-api/index.html).
- **W9 (packaging).** Next lecture.
- **W10 (metaprogramming).** You probably do not need any. A function-level public API with type hints is sufficient.
- **W11 (concurrency).** See the table above.

## 5. Common scoping mistakes

- **The kernel is too big.** "An image-processing library" is not a kernel. "A 2D gaussian blur for `uint8` RGB images" is. The library can have one filter; ship that and call it done.
- **The success criteria are not numeric.** "Make it faster" is not a success criterion. "Beat the baseline by at least `100x` on the reference hardware" is.
- **The correctness oracle does not exist.** If you cannot say `assert_allclose(my_result, reference)`, you cannot say your fast version is correct. The reference might be SciPy, NumPy, the naive baseline itself, or a hand-checked output for a fixed test input.
- **The hardware is not stated.** Without a hardware spec, the speedup numbers are meaningless. State the CPU model, the RAM, the OS, the Python version, the power state.
- **No non-goals paragraph.** Without an explicit list of what you are not doing, you will end up doing all of it by Friday.

## 6. The Monday deliverable

By the end of Monday, you have, in `mini-project/SCOPE.md` (which you will create):

- The kernel description (one paragraph).
- The success criteria (one paragraph with at least two numbers).
- The non-goals (one paragraph).
- The naive baseline implementation, working and correct, with a `time.perf_counter` wall-clock measurement on your hardware.

Tuesday begins with the profile of that baseline. Wednesday with Tier 2 and possibly Tier 3. Thursday with Tier 4 and the packaging skeleton. Friday with the packaging end-to-end. Saturday with the TestPyPI upload and the report. Sunday is the final exam.

If you do not have Monday's deliverables on Monday, you will not have a capstone on Sunday. The schedule is not generous. Scope tightly.

## References

- The W1–W11 lecture notes of this track.
- Knuth, Donald. "Structured Programming with go to Statements" (1974), *ACM Computing Surveys*, vol. 6, no. 4. Source of "premature optimisation is the root of all evil," which the senior engineer knows extends to *measured* premature optimisation — picking the right tier means measuring before climbing.
- Gorelick, Micha and Ozsvald, Ian. *High Performance Python*, 2nd ed. (O'Reilly, 2020). Chapter 1: "Understanding Performant Python." Chapter 5: "Iterators and Generators."
- [scipy.ndimage source](https://github.com/scipy/scipy/tree/main/scipy/ndimage). The reference for what a production-grade C-level filter implementation looks like; read once.
