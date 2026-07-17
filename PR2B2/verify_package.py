from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"
RECEIPT = PACKAGE / "LIVE_VERIFY_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    result = {
        "action": "foxai_portable_runtime_phase2b2_package_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "live_files_modified": False,
        "apply_capability_present": False,
        "checks": {},
        "failure": None,
    }
    try:
        files = []
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, relative = line.split("  ", 1)
            path = PACKAGE / relative
            actual = sha256(path) if path.is_file() else None
            item = {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
            files.append(item)
        if not files or not all(item["ok"] for item in files):
            raise RuntimeError("Package manifest failed.")
        result["checks"]["package_manifest"] = {
            "passed": True,
            "files": files,
        }

        lock = json.loads((PACKAGE / "WHEELHOUSE_LOCK.json").read_text(
            encoding="utf-8"
        ))
        if len(lock.get("wheels", [])) != 12:
            raise RuntimeError("Wheel lock must contain exactly 12 wheels.")
        if not lock.get("policy", {}).get("wheels_only"):
            raise RuntimeError("Wheels-only policy is missing.")
        if lock.get("policy", {}).get("live_runtime_install"):
            raise RuntimeError("Live install is unexpectedly enabled.")
        result["checks"]["lock_contract"] = {
            "passed": True,
            "wheel_count": 12,
            "wheels_only": True,
            "live_install": False,
            "official_pypi_files_only": True,
        }

        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError("Unexpected Python version.")
        if Path(sys.executable).resolve() != (
            ROOT / "env/python/python.exe"
        ).resolve():
            raise RuntimeError("Verifier is not running with bundled Python.")
        result["checks"]["target_runtime"] = {
            "passed": True,
            "version": sys.version,
            "executable": sys.executable,
        }

        result["state"] = "acquisition_package_verified"
        result["verified"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    RECEIPT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "State": result["state"],
        "Verified": result["verified"],
        "Live files modified": False,
        "Apply capability present": False,
        "Receipt": str(RECEIPT),
    }, indent=2))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
