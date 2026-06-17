"""
exercise-02-build_cffi.py - one-time build of the cffi API-mode binding.

Run this script once. It generates a CPython extension module called
`_ex2_cffi` in the current directory:

    _ex2_cffi.cpython-313-darwin.so   (macOS)
    _ex2_cffi.cpython-313-x86_64-linux-gnu.so   (Linux)
    _ex2_cffi.cp313-win_amd64.pyd   (Windows)

The exercise script (exercise-02-cffi-abi-and-api.py) imports this module
and compares its per-call overhead against ctypes and cffi ABI mode.

Reference:
    - https://cffi.readthedocs.io/en/latest/cdef.html#ffi-set-source-preparing-out-of-line-modules
    - https://cffi.readthedocs.io/en/latest/overview.html#abi-versus-api-level
"""

from __future__ import annotations

from cffi import FFI

ffi = FFI()

# The C interface: what Python can call. These declarations are parsed by
# cffi and used to generate the wrapper.
ffi.cdef(
    """
    double sum_squares(const double *buf, size_t n);
    void   scale_inplace(double *buf, size_t n, double factor);
    """
)

# The C source: what the wrapper *is*. cffi places this inside the generated
# .c file, then compiles it into the resulting .so. We inline the kernel
# source here so the build is self-contained (no separate header to chase).
#
# In a real project you would typically `#include "header.h"` and link
# against an external library; here we keep everything in one file so the
# exercise builds with one command.
ffi.set_source(
    "_ex2_cffi",
    """
    #include <stddef.h>

    static double
    sum_squares(const double *buf, size_t n)
    {
        double s = 0.0;
        for (size_t i = 0; i < n; ++i) {
            s += buf[i] * buf[i];
        }
        return s;
    }

    static void
    scale_inplace(double *buf, size_t n, double factor)
    {
        for (size_t i = 0; i < n; ++i) {
            buf[i] *= factor;
        }
    }
    """,
    extra_compile_args=["-O2"],
)

if __name__ == "__main__":
    print("Building _ex2_cffi ...")
    ffi.compile(verbose=True)
    print("Done. Try: python exercise-02-cffi-abi-and-api.py")
