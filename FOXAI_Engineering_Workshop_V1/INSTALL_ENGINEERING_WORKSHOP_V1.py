from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent / "Engineering"
CHANGED_FILES = [
    "__init__.py",
    "README.md",
    "WORKSHOP_GUIDE.md",
    "manifest.json",
    "officer.py",
    "services.py",
    "health.py",
    "models.py",
    "policy.py",
    "mission_router.py",
    "mission_state.py",
    "source_locator.py",
    "evidence.py",
    "snapshot.py",
    "patch_engine.py",
    "validator.py",
    "workshop.py",
    "cli.py",
    "RUN_ENGINEERING_WORKSHOP.bat",
    "RUN_WORKSHOP_TESTS.bat",
    "tests/__init__.py",
    "tests/test_workshop.py",
    "examples/PLAN_TEMPLATE.json",
    "examples/fixture_project/app.py",
    "examples/fixture_project/test_app.py",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_within(path: Path, root: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise RuntimeError(f"Path escapes target root: {path}") from exc


def choose_python(foxai_root: Path) -> Path:
    portable = foxai_root / "Runtime" / "Desktop" / "python" / "python.exe"
    return portable if portable.exists() else Path(sys.executable)


def create_backup(target: Path, backup_root: Path) -> tuple[Path, dict]:
    stamp = utc_stamp()
    backup_dir = backup_root / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    zip_path = backup_dir / "engineering_before_workshop_v1.zip"
    entries = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in CHANGED_FILES:
            source = target / rel
            ensure_within(source, target)
            if source.exists() and source.is_file():
                archive.write(source, arcname=f"files/{rel}")
                entries.append({"path": rel, "existed": True, "sha256": sha256(source), "size": source.stat().st_size})
            else:
                entries.append({"path": rel, "existed": False, "sha256": None, "size": None})
        archive.writestr("manifest.json", json.dumps({"target": str(target), "entries": entries}, indent=2))
    receipt = {
        "created_at": stamp,
        "target": str(target),
        "backup_zip": str(zip_path),
        "backup_sha256": sha256(zip_path),
        "entries": entries,
    }
    (backup_dir / "backup_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return zip_path, receipt


def restore_backup(zip_path: Path, target: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        for entry in manifest["entries"]:
            rel = entry["path"]
            destination = target / rel
            ensure_within(destination, target)
            if entry["existed"]:
                data = archive.read(f"files/{rel}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                temp = destination.with_name(destination.name + ".install-restore.tmp")
                temp.write_bytes(data)
                os.replace(temp, destination)
            else:
                destination.unlink(missing_ok=True)


def copy_package(target: Path) -> list[dict]:
    changes = []
    for rel in CHANGED_FILES:
        source = PACKAGE_DIR / rel
        destination = target / rel
        ensure_within(destination, target)
        if not source.exists():
            raise RuntimeError(f"Package file is missing: {source}")
        before = sha256(destination) if destination.exists() and destination.is_file() else None
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent, prefix=destination.name, suffix=".tmp") as handle:
            temp = Path(handle.name)
            handle.write(source.read_bytes())
        os.replace(temp, destination)
        changes.append({"path": rel, "before_sha256": before, "after_sha256": sha256(destination)})
    return changes


def run_tests(foxai_root: Path, python_exe: Path) -> dict:
    test_dir = str(Path("Departments") / "Engineering" / "tests")
    command = [str(python_exe), "-m", "unittest", "discover", "-s", test_dir, "-v"]
    completed = subprocess.run(command, cwd=foxai_root, capture_output=True, text=True, timeout=180, shell=False)
    return {
        "argv": command,
        "cwd": str(foxai_root),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install FOXAI Engineering Workshop V1")
    parser.add_argument("--foxai-root", default=r"Z:\FOXAI")
    parser.add_argument("--target", help="Override Engineering department target")
    parser.add_argument("--approve", action="store_true", help="Apply after displaying exact target and backup location")
    args = parser.parse_args()

    foxai_root = Path(args.foxai_root).expanduser().resolve(strict=False)
    target = Path(args.target).expanduser().resolve(strict=False) if args.target else foxai_root / "Departments" / "Engineering"
    backup_root = foxai_root / "System" / "EngineeringWorkshop" / "InstallBackups"

    print(json.dumps({
        "package": str(PACKAGE_DIR),
        "target": str(target),
        "backup_root": str(backup_root),
        "files_to_add_or_replace": CHANGED_FILES,
        "deletions": 0,
        "network": False,
        "packages_installed": False,
        "approved": args.approve,
    }, indent=2))

    if not args.approve:
        print("Preview only. Re-run with --approve to install.")
        return 0
    if not PACKAGE_DIR.exists():
        raise RuntimeError(f"Package directory missing: {PACKAGE_DIR}")
    if not target.exists() or not target.is_dir():
        raise RuntimeError(f"Existing Engineering department not found: {target}")

    backup_zip, backup_receipt = create_backup(target, backup_root)
    changes = []
    test_result = None
    result = "failed_rolled_back"
    error = None
    try:
        changes = copy_package(target)
        test_result = run_tests(foxai_root, choose_python(foxai_root))
        if test_result["returncode"] != 0:
            raise RuntimeError("Workshop tests failed after installation")
        result = "installed_verified"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        restore_backup(backup_zip, target)

    receipt = {
        "schema": "foxai.engineering.workshop.install-receipt.v1",
        "result": result,
        "timestamp": utc_stamp(),
        "foxai_root": str(foxai_root),
        "target": str(target),
        "backup": backup_receipt,
        "changes": changes,
        "test": test_result,
        "error": error,
        "deletions": 0,
        "network_used": False,
        "packages_installed": False,
    }
    receipt_path = backup_zip.parent / "install_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({**receipt, "receipt_path": str(receipt_path)}, indent=2))
    return 0 if result == "installed_verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
