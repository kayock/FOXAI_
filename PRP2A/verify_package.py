from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PACKAGE_SHA256SUMS.txt"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> int:
    failures = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            failures.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
            })
    result = {
        "action": "foxai_portable_runtime_phase2a_probe_package_verify",
        "state": "verified" if not failures else "stopped_fail_closed",
        "verified": not failures,
        "apply_capability_present": False,
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 2

if __name__ == "__main__":
    raise SystemExit(main())
