# Exercise 3 — Attach `py-spy` to a Running Process

> **Goal:** attach `py-spy` to a long-running script you did *not* start under a profiler, produce a flamegraph, identify the hot leaf, and write a one-paragraph diagnosis. **Estimated time:** 45 minutes.

This is the production-shaped exercise. The script does not import `cProfile`. It does not have `@profile` decorators. It is a long-running process you cannot restart. You need to know what it is doing.

## What you ship

A directory `exercise-03/` in your portfolio containing:

1. `flame.svg` — the flamegraph produced by `py-spy record`.
2. `dump.txt` — the one-shot stack snapshot produced by `py-spy dump`.
3. `diagnosis.md` — a 150–250 word write-up that names the hot leaf, names the hot call path, and predicts a fix.

## Setup — the target script

Save this as `target.py` somewhere outside your portfolio (the script is the *thing being profiled*; it does not need to live in your repo):

```python
# target.py
"""
A long-running script that does several things, one of which is dominantly slow.
The script is intentionally not instrumented; pretend it is a production
service whose source you cannot edit. Run it from a terminal, then attach
py-spy from a second terminal.
"""
from __future__ import annotations

import hashlib
import random
import re
import time
from typing import List


def slow_regex(text: str) -> int:
    """Quadratic regex on a long string. The intentional hot leaf."""
    pattern = re.compile(r"(a+)+b")
    return len(pattern.findall(text))


def hash_round(buffer: bytes) -> str:
    """A few rounds of sha256. Releases the GIL; not slow."""
    h = hashlib.sha256()
    h.update(buffer)
    return h.hexdigest()


def generate_payload(n: int, rng: random.Random) -> str:
    """Build a long string with a lot of 'a's. Not the bottleneck."""
    return "a" * n + "b"


def loop_once(rng: random.Random) -> int:
    payload = generate_payload(40_000, rng)
    matches = slow_regex(payload)
    digest = hash_round(payload.encode())
    return len(digest) + matches


def main() -> None:
    rng = random.Random(0)
    print(f"target.py running, pid={__import__('os').getpid()}")
    iteration = 0
    while True:
        result = loop_once(rng)
        iteration += 1
        if iteration % 5 == 0:
            print(f"iteration {iteration} done; last result={result}")
        time.sleep(0.05)


if __name__ == "__main__":
    main()
```

The script prints its PID on startup and runs forever. The hot leaf is `slow_regex`: the regex `(a+)+b` against `aaaaa...b` is catastrophic backtracking. Each iteration takes seconds. You don't need to know that yet — you will find it out from py-spy.

## Step 1 — Run the target

Terminal A:

```bash
python target.py
```

It prints `target.py running, pid=12345` (your PID will differ). Leave it running.

## Step 2 — One-shot dump

Terminal B:

```bash
py-spy dump --pid 12345
```

You should see a stack like:

```
Process 12345: python target.py
Python v3.13.0

Thread 0x... (active)
  File "target.py", line N, in slow_regex
    return len(pattern.findall(text))
  File "target.py", line N, in loop_once
    matches = slow_regex(payload)
  File "target.py", line N, in main
    result = loop_once(rng)
  ...
```

If you see "permission denied," see Lecture 3 §3 — Linux's `ptrace_scope=1` is the default. Use `sudo py-spy dump --pid 12345` for this exercise. On macOS, `sudo` is also required.

Save the output to `dump.txt`:

```bash
sudo py-spy dump --pid 12345 > dump.txt
```

## Step 3 — Record a flamegraph

```bash
sudo py-spy record -o flame.svg --pid 12345 --duration 30
```

This samples for 30 seconds (the target keeps running) and writes `flame.svg`. Open in a browser.

You should see a flamegraph dominated by a wide tower ending in `slow_regex` and `re.Pattern.findall`. The `loop_once` and `main` frames are narrower (well, the same width, since everything goes through them — but their *exclusive* time, the bit not shared with descendants, is near zero).

## Step 4 — Write the diagnosis

Open `diagnosis.md`. Write 150–250 words. Address each of these:

- **Hot leaf.** What function is at the top of the widest tower? Quote the line of the source.
- **Hot path.** What is the call chain from `main` to the hot leaf?
- **Why is it slow?** Make a hypothesis. (Hint: read the regex carefully. The pattern `(a+)+b` against an `a`-heavy string is a classic.)
- **What would a fix look like?** One sentence; you do not have to implement it.

Example structure (do not copy verbatim):

> The hot leaf is `slow_regex` (target.py:N), specifically the `pattern.findall(text)` call. The hot path is `main` → `loop_once` → `slow_regex`. The cost is catastrophic backtracking: the regex `(a+)+b` against a long run of `a`'s exhibits exponential time in the length of the run because nested quantifiers allow the engine to retry every possible partition of `a`'s. The fix is either to rewrite the pattern to be linear-time — `a+b` matches the same intent without nested quantifiers — or to switch to a regex engine with linear-time guarantees such as `regex` with the `(?>...)` possessive form or `re2`. Sampling at 100 Hz over 30 seconds with py-spy showed `slow_regex` on top of 92% of samples.

## Step 5 — Clean up

Kill the target script in Terminal A (`Ctrl-C`).

## Acceptance

- [ ] `flame.svg` exists and shows a wide tower ending in `slow_regex` or `findall`.
- [ ] `dump.txt` contains a Python stack with `slow_regex` near the top.
- [ ] `diagnosis.md` names the hot leaf, hot path, hypothesis, and proposed fix.
- [ ] You did **not** edit `target.py` — the whole point is that you found the bottleneck from outside the process.

## Further exploration (optional, ~15 min)

- Try `py-spy top --pid PID` while the target is running. The live view should show the same hot leaf within a second or two of starting.
- Try `py-spy record --rate 250 -o flame_250hz.svg --pid PID --duration 10` for a 10-second capture at higher sample rate. Compare to the 100 Hz capture — the higher-rate version has finer-grained data but the hot leaf is the same.
- Pass `--idle` and re-record. The `time.sleep(0.05)` between iterations should now appear in the flamegraph as a separate stack — without `--idle` it is invisible.
- Confirm that `cProfile` would *not* have caught this without re-launching the target. (The exercise's point.)

## Reading

- Lecture 3 §§2–7 (py-spy in depth).
- py-spy README "Examples" section: <https://github.com/benfred/py-spy#examples>.
- Brendan Gregg, "Flame Graphs" — re-read the "Reading the Graph" section: <https://www.brendangregg.com/flamegraphs.html>.

## Why this exercise matters

Production stalls do not respect your `python -m cProfile script.py` workflow. The script is already running. You cannot restart it without losing in-flight requests, losing warm caches, losing the *exact state* that triggers the bug. `py-spy` is the only general-purpose answer. The skill you build here — attach, dump, record, read, diagnose — is the production skill. Practice it until the muscle memory is unconscious.
