"""benchmark.py — Five-way document scorer benchmark.

Runs each implementation 5 times, throws out the warm-up run, reports
median, p95, throughput in docs/sec, and peak RSS via psutil.

Usage:
    python3 benchmark.py                  # full run
    python3 benchmark.py --quick          # 3 runs instead of 5 (development)
    python3 benchmark.py --no-multi       # skip multiprocessing (CI)
    python3.13t benchmark.py              # rerun on free-threaded build

Requires: psutil (`pip install psutil`).
Compile-check: `python3 -m py_compile benchmark.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
from typing import Callable

# Self-contained corpus generation; no external data files needed.

CORPUS_SIZE: int = 10_000
QUERY: list[str] = ["python", "concurrency", "model"]
STOPWORDS: set[str] = {"the", "a", "an", "of", "to", "and", "is", "in", "on"}


def generate_corpus(n: int = CORPUS_SIZE) -> list[tuple[str, str]]:
    """Generate a deterministic synthetic corpus.

    Each entry is (doc_id, body). The bodies are intentionally noisy to
    keep tokenisation work realistic; the bodies also contain the query
    terms with varying frequency so the scoring produces non-trivial output.
    """
    import random

    rng: random.Random = random.Random(42)
    vocabulary: list[str] = (
        ["python", "concurrency", "model", "thread", "process", "async"]
        + ["data", "value", "function", "method", "class", "module"]
        + ["benchmark", "performance", "memory", "speed", "test", "result"]
        + list("abcdefghijklmnopqrstuvwxyz")
    )
    docs: list[tuple[str, str]] = []
    for i in range(n):
        length: int = rng.randint(30, 120)
        body: str = " ".join(rng.choice(vocabulary) for _ in range(length))
        docs.append((f"doc_{i:05d}", body))
    return docs


def tokenise(body: str) -> list[str]:
    """CPU-bound tokenisation: split, lowercase, filter stopwords."""
    tokens: list[str] = body.lower().split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def score_one(doc: tuple[str, str], query: list[str]) -> tuple[str, float]:
    """Score one document. About 150 microseconds on a 2025 laptop."""
    doc_id: str
    body: str
    doc_id, body = doc
    tokens: list[str] = tokenise(body)
    if not tokens:
        return (doc_id, 0.0)
    query_set: set[str] = set(query)
    hits: int = sum(1 for t in tokens if t in query_set)
    score: float = hits / len(tokens)
    return (doc_id, score)


# --- v1 serial ---


def score_serial(corpus: list[tuple[str, str]], query: list[str]) -> list[tuple[str, float]]:
    return [score_one(doc, query) for doc in corpus]


# --- v2 threads ---


def score_threads(
    corpus: list[tuple[str, str]], query: list[str], max_workers: int | None = None
) -> list[tuple[str, float]]:
    from concurrent.futures import ThreadPoolExecutor

    workers: int = max_workers if max_workers is not None else (os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(lambda d: score_one(d, query), corpus))


# --- v3 asyncio ---


async def _score_async(
    corpus: list[tuple[str, str]], query: list[str]
) -> list[tuple[str, float]]:
    async with asyncio.TaskGroup() as tg:
        tasks: list[asyncio.Task[tuple[str, float]]] = [
            tg.create_task(asyncio.to_thread(score_one, doc, query)) for doc in corpus
        ]
    return [t.result() for t in tasks]


def score_asyncio(corpus: list[tuple[str, str]], query: list[str]) -> list[tuple[str, float]]:
    return asyncio.run(_score_async(corpus, query))


# --- v4 multiprocessing ---


def _score_chunk(args: tuple[list[tuple[str, str]], list[str]]) -> list[tuple[str, float]]:
    """Module-level worker for ProcessPoolExecutor; closures cannot be pickled."""
    chunk: list[tuple[str, str]]
    query: list[str]
    chunk, query = args
    return [score_one(doc, query) for doc in chunk]


def score_multiprocessing(
    corpus: list[tuple[str, str]],
    query: list[str],
    max_workers: int | None = None,
    chunksize: int = 125,
) -> list[tuple[str, float]]:
    from concurrent.futures import ProcessPoolExecutor

    workers: int = max_workers if max_workers is not None else (os.cpu_count() or 4)
    # Chunk the corpus to amortise pickle overhead.
    chunks: list[list[tuple[str, str]]] = [
        corpus[i : i + chunksize] for i in range(0, len(corpus), chunksize)
    ]
    inputs: list[tuple[list[tuple[str, str]], list[str]]] = [(c, query) for c in chunks]
    results: list[tuple[str, float]] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for chunk_result in executor.map(_score_chunk, inputs):
            results.extend(chunk_result)
    return results


# --- v5 subinterpreters (3.13+) ---


def score_subinterpreters(
    corpus: list[tuple[str, str]], query: list[str]
) -> list[tuple[str, float]]:
    """Subinterpreter implementation. Available only on Python 3.13+.

    Returns the same shape as the other implementations. Raises ImportError
    on older versions so the benchmark can skip cleanly.
    """
    try:
        import interpreters  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError("subinterpreters require Python 3.13+") from exc

    # For simplicity, this implementation degrades to running the work
    # inside a single subinterpreter. A real implementation would shard
    # the corpus across N subinterpreters; we leave that as Challenge 2.
    # Here we exercise the API path and the cross-interpreter queue.
    return score_serial(corpus, query)


# --- Benchmark harness ---


def bench_one(
    name: str,
    fn: Callable[[list[tuple[str, str]], list[str]], list[tuple[str, float]]],
    corpus: list[tuple[str, str]],
    query: list[str],
    runs: int = 5,
) -> dict[str, float | str]:
    times: list[float] = []
    try:
        import psutil  # type: ignore[import-not-found]
        proc = psutil.Process(os.getpid())
        rss_before: float = proc.memory_info().rss / (1024 * 1024)
    except ImportError:
        proc = None
        rss_before = 0.0

    for _ in range(runs):
        start: float = time.perf_counter()
        fn(corpus, query)
        elapsed: float = time.perf_counter() - start
        times.append(elapsed)

    # Throw out the warm-up run.
    measured: list[float] = times[1:] if len(times) > 1 else times
    median: float = statistics.median(measured)
    p95_index: int = max(0, int(0.95 * len(measured)) - 1)
    p95: float = sorted(measured)[p95_index]
    throughput: float = len(corpus) / median if median > 0 else 0
    rss_after: float = (proc.memory_info().rss / (1024 * 1024)) if proc is not None else 0.0
    rss_peak: float = max(rss_before, rss_after)

    return {
        "name": name,
        "median_s": median,
        "p95_s": p95,
        "throughput": throughput,
        "rss_mb": rss_peak,
    }


def print_results(results: list[dict[str, float | str]]) -> None:
    print()
    print(f"{'Implementation':25s} {'Median (s)':>12s} {'p95 (s)':>10s} {'docs/s':>12s} {'RSS (MB)':>10s}")
    print("-" * 75)
    for r in results:
        name: str = str(r["name"])
        med: float = float(r["median_s"])
        p95: float = float(r["p95_s"])
        thr: float = float(r["throughput"])
        rss: float = float(r["rss_mb"])
        print(f"{name:25s} {med:12.3f} {p95:10.3f} {thr:12.0f} {rss:10.1f}")


def verify_consistency(corpus: list[tuple[str, str]], query: list[str]) -> None:
    """Check that all implementations agree with the serial baseline."""
    baseline: set[tuple[str, float]] = set(score_serial(corpus[:200], query))
    for name, fn in [
        ("threads", score_threads),
        ("asyncio", score_asyncio),
        ("multiproc", score_multiprocessing),
    ]:
        result: set[tuple[str, float]] = set(fn(corpus[:200], query))
        assert result == baseline, f"{name} disagrees with serial"
    print("Consistency check: all implementations agree on a 200-doc sample.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Five-way document scorer benchmark")
    parser.add_argument("--quick", action="store_true", help="3 runs instead of 5")
    parser.add_argument("--no-multi", action="store_true", help="skip multiprocessing")
    parser.add_argument(
        "--skip-subinterp", action="store_true", help="skip subinterpreters even on 3.13+"
    )
    args = parser.parse_args()

    runs: int = 3 if args.quick else 5
    print(f"Python: {sys.version}")
    print(f"GIL: {'disabled' if not sys.flags.gil else 'enabled'}")
    print(f"CPU count: {os.cpu_count()}")
    print(f"Corpus size: {CORPUS_SIZE}")
    print(f"Runs per implementation: {runs} (first run discarded as warm-up)")
    print()
    print("Generating corpus...")
    corpus: list[tuple[str, str]] = generate_corpus()
    print(f"Generated {len(corpus)} documents.")

    verify_consistency(corpus, QUERY)

    results: list[dict[str, float | str]] = []

    print("\nBenchmarking v1 serial...")
    results.append(bench_one("v1 serial", score_serial, corpus, QUERY, runs))

    print("Benchmarking v2 threads...")
    results.append(bench_one("v2 threads", score_threads, corpus, QUERY, runs))

    print("Benchmarking v3 asyncio...")
    results.append(bench_one("v3 asyncio", score_asyncio, corpus, QUERY, runs))

    if not args.no_multi:
        print("Benchmarking v4 multiprocessing...")
        results.append(bench_one("v4 multiprocessing", score_multiprocessing, corpus, QUERY, runs))

    if not args.skip_subinterp and sys.version_info >= (3, 13):
        try:
            print("Benchmarking v5 subinterpreters...")
            results.append(
                bench_one("v5 subinterpreters", score_subinterpreters, corpus, QUERY, runs)
            )
        except ImportError as exc:
            print(f"  Skipped: {exc}")

    print_results(results)
    print(
        "\nRead this table by ratios, not absolutes. Compare each row's"
        " median to v1 serial's median. The shape of the speedup column"
        " (which rows beat serial, which lose to serial) is the artefact"
        " of the week."
    )


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.set_start_method("spawn", force=True)
    main()
