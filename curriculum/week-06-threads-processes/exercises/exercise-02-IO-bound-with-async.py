"""
Exercise 2 - IO-bound work: async vs. thread pool vs. process pool

Goal: prove in code that for an IO-BOUND workload (N HTTP fetches against
a local server with a built-in artificial delay):

  (a) serial is dramatically slow - wall-clock = N * latency;
  (b) asyncio.gather is the fastest and uses ONE OS thread - wall-clock
      approaches max(latencies), and memory/process count is bounded;
  (c) ThreadPoolExecutor(max_workers=N) is COMPETITIVE with asyncio for
      modest N (typical: 50-200 within 20-50% of the async wall-clock),
      because requests releases the GIL inside the socket recv;
  (d) ProcessPoolExecutor is dramatically WORSE - the GIL was already
      released around the IO, so processes buy nothing, and the pickle
      cost and process-spawn cost dominate.

We do NOT hit the public internet. The exercise ships a tiny in-process
HTTP server (stdlib http.server) that artificially sleeps `delay`
seconds before responding to each request. This makes the timing
predictable and offline-friendly.

Estimated time: 45 minutes.

Run with:   python exercise-02-IO-bound-with-async.py
Requires:   Python 3.11+ (asyncio.TaskGroup not strictly required here;
            we use asyncio.gather to keep the example narrow).
            `pip install aiohttp` for the asyncio fetcher.
            `pip install requests` for the blocking fetcher.

Acceptance criteria:
- Script runs end-to-end and prints a comparison table.
- The ordering of wall-clock times matches:
      asyncio.gather    <  ThreadPoolExecutor    <<  serial
      ProcessPoolExecutor                        >> all the others
- You can articulate WHY the thread pool is competitive (the GIL is
  released inside the recv() syscall) and WHY the process pool is bad
  (no GIL benefit; pickle + spawn overhead added).

Reading before / during:
- Lecture 1 sections 3 (the GIL-release test) and 6 (cost model).
- Lecture 2 section 6 (the five failure modes; the process-pool tax).
- Lecture 3 section 9 (when to reach for 3.13t; IO is unchanged).
"""

from __future__ import annotations

import asyncio
import http.server
import socketserver
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
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
# An in-process HTTP server that artificially sleeps `DELAY_SECONDS` before
# responding. This emulates a slow remote service with predictable latency.
# We run it on a background thread so the main program can make requests
# against it.
# -----------------------------------------------------------------------------

DELAY_SECONDS = 0.10  # 100 ms per request


class SlowHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        time.sleep(DELAY_SECONDS)
        body = f"hello from {self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        # silence the default request log
        return


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_server() -> Tuple[ThreadedHTTPServer, int]:
    """Bind to a free port; run the server in a daemon thread; return both."""
    srv = ThreadedHTTPServer(("127.0.0.1", 0), SlowHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="http-server")
    t.start()
    return srv, port


# -----------------------------------------------------------------------------
# Fetchers. Each takes a URL and returns the body length. We standardise on
# "fetch and discard body, return length" so we can compare apples to apples
# without paying for body parsing.
# -----------------------------------------------------------------------------


def fetch_blocking(url: str) -> int:
    """Blocking fetch via `requests`. The GIL is released inside recv()."""
    if requests is None:
        raise RuntimeError("requests is not installed; pip install requests")
    r = requests.get(url, timeout=10.0)
    return len(r.content)


async def fetch_async(session: "aiohttp.ClientSession", url: str) -> int:
    """Async fetch via aiohttp. Yields the loop during the IO wait."""
    async with session.get(url) as resp:
        body = await resp.read()
        return len(body)


# -----------------------------------------------------------------------------
# Scenario runners. Each runs N fetches and returns the wall-clock seconds.
# -----------------------------------------------------------------------------


def scenario_serial(urls: List[str]) -> float:
    t0 = time.perf_counter()
    for u in urls:
        fetch_blocking(u)
    return time.perf_counter() - t0


def scenario_threadpool(urls: List[str], workers: int) -> float:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_blocking, urls))
    return time.perf_counter() - t0


def scenario_processpool(urls: List[str], workers: int) -> float:
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch_blocking, urls))
    return time.perf_counter() - t0


async def scenario_async(urls: List[str]) -> float:
    assert aiohttp is not None, "aiohttp not installed"
    t0 = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(fetch_async(session, u) for u in urls))
    return time.perf_counter() - t0


# -----------------------------------------------------------------------------
# Main driver. Starts the server, generates URLs, runs each scenario, prints
# a comparison table.
# -----------------------------------------------------------------------------


def main() -> None:
    if aiohttp is None:
        print(
            "WARNING: aiohttp is not installed. The async scenario will be skipped.\n"
            "Install with: pip install aiohttp",
            file=sys.stderr,
        )
    if requests is None:
        print(
            "ERROR: requests is not installed. Install with: pip install requests",
            file=sys.stderr,
        )
        sys.exit(1)

    srv, port = start_server()
    try:
        n_urls = 32
        urls = [f"http://127.0.0.1:{port}/page/{i}" for i in range(n_urls)]
        ideal_serial_seconds = n_urls * DELAY_SECONDS
        ideal_concurrent_seconds = DELAY_SECONDS  # if perfectly overlapped

        print(f"==== IO-bound benchmark: {n_urls} fetches, {DELAY_SECONDS:.2f}s each ====")
        print(f"  ideal serial wall-clock      = {ideal_serial_seconds:.2f}s")
        print(f"  ideal concurrent wall-clock  = {ideal_concurrent_seconds:.2f}s")
        print()

        rows: List[Tuple[str, float]] = []

        rows.append(("serial (requests)", scenario_serial(urls)))
        rows.append(("threads (4)", scenario_threadpool(urls, 4)))
        rows.append(("threads (16)", scenario_threadpool(urls, 16)))
        rows.append(("threads (32)", scenario_threadpool(urls, 32)))
        if aiohttp is not None:
            rows.append(("asyncio.gather (32)", asyncio.run(scenario_async(urls))))
        # ProcessPoolExecutor with `requests` and `spawn` start method is the
        # slowest. Pickling the URL is fine (it's a str), but every worker
        # re-imports requests (~200ms) on spawn. We use a small worker count
        # to keep the example bounded. Even so this row will be slow.
        rows.append(("processes (4)", scenario_processpool(urls, 4)))

        print("  scenario                                 wall-clock")
        print("  " + "-" * 50)
        for label, dt in rows:
            print(f"  {label:<40s}  {dt:8.3f}s")
        print()
        # Speedup vs serial.
        serial_t = rows[0][1]
        print("  speedup vs serial:")
        for label, dt in rows:
            speedup = serial_t / dt if dt > 0 else float("inf")
            print(f"    {label:<40s}  {speedup:5.2f}x")
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
# EXPECTED OUTPUT (default CPython 3.13, 4-core laptop, aiohttp installed)
# -----------------------------------------------------------------------------
# ==== IO-bound benchmark: 32 fetches, 0.10s each ====
#   ideal serial wall-clock      = 3.20s
#   ideal concurrent wall-clock  = 0.10s
#
#   scenario                                  wall-clock
#   --------------------------------------------------
#   serial (requests)                            3.21s
#   threads (4)                                  0.83s
#   threads (16)                                 0.23s
#   threads (32)                                 0.13s
#   asyncio.gather (32)                          0.11s    <-- closest to ideal
#   processes (4)                                4.50s    <-- WORSE than serial (warm-up dominates)
#
#   speedup vs serial:
#     serial (requests)                          1.00x
#     threads (4)                                3.87x
#     threads (16)                              13.96x
#     threads (32)                              24.69x
#     asyncio.gather (32)                       29.18x    <-- best
#     processes (4)                              0.71x    <-- SLOWDOWN
#
# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. The threads(32) row is within 20% of asyncio.gather(32). Why is async
#    still faster? Two reasons. (a) The thread pool spends ~100us per task
#    on queue.put / queue.get and per-thread state; asyncio's per-task
#    scheduling is ~1us. (b) The thread pool holds 32 OS threads (~50KB
#    resident each, ~1.6MB total stack pressure); asyncio holds 32 Task
#    objects (~5KB each, ~160KB total). For 32 the difference is small;
#    for 10_000 it is the difference between "works" and "crashes."
#
# 2. The processes(4) row is SLOWER than serial. Why? On macOS/Windows the
#    default start method is `spawn`. Each worker re-imports `requests`,
#    which costs ~150-300ms. Four workers x ~200ms warm-up = ~800ms before
#    any fetch begins, on top of the parallelism win. The result is a
#    SLOWDOWN. On Linux with `fork` you'd see ~3-4x speedup over serial,
#    because the cost is much lower - but still strictly worse than the
#    thread pool. The GIL was already released for IO; processes buy
#    nothing additional.
#
# 3. Apply the GIL-release test to `requests.get(url).content`. The slowest
#    operation is the recv() syscall inside socket. Is the GIL held during
#    that call? Answer: No. Modules/socketmodule.c wraps the recv loop in
#    Py_BEGIN_ALLOW_THREADS / Py_END_ALLOW_THREADS. Therefore threads
#    parallelise IO on default CPython. (See Lecture 1 section 3 case 2.)
#
# 4. On 3.13t, the timings should be approximately UNCHANGED. Why? Because
#    the GIL was already released for IO - there was nothing for the
#    free-threaded build to "fix." The performance difference between 3.13
#    and 3.13t on this workload is in the noise. (See Lecture 3 section 4
#    bucket 2.)
#
# 5. (Stretch) Replace `time.sleep(0.10)` in the server with `time.sleep(0.5)`
#    and run with `n_urls = 200`. The asyncio.gather row scales gracefully
#    (still ~0.6s wall-clock; 200 tasks at ~5KB each is negligible).
#    The threads(200) row works but uses 200 OS threads (~10MB of stack
#    pressure). The threads(64) row will be slower (~1.5s; ~3 batches).
#    This is the canonical "10K connections" example, miniaturised.
#
# 6. (Stretch) Add a row using aiohttp WITHOUT gather - one fetch at a
#    time, awaiting each before starting the next. Time it. It should
#    approach the serial(requests) timing, but with one OS thread instead
#    of (synchronously) blocking. The asynchrony is wasted without
#    concurrency; the win is concurrency, not the async syntax itself.
#
# 7. (Stretch) Add the asyncio scenario behind asyncio.TaskGroup() as tg:
#    and tg.create_task(...) for each URL. The structure should mirror
#    Week 5's exercises. The wall-clock should match gather() within 5%.
# -----------------------------------------------------------------------------
