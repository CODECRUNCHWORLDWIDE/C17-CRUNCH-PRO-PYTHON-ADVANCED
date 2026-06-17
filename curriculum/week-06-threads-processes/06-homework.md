# Week 6 — Homework

Six problems, ~6 hours total. Commit each as you finish.

---

## Problem 1 — Read `Lib/concurrent/futures/process.py` end-to-end (60 min)

Open the file on the CPython main branch: <https://github.com/python/cpython/blob/main/Lib/concurrent/futures/process.py>.

Read it top to bottom. It is ~600 lines as of 3.13. After Lecture 2 you should recognise the architecture: a `_CallQueue`, a `_ResultQueue`, the executor manager thread that bridges them to user `Future` objects.

**Acceptance:** `process-executor-reading.md` in your portfolio:

- A GitHub permalink to `_queue_management_worker`.
- A 350-word, line-by-line walkthrough of what happens when:
  - User calls `executor.submit(fn, x)`.
  - A `_WorkItem(future, fn, args, kwargs)` lands in `_pending_work_items`.
  - The manager thread picks it up and puts a `_CallItem(work_id, fn, args)` on `_call_queue`.
  - A worker reads the `_CallItem`, runs `fn(*args)`, puts a `_ResultItem(work_id, exception, result)` on `_result_queue`.
  - The manager thread reads the result and calls `future.set_result(...)` or `future.set_exception(...)`.
- One observation: how does `process.py` handle the case where the worker process dies (segfault, OOM-kill)? Cite the relevant code path. (Search for `BrokenProcessPool`.)
- One critique: where do you think the most subtle bug in this file lives? Defend.

---

## Problem 2 — Benchmark `os.cpu_count()` vs. effective threads on your machine (45 min)

Write `cpu-count-bench.py` that:

1. Reports `os.cpu_count()`, `psutil.cpu_count(logical=False)`, `psutil.cpu_count(logical=True)`, `os.process_cpu_count()` (3.13+), and `os.sched_getaffinity(0)` if available.
2. Runs a pure-Python CPU kernel (e.g., `count_primes_up_to(40_000)`) under `ThreadPoolExecutor(max_workers=N)` for N in `{1, 2, 4, 8, 16, 32}`. Reports wall-clock.
3. Repeats with `ProcessPoolExecutor`. Reports wall-clock.
4. If on 3.13t, repeats threads. (Skip cleanly if not on 3.13t.)

**Acceptance:**

- `cpu-count-bench.py` runs end-to-end.
- A `results.md` table: machine spec on top, the timing rows below.
- A `notes.md` paragraph (~150 words): what does the threads-vs-processes curve look like on your machine? At what `max_workers` value does each plateau? Hyperthreading (SMT) on most x86 machines reports 2x the physical core count via `os.cpu_count()` — does your process pool benefit from hyperthread count, or does it plateau at physical core count? Cite one source supporting your hypothesis.

---

## Problem 3 — Reproduce the four canonical `multiprocessing` failure modes (60 min)

Write `mp-failures.py` that reproduces each of the four failure modes from Lecture 2 §6, with a comment naming each:

1. **Tiny tasks**: 100_000 tasks of `x -> x + 1` under `ProcessPoolExecutor(max_workers=4)` with default chunksize. Compare to chunksize=1000 and to serial. Print wall-clock for all three.
2. **Large captured state**: a 50 MB bytes object captured by a closure passed to a worker. Show that each worker receives a pickled copy (count the total IPC bytes via `psutil.Process(...).io_counters()` if available, or estimate via timing).
3. **Missing `if __name__ == "__main__":` guard** (demonstrate via a separate `bad_script.py` that *does not have* the guard; document its behaviour on your OS; do not actually run it as a fork bomb — run with a worker limit and observe the error).
4. **Unpicklable arguments**: try to send a `sqlite3.Connection` (or a `threading.Lock`, or a `lambda`) to a worker. Capture the `TypeError`. Demonstrate the fix using `ProcessPoolExecutor(initializer=...)` with `initargs=(db_path,)`.

**Acceptance:**

- `mp-failures.py` reproduces all four. The fixes for 1 and 4 are demonstrated.
- A `notes.md` paragraph (~200 words): which failure mode have you (or a colleague) actually hit in production? If none, which is most likely to bite first?

---

## Problem 4 — Implement the workload-to-primitive decision tree as a function (60 min)

Write `recommend.py` containing a `recommend(workload_traits: dict) -> str` function. Input is a dict with keys:

- `"cpu_or_io"`: `"cpu"`, `"io"`, or `"mixed"`.
- `"gil_releasing"`: `True` if the dominant operation releases the GIL, `False` otherwise (only meaningful when `cpu_or_io != "io"`).
- `"task_count"`: an int.
- `"task_duration_ms"`: an int, the per-task wall-clock cost.
- `"shared_state_mb"`: an int, the size of read-mostly shared state.
- `"target_python"`: `"3.13"` or `"3.13t"`.

Output is a string: one of `"serial"`, `"threading"`, `"thread-pool"`, `"asyncio"`, `"process-pool"`, `"joblib-loky"`.

Encode the lectures' decision tree in the function. Justify each branch with a one-line comment citing the lecture and section.

Then write `test_recommend.py` with 15 test cases covering:

- IO-bound greenfield → `asyncio`.
- IO-bound brownfield (blocking library mentioned in the workload) → `thread-pool`.
- CPU-bound + GIL-releasing → `thread-pool`.
- CPU-bound + pure-Python + 3.13 → `process-pool` (or `joblib-loky` for large shared state).
- CPU-bound + pure-Python + 3.13t → `thread-pool`.
- Tiny tasks (`task_duration_ms < 10`) → `serial` (with a comment about chunksize).
- Mixed with large shared read-mostly state → `joblib-loky` with memmap.

**Acceptance:**

- `recommend.py` ≤120 lines, `test_recommend.py` ≤200 lines.
- `pytest test_recommend.py` passes all 15 cases.
- A `notes.md` paragraph: where do you disagree with the canonical decision tree? Defend or update.

---

## Problem 5 — Measure your `os.cpu_count()` on a free-threaded build (45 min)

If you have `python3.13t` available (via `uv python install 3.13t`, `pyenv install`, or a source build), run `exercise-01-CPU-bound-with-multiprocessing.py` on both `python3.13` and `python3.13t`. Capture the output of both.

**Acceptance:**

- A `freethreaded-comparison.md` containing both runs side by side.
- A 200-word paragraph contrasting them: which scenario showed the biggest difference; was the single-threaded slowdown visible; did the C-extension behavior surprise you.
- Run `python3.13t -c "import sys; print(sys._is_gil_enabled())"` before and after `import numpy` (or whichever heavy C extension you use). If `_is_gil_enabled()` flips from `False` to `True`, the extension is not free-threaded-compatible in your installed version. Note this in the writeup.

If you cannot get a 3.13t build working, document the attempt, what failed, and what you would try next. The honest write-up is the deliverable.

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 400–500 words:

1. Before this week, when someone said "use multiprocessing for CPU work," what was your default mental model? How has it sharpened? Be specific.
2. The GIL-release test from Lecture 1 §3: apply it to a piece of code you wrote in the last 12 months. Did your tool choice match what the test would have recommended? If not, would the recommended tool have been faster?
3. The 3.13 free-threaded build (PEP 703). If you were starting a new Python service today (2026), would you target `python3.13` or `python3.13t`? Give two concrete tradeoffs in each direction.
4. Imagine you are reviewing a teammate's PR that introduces `ProcessPoolExecutor` for a workload of 100 ms tasks on 1 KB inputs. Defend or critique their choice. What measurement would you ask them to add to the PR description?
5. asyncio (Weeks 4–5) vs. threads (this week): the same IO-bound problem can usually be solved either way. Name one IO-bound workload where threads are clearly the better choice in 2026, and one where async is clearly better. Defend.
6. Which lecture was the hardest to follow? What single concept would have helped if it had come earlier?

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 — `process.py` reading | 60 min |
| 2 — `cpu_count` vs. effective threads | 45 min |
| 3 — Four `multiprocessing` failure modes | 60 min |
| 4 — Decision tree as a function | 60 min |
| 5 — Free-threaded measurement | 45 min |
| 6 — Reflection | 45 min |
| **Total** | **~5.5 h** |

After homework, ship the [mini-project](./07-mini-project/00-overview.md): three workloads, every primitive, the comparison memo.
