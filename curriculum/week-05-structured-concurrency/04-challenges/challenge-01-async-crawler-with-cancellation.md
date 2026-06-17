# Challenge 1 — Async crawler skeleton with cancellation, in 3 hours

**Time:** ~3 hours, in one continuous block. Set a timer.
**Difficulty:** Hard.
**Prerequisite:** All three lectures read; all three exercises done.

## The brief

Build a runnable async crawler skeleton in **≤300 lines of Python** (including imports and the `if __name__ == "__main__":` block, excluding blank lines and comments). It must expose:

1. A `crawl(seeds: list[str], *, n_workers: int, per_host_concurrency: int, fetch_timeout: float, max_pages: int) -> list[Result]` coroutine that fans out N workers behind an `asyncio.Queue(maxsize=...)` and returns a list of crawl results.
2. **Structured concurrency**: every worker, the producer, the sink writer, and the monitor live in **one `asyncio.TaskGroup`**. No `asyncio.create_task` outside the group.
3. **Per-fetch timeout**: each fetch is wrapped in `async with asyncio.timeout(fetch_timeout):`. On timeout, the fetch is recorded as a failure and the worker moves on.
4. **Per-host concurrency cap**: a `dict[str, asyncio.Semaphore]` (one semaphore per host) gates HTTP calls so any one host sees at most `per_host_concurrency` concurrent connections.
5. **Bounded frontier**: `asyncio.Queue(maxsize=64)` for URLs to fetch. The producer/seed-feeder parks when full.
6. **Bounded sink**: `asyncio.Queue(maxsize=16)` for results. A single sink-writer task drains it. Workers park on `sink.put(result)` if the writer falls behind.
7. **Shielded sink write**: the worker's final `await sink.put(result)` is wrapped in `asyncio.shield(...)` so that a worker being cancelled during the put still delivers the result.
8. **Clean shutdown on `KeyboardInterrupt`**: a signal handler converts SIGINT into a cancellation of the TaskGroup. All in-flight fetches are cancelled; their `finally` blocks run; the sink is fully drained; the program exits with `exit code 130` (POSIX SIGINT convention).
9. **A small local test server** that the crawler can hit without the real internet. Use `aiohttp.web` to serve a tree of N HTML pages with cross-links.

Use only `asyncio`, `aiohttp` (`pip install aiohttp`), `html.parser` (stdlib), `urllib.parse` (stdlib), and `signal` (stdlib).

The demo (at the bottom of your file) should:

- Start the local test server with 200 pages and a branching factor of 5.
- Crawl with `n_workers=16`, `per_host_concurrency=4`, `fetch_timeout=2.0`, `max_pages=100`.
- Print, every 0.5s, the current state: `frontier=X sink=Y in_flight=Z fetched=W`.
- After `max_pages` pages, gracefully stop: producer stops adding to the frontier, workers drain it, sink writer flushes, server stops.
- Print the wall-clock and the total bytes downloaded.

## Acceptance criteria

- [ ] Source file is named `crawler.py`, ≤300 non-blank non-comment lines.
- [ ] Runs as `python crawler.py` and prints a sensible trace.
- [ ] Pressing Ctrl-C at any time produces a clean shutdown (no traceback at top level, no "Task was destroyed but it is pending!" warning).
- [ ] Removing the `asyncio.shield(...)` around the sink put causes at least one result to be lost when SIGINT fires mid-crawl. (Verify by counting: with shield, the count equals what the workers reported; without shield, the count is lower.)
- [ ] Removing the per-host `Semaphore` causes the crawler to open >`per_host_concurrency` connections to the test host. (Verify by counting concurrent server-side handlers.)
- [ ] The TaskGroup catches any unexpected exception and surfaces it as an `ExceptionGroup`; the crawler does not silently lose errors.
- [ ] No `asyncio.create_task` outside the `TaskGroup` (greppable).

## Time budget (suggested)

| Phase | Time |
|-------|------|
| Read your Lecture 3 §7 architecture diagram. Sketch the pipeline | 10 min |
| Write the local `aiohttp.web` test server | 25 min |
| Write `parse_links(html, base)` using `html.parser` | 15 min |
| Write `producer` (seeds + new URLs from workers) and `frontier` | 25 min |
| Write `worker(frontier, sink, per_host_sems)` with timeout + shield | 35 min |
| Write `sink_writer(sink, output_path)` | 15 min |
| Wire everything in a `TaskGroup` inside `crawl(...)` | 25 min |
| Add the SIGINT handler that cancels the TaskGroup | 15 min |
| Add the monitor / periodic status print | 10 min |
| Test the happy path; trim, refactor | 30 min |
| **Total** | **~3 h** |

## Gotchas in advance

1. **`asyncio.Queue.shutdown()` is 3.13+.** On 3.11/3.12, signal end-of-stream with a sentinel (`None`) and have each worker forward it before exiting.

2. **`aiohttp.ClientSession` must outlive the workers.** Open it in `crawl(...)` before the `TaskGroup`; close it after. If you put it inside the `TaskGroup`, the `__aexit__` on the session races the `__aexit__` on the group.

3. **The per-host `Semaphore` dict has a race.** `if host not in sems: sems[host] = Semaphore(N)` is not safe under concurrent workers. Use `setdefault` or wrap the dict in an `asyncio.Lock`. (Or pre-populate from a hostname allowlist.)

4. **Signal handlers in asyncio go through `loop.add_signal_handler`, not the `signal` module directly.** The `signal.signal()` API does not interact with the event loop on POSIX. Use `asyncio.get_running_loop().add_signal_handler(signal.SIGINT, _sigint_handler)`. Cite [`Lib/asyncio/unix_events.py:add_signal_handler`](https://github.com/python/cpython/blob/main/Lib/asyncio/unix_events.py).

5. **Cancelling a `TaskGroup` from a signal handler is subtle.** The handler runs in the loop's main task context but cannot `await`. The idiom: capture the `TaskGroup`'s parent task in a closure and call `parent_task.cancel()` from the handler. The group's `__aexit__` sees the cancellation and aborts every child.

6. **`html.parser.HTMLParser` does not stream gracefully.** For large pages, you may want to short-circuit after collecting `max_links_per_page` links. The local test server emits small pages so this is not critical for the challenge.

## Hints

<details>
<summary>Hint 1 - the worker skeleton</summary>

```python
async def worker(
    frontier: asyncio.Queue,
    sink: asyncio.Queue,
    per_host_sems: dict[str, asyncio.Semaphore],
    fetch_timeout: float,
    session: aiohttp.ClientSession,
) -> None:
    while True:
        try:
            url = await frontier.get()
        except asyncio.QueueShutDown:
            return
        try:
            host = urlparse(url).netloc
            sem = per_host_sems.setdefault(host, asyncio.Semaphore(PER_HOST))
            async with sem:
                async with asyncio.timeout(fetch_timeout):
                    async with session.get(url) as resp:
                        body = await resp.read()
            result = Result(url=url, status=resp.status, body_len=len(body))
            await asyncio.shield(sink.put(result))
        except (TimeoutError, aiohttp.ClientError) as e:
            await asyncio.shield(sink.put(Result(url=url, error=str(e))))
        finally:
            frontier.task_done()
```

</details>

<details>
<summary>Hint 2 - the SIGINT handler</summary>

```python
def install_sigint(parent_task: asyncio.Task) -> None:
    loop = asyncio.get_running_loop()
    def _handler():
        if not parent_task.done():
            parent_task.cancel()
    loop.add_signal_handler(signal.SIGINT, _handler)
```

Call `install_sigint(asyncio.current_task())` inside `crawl(...)` *before* entering the `TaskGroup`. Then on Ctrl-C, the current task (the one running the `async with TaskGroup`) is cancelled, the group's `__aexit__` propagates the cancellation to every child, every `finally` runs, the shielded sink put still lands.

</details>

<details>
<summary>Hint 3 - the test server</summary>

```python
from aiohttp import web

def make_test_server(n_pages: int, branching: int) -> web.Application:
    app = web.Application()
    async def page(request):
        i = int(request.match_info["i"])
        links = "".join(
            f'<a href="/page/{(i * branching + k) % n_pages}">k</a>'
            for k in range(1, branching + 1)
        )
        return web.Response(text=f"<html><body>page {i}{links}</body></html>",
                            content_type="text/html")
    app.router.add_get("/page/{i:\\d+}", page)
    app.router.add_get("/", lambda r: web.HTTPFound("/page/0"))
    return app
```

Run on `http://127.0.0.1:8000`. Start it via `aiohttp.web._run_app(...)` inside your crawler before the `TaskGroup` and shut it down inside the same group's exit cleanup.

</details>

## What "done" looks like

A single file `crawler.py`. Running it:

```
$ python crawler.py
[ 0.000s] test server up at http://127.0.0.1:8000
[ 0.000s] crawl starting: workers=16 per_host=4 timeout=2.0 max_pages=100
[ 0.500s] frontier=18 sink= 3 in_flight=16 fetched= 23
[ 1.000s] frontier=22 sink= 0 in_flight=16 fetched= 60
[ 1.421s] crawl complete: 100 pages, 8.4 MB total
$
```

Ctrl-C mid-crawl:

```
[ 0.502s] frontier=20 sink= 4 in_flight=16 fetched= 19
^C
[ 0.510s] SIGINT received, shutting down
[ 0.514s] cancellations delivered to 16 workers; sink draining...
[ 0.521s] crawl interrupted: 23 pages, 1.9 MB total (16 in-flight fetches cancelled cleanly)
$
```

No traceback at the top level. No "Task was destroyed but it is pending!" warnings. The sink file contains exactly 23 lines (or whatever the count was at the moment of SIGINT).

If your output looks like this, you have built the muscle for the mini-project. Continue to [`mini-project/README.md`](../07-mini-project/00-overview.md) on Thursday.
