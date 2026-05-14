# Lecture 3 — The 3.13 Free-Threaded Build, Revisited

> **Duration:** ~1.5 hours. **Outcome:** You can install the 3.13t build via `uv` or `pyenv`; you can detect at runtime whether the GIL is enabled or disabled; you can predict which of your code paths are correctness-affected by the GIL removal (essentially none, if you have been writing locks); you can predict which paths are *performance*-affected (the pure-Python CPU paths, which now scale with threads); you know the three classes of compatibility hazard (free-threaded-incompatible C extensions, biased-refcount edge cases, latent races); you can read the PEP 703 implementation notes and recognise the key data structures (the biased reference-counting scheme, the per-object lock, the deferred reference-counting heap).

## 1. What PEP 703 actually does

Week 3 covered PEP 703 from inside the interpreter: what `take_gil` and `drop_gil` are, what the eval-breaker is, how the gilstate per-thread structure threads through every C API call. This lecture is the practitioner's side: **what changes about your code, when the runtime is `python3.13t` instead of `python3.13`, and what stays the same.**

The short answer: the language semantics are unchanged. The same Python source code runs and produces the same results. What changes is **the relationship between `threading.Thread` and CPU parallelism**.

On default CPython (`python3.13`): N threads running pure-Python code run at 1× speed, modulo overhead. The GIL serialises them. To get parallelism, you reach for `multiprocessing` (Lecture 2).

On the free-threaded build (`python3.13t`): N threads running pure-Python code run at ~N× speed on N cores, modulo overhead. The GIL is *not present*. `threading.Thread` is now a real parallelism primitive for pure-Python work.

That single sentence is the entire user-facing change. Everything else in this lecture is either *how* it works underneath, *what to watch out for*, or *how to measure* the win.

PEP 703 (Sam Gross, 2023; accepted 2024; rolling out via 3.13–3.15) is the third serious attempt at GIL removal. The first (`Stackless Python`, 1999) and the second (`Gilectomy`, 2017) both failed: the former because it required language-level redesign, the latter because the slowdown on single-threaded code was ~2× and unacceptable. Gross's approach is different — it uses **biased reference counting** (§5.1 of the PEP) to make the common case (single-threaded refcount updates) fast, with atomic refcount updates only when an object crosses threads. The PEP claims a single-threaded slowdown of "less than 10%" in the 3.13t initial release; subsequent releases will close that gap.

## 2. Installing `python3.13t`

The free-threaded build ships alongside the regular 3.13 build but is a *separate executable*. You cannot enable or disable the GIL on a regular `python3.13`; you need the binary built with `--disable-gil`.

Three options, in order of ease:

**Option A: `uv` (recommended).**

```bash
uv python install 3.13t
uv run --python 3.13t python -c "import sys; print(sys._is_gil_enabled())"
```

Output: `False`. The interpreter is free-threaded; the GIL is disabled by default. `uv` downloads a prebuilt 3.13t from `python-build-standalone`. This is the fastest path.

**Option B: `pyenv`.**

```bash
pyenv install 3.13t-dev   # or 3.13.0t depending on version
pyenv shell 3.13t-dev
python -c "import sys; print(sys._is_gil_enabled())"
```

**Option C: build from source.**

```bash
git clone https://github.com/python/cpython.git
cd cpython
./configure --disable-gil --enable-optimizations
make -j$(nproc)
./python -c "import sys; print(sys._is_gil_enabled())"
```

The build takes 15–45 minutes depending on machine. Worth doing once, to see the `--disable-gil` flag flow through to the `Py_GIL_DISABLED` preprocessor macros in `Include/internal/pycore_runtime.h` and the call sites that branch on it.

## 3. Detecting the GIL at runtime

Two APIs, both useful in different contexts.

**`sys._is_gil_enabled()`** — returns `True` on default CPython, `False` on 3.13t with the GIL disabled. The underscore indicates the API is provisional (subject to rename in 3.14+; the underlying mechanism is stable). Cheap to call; safe in hot paths if you must.

**`sysconfig.get_config_var('Py_GIL_DISABLED')`** — returns `1` if the *build* was configured with `--disable-gil`, `0` otherwise. This is the build-time flag, not the runtime state. On 3.13t, the GIL can in principle be re-enabled at startup (via `PYTHON_GIL=1` environment variable, or via the `-X gil=1` interpreter flag); `_is_gil_enabled()` reflects the runtime state, `Py_GIL_DISABLED` reflects the build.

For an honest benchmark or correctness check:

```python
import sys
import sysconfig

build_is_freethreaded = sysconfig.get_config_var("Py_GIL_DISABLED") == 1
gil_is_running = sys._is_gil_enabled()
print(f"Build: {'free-threaded' if build_is_freethreaded else 'standard'}")
print(f"Runtime GIL: {'enabled' if gil_is_running else 'disabled'}")
```

A free-threaded build with the GIL re-enabled (via `PYTHON_GIL=1`) is useful for A/B testing: same binary, same Python objects, same C extensions, just toggle the GIL. This is what the mini-project will have you do for the cleanest measurement.

## 4. What changes about your code: a four-bucket analysis

**Bucket 1: pure-Python CPU loops.**

Before (default 3.13):

```python
import threading

def count_primes_up_to(n):
    total = 0
    for k in range(2, n):
        if all(k % d for d in range(2, int(k**0.5) + 1)):
            total += 1
    return total

threads = [threading.Thread(target=count_primes_up_to, args=(50_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
# wall-clock: 4× single-threaded time. GIL serialises the loop.
```

After (3.13t): wall-clock ≈ 1× single-threaded time, on a 4-core box. The threads run in parallel. This is the headline. **Change in your code: zero.** You wrote the same `threading.Thread` you would have written before. The runtime now respects it as a parallelism request.

**Bucket 2: IO-bound code with threads.**

```python
import requests
def fetch(url): return requests.get(url).content

threads = [threading.Thread(target=fetch, args=(u,)) for u in urls]
```

Before and after: behaves the same way. `socket.recv` releases the GIL in the default build; the GIL release is a no-op on 3.13t (because there is no GIL). The wall-clock is approximately the same on both builds. No win, no loss.

**Bucket 3: code that uses C extensions.**

NumPy, pandas, hashlib, json, etc. The behaviour depends on the extension's free-threaded readiness:

- **Extensions marked free-threaded-compatible**: load and run normally on 3.13t. As of early 2026: NumPy (with caveats; some operations are slower because they had to be re-locked), pandas (mostly), `hashlib`, `cryptography`, parts of `lxml`. The ecosystem moves weekly; check `py-free-threading.github.io` for the live status.
- **Extensions not marked free-threaded-compatible**: by default 3.13t will *re-enable* the GIL when such an extension is imported. The interpreter prints a `Py_mod_gil` warning. You will see this in the wild for a year or two yet. The fix is either to use a newer version of the package, or to live with the GIL re-enabled.

`sys._is_gil_enabled()` is dynamic: if you import a non-compatible extension, the call may return `True` even on a 3.13t binary. The mini-project will have you check this before and after `import numpy` on your machine.

**Bucket 4: code with shared mutable state and no locks.**

This is the bucket to worry about. On default CPython, the GIL made *most* shared-state bugs latent — the bytecode was atomic enough that two threads rarely visibly raced on a `counter += 1`. On 3.13t, those races are real.

The good news: PEP 703 introduces *per-object locks* on `dict`, `list`, and `set`. The container's structural invariants are preserved. You cannot crash the interpreter by concurrently writing to a `dict` from two threads. You can, however, lose updates — exactly as on default CPython, just at finer granularity. The fix is unchanged: `threading.Lock`.

**The rule: if your code was correct under the GIL with explicit locks, it is correct under 3.13t.** If it was correct only because of GIL accidents (relying on bytecode atomicity rather than explicit locking), it is now incorrect. The PEP recommends an audit pass; in practice, well-written threading code is fine.

## 5. Biased reference counting, explained for users

PEP 703 §5.1 describes biased reference counting. The two-paragraph user-facing version:

Every Python object has a refcount. On default CPython, every `Py_INCREF` and `Py_DECREF` increments/decrements that counter without atomicity, because the GIL serialises threads. On a free-threaded interpreter without biased refcount, every `Py_INCREF`/`DECREF` would need to be an *atomic* operation — and atomic instructions are 10–50× slower than non-atomic ones. That cost would dominate single-threaded performance.

Biased refcount's trick: an object is *biased* toward its creating thread. While only the creating thread touches the object, refcount updates are non-atomic (fast). When another thread first touches the object, it pays an upfront cost to convert the object to *shared* mode, after which refcount updates on it are atomic. Most objects (locals, frame state, short-lived intermediaries) are touched only by their creating thread; the bias optimises for them. Long-lived shared objects (module globals, class dicts, interned strings) pay the atomic cost but their refcount updates are rare relative to their use.

The result: single-threaded slowdown is ~5–10% in 3.13t initial release (Gross's measurements), with further work ongoing. Multi-threaded scaling on pure-Python code is the headline win.

You will not interact with this directly. The mechanism is entirely under the C API. But it is helpful to know *why* 3.13t is fast enough to be the default eventually: the trick that makes the math work is biased refcount.

## 6. Per-object locks and the immortal-object trick

Two more PEP 703 mechanisms worth being aware of:

**Per-object locks on built-in containers**: `dict`, `list`, and `set` have a small lock embedded in their C struct (one byte; bit-packed). Operations that mutate the container's structure (resize, allocate-new-table) acquire that lock briefly. Operations that read or write a single slot may or may not — the details are in `Objects/dictobject.c` and `Objects/listobject.c`. The point: structural invariants are preserved without language-level locks.

**Immortal objects** (PEP 683, Eric Snow, 2023; companion to PEP 703): some objects (`None`, `True`, `False`, small integers, interned strings, type objects) are marked as never being garbage-collected. Their refcounts are set to a saturated max value, and `Py_INCREF`/`DECREF` skip them. This avoids the per-object-lock and atomic-refcount cost on the most-referenced objects in the interpreter. The free-threaded build relies on immortal objects heavily; the default build benefits too.

**Deferred reference counting** for some long-lived heap objects: module globals and class dicts use a deferred refcount where increments are queued and processed by the GC rather than written immediately. This further reduces atomic contention on shared objects. Implementation details in `Python/gc.c`.

You will not modify any of this. You will, however, see references to these structures when reading the CPython source. Recognise them, move past them; trust the runtime to do the right thing.

## 7. Compatibility hazards in 2026

Three classes of problem you will encounter when running 3.13t in production. None are dealbreakers; all are knowable.

**Hazard A: C extensions that have not been marked compatible.**

The PEP defines a module-init flag `Py_mod_gil` with values `Py_MOD_GIL_USED` (the default for unmarked extensions; re-enables the GIL on import) and `Py_MOD_GIL_NOT_USED` (the extension claims free-threaded compatibility). At import time, the interpreter checks the flag; if unset, the GIL is re-enabled and a warning is printed.

In early 2026, the major libraries (NumPy, pandas, scikit-learn, PyTorch, Pillow, lxml, cryptography) have free-threaded-compatible releases. The long tail of smaller libraries is partial. Check `py-free-threading.github.io` before targeting 3.13t in production.

If you are stuck with an incompatible extension, you have three options: (1) use a compatible alternative; (2) pin to default CPython and use `multiprocessing` for the parallelism; (3) live with the GIL re-enabled on the 3.13t binary (you get the binary's other improvements but no parallelism win).

**Hazard B: latent races.**

```python
# This works fine on default 3.13. Does it work on 3.13t?

class Cache:
    def __init__(self):
        self.store = {}

    def get_or_create(self, key, factory):
        if key not in self.store:
            self.store[key] = factory(key)
        return self.store[key]
```

On default 3.13, the GIL serialises bytecode, so the `if key not in` and the `self.store[key] = ...` happen "close together" — two threads rarely race. On 3.13t, the two operations are truly concurrent on different cores; both threads can see `key not in self.store` and both can call `factory(key)`. If `factory` is idempotent, the only cost is duplicated work; if it has side effects (allocating an external resource, billing an API), the bug is real.

The fix is the same as it always was: `threading.Lock` around the read-modify-write. **The change between default CPython and 3.13t is that the bug becomes easy to hit, not that the bug is new.**

Audit your hot paths for read-modify-write patterns. Use `threading.Lock`, `threading.RLock`, or — better — a higher-level structured primitive like `functools.lru_cache` (which is atomic in 3.13+) or a queue-based coordination.

**Hazard C: single-threaded slowdown.**

3.13t's biased-refcount trick keeps single-threaded slowdown small (5–10% in early measurements) but not zero. If your workload is entirely single-threaded (a CLI script, a request handler that never spawns threads), 3.13t is slower than default 3.13 for the same work.

The implication: **3.13t is not "just better." It is a tradeoff. Single-threaded throughput in exchange for multi-threaded scaling.** Choose per workload, not per organisation. A CLI tool stays on default CPython; a multi-threaded service benefits from 3.13t.

By 3.15 or 3.16, the single-threaded gap is expected to close (Gross's roadmap). At that point, 3.13t-style builds become the practical default and the GIL becomes a legacy compatibility option. We are not there yet in 2026.

## 8. Measuring the win, properly

The benchmark recipe (used in the mini-project and Exercise 1):

```python
# bench.py
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def pure_python_cpu(n):
    total = 0
    for k in range(2, n):
        if all(k % d for d in range(2, int(k**0.5) + 1)):
            total += 1
    return total

def run(workers, n_per_worker):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(pure_python_cpu, [n_per_worker] * workers))
    return time.perf_counter() - t0

if __name__ == "__main__":
    import sys
    print(f"Python: {sys.version.split()[0]}, GIL enabled: {sys._is_gil_enabled()}")
    for w in (1, 2, 4, 8):
        dt = run(w, 10_000)
        print(f"  workers={w}  wall={dt:6.3f}s  per_unit={dt / w:6.3f}s")
```

Run on default 3.13:

```
Python: 3.13.0, GIL enabled: True
  workers=1  wall= 0.21s  per_unit= 0.21s
  workers=2  wall= 0.42s  per_unit= 0.21s
  workers=4  wall= 0.83s  per_unit= 0.21s
  workers=8  wall= 1.67s  per_unit= 0.21s
```

The total wall scales linearly with workers because they serialise. Per-unit time is constant (and equal to the single-worker time).

Run on 3.13t (GIL disabled):

```
Python: 3.13.0, GIL enabled: False
  workers=1  wall= 0.23s  per_unit= 0.23s
  workers=2  wall= 0.24s  per_unit= 0.12s
  workers=4  wall= 0.25s  per_unit= 0.06s
  workers=8  wall= 0.41s  per_unit= 0.05s     # 8 cores saturated, OS noise; per_unit dropping
```

Now the workers parallelise. Per-unit time falls toward 1/N. The single-worker case is slightly slower than default 3.13 (biased-refcount tax). The 8-worker case is ~4× faster wall-clock than default 3.13. Exactly the win PEP 703 promises.

Same exercise on the IO-bound workload (an HTTP fetch with `requests`): the curves are nearly identical between default and free-threaded, because the GIL was already released around the syscall. No change. Lecture 1's GIL-release test predicted this exactly.

## 9. When to reach for 3.13t in 2026

The decision criteria, distilled:

| Workload | Default 3.13 answer | 3.13t consideration |
|----------|---------------------|---------------------|
| Pure-Python CPU, embarrassingly parallel | `ProcessPoolExecutor` | `ThreadPoolExecutor` (lower overhead, no pickle tax) |
| Pure-Python CPU, shared mutable state | `ProcessPoolExecutor` + `shared_memory` | `ThreadPoolExecutor` + explicit locks (much simpler) |
| C-extension CPU (NumPy, hashlib) | `ThreadPoolExecutor` (GIL-releasing) | Same. No real change. |
| IO-bound (network, disk) | `asyncio` or `ThreadPoolExecutor` | Same. No change. |
| Mixed CPU/IO | `ThreadPoolExecutor` or `asyncio` + `run_in_executor` | Same. The CPU phase scales now. |
| Single-threaded CLI | Default 3.13 | Stay on default; 3.13t is slightly slower. |

The bottom line: 3.13t **expands** the set of cases where threads are the right answer; it does not eliminate processes (still useful for fault isolation, GPU contexts, library boundaries) or asyncio (still useful for IO-bound 10K-connection scale). It is one more tool, with a clear "when to use" niche.

## 10. The takeaway

PEP 703 retires a 30-year limitation. The GIL is no longer the answer to "why can't Python do CPU parallelism with threads."

The practitioner-level changes are:

- One new build flavour (`python3.13t`).
- One new runtime API (`sys._is_gil_enabled()`).
- One new build-time API (`sysconfig.get_config_var('Py_GIL_DISABLED')`).
- A small (5–10% and shrinking) tax on single-threaded throughput.
- A class of latent shared-state bugs that are now easier to hit and need explicit locking.
- A C-extension compatibility flag (`Py_mod_gil`) that you will sometimes encounter at import time.

The language semantics are unchanged. The standard library is unchanged. Your code, if it was correct under the GIL with explicit locking, runs unchanged on 3.13t and now scales. If it was implicitly relying on GIL atomicity, audit it and add locks.

The 3.13t story will play out over 3.13 → 3.16 (2024–2027 release window). By the end of that arc, the free-threaded build is the default and the GIL is a legacy compatibility mode. We are in the early-adopter phase in 2026; the mini-project this week is exactly the right exercise to develop a feel for when to reach for it.

---

## Exercises tied to this lecture

- The exercises this week are written to run on *both* default 3.13 and 3.13t. Run them on both if you have both installed. The mini-project is explicit: same code, two builds, two columns in the comparison table.

## Source references

- PEP 703 — Making the GIL Optional in CPython — <https://peps.python.org/pep-0703/>
- PEP 683 — Immortal Objects — <https://peps.python.org/pep-0683/>
- `Doc/howto/free-threading-python.rst` (user HOWTO) — <https://docs.python.org/3/howto/free-threading-python.html>
- `Doc/howto/free-threading-extensions.rst` (C-extension HOWTO) — <https://docs.python.org/3/howto/free-threading-extensions.html>
- `Doc/whatsnew/3.13.rst` (Free-Threaded section) — <https://docs.python.org/3/whatsnew/3.13.html#free-threaded-cpython>
- `Python/sysmodule.c` (`sys._is_gil_enabled`) — <https://github.com/python/cpython/blob/main/Python/sysmodule.c>
- `Include/internal/pycore_runtime.h` (`Py_GIL_DISABLED` macro) — <https://github.com/python/cpython/blob/main/Include/internal/pycore_runtime.h>
- `Objects/dictobject.c` (per-object dict lock) — <https://github.com/python/cpython/blob/main/Objects/dictobject.c>
- `py-free-threading.github.io` (community status tracker) — <https://py-free-threading.github.io/>
