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


SOURCE_SHA256 = "3d50f594191a130d7c816d7a8fc4defa434dba467cf79f8384ceadb6988f284b"
PATCHED_SHA256 = "5601b36cd49d213d367954b9ff5e1456fb3c41b5eabe0b7e1ba56364e8ecec65"
BROKEN = "};renderRepairGuidedStatus(s)\n\nasync function refreshComfyOperations()"
FIXED = ";renderRepairGuidedStatus(s)}\n\nasync function refreshComfyOperations()"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compile_file(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="foxai_repair_v1_2_") as temp:
        py_compile.compile(
            str(path),
            cfile=str(Path(temp) / "foxai_web.pyc"),
            doraise=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    target = root / "core" / "foxai_web.py"

    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        return 2
    if not target.is_file():
        print("ERROR: Live WebUI file is missing:", target)
        return 3

    live_hash = sha256_file(target)
    print("Live file:", target)
    print("Before SHA-256:", live_hash)

    if live_hash == PATCHED_SHA256:
        print("Repair Bay V1.2 direct fix is already installed.")
        return 0
    if live_hash != SOURCE_SHA256:
        print("ERROR: Live file does not match the exact broken V1 build.")
        print("Nothing was changed.")
        print("Expected:", SOURCE_SHA256)
        print("Actual:  ", live_hash)
        return 4

    original = target.read_text(encoding="utf-8")
    count = original.count(BROKEN)
    if count != 1:
        print("ERROR: Expected exactly one misplaced status call.")
        print("Found:", count)
        print("Nothing was changed.")
        return 5

    patched = original.replace(BROKEN, FIXED, 1)
    patched_bytes = patched.encode("utf-8")
    calculated = sha256_bytes(patched_bytes)

    if calculated != PATCHED_SHA256:
        print("ERROR: Patched content hash did not match the reviewed result.")
        print("Expected:", PATCHED_SHA256)
        print("Actual:  ", calculated)
        return 6

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = (
        root
        / "Backups"
        / "RepairBay"
        / "DirectOneLineFixV1_2"
        / stamp
    )
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / "foxai_web.py"
    shutil.copy2(target, backup)

    if sha256_file(backup) != SOURCE_SHA256:
        print("ERROR: Backup verification failed.")
        return 7

    temporary = target.with_name("foxai_web.py.repair_v1_2.tmp")
    temporary.write_bytes(patched_bytes)

    try:
        compile_file(temporary)
        if sha256_file(temporary) != PATCHED_SHA256:
            raise RuntimeError("Temporary file hash verification failed.")
        os.replace(temporary, target)
        final_hash = sha256_file(target)
        if final_hash != PATCHED_SHA256:
            raise RuntimeError("Final live hash verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, target)
        print("ERROR:", exc)
        print("The verified backup was restored.")
        return 8

    receipt_dir = root / "Reports" / "RepairBay" / "DirectOneLineFixV1_2"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / f"{stamp}_apply_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": "foxai.patch.receipt.v1",
                "patch_id": "foxai.repair_bay.v1.2.direct_one_line_fix",
                "created": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
                "verified": True,
                "network_used": False,
                "target": str(target),
                "backup": str(backup),
                "before_sha256": SOURCE_SHA256,
                "after_sha256": PATCHED_SHA256,
                "changes": [
                    "Moved renderRepairGuidedStatus(s) inside refresh()."
                ],
                "source_files_modified": 1,
                "source_files_deleted": 0,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("REPAIR BAY V1.2 DIRECT FIX INSTALLED")
    print("=" * 72)
    print("After SHA-256:", sha256_file(target))
    print("Backup:", backup)
    print("Receipt:", receipt)
    print()
    print("Restart FOXAI WebUI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
