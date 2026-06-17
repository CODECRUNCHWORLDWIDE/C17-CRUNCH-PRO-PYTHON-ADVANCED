/*
 * exercise-01-kernel.c - the C kernel for Exercise 1.
 *
 * Two simple functions:
 *   - sum_squares: sum of x[i]*x[i] over a buffer
 *   - scale_inplace: multiply every element by a constant
 *
 * Style: PEP 7 (https://peps.python.org/pep-0007/).
 *   - K&R braces.
 *   - 4-space indentation, no tabs.
 *   - Function return type on its own line for top-level definitions.
 *   - Max line length ~79 columns.
 *
 * Build (Linux):
 *     gcc -shared -fPIC -O2 -o libk.so exercise-01-kernel.c
 *
 * Build (macOS):
 *     clang -shared -fPIC -O2 -o libk.so exercise-01-kernel.c
 *
 * Build (Windows, MSVC):
 *     cl /LD /O2 exercise-01-kernel.c /Fe:k.dll
 *
 * Verify the symbols:
 *     nm libk.so | grep -E "(sum_squares|scale_inplace)"
 *
 * The exercise script (exercise-01-ctypes-first-binding.py) builds the
 * library by shelling out to gcc if libk.so is not present. You can also
 * build it manually with the line above.
 */

#ifndef EXERCISE_01_KERNEL_INCLUDED
#define EXERCISE_01_KERNEL_INCLUDED

#include <stddef.h>

/*
 * sum_squares - return the sum of x[i]*x[i] for i in the range 0..n-1.
 *
 * Parameters:
 *   buf : pointer to a C-contiguous array of doubles
 *   n   : number of elements
 *
 * Returns:
 *   the scalar sum, as a double
 *
 * Edge cases:
 *   n == 0   -> returns 0.0
 *   buf NULL -> undefined behaviour; caller's responsibility
 */
double
sum_squares(const double *buf, size_t n)
{
    double s = 0.0;
    for (size_t i = 0; i < n; ++i) {
        s += buf[i] * buf[i];
    }
    return s;
}

/*
 * scale_inplace - multiply every element of buf by factor.
 *
 * Parameters:
 *   buf    : pointer to a C-contiguous array of doubles
 *   n      : number of elements
 *   factor : scalar multiplier
 *
 * Returns:
 *   nothing; the buffer is modified in place
 *
 * Edge cases:
 *   n == 0   -> no-op
 *   buf NULL -> undefined behaviour; caller's responsibility
 *   factor 0 -> zeros the buffer (expected)
 *   factor NaN -> propagates NaN to every element (expected)
 */
void
scale_inplace(double *buf, size_t n, double factor)
{
    for (size_t i = 0; i < n; ++i) {
        buf[i] *= factor;
    }
}

#endif /* EXERCISE_01_KERNEL_INCLUDED */
