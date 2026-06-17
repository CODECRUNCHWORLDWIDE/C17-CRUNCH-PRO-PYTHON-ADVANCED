"""
Exercise 3 - GIL vs. threads

Goal: measure thread scaling under three workload shapes:
  (a) CPU-bound pure Python      - expected: NO speedup under stock GIL.
  (b) IO-bound (time.sleep)      - expected: NEAR-LINEAR speedup, the GIL
                                   is released around the C sleep.
  (c) CPU-bound but NumPy        - expected: speedup (NumPy ufuncs release
                                   the GIL around the C kernel).
                                   This stage is OPTIONAL; if NumPy isn't
                                   installed, the script skips it.

Estimated time: 35 minutes.

Run with:   python exercise-03-GIL-vs-threads.py
            python3.13t exercise-03-GIL-vs-threads.py   # free-threaded build

Acceptance criteria:
- You have run the script on stock CPython 3.13 (or newer) and recorded the
  output as notes/exercise-03-stock.md in your portfolio.
- If you have python3.13t (or python3.14t), you have re-run and recorded
  the output as notes/exercise-03-freethreaded.md.
- You can articulate, with these numbers in hand, why "use threads for IO,
  processes for CPU" is the conventional advice under the GIL build.

References:
- PEP 703 free-threaded build:
  https://peps.python.org/pep-0703/
- Python/ceval_gil.c:
  https://github.com/python/cpython/blob/main/Python/ceval_gil.c
- sys.setswitchinterval:
  https://docs.python.org/3/library/sys.html#sys.setswitchinterval
"""

from __future__ import annotations

import sys
import threading
import time


N_THREADS = 4
CPU_WORK = 20_000_000     # iterations per "burn" call; tune for ~1s on your CPU
IO_SLEEP_SECONDS = 1.0    # per call


# -----------------------------------------------------------------------------
# Workloads
# -----------------------------------------------------------------------------

def cpu_burn(n: int) -> int:
    """Pure Python tight loop. Holds the GIL for its entire run."""
    x = 0
    for _ in range(n):
        x += 1
    return x


def io_block(seconds: float) -> None:
    """time.sleep releases the GIL while waiting (Py_BEGIN_ALLOW_THREADS)."""
    time.sleep(seconds)


def numpy_burn(size: int) -> "any":
    """NumPy ufuncs release the GIL around their C kernel."""
    import numpy as np
    a = np.random.random(size)
    # Several passes so the call dominates over allocation.
    for _ in range(20):
        a = np.sin(a) + np.cos(a)
    return a


# -----------------------------------------------------------------------------
# Timer harness
# -----------------------------------------------------------------------------

def run_serial(fn, args_tuple_list) -> float:
    start = time.perf_counter()
    for args in args_tuple_list:
        fn(*args)
    return time.perf_counter() - start


def run_threaded(fn, args_tuple_list) -> float:
    threads = [threading.Thread(target=fn, args=args) for args in args_tuple_list]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - start


def report(label: str, serial_t: float, threaded_t: float) -> None:
    speedup = serial_t / threaded_t if threaded_t > 0 else float("inf")
    print(f"  {label:<30}  serial={serial_t:6.2f}s  threaded={threaded_t:6.2f}s"
          f"   speedup={speedup:4.2f}x")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    print(f"Python: {sys.version.split()[0]}")
    # Is this a free-threaded build?
    gil_status = "with GIL"
    try:
        # sys._is_gil_enabled() exists in 3.13+; True when the GIL is on.
        if hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled():
            gil_status = "FREE-THREADED (GIL disabled)"
    except Exception:
        pass
    print(f"Mode:   {gil_status}")
    print(f"Threads per test: {N_THREADS}")
    print()

    # ---- CPU-bound ----
    print("CPU-bound (pure Python tight loop):")
    args = [(CPU_WORK,)] * N_THREADS
    serial = run_serial(cpu_burn, args)
    threaded = run_threaded(cpu_burn, args)
    report("cpu_burn", serial, threaded)
    # Under the GIL: expect threaded ~= serial (no speedup).
    # Under PEP 703 free-threaded: expect threaded ~= serial / N_THREADS.
    print()

    # ---- IO-bound ----
    print("IO-bound (time.sleep):")
    args = [(IO_SLEEP_SECONDS,)] * N_THREADS
    serial = run_serial(io_block, args)
    threaded = run_threaded(io_block, args)
    report("io_block (sleep)", serial, threaded)
    # Both builds: expect threaded ~= IO_SLEEP_SECONDS (N-way parallelism).
    print()

    # ---- NumPy (if available) ----
    try:
        import numpy as np  # noqa: F401
        print("NumPy ufunc (C kernel, GIL released around the work):")
        args = [(2_000_000,)] * N_THREADS
        serial = run_serial(numpy_burn, args)
        threaded = run_threaded(numpy_burn, args)
        report("numpy_burn", serial, threaded)
        # GIL build: substantial speedup because the ufunc releases the GIL.
        # Free-threaded build: similar speedup, slightly less overhead.
        print()
    except ImportError:
        print("NumPy not installed; skipping numpy_burn test.")
        print()

    print("Interpretation:")
    print(" - If 'cpu_burn speedup' is ~1.0x, you are on a stock GIL build.")
    print(" - If 'cpu_burn speedup' is ~", N_THREADS, "x, you are on a free-threaded build.")
    print(" - 'io_block speedup' should be ~", N_THREADS, "x on either build.")
    print(" - 'numpy_burn speedup' should be substantial on either build,")
    print("   because NumPy releases the GIL around its C kernels.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (approximate; numbers vary)
# -----------------------------------------------------------------------------
# === Stock CPython 3.13 (with GIL) ===
# CPU-bound:    serial=3.80s  threaded=3.95s  speedup=0.96x
# IO-bound:     serial=4.00s  threaded=1.01s  speedup=3.96x
# NumPy:        serial=2.40s  threaded=0.78s  speedup=3.08x
#
# === python3.13t (free-threaded build) ===
# CPU-bound:    serial=4.20s  threaded=1.12s  speedup=3.75x
# IO-bound:     serial=4.00s  threaded=1.01s  speedup=3.96x
# NumPy:        serial=2.65s  threaded=0.80s  speedup=3.31x
#
# The headline result: on the free-threaded build, the CPU-bound speedup
# matches the IO-bound speedup. Under the stock GIL, only IO and
# GIL-releasing C extensions scale.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Why does the CPU-bound *threaded* time sometimes come out very slightly
#    HIGHER than the serial time on the GIL build?
#    Answer: GIL hand-off has measurable overhead (a condition-variable wait
#    plus a few system calls per ~5ms switch). With one thread, no hand-offs
#    happen.
#
# 2. What is the effect of `sys.setswitchinterval(0.0001)` on the CPU-bound
#    test? Try it. (Hint: more frequent GIL hand-offs => more overhead =>
#    sometimes worse, never better, on this workload.)
#
# 3. If you reduce CPU_WORK from 20_000_000 to 200, do the IO-bound numbers
#    change? Why or why not?
#    Answer: no, IO blocks in the kernel, not in the eval loop; CPU_WORK
#    has no influence on the io_block test.
#
# 4. Why is the NumPy "speedup" usually less than N_THREADS even on the
#    GIL build?
#    Answer: cache pressure and memory-bandwidth saturation. Vectorized
#    work is often memory-bound on a modern CPU, so multiple cores compete
#    for the same memory channels rather than for the GIL.
#
# 5. (Stretch) Build CPython from source with `./configure --disable-gil`
#    (instructions at https://github.com/python/cpython/blob/main/Doc/howto/free-threading-python.rst)
#    and re-run. Commit both outputs.
# -----------------------------------------------------------------------------
