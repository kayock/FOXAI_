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

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_ENGINEERING = PACKAGE_ROOT / "Engineering"
PACKAGE_BRIDGE = PACKAGE_ROOT / "core" / "engineering_workshop_bridge.py"
INTEGRATION_MARKER = "FOXAI_ENGINEERING_WORKSHOP_V1_1_INTEGRATION"

IMPORT_ANCHOR = "from core.engineer_intent import EngineerIntent"
INIT_ANCHOR = "        self.intent = EngineerIntent()"
HANDLE_ANCHOR = "        query = (payload or text or \"\").strip()"

IMPORT_BLOCK = f'''\n# {INTEGRATION_MARKER}\ntry:\n    from core.engineering_workshop_bridge import EngineeringWorkshopBridge\nexcept Exception:\n    EngineeringWorkshopBridge = None\n'''

INIT_BLOCK = f'''\n        # {INTEGRATION_MARKER}\n        self.engineering_workshop = (\n            EngineeringWorkshopBridge(self)\n            if EngineeringWorkshopBridge is not None\n            else None\n        )\n'''

HANDLE_BLOCK = f'''\n        # {INTEGRATION_MARKER}\n        if self.engineering_workshop is not None:\n            workshop_report = self.engineering_workshop.handle(\n                query,\n                caller=caller,\n                operator_approved=operator_approved,\n            )\n            if workshop_report is not None:\n                self.app.add_chat(\"ERIC\", query)\n                self.app.mission_status(\n                    \"Engineering Workshop online.\\n\\n\"\n                    \"Controlled implementation workflow active.\"\n                )\n                self.app.add_chat(\"ENGINEER\", workshop_report)\n                self.app.mission_memory.save()\n                if hasattr(self.app, \"complete_workshop_mission\"):\n                    self.app.complete_workshop_mission(\"ONLINE\")\n                return \"break\"\n'''

DEPARTMENT_FILES = sorted(
    str(path.relative_to(PACKAGE_ENGINEERING)).replace("\\", "/")
    for path in PACKAGE_ENGINEERING.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts
)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, prefix=path.name, suffix=".tmp") as handle:
        temp = Path(handle.name)
        handle.write(data)
    os.replace(temp, path)


def patch_engineer_source(source: str) -> str:
    if INTEGRATION_MARKER in source:
        return source
    missing = [anchor for anchor in (IMPORT_ANCHOR, INIT_ANCHOR, HANDLE_ANCHOR) if source.count(anchor) != 1]
    if missing:
        raise RuntimeError(
            "Current core/engineer_agent.py does not match the verified GitHub anchors: "
            + ", ".join(missing)
        )
    patched = source.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_BLOCK, 1)
    patched = patched.replace(INIT_ANCHOR, INIT_ANCHOR + INIT_BLOCK, 1)
    patched = patched.replace(HANDLE_ANCHOR, HANDLE_ANCHOR + HANDLE_BLOCK, 1)
    patched = patched.replace(
        "Engineer is FOXAI's read-only code and architecture specialist.",
        "Engineer is FOXAI's read-only-first code specialist with a controlled implementation Workshop.",
        1,
    )
    patched = patched.replace(
        "- Never modify files.",
        "- Modify project files only through exact-plan preview, explicit approval, snapshot, validation, and rollback.",
        1,
    )
    compile(patched, "core/engineer_agent.py", "exec")
    return patched


def target_paths(root: Path) -> list[Path]:
    paths = [root / "core" / "engineer_agent.py", root / "core" / "engineering_workshop_bridge.py"]
    paths.extend(root / "Departments" / "Engineering" / rel for rel in DEPARTMENT_FILES)
    return paths


def make_backup(root: Path, paths: list[Path], backup_dir: Path) -> tuple[Path, dict]:
    backup_dir.mkdir(parents=True, exist_ok=False)
    archive_path = backup_dir / "before_engineering_workshop_v1_1.zip"
    entries = []
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            rel = path.relative_to(root).as_posix()
            if path.exists() and path.is_file():
                archive.write(path, arcname=f"files/{rel}")
                entries.append({"path": rel, "existed": True, "sha256": sha256(path), "size": path.stat().st_size})
            else:
                entries.append({"path": rel, "existed": False, "sha256": None, "size": None})
        archive.writestr("manifest.json", json.dumps({"root": str(root), "entries": entries}, indent=2))
    receipt = {
        "archive": str(archive_path),
        "sha256": sha256(archive_path),
        "entries": entries,
    }
    (backup_dir / "backup_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return archive_path, receipt


def restore(root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        for item in manifest["entries"]:
            destination = root / item["path"]
            if item["existed"]:
                atomic_write(destination, archive.read(f"files/{item['path']}"))
            else:
                destination.unlink(missing_ok=True)


def copy_department(root: Path) -> list[dict]:
    changes = []
    target = root / "Departments" / "Engineering"
    for rel in DEPARTMENT_FILES:
        source = PACKAGE_ENGINEERING / rel
        destination = target / rel
        before = sha256(destination) if destination.exists() and destination.is_file() else None
        atomic_write(destination, source.read_bytes())
        changes.append({"path": destination.relative_to(root).as_posix(), "before_sha256": before, "after_sha256": sha256(destination)})
    return changes


def choose_python(root: Path) -> Path:
    candidates = [
        root / "Runtime" / "Desktop" / "python" / "python.exe",
        Path(sys.executable),
    ]
    return next((item for item in candidates if item.exists()), Path(sys.executable))


def run_validation(root: Path) -> list[dict]:
    python_exe = choose_python(root)
    commands = [
        [str(python_exe), "-m", "py_compile", "core/engineer_agent.py", "core/engineering_workshop_bridge.py"],
        [str(python_exe), "-m", "unittest", "discover", "-s", "Departments/Engineering/tests", "-v"],
    ]
    results = []
    for argv in commands:
        completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=240, shell=False)
        result = {
            "argv": argv,
            "cwd": str(root),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        results.append(result)
        if completed.returncode != 0:
            break
    return results


def preflight(root: Path) -> dict:
    engineer = root / "core" / "engineer_agent.py"
    department = root / "Departments" / "Engineering"
    checks = {
        "root_exists": root.exists() and root.is_dir(),
        "engineer_agent_exists": engineer.exists() and engineer.is_file(),
        "engineering_department_exists": department.exists() and department.is_dir(),
        "package_bridge_exists": PACKAGE_BRIDGE.exists(),
        "package_department_exists": PACKAGE_ENGINEERING.exists(),
    }
    if checks["engineer_agent_exists"]:
        source = engineer.read_text(encoding="utf-8")
        checks.update({
            "import_anchor_count": source.count(IMPORT_ANCHOR),
            "init_anchor_count": source.count(INIT_ANCHOR),
            "handle_anchor_count": source.count(HANDLE_ANCHOR),
            "already_integrated": INTEGRATION_MARKER in source,
        })
        if not checks["already_integrated"]:
            patch_engineer_source(source)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Install FOXAI Engineering Workshop V1.1 integration")
    parser.add_argument("--foxai-root", default=r"Z:\FOXAI")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    root = Path(args.foxai_root).expanduser().resolve(strict=False)
    checks = preflight(root)
    preview = {
        "schema": "foxai.engineering.workshop.integration-preview.v1",
        "target_root": str(root),
        "preflight": checks,
        "files_added_or_replaced": [
            "core/engineering_workshop_bridge.py",
            *[f"Departments/Engineering/{rel}" for rel in DEPARTMENT_FILES],
        ],
        "file_patched": "core/engineer_agent.py",
        "deletions": 0,
        "network": False,
        "packages_installed": False,
        "approval_required": True,
        "approved": args.approve,
    }
    print(json.dumps(preview, indent=2))
    required = [
        checks.get("root_exists"),
        checks.get("engineer_agent_exists"),
        checks.get("engineering_department_exists"),
        checks.get("package_bridge_exists"),
        checks.get("package_department_exists"),
    ]
    if not all(required):
        print("Preflight failed; nothing changed.")
        return 2
    if not args.approve:
        print("Preview only. Re-run with --approve after reviewing the target.")
        return 0

    backup_dir = root / "System" / "EngineeringWorkshop" / "InstallBackups" / stamp()
    paths = target_paths(root)
    backup_zip, backup_receipt = make_backup(root, paths, backup_dir)
    changes = []
    validations = []
    result = "failed_rolled_back"
    error = None
    try:
        changes.extend(copy_department(root))
        bridge_target = root / "core" / "engineering_workshop_bridge.py"
        before = sha256(bridge_target) if bridge_target.exists() else None
        atomic_write(bridge_target, PACKAGE_BRIDGE.read_bytes())
        changes.append({"path": "core/engineering_workshop_bridge.py", "before_sha256": before, "after_sha256": sha256(bridge_target)})

        engineer_target = root / "core" / "engineer_agent.py"
        original = engineer_target.read_text(encoding="utf-8")
        patched = patch_engineer_source(original)
        before = sha256(engineer_target)
        atomic_write(engineer_target, patched.encode("utf-8"))
        changes.append({"path": "core/engineer_agent.py", "before_sha256": before, "after_sha256": sha256(engineer_target)})

        validations = run_validation(root)
        if not validations or any(item["returncode"] != 0 for item in validations):
            raise RuntimeError("Post-install validation failed")
        result = "installed_verified"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        restore(root, backup_zip)

    receipt = {
        "schema": "foxai.engineering.workshop.integration-receipt.v1",
        "result": result,
        "timestamp": stamp(),
        "target_root": str(root),
        "backup": backup_receipt,
        "changes": changes,
        "validations": validations,
        "error": error,
        "deletions": 0,
        "network_used": False,
        "packages_installed": False,
    }
    receipt_path = backup_dir / "install_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({**receipt, "receipt_path": str(receipt_path)}, indent=2))
    return 0 if result == "installed_verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
