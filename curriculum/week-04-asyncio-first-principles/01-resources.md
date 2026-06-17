# Week 4 — Resources

All free. Citations are CPython `main` branch (3.13/3.14 dev) unless noted.

## Primary sources — CPython source tree (`Lib/asyncio/`)

| What | Where |
|------|-------|
| **The package init / public API surface** | `Lib/asyncio/__init__.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/__init__.py> |
| **The base event loop (where `_run_once` lives)** | `Lib/asyncio/base_events.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py> |
| **Selector-backed loop (the default on Unix and Windows ProactorPolicy)** | `Lib/asyncio/selector_events.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/selector_events.py> |
| **`Future`** | `Lib/asyncio/futures.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/futures.py> |
| **`Task`, `gather`, `wait`, `as_completed`, `sleep`, `wait_for`, `shield`** | `Lib/asyncio/tasks.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py> |
| **`TaskGroup` (PEP 654)** | `Lib/asyncio/taskgroups.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py> |
| **`asyncio.timeout` context manager** | `Lib/asyncio/timeouts.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/timeouts.py> |
| **Coroutine detection / `iscoroutine` / `iscoroutinefunction`** | `Lib/asyncio/coroutines.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/coroutines.py> |
| **`Runner` (the implementation behind `asyncio.run`)** | `Lib/asyncio/runners.py` — <https://github.com/python/cpython/blob/main/Lib/asyncio/runners.py> |
| **Locks, semaphore, queue, event** | `Lib/asyncio/locks.py`, `Lib/asyncio/queues.py` — <https://github.com/python/cpython/tree/main/Lib/asyncio> |
| **Transports and protocols (the I/O abstraction)** | `Lib/asyncio/transports.py`, `Lib/asyncio/protocols.py` |
| **High-level streams API (`StreamReader`/`StreamWriter`)** | `Lib/asyncio/streams.py` |
| **C accelerator for `Future` and `Task`** | `Modules/_asynciomodule.c` — <https://github.com/python/cpython/blob/main/Modules/_asynciomodule.c> (the pure-Python `Task`/`Future` are used when this is unavailable) |
| **`selectors` (the cross-platform I/O readiness wrapper)** | `Lib/selectors.py` — <https://github.com/python/cpython/blob/main/Lib/selectors.py> |
| **Coroutine bytecode opcodes (`GET_AWAITABLE`, `SEND`, `END_SEND`, `RETURN_GENERATOR`)** | `Python/bytecodes.c` — search `inst(GET_AWAITABLE,` and `inst(SEND,` |

## Required PEPs

- **PEP 342 — Coroutines via Enhanced Generators** (van Rossum, Eby, 2005; landed 2.5): <https://peps.python.org/pep-0342/>
  *The PEP that gave generators `.send()` and `.throw()` — the seed of every coroutine system Python has had since.*
- **PEP 380 — `yield from`** (Ewing, 2009; landed 3.3): <https://peps.python.org/pep-0380/>
  *Delegation. The mechanism that made generator-based coroutines composable. `yield from coro` is what `await coro` desugared to before native coroutines.*
- **PEP 492 — Coroutines with `async` and `await` syntax** (Selivanov, 2015; landed 3.5): <https://peps.python.org/pep-0492/>
  *The "native coroutine" PEP. Introduced `async def`, `await`, the `Coroutine` type as distinct from `Generator`.*
- **PEP 525 — Asynchronous Generators** (Selivanov, 2016; landed 3.6): <https://peps.python.org/pep-0525/>
  *`async def` functions that contain `yield`. Powers `async for`. Distinguishes from coroutines and from sync generators.*
- **PEP 530 — Asynchronous Comprehensions** (Selivanov, 2016; landed 3.6): <https://peps.python.org/pep-0530/>
- **PEP 654 — Exception Groups and `except*`** (van Rossum et al., 2021; landed 3.11): <https://peps.python.org/pep-0654/>
  *The mechanism that lets `TaskGroup` raise multiple errors at once without losing any.*
- **PEP 3156 — The "Tulip" PEP, asyncio's design** (van Rossum, 2012; landed 3.4): <https://peps.python.org/pep-3156/>
  *The original design document. Reading this is the fastest way to understand why asyncio is shaped the way it is — including the "callbacks at the bottom, coroutines on top" architecture.*
- **PEP 567 — Context Variables** (Selivanov, 2017; landed 3.7) (background): <https://peps.python.org/pep-0567/>
  *Why `asyncio.Task.get_loop().create_task(coro)` propagates context. Skim only.*

## Stdlib docs

- **`asyncio` index:** <https://docs.python.org/3/library/asyncio.html>
- **`asyncio` task and coroutine API:** <https://docs.python.org/3/library/asyncio-task.html>
- **`asyncio.TaskGroup`:** <https://docs.python.org/3/library/asyncio-task.html#task-groups>
- **`asyncio.run`, `asyncio.Runner`:** <https://docs.python.org/3/library/asyncio-runner.html>
- **`asyncio` low-level API (you need this for the toy clone):** <https://docs.python.org/3/library/asyncio-llapi-index.html>
- **`selectors`:** <https://docs.python.org/3/library/selectors.html>
- **`heapq` (the timer heap):** <https://docs.python.org/3/library/heapq.html>
- **`contextvars`:** <https://docs.python.org/3/library/contextvars.html>

## Background reading — the canon

- **Nathaniel J. Smith, *Notes on structured concurrency, or: Go statement considered harmful* (2018):**
  <https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/>
  *The single most important essay on async programming this decade. Required reading. The argument that motivated Trio's `nursery` and asyncio's `TaskGroup`.*
- **Nathaniel J. Smith, *Companion to "Notes on structured concurrency"*:** <https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/>
  *Why he built Trio rather than fix asyncio. Read after the first essay.*
- **Bob Nystrom, *What Color is Your Function?* (2015):**
  <https://journal.stuffwithstuff.com/2015/02/01/what-color-is-your-function/>
  *The "colored function" essay. The original framing of the `async`-everywhere infectious-keyword problem. Take it seriously: it explains a real cost.*
- **David Beazley, *Build Your Own Async* (2019, PyCon India):**
  <https://www.dabeaz.com/talks.html> (also on YouTube — search "Beazley async")
  *A live-coded 100-line event loop. The closest spiritual ancestor to this week's mini-project. Watch this if you have time before Tuesday.*
- **Andrew Svetlov, *asyncio in 2026*, PyCon US 2025 keynote** (search YouTube)
  *Optional. Current state of the package from the active maintainer.*
- **Brett Cannon, *How the heck does async/await work in Python 3.5?* (2016):**
  <https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/>
  *Walks through coroutine bytecode and the `Future.__await__` desugaring. Slightly dated but the mechanism is unchanged.*

## Adjacent libraries (worth knowing exist; skim, don't dive)

- **`trio`** — the other model: structured-concurrency-first, no callbacks, no `Future`. <https://trio.readthedocs.io/>
- **`anyio`** — a unifying layer that runs on both `asyncio` and `trio` backends. <https://anyio.readthedocs.io/>
- **`uvloop`** — a libuv-backed drop-in `asyncio` event loop, 2–4× faster on raw socket throughput. <https://github.com/MagicStack/uvloop>
- **`aiohttp`** — the de facto async HTTP client. <https://docs.aiohttp.org/>
- **`httpx`** — sync + async HTTP, anyio-based. <https://www.python-httpx.org/>

## Tools used this week

- **`asyncio` (stdlib)** — no install.
- **`aiohttp` (optional)** — for Exercise 2 (async HTTP fan-out). `pip install aiohttp`.
- **`memray` (optional)** — to measure memory of an async fan-out vs. a thread fan-out. `pip install memray`. We used this in Week 2; same install.
- **`tracemalloc` (stdlib)** — sufficient for Exercise 2's memory measurement if you do not want to install `memray`.

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `BaseEventLoop._run_once` (the heart) | `Lib/asyncio/base_events.py` (~line 1900 in 3.13) |
| `BaseEventLoop.call_soon` | `Lib/asyncio/base_events.py:call_soon` |
| `BaseEventLoop.call_later` | `Lib/asyncio/base_events.py:call_later` |
| `BaseEventLoop.create_task` | `Lib/asyncio/base_events.py:create_task` |
| `Task.__init__` | `Lib/asyncio/tasks.py` (pure-Python class; C version in `Modules/_asynciomodule.c`) |
| `Task.__step` | `Lib/asyncio/tasks.py` (the heart of the coroutine driver) |
| `Task.__wakeup` | `Lib/asyncio/tasks.py` |
| `sleep` | `Lib/asyncio/tasks.py:sleep` |
| `gather` | `Lib/asyncio/tasks.py:gather` |
| `wait` | `Lib/asyncio/tasks.py:wait` |
| `as_completed` | `Lib/asyncio/tasks.py:as_completed` |
| `TaskGroup` | `Lib/asyncio/taskgroups.py` |
| `Future.__await__` (the desugaring everything depends on) | `Lib/asyncio/futures.py` |
| `Future.add_done_callback` | `Lib/asyncio/futures.py` |
| `asyncio.run` / `Runner` | `Lib/asyncio/runners.py` |
| `iscoroutine` / coroutine detection | `Lib/asyncio/coroutines.py` |
| `selectors.DefaultSelector` | `Lib/selectors.py:DefaultSelector` |
| `GET_AWAITABLE` opcode | `Python/bytecodes.c`, search `inst(GET_AWAITABLE,` |
| `SEND` opcode | `Python/bytecodes.c`, search `inst(SEND,` |
| `RETURN_GENERATOR` opcode | `Python/bytecodes.c`, search `inst(RETURN_GENERATOR,` |
| `END_SEND` opcode | `Python/bytecodes.c`, search `inst(END_SEND,` |
| `_PyCoro_GetAwaitableIter` (the C-side awaitable-protocol resolver) | `Objects/genobject.c` — <https://github.com/python/cpython/blob/main/Objects/genobject.c> |

## Glossary

| Term | Definition |
|------|------------|
| **Awaitable** | An object the `await` expression accepts. Either a native coroutine (PEP 492), a generator-based coroutine (PEP 380 + `@types.coroutine`), or any object with `__await__` returning an iterator. |
| **Native coroutine** | A function defined with `async def`. Its `__class__` is `types.CoroutineType`. Distinct from a generator: cannot be iterated with `next()`, only driven with `.send()` or `await`-ed. |
| **Generator-based coroutine** | A generator decorated with `@types.coroutine` (or, historically, `@asyncio.coroutine`). Deprecated in 3.8, removed in 3.12 for `asyncio.coroutine`; `types.coroutine` itself remains. |
| **`__await__`** | A method that returns an iterator. The event loop reads what the iterator yields and decides what to do. `Future.__await__` yields `self` when not done; this is how the loop knows what the coroutine is waiting on. |
| **Event loop** | A `while True` that processes a runnable queue, a timer heap, and an I/O selector. The "loop" in `asyncio.run()`. |
| **Runnable queue (`_ready`)** | A `collections.deque` of `Handle` objects to call back. Drained every step of the loop. |
| **Timer heap (`_scheduled`)** | A `heapq` of `TimerHandle` objects, ordered by deadline. Expired entries are moved to `_ready` each step. |
| **Selector** | A wrapper over `epoll`/`kqueue`/`select` that reports which file descriptors are readable/writable. `selectors.DefaultSelector` picks the best for the platform. |
| **`Handle`** | A scheduled callback. `loop.call_soon(fn)` returns one. Cancellable. |
| **`Future`** | A value-or-exception cell with `add_done_callback`. The bridge between "a coroutine is awaiting this" and "the loop has finished it." |
| **`Task`** | A `Future` that drives a coroutine to completion. `Task.__step` is the coroutine driver. |
| **`Task.__step`** | The method that calls `coro.send(None)`, inspects what comes back (`StopIteration` → done; a `Future` → register as callback), and arranges for the next step. The heart of the coroutine driver. |
| **`gather`** | Wrap N coroutines as tasks, return a future that completes when all do; on first exception (default) cancels the rest. |
| **`TaskGroup`** | The PEP 654 / 3.11+ structured-concurrency tool. An async context manager whose `__aexit__` waits for every task and re-raises any failures as an `ExceptionGroup`. |
| **ExceptionGroup** | The PEP 654 type. `raise ExceptionGroup("msg", [exc1, exc2])` raises a group; `try ... except* TypeError` catches the `TypeError`s without losing the rest. |
| **Cancellation** | `task.cancel()` schedules a `CancelledError` to be `throw()`-n into the coroutine at its next `await` point. The cancellation story is much larger; this week we cover only enough to understand `TaskGroup`. |
| **Colored function** | Bob Nystrom's term. A function whose color (sync/async) must match its caller's. Once you have a green (async) function, every function up the call stack must also be green. |

---

*Broken link? Open an issue.*
