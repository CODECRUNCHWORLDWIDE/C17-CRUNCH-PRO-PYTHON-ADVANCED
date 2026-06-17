# Mini-Project — `crawl`: a robust async web crawler

> Build a production-shaped async crawler. ~500 lines of Python. Structured concurrency via `asyncio.TaskGroup`; per-fetch deadlines via `asyncio.timeout`; per-host politeness via `asyncio.Semaphore`; bounded frontier + bounded sink via `asyncio.Queue(maxsize=...)`; shielded sink writes via `asyncio.shield`; clean SIGINT shutdown via `loop.add_signal_handler`. Respects `robots.txt`. Publish it on GitHub.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-05-crawl-<yourhandle>` containing:

1. **`crawl/__init__.py`** — the package, re-exporting `Crawler`, `Result`, `crawl`. ≤600 non-blank, non-comment lines total across the package. Pure stdlib + `aiohttp`. Runs on CPython 3.11+.
2. **`crawl/crawler.py`** — the `Crawler` class. Owns the `aiohttp.ClientSession`, the per-host semaphores, the frontier queue, the sink queue, the `TaskGroup` orchestration.
3. **`crawl/fetch.py`** — `fetch(session, url, timeout) -> Result`. Wraps the HTTP call in `asyncio.timeout`. Returns a `Result` with status, body, headers, error.
4. **`crawl/parse.py`** — `extract_links(body: bytes, base_url: str) -> Iterable[str]`. Uses `html.parser`. Resolves relative URLs with `urllib.parse.urljoin`. Filters non-http schemes and off-host links.
5. **`crawl/robots.py`** — `RobotsCache`. Fetches `/robots.txt` once per host, caches the parsed rules (`urllib.robotparser`), exposes `is_allowed(url, user_agent) -> bool`.
6. **`crawl/sink.py`** — `JsonlSink`. A queue-backed sink writer task. Drains its queue, writes one JSON line per result, flushes on close. The single writer; workers `put` into its queue.
7. **`crawl/__main__.py`** — CLI entry. `python -m crawl --seed URL [--seed URL ...] --max-pages N --workers W --per-host P --timeout T --output PATH`. Parses arguments, installs the SIGINT handler, calls `crawl(...)`, exits with status code.
8. **`tests/test_crawl.py`** — at least seven tests covering:
   - A single URL is fetched and one result is written to the sink.
   - Two URLs on different hosts are crawled concurrently (verify wall-clock ≈ max, not sum).
   - A URL that times out yields a `Result(error="timeout")`, not an exception.
   - A `robots.txt` disallow is honored (the URL is not fetched).
   - Pressing Ctrl-C mid-crawl produces a clean shutdown (no `Task was destroyed but it is pending!` warning).
   - The sink file has exactly N lines, where N is the number of results the workers reported.
   - Removing the per-host semaphore causes >P concurrent server-side handlers for one host.
9. **`tests/fixtures/server.py`** — a small `aiohttp.web` test server. Serves `/page/N` with cross-links, plus `/robots.txt` and `/slow` (deliberately slow endpoint for timeout tests). Used by every test.
10. **`README.md`** — what it is, how to install (`pip install -e .[test]`), how to use it, example output, a paragraph on the design tradeoffs.
11. **`design.md`** — 800–1200 words on:
    - The structured-concurrency invariant: every task lives in one `TaskGroup`. Cite `Lib/asyncio/taskgroups.py:__aexit__` by file:line.
    - The cancellation strategy: per-fetch `asyncio.timeout`, per-write `asyncio.shield`, top-level `loop.add_signal_handler(SIGINT, ...)`. Cite `Lib/asyncio/timeouts.py:_on_timeout` and `Lib/asyncio/tasks.py:shield`.
    - The back-pressure strategy: bounded frontier + bounded sink. Why both bounds are necessary. Cite `Lib/asyncio/queues.py:Queue.put`.
    - The trade-offs you made: what is *not* in the crawler (e.g., JavaScript rendering, sitemaps, ETag-aware caching). Argue your priorities.
    - What you would add if you had another week.

## What the crawler must do

- **Crawl from one or more seed URLs**, following same-host links, until `max_pages` are fetched or the frontier is empty.
- **Honor `robots.txt`** for each host (fetch once, cache forever).
- **Apply a politeness delay** between fetches to the same host (configurable; default 0.5s — note: this is the *minimum* delay, not the only delay; the per-host semaphore is the concurrency cap).
- **Time out individual fetches** at `--timeout` seconds; failed fetches record `Result(error=...)` and the worker moves on.
- **Apply back-pressure**: the frontier queue is bounded (`maxsize=64`); the sink queue is bounded (`maxsize=32`). Workers parked on a full sink should parking propagate back through the frontier to the producer.
- **Shield the sink write**: the final `await sink.put(result)` must be wrapped in `asyncio.shield(...)` so that a worker being cancelled mid-write still delivers the result to the sink.
- **Clean SIGINT shutdown**: Ctrl-C at any time produces a graceful shutdown with no `Task was destroyed` warnings, no top-level traceback, and a final summary line. Exit code 130 (POSIX SIGINT).
- **Single `TaskGroup` at the top**: every task (workers, sink writer, monitor, signal-bridge) lives in one `async with asyncio.TaskGroup() as tg:`. No `asyncio.create_task` outside it.

## Acceptance criteria

- [ ] Repo public on GitHub at the URL above.
- [ ] `pip install -e .` succeeds.
- [ ] `pytest tests/` passes on CPython 3.11 and 3.13.
- [ ] `python -m crawl --seed http://127.0.0.1:8000/page/0 --max-pages 100 --output crawl.jsonl` against the bundled test server produces exactly 100 lines in `crawl.jsonl`.
- [ ] Ctrl-C mid-crawl produces a clean shutdown — verified by the test in `tests/test_crawl.py` that sends SIGINT to a subprocess and asserts on the exit code and output.
- [ ] No `asyncio.create_task` outside the top-level `TaskGroup`. Verifiable by `grep -n "asyncio.create_task" crawl/` returning at most matches that are inside `async with TaskGroup`.
- [ ] `design.md` exists and explains the choices. Citations include at least three `Lib/asyncio/*.py:method` references.
- [ ] README at the repo root is sufficient for a reviewer to install, run, and read the output without asking you.

## Suggested order of operations

### Phase 1 — Bones (90 min, Thursday)

1. From the challenge, you have a working ≤300-line single-file draft. Start there.
2. Move it into the new repo. Split into `crawler.py`, `fetch.py`, `parse.py`, `robots.py`, `sink.py`. Add `__init__.py` with the re-exports and `__main__.py` with the CLI.
3. Add the `tests/fixtures/server.py` (lift it from the challenge). Wire it into `tests/conftest.py` as a `pytest-asyncio` fixture.
4. Get one test passing: the single-URL happy path.

### Phase 2 — `robots.txt` and politeness (60 min, Friday)

5. Implement `crawl/robots.py` with `urllib.robotparser.RobotFileParser`. Cache one parser per host. Fetch lazily on the first request to a host.
6. Add a politeness `asyncio.Semaphore(per_host)` per host, plus a `last_fetch[host]` timestamp and a `delay` parameter that workers honor with `asyncio.sleep(remaining_delay)`. Note: the semaphore + delay together are the politeness story; either alone is insufficient.
7. Add a test that the test server's `/disallowed/*` route is not fetched when `robots.txt` disallows it.

### Phase 3 — Back-pressure and shielding (90 min, Friday)

8. Verify the frontier and sink queues are correctly bounded. Add a monitor task that logs `frontier.qsize()` and `sink.qsize()` every 0.5s.
9. Add the `asyncio.shield(...)` wrapper around the sink put. Verify (via a test that cancels mid-fetch) that the shielded write still lands.
10. Add a test that explicitly stalls the sink writer (sleep 5s before processing) and observes the frontier filling, the workers parking, the producer parking — back-pressure end-to-end.

### Phase 4 — Cancellation and SIGINT (90 min, Saturday morning)

11. Install the SIGINT handler with `loop.add_signal_handler(signal.SIGINT, _handler)`. The handler cancels the top-level task.
12. Add a test that spawns the crawler as a subprocess, waits 0.5s, sends SIGINT, asserts the exit code and reads the output file. The file must contain exactly the number of results the crawler reported as completed before the signal.
13. Run the crawler with the asyncio debug mode (`PYTHONASYNCIODEBUG=1`) and a small `max_pages`. Verify no warnings about destroyed pending tasks.

### Phase 5 — Polish, design.md, publish (90 min, Saturday afternoon)

14. Write `design.md`. This is the artifact that survives the longest. Cite `Lib/asyncio/taskgroups.py:__aexit__`, `Lib/asyncio/timeouts.py:_on_timeout`, `Lib/asyncio/queues.py:Queue.put`, `Lib/asyncio/tasks.py:shield` by file:line.
15. Write the `README.md`. Include the example invocation and expected output.
16. Push to GitHub. Verify the test server fixture is in the repo (some folks accidentally exclude it via `.gitignore`).

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| `crawl/` ≤ 600 lines and clear | 15% | Reads top-to-bottom in one pass; no clever tricks needed |
| Correctness: structured concurrency, back-pressure, robots, politeness | 25% | All seven required tests pass; behavior matches the spec |
| Cancellation correctness | 20% | Ctrl-C shutdown is genuinely clean; the shielded sink write test passes |
| Tests | 15% | All seven required tests, plus two of your own. Tests use the local server fixture, not the real internet. |
| `design.md` is technically substantive | 15% | Cites `Lib/asyncio/*.py` by file:line, names the primitives, defends tradeoffs without hand-waving |
| README is reviewer-friendly | 10% | One-screen install + use; clear examples; CLI documented |

## Stretch (optional, +5%)

Pick one (or more):

- **`anyio` port.** Re-implement the crawler against `anyio.create_task_group()` instead of `asyncio.TaskGroup`. The diff is illuminating. Document it in `design.md`.
- **Trio port.** Re-implement against Trio. Note: you will need to swap `aiohttp` for an HTTP client that works on Trio (e.g., `httpx` with Trio backend, or `asks`).
- **Sitemap support.** Fetch `/sitemap.xml` and add the listed URLs to the frontier (with deduplication).
- **Resume from checkpoint.** Periodically write the frontier state to disk; on startup, load it and continue where you left off. Useful for long crawls.
- **Distributed mode.** Replace the in-memory frontier with a Redis queue. Two crawler processes share the queue. Cancellation must still be clean per-process.
- **Live progress.** Render a `rich.progress.Progress` bar showing frontier depth, fetched count, errors, ETA.

## Why this matters

An async crawler is the canonical mid-size async portfolio piece. It exercises *every* primitive from this week's lectures in production-realistic combinations. After this project, when you read an unfamiliar async service, you will recognise the same shape: a TaskGroup wrapping a producer/consumer pipeline with bounded queues, per-fetch timeouts, per-resource semaphores, shielded final writes, and a signal handler that cancels the top-level task.

The real-world crawlers in the wild — `scrapy` (Twisted-era, not asyncio), `aiohttp`'s example crawler, GoogleBot, the Internet Archive's `heritrix` — are vastly larger but use the same core structure for their async paths. After this project, you can read their source and recognise the shape.

This artifact is **public-facing**: it goes on your GitHub, it is reasonable to mention in a senior-role interview ("I built a ~500-line async crawler with structured concurrency, back-pressure, and clean SIGINT shutdown"). The mini-project README is the conversation starter; `design.md` is the substantive backing. Make both readable.

## Submission

Push to GitHub. Paste the URL into `c17-week-05-submission.md` in your portfolio repo with one sentence on what you would do next if you had another day. (Most students answer: "implement the distributed-frontier stretch goal" or "add a small `rich` TUI showing live progress.")

After: continue to [Week 6 — Threads, Processes, and When to Use What](../../week-06-threads-processes-when-to-use-what/). Week 6 takes the other half of the concurrency picture — `threading`, `concurrent.futures`, `multiprocessing`, and the 3.13 free-threaded build.
