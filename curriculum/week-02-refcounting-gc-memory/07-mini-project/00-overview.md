# Mini-Project — Detect a Leak in a Real Open-Source Project

> Pick a real Python project. Reproduce a memory leak. Identify the source. Propose a patch.

**Estimated time:** 7 hours, spread across Thursday-Saturday.

## What you ship

A repository called `c17-week-02-leak-hunt-<yourhandle>` containing:

1. **Target identification** — which open-source project, which version, what URL.
2. **Reproduction recipe** — a deterministic `repro.sh` (or `repro.py`) that grows memory by ≥10 MB over its run.
3. **Evidence** — `tracemalloc` or `memray` output, in a form a reviewer can re-run.
4. **Diagnosis** — `diagnosis.md` identifying the leak line.
5. **Fix** — either a code diff (`fix.patch`) or, if you can't fix it cleanly, a documented workaround.
6. **Verification** — re-running the repro after the fix shows flat memory.
7. **(Optional) PR upstream** — link if you opened one.

## Suggested targets

Pick any. Difficulty in parentheses:

- **Your own Week-1 `pyexplain` CLI** (easiest) — easy to instrument; you control everything.
- **A Flask or FastAPI tutorial app** (easy) — clone, run it under stress, observe.
- **`requests` + `urllib3`'s session pooling under high churn** (medium) — known leaky patterns.
- **A Celery worker that processes a stream of large tasks** (medium-hard) — common production target.
- **An open-source Python web app whose issue tracker mentions "memory" or "growing RSS"** (hard, real impact).

## Acceptance criteria

- [ ] Repo public on GitHub at the URL above.
- [ ] `repro.sh` runs in under 2 minutes on a stock laptop and reproduces the leak.
- [ ] Memory growth is visible: either a `tracemalloc` snapshot diff, a `memray` flamegraph, or `/usr/bin/time -v` RSS measurement.
- [ ] `diagnosis.md` identifies the source line by `file:line`.
- [ ] `fix.patch` or `fix.md` proposes a concrete fix.
- [ ] `verification.md` shows the fix actually works (re-run the repro; new measurement; difference).
- [ ] A README at the repo root explaining what's in the repo, how to run it, and the high-level finding.

## Suggested order of operations

### Phase 1 — Pick + reproduce (90 min)

1. Pick the target.
2. Set up a fresh venv. Pin versions.
3. Write a stress loop that exercises the code path.
4. Run under `tracemalloc` or `memray`. Confirm memory grows.

### Phase 2 — Localize (120 min)

5. Use `snapshot.compare_to` or the memray flamegraph to identify the source line.
6. Validate by adding `print(len(suspicious_collection))` at strategic points.
7. Confirm the leak grows linearly with the workload.

### Phase 3 — Fix (90 min)

8. Apply the smallest possible fix.
9. Re-run the repro. Measure.
10. Document the diff and the reasoning.

### Phase 4 — Polish + publish (60 min)

11. Clean up the repo. README it.
12. Commit, push.
13. If upstream is open-source: open an issue or PR. Reference your repo as the reproduction case.

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Repro is deterministic | 25% | Runs in <2 min, shows leak every time |
| Localization is precise | 25% | Names the file:line of the leak |
| Fix is minimal | 20% | One or two lines changed, not a refactor |
| Verification is rigorous | 15% | Same tooling, before/after, numbers |
| Documentation | 10% | Reviewer can re-run without asking you |
| Optional: PR upstream | 5% | Bonus if you submit it |

## Stretch

- Find a SECOND leak in the same project.
- Write a pytest plugin that detects memory growth across test runs (a small but real tool).
- Contribute the repro to the project's test suite as a regression test.

## Why this matters

Every senior Python role's interview at some point asks "tell me about a hard bug you found." Real memory leaks make great stories. This mini-project produces one — and a public artifact you can point at.

## Submission

Push to GitHub, paste the URL into `c17-week-02-submission.md` in your portfolio repo.

After: continue to [Week 3 — Bytecode, the Stack Machine, and the GIL](../../week-03-bytecode-stack-machine-gil/) — coming soon.
