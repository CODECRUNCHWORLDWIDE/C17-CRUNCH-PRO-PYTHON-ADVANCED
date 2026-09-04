# Week 5 — Structured Concurrency, Cancellation, Back-Pressure

> *A `go` statement, a thread `spawn`, an `asyncio.ensure_future` — they all share one defect: the parent has no idea the child exists. The child outlives the function that created it; its errors land somewhere unrelated; cancellation, when it eventually comes, races a half-flushed buffer. **Structured concurrency** is the discipline that fixes this. A nursery (Trio) or a `TaskGroup` (asyncio 3.11+) ties every task to a syntactic block. Exit the block, every task is done. One child raises, every sibling is cancelled. No child outlives its parent. The block is the lifetime. That single rule pays back ten years of subtle production bugs.*

Welcome to Week 5 of **C17 · Crunch Pro Python Advanced**. Week 4 reconstructed `asyncio` from the inside: coroutines as suspendable generators, a runnable queue plus timer heap plus selector, a `Task` that drives a coroutine, a `Future` that carries a value-or-exception cell, a `TaskGroup` that aggregates errors into an `ExceptionGroup` per PEP 654. By Sunday of Week 4 you had a 500-line `mini_asyncio` clone that runs a real fan-out.

This week takes that scaffolding and asks the harder question: **how do you write async code that does not leak, lie, or deadlock when something goes wrong?** Concretely: how do you cancel one task without breaking three others; how do you time out a network call without losing the connection's `finally` cleanup; how do you fan out a million URLs through a 16-connection pool without melting the producer.

The answer is **structured concurrency** (Smith 2018), and it is a real conceptual shift. Once internalised, it makes async Python feel like sync Python: every block has a definite lifetime, every error has a definite caller, every task has a definite parent. Trio invented the pattern with `nursery`; `anyio` (Wennergren, 2018+) lifted it onto both Trio and asyncio backends; CPython landed `asyncio.TaskGroup` and `asyncio.timeout` in 3.11 (PEP 654 + the timeout context manager); 3.12 hardened cancellation with the new `uncancel`/`cancelling` API; 3.13 polished it further. This week is the cumulative story.

Cancellation is the dual story. Cancellation in asyncio is **exception-based**: `task.cancel()` schedules a `CancelledError` to be thrown into the coroutine at its next `await` point. That single design decision has consequences — some pleasant (cancellation runs your `finally` blocks just like any other exception), some hostile (you can accidentally *swallow* a `CancelledError` with a bare `except Exception:` and live to regret it). We will walk through every consequence: shielded sections, timeout nesting, uncancel, the difference between "this task is cancelled" and "this task's *current await* is cancelled," and why `BaseException` (not `Exception`) is `CancelledError`'s parent since 3.8.

Back-pressure is the third axis. Async code makes it trivial to *start* a million tasks; it makes nothing easier about *finishing* them. A naïve `asyncio.gather(*[fetch(u) for u in urls])` will happily open ten thousand sockets, exhaust the file-descriptor table, and OOM the host. The remedy is **bounded queues** (`asyncio.Queue(maxsize=N)`) and **bounded concurrency** (`asyncio.Semaphore(N)`), used together to put a hard ceiling on how much in-flight work the system holds. When the consumer is slow, the producer parks on `queue.put()`; the pressure propagates backwards up the pipeline. This is the only correct architecture for an async crawler, an async ETL, or an async log shipper.

By Sunday you will have built a robust async crawler (`crawl`) that obeys robots.txt, applies a politeness delay per host, runs N workers behind a bounded queue, surfaces every error through a single `TaskGroup`, cancels cleanly on Ctrl-C, and shields a final sink-flush from cancellation. The crawler is ~500 lines and is interview-grade.

## Learning objectives

By the end of this week, you will be able to:

- **Define** structured concurrency formally (Smith 2018): every task has a syntactic parent block; the block returns only when every child is done; an unhandled error in a child cancels every sibling and propagates to the parent. Cite the asyncio implementation: `Lib/asyncio/taskgroups.py:TaskGroup.__aexit__`.
- **Distinguish** the four ways to cancel a task in modern asyncio: `Task.cancel()`, `asyncio.timeout()` (3.11+ context manager), `asyncio.wait_for()` (legacy timeout-and-cancel), and a parent `TaskGroup` aborting on a sibling failure. Know which one raises `TimeoutError` (PEP 654-aware since 3.11) and which one raises `CancelledError`.
- **Explain** why `CancelledError` inherits from `BaseException` (PEP 565 / Python 3.8) and what the practical consequence is for `except Exception:` clauses in long-lived async code.
- **Use** `asyncio.shield()` correctly to protect a critical region from outer cancellation, and explain the two-level semantics: the *inner* coroutine continues; the *outer* `await shield(...)` raises `CancelledError`. Cite `Lib/asyncio/tasks.py:shield`.
- **Apply** the `Task.uncancel()` / `Task.cancelling()` API (3.11+) and explain when a nested `asyncio.timeout()` context manager must call it on exit (the "single-shot cancel" idiom). Cite `Lib/asyncio/tasks.py:Task.uncancel` and `Lib/asyncio/timeouts.py`.
- **Design** a producer/consumer pipeline with `asyncio.Queue(maxsize=N)` where the producer correctly parks on a full queue and the consumer correctly signals end-of-stream with a sentinel or `queue.shutdown()` (3.13+).
- **Reason about** the difference between bounding work with a `Semaphore` (concurrency limit) and bounding work with a `Queue` (in-flight items limit), and pick the right one for fan-out vs. pipeline workloads.
- **Diagnose** the four canonical async bugs: the leaked task (no parent waiting), the swallowed cancellation (`except Exception:` over an `await`), the deadlocked queue (producer never closes, consumer waits forever), the silent timeout (a sibling task absorbs the timeout-induced cancel).
- **Cite** the PEPs and source files from memory: PEP 654 (ExceptionGroup), PEP 657 (fine-grained tracebacks, related), Trio's nursery essay, `Lib/asyncio/taskgroups.py`, `Lib/asyncio/timeouts.py`, `Lib/asyncio/queues.py`, `Lib/asyncio/tasks.py:shield`.

## Standards this week meets

| Bar | What this week is measured against |
| --- | --- |
| University | `COP 3337` — Raise, propagate and handle exceptions, and design what a failing operation promises its caller. |
| Industry | Ship async code that cancels cleanly under load, so a timeout firing mid-request leaves no half-written record and no task nobody is waiting on. |
| Beyond the bar | It names the four cancellation bugs and shows each one failing, including the `except Exception:` clause that swallowed `CancelledError` before Python 3.8 — `lecture-notes/02-timeouts-shield-and-cancellation-semantics.md` |


## Prerequisites

- **C17 Weeks 1–4** completed. You should be able to draw the `Task.__step` algorithm on a whiteboard, explain the `Future` state machine, and know what `gather(*coros)` does on first failure.
- A working CPython **3.13 or newer**. `TaskGroup` requires 3.11+; `asyncio.timeout()` requires 3.11+; `Task.uncancel()` requires 3.11+; `Queue.shutdown()` requires 3.13+. Several examples assume 3.13; we will flag the 3.11/3.12 alternatives explicitly.
- Comfort with **`async with`** (async context managers, PEP 492) and **`async for`** (async iterators, PEP 525). If new, re-read PEP 492 §3 and PEP 525 §1 before Monday.
- Comfort with **`except*`** (PEP 654). If new, re-read PEP 654 §2 before Monday. Week 4's Exercise 3 is the hands-on intro.
- Optional: install `trio` (`pip install trio`) and `anyio` (`pip install anyio`) for the side-by-side comparisons. We will use both in Lecture 1.

## Topics covered

- **What structured concurrency *is*** — Nathaniel J. Smith's 2018 essay reduced to one rule: *every concurrent task has a syntactic parent block, and the block does not exit until every child is done.* The contrast with `go`, `pthread_create`, `asyncio.ensure_future`. Why this rule pays back ten years of subtle bugs (no leaked tasks, no orphaned futures, no "task was destroyed but it is pending").
- **Nurseries and `TaskGroup`** — Trio's `async with trio.open_nursery() as n: n.start_soon(coro)`; the asyncio analog `async with asyncio.TaskGroup() as tg: tg.create_task(coro)`. Implementation: a list of tasks plus a done-callback that triggers abort-on-first-error. Cite `Lib/asyncio/taskgroups.py:TaskGroup.__aexit__` and `:_on_task_done`.
- **Cancellation semantics in depth** — `task.cancel()` schedules `CancelledError` at the next `await`. `BaseException`, not `Exception`. The PEP 565 / 3.8 promotion. Why this matters for long-running services that wrap blocks in `except Exception:`. Cite `Lib/asyncio/tasks.py:Task.cancel` and `Task.__cancel_message`.
- **`asyncio.timeout()` and the `cancelling` counter** — The 3.11+ context manager that raises `TimeoutError` on deadline. How it issues exactly one cancel and uses `Task.uncancel()` on exit to make timeouts compose cleanly (nested timeouts don't mis-target each other). Cite `Lib/asyncio/timeouts.py:Timeout.__aexit__`.
- **`asyncio.shield()`** — Protect a critical region from outer cancellation. The exact semantics: the inner coroutine continues to run on the loop; the outer `await shield(coro)` raises `CancelledError` if the caller is cancelled, but the inner coroutine itself is not. Cite `Lib/asyncio/tasks.py:shield`.
- **`wait_for` vs. `timeout()`** — Why both exist; why `timeout()` is the modern choice; the `wait_for` quirk where a finished result can be discarded if the timeout fires concurrently (the 3.11 fix is the `cancelling` counter). Cite `Lib/asyncio/tasks.py:wait_for`.
- **`ExceptionGroup` revisited** — PEP 654's `except*`, `BaseExceptionGroup` vs. `ExceptionGroup`, the split semantics, the residual group. When a `TaskGroup` re-raises with one error vs. with many. Why `KeyboardInterrupt` lands in a `BaseExceptionGroup`.
- **Back-pressure with bounded queues** — `asyncio.Queue(maxsize=N)`: `put()` parks when full, `get()` parks when empty. The producer/consumer pattern; the sentinel for end-of-stream; the 3.13 `Queue.shutdown()` and `QueueShutDown` exception. Cite `Lib/asyncio/queues.py`.
- **Semaphores for bounded concurrency** — `asyncio.Semaphore(N)` as an in-flight gate. When `Semaphore` vs. `Queue` is the right primitive. Cite `Lib/asyncio/locks.py:Semaphore`.
- **Async iterators and back-pressure** — `async for` plus `__aiter__`/`__anext__` (PEP 525). Why an async generator is a *cooperative* back-pressure primitive: the producer cannot run faster than the consumer pulls.
- **The four canonical bugs** — Leaked task; swallowed `CancelledError`; deadlocked queue; silent timeout-stolen-by-sibling. Each illustrated with a minimal reproduction.

## Weekly schedule (~34h intensive)

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Nurseries, TaskGroups, structured cancellation         | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Tuesday   | Timeouts, shield, cancellation semantics               | 2h       | 1.5h      | 0h         | 0.5h      | 1h       | 0h           | 0.5h       | 5.5h        |
| Wednesday | Back-pressure: bounded queues, semaphores              | 2h       | 1.5h      | 1h         | 0.5h      | 1h       | 0h           | 0.5h       | 6.5h        |
| Thursday  | Mini-project kickoff: the crawler architecture         | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Friday    | Mini-project deep work                                 | 0h       | 0h        | 1h         | 0.5h      | 1h       | 2h           | 0.5h       | 5h          |
| Saturday  | Mini-project polish + benchmark                        | 0h       | 0h        | 0h         | 0h        | 1h       | 3h           | 0h         | 4h          |
| Sunday    | Quiz + reflection                                      | 0h       | 0h        | 0h         | 0.5h      | 1h       | 0h           | 0h         | 1.5h        |
| **Total** |                                                        | **6h**   | **4.5h**  | **3h**     | **3h**    | **7h**   | **7h**       | **2.5h**   | **33h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Trio docs, anyio docs, PEP 654, asyncio source pointers, Nathaniel J. Smith's essay |
| [lecture-notes/01-nurseries-task-groups-and-structured-cancellation.md](./lecture-notes/01-nurseries-task-groups-and-structured-cancellation.md) | Smith's rule, Trio nurseries vs. asyncio `TaskGroup`, ExceptionGroup, the implementation of `__aexit__` |
| [lecture-notes/02-timeouts-shield-and-cancellation-semantics.md](./lecture-notes/02-timeouts-shield-and-cancellation-semantics.md) | `asyncio.timeout`, `shield`, `wait_for`, `Task.uncancel`, the cancellation state machine in 3.11+ |
| [lecture-notes/03-back-pressure-with-bounded-queues.md](./lecture-notes/03-back-pressure-with-bounded-queues.md) | `asyncio.Queue`, `Semaphore`, async iterators, the producer/consumer pipeline, sentinels and `Queue.shutdown` |
| [exercises/README.md](./exercises/README.md) | Index |
| [exercises/exercise-01-taskgroup-with-cancel.py](./exercises/exercise-01-taskgroup-with-cancel.py) | TaskGroup with one child cancelled mid-flight; verify sibling cancellation and `finally` ordering |
| [exercises/exercise-02-timeout-and-shield.py](./exercises/exercise-02-timeout-and-shield.py) | Nested `asyncio.timeout`; `shield` around a critical write; observe `uncancel` |
| [exercises/exercise-03-bounded-queue-fan-out.py](./exercises/exercise-03-bounded-queue-fan-out.py) | One producer, N consumers, `Queue(maxsize=K)`; watch the producer park when consumers stall |
| [challenges/README.md](./challenges/README.md) | Stretch challenge |
| [challenges/challenge-01-async-crawler-with-cancellation.md](./challenges/challenge-01-async-crawler-with-cancellation.md) | A small crawler skeleton that exercises every primitive in one timed sitting (~3h) |
| [quiz.md](./quiz.md) | 10 MCQ |
| [homework.md](./homework.md) | Six problems (~6h) |
| [mini-project/README.md](./mini-project/README.md) | A robust async web crawler with cancellation + back-pressure |

## Stretch

- Read [Nathaniel J. Smith, *Notes on structured concurrency, or: Go statement considered harmful*](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/) **end-to-end** (~45 min). This is the argument that motivated everything in this week. Required reading; the schedule above includes time for it on Monday morning.
- Read [`Lib/asyncio/taskgroups.py`](https://github.com/python/cpython/blob/main/Lib/asyncio/taskgroups.py) end-to-end (~250 lines, 20 min). After Lecture 1 you will recognise every line.
- Read [`Lib/asyncio/timeouts.py`](https://github.com/python/cpython/blob/main/Lib/asyncio/timeouts.py) end-to-end (~180 lines, 15 min). The `_on_timeout` callback and the `__aexit__` interplay with `uncancel` are the heart of the modern timeout story.
- Install `trio` and re-implement the mini-project against `trio` instead of `asyncio`. The diff is illuminating: Trio's nursery API is what `TaskGroup` was retrofitted to mimic.
- Read [Stuart Cook, *anyio: structured concurrency for the rest of us*](https://anyio.readthedocs.io/) and the anyio source. anyio's `CancelScope` and `move_on_after` are a generalisation of `asyncio.timeout` that runs on both backends.

## Up next

[Week 6 — Threads, Processes, and When to Use What](../week-06-threads-processes-when-to-use-what/) — `threading`, `concurrent.futures`, `multiprocessing`, `joblib`, the 3.13 free-threaded build. The other half of the concurrency story.
