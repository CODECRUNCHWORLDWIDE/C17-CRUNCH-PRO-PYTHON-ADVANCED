"""
Exercise 2 - cffi in both modes; per-call overhead comparison.

Goal: see, in measured numbers, the per-call overhead of three FFI paths:

    1. ctypes (libffi dispatch, ~1-3 us)
    2. cffi ABI mode (libffi dispatch, similar to ctypes)
    3. cffi API mode (direct CPython-C-API call, ~50-200 ns)

The same kernel is reachable through all three. We measure:

    - Per-call overhead (n=1 call, repeated 1,000,000 times)
    - Bulk throughput (n=1,000,000 elements, single call)

The per-call number is the one that matters. The bulk-throughput number
will be roughly the same for all three; the inner C loop dominates.

Setup:
    1. Build libk.so from exercise-01-kernel.c:
         gcc -shared -fPIC -O2 -o libk.so exercise-01-kernel.c
       (Or: re-run exercise-01-ctypes-first-binding.py once; it builds
       libk.so as a side effect.)

    2. Build the cffi API-mode binding:
         python exercise-02-build_cffi.py
       This creates _ex2_cffi.<...>.so in the current directory.

    3. pip install cffi numpy
         (cffi ships binary wheels; no compiler needed for install.)

    4. Run this script.

Acceptance criteria:

    - Script runs end-to-end on CPython 3.11+.
    - All three FFI paths produce the same answer to within 1e-9.
    - On a small-N test (n=10), cffi API mode is at least 5x faster
      *per call* than ctypes (the per-call overhead gap is the point).
    - On a large-N test (n=1,000,000), all three are within 20% of each
      other (the kernel dominates).
    - The student can articulate why the per-call gap exists.

Estimated time: 60 minutes.

Reading before / during:
    - Lecture 2 sections 4, 5 (cffi ABI vs API mode).
    - https://cffi.readthedocs.io/en/latest/overview.html
    - https://cffi.readthedocs.io/en/latest/cdef.html

References:
    - https://github.com/python-cffi/cffi
    - cryptography's design rationale (cffi over ctypes):
      https://cryptography.io/en/latest/faq/
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from typing import Callable, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(HERE, "libk.so")


# -----------------------------------------------------------------------------
# Path 1: ctypes (same binding as Exercise 1).
# -----------------------------------------------------------------------------


def make_ctypes_binding() -> ctypes.CDLL:
    """Load libk.so via ctypes and set argtypes/restype."""
    if not os.path.exists(LIB_PATH):
        sys.stderr.write(
            f"Missing {LIB_PATH}. Build it with:\n"
            f"    gcc -shared -fPIC -O2 -o {LIB_PATH} "
            f"exercise-01-kernel.c\n"
        )
        sys.exit(1)

    lib = ctypes.CDLL(LIB_PATH)
    lib.sum_squares.restype = ctypes.c_double
    lib.sum_squares.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
        ctypes.c_size_t,
    ]
    return lib


# -----------------------------------------------------------------------------
# Path 2: cffi ABI mode.
# -----------------------------------------------------------------------------


def make_cffi_abi_binding():
    """Build a cffi ABI-mode binding against libk.so."""
    import cffi

    ffi = cffi.FFI()
    ffi.cdef(
        """
        double sum_squares(const double *buf, size_t n);
        void   scale_inplace(double *buf, size_t n, double factor);
        """
    )
    lib = ffi.dlopen(LIB_PATH)
    return ffi, lib


# -----------------------------------------------------------------------------
# Path 3: cffi API mode (built by exercise-02-build_cffi.py).
# -----------------------------------------------------------------------------


def load_cffi_api_binding():
    """Import the API-mode binding built by exercise-02-build_cffi.py."""
    try:
        # The build script generates _ex2_cffi in the current dir.
        sys.path.insert(0, HERE)
        from _ex2_cffi import ffi, lib  # type: ignore[import]
        return ffi, lib
    except ImportError as e:
        sys.stderr.write(
            "Missing _ex2_cffi. Build it with:\n"
            "    python exercise-02-build_cffi.py\n"
            f"(error was: {e})\n"
        )
        sys.exit(1)


# -----------------------------------------------------------------------------
# Adapters: all three return the same function shape (np.ndarray -> float).
# -----------------------------------------------------------------------------


def make_ctypes_caller() -> Callable[[np.ndarray], float]:
    lib = make_ctypes_binding()

    def call(arr: np.ndarray) -> float:
        return float(lib.sum_squares(arr, arr.size))

    return call


def make_cffi_abi_caller() -> Callable[[np.ndarray], float]:
    ffi, lib = make_cffi_abi_binding()

    def call(arr: np.ndarray) -> float:
        ptr = ffi.cast("double *", arr.ctypes.data)
        return float(lib.sum_squares(ptr, arr.size))

    return call


def make_cffi_api_caller() -> Callable[[np.ndarray], float]:
    ffi, lib = load_cffi_api_binding()

    def call(arr: np.ndarray) -> float:
        ptr = ffi.cast("double *", arr.ctypes.data)
        return float(lib.sum_squares(ptr, arr.size))

    return call


# -----------------------------------------------------------------------------
# Measurement.
# -----------------------------------------------------------------------------


def time_per_call(fn: Callable[[np.ndarray], float], arr: np.ndarray,
                  iters: int) -> float:
    """Time `iters` repeated calls to fn(arr). Returns seconds per call."""
    t0 = time.perf_counter()
    for _ in range(iters):
        fn(arr)
    elapsed = time.perf_counter() - t0
    return elapsed / iters


def benchmark_small_n() -> None:
    """n=10 array, 1,000,000 calls. Per-call overhead dominates."""
    print("\n[Per-call overhead] n=10, 1,000,000 calls each")
    print("-" * 60)
    arr = np.random.default_rng(42).random(10)

    callers = {
        "ctypes      ": make_ctypes_caller(),
        "cffi ABI mode": make_cffi_abi_caller(),
        "cffi API mode": make_cffi_api_caller(),
    }

    # Sanity: all three agree on the answer.
    answers = {name: fn(arr) for name, fn in callers.items()}
    ref = list(answers.values())[0]
    for name, val in answers.items():
        if abs(val - ref) > 1e-9:
            raise AssertionError(f"{name} disagrees: {val} vs {ref}")

    results = {}
    for name, fn in callers.items():
        per_call = time_per_call(fn, arr, iters=1_000_000)
        results[name] = per_call
        print(f"  {name} : {per_call * 1e6:6.3f} us/call")

    # Compare API mode to ctypes.
    speedup = results["ctypes      "] / results["cffi API mode"]
    print(f"\n  cffi API vs ctypes: {speedup:.1f}x faster per call")


def benchmark_large_n() -> None:
    """n=1,000,000 array, 5 calls. The inner C loop dominates."""
    print("\n[Bulk throughput] n=1,000,000, 5 calls each, min time")
    print("-" * 60)
    arr = np.random.default_rng(42).random(1_000_000)

    callers = {
        "ctypes      ": make_ctypes_caller(),
        "cffi ABI mode": make_cffi_abi_caller(),
        "cffi API mode": make_cffi_api_caller(),
    }

    for name, fn in callers.items():
        best = float("inf")
        for _ in range(5):
            t0 = time.perf_counter()
            fn(arr)
            elapsed = time.perf_counter() - t0
            if elapsed < best:
                best = elapsed
        print(f"  {name} : {best * 1000:6.3f} ms")

    print(
        "\n  All three should be within ~20% at this N. The C loop is\n"
        "  the cost; per-call overhead is <0.1% of the total."
    )


def main() -> None:
    print("Exercise 2 - cffi ABI vs API mode vs ctypes")
    print("=" * 60)
    benchmark_small_n()
    benchmark_large_n()

    print(
        "\nDone. Open SOLUTIONS.md for the discussion of *why* the per-call\n"
        "numbers are what they are, and what the cryptography project\n"
        "found when they evaluated cffi against ctypes for OpenSSL bindings."
    )


if __name__ == "__main__":
    main()
