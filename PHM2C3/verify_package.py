from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads(
    (PACKAGE / "VALIDATION_TARGETS.json").read_text(encoding="utf-8")
)
MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"
RECEIPT = PACKAGE / "PACKAGE_VERIFY_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    result = {
        "action": "foxai_host_model_phase2c3_package_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "live_registry_modified": False,
        "model_files_modified": False,
        "automatic_model_launch": False,
        "network_access": False,
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
            files.append(
                {
                    "path": relative,
                    "expected": expected,
                    "actual": actual,
                    "ok": actual == expected,
                }
            )
        if not files or not all(item["ok"] for item in files):
            raise RuntimeError("Package manifest verification failed.")
        result["checks"]["package_manifest"] = {
            "passed": True,
            "files": files,
        }

        expected_python = (ROOT / "env/python/python.exe").resolve()
        actual_python = Path(sys.executable).resolve()
        if actual_python != expected_python:
            raise RuntimeError(
                "Verifier is not using FOXAI bundled Python."
            )
        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError("Unexpected bundled Python version.")
        result["checks"]["bundled_python"] = {
            "passed": True,
            "expected": str(expected_python),
            "actual": str(actual_python),
            "version": sys.version,
        }

        policy = TARGETS["policy"]
        prohibited = (
            "automatic_model_launch",
            "model_server_start",
            "model_server_stop",
            "external_network_access",
            "loopback_api_calls",
            "full_large_model_hashing",
            "model_copy_move_rename_delete",
            "live_registry_changes",
            "source_changes",
            "launcher_changes",
            "apply_capability",
        )
        if not policy.get("read_only_live_files"):
            raise RuntimeError("Read-only policy is missing.")
        if any(policy.get(name) for name in prohibited):
            raise RuntimeError("A prohibited capability is enabled.")
        result["checks"]["scope"] = {
            "passed": True,
            "policy": policy,
        }

        live_files = []
        for relative, expected in TARGETS["locked_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            live_files.append(
                {
                    "path": relative,
                    "expected": expected,
                    "actual": actual,
                    "ok": actual == expected,
                }
            )
        if not all(item["ok"] for item in live_files):
            raise RuntimeError(
                "One or more Phase 2C2 or security baselines changed."
            )
        result["checks"]["live_baselines"] = {
            "passed": True,
            "files": live_files,
        }

        result["state"] = "portability_validation_package_verified"
        result["verified"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    RECEIPT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "State": result["state"],
            "Verified": result["verified"],
            "Apply capability present": False,
            "Live files modified": False,
            "Live registry modified": False,
            "Model files modified": False,
            "Receipt": str(RECEIPT),
        },
        indent=2,
    ))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
