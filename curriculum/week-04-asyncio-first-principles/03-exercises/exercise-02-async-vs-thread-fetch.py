"""
Exercise 2 - asyncio fan-out vs. ThreadPoolExecutor fan-out

Goal: stand up a tiny local HTTP server, fire 200 concurrent fetches against
      it two ways - asyncio + a coroutine pool, and ThreadPoolExecutor +
      stdlib urllib - then compare wall-clock, peak resident memory, and
      per-request latency distribution. The answer is large and worth seeing.

This exercise needs no external network and no third-party packages: we
ship our own one-screen HTTP server in a thread and hit it with raw socket
I/O from asyncio. If you have `aiohttp` installed it will use that; otherwise
it falls back to the stdlib `urllib` + `loop.run_in_executor` bridge.

Estimated time: 60 minutes.

Run with:   python exercise-02-async-vs-thread-fetch.py
Requires:   Python 3.11+  (asyncio.TaskGroup, asyncio.timeout).
            Optional: pip install aiohttp  (for the "pure async" path).

Acceptance criteria:
- Script runs without modification, prints a comparison table.
- asyncio fan-out wall-clock < ThreadPool wall-clock at concurrency >= 100.
- asyncio peak memory < ThreadPool peak memory by at least 2x.
- You can articulate the cost model: threads cost ~8MB stack each; coroutines
  cost ~few-KB-each (one Task + one Future + one coroutine frame).

Reading before / during:
- asyncio task and coroutine API:
  https://docs.python.org/3/library/asyncio-task.html
- concurrent.futures.ThreadPoolExecutor:
  https://docs.python.org/3/library/concurrent.futures.html
- aiohttp client docs (optional):
  https://docs.aiohttp.org/en/stable/client_quickstart.html
"""

from __future__ import annotations

import asyncio
import http.server
import socketserver
import statistics
import threading
import time
import tracemalloc
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple


# -----------------------------------------------------------------------------
# A tiny HTTP server, in a thread, that introduces a fixed per-request delay.
#
# The delay simulates a slow upstream: this is the IO-bound case where both
# threads and asyncio can shine. The point: the wait is on the network, not
# on the CPU; there's no CPU-vs-thread contention.
# -----------------------------------------------------------------------------

REQUEST_DELAY_S = 0.05      # 50ms per request - simulated upstream latency
N_REQUESTS = 200            # fan-out width
PORT = 0                    # let the OS pick


class SlowHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        time.sleep(REQUEST_DELAY_S)
        body = b'{"ok": true}\n'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Silence the per-request log; we'll print our own summary.
        return


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server() -> Tuple[ThreadingServer, str]:
    server = ThreadingServer(("127.0.0.1", PORT), SlowHandler)
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, url


# -----------------------------------------------------------------------------
# Path A: ThreadPoolExecutor + urllib (the classic "make it concurrent" recipe).
#
# This is what most senior engineers wrote before 2018. It works, it's simple,
# and it costs you ~8MB of OS thread stack per worker. At N=200 workers that
# is 1.6 GB of virtual address space (lazy-paged; not all resident, but real).
# -----------------------------------------------------------------------------

def fetch_sync(url: str) -> Tuple[int, float]:
    t0 = time.perf_counter()
    with urllib.request.urlopen(url, timeout=5.0) as resp:
        _ = resp.read()
        elapsed = time.perf_counter() - t0
        return resp.status, elapsed


def run_threaded(url: str, n: int, max_workers: int) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    latencies: List[float] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_sync, url) for _ in range(n)]
        for fut in futures:
            status, latency = fut.result()
            assert status == 200, f"unexpected status {status}"
            latencies.append(latency)
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return _summarize("threaded", wall, peak, latencies, max_workers)


# -----------------------------------------------------------------------------
# Path B: asyncio + aiohttp (or asyncio + run_in_executor as fallback).
#
# The pure-async path is what you write today. Each fetch is a coroutine,
# the coroutines all share one thread, the OS sees one socket per pending
# request and one thread running the loop. Memory: a few KB per task.
# -----------------------------------------------------------------------------

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


async def fetch_aiohttp(session, url: str) -> Tuple[int, float]:
    t0 = time.perf_counter()
    async with session.get(url) as resp:
        await resp.read()
        return resp.status, time.perf_counter() - t0


async def run_aiohttp(url: str, n: int) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    latencies: List[float] = []
    async with aiohttp.ClientSession() as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_aiohttp(session, url)) for _ in range(n)]
        for t in tasks:
            status, latency = t.result()
            assert status == 200
            latencies.append(latency)
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return _summarize("asyncio+aiohttp", wall, peak, latencies, n)


# Fallback: asyncio drives urllib via run_in_executor. Not "pure async" - it's
# really a thread pool wearing an async face. Included so the exercise runs on
# any stock Python. Compare the wall-clock to the threaded path; they should
# be similar (because they ARE essentially the same).

async def fetch_via_executor(url: str) -> Tuple[int, float]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_sync, url)


async def run_executor_bridge(url: str, n: int) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    latencies: List[float] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_via_executor(url)) for _ in range(n)]
    for t in tasks:
        status, latency = t.result()
        assert status == 200
        latencies.append(latency)
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return _summarize("asyncio+executor-bridge", wall, peak, latencies, n)


# -----------------------------------------------------------------------------
# Pretty stats.
# -----------------------------------------------------------------------------

def _summarize(
    label: str, wall: float, peak_bytes: int, latencies: List[float], workers: int
) -> dict:
    return {
        "label": label,
        "wall_s": wall,
        "peak_kib": peak_bytes / 1024.0,
        "workers": workers,
        "n_ok": len(latencies),
        "p50": statistics.median(latencies),
        "p95": _percentile(latencies, 0.95),
        "p99": _percentile(latencies, 0.99),
        "min": min(latencies),
        "max": max(latencies),
    }


def _percentile(xs: List[float], q: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(q * len(xs))))
    return xs[k]


def _print_table(rows: List[dict]) -> None:
    cols = ["label", "wall_s", "peak_kib", "workers", "n_ok", "p50", "p95", "p99"]
    widths = {c: max(len(c), max(len(_fmt(r[c])) for r in rows)) for c in cols}
    header = "  ".join(f"{c:>{widths[c]}}" for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(f"{_fmt(r[c]):>{widths[c]}}" for c in cols))


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


# -----------------------------------------------------------------------------
# Main: run the three paths, print a table, draw conclusions.
# -----------------------------------------------------------------------------

def main() -> None:
    server, url = start_server()
    print(f"local server: {url}")
    print(f"per-request server-side delay: {REQUEST_DELAY_S * 1000:.0f}ms")
    print(f"fan-out: {N_REQUESTS}")
    print()

    rows: List[dict] = []

    # Path A: warm-up the server with a single request (avoid first-request
    # cost noise in the comparison).
    fetch_sync(url)

    # Path A: thread pool at N=200 workers. Ambitious; some systems will
    # refuse to create that many threads, in which case bump max_workers
    # down. We will test 32, 64, and 200 to see the scaling.
    for w in (32, 64, 200):
        try:
            rows.append(run_threaded(url, N_REQUESTS, max_workers=w))
        except RuntimeError as e:
            # ThreadPoolExecutor raises if we cannot create that many threads.
            print(f"  threaded w={w}: skipped ({e})")

    # Path B: asyncio.
    if HAS_AIOHTTP:
        rows.append(asyncio.run(run_aiohttp(url, N_REQUESTS)))
    else:
        print("  (aiohttp not installed; skipping the pure-async path)")
    rows.append(asyncio.run(run_executor_bridge(url, N_REQUESTS)))

    print()
    _print_table(rows)
    print()

    # The shape of the result that should hold across machines:
    # 1. threaded(32) and threaded(64) take ~max(0.05, n/w) wall-clock.
    # 2. threaded(200) is faster but uses much more peak memory (>>1MB).
    # 3. asyncio+aiohttp is fastest (~0.05-0.1s for n=200) at low memory.
    # 4. asyncio+executor-bridge is essentially threaded(200) in disguise.

    print("Observations to write down in your portfolio:")
    print("  - At what worker count does threaded match asyncio on wall-clock?")
    print("  - What is the memory ratio at N=200?")
    print("  - Why is `executor-bridge` not faster than the threaded path?")
    print("  - At what N does the threaded path stop scaling (OS thread cap)?")
    print()

    server.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# EXPECTED-SHAPE OUTPUT (numbers vary by machine; the shape is the lesson)
# -----------------------------------------------------------------------------
# local server: http://127.0.0.1:53921/
# per-request server-side delay: 50ms
# fan-out: 200
#
#                  label  wall_s  peak_kib  workers  n_ok    p50    p95    p99
# -----------------------------------------------------------------------------
#               threaded   0.385    115.3       32   200  0.054  0.060  0.065
#               threaded   0.205    225.0       64   200  0.053  0.058  0.062
#               threaded   0.105    689.7      200   200  0.060  0.072  0.080
#       asyncio+aiohttp    0.072     45.1      200   200  0.061  0.069  0.073
#  asyncio+executor-bridge 0.115    712.5      200   200  0.060  0.073  0.079
#
# Read this carefully:
# - threaded(32): wall = 200 / 32 * 0.05 = 0.31s, with overhead -> 0.39s. Right.
# - threaded(200): one thread per request, near-perfect parallelism on I/O.
#   But peak_kib of 689 is the tracemalloc-traced part - the *actual* OS
#   thread stack cost is ~1.6 GB virtual on Linux (8MB * 200).
# - asyncio+aiohttp: same wall-clock; 1/15th the traced memory; one OS thread.
# - asyncio+executor-bridge: indistinguishable from threaded(200) because that
#   is what it IS underneath - one thread per ongoing run_in_executor call.
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. The tracemalloc number is *small* compared to the OS-thread reality.
#    Why? tracemalloc only counts Python heap allocations made by the
#    profiled process from inside Python code. OS thread stacks (8MB each
#    by default on Linux x86_64) and kernel data structures (one task_struct
#    per thread) are invisible to it. The honest accounting requires
#    /proc/PID/status RSS reads, OR ulimit observations.
#
# 2. At what fan-out does threaded "break"? On a typical Linux laptop,
#    around N=4000-8000 threads you hit /proc/sys/kernel/threads-max or
#    `ulimit -u`. asyncio on the same machine handles 100,000+ tasks. The
#    asymmetry is the entire reason asyncio exists at scale.
#
# 3. Why doesn't asyncio just use threads internally? Because the asyncio
#    promise is "one OS thread, N user-space tasks, scheduled cooperatively
#    on I/O readiness." Once you fork to a thread, you've left that model.
#    `run_in_executor` is the deliberate escape hatch *to* threads for
#    blocking work; it is not the default.
#
# 4. (Stretch) Replace tracemalloc with the `resource` module's
#    getrusage(RUSAGE_SELF).ru_maxrss for a true peak-RSS comparison.
#    The asymmetry is much starker.
#
# 5. (Stretch) Raise N_REQUESTS to 1000. Does asyncio still hold? At what
#    point does the Linux file-descriptor limit (ulimit -n) bite?
# -----------------------------------------------------------------------------
