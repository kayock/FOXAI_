from __future__ import annotations

from pathlib import Path
import runpy
import sys

if len(sys.argv) < 3:
    raise SystemExit("usage: run_test_bootstrap.py PAYLOAD TEST [ARGS...]")

payload = str(Path(sys.argv[1]).resolve())
test = str(Path(sys.argv[2]).resolve())
sys.path.insert(0, payload)
sys.argv = [test, *sys.argv[3:]]
runpy.run_path(test, run_name="__main__")
