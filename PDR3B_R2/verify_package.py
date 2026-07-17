from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads(
    (PACKAGE / "DESIGN_TARGETS.json").read_text(encoding="utf-8")
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
        "action": "foxai_portable_desktop_runtime_phase3b_package_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "desktop_gui_launched": False,
        "package_install": False,
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
            raise RuntimeError(
                "Verifier is not using FOXAI bundled Python."
            )
        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError("Unexpected bundled Python version.")
        receipt["checks"]["bundled_python"] = {
            "passed": True,
            "executable": str(actual_python),
            "version": sys.version,
        }

        policy = TARGETS["policy"]
        prohibited = (
            "apply_capability",
            "desktop_gui_launch",
            "automatic_launch",
            "model_server_action",
            "comfyui_action",
            "network_access",
            "pip_install",
            "package_install",
            "shortcut_changes",
            "launcher_changes",
            "source_changes",
            "runtime_changes",
        )
        if not policy.get("read_only"):
            raise RuntimeError("Read-only policy is missing.")
        if any(policy.get(name) for name in prohibited):
            raise RuntimeError(
                "A prohibited Phase 3B capability is enabled."
            )
        receipt["checks"]["scope"] = {
            "passed": True,
            "policy": policy,
        }

        live_files = []
        for relative, expected in TARGETS["known_live_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            live_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })
        if not all(item["ok"] for item in live_files):
            raise RuntimeError(
                "One or more protected Desktop/WebUI baselines changed."
            )
        receipt["checks"]["live_baselines"] = {
            "passed": True,
            "files": live_files,
        }

        receipt["state"] = "desktop_runtime_design_package_verified"
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
        "Desktop GUI launched": False,
        "Package install": False,
        "Receipt": str(RECEIPT),
    }, indent=2))

    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
