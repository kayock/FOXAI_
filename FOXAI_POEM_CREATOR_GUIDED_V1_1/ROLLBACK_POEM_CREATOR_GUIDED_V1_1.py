from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BUILD_ID = "FOXAI_POEM_CREATOR_GUIDED_V1_1"
EXPECTED_PAYLOAD_SHA256 = "229d45ac0b7b10182bd4b6a45faf7e09deb8bd56e2da8ed002b8e502d762e086"
EXPECTED_BASELINE_SHA256 = "0b20128bb67aa757e03162612a97b99383b41d0a3ce7a4eb35a493f26bcc1d48"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_target(argument: str | None) -> Path:
    if argument:
        candidate = Path(argument).expanduser()
        if candidate.is_dir() or candidate.suffix.lower() != ".py":
            candidate = candidate / "core" / "foxai_web.py"
        return candidate
    env_root = os.environ.get("FOXAI_ROOT", "").strip()
    if env_root:
        return Path(env_root) / "core" / "foxai_web.py"
    return Path(r"Z:\FOXAI\core\foxai_web.py")


def verify_python_source(path: Path) -> None:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def main() -> int:
    target = resolve_target(sys.argv[1] if len(sys.argv) > 1 else None)
    print("ROLLBACK " + BUILD_ID)
    print(f"Target: {target}")

    if not target.is_file():
        print("ERROR: Target file not found. No changes made.")
        return 2

    current_hash = sha256_file(target)
    if current_hash == EXPECTED_BASELINE_SHA256:
        print("ALREADY ROLLED BACK: Target matches the uploaded baseline.")
        return 0
    if current_hash != EXPECTED_PAYLOAD_SHA256:
        print("BLOCKED: The current file is not the installed V1.1 payload.")
        print("This prevents erasing work added after this build.")
        print(f"Current SHA-256: {current_hash}")
        print("No changes made.")
        return 3

    root = target.parent.parent
    backup_dir = (
        root
        / "Backups"
        / "KayockWriter"
        / "PoetryStudio"
        / "PoemCreatorGuidedV1_1"
    )
    backups = sorted(
        backup_dir.glob("foxai_web_before_POEM_CREATOR_GUIDED_V1_1_*.py"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        print("ERROR: No verified pre-install backup was found. No changes made.")
        return 4

    backup = backups[0]
    verify_python_source(backup)
    backup_hash = sha256_file(backup)
    if backup_hash != EXPECTED_BASELINE_SHA256:
        print("ERROR: Latest backup does not match the expected baseline. No changes made.")
        return 4

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_copy = backup_dir / f"foxai_web_before_rollback_{stamp}.py"
    shutil.copy2(target, safety_copy)

    temp = target.with_name(target.name + ".poem_creator_guided_v1_1_rollback.tmp")
    shutil.copy2(backup, temp)
    verify_python_source(temp)
    os.replace(temp, target)
    verify_python_source(target)
    after_hash = sha256_file(target)
    if after_hash != EXPECTED_BASELINE_SHA256:
        print("ERROR: Rollback verification failed.")
        return 5

    receipt_dir = (
        root
        / "Reports"
        / "KayockWriter"
        / "PoetryStudio"
        / "PoemCreatorGuidedV1_1"
    )
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "build_id": BUILD_ID,
        "status": "rollback_verified",
        "time": datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "before_sha256": current_hash,
        "after_sha256": after_hash,
        "restored_from": str(backup),
        "safety_copy_of_removed_build": str(safety_copy),
        "existing_poem_files_modified": False,
    }
    receipt_path = receipt_dir / f"Poem_Creator_Guided_V1_1_ROLLBACK_{stamp}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print("ROLLBACK VERIFIED")
    print(f"Restored: {backup}")
    print(f"Receipt: {receipt_path}")
    print("Restart FOXAI WebUI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
