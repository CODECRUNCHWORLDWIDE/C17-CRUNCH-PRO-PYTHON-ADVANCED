# Challenge 1 — Hunt a real leak

**Time:** ~120 minutes. **Difficulty:** Hard.

## Problem

Find a real memory leak in a real Python codebase. Reproduce it. Locate the source line. Propose a fix.

## Recommended targets

Pick one:

- **Your own Week-1 mini-project** — easy mode. Add a long-running loop that accumulates objects (e.g., a global cache that never expires).
- **A small open-source Flask/FastAPI app** — run it under load. Pick one with an active issue queue mentioning "memory leak" or "growing RSS."
- **A Jupyter notebook of your own that's been getting slow** — common real-world target.
- **A test suite that gets slower over time** — leaks across tests are common.

## What to produce

`challenge-01-leak-hunt.md` in your portfolio, containing:

1. The target (link if open-source, description if your own).
2. **Reproduction steps** — a deterministic recipe to grow memory.
3. **The leak source** — file path + line number, identified.
4. **Evidence**:
   - `tracemalloc` snapshot.compare_to() output showing the growing line.
   - OR `memray` flamegraph (PNG/HTML attached).
   - OR `objgraph.show_backrefs()` of a leaking object class.
5. **The fix** — code diff (a `git diff` works).
6. **Verification** — re-run the leak detector after the fix; line is gone.

## Acceptance criteria

- [ ] You produce evidence (snapshot output OR flamegraph OR objgraph PNG).
- [ ] You identify the leak by file:line, not just "somewhere in module X."
- [ ] The fix is committed (or, if open-source, drafted as a patch).
- [ ] Verification confirms the leak is gone — not just "smaller."

## Hints

<details>
<summary>How to set up the loop</summary>

Most leaks are "I do something repeatedly and memory grows over time." Wrap your target in a stress loop:

```python
import tracemalloc, time

tracemalloc.start()
snap_before = tracemalloc.take_snapshot()

for _ in range(1000):
    do_the_thing()    # what you're testing

snap_after = tracemalloc.take_snapshot()
top = snap_after.compare_to(snap_before, "lineno")
for line in top[:10]:
    print(line)
```

The top line in the output is your culprit (or a close relative).

</details>

<details>
<summary>Common leak patterns</summary>

- Global lists / dicts you append to and never clear.
- `functools.lru_cache(maxsize=None)` on a function that takes large args.
- Event listeners / callbacks that are never unsubscribed.
- Generators that hold large captures and are never closed.
- Long-lived sessions / connection pools that hold references to per-request objects.
- `logging` handlers that grow a buffer indefinitely.

</details>

<details>
<summary>If memray refuses to run on your platform</summary>

memray supports Linux and macOS. On Windows, use WSL2 or fall back to `tracemalloc` + `objgraph`. Or run your target in a Linux Docker container.

</details>

## Stretch

- Find a SECOND leak in the same codebase.
- File an issue (or PR) upstream if the leak is in an open-source project.
- Generalize the fix: write a `pytest` plugin that runs the test suite under tracemalloc and flags any test whose memory growth exceeds a threshold.

## Submission

Commit `challenge-01-leak-hunt.md` plus evidence files (PNG / HTML / .txt) to your portfolio under `c17-week-02/challenge-01/`.

## Why this matters

The first leak you find is the hardest. The reflexes you build here (instrumenting before guessing, isolating a smaller repro, validating the fix with the same tool) carry over to every kind of debugging.
