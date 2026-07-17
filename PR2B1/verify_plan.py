from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import platform
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PACKAGE_MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"
PLAN = PACKAGE / "CORE_WHEELHOUSE_MANIFEST.json"
RECEIPT = PACKAGE / "LIVE_VERIFY_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    result = {
        "action": "foxai_portable_runtime_phase2b1_manifest_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "live_files_modified": False,
        "apply_capability_present": False,
        "checks": {},
        "failure": None,
    }

    try:
        package_files = []
        for line in PACKAGE_MANIFEST.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, relative = line.split("  ", 1)
            path = PACKAGE / relative
            actual = sha256(path) if path.is_file() else None
            package_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })
        if not package_files or not all(item["ok"] for item in package_files):
            raise RuntimeError("Package manifest failed.")
        result["checks"]["package_manifest"] = {
            "passed": True,
            "files": package_files,
        }

        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        required_direct = {
            "psutil": "7.2.2",
            "requests": "2.34.2",
            "pycasbin": "2.8.0",
            "watchdog": "6.0.0",
            "pluggy": "1.6.0",
        }
        actual_direct = {
            item["name"]: item["version"]
            for item in plan.get("direct_packages", [])
        }
        if actual_direct != required_direct:
            raise RuntimeError("Direct package lock does not match the approved plan.")
        if not plan.get("policy", {}).get("wheels_only"):
            raise RuntimeError("Wheels-only policy is not enabled.")
        if plan.get("policy", {}).get("source_distributions_allowed"):
            raise RuntimeError("Source distributions are unexpectedly allowed.")
        if plan.get("policy", {}).get("network_install_into_live_runtime"):
            raise RuntimeError("Live network installation is unexpectedly allowed.")
        result["checks"]["plan_contract"] = {
            "passed": True,
            "direct_packages": actual_direct,
            "transitive_constraints": len(plan.get("transitive_constraints", [])),
            "wheels_only": True,
            "live_network_install": False,
        }

        runtime_ok = (
            sys.version_info[:3] == (3, 14, 6)
            and platform.system() == "Windows"
            and platform.machine().lower() in {"amd64", "x86_64"}
            and Path(sys.executable).resolve() == (ROOT / "env/python/python.exe").resolve()
        )
        result["checks"]["target_runtime"] = {
            "passed": runtime_ok,
            "version": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
        }
        if not runtime_ok:
            raise RuntimeError("Target bundled Python identity does not match the plan.")

        live_files = []
        for relative, expected in plan.get("live_baselines", {}).items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            live_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })
        if not live_files or not all(item["ok"] for item in live_files):
            raise RuntimeError("One or more live baselines changed.")
        result["checks"]["live_baselines"] = {
            "passed": True,
            "files": live_files,
        }

        result["state"] = "wheelhouse_manifest_verified"
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
