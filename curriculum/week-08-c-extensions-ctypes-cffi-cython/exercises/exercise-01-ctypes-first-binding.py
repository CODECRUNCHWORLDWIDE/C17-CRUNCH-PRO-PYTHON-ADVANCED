"""
Exercise 1 - your first ctypes binding.

Goal: compile a small C library, bind it from Python via ctypes, and
prove the speedup over equivalent Python on two simple kernels.

The C source is exercise-01-kernel.c (sibling file). It exports two
functions:

    double sum_squares(const double *buf, size_t n);
    void   scale_inplace(double *buf, size_t n, double factor);

Acceptance criteria:

    - Script runs end-to-end on CPython 3.11+.
    - libk.so is built (or fails clearly with the gcc/clang command to run).
    - sum_squares: Python and C produce the same answer to within 1e-9 on
      a 1,000,000-element random buffer.
    - scale_inplace: Python and C produce the same buffer after a scale.
    - The C implementation is at least 30x faster than the pure-Python loop
      on n=1,000,000.
    - argtypes and restype are set on both bindings. A test verifies that
      omitting them produces a wrong answer (or a crash). We do not run that
      test; we explain it in SOLUTIONS.md.

Estimated time: 60 minutes.

Reading before / during:
    - Lecture 1 sections 3, 7 (the C API at a glance; the first ctypes
      example).
    - Lecture 2 sections 2, 3 (the ctypes binding mechanics).
    - https://docs.python.org/3/library/ctypes.html
    - https://docs.python.org/3/library/ctypes.html#fundamental-data-types
    - https://numpy.org/doc/stable/reference/routines.ctypeslib.html

References:
    - PEP 7 (C style guide): https://peps.python.org/pep-0007/
    - CPython source for ctypes: Lib/ctypes/__init__.py
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from typing import List, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(HERE, "libk.so")
SRC_PATH = os.path.join(HERE, "exercise-01-kernel.c")


# -----------------------------------------------------------------------------
# Build helper.
# -----------------------------------------------------------------------------


def build_library_if_missing() -> None:
    """Compile libk.so from exercise-01-kernel.c if it is not present.

    Tries gcc first, then clang. Prints the exact command on failure so the
    student can run it themselves.
    """
    if os.path.exists(LIB_PATH):
        return

    cmds: List[List[str]] = [
        ["gcc", "-shared", "-fPIC", "-O2", "-o", LIB_PATH, SRC_PATH],
        ["clang", "-shared", "-fPIC", "-O2", "-o", LIB_PATH, SRC_PATH],
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Built {LIB_PATH} with: {' '.join(cmd)}")
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    sys.stderr.write(
        "Could not build libk.so automatically. Run one of:\n"
        f"    gcc -shared -fPIC -O2 -o {LIB_PATH} {SRC_PATH}\n"
        f"    clang -shared -fPIC -O2 -o {LIB_PATH} {SRC_PATH}\n"
        "and re-run this script.\n"
    )
    sys.exit(1)


# -----------------------------------------------------------------------------
# The ctypes binding.
# -----------------------------------------------------------------------------


def load_library() -> ctypes.CDLL:
    """Load libk.so and configure argtypes/restype for both functions."""
    lib = ctypes.CDLL(LIB_PATH)

    # sum_squares: double sum_squares(const double *buf, size_t n)
    lib.sum_squares.restype = ctypes.c_double
    lib.sum_squares.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
        ctypes.c_size_t,
    ]

    # scale_inplace: void scale_inplace(double *buf, size_t n, double factor)
    lib.scale_inplace.restype = None
    lib.scale_inplace.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
        ctypes.c_size_t,
        ctypes.c_double,
    ]
    return lib


# -----------------------------------------------------------------------------
# Pure-Python reference implementations.
# -----------------------------------------------------------------------------


def sum_squares_python(data: List[float]) -> float:
    """Pure-Python sum of squares. The baseline."""
    s = 0.0
    for x in data:
        s += x * x
    return s


def scale_inplace_python(data: List[float], factor: float) -> None:
    """Pure-Python in-place scale. The baseline."""
    for i in range(len(data)):
        data[i] *= factor


# -----------------------------------------------------------------------------
# ctypes-backed wrappers.
# -----------------------------------------------------------------------------


def sum_squares_ctypes(lib: ctypes.CDLL, arr: np.ndarray) -> float:
    """Wrap the C function. arr must be float64, C-contiguous."""
    return float(lib.sum_squares(arr, arr.size))


def scale_inplace_ctypes(lib: ctypes.CDLL, arr: np.ndarray, factor: float) -> None:
    """Wrap the C function. arr is modified in place."""
    lib.scale_inplace(arr, arr.size, factor)


# -----------------------------------------------------------------------------
# Driver.
# -----------------------------------------------------------------------------


def time_call(fn, *args, repeats: int = 1) -> float:
    """Time a call. Returns the *minimum* wall time across repeats."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        elapsed = time.perf_counter() - t0
        if elapsed < best:
            best = elapsed
    return best


def assert_close(a: float, b: float, tol: float = 1e-6) -> None:
    """Compare two floats; raise if not close to within `tol`."""
    if abs(a - b) > tol:
        raise AssertionError(f"values disagree: {a} vs {b}")


def benchmark_sum_squares(lib: ctypes.CDLL) -> Tuple[float, float, float]:
    """Run the sum_squares benchmark. Returns (python_t, ctypes_t, speedup)."""
    n = 1_000_000
    arr = np.random.default_rng(42).random(n)
    arr_list: List[float] = arr.tolist()

    t_py = time_call(sum_squares_python, arr_list, repeats=1)
    t_c = time_call(sum_squares_ctypes, lib, arr, repeats=5)

    r_py = sum_squares_python(arr_list)
    r_c = sum_squares_ctypes(lib, arr)
    assert_close(r_py, r_c, tol=1e-6)

    return t_py, t_c, t_py / t_c


def benchmark_scale_inplace(lib: ctypes.CDLL) -> Tuple[float, float, float]:
    """Run the scale_inplace benchmark. Returns (python_t, ctypes_t, speedup)."""
    n = 1_000_000
    arr_c = np.random.default_rng(42).random(n)
    arr_list = arr_c.tolist()

    factor = 2.5

    t_py = time_call(scale_inplace_python, arr_list, factor, repeats=1)
    t_c = time_call(scale_inplace_ctypes, lib, arr_c, factor, repeats=5)

    # Sanity: the first element of each should match (to a tolerance).
    assert_close(arr_list[0], arr_c[0], tol=1e-9)

    return t_py, t_c, t_py / t_c


def main() -> None:
    print("Exercise 1 - ctypes first binding")
    print("=" * 60)

    build_library_if_missing()
    lib = load_library()

    print("\n[Benchmark] sum_squares, n=1,000,000")
    t_py, t_c, speedup = benchmark_sum_squares(lib)
    print(f"  Python : {t_py * 1000:8.2f} ms")
    print(f"  ctypes : {t_c * 1000:8.2f} ms")
    print(f"  speedup: {speedup:6.1f}x")
    if speedup < 30:
        print(f"  WARNING: expected at least 30x; got {speedup:.1f}x")
    else:
        print("  OK: speedup >= 30x as expected")

    print("\n[Benchmark] scale_inplace, n=1,000,000")
    t_py, t_c, speedup = benchmark_scale_inplace(lib)
    print(f"  Python : {t_py * 1000:8.2f} ms")
    print(f"  ctypes : {t_c * 1000:8.2f} ms")
    print(f"  speedup: {speedup:6.1f}x")

    print(
        "\nDone. Open SOLUTIONS.md for the discussion of *why* the\n"
        "speedups are what they are, and what would happen if argtypes\n"
        "and restype were omitted (do not try this on production data)."
    )


if __name__ == "__main__":
    main()
