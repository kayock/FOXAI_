from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone

APPROVAL_PHRASE = "ROLLBACK USB COMMISSIONING PHASE 1"
EXPECTED_CANDIDATE = {
    "COMMISSION_FOXAI_USB.bat": "3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b",
    "System/Commissioning/commission_usb.py": "cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869",
    "00_START_HERE/USB_COMMISSIONING_GUIDE.md": "bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def find_root(package: Path) -> Path:
    for candidate in (package.parent, *package.parents):
        if (candidate / "core/foxai_web.py").is_file() and (candidate / "Config/FoxAI.ini").is_file():
            return candidate
    raise RuntimeError("FOXAI root not found.")


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp.{os.getpid()}")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    states = {}
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        states[relative] = {"actual": actual, "expected": expected, "ok": actual == expected}
    if not all(item["ok"] for item in states.values()):
        print("Rollback stopped fail-closed: installed files are missing or changed.")
        return 2
    print("\nThis removes only the three exact Phase 1 commissioning files.")
    print("Type the exact rollback phrase:")
    if input("> ").strip() != APPROVAL_PHRASE:
        print("Rollback cancelled. Nothing changed.")
        return 2
    stamp = utc_stamp()
    backup = root / "Backups/SecurityMilestone" / f"USBC1_ROLLBACK_{stamp}"
    report = root / "Reports/Commissioning" / f"USBC1_ROLLBACK_{stamp}"
    backup.mkdir(parents=True)
    report.mkdir(parents=True)
    for relative in EXPECTED_CANDIDATE:
        source = root / relative
        destination = backup / "removed" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    removed = []
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = root / relative
        if path.is_file() and sha256(path) == expected:
            path.unlink()
            removed.append(relative)
    verified = all(not (root / relative).exists() for relative in EXPECTED_CANDIDATE)
    receipt = {
        "action": "foxai_usb_commissioning_phase1_rollback",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "rollback_verified" if verified else "rollback_incomplete",
        "verified": verified,
        "removed_files": removed,
        "backup_folder": str(backup),
        "existing_protected_files_modified": False,
    }
    write_json_atomic(backup / "ROLLBACK_RECEIPT.json", receipt)
    write_json_atomic(report / "ROLLBACK_RECEIPT.json", receipt)
    print("State:", receipt["state"])
    print("Removed files:", len(removed))
    print("Backup:", backup)
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
