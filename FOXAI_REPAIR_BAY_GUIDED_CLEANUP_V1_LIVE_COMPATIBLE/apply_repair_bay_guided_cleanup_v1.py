from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import tempfile


SOURCE_SHA256 = "8f272017d83c054a480fcb960f263c56ba53b75414588ebd680b5cd2f3da83dc"
PATCHED_SHA256 = "3d50f594191a130d7c816d7a8fc4defa434dba467cf79f8384ceadb6988f284b"
PATCH_ID = "foxai.repair_bay.guided_cleanup.v1"

REQUIRED_MARKERS = (
    "REPAIR_BAY_GUIDED_CLEANUP_V1_START",
    "REPAIR_BAY_GUIDED_CLEANUP_V1_BROWSER_START",
    "function openGuidedEngineer()",
    "function renderRepairGuidedStatus(s)",
    "Engineering Advanced Tools",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compile_candidate(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="foxai_repair_cleanup_") as temp:
        output = Path(temp) / "foxai_web.pyc"
        py_compile.compile(str(path), cfile=str(output), doraise=True)


def write_receipt(root: Path, action: str, details: dict) -> Path:
    report_dir = (
        root
        / "Reports"
        / "RepairBay"
        / "GuidedCleanupV1"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = report_dir / f"{stamp}_{action}_receipt.json"
    receipt = {
        "schema": "foxai.patch.receipt.v1",
        "patch_id": PATCH_ID,
        "action": action,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "verified": True,
        "network_used": False,
        "details": details,
    }
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def apply_patch(root: Path, package_dir: Path) -> int:
    target = root / "core" / "foxai_web.py"
    payload = package_dir / "payload" / "foxai_web.py"

    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        return 2
    if not target.is_file():
        print("ERROR: Live WebUI file is missing:", target)
        return 3
    if not payload.is_file():
        print("ERROR: Patch payload is missing:", payload)
        return 4

    payload_hash = sha256_file(payload)
    if payload_hash != PATCHED_SHA256:
        print("ERROR: Payload identity check failed.")
        print("Expected:", PATCHED_SHA256)
        print("Actual:  ", payload_hash)
        return 5

    payload_text = payload.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in payload_text]
    if missing:
        print("ERROR: Payload marker check failed:", ", ".join(missing))
        return 6

    compile_candidate(payload)

    live_hash = sha256_file(target)
    if live_hash == PATCHED_SHA256:
        print("Repair Bay Guided Cleanup V1 is already installed.")
        print("Live SHA-256:", live_hash)
        return 0
    if live_hash != SOURCE_SHA256:
        print("ERROR: Live WebUI does not match the reviewed source.")
        print("Nothing was changed.")
        print("Expected source SHA-256:", SOURCE_SHA256)
        print("Actual live SHA-256:   ", live_hash)
        return 7

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = (
        root
        / "Backups"
        / "RepairBay"
        / "GuidedCleanupV1"
        / stamp
    )
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / "foxai_web.py"
    shutil.copy2(target, backup)

    if sha256_file(backup) != SOURCE_SHA256:
        print("ERROR: Backup verification failed. Nothing was replaced.")
        return 8

    temporary = target.with_name("foxai_web.py.repair_guided_v1.tmp")
    shutil.copy2(payload, temporary)

    try:
        if sha256_file(temporary) != PATCHED_SHA256:
            raise RuntimeError("Temporary payload verification failed.")
        compile_candidate(temporary)
        os.replace(temporary, target)

        final_hash = sha256_file(target)
        if final_hash != PATCHED_SHA256:
            raise RuntimeError("Post-install hash verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, target)
        print("ERROR:", exc)
        print("The verified backup was restored.")
        return 9

    receipt = write_receipt(
        root,
        "apply",
        {
            "target": str(target),
            "source_sha256": SOURCE_SHA256,
            "patched_sha256": PATCHED_SHA256,
            "backup": str(backup),
            "source_files_modified": 1,
            "source_files_deleted": 0,
            "saved_projects_modified": False,
            "features": [
                "Task-first Repair Bay home",
                "Read-only-first Engineer launcher",
                "Visible four-step repair safety path",
                "Compact live readiness status",
                "Primary Engineering and Repair navigation reduced",
                "Technical pages preserved under Engineering Advanced Tools",
                "Existing approvals, backups, verification, and receipts preserved",
            ],
        },
    )

    print()
    print("=" * 72)
    print("REPAIR BAY GUIDED CLEANUP V1 INSTALLED")
    print("=" * 72)
    print("Target:", target)
    print("Backup:", backup)
    print("Receipt:", receipt)
    print("SHA-256:", PATCHED_SHA256)
    print()
    print("Restart FOXAI WebUI and open Repair Bay.")
    return 0


def rollback_patch(root: Path) -> int:
    target = root / "core" / "foxai_web.py"
    backup_base = (
        root
        / "Backups"
        / "RepairBay"
        / "GuidedCleanupV1"
    )

    if not target.is_file():
        print("ERROR: Live WebUI file is missing:", target)
        return 20

    live_hash = sha256_file(target)
    if live_hash == SOURCE_SHA256:
        print("The reviewed pre-cleanup WebUI is already active.")
        return 0
    if live_hash != PATCHED_SHA256:
        print("ERROR: The live WebUI has changed since this cleanup.")
        print("Rollback stopped to protect newer work.")
        print("Actual live SHA-256:", live_hash)
        return 21

    backups = sorted(
        (
            path for path in backup_base.glob("*/foxai_web.py")
            if path.is_file() and sha256_file(path) == SOURCE_SHA256
        ),
        key=lambda item: item.parent.name,
        reverse=True,
    )
    if not backups:
        print("ERROR: No verified Guided Cleanup V1 backup was found.")
        return 22

    backup = backups[0]
    compile_candidate(backup)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    preserve_dir = (
        root
        / "Backups"
        / "RepairBay"
        / "GuidedCleanupV1Rollback"
        / stamp
    )
    preserve_dir.mkdir(parents=True, exist_ok=False)
    guided_copy = preserve_dir / "foxai_web_repair_guided_v1.py"
    shutil.copy2(target, guided_copy)

    temporary = target.with_name("foxai_web.py.repair_guided_rollback.tmp")
    shutil.copy2(backup, temporary)

    try:
        if sha256_file(temporary) != SOURCE_SHA256:
            raise RuntimeError("Rollback source verification failed.")
        os.replace(temporary, target)
        if sha256_file(target) != SOURCE_SHA256:
            raise RuntimeError("Rollback post-write verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(guided_copy, target)
        print("ERROR:", exc)
        print("The Guided V1 WebUI was restored.")
        return 23

    receipt = write_receipt(
        root,
        "rollback",
        {
            "target": str(target),
            "restored_sha256": SOURCE_SHA256,
            "restored_from": str(backup),
            "guided_copy_preserved": str(guided_copy),
        },
    )

    print()
    print("Repair Bay Guided Cleanup V1 was rolled back safely.")
    print("Restored:", target)
    print("Receipt:", receipt)
    print("Restart FOXAI WebUI.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--action",
        choices=("apply", "rollback"),
        default="apply",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    package_dir = Path(__file__).resolve().parent

    if args.action == "rollback":
        return rollback_patch(root)
    return apply_patch(root, package_dir)


if __name__ == "__main__":
    raise SystemExit(main())
