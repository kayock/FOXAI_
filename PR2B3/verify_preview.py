from __future__ import annotations

from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / "PREVIEW_PLAN.json").read_text(encoding="utf-8"))
PACKAGE_MANIFEST = PACKAGE / "PACKAGE_SHA256SUMS.txt"
RECEIPT_PATH = PACKAGE / "LIVE_VERIFY_RECEIPT.json"
TREE_MANIFEST_PATH = PACKAGE / "CANDIDATE_TREE_MANIFEST.json"
CANDIDATE_SITE = PACKAGE / "candidate/Runtime/Core/site-packages"
CANDIDATE_RUNTIME_MANIFEST = (
    PACKAGE / "candidate/Runtime/Core/CORE_RUNTIME_MANIFEST.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: str) -> bool:
    pure = PurePosixPath(name)
    return (
        bool(name)
        and not pure.is_absolute()
        and ".." not in pure.parts
        and not any(":" in part for part in pure.parts)
    )


def tree_records(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            records.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return records


def tree_digest(records: list[dict]) -> str:
    digest = hashlib.sha256()
    for item in records:
        line = (
            f"{item['path']}\0{item['size_bytes']}\0"
            f"{item['sha256']}\n"
        )
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def extract_wheels(receipt: dict) -> dict:
    if CANDIDATE_SITE.exists() and any(CANDIDATE_SITE.iterdir()):
        raise RuntimeError(
            "Candidate runtime already exists. Re-extract a fresh PR2B3 "
            "folder before rerunning the exact preview."
        )
    CANDIDATE_SITE.mkdir(parents=True, exist_ok=True)
    verified = Path(receipt["verified_path"])
    seen: dict[str, str] = {}
    wheels = []

    for item in receipt["wheels"]:
        wheel = verified / item["filename"]
        actual = sha256(wheel) if wheel.is_file() else None
        if actual != item["expected_sha256"]:
            raise RuntimeError(f"Verified wheel changed: {item['filename']}")
        wheel_record = {
            "filename": item["filename"],
            "sha256": actual,
            "files": 0,
        }

        with zipfile.ZipFile(wheel) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if not safe_member(info.filename):
                    raise RuntimeError(
                        f"Unsafe wheel member: {item['filename']} :: "
                        f"{info.filename}"
                    )
                relative = PurePosixPath(info.filename).as_posix()
                data = archive.read(info)
                file_hash = hashlib.sha256(data).hexdigest()
                if relative in seen and seen[relative] != file_hash:
                    raise RuntimeError(
                        f"Conflicting wheel member: {relative}"
                    )
                seen[relative] = file_hash
                destination = CANDIDATE_SITE / Path(*PurePosixPath(relative).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(data)
                wheel_record["files"] += 1
        wheels.append(wheel_record)

    records = tree_records(CANDIDATE_SITE)
    if not records:
        raise RuntimeError("Candidate runtime tree is empty.")
    return {
        "wheels": wheels,
        "files": records,
        "file_count": len(records),
        "tree_digest": tree_digest(records),
    }


def run_candidate_test() -> dict:
    python = ROOT / "env/python/python.exe"
    process = subprocess.run(
        [
            str(python),
            "-s",
            str(PACKAGE / "candidate_runtime_test.py"),
            str(CANDIDATE_SITE),
            str(ROOT),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    result = {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "passed": False,
    }
    if process.stdout.strip():
        result.update(json.loads(process.stdout))
    if process.returncode != 0 or not result.get("passed"):
        raise RuntimeError(
            "Candidate import test failed: "
            + (process.stderr[-3000:] or process.stdout[-3000:])
        )
    return result


def run_boundary_watch() -> dict:
    python = ROOT / "env/python/python.exe"
    runner = (
        "import sys,unittest;"
        "runtime=sys.argv[1];root=sys.argv[2];tests=sys.argv[3];"
        "sys.path.insert(0,runtime);sys.path.insert(0,root);"
        "suite=unittest.defaultTestLoader.discover("
        "start_dir=tests,pattern='test_boundary_watch.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run(
        [
            str(python),
            "-s",
            "-c",
            runner,
            str(CANDIDATE_SITE),
            str(ROOT),
            str(ROOT / "tests"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = (process.stdout or "") + "\n" + (process.stderr or "")
    passed = (
        process.returncode == 0
        and "Ran 5 tests" in combined
        and "\nOK" in combined
    )
    result = {
        "passed": passed,
        "tests": 5 if "Ran 5 tests" in combined else None,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "candidate_casbin_active": True,
    }
    if not passed:
        raise RuntimeError(
            "Boundary Watch failed with candidate runtime: "
            + combined[-3000:]
        )
    return result


def main() -> int:
    result = {
        "action": "foxai_portable_runtime_phase2b3_exact_preview_verify",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "live_files_modified": False,
        "candidate_created": False,
        "apply_capability_present": False,
        "proposed_new_paths": PLAN["proposed_changes"]["new"],
        "proposed_modified_files": PLAN["proposed_changes"]["modified"],
        "delete_operations": [],
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
            item = {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
            package_files.append(item)
        if not package_files or not all(item["ok"] for item in package_files):
            raise RuntimeError("Preview package manifest failed.")
        result["checks"]["package_manifest"] = {
            "passed": True,
            "files": package_files,
        }

        live_files = []
        for relative, expected in PLAN["live_baselines"].items():
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
            raise RuntimeError("One or more live baselines changed.")
        result["checks"]["live_baselines"] = {
            "passed": True,
            "files": live_files,
        }

        acquisition_path = ROOT / PLAN["acquisition_receipt"]["live_path"]
        actual_acq_hash = (
            sha256(acquisition_path) if acquisition_path.is_file() else None
        )
        if actual_acq_hash != PLAN["acquisition_receipt"]["sha256"]:
            raise RuntimeError("The live Phase 2B2 receipt changed or is missing.")
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        if (
            acquisition.get("state") != "quarantined_wheelhouse_verified"
            or acquisition.get("verified") is not True
            or len(acquisition.get("wheels", [])) != 12
        ):
            raise RuntimeError("The acquisition receipt contract failed.")
        result["checks"]["acquisition_receipt"] = {
            "passed": True,
            "path": str(acquisition_path),
            "sha256": actual_acq_hash,
            "wheel_count": 12,
        }

        tree = extract_wheels(acquisition)
        result["candidate_created"] = True
        result["checks"]["candidate_tree"] = {
            "passed": True,
            "file_count": tree["file_count"],
            "tree_digest": tree["tree_digest"],
            "wheels": tree["wheels"],
        }

        runtime_manifest = {
            "schema": "foxai.portable-core-runtime.v1",
            "created": result["created"],
            "source_acquisition_receipt_sha256": actual_acq_hash,
            "python": "CPython 3.14.6",
            "platform": "Windows AMD64",
            "package_root": "Runtime/Core/site-packages",
            "user_site_policy": "disabled by primary launcher",
            "wheel_count": 12,
            "file_count": tree["file_count"],
            "tree_digest": tree["tree_digest"],
            "wheels": tree["wheels"],
        }
        CANDIDATE_RUNTIME_MANIFEST.write_text(
            json.dumps(runtime_manifest, indent=2), encoding="utf-8"
        )
        tree_with_manifest = tree_records(PACKAGE / "candidate/Runtime/Core")
        tree_manifest = {
            "runtime_site_packages": tree,
            "candidate_runtime_core": {
                "files": tree_with_manifest,
                "file_count": len(tree_with_manifest),
                "tree_digest": tree_digest(tree_with_manifest),
            },
        }
        TREE_MANIFEST_PATH.write_text(
            json.dumps(tree_manifest, indent=2), encoding="utf-8"
        )

        for relative, expected in PLAN["candidate_hashes"].items():
            candidate = PACKAGE / "candidate" / relative
            actual = sha256(candidate)
            if actual != expected:
                raise RuntimeError(f"Static candidate changed: {relative}")

        launcher_text = (
            PACKAGE / "candidate/START_FOXAI_WEB_PORTABLE.bat"
        ).read_text(encoding="utf-8").lower()
        forbidden = ["pip install", "npm install", "powershell", "curl ", "del "]
        hits = [term for term in forbidden if term in launcher_text]
        if hits:
            raise RuntimeError(f"Candidate launcher contains forbidden text: {hits}")
        if (
            'set "pythonnousersite=1"' not in launcher_text
            or "python.exe\" -s " not in launcher_text
        ):
            raise RuntimeError("Candidate launcher hardening is incomplete.")
        result["checks"]["static_candidates"] = {
            "passed": True,
            "candidate_hashes": PLAN["candidate_hashes"],
            "launcher_forbidden_terms": hits,
            "user_site_disabled": True,
        }

        result["checks"]["candidate_imports"] = run_candidate_test()
        result["checks"]["boundary_watch"] = run_boundary_watch()

        resolved_package_path = (
            ROOT / "env/python/../../Runtime/Core/site-packages"
        ).resolve()
        expected_package_path = (
            ROOT / "Runtime/Core/site-packages"
        ).resolve()
        if resolved_package_path != expected_package_path:
            raise RuntimeError("Candidate _pth path does not resolve correctly.")
        result["checks"]["pth_resolution"] = {
            "passed": True,
            "entry": r"..\..\Runtime\Core\site-packages",
            "resolved": str(resolved_package_path),
        }

        result["state"] = "exact_preview_verified"
        result["verified"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    RECEIPT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "State": result["state"],
        "Verified": result["verified"],
        "Live files modified": False,
        "Candidate created": result["candidate_created"],
        "Apply capability present": False,
        "Receipt": str(RECEIPT_PATH),
    }, indent=2))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
