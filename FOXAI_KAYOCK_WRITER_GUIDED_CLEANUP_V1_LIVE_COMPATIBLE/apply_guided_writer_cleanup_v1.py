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


SOURCE_SHA256 = "e939e9a43b1705f3b1fa28e294d77261429d7dbecc516cae469a203bcebac296"
PATCHED_SHA256 = "8f272017d83c054a480fcb960f263c56ba53b75414588ebd680b5cd2f3da83dc"
PATCH_ID = "foxai.kayock_writer.guided_cleanup.v1"
REQUIRED_MARKERS = (
    "KAYOCK_WRITER_GUIDED_CLEANUP_V1_START",
    "KAYOCK_WRITER_GUIDED_CLEANUP_V1_BROWSER_START",
    "function startStoryWriterTask(task)",
    "function openPoemPolisherFromWriterHome()",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compile_candidate(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="foxai_writer_check_") as temp:
        output = Path(temp) / "foxai_web.pyc"
        py_compile.compile(str(path), cfile=str(output), doraise=True)


def write_receipt(root: Path, action: str, details: dict) -> Path:
    report_dir = (
        root
        / "Reports"
        / "KayockWriter"
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
    missing_markers = [
        marker for marker in REQUIRED_MARKERS
        if marker not in payload_text
    ]
    if missing_markers:
        print("ERROR: Payload marker check failed:", ", ".join(missing_markers))
        return 6

    compile_candidate(payload)

    live_hash = sha256_file(target)
    if live_hash == PATCHED_SHA256:
        print("Guided Writer Cleanup V1 is already installed.")
        print("Live SHA-256:", live_hash)
        return 0
    if live_hash != SOURCE_SHA256:
        print("ERROR: Live file does not match the reviewed source.")
        print("Nothing was changed.")
        print("Expected source SHA-256:", SOURCE_SHA256)
        print("Actual live SHA-256:   ", live_hash)
        return 7

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = (
        root
        / "Backups"
        / "KayockWriter"
        / "GuidedCleanupV1"
        / stamp
    )
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / "foxai_web.py"
    shutil.copy2(target, backup)

    if sha256_file(backup) != SOURCE_SHA256:
        print("ERROR: Backup verification failed. Nothing was replaced.")
        return 8

    temporary = target.with_name("foxai_web.py.guided_cleanup_v1.tmp")
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
            "features": [
                "Task-first Kayock Writer home",
                "Guided Story Forge home",
                "Progressive-disclosure Poetry Studio controls",
                "Existing poetry tools preserved",
                "Existing Story Forge reports preserved under Advanced Tools",
            ],
        },
    )

    print()
    print("=" * 70)
    print("KAYOCK WRITER GUIDED CLEANUP V1 INSTALLED")
    print("=" * 70)
    print("Target:", target)
    print("Backup:", backup)
    print("Receipt:", receipt)
    print("SHA-256:", PATCHED_SHA256)
    print()
    print("Restart FOXAI WebUI to load the new interface.")
    return 0


def rollback_patch(root: Path) -> int:
    target = root / "core" / "foxai_web.py"
    backup_base = (
        root
        / "Backups"
        / "KayockWriter"
        / "GuidedCleanupV1"
    )

    if not target.is_file():
        print("ERROR: Live WebUI file is missing:", target)
        return 20

    live_hash = sha256_file(target)
    if live_hash == SOURCE_SHA256:
        print("The reviewed pre-cleanup version is already active.")
        return 0
    if live_hash != PATCHED_SHA256:
        print("ERROR: The live file has changed since this patch.")
        print("Rollback stopped to avoid overwriting newer work.")
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
        print("ERROR: No verified cleanup backup was found.")
        return 22

    backup = backups[0]
    compile_candidate(backup)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    rollback_backup_dir = (
        root
        / "Backups"
        / "KayockWriter"
        / "GuidedCleanupV1Rollback"
        / stamp
    )
    rollback_backup_dir.mkdir(parents=True, exist_ok=False)
    current_copy = rollback_backup_dir / "foxai_web_guided_v1.py"
    shutil.copy2(target, current_copy)

    temporary = target.with_name("foxai_web.py.guided_cleanup_rollback.tmp")
    shutil.copy2(backup, temporary)
    try:
        if sha256_file(temporary) != SOURCE_SHA256:
            raise RuntimeError("Rollback source verification failed.")
        os.replace(temporary, target)
        if sha256_file(target) != SOURCE_SHA256:
            raise RuntimeError("Rollback post-write verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(current_copy, target)
        print("ERROR:", exc)
        print("The Guided V1 file was restored.")
        return 23

    receipt = write_receipt(
        root,
        "rollback",
        {
            "target": str(target),
            "restored_sha256": SOURCE_SHA256,
            "restored_from": str(backup),
            "guided_copy_preserved": str(current_copy),
        },
    )

    print()
    print("Guided Writer Cleanup V1 was rolled back safely.")
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
