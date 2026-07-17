from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"
TARGETS = json.loads((PACKAGE / "AUDIT_TARGETS.json").read_text(encoding="utf-8"))
RECEIPT = PACKAGE / "PACKAGE_VERIFY_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    result = {
        "action": "foxai_portable_host_model_library_phase2c1_package_verify",
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

        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError("Unexpected bundled Python version.")
        if Path(sys.executable).resolve() != (
            ROOT / "env/python/python.exe"
        ).resolve():
            raise RuntimeError("Verifier is not using bundled Python.")
        result["checks"]["runtime"] = {
            "passed": True,
            "version": sys.version,
            "executable": sys.executable,
        }

        policy = TARGETS.get("policy", {})
        required_false = [
            "automatic_launch",
            "network_access",
            "full_gguf_hashing",
            "model_copy_move_rename_delete",
            "configuration_changes",
            "source_changes",
            "launcher_changes",
        ]
        if not policy.get("read_only"):
            raise RuntimeError("Read-only policy is missing.")
        if any(policy.get(key) for key in required_false):
            raise RuntimeError("A prohibited audit capability is enabled.")
        result["checks"]["scope"] = {
            "passed": True,
            "read_only": True,
            "automatic_launch": False,
            "network_access": False,
            "full_gguf_hashing": False,
            "model_changes": False,
        }

        live_files = []
        for relative, expected in TARGETS["locked_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            item = {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
            live_files.append(item)
        if not all(item["ok"] for item in live_files):
            raise RuntimeError("One or more locked live baselines changed.")
        result["checks"]["live_baselines"] = {
            "passed": True,
            "files": live_files,
        }

        result["state"] = "host_model_audit_package_verified"
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
