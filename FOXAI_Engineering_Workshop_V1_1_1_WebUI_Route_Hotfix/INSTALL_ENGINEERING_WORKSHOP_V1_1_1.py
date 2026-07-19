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

HOTFIX_MARKER = "FOXAI_ENGINEERING_WORKSHOP_V1_1_1_WEBUI_ROUTE"
V11_MARKER = "FOXAI_ENGINEERING_WORKSHOP_V1_1_INTEGRATION"
WEBUI_ANCHOR = "            return _web_engineer.analyze(text)"

OLD_IMPORT_BLOCK = f'''# {V11_MARKER}\ntry:\n    from core.engineering_workshop_bridge import EngineeringWorkshopBridge\nexcept Exception:\n    EngineeringWorkshopBridge = None\n'''
NEW_IMPORT_BLOCK = f'''# {V11_MARKER}\ntry:\n    from core.engineering_workshop_bridge import EngineeringWorkshopBridge\n    _ENGINEERING_WORKSHOP_IMPORT_ERROR = ""\nexcept Exception as _engineering_workshop_import_exception:\n    EngineeringWorkshopBridge = None\n    _ENGINEERING_WORKSHOP_IMPORT_ERROR = (\n        f"{{type(_engineering_workshop_import_exception).__name__}}: "\n        f"{{_engineering_workshop_import_exception}}"\n    )\n'''

OLD_INIT_BLOCK = f'''        # {V11_MARKER}\n        self.engineering_workshop = (\n            EngineeringWorkshopBridge(self)\n            if EngineeringWorkshopBridge is not None\n            else None\n        )\n'''
NEW_INIT_BLOCK = f'''        # {V11_MARKER}\n        self._engineering_workshop_import_error = _ENGINEERING_WORKSHOP_IMPORT_ERROR\n        self.engineering_workshop = (\n            EngineeringWorkshopBridge(self)\n            if EngineeringWorkshopBridge is not None\n            else None\n        )\n'''

WEBUI_ROUTE_BLOCK = f'''            # {HOTFIX_MARKER}\n            normalized_workshop_text = (text or "").strip()\n            if re.match(\n                r"^(?:/engineer\\s+)?workshop\\b",\n                normalized_workshop_text,\n                flags=re.IGNORECASE,\n            ):\n                workshop_bridge = getattr(\n                    _web_engineer,\n                    "engineering_workshop",\n                    None,\n                )\n                if workshop_bridge is None:\n                    import_error = str(\n                        getattr(\n                            _web_engineer,\n                            "_engineering_workshop_import_error",\n                            "",\n                        )\n                        or ""\n                    ).strip()\n                    detail = (\n                        f"\\n\\nImport error: {{import_error}}"\n                        if import_error\n                        else ""\n                    )\n                    return (\n                        "ENGINEERING WORKSHOP — ROUTE UNAVAILABLE\\n\\n"\n                        "The WebUI recognized the Workshop command, but the "\n                        "Workshop bridge did not load."\n                        + detail\n                    )\n                workshop_report = workshop_bridge.handle(\n                    normalized_workshop_text,\n                    caller=caller,\n                    operator_approved=True,\n                )\n                if workshop_report is not None:\n                    return workshop_report\n\n{WEBUI_ANCHOR}'''


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
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def patch_engineer_agent(source: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    patched = source

    if OLD_IMPORT_BLOCK in patched:
        patched = patched.replace(OLD_IMPORT_BLOCK, NEW_IMPORT_BLOCK, 1)
        changes.append("exposed_bridge_import_error")
    elif "_ENGINEERING_WORKSHOP_IMPORT_ERROR" not in patched:
        raise RuntimeError(
            "The V1.1 Engineer import block was not found. "
            "Reinstall Engineering Workshop V1.1 before this hotfix."
        )

    if OLD_INIT_BLOCK in patched:
        patched = patched.replace(OLD_INIT_BLOCK, NEW_INIT_BLOCK, 1)
        changes.append("stored_bridge_import_error_on_agent")
    elif "self._engineering_workshop_import_error" not in patched:
        raise RuntimeError(
            "The V1.1 Engineer initialization block was not found. "
            "Reinstall Engineering Workshop V1.1 before this hotfix."
        )

    compile(patched, "core/engineer_agent.py", "exec")
    return patched, changes


def patch_webui(source: str) -> tuple[str, list[str]]:
    if HOTFIX_MARKER in source:
        return source, []
    count = source.count(WEBUI_ANCHOR)
    if count != 1:
        raise RuntimeError(
            "Expected exactly one live WebUI Engineer analyze anchor, "
            f"but found {count}. Nothing was changed."
        )
    patched = source.replace(WEBUI_ANCHOR, WEBUI_ROUTE_BLOCK, 1)
    compile(patched, "core/foxai_web.py", "exec")
    return patched, ["routed_workshop_before_read_only_analyze"]


def choose_python(root: Path) -> Path:
    candidates = [
        root / "Runtime" / "Desktop" / "python" / "python.exe",
        Path(sys.executable),
    ]
    return next((path for path in candidates if path.exists()), Path(sys.executable))


def make_backup(root: Path, targets: list[Path], backup_dir: Path) -> tuple[Path, dict]:
    backup_dir.mkdir(parents=True, exist_ok=False)
    archive = backup_dir / "before_engineering_workshop_v1_1_1.zip"
    entries = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for target in targets:
            relative = target.relative_to(root).as_posix()
            bundle.write(target, arcname=f"files/{relative}")
            entries.append(
                {
                    "path": relative,
                    "sha256": sha256(target),
                    "size": target.stat().st_size,
                }
            )
        bundle.writestr(
            "manifest.json",
            json.dumps({"root": str(root), "entries": entries}, indent=2),
        )
    receipt = {
        "archive": str(archive),
        "sha256": sha256(archive),
        "entries": entries,
    }
    (backup_dir / "backup_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    return archive, receipt


def restore(root: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "r") as bundle:
        manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
        for item in manifest["entries"]:
            atomic_write(root / item["path"], bundle.read(f"files/{item['path']}"))


def run_validation(root: Path) -> list[dict]:
    python_exe = choose_python(root)
    commands = [
        [
            str(python_exe),
            "-m",
            "py_compile",
            "core/engineer_agent.py",
            "core/engineering_workshop_bridge.py",
            "core/foxai_web.py",
        ],
        [
            str(python_exe),
            "-c",
            (
                "from core.engineering_workshop_bridge import "
                "EngineeringWorkshopBridge; "
                "print('WORKSHOP_BRIDGE_IMPORT_OK')"
            ),
        ],
        [
            str(python_exe),
            "-m",
            "unittest",
            "discover",
            "-s",
            "Departments/Engineering/tests",
            "-v",
        ],
    ]
    results = []
    for argv in commands:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install Engineering Workshop V1.1.1 WebUI route hotfix"
    )
    parser.add_argument("--foxai-root", default=r"Z:\FOXAI")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    root = Path(args.foxai_root).expanduser().resolve(strict=False)
    engineer = root / "core" / "engineer_agent.py"
    bridge = root / "core" / "engineering_workshop_bridge.py"
    webui = root / "core" / "foxai_web.py"

    checks = {
        "root_exists": root.is_dir(),
        "engineer_agent_exists": engineer.is_file(),
        "workshop_bridge_exists": bridge.is_file(),
        "foxai_web_exists": webui.is_file(),
        "v1_1_installed": False,
        "webui_analyze_anchor_count": 0,
        "already_hotfixed": False,
    }

    patched_engineer = None
    patched_webui = None
    planned_changes: list[str] = []
    if engineer.is_file():
        engineer_source = engineer.read_text(encoding="utf-8")
        checks["v1_1_installed"] = V11_MARKER in engineer_source
        if checks["v1_1_installed"]:
            patched_engineer, agent_changes = patch_engineer_agent(engineer_source)
            planned_changes.extend(f"core/engineer_agent.py: {item}" for item in agent_changes)
    if webui.is_file():
        webui_source = webui.read_text(encoding="utf-8")
        checks["webui_analyze_anchor_count"] = webui_source.count(WEBUI_ANCHOR)
        checks["already_hotfixed"] = HOTFIX_MARKER in webui_source
        patched_webui, web_changes = patch_webui(webui_source)
        planned_changes.extend(f"core/foxai_web.py: {item}" for item in web_changes)

    preview = {
        "schema": "foxai.engineering.workshop.v1_1_1.preview",
        "target_root": str(root),
        "checks": checks,
        "planned_changes": planned_changes,
        "files_targeted": [
            "core/engineer_agent.py",
            "core/foxai_web.py",
        ],
        "deletions": 0,
        "network": False,
        "packages_installed": False,
        "approved": args.approve,
    }
    print(json.dumps(preview, indent=2))

    required = [
        checks["root_exists"],
        checks["engineer_agent_exists"],
        checks["workshop_bridge_exists"],
        checks["foxai_web_exists"],
        checks["v1_1_installed"],
    ]
    if not all(required):
        print("Required V1.1 files were not found. Nothing changed.")
        return 2
    if checks["already_hotfixed"]:
        print("V1.1.1 WebUI route is already installed. Nothing changed.")
        return 0
    if not args.approve:
        print("Preview only. Re-run with --approve after reviewing it.")
        return 0

    backup_dir = (
        root
        / "System"
        / "EngineeringWorkshop"
        / "InstallBackups"
        / stamp()
    )
    targets = [engineer, webui]
    archive, backup_receipt = make_backup(root, targets, backup_dir)

    before = {target.relative_to(root).as_posix(): sha256(target) for target in targets}
    validations: list[dict] = []
    result = "failed_rolled_back"
    error = None
    try:
        assert patched_engineer is not None
        assert patched_webui is not None
        atomic_write(engineer, patched_engineer.encode("utf-8"))
        atomic_write(webui, patched_webui.encode("utf-8"))
        validations = run_validation(root)
        if not validations or any(item["returncode"] != 0 for item in validations):
            raise RuntimeError("Post-install validation failed")
        result = "installed_verified"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        restore(root, archive)

    after = {target.relative_to(root).as_posix(): sha256(target) for target in targets}
    receipt = {
        "schema": "foxai.engineering.workshop.v1_1_1.receipt",
        "result": result,
        "timestamp": stamp(),
        "target_root": str(root),
        "diagnosis": (
            "FOXAI WebUI called EngineerAgent.analyze() directly and bypassed "
            "the V1.1 hook in EngineerAgent.handle()."
        ),
        "backup": backup_receipt,
        "changes": [
            {
                "path": path,
                "before_sha256": before[path],
                "after_sha256": after[path],
            }
            for path in before
        ],
        "validations": validations,
        "error": error,
        "deletions": 0,
        "network_used": False,
        "packages_installed": False,
        "receipt_path": str(backup_dir / "install_receipt.json"),
    }
    (backup_dir / "install_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))

    if result != "installed_verified":
        print("Hotfix failed validation and the two original files were restored.")
        return 1
    print("Engineering Workshop V1.1.1 WebUI route installed and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
