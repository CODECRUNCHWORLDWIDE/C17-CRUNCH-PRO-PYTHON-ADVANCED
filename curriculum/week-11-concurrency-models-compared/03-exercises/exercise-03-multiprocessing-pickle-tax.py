"""Exercise 3 — Measure the pickling tax.

ProcessPoolExecutor crosses a process boundary for every task. Every argument
is pickled before the cross; every result is pickled on the return. The
pickle cost is the "pickling tax." On small-data, small-compute workloads
the tax can wipe out the parallelism gain. On large-data, large-compute
workloads the tax is amortised.

This exercise measures the tax explicitly. Three argument shapes:
    A. scalar int                      (tiny pickle, tiny compute)
    B. 1 MB bytes buffer               (medium pickle, medium compute)
    C. 10_000-element list of dicts    (heavy pickle, medium compute)

For each shape:
    1. Time the pure compute (no IPC).
    2. Time pickle.dumps + pickle.loads of the argument and result.
    3. Time ProcessPoolExecutor(8) end-to-end.
    4. Compute pickle_overhead / total_process_time as a percentage.

The reference output, 8-core 2025 laptop, stock 3.13:

    shape   compute    pickle_rt    process(8)   pickle_% of process
    A       1.0 ms     0.05 ms      ~6 ms        ~10% (overhead dominated)
    B       4.2 ms     2.6 ms       ~8 ms        ~40%
    C       1.1 ms     5.0 ms       ~9 ms        ~70%

The interpretation:
    - Shape A is overhead-dominated: ProcessPoolExecutor is slower than
      serial (~1.0 ms x 64 / 8 = 8 ms minimum without overhead, but spawn
      + queue + 4-pickle-per-task adds another 6+ ms).
    - Shape B is the right shape for multiprocessing: pickle is real but
      compute is bigger, so the model still wins ~3x over serial.
    - Shape C is pickle-dominated: 70% of the wall-clock is moving data
      between processes. The fix: use shared_memory, or chunk batches
      to amortise, or pick a different model.

Cite: PEP 3148 (concurrent.futures),
      pickle docs: https://docs.python.org/3/library/pickle.html
      multiprocessing.shared_memory docs:
      https://docs.python.org/3/library/multiprocessing.shared_memory.html

Run with `python3 exercise-03-multiprocessing-pickle-tax.py`.
Compile-check: `python3 -m py_compile exercise-03-multiprocessing-pickle-tax.py`.
"""

from __future__ import annotations

import hashlib
import pickle
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

ITERATIONS: int = 64
MB: int = 1024 * 1024


# --- Worker functions: must be module-level for pickle to find them. ---


def compute_a(value: int) -> int:
    """Workload A worker: tiny scalar in, tiny scalar out."""
    return sum(i * value for i in range(1000))


def compute_b(buf: bytes) -> bytes:
    """Workload B worker: 1 MB in, 32 bytes out (the SHA digest)."""
    return hashlib.sha256(buf).digest()


def compute_c(records: list[dict[str, Any]]) -> int:
    """Workload C worker: list of dicts in, scalar out."""
    total: int = 0
    for record in records:
        total += len(record.get("value", ""))
    return total


# --- Argument factories. ---


def make_inputs_a() -> list[int]:
    return list(range(1, ITERATIONS + 1))


def make_inputs_b() -> list[bytes]:
    return [bytes((i % 256,) * MB) for i in range(ITERATIONS)]


def make_inputs_c() -> list[list[dict[str, Any]]]:
    return [[{"id": j, "value": "x" * 50} for j in range(10_000)] for _ in range(ITERATIONS)]


# --- Measurement helpers. ---


def time_compute_serial(fn, inputs: list) -> tuple[float, list]:
    start: float = time.perf_counter()
    results: list = [fn(x) for x in inputs]
    return time.perf_counter() - start, results


def time_pickle_roundtrip(arg: Any, result: Any) -> float:
    start: float = time.perf_counter()
    # Two dumps, two loads = one cross-boundary task's pickle cost.
    pickled_arg: bytes = pickle.dumps(arg)
    pickle.loads(pickled_arg)
    pickled_result: bytes = pickle.dumps(result)
    pickle.loads(pickled_result)
    return time.perf_counter() - start


def time_process_pool(fn, inputs: list, max_workers: int = 8) -> float:
    start: float = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(fn, inputs))
    return time.perf_counter() - start


def report(shape: str, fn, inputs: list) -> None:
    compute_time, results = time_compute_serial(fn, inputs)
    # Sample one task for pickle measurement; multiply by N for total cost.
    sample_pickle: float = time_pickle_roundtrip(inputs[0], results[0])
    total_pickle: float = sample_pickle * len(inputs)
    process_time: float = time_process_pool(fn, inputs)
    pickle_pct: float = (total_pickle / process_time) * 100 if process_time > 0 else 0
    print(
        f"  Shape {shape}: compute={compute_time*1000:7.1f}ms  "
        f"pickle_total={total_pickle*1000:7.1f}ms  "
        f"process(8)={process_time*1000:7.1f}ms  "
        f"pickle %={pickle_pct:5.1f}%"
    )


def main() -> None:
    print(f"Iterations: {ITERATIONS}")
    print("Measuring pickling tax for three argument shapes.")
    print()
    print("Shape A: scalar int  (tiny pickle, tiny compute)")
    report("A", compute_a, make_inputs_a())
    print()
    print("Shape B: 1 MB bytes  (medium pickle, medium compute)")
    report("B", compute_b, make_inputs_b())
    print()
    print("Shape C: 10k-dict list  (heavy pickle, medium compute)")
    report("C", compute_c, make_inputs_c())
    print()
    print(
        "Reading the table:"
        "\n  pickle_total >> compute  =>  pickling tax dominates;"
        " ProcessPoolExecutor may be slower than serial."
        "\n  pickle_total << compute  =>  multiprocessing wins;"
        " parallelism amortises the tax."
        "\n  pickle %     > 50%       =>  consider shared_memory, chunksize,"
        " or a different model entirely."
    )


if __name__ == "__main__":
    main()
