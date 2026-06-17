# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""
exercise-03-convolve.pyx - the Cython kernel for Exercise 3.

Build:
    cythonize -i exercise-03-convolve.pyx

That command produces (next to this file):
    exercise-03-convolve.c
    exercise-03-convolve.cpython-313-darwin.so  (or .so / .pyd on
                                                  Linux / Windows)

The .so is importable from Python as
    from exercise_03_convolve import convolve_naive, convolve_typed, convolve_fast

(Note: Python munges the filename "exercise-03-convolve" into
"exercise_03_convolve" for the module name. This is also why production
.pyx files use underscores, not hyphens, in their filenames.)

Three implementations side by side:

    convolve_naive - no types. Compiled but still calls Python at every
                     op. ~1.2x faster than pure Python.

    convolve_typed - typed memoryviews. The inner loop is real C.
                     ~150x faster than pure Python.

    convolve_fast  - typed + nogil + (file-level) boundscheck/wraparound
                     off. ~250x faster than pure Python.

Run `cython -a exercise-03-convolve.pyx` to produce
exercise-03-convolve.html. Open it in a browser. The inner loop of
convolve_fast should be white (pure C). The inner loop of convolve_naive
should be yellow (Python calls).

References:
    - https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html
    - https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#compiler-directives
"""

import cython


def convolve_naive(x, h, out):
    """No types. Compiled but still calls Python at every op.

    Provided as a baseline to see what "Cython without types" buys you.
    Spoiler: not much.
    """
    cdef Py_ssize_t n = len(x)
    cdef Py_ssize_t k = len(h)
    cdef Py_ssize_t i, j
    cdef double s
    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s = s + x[i + j] * h[j]
        out[i] = s


def convolve_typed(double[::1] x, double[::1] h, double[::1] out):
    """Typed memoryviews. The inner loop compiles to real C.

    x, h, out must be 1D, C-contiguous, dtype float64.
    out must have length len(x) - len(h) + 1.
    """
    cdef Py_ssize_t n = x.shape[0]
    cdef Py_ssize_t k = h.shape[0]
    cdef Py_ssize_t i, j
    cdef double s

    for i in range(n - k + 1):
        s = 0.0
        for j in range(k):
            s = s + x[i + j] * h[j]
        out[i] = s


def convolve_fast(double[::1] x, double[::1] h, double[::1] out):
    """Typed + nogil. The inner loop runs without the GIL.

    Same shape as convolve_typed but the GIL is released for the kernel
    duration. With the file-level @boundscheck(False) and @wraparound(False)
    directives (set at the top of this .pyx), the inner loop has no
    Python overhead at all.
    """
    cdef Py_ssize_t n = x.shape[0]
    cdef Py_ssize_t k = h.shape[0]
    cdef Py_ssize_t i, j
    cdef double s

    with nogil:
        for i in range(n - k + 1):
            s = 0.0
            for j in range(k):
                s = s + x[i + j] * h[j]
            out[i] = s
