# Challenge 1 — Three Implementations of the Same Workload, in Three Hours

> Pick ONE workload. Implement it THREE ways. Measure. Produce a one-page recommendation memo. Time budget: 3 hours hard cap. This is the muscle build for the mini-project; do it before Thursday.

## Time budget

| Phase | Time |
|------:|----:|
| 1. Specify the workload | 15 min |
| 2. Serial baseline | 15 min |
| 3. `ProcessPoolExecutor` implementation | 30 min |
| 4. `ThreadPoolExecutor` implementation | 30 min |
| 5. `asyncio` (with `run_in_executor` if needed) | 45 min |
| 6. Measurement harness + table | 30 min |
| 7. Recommendation paragraph | 15 min |
| **Total** | **3 h** |

If you blow past 3 hours, stop and ship what you have. The next-week mini-project is the place for polish.

## 1. The workload

The default workload (pick this unless you have a strong reason to choose something else):

**`image_blur(img: bytes, sigma: float) -> bytes`** — apply a Gaussian blur with sigma=2 to an RGB JPEG, returning the blurred bytes. Input is a 1024×768 JPEG (a real one — pick any test image; the standard `lena.png` or any 500 KB sample image works). Run the function on a list of 32 identical inputs and produce 32 outputs.

This is a CPU-bound workload that uses a C extension (`Pillow`). Pillow's blur releases the GIL during the convolution. **The interesting question is: does threading scale, even though pillow releases the GIL — and how much does the JPEG decode/encode wrapping the blur cost on each side?**

If `Pillow` is unavailable or you want to avoid it, pick from these alternatives (each is roughly equivalent in CPU profile):

- **Pure-Python prime counter** (Exercise 1's `count_primes_up_to`). Pure-Python; no GIL release. The "process pool wins" baseline.
- **`hashlib.blake2b` over 16 MB buffers**. C extension; GIL released. The "thread pool wins" baseline.
- **`numpy.linalg.eig` on 200×200 random matrices**. C extension via LAPACK; GIL released; LAPACK itself multithreaded. The "watch out for thread oversubscription" baseline.

Whichever you pick, **be specific about your inputs.** A reviewer should be able to reproduce your numbers from your `README.md`.

## 2. The three implementations

You ship three files. Each takes the same input list (a list of byte buffers, or a list of integers for the prime counter) and returns the same output list. No other differences.

### `serial.py`

```python
def run(inputs: list) -> list:
    return [work(x) for x in inputs]
```

The baseline. Run it once to confirm the workload is correct and to measure the unit cost.

### `proc_pool.py`

```python
from concurrent.futures import ProcessPoolExecutor

def run(inputs: list, workers: int = 4) -> list:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(work, inputs))
```

Plus the `if __name__ == "__main__":` guard in the driver script. Plus an explicit `multiprocessing.set_start_method('forkserver', force=True)` if you are on Linux with threads in the parent. Document your choice.

### `thread_pool.py`

```python
from concurrent.futures import ThreadPoolExecutor

def run(inputs: list, workers: int = 4) -> list:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(work, inputs))
```

### `asyncio_impl.py`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def run(inputs: list, workers: int = 4) -> list:
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return await asyncio.gather(
            *(loop.run_in_executor(pool, work, x) for x in inputs)
        )
```

For a CPU-bound workload, this is structurally similar to `thread_pool.py`. For an IO-bound or mixed workload it would be meaningfully different. Note this in your memo.

## 3. The harness

`bench.py`:

```python
import time
import os
import sys
import asyncio

def time_call(label, fn):
    t0 = time.perf_counter()
    out = fn()
    dt = time.perf_counter() - t0
    print(f"  {label:<30s}  {dt:7.3f}s")
    return label, dt

def main():
    print(f"Python {sys.version.split()[0]}, os.cpu_count()={os.cpu_count()}")
    inputs = build_inputs()      # your input list
    rows = []
    rows.append(time_call("serial", lambda: serial.run(inputs)))
    for n in (1, 2, 4, 8):
        rows.append(time_call(f"threads ({n})", lambda n=n: thread_pool.run(inputs, n)))
    for n in (1, 2, 4, 8):
        rows.append(time_call(f"processes ({n})", lambda n=n: proc_pool.run(inputs, n)))
    for n in (1, 2, 4, 8):
        rows.append(time_call(f"async+pool ({n})", lambda n=n: asyncio.run(asyncio_impl.run(inputs, n))))
    # ... print speedups vs serial ...
```

Run each scenario **three times**, take the median. Document the machine spec (OS, CPU, RAM, Python version, `sys._is_gil_enabled()`).

## 4. The acceptance criteria

A repo or directory called `c17-week-06-challenge-<yourhandle>` containing:

- `serial.py`, `proc_pool.py`, `thread_pool.py`, `asyncio_impl.py`. Each ≤80 lines.
- `bench.py`. ≤120 lines.
- A `README.md` that:
  - States the workload precisely (function signature, input distribution, what the work actually computes).
  - Shows the machine spec (CPU, cores, Python version, OS, free-threaded or not).
  - Includes the timing table (median of three runs each, all worker counts).
  - Includes one paragraph (~150 words) recommending which implementation you would ship, and why. Reference your numbers; do not hand-wave.
- A short `notes.md` (~200 words) on:
  - One thing that surprised you.
  - One thing that confirmed what the lectures predicted.
  - The GIL-release test for your workload: is the GIL held during the slowest operation? Cite the source file (e.g., `Pillow's libImaging/Filter.c`, or `Modules/_hashopenssl.c`) where you confirmed this.

## 5. The recommendation paragraph — what makes it good

A weak paragraph: *"I would use multiprocessing because it was fastest."*

A good paragraph:

> *On the default-CPython-3.13 build, the process pool with 4 workers was the fastest implementation (1.04s vs. 3.81s serial, 3.66× speedup). The thread pool was identical to serial within noise (3.74s, 1.02× speedup) — confirming that Pillow's GIL release during the convolution is not enough to offset the JPEG decode/encode cost, which is in `_imagingft.c` and holds the GIL. The asyncio + run_in_executor version matched the thread pool within 5%, because for a pure-CPU workload the asyncio layer is wasted ceremony. If I were shipping this, I would use the process pool — but only with chunksize=4 (one chunk per worker) to amortise the pickle cost over the input list, and only after measuring on the target deployment hardware. On a Mac M2 the process spawn is `spawn` and costs ~150ms per worker; on a Linux deployment with `forkserver`, the same workers cost ~5ms. Pick the start method based on deployment.*

The good paragraph names numbers, names primitives, names files, makes a defensible recommendation, and acknowledges deployment-context tradeoffs. Aim for that shape.

## 6. Common pitfalls in three hours

- **Picking a workload that is too small.** If each task is under 5ms, the pool overhead dominates and you cannot distinguish thread from process from async with meaningful confidence. Size your input so each task takes 50–500 ms.
- **Forgetting the `if __name__ == "__main__":` guard.** On macOS, this is a fork bomb. On Windows, it is a fork bomb. On Linux with default `fork`, it works by accident; do not rely on accident.
- **Running once and trusting the number.** Run three times, take the median. The first run pays a cold-start cost (JIT specialisation hot-paths, OS file cache, BLAS thread pool warm-up); your second and third runs are the real number.
- **Pickling failure on the process pool.** Closures, lambdas, locally-defined classes — none picklable by default. Top-level functions only. If you must capture state, use `initializer`/`initargs` or `joblib(loky)` (which uses `cloudpickle`).
- **Letting the report "drift" past the time budget.** This is a 3-hour exercise. Ship at 3 hours. The mini-project is the place to polish.

## 7. Stretch — only if you finish in 2 hours

- Add a `joblib_loky.py` implementation: `Parallel(n_jobs=N, backend="loky")(delayed(work)(x) for x in inputs)`. Compare the cold-start time and the warm-pool reuse cost.
- Re-run the entire benchmark on `python3.13t` (free-threaded). Compare the thread-pool rows specifically. If your workload is CPU-bound and uses a GIL-releasing C extension, the change should be minor. If it is pure-Python CPU, the change is dramatic (the thread row collapses toward the process row).
- Add the `chunksize=` argument to the process pool's `pool.map(...)`. Sweep `chunksize ∈ {1, 4, 16, 64}`. Show where the pickle amortisation curve flattens out.
- Profile your "winning" implementation with `cProfile`. Identify the second-slowest function. Is it doing what you think it is?

## 8. Submission

Push to GitHub or share a tarball. Paste the URL or path into `c17-week-06-challenge-submission.md` in your portfolio repo. One sentence on what you would do next if you had another day. Most learners answer: "add the free-threaded variant and a second workload (IO-bound) for contrast" — which is exactly the mini-project on Thursday onwards.
