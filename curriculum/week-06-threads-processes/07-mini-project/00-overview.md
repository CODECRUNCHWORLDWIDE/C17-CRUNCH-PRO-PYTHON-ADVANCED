# Mini-Project — `concurrency-bench`: Three Workloads, Every Primitive, One Memo

> Build a small but real benchmark suite. Three workloads (one CPU-bound, one IO-bound, one mixed); five primitives (`serial`, `ThreadPoolExecutor`, `ProcessPoolExecutor`, `asyncio`, `joblib(loky)`); two CPython builds (`3.13`, `3.13t` if available); one comparison table; one ~800-word memo defending which primitive you would ship for each workload. The artifact is small (~400–600 lines) but its job is to make you defensible in any "should this be threads, processes, or async" code review.

**Estimated time:** 7 hours, spread across Thursday–Saturday.

## What you ship

A repository called `c17-week-06-concurrency-bench-<yourhandle>` containing:

1. **`bench/__init__.py`** — the package root. Re-exports `Workload`, `Implementation`, `BenchmarkRun`, `run_all`.
2. **`bench/workloads.py`** — the three workload definitions. Each is a `Workload(name, work_fn, gen_inputs, expected_check)`:
   - **CPU-bound (pure Python)**: `count_primes_in_range(start, end)` — pure-Python primality counter. The GIL is held throughout. The "process pool wins on default 3.13; 3.13t threads catch up" workload.
   - **IO-bound**: `fetch_url(url)` against a local `aiohttp.web` server with 100ms artificial latency. The "asyncio and thread pool both win, processes lose" workload.
   - **Mixed**: `fetch_then_hash(url)` — fetch a URL, then sha256-hash the body 5000 times. Both phases release the GIL (socket recv; hashlib). The "thread pool is the simplest right answer" workload.
3. **`bench/implementations.py`** — the five implementations. Each is `Implementation(name, run_fn)`:
   - `serial`: a `for` loop.
   - `threadpool`: `ThreadPoolExecutor.map(workload.work_fn, inputs)`.
   - `processpool`: `ProcessPoolExecutor.map(workload.work_fn, inputs)`.
   - `asyncio_impl`: `asyncio.gather(workload.work_fn_async(x) for x in inputs)` if the workload has an async variant; otherwise `loop.run_in_executor(thread_pool, work_fn, x)` for each input.
   - `joblib_loky`: `joblib.Parallel(n_jobs=N, backend="loky")(delayed(work_fn)(x) for x in inputs)`.
4. **`bench/harness.py`** — the measurement code. Runs each (workload, implementation, n_workers) cell three times, takes the median, captures wall-clock, peak RSS via `psutil.Process(...).memory_info().rss`, and per-process CPU time. Writes one CSV row per cell.
5. **`bench/runtime.py`** — runtime detection: Python version, `os.cpu_count()`, `sys._is_gil_enabled()`, `sysconfig.get_config_var('Py_GIL_DISABLED')`, platform.uname(). Captures these into the CSV.
6. **`bench/server.py`** — a tiny `aiohttp.web` server used by the IO-bound and mixed workloads. Serves `/page/{n}` with an artificial sleep. Bundled with the package; started by the harness.
7. **`bench/__main__.py`** — CLI entry. `python -m bench --workload {cpu,io,mixed,all} --impl {all,threadpool,...} --workers 1,2,4,8 --runs 3 --output results.csv`.
8. **`scripts/plot.py`** — reads the CSV and produces a stacked-bar chart (matplotlib, optional) with one bar per implementation per workload. Saves to `plots/{workload}.png`.
9. **`tests/test_workloads.py`** — pytest tests for each workload (correctness, not performance): each workload's `work_fn` produces the expected output for a known input. The benchmark is meaningless if the work_fn is wrong.
10. **`tests/test_implementations.py`** — pytest tests for each implementation: each one produces the same output for the same inputs.
11. **`README.md`** — what it is, how to install (`pip install -e .[test]`), how to run, example output.
12. **`MEMO.md`** — **the load-bearing artifact**. 800–1200 words. Three sections, one per workload, each containing:
    - The timing table.
    - The recommended primitive, named and justified with numbers.
    - One paragraph on what would change if the workload's parameters changed (more tasks, larger tasks, more shared state, target 3.13t).
    - References to lecture sections and `Lib/concurrent/futures/...` lines.

## What the harness must do

- **Run each cell three times**, take the median. Print warnings if the three runs disagree by more than 20%.
- **Capture runtime config**: Python version, build, GIL state, `cpu_count()`, OS.
- **Save raw timings to CSV** for later analysis. Do not just print to stdout.
- **Bound memory** to prevent OOM-killing on the process-pool variant of the CPU workload at large N. Cap `n_workers` at `min(max_workers_requested, os.cpu_count())`.
- **Start the local server once**, share it across all IO-bound runs. Do not start a new server per cell.
- **Clean up workers**: every `Executor` is used inside a `with` block. The harness should not leak workers across cells.
- **Be tolerant of `aiohttp` / `joblib` absence**: skip those impls gracefully if not installed.
- **Detect 3.13t and add a `gil_state` column** to the CSV: `enabled` or `disabled` (the runtime value of `sys._is_gil_enabled()` at the time of measurement).

## Acceptance criteria

- [ ] Repo public on GitHub at the URL above (or a private link shared with the reviewer).
- [ ] `pip install -e .` succeeds.
- [ ] `pytest tests/` passes on CPython 3.13.
- [ ] `python -m bench --workload all --impl all --workers 1,2,4,8 --runs 3` runs to completion in <10 minutes total on a 4-core laptop.
- [ ] `results.csv` contains at least 5 (impls) × 4 (worker counts) × 3 (workloads) = 60 rows.
- [ ] `MEMO.md` exists and contains three workload sections, each with timing table + numbered recommendation.
- [ ] If 3.13t is available, the memo includes one bonus paragraph contrasting the CPU-bound rows on both builds.
- [ ] The README is sufficient for a reviewer to install, run, and read the memo without asking you.

## Suggested order of operations

### Phase 1 — Skeleton (90 min, Thursday)

1. Create the package layout. `pip install -e .` should work after step 1.
2. Implement `bench/workloads.py`: just the three `Workload` objects, each with a tiny input set, each correct. Write `tests/test_workloads.py` and get it passing.
3. Implement `bench/implementations.py` with the four sync implementations (`serial`, `threadpool`, `processpool`, `joblib_loky`). Add the async one in Phase 2.
4. Get `tests/test_implementations.py` passing for the four sync impls — they all produce the same output as serial.

### Phase 2 — Async workload + measurement (90 min, Friday)

5. Add `bench/server.py`. Use `aiohttp.web` to serve `/page/{n}` with `await asyncio.sleep(0.1)` before responding. Bundle with the package.
6. Add the async variant of the IO-bound and mixed workloads. The CPU-bound workload's async variant uses `loop.run_in_executor`; document this as a deliberate choice in the memo.
7. Implement `bench/harness.py`: the loop over cells; the three-run median; the CSV writer. Include the runtime-config columns.
8. Run `python -m bench --workload io --impl all --workers 4 --runs 3` and verify the timings are plausible (async fastest, threads close, processes slow).

### Phase 3 — Polish and the memo (120 min, Friday + Saturday)

9. Run the full grid: every workload × every implementation × every worker count. Save to `results.csv`. Total runtime should be 5–10 minutes.
10. Write `scripts/plot.py` (optional but recommended). One PNG per workload showing wall-clock vs. n_workers, with one line per implementation.
11. **Write `MEMO.md`**. This is the artifact that survives. Three workload sections. Each:
    - One-paragraph workload description.
    - The timing table (read from `results.csv`).
    - The named, numbered recommendation: "I would ship `processpool` with `n_workers=4` for this workload because…".
    - The "what changes if" paragraph: parameters varied.
    - Source citations.

### Phase 4 — Free-threaded variant (90 min, Saturday)

12. Install `python3.13t` (`uv python install 3.13t`).
13. Re-run the full grid. Add a `--label python3.13t` argument so the CSV rows are distinguishable.
14. Add a fourth section to the memo: "What changes on 3.13t". One paragraph per workload (CPU-bound: thread pool catches up to process pool; IO-bound: no change; mixed: thread pool slightly improves on the CPU phase).

### Phase 5 — Polish, publish (60 min, Saturday afternoon)

15. Write the `README.md`. Include the example command and where to find the memo.
16. Push to GitHub. Verify `results.csv` is in the repo. Verify `MEMO.md` is in the repo. Verify the test fixtures (the server) are in the repo.

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| `bench/` ≤ 600 lines and clear | 10% | Reads top-to-bottom in one pass; no clever tricks needed |
| Correctness: every implementation produces identical output | 10% | All tests pass; the cross-impl correctness test catches a deliberately broken impl |
| Coverage: three workloads × five impls × four worker counts | 20% | The CSV has all the cells; the harness is reusable |
| Measurement discipline (median of 3, RSS captured, runtime metadata) | 15% | The numbers are believable; a 20%-disagreement warning is logged when it happens |
| The memo is technically substantive | 25% | Cites `Lib/concurrent/futures/...`, names the GIL-release predicate, justifies each recommendation with numbers, considers the "what if parameters change" axis |
| Free-threaded variant present (if available) | 10% | The memo's fourth section makes a concrete observation: thread row collapses on 3.13t for the CPU workload |
| README + repo hygiene | 10% | A reviewer can install + run + read in 15 minutes without asking questions |

## Stretch (optional, +5%)

Pick one (or more):

- **Distributed mode**. Add a `bench/dask_impl.py` or `bench/ray_impl.py` that runs the same workload across multiple machines (or even a single multi-process cluster). The interesting comparison is "how much overhead does network IPC add vs. local pickle IPC."
- **The chunksize sweep**. For the CPU-bound workload, run `processpool` with `chunksize ∈ {1, 4, 16, 64, 256}` and add a chart showing the amortisation curve.
- **NumPy variant**. Add a fourth workload: `numpy_eig(matrix)` — eigendecomposition of a 200×200 matrix. Both threading and `ThreadPoolExecutor` benefit because NumPy's LAPACK call releases the GIL; the comparison with the pure-Python prime counter is illuminating.
- **`max_tasks_per_child`**. On the process pool, add a sweep showing the effect of `maxtasksperchild=N` for the CPU workload, particularly when each task has a small memory leak. (This is the production reason `maxtasksperchild` exists.)
- **PyPy comparison**. Run the benchmark under PyPy 3.10+. The single-threaded performance should be 3–5× CPython on the pure-Python CPU workload; threading doesn't scale (PyPy still has a GIL); the implications for the decision tree are non-trivial.
- **Web UI**. A tiny `aiohttp` page that reads `results.csv` and renders the timing tables interactively. Two days of work; only do this if you genuinely enjoy frontend.

## Why this matters

A senior Python engineer should be able to answer "should this be threads or processes or async" in 60 seconds, with one or two questions back to clarify the workload. The decision tree from this week's lectures is what makes that 60-second answer possible.

This mini-project forces you to internalise the decision tree by measurement, not by intuition. After you have run the same workload eight ways and seen the numbers, the decision tree is muscle memory. The MEMO.md is the artifact you re-read when a colleague asks "which one should I use" — both as a reminder of your own conclusions and as a model for the kind of reasoning you should bring to the question.

This artifact is **public-facing**: it goes on your GitHub. The MEMO.md is the conversation starter ("here is when I would reach for each primitive, with numbers"). It is exactly the kind of artifact a senior interviewer will respond to.

## Submission

Push to GitHub. Paste the URL into `c17-week-06-submission.md` in your portfolio repo with one sentence on what you would do next if you had another day. (Common answers: "add the distributed-mode stretch goal" or "add a fourth workload that crosses 1M tasks to expose pickle behaviour at scale.")

After: continue to [Week 7 — Profiling Like It's Your Job](../../week-07-profiling-like-its-your-job/). Week 7 takes the measurement discipline you built here and adds `cProfile`, `py-spy`, `austin`, `scalene`, and flamegraphs. Phase 3 (Performance & Native Code) begins.
