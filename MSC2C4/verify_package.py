from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads(
    (PACKAGE / "EXACT_PREVIEW_PLAN.json").read_text(encoding="utf-8")
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
    receipt = {
        "action": "foxai_model_status_clarity_phase2c4_package_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "model_files_modified": False,
        "registry_modified": False,
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
            files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })
        if not files or not all(item["ok"] for item in files):
            raise RuntimeError("Package manifest verification failed.")
        receipt["checks"]["package_manifest"] = {
            "passed": True,
            "files": files,
        }

        expected_python = (ROOT / "env/python/python.exe").resolve()
        actual_python = Path(sys.executable).resolve()
        if actual_python != expected_python:
            raise RuntimeError("Verifier is not using FOXAI bundled Python.")
        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError("Unexpected bundled Python version.")
        receipt["checks"]["bundled_python"] = {
            "passed": True,
            "executable": str(actual_python),
            "version": sys.version,
        }

        policy = PLAN["policy"]
        if policy["apply_capability_present"]:
            raise RuntimeError("Apply capability must be absent.")
        prohibited = (
            "live_files_modified",
            "model_files_modified",
            "registry_modified",
            "automatic_model_launch",
            "model_server_action",
            "network_access",
        )
        if any(policy[name] for name in prohibited):
            raise RuntimeError("A prohibited preview capability is enabled.")
        if policy["delete_operations"]:
            raise RuntimeError("Delete operations must be empty.")
        receipt["checks"]["scope"] = {
            "passed": True,
            "policy": policy,
        }

        live = ROOT / "core/foxai_web.py"
        actual_live = sha256(live) if live.is_file() else None
        expected_live = PLAN["current_foxai_web_sha256"]
        if actual_live != expected_live:
            raise RuntimeError(
                "Live core/foxai_web.py no longer matches the approved baseline."
            )

        candidate = PACKAGE / "candidate/core/foxai_web.py"
        actual_candidate = sha256(candidate)
        if actual_candidate != PLAN["candidate_foxai_web_sha256"]:
            raise RuntimeError("Candidate WebUI hash mismatch.")

        receipt["checks"]["webui_hashes"] = {
            "passed": True,
            "live": actual_live,
            "candidate": actual_candidate,
        }

        receipt["state"] = "exact_preview_package_verified"
        receipt["verified"] = True
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    RECEIPT.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "State": receipt["state"],
        "Verified": receipt["verified"],
        "Apply capability present": False,
        "Live files modified": False,
        "Model files modified": False,
        "Receipt": str(RECEIPT),
    }, indent=2))
    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
