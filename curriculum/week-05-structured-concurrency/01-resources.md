# Week 5 — Resources

All free. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — CPython source tree (`Lib/asyncio/`)

| What | Where |
|------|-------|
| **`TaskGroup` (PEP 654, structured concurrency in stdlib)** | `Lib/asyncio/taskgroups.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py> |
| **`asyncio.timeout` / `timeout_at` context manager (3.11+)** | `Lib/asyncio/timeouts.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/timeouts.py> |
| **`Task.cancel`, `Task.uncancel`, `Task.cancelling`** | `Lib/asyncio/tasks.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py> |
| **`shield`** | `Lib/asyncio/tasks.py:shield` — same file |
| **`wait_for`** | `Lib/asyncio/tasks.py:wait_for` — same file |
| **`gather` (for comparison)** | `Lib/asyncio/tasks.py:gather` — same file |
| **`Queue`, `LifoQueue`, `PriorityQueue`, `QueueShutDown` (3.13)** | `Lib/asyncio/queues.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py> |
| **`Semaphore`, `BoundedSemaphore`, `Lock`, `Event`, `Condition`** | `Lib/asyncio/locks.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/locks.py> |
| **`Future` (cancellation, callbacks)** | `Lib/asyncio/futures.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/futures.py> |
| **The base event loop (`_run_once`, scheduling)** | `Lib/asyncio/base_events.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py> |
| **Exceptions (`CancelledError`, `TimeoutError`, `InvalidStateError`)** | `Lib/asyncio/exceptions.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/exceptions.py> |
| **C accelerator for `Task`/`Future` (cancellation path)** | `Modules/_asynciomodule.c` — <https://github.com/python/cpython/blob/main/Modules/_asynciomodule.c> |

## Required PEPs

- **PEP 654 — Exception Groups and `except*`** (van Rossum, Stinner, Galindo, 2021; landed 3.11): <https://peps.python.org/pep-0654/>
  *The mechanism that lets `TaskGroup` raise multiple errors at once without losing any. Read §1 (rationale), §2 (`ExceptionGroup`), §3 (`except*` semantics).*
- **PEP 492 — Coroutines with `async` and `await` syntax** (Selivanov, 2015; landed 3.5; background): <https://peps.python.org/pep-0492/>
  *Background. The `async with` and `async for` constructs are introduced here; both are load-bearing this week.*
- **PEP 525 — Asynchronous Generators** (Selivanov, 2016; landed 3.6): <https://peps.python.org/pep-0525/>
  *`async def` functions that contain `yield`. The cooperative back-pressure primitive in Lecture 3 §5.*
- **PEP 565 — Show DeprecationWarning** (Cannon, 2017; background): <https://peps.python.org/pep-0565/>
  *Not directly related, but the 3.8 `CancelledError` reparenting to `BaseException` landed in the same release cycle and is documented in the 3.8 What's New: <https://docs.python.org/3/whatsnew/3.8.html#asyncio>.*
- **PEP 657 — Fine-Grained Error Locations in Tracebacks** (Galindo, Cheukyin, Pablo, 2021; landed 3.11; background): <https://peps.python.org/pep-0657/>
  *Useful when reading the multi-frame tracebacks an `ExceptionGroup` produces.*
- **PEP 3156 — The "Tulip" PEP, asyncio's design** (van Rossum, 2012; background): <https://peps.python.org/pep-3156/>
  *Background. Section 3 ("Coroutines and the scheduler") sets up the cancellation story.*

## Required reading — Nathaniel J. Smith

These three essays are the philosophical basis for everything in this week. Read at least the first.

- **Nathaniel J. Smith, *Notes on structured concurrency, or: Go statement considered harmful* (2018):**
  <https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/>
  *The single most important essay on async programming this decade. Required reading. ~45 minutes. The argument that motivated Trio's `nursery` and asyncio's `TaskGroup` (PEP 654).*
- **Nathaniel J. Smith, *Some thoughts on asynchronous API design in a post-`async/await` world* (2016):**
  <https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/>
  *Why he built Trio rather than fix asyncio. The case for "checkpoints" as a first-class concept. Read after the structured-concurrency essay.*
- **Nathaniel J. Smith, *Control-C handling in Python and Trio* (2018):**
  <https://vorpus.org/blog/control-c-handling-in-python-and-trio/>
  *The most carefully thought-through treatment of `KeyboardInterrupt` plus async cancellation in any language. Read before writing the mini-project; it saves you a class of bugs.*

## Stdlib docs

- **`asyncio` task and coroutine API:** <https://docs.python.org/3/library/asyncio-task.html>
- **`asyncio.TaskGroup`:** <https://docs.python.org/3/library/asyncio-task.html#task-groups>
- **`asyncio.timeout`:** <https://docs.python.org/3/library/asyncio-task.html#asyncio.timeout>
- **`asyncio.shield`:** <https://docs.python.org/3/library/asyncio-task.html#asyncio.shield>
- **`asyncio.wait_for`:** <https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for>
- **`asyncio.Queue`:** <https://docs.python.org/3/library/asyncio-queue.html>
- **`asyncio.Semaphore`:** <https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore>
- **`asyncio` exceptions (`CancelledError`, `TimeoutError`):** <https://docs.python.org/3/library/asyncio-exceptions.html>
- **`asyncio.Task.cancel` / `uncancel` / `cancelling`:** <https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel>

## Trio and anyio — the other models

Trio invented structured concurrency in Python. anyio generalised it across backends. Both are worth reading even if your production stack is `asyncio`.

- **Trio docs (start here):** <https://trio.readthedocs.io/en/stable/>
- **Trio nurseries reference:** <https://trio.readthedocs.io/en/stable/reference-core.html#tasks-let-you-do-multiple-things-at-once>
- **Trio cancellation reference (`CancelScope`, `move_on_after`, `fail_after`):** <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>
- **anyio docs:** <https://anyio.readthedocs.io/en/stable/>
- **anyio cancellation reference (`CancelScope`):** <https://anyio.readthedocs.io/en/stable/cancellation.html>
- **anyio tasks and task groups:** <https://anyio.readthedocs.io/en/stable/tasks.html>
- **`hypercorn`, `httpx`, `starlette`** — three production async libraries that use anyio. Worth skimming their structured-concurrency idioms.

## Background reading — the canon

- **David Beazley, *Build Your Own Async* (PyCon India 2019):** <https://www.dabeaz.com/talks.html>
  *The bottom-up version of the Week 4 / Week 5 story.*
- **Glyph Lefkowitz, *Unyielding* (2014):** <https://glyph.twistedmatrix.com/2014/02/unyielding.html>
  *Twisted-era argument for cooperative scheduling. Predates async/await; still relevant. The case for explicit yields.*
- **Sam Bull, *Robust Generic Functions on `asyncio`* (2018):** <https://sambull.org/2018/07/27/asyncio/>
  *The canonical write-up of the "swallowed `CancelledError`" bug. Short, sharp.*
- **`uvloop` blog, *Asynchronous Python at GitHub-scale* (2020):** <https://magic.io/blog/uvloop-blazing-fast-python-networking/>
  *Production tuning of asyncio. Optional but motivating.*
- **CPython 3.11 What's New, `asyncio` section:** <https://docs.python.org/3/whatsnew/3.11.html#asyncio>
  *The release notes for `TaskGroup`, `timeout()`, `uncancel`, `cancelling` — every new primitive used in this week.*
- **CPython 3.13 What's New, `asyncio` section:** <https://docs.python.org/3/whatsnew/3.13.html#asyncio>
  *`Queue.shutdown()`, `QueueShutDown`, eager-task-factory polish.*

## Adjacent libraries (worth knowing exist; skim, don't dive)

- **`aiohttp`** — the async HTTP client/server. The crawler mini-project uses `aiohttp.ClientSession`. <https://docs.aiohttp.org/>
- **`httpx`** — sync + async HTTP, anyio-based. Drop-in alternative if you prefer the anyio idiom. <https://www.python-httpx.org/>
- **`aiojobs`** — older "job scheduler" for asyncio; the pre-`TaskGroup` workaround for structured-ish concurrency. Read only to appreciate what `TaskGroup` replaced. <https://aiojobs.readthedocs.io/>
- **`aiostream`** — async stream/iterator combinators (`merge`, `pipe`, `map`). Useful for back-pressure pipelines. <https://aiostream.readthedocs.io/>
- **`uvloop`** — libuv-backed `asyncio` event loop, 2–4× faster on raw socket throughput. Drop-in. <https://github.com/MagicStack/uvloop>

## Tools used this week

- **`asyncio` (stdlib)** — no install.
- **`aiohttp`** — required for the mini-project crawler. `pip install aiohttp`.
- **`trio`** — optional, used in Lecture 1's side-by-side. `pip install trio`.
- **`anyio`** — optional, mentioned in Lecture 1 §6. `pip install anyio`.
- **`pytest` + `pytest-asyncio`** — for the homework tests. `pip install pytest pytest-asyncio`.
- **A local HTTP test server** — the mini-project ships with a small `aiohttp.web` server you can crawl against without hitting the real internet.

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `TaskGroup.__aenter__` | `Lib/asyncio/taskgroups.py:TaskGroup.__aenter__` |
| `TaskGroup.__aexit__` (the heart) | `Lib/asyncio/taskgroups.py:TaskGroup.__aexit__` |
| `TaskGroup._on_task_done` (the abort-on-first-error) | `Lib/asyncio/taskgroups.py:_on_task_done` |
| `TaskGroup.create_task` | `Lib/asyncio/taskgroups.py:create_task` |
| `Timeout.__aenter__` / `__aexit__` | `Lib/asyncio/timeouts.py` |
| `Timeout._on_timeout` (the scheduled cancel) | `Lib/asyncio/timeouts.py:_on_timeout` |
| `Task.cancel` (sets `_must_cancel`) | `Lib/asyncio/tasks.py:Task.cancel` |
| `Task.uncancel` (3.11+) | `Lib/asyncio/tasks.py:Task.uncancel` |
| `Task.cancelling` (3.11+) | `Lib/asyncio/tasks.py:Task.cancelling` |
| `shield` | `Lib/asyncio/tasks.py:shield` |
| `wait_for` | `Lib/asyncio/tasks.py:wait_for` |
| `Queue.put` / `Queue.get` | `Lib/asyncio/queues.py:Queue.put` / `:Queue.get` |
| `Queue.shutdown` (3.13+) | `Lib/asyncio/queues.py:Queue.shutdown` |
| `Semaphore.acquire` / `release` | `Lib/asyncio/locks.py:Semaphore.acquire` |
| `CancelledError` (since 3.8 a `BaseException`) | `Lib/asyncio/exceptions.py:CancelledError` |

## Glossary

| Term | Definition |
|------|------------|
| **Structured concurrency** | A discipline (Smith 2018) in which every concurrent task has a syntactic parent block; the block does not return until every child is done; an unhandled child error cancels every sibling. |
| **Nursery** | Trio's name for a structured-concurrency block. The thing `async with trio.open_nursery() as n` opens. |
| **`TaskGroup`** | asyncio's nursery, landed in 3.11. PEP 654-aware: re-raises errors as an `ExceptionGroup`. |
| **`ExceptionGroup`** | The PEP 654 container type. `raise ExceptionGroup("msg", [exc1, exc2])` raises a group; `try ... except* TypeError` splits it. |
| **`except*`** | The PEP 654 "starred except." Matches members of an `ExceptionGroup` by type; leaves the rest as a residual group. |
| **`CancelledError`** | The exception thrown into a task when something cancels it. Since 3.8, inherits from `BaseException`, not `Exception`. |
| **Cancellation** | The act of asking a task to stop. In asyncio, exception-based: `task.cancel()` schedules a `CancelledError` to be thrown at the task's next `await`. |
| **Cancel scope** | Trio's name for a region of code with its own cancel/timeout. asyncio approximates with `asyncio.timeout()` and the task's own cancel state. |
| **`asyncio.timeout`** | The 3.11+ context manager. `async with asyncio.timeout(5): ...` raises `TimeoutError` if the block doesn't finish in 5 seconds. Implemented via `Task.cancel` + `uncancel` on exit. |
| **`shield`** | A wrapper that protects a coroutine from being cancelled when *the awaiter* is cancelled. The inner coroutine continues to run; the awaiter raises `CancelledError`. |
| **`uncancel`** | The 3.11+ inverse of `cancel`. Decrements the cancelling counter on a task; if it reaches zero, the task is no longer pending cancellation. Used by `asyncio.timeout` to "absorb" the cancel it issued. |
| **`cancelling`** | The 3.11+ counter on a `Task`. Number of pending cancellations not yet observed. Returns 0 if the task is not being cancelled. |
| **Back-pressure** | The mechanism by which a slow consumer slows down a fast producer. In asyncio, expressed as a producer parking on `queue.put()` when the queue is full. |
| **Bounded queue** | A queue with a `maxsize`. `put()` parks when full; without a bound, a fast producer fills memory. |
| **Sentinel** | A marker value (often `None`) producers put on a queue to tell consumers "no more items." The 3.13 `Queue.shutdown()` is the modern alternative. |
| **`Queue.shutdown` (3.13)** | A method that marks a queue as closed. Pending `get()` calls raise `QueueShutDown`; pending `put()` calls raise the same. Replaces the sentinel idiom. |
| **`Semaphore`** | A counter-backed lock. `acquire()` decrements; `release()` increments. `Semaphore(N)` lets at most N coroutines past a gate at once. |
| **Async iterator** | An object with `__aiter__` and `__anext__` (PEP 525). Consumed by `async for`. A natural back-pressure primitive: the producer runs only when the consumer pulls. |
| **The "colored function" problem** | Bob Nystrom 2015. Once a function is `async def`, every caller must be `async def`. Re-raised here because cancellation only works for async-coloured frames. |

---

*Broken link? Open an issue.*
