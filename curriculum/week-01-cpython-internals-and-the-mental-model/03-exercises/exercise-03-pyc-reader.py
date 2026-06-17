"""
Exercise 3 — Read a `.pyc` file

A `.pyc` file has a 16-byte header followed by a marshalled code object.
Your job: parse the header and unmarshal the code object using only the
standard library.

The header layout (CPython 3.7+):

    bytes  0..3    magic number (identifies Python version)
    bytes  4..7    flags (PEP 552; we'll just read them)
    bytes  8..11   source modification time OR source hash, depending on flags
    bytes 12..15   source size in bytes
    bytes 16..     marshalled code object

Estimated time: 30 minutes.

Run with: python exercise-03-pyc-reader.py

Acceptance criteria:
- The script accepts a .pyc path on the command line (or defaults to
  this file's own .pyc once you've created it).
- It prints the magic number (in hex), the version it implies (use
  importlib.util.MAGIC_NUMBER to compare against your current Python),
  the source modification time (or hash), the source size, and a
  summary of the marshalled code object (filename, name, argcount).
- The script does NOT use any third-party libraries.
"""

from __future__ import annotations

import importlib.util
import marshal
import struct
import sys
import time
from pathlib import Path


def read_pyc(path: Path) -> None:
    data = path.read_bytes()

    if len(data) < 16:
        print("File is too short to be a .pyc")
        return

    # The header is 16 bytes.
    magic = data[0:4]
    flags = struct.unpack("<I", data[4:8])[0]
    mtime_or_hash = data[8:12]
    src_size = struct.unpack("<I", data[12:16])[0]
    marshalled = data[16:]

    print(f"File:               {path}")
    print(f"Magic number:       {magic.hex()}  (current Python: {importlib.util.MAGIC_NUMBER.hex()})")
    if magic == importlib.util.MAGIC_NUMBER:
        print("                    ✓ matches the current interpreter")
    else:
        print("                    ✗ different from current interpreter")
    print(f"Flags:              0x{flags:08x}")
    if flags & 0x01:
        # Hash-based pyc (PEP 552)
        print(f"  -> hash-based PEP 552; bytes 8..11 are a 32-bit hash: {mtime_or_hash.hex()}")
    else:
        # Timestamp-based pyc
        mtime = struct.unpack("<I", mtime_or_hash)[0]
        print(f"  -> timestamp-based; source mtime: {mtime} ({time.ctime(mtime)})")
    print(f"Source size:        {src_size} bytes")

    # Now unmarshal the code object.
    try:
        code = marshal.loads(marshalled)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to unmarshal: {exc}")
        return

    print("\nCode object:")
    print(f"  co_filename:  {code.co_filename}")
    print(f"  co_name:      {code.co_name}")
    print(f"  co_argcount:  {code.co_argcount}")
    print(f"  co_consts:    {code.co_consts}")
    print(f"  co_varnames:  {code.co_varnames}")
    print(f"  co_names:     {code.co_names}")
    print(f"  bytecode:     {code.co_code[:32].hex()}... ({len(code.co_code)} bytes total)")


def main(argv: list[str]) -> int:
    if len(argv) >= 2:
        path = Path(argv[1])
    else:
        # Default: try to find this file's own .pyc.
        cache_dir = Path(__file__).parent / "__pycache__"
        candidates = list(cache_dir.glob("exercise-03-pyc-reader.*.pyc"))
        if not candidates:
            print(
                "No .pyc found yet — run `python -m py_compile "
                "exercise-03-pyc-reader.py` once, then re-run me."
            )
            return 1
        path = candidates[0]

    if not path.exists():
        print(f"No such file: {path}")
        return 1
    read_pyc(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


# -----------------------------------------------------------------------------
# WHAT TO PRODUCE
# -----------------------------------------------------------------------------
# Commit:
#   - This file.
#   - A `notes/exercise-03.md` that:
#       * pastes one .pyc output for your current Python,
#       * pastes one .pyc output for the SAME source compiled on a DIFFERENT
#         Python (use a second venv or Docker — `python3.12` and `python3.13`
#         is enough) — note how the magic number differs.
#       * explains in 2-3 sentences why PEP 552 hash-based pycs exist
#         (hint: reproducible builds).
#
# Acceptance: the comparison file is committed and shows two distinct magic
# numbers.
# -----------------------------------------------------------------------------
