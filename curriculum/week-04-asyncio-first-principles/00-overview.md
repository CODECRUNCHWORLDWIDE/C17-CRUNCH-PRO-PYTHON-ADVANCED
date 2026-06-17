# Week 4 — `asyncio` From First Principles

> *An event loop is a `while True` over a runnable queue, a heap of timers, and a `select()` call. Coroutines are generators with an `await` instead of a `yield`. `asyncio.run()` is twelve lines of Python wrapping that loop around a single top-level coroutine. Everything else — `Task`, `Future`, `gather`, `TaskGroup`, `wait_for`, `sleep` — is bookkeeping on top of those three primitives. If you can write a 200-line clone that runs a real program, you understand asyncio.*

Welcome to Week 4 of **C17 · Crunch Pro Python Advanced**. Phase 1 (Weeks 1–3) traced one Python instruction from source through bytecode into the value stack and showed why the GIL exists. Phase 2 opens here, with the concurrency model most senior Python engineers handle daily and few can explain from the inside: **`asyncio`**.

The standard library's `asyncio` package is roughly 12 000 lines of Python across 40 files (`Lib/asyncio/` in CPython main). Most of that code is *features* — protocols, transports, subprocesses, streams, locks, queues, signal handling on every platform, debug instrumentation, shutdown ordering. The *engine* under all of it is small. This week reconstructs that engine from scratch: coroutines as suspendable generators (PEP 492 plus the older PEP 380), the awaitable protocol (`__await__` returning an iterator that yields markers the loop understands), a runnable-queue scheduler, an `epoll`/`kqueue`/`select` selector, a heap of timers, and a `Task` wrapper that drives a coroutine to completion. By Sunday you will have built a toy `asyncio` clone — `mini_asyncio` — under 400 lines that runs a real fan-out program with `sleep`, `gather`, and a `TaskGroup` analogue, against your own event loop.

This is the lecture that ends the magic. After it, every `await` in Python source is a concrete instruction with a concrete semantics: "yield a marker to the loop, ask to be resumed when X happens, do not consume a thread while you wait."

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish** native coroutines (`async def`, PEP 492) from generator-based coroutines (PEP 380's `yield from`, deprecated but still informative) at the bytecode level — `GET_AWAITABLE`, `SEND`, `YIELD_VALUE`, `RESUME`, `RETURN_GENERATOR`.
- **Define** the awaitable protocol precisely: an object is awaitable iff it has `__await__()` returning an iterator, OR it is an instance of `types.CoroutineType`, OR it is a `Future`-like object that `inspect.isawaitable` accepts. Cite `Lib/asyncio/coroutines.py` and `Lib/asyncio/futures.py`.
- **Build** a single-threaded event loop in <200 lines of Python: runnable deque + timer heap + `selectors.DefaultSelector` for I/O readiness + a step-once driver.
- **Implement** `Task`, `Future`, `sleep`, `gather`, and a structured `TaskGroup` analogue against your loop. Cite the CPython implementation (`Lib/asyncio/tasks.py`, `Lib/asyncio/futures.py`, `Lib/asyncio/taskgroups.py`).
- **Explain** what the "colored function" problem is (Bob Nystrom, 2015), why asyncio inherits it from the choice to expose coroutines as a separate type, and why Trio and `anyio` did not solve it — only paved over it.
- **Reason about** `gather` vs. `wait` vs. `as_completed` vs. `TaskGroup` (PEP 654 ExceptionGroup-aware, 3.11+): when each is the correct tool, what their cancellation semantics are, and which one a senior Python engineer reaches for by default in 2026.
- **Benchmark** an async fan-out (1000 concurrent HTTP requests against a local server) against the same fan-out using a thread pool, and explain the order-of-magnitude difference in memory and tail-latency.
- **Read** the real `asyncio` event loop (`Lib/asyncio/base_events.py` and `Lib/asyncio/selector_events.py`) and locate, by `file:line`, the equivalent of every primitive in your toy clone.

## Prerequisites

- **C17 Weeks 1–3** completed. You should be able to read `dis.dis(f)` output, sketch a `PyObject` refcount, and explain the GIL.
- A working CPython **3.13 or newer**. `TaskGroup` requires 3.11+; `ExceptionGroup` is PEP 654 (3.11+); `asyncio.Runner` is 3.11+. Some examples use `asyncio.timeout()` (3.11+).
- Comfort reading **generators**: `next()`, `.send()`, `.throw()`, `.close()`, `StopIteration.value`. If `yield from` returning a value via `StopIteration` is unfamiliar, re-read PEP 380 before Monday.
- Comfort with the **`selectors`** stdlib module (level-triggered wrapper over `epoll`/`kqueue`/`select`). If new, skim `Lib/selectors.py` before Monday.

## Topics covered

- **Coroutines vs. generators** — PEP 342 (generator `.send()`), PEP 380 (`yield from` delegation), PEP 492 (`async def`, `await`), PEP 525 (asynchronous generators), PEP 530 (asynchronous comprehensions). What the compiler emits: `RESUME`, `SEND`, `YIELD_VALUE`, `GET_AWAITABLE`, `END_SEND`, `RETURN_GENERATOR`.
- **The awaitable protocol** — `__await__` returning an iterator; the loop reads what that iterator yields. `asyncio` chose to yield `Future`-like objects; Trio chose to yield strings ("checkpoint", "wait_readable", ...); both are valid implementations of the protocol.
- **The event loop, structurally** — `_ready: deque[Handle]` for runnable callbacks, `_scheduled: list[TimerHandle]` as a min-heap, `_selector: selectors.DefaultSelector` for I/O. The `_run_once` step: drain expired timers into `_ready`, poll the selector with timeout = next-timer-deadline, drain selector callbacks into `_ready`, run everything in `_ready` exactly once. Cite `Lib/asyncio/base_events.py:1900` (3.13).
- **`Future`** — a value-or-exception cell with callbacks. State machine: `PENDING` → `CANCELLED` | `FINISHED`. `add_done_callback` is the bridge between "I am waiting on this future" and "the loop will resume me."
- **`Task`** — a `Future` whose `__init__` schedules a step that calls `coro.send(None)`, receives back a `Future` (the thing the coroutine is awaiting), and registers itself as a callback on that `Future`. Cite `Lib/asyncio/tasks.py:Task.__step` (3.13).
- **`sleep`** — schedules a no-op callback for `now + delay` and `await`s a `Future` that the callback completes. Eight lines of Python. Cite `Lib/asyncio/tasks.py:sleep` (3.13).
- **`gather`** — wraps each coroutine in a `Task`, returns a `Future` that completes when all (or any, in the `return_exceptions=False` case, on first exception) complete. Cite `Lib/asyncio/tasks.py:gather` (3.13).
- **`TaskGroup` (PEP 654)** — structured concurrency, ExceptionGroup-aware cancellation. The async-context-manager exit method waits for every task in the group and re-raises any unhandled errors as an `ExceptionGroup`. Cite `Lib/asyncio/taskgroups.py` (3.13).
- **The "colored function" debate** — Bob Nystrom's 2015 essay. Why `async def` propagates: any function that wants to call an `async def` must itself be `async def`. The cost (every API choice eventually doubles). The benefit (the static "this can suspend" property survives composition).
- **Cancellation, briefly** — `task.cancel()` schedules a `CancelledError` to be thrown into the coroutine at the next `await` point. The full cancellation story is Week 5; this week we cover only enough to make `TaskGroup`'s exception aggregation work.

## Weekly schedule (~36h intensive)

| Day       | Focus                                            | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Coroutines, generators, the awaitable protocol   | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | Build an event loop from scratch                 | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0h         | 6.5h        |
| Wednesday | Tasks, Futures, gather, TaskGroup                | 2h       | 2h        | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 7h          |
| Thursday  | Real asyncio source tour + mini-project kickoff  | 0h       | 1.5h      | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6.5h        |
| Friday    | Mini-project deep work                           | 0h       | 1h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 6h          |
| Saturday  | Mini-project polish + benchmark                  | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                | 0h       | 0h        | 0h         | 0.5h      | 0h       | 0h           | 0h         | 0.5h        |
| **Total** |                                                  | **6h**   | **8h**    | **4h**     | **3h**    | **6h**   | **7h**       | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview |
| [resources.md](./01-resources.md) | `asyncio` source pointers, PEPs, devguide, Trio readings |
| [lecture-notes/01-coroutines-vs-generators.md](./02-lecture-notes/01-coroutines-vs-generators.md) | `async def`, `await`, awaitables, bytecode for both, PEP 492 |
| [lecture-notes/02-the-event-loop-build-your-own.md](./02-lecture-notes/02-the-event-loop-build-your-own.md) | Runnable queue, timer heap, selector poll, the `_run_once` step |
| [lecture-notes/03-tasks-futures-gather-taskgroup.md](./02-lecture-notes/03-tasks-futures-gather-taskgroup.md) | `Future` state machine, `Task.__step`, `gather`, `TaskGroup` (PEP 654) |
| [exercises/README.md](./03-exercises/00-overview.md) | Index |
| [exercises/exercise-01-toy-event-loop.py](./03-exercises/exercise-01-toy-event-loop.py) | ~80-line event loop running two coroutines with sleep |
| [exercises/exercise-02-async-vs-thread-fetch.py](./03-exercises/exercise-02-async-vs-thread-fetch.py) | Fan-out: asyncio vs. ThreadPoolExecutor; measure memory and latency |
| [exercises/exercise-03-taskgroup-fan-out.py](./03-exercises/exercise-03-taskgroup-fan-out.py) | Real `asyncio.TaskGroup` with one failing child; observe ExceptionGroup |
| [challenges/README.md](./04-challenges/00-overview.md) | Stretch challenge |
| [challenges/challenge-01-asyncio-clone.md](./04-challenges/challenge-01-asyncio-clone.md) | Build the mini-project's clone from scratch in one 4-hour sitting |
| [quiz.md](./05-quiz.md) | 10 MCQ |
| [homework.md](./06-homework.md) | Six problems (~6h) |
| [mini-project/README.md](./07-mini-project/00-overview.md) | A toy `asyncio` clone: `sleep`, `gather`, `Task`, `run` |

## Stretch

- Read `Lib/asyncio/base_events.py` end-to-end (~2000 lines as of 3.13; ~3 hours). The core loop is `_run_once` at roughly line 1900; every other method is policy. After this week you will recognize every primitive.
- Read [Nathaniel J. Smith, *Notes on structured concurrency*](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/) (2018). It is the philosophical basis for Trio and for asyncio's `TaskGroup` (3.11+).
- Build a `aiohttp`-style HTTP client *against your toy loop* — i.e., wrap a raw TCP socket with your selector and parse one HTTP/1.1 response. ~2 hours; an excellent stress-test of the design.

## Up next

[Week 5 — Structured Concurrency, Cancellation, Back-Pressure](../week-05-structured-concurrency-cancellation-backpressure/) — coming soon. We will take this week's `TaskGroup` analogue and harden it: nurseries, cancellation scopes, `shield`, `wait_for`, bounded queues, back-pressure on async iterators.
