from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BUILD_ID = "FOXAI_POEM_CREATOR_GUIDED_V1_1"
EXPECTED_BASELINE_SHA256 = "0b20128bb67aa757e03162612a97b99383b41d0a3ce7a4eb35a493f26bcc1d48"
EXPECTED_PAYLOAD_SHA256 = "229d45ac0b7b10182bd4b6a45faf7e09deb8bd56e2da8ed002b8e502d762e086"


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
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    required = (
        "FOXAI_POEM_CREATOR_GUIDED_V1_1_STYLE_START",
        "FOXAI_POEM_CREATOR_GUIDED_V1_1_HTML_START",
        "FOXAI_POEM_CREATOR_GUIDED_V1_1_JS_START",
        "FOXAI_POEM_CREATOR_GUIDED_V1_1_BACKEND_START",
        "FOXAI_POEM_CREATOR_GUIDED_V1_1_STORAGE_START",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise RuntimeError("Payload is missing build markers: " + ", ".join(missing))


def write_receipt(root: Path, receipt: dict) -> tuple[Path, Path]:
    folder = (
        root
        / "Reports"
        / "KayockWriter"
        / "PoetryStudio"
        / "PoemCreatorGuidedV1_1"
    )
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = folder / f"Poem_Creator_Guided_V1_1_{stamp}.json"
    txt_path = folder / f"Poem_Creator_Guided_V1_1_{stamp}.txt"
    json_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    lines = [
        BUILD_ID,
        "",
        f"Status: {receipt.get('status')}",
        f"Time: {receipt.get('time')}",
        f"Target: {receipt.get('target')}",
        f"Before SHA-256: {receipt.get('before_sha256')}",
        f"After SHA-256: {receipt.get('after_sha256')}",
        f"Backup: {receipt.get('backup')}",
        "",
        "Scope: one file only — core\\foxai_web.py",
        "Existing poem Markdown files were not opened, changed, moved, or deleted.",
        "Restart FOXAI WebUI before testing the new Poetry Studio page.",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, txt_path


def main() -> int:
    package_root = Path(__file__).resolve().parent
    payload = package_root / "payload" / "core" / "foxai_web.py"
    target = resolve_target(sys.argv[1] if len(sys.argv) > 1 else None)

    print(f"{BUILD_ID}")
    print(f"Target: {target}")
    print("Mode: exact baseline check, backup, one-file replacement, verification")

    if not payload.is_file():
        print("ERROR: Package payload is missing. No changes made.")
        return 2
    verify_python_source(payload)
    payload_hash = sha256_file(payload)
    if payload_hash != EXPECTED_PAYLOAD_SHA256:
        print("ERROR: Payload SHA-256 does not match the packaged value. No changes made.")
        return 2

    if not target.is_file():
        print("ERROR: FOXAI target file was not found.")
        print(r"Expected default: Z:\FOXAI\core\foxai_web.py")
        print("You may pass the FOXAI root folder or the full foxai_web.py path.")
        print("No changes made.")
        return 2

    current_hash = sha256_file(target)
    if current_hash == EXPECTED_PAYLOAD_SHA256:
        verify_python_source(target)
        print("ALREADY INSTALLED: The target already matches this build.")
        return 0

    if current_hash != EXPECTED_BASELINE_SHA256:
        print("BLOCKED: The live file does not match the uploaded known-good baseline.")
        print(f"Expected: {EXPECTED_BASELINE_SHA256}")
        print(f"Found:    {current_hash}")
        print("No changes were made. This prevents overwriting newer or different work.")
        return 3

    root = target.parent.parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = (
        root
        / "Backups"
        / "KayockWriter"
        / "PoetryStudio"
        / "PoemCreatorGuidedV1_1"
    )
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"foxai_web_before_POEM_CREATOR_GUIDED_V1_1_{stamp}.py"
    shutil.copy2(target, backup)
    if sha256_file(backup) != current_hash:
        print("ERROR: Backup verification failed. No live replacement attempted.")
        return 4

    temp = target.with_name(target.name + ".poem_creator_guided_v1_1.tmp")
    if temp.exists():
        temp.unlink()
    shutil.copy2(payload, temp)
    verify_python_source(temp)

    replaced = False
    try:
        os.replace(temp, target)
        replaced = True
        verify_python_source(target)
        after_hash = sha256_file(target)
        if after_hash != EXPECTED_PAYLOAD_SHA256:
            raise RuntimeError("Installed target SHA-256 did not match the payload.")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        if temp.exists():
            temp.unlink()
        if replaced:
            rollback_temp = target.with_name(target.name + ".rollback.tmp")
            shutil.copy2(backup, rollback_temp)
            verify_python_source(rollback_temp)
            os.replace(rollback_temp, target)
            print("The verified backup was restored.")
        else:
            print("The live file was not replaced.")
        return 5

    receipt = {
        "build_id": BUILD_ID,
        "status": "installed_verified",
        "time": datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "before_sha256": current_hash,
        "after_sha256": after_hash,
        "expected_payload_sha256": EXPECTED_PAYLOAD_SHA256,
        "backup": str(backup),
        "scope": ["core/foxai_web.py"],
        "existing_poem_files_modified": False,
        "poetry_archive_modified": False,
        "repair_bay_modified": False,
        "bibliotheca_modified": False,
        "runtime_modified": False,
        "restart_required": True,
    }
    receipt_json, receipt_text = write_receipt(root, receipt)

    print("")
    print("INSTALLED AND VERIFIED")
    print(f"Backup: {backup}")
    print(f"Receipt: {receipt_text}")
    print(f"JSON receipt: {receipt_json}")
    print("")
    print("Restart FOXAI WebUI, open Poetry Studio, and test Poem Creator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
