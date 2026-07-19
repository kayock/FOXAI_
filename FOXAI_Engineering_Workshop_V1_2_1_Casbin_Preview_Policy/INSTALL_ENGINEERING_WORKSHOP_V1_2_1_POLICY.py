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

POLICY_LINE = "p, operator, engineering_airlock, preview, allow"
TARGET_RELATIVE = Path("Config") / "engineering_airlock_policy.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def find_root() -> Path:
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
        Path(r"Z:\FOXAI"),
    ]
    for candidate in candidates:
        if (candidate / "core" / "security_containment.py").exists() and (candidate / TARGET_RELATIVE).exists():
            return candidate.resolve()
    raise RuntimeError("Could not locate the live FOXAI root containing core/security_containment.py and Config/engineering_airlock_policy.csv.")


def normalized_policy_lines(text: str) -> list[str]:
    # The live file may be normal CSV lines or may have been flattened by a display tool.
    # Only real newline-delimited policy rows are modified here.
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def preview(root: Path) -> dict:
    target = root / TARGET_RELATIVE
    text = target.read_text(encoding="utf-8")
    lines = normalized_policy_lines(text)
    return {
        "schema": "foxai.engineering.workshop.v1_2_1.policy-preview",
        "target_root": str(root),
        "file_targeted": str(TARGET_RELATIVE).replace("\\", "/"),
        "target_exists": target.exists(),
        "current_sha256": sha256_file(target),
        "policy_line": POLICY_LINE,
        "already_present": POLICY_LINE in lines,
        "files_explicitly_not_targeted": [
            "core/engineer_agent.py",
            "core/foxai_web.py",
            "core/security_containment.py",
            "Engine/**",
            "Models/**",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/**",
            "Library/**",
        ],
        "deletions": 0,
        "network": False,
        "packages_installed": False,
        "model_started_or_stopped": False,
    }


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def apply(root: Path) -> dict:
    target = root / TARGET_RELATIVE
    before_bytes = target.read_bytes()
    before_sha = hashlib.sha256(before_bytes).hexdigest()
    text = before_bytes.decode("utf-8")
    lines = normalized_policy_lines(text)

    backup_dir = root / "System" / "EngineeringWorkshop" / "InstallBackups" / utc_stamp()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_zip = backup_dir / "before_engineering_workshop_v1_2_1_policy.zip"

    with zipfile.ZipFile(backup_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(str(TARGET_RELATIVE).replace("\\", "/"), before_bytes)

    backup_sha = sha256_file(backup_zip)

    changed = False
    try:
        if POLICY_LINE not in lines:
            # Preserve all existing policy rows and add only the missing operator preview permission.
            if text and not text.endswith(("\n", "\r")):
                text += "\n"
            text += POLICY_LINE + "\n"
            write_atomic(target, text.encode("utf-8"))
            changed = True

        python_exe = root / "Runtime" / "Desktop" / "python" / "python.exe"
        if not python_exe.exists():
            python_exe = Path(sys.executable)

        validation_code = (
            "from core.security_containment import _casbin_enforcer, authorize_department_route\n"
            "_casbin_enforcer.cache_clear()\n"
            "decision=authorize_department_route('operator','engineering_airlock','preview')\n"
            "assert decision.allowed, decision\n"
            "assert decision.policy_source == 'casbin', decision\n"
            "print('CASBIN_ENGINEERING_PREVIEW_POLICY_OK')\n"
        )
        result = subprocess.run(
            [str(python_exe), "-c", validation_code],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        validation = {
            "argv": [str(python_exe), "-c", "<policy validation>"],
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        if result.returncode != 0:
            raise RuntimeError("Casbin preview-policy validation failed.")

        after_sha = sha256_file(target)
        receipt = {
            "schema": "foxai.engineering.workshop.v1_2_1.policy-receipt",
            "result": "installed_verified",
            "timestamp": utc_stamp(),
            "target_root": str(root),
            "diagnosis": (
                "Workshop begin/locate/save-plan/preview request the engineering_airlock preview action. "
                "Casbin was installed and the live policy omitted the operator preview allow row, so Casbin denied before the deterministic fallback could allow it."
            ),
            "backup": {
                "archive": str(backup_zip),
                "sha256": backup_sha,
                "target_before_sha256": before_sha,
            },
            "change": {
                "path": str(TARGET_RELATIVE).replace("\\", "/"),
                "line_added": POLICY_LINE if changed else None,
                "already_present": not changed,
                "before_sha256": before_sha,
                "after_sha256": after_sha,
            },
            "validation": validation,
            "deletions": 0,
            "network_used": False,
            "packages_installed": False,
            "model_started_or_stopped": False,
            "restart_required": True,
            "receipt_path": str(backup_dir / "install_receipt.json"),
        }
        (backup_dir / "install_receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return receipt
    except Exception:
        write_atomic(target, before_bytes)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    root = find_root()
    info = preview(root)
    info["approved"] = bool(args.approve)
    print(json.dumps(info, indent=2, ensure_ascii=False))

    if not args.approve:
        print("Preview only. Re-run with --approve after confirming the single CSV target.")
        return 0

    receipt = apply(root)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    print("Engineering Workshop V1.2.1 Casbin preview policy installed and verified.")
    print("Fully restart FOXAI WebUI before testing Workshop begin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
