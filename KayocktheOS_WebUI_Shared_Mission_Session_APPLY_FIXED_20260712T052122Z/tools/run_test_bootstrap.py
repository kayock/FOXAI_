from __future__ import annotations

"""Portable-Python test bootstrap.

FOXAI's embedded/portable Python may run in isolated mode and ignore PYTHONPATH.
This bootstrap inserts the approved payload directory directly into sys.path
before executing a test file.
"""

from pathlib import Path
import runpy
import sys

if len(sys.argv) < 3:
    raise SystemExit(
        "Usage: run_test_bootstrap.py <payload_dir> <test_file> [test args...]"
    )

payload_dir = Path(sys.argv[1]).resolve()
test_file = Path(sys.argv[2]).resolve()
test_args = sys.argv[3:]

if not payload_dir.is_dir():
    raise SystemExit(f"Payload directory missing: {payload_dir}")
if not test_file.is_file():
    raise SystemExit(f"Test file missing: {test_file}")

sys.path.insert(0, str(payload_dir))
sys.argv = [str(test_file), *test_args]
runpy.run_path(str(test_file), run_name="__main__")
