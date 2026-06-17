"""Exercise 2 — GIL release audit.

Build the empirical table: which standard-library calls actually release the
GIL? The official answer is "any blocking syscall and any C extension that
chose to drop the GIL." The unofficial answer is "we measure it."

The test methodology:
    1. Run the candidate function N times in serial. Record wall time.
    2. Run the candidate function N times in a ThreadPoolExecutor(8).
       Record wall time.
    3. If thread/serial speedup is > 4x on an 8-core machine, the call
       releases the GIL. If speedup is ~1x, it does not.

This is a black-box test. The white-box test is to read the CPython source
for each module and grep for `Py_BEGIN_ALLOW_THREADS`. Both should agree.

Candidates audited here:
    - hashlib.sha256() over 1 MB           [releases]
    - hashlib.sha256() over 256 bytes      [does NOT release; below threshold]
    - zlib.compress(1 MB)                  [releases]
    - json.loads(64 KB string)             [does NOT release]
    - re.search on a 64 KB string          [does NOT release]
    - time.sleep(0.01)                     [releases]
    - pure Python sum loop                 [does NOT release]

The expected table (8-core, stock 3.13):

    candidate                       serial    threads(8)   speedup   verdict
    sha256(1MB) x 64                ~250 ms   ~ 35 ms      ~7x       RELEASES
    sha256(256B) x 64               ~  1 ms   ~  1 ms      ~1x       holds (small)
    zlib.compress(1MB) x 32         ~600 ms   ~ 85 ms      ~7x       RELEASES
    json.loads(64KB) x 32           ~ 70 ms   ~ 70 ms      ~1x       HOLDS
    re.search(64KB) x 32            ~  4 ms   ~  4 ms      ~1x       HOLDS
    time.sleep(0.01) x 32           ~320 ms   ~ 40 ms      ~8x       RELEASES
    pure Python sum x 32            ~150 ms   ~150 ms      ~1x       HOLDS

The lesson: even C-implemented modules are not GIL-releasing by default. The
extension author had to explicitly add Py_BEGIN_ALLOW_THREADS. The set of
modules that do this is small and well-known.

Cite: PEP 703 (the build where the verdict column becomes irrelevant),
      C-API docs on Py_BEGIN_ALLOW_THREADS:
      https://docs.python.org/3/c-api/init.html#c.Py_BEGIN_ALLOW_THREADS

Run with `python3 exercise-02-gil-release-audit.py`.
Compile-check: `python3 -m py_compile exercise-02-gil-release-audit.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

ITERATIONS_MEDIUM: int = 64
ITERATIONS_SMALL: int = 32
LARGE_BUFFER: bytes = b"\xa5" * (1024 * 1024)
SMALL_BUFFER: bytes = b"\xa5" * 256
JSON_PAYLOAD: str = json.dumps({"records": [{"id": i, "value": "x" * 50} for i in range(200)]})
TEXT_PAYLOAD: str = "lorem ipsum dolor sit amet " * 2000
COMPILED_REGEX: re.Pattern[str] = re.compile(r"lorem ([a-z]+) dolor")


def w_sha256_large(_: int) -> bytes:
    return hashlib.sha256(LARGE_BUFFER).digest()


def w_sha256_small(_: int) -> bytes:
    return hashlib.sha256(SMALL_BUFFER).digest()


def w_zlib_compress(_: int) -> bytes:
    return zlib.compress(LARGE_BUFFER)


def w_json_loads(_: int) -> object:
    return json.loads(JSON_PAYLOAD)


def w_re_search(_: int) -> object:
    return COMPILED_REGEX.search(TEXT_PAYLOAD)


def w_time_sleep(_: int) -> None:
    time.sleep(0.01)


def w_pure_python_sum(_: int) -> int:
    total: int = 0
    for i in range(100_000):
        total += i * i
    return total


def time_serial(fn: Callable[[int], object], n: int) -> float:
    start: float = time.perf_counter()
    for i in range(n):
        fn(i)
    return time.perf_counter() - start


def time_threaded(fn: Callable[[int], object], n: int, max_workers: int = 8) -> float:
    start: float = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(fn, range(n)))
    return time.perf_counter() - start


def report(label: str, fn: Callable[[int], object], n: int) -> None:
    serial: float = time_serial(fn, n)
    threaded: float = time_threaded(fn, n)
    speedup: float = serial / threaded if threaded > 0 else float("inf")
    verdict: str
    if speedup > 4.0:
        verdict = "RELEASES"
    elif speedup > 1.5:
        verdict = "partial (or short)"
    else:
        verdict = "HOLDS"
    print(
        f"  {label:30s} serial={serial*1000:7.2f}ms  threads(8)={threaded*1000:7.2f}ms  "
        f"speedup={speedup:5.2f}x  {verdict}"
    )


def main() -> None:
    import sys

    gil_state: str = "free-threaded (Py_GIL_DISABLED)" if not sys.flags.gil else "stock (GIL on)"
    print(f"Python build: {gil_state}")
    print(f"Iterations: medium={ITERATIONS_MEDIUM}, small={ITERATIONS_SMALL}")
    print()
    print("Candidate                       Result")
    print("-" * 75)
    report("sha256(1MB)", w_sha256_large, ITERATIONS_MEDIUM)
    report("sha256(256B)", w_sha256_small, ITERATIONS_MEDIUM)
    report("zlib.compress(1MB)", w_zlib_compress, ITERATIONS_SMALL)
    report("json.loads(64KB)", w_json_loads, ITERATIONS_SMALL)
    report("re.search(64KB)", w_re_search, ITERATIONS_SMALL)
    report("time.sleep(0.01)", w_time_sleep, ITERATIONS_SMALL)
    report("pure Python sum(100k)", w_pure_python_sum, ITERATIONS_SMALL)
    print()
    print(
        "On the stock build, RELEASES means the C code wraps the work in"
        "\nPy_BEGIN_ALLOW_THREADS. On the free-threaded build, every row"
        "\nthat is pure-Python CPU work also reaches RELEASES, because there"
        "\nis no GIL to release."
    )


if __name__ == "__main__":
    main()
