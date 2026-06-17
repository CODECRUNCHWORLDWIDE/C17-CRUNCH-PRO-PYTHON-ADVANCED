"""
Exercise 3 - Mixed CPU + IO work: thread pool vs. asyncio + run_in_executor

Goal: for a MIXED workload (each task: fetch a URL, then hash the body
with sha256 over a few thousand iterations to amplify the CPU phase),
compare:

  (a) serial: dominated by the sum of IO + CPU phases;
  (b) ThreadPoolExecutor: IO phases overlap freely (GIL released in
      recv); CPU phases overlap because hashlib.sha256().update()
      releases the GIL inside the OpenSSL call;
  (c) asyncio.gather + loop.run_in_executor for the hash: cleanly
      separates the IO phase (run on the event loop) from the CPU
      phase (run in a worker thread);
  (d) ProcessPoolExecutor: parallelises the CPU phase by paying pickle
      cost, but also fetches in workers - the IO phase no longer
      overlaps cleanly because each worker does serial requests.

The expected lesson: ThreadPoolExecutor is the SIMPLEST acceptable
answer for mixed workloads at modest scale (tens of concurrent tasks).
asyncio + run_in_executor is the CLEANER answer when the codebase is
already async. ProcessPoolExecutor is the WRONG answer because
hashlib already releases the GIL, so there's no parallelism benefit
to processes - and pickle adds cost.

Estimated time: 30 minutes.

Run with:   python exercise-03-mixed-with-threadpool.py
Requires:   Python 3.11+ for asyncio.TaskGroup.
            `pip install requests` for blocking fetcher.
            `pip install aiohttp` for the async fetcher.

Acceptance criteria:
- Script runs end-to-end and prints a comparison table.
- The ordering of wall-clock times matches:
      threads ~ asyncio+run_in_executor < processes  <<  serial
- You can articulate WHY a thread pool is the simpler primitive here
  even though asyncio is faster at higher scale.

Reading before / during:
- Lecture 1 section 4 (the executor idioms).
- Lecture 2 section 8 (run_in_executor as the async/blocking bridge).
"""

from __future__ import annotations

import asyncio
import hashlib
import http.server
import socketserver
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Tuple

try:
    import aiohttp  # type: ignore
except ImportError:
    aiohttp = None  # type: ignore

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore


# -----------------------------------------------------------------------------
# Same in-process slow server as Exercise 2. We re-define it here so this
# file is standalone.
# -----------------------------------------------------------------------------

DELAY_SECONDS = 0.05  # 50ms per fetch
HASH_ROUNDS = 5000  # how many times we re-hash the body (amplifies CPU phase)


class SlowHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        time.sleep(DELAY_SECONDS)
        # Return a 4 KB body so the hash has something substantial to chew on.
        body = (b"x" * 4096) + self.path.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server() -> Tuple[ThreadedHTTPServer, int]:
    srv = ThreadedHTTPServer(("127.0.0.1", 0), SlowHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="http-server")
    t.start()
    return srv, port


# -----------------------------------------------------------------------------
# The kernel: a mixed worker that fetches a URL then re-hashes the body
# HASH_ROUNDS times. The re-hash amplifies the CPU phase so it is
# comparable in wall-clock to the IO phase; this makes the contributions
# visible in the benchmark.
# -----------------------------------------------------------------------------


def cpu_hash(body: bytes, rounds: int = HASH_ROUNDS) -> str:
    """Iteratively hash the body. hashlib releases the GIL during .update()."""
    h = hashlib.sha256()
    for _ in range(rounds):
        h.update(body)
    return h.hexdigest()


def fetch_and_hash_blocking(url: str) -> str:
    """Sync version: requests.get + cpu_hash. The whole function is sync."""
    if requests is None:
        raise RuntimeError("requests is not installed; pip install requests")
    r = requests.get(url, timeout=10.0)
    return cpu_hash(r.content)


async def fetch_and_hash_async_inline(session: "aiohttp.ClientSession", url: str) -> str:
    """Async version that does the hash on the event loop. WRONG SHAPE."""
    async with session.get(url) as resp:
        body = await resp.read()
    # Doing the CPU phase on the loop blocks every other coroutine.
    return cpu_hash(body)


async def fetch_and_hash_async_offloaded(
    session: "aiohttp.ClientSession", url: str, pool: ThreadPoolExecutor
) -> str:
    """Async version that offloads the hash to a thread pool. RIGHT SHAPE."""
    async with session.get(url) as resp:
        body = await resp.read()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, cpu_hash, body)


# -----------------------------------------------------------------------------
# Scenario runners.
# -----------------------------------------------------------------------------


def scenario_serial(urls: List[str]) -> float:
    t0 = time.perf_counter()
    for u in urls:
        fetch_and_hash_blocking(u)
    return time.perf_counter() - t0


def scenario_threadpool(urls: List[str], workers: int) -> float:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_and_hash_blocking, urls))
    return time.perf_counter() - t0


def scenario_processpool(urls: List[str], workers: int) -> float:
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_and_hash_blocking, urls))
    return time.perf_counter() - t0


async def scenario_async_inline(urls: List[str]) -> float:
    """asyncio.gather, hash on the loop (the wrong shape, for comparison)."""
    assert aiohttp is not None
    t0 = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(fetch_and_hash_async_inline(session, u) for u in urls))
    return time.perf_counter() - t0


async def scenario_async_offloaded(urls: List[str], workers: int) -> float:
    """asyncio.gather, hash offloaded to a thread pool (the right shape)."""
    assert aiohttp is not None
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(
                *(fetch_and_hash_async_offloaded(session, u, pool) for u in urls)
            )
    return time.perf_counter() - t0


# -----------------------------------------------------------------------------
# Main.
# -----------------------------------------------------------------------------


def main() -> None:
    if requests is None:
        print("ERROR: install requests (pip install requests)", file=sys.stderr)
        sys.exit(1)
    if aiohttp is None:
        print(
            "WARNING: aiohttp not installed; async scenarios will be skipped.",
            file=sys.stderr,
        )

    srv, port = start_server()
    try:
        n_urls = 16
        urls = [f"http://127.0.0.1:{port}/page/{i}" for i in range(n_urls)]

        # Calibrate the relative cost of fetch vs. hash so the reader knows
        # what the mix looks like on their machine.
        body = (b"x" * 4096) + b"/page/calib"
        t0 = time.perf_counter()
        cpu_hash(body)
        hash_one = time.perf_counter() - t0
        print(f"==== Mixed CPU/IO benchmark: {n_urls} (fetch + sha256x{HASH_ROUNDS}) ====")
        print(f"  per-task fetch latency : ~{DELAY_SECONDS:.3f}s")
        print(f"  per-task hash latency  : ~{hash_one:.3f}s")
        print(
            f"  ideal serial total     : ~{n_urls * (DELAY_SECONDS + hash_one):.3f}s"
        )
        print()

        rows: List[Tuple[str, float]] = []
        rows.append(("serial", scenario_serial(urls)))
        rows.append(("threads (4)", scenario_threadpool(urls, 4)))
        rows.append(("threads (8)", scenario_threadpool(urls, 8)))
        rows.append(("threads (16)", scenario_threadpool(urls, 16)))
        if aiohttp is not None:
            rows.append(("asyncio inline hash (wrong shape)", asyncio.run(scenario_async_inline(urls))))
            rows.append(
                ("asyncio + run_in_executor (4)", asyncio.run(scenario_async_offloaded(urls, 4)))
            )
            rows.append(
                ("asyncio + run_in_executor (8)", asyncio.run(scenario_async_offloaded(urls, 8)))
            )
        rows.append(("processes (4)", scenario_processpool(urls, 4)))

        print("  scenario                                       wall-clock")
        print("  " + "-" * 56)
        for label, dt in rows:
            print(f"  {label:<46s}  {dt:8.3f}s")
        print()

        serial_t = rows[0][1]
        print("  speedup vs serial:")
        for label, dt in rows:
            speedup = serial_t / dt if dt > 0 else float("inf")
            print(f"    {label:<46s}  {speedup:5.2f}x")
        print()

    finally:
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        sys.exit(
            "This exercise requires Python 3.11 or newer. "
            f"You are on {sys.version.split()[0]}."
        )
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (default CPython 3.13, 4-core laptop)
# -----------------------------------------------------------------------------
# ==== Mixed CPU/IO benchmark: 16 (fetch + sha256x5000) ====
#   per-task fetch latency : ~0.050s
#   per-task hash latency  : ~0.040s
#   ideal serial total     : ~1.440s
#
#   scenario                                        wall-clock
#   --------------------------------------------------------
#   serial                                              1.45s
#   threads (4)                                         0.52s
#   threads (8)                                         0.36s
#   threads (16)                                        0.32s
#   asyncio inline hash (wrong shape)                   0.71s    <-- the loop is blocked by the hash
#   asyncio + run_in_executor (4)                       0.52s
#   asyncio + run_in_executor (8)                       0.36s
#   processes (4)                                       0.95s    <-- spawn + pickle dominates
#
#   speedup vs serial:
#     serial                                          1.00x
#     threads (4)                                     2.79x
#     threads (8)                                     4.03x
#     threads (16)                                    4.53x      <-- diminishing returns past CPU count
#     asyncio inline hash (wrong shape)               2.04x      <-- limited by hash serialisation on loop
#     asyncio + run_in_executor (4)                   2.79x
#     asyncio + run_in_executor (8)                   4.03x      <-- matches threadpool, by construction
#     processes (4)                                   1.53x      <-- much worse than threads
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. Why is threads(16) only ~12% faster than threads(8) on a 4-core box?
#    Answer: the IO phase scales linearly with workers up to ~the inverse
#    of latency (so ~50ms-worth of fetches per worker per second), but
#    the CPU phase (hashlib) scales linearly only up to the number of
#    cores. Past 4 workers the CPU phase serialises on the cores
#    (the GIL is released, so we're competing for cores not the GIL).
#    threads(8) saturates both axes; threads(16) is wasted threads.
#
# 2. The "asyncio inline hash" row is dramatically worse than the
#    "asyncio + run_in_executor" row. Why? Answer: when the hash runs
#    on the event loop, the loop cannot service other coroutines while
#    cpu_hash is running. The 16 hashes serialise on the single thread.
#    Wall-clock = sum(fetches) overlapping + sum(hashes) serialised.
#    Compare to run_in_executor where hashes parallelise across the
#    thread pool, just like the pure-threads version.
#
# 3. Why is the asyncio + run_in_executor(8) row IDENTICAL to threads(8)?
#    Answer: they ARE the same thing. run_in_executor on the asyncio loop
#    submits the call to a ThreadPoolExecutor. The asyncio side is just
#    orchestration. The actual hashing runs in 8 worker threads either
#    way. The IO side differs slightly (aiohttp uses 1 thread + selector
#    vs. requests in N threads), but for 16 fetches at modest scale that
#    difference is in the noise.
#
# 4. The processes(4) row is the WORST non-serial answer. Why? Two
#    reasons. (a) hashlib.sha256().update() ALREADY releases the GIL -
#    processes buy us nothing here. (b) Every worker has to import
#    requests on spawn (~150ms-200ms per worker, 4 workers = 600-800ms
#    of warm-up). The pickle round-trip per task adds further overhead.
#    The lesson: if your CPU work uses a GIL-releasing C extension,
#    NEVER reach for processes. Cite Modules/_hashopenssl.c for the
#    Py_BEGIN_ALLOW_THREADS / Py_END_ALLOW_THREADS pair around the
#    OpenSSL EVP_DigestUpdate call.
#
# 5. (Stretch) Replace cpu_hash with a PURE-PYTHON CPU kernel (e.g., a
#    Fibonacci loop) that holds the GIL. Re-run. The processes(4) row
#    should now BEAT threads(4) because the GIL is the bottleneck.
#    The threads row will look just like the serial row for the CPU
#    phase, with only the IO phase still benefiting from concurrency.
#    This is the GIL-RELEASE TEST in negative: pure-Python CPU work
#    inverts the conclusion.
#
# 6. (Stretch) Run this exercise on 3.13t (free-threaded). The threads
#    rows should look similar (hashlib already releases the GIL). The
#    asyncio inline hash row improves slightly (the hash thread can
#    overlap with the IO selector thread now), but is still worse than
#    the offloaded version because there's still only one event-loop
#    thread for orchestration.
#
# 7. (Stretch) Read Lib/asyncio/base_events.py:BaseEventLoop.run_in_executor.
#    The function does little more than wrap the executor.submit return
#    value in an asyncio.Future via futures.wrap_future. The asyncio
#    Future then completes when the concurrent.futures Future completes.
#    The bridge is shorter than you might guess.
# -----------------------------------------------------------------------------
