# Challenge 1 — Build CPython from source

**Time estimate:** ~120 minutes (most of which is waiting for `make`).

## Problem statement

Clone the CPython repo, build it on your machine, and run a "hello world" with the Python you built. This is the single highest-leverage thing you can do to demystify CPython.

## Acceptance criteria

- [ ] You have a clone of `https://github.com/python/cpython.git` somewhere on disk.
- [ ] `./configure --enable-optimizations --with-pydebug` ran cleanly (or the platform-appropriate equivalent — see hints).
- [ ] `make -j$(nproc)` (or `make -j8`) completed.
- [ ] `./python -V` (Linux) or `./python.exe -V` (macOS) prints the version of the source you cloned.
- [ ] `./python -c "print('hello from my CPython')"` works.
- [ ] You captured a screenshot or terminal log of the build's final output and committed it to `notes/cpython-build.md` along with a short description of any platform-specific hiccups you hit.

## Stretch

- Run the CPython test suite: `./python -m test -j4`. Most tests should pass; a handful might fail on your machine. Note which ones.
- Edit `Python/bltinmodule.c` and change the implementation of `print` to prefix every call with `[my python]`. Rebuild. Try `./python -c "print('hi')"`. (Don't commit this change!)

## Hints

<details>
<summary>Prerequisites by platform</summary>

**macOS:**

```bash
brew install openssl xz gdbm tcl-tk
```

Then in the cpython directory:

```bash
./configure --with-openssl=$(brew --prefix openssl@3) --enable-optimizations
make -j$(sysctl -n hw.ncpu)
```

**Linux (Debian/Ubuntu):**

```bash
sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev \
                 libreadline-dev libsqlite3-dev libffi-dev liblzma-dev \
                 libncurses-dev tk-dev
./configure --enable-optimizations
make -j$(nproc)
```

**Windows:**

Open `PCbuild\pcbuild.sln` in Visual Studio 2022 and build. Or use WSL2 and follow the Linux instructions — recommended.

</details>

<details>
<summary>If `--enable-optimizations` takes forever</summary>

It runs the PGO (profile-guided optimization) training step which executes the test suite. For a faster, debug-friendly build, drop the flag:

```bash
./configure --with-pydebug
make -j8
```

You'll get a slower interpreter but a faster build. For exploration, this is fine.

</details>

<details>
<summary>If something fails with "module not found"</summary>

Probably a missing OS package. The configure step at the top prints "checking for X… no" lines — those are hints. Install the missing dev package and re-run `./configure && make clean && make -j$(nproc)`.

</details>

## Why this matters

For the rest of your career, when someone says "in CPython, X is implemented as Y in the C source," you'll have a built copy of that source on your machine. You'll know that "edit a C file, rebuild, run my edit" takes about 20 minutes the first time and 2 minutes after that. You'll stop treating the interpreter as a black box.

Even if you never look at the C source again, this challenge changes how you *feel* about Python. That's its purpose.

## Submission

Commit `notes/cpython-build.md` with the screenshot or paste of `./python -V` working.
