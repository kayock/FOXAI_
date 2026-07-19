from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MARKER = "FOXAI_ENGINEERING_WORKSHOP_V1_2_ANALYZE_ROUTE"
ANALYZE_SIGNATURE = "    def analyze(self, query):"
NORMALIZE_LINE = "        query = self.normalize_operator_query(query)"

ROUTE_BLOCK_LINES = [
    f"        # {MARKER}",
    "        if re.match(r\"^workshop\\b\", query, flags=re.IGNORECASE):",
    "            workshop_bridge = (",
    "                getattr(self, \"engineering_workshop\", None)",
    "                or getattr(self, \"_engineering_workshop_bridge\", None)",
    "            )",
    "            if workshop_bridge is None:",
    "                try:",
    "                    from core.engineering_workshop_bridge import EngineeringWorkshopBridge",
    "                    workshop_bridge = EngineeringWorkshopBridge(self)",
    "                    self._engineering_workshop_bridge = workshop_bridge",
    "                    self.engineering_workshop = workshop_bridge",
    "                except Exception as workshop_error:",
    "                    return (",
    "                        \"ENGINEERING WORKSHOP — ROUTE UNAVAILABLE\\n\\n\"",
    "                        \"The explicit Workshop command was recognized, but the \"",
    "                        \"Workshop bridge could not load.\\n\\n\"",
    "                        f\"{type(workshop_error).__name__}: {workshop_error}\"",
    "                    )",
    "            context = getattr(self, \"_active_airlock_context\", {}) or {}",
    "            caller = str(context.get(\"actor\") or \"operator\")",
    "            workshop_report = workshop_bridge.handle(",
    "                query,",
    "                caller=caller,",
    "                operator_approved=bool(context.get(\"authorization_allowed\")),",
    "            )",
    "            if workshop_report is not None:",
    "                return workshop_report",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_text(data: bytes) -> tuple[str, str, bool]:
    has_bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    newline = "\r\n" if text.count("\r\n") >= text.count("\n") / 2 and "\r\n" in text else "\n"
    return text, newline, has_bom


def encode_text(text: str, *, has_bom: bool) -> bytes:
    encoded = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + encoded) if has_bom else encoded


def patch_engineer_source(source: str, newline: str = "\n") -> tuple[str, list[str]]:
    if MARKER in source:
        compile(source, "core/engineer_agent.py", "exec")
        return source, []

    signature_count = source.count(ANALYZE_SIGNATURE)
    if signature_count != 1:
        raise RuntimeError(
            f"Expected exactly one EngineerAgent.analyze signature; found {signature_count}."
        )

    anchor = ANALYZE_SIGNATURE + newline + NORMALIZE_LINE
    anchor_count = source.count(anchor)
    if anchor_count != 1:
        # Permit a source string normalized to LF while preserving the original on write.
        normalized = source.replace("\r\n", "\n")
        normalized_anchor = ANALYZE_SIGNATURE + "\n" + NORMALIZE_LINE
        if normalized.count(normalized_anchor) != 1:
            raise RuntimeError(
                "The current Engineer analyze route does not match the verified baseline anchor."
            )
        block = "\n".join(ROUTE_BLOCK_LINES)
        patched_normalized = normalized.replace(
            normalized_anchor,
            normalized_anchor + "\n" + block,
            1,
        )
        patched = patched_normalized.replace("\n", newline)
    else:
        block = newline.join(ROUTE_BLOCK_LINES)
        patched = source.replace(anchor, anchor + newline + block, 1)

    compile(patched, "core/engineer_agent.py", "exec")
    verify_analyze_ast(patched)
    return patched, ["route_explicit_workshop_commands_inside_EngineerAgent.analyze"]


def verify_analyze_ast(source: str) -> None:
    tree = ast.parse(source, filename="core/engineer_agent.py")
    engineer_class = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "EngineerAgent"),
        None,
    )
    if engineer_class is None:
        raise RuntimeError("EngineerAgent class was not found after staging the patch.")
    analyze = next(
        (node for node in engineer_class.body if isinstance(node, ast.FunctionDef) and node.name == "analyze"),
        None,
    )
    if analyze is None:
        raise RuntimeError("EngineerAgent.analyze was not found after staging the patch.")
    if not any(isinstance(node, ast.ImportFrom) and node.module == "core.engineering_workshop_bridge" for node in ast.walk(analyze)):
        raise RuntimeError("The staged analyze route does not contain the lazy Workshop bridge import.")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def choose_python(root: Path) -> Path:
    candidates = [
        root / "Runtime" / "Desktop" / "python" / "python.exe",
        Path(sys.executable),
    ]
    return next((candidate for candidate in candidates if candidate.exists()), Path(sys.executable))


def make_backup(root: Path, engineer: Path, backup_dir: Path) -> tuple[Path, dict]:
    backup_dir.mkdir(parents=True, exist_ok=False)
    archive = backup_dir / "before_engineering_workshop_v1_2.zip"
    relative = engineer.relative_to(root).as_posix()
    entry = {
        "path": relative,
        "sha256": sha256(engineer),
        "size": engineer.stat().st_size,
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(engineer, arcname=f"files/{relative}")
        bundle.writestr("manifest.json", json.dumps({"root": str(root), "entries": [entry]}, indent=2))
    receipt = {
        "archive": str(archive),
        "sha256": sha256(archive),
        "entries": [entry],
    }
    (backup_dir / "backup_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return archive, receipt


def restore(root: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "r") as bundle:
        manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
        for item in manifest["entries"]:
            atomic_write(root / item["path"], bundle.read(f"files/{item['path']}"))


def run_command(argv: list[str], root: Path, timeout: int = 300) -> dict:
    completed = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return {
        "argv": argv,
        "cwd": str(root),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_validation(root: Path) -> list[dict]:
    python_exe = choose_python(root)
    probe = (
        "from core.engineer_agent import EngineerAgent\n"
        "class ProbeApp:\n"
        "    models=[]\n"
        "    threads=8\n"
        "agent=EngineerAgent(ProbeApp())\n"
        "agent._active_airlock_context={'actor':'operator','authorization_allowed':True}\n"
        "report=agent.analyze('/engineer workshop capabilities')\n"
        "assert report.startswith('ENGINEERING WORKSHOP CAPABILITIES'), report[:800]\n"
        "print('WORKSHOP_ANALYZE_ROUTE_OK')\n"
    )
    commands = [
        [str(python_exe), "-m", "py_compile", "core/engineer_agent.py", "core/engineering_workshop_bridge.py"],
        [str(python_exe), "-c", probe],
        [str(python_exe), "-m", "unittest", "discover", "-s", "Departments/Engineering/tests", "-v"],
    ]
    results: list[dict] = []
    for argv in commands:
        result = run_command(argv, root)
        results.append(result)
        if result["returncode"] != 0:
            break
    return results


def preflight(root: Path) -> tuple[dict, str | None, bytes | None]:
    engineer = root / "core" / "engineer_agent.py"
    bridge = root / "core" / "engineering_workshop_bridge.py"
    workshop = root / "Departments" / "Engineering" / "workshop.py"
    webui = root / "core" / "foxai_web.py"
    checks = {
        "root_exists": root.is_dir(),
        "engineer_agent_exists": engineer.is_file(),
        "workshop_bridge_exists": bridge.is_file(),
        "workshop_engine_exists": workshop.is_file(),
        "foxai_web_exists_for_unchanged_hash": webui.is_file(),
        "already_integrated": False,
        "analyze_signature_count": 0,
        "verified_analyze_anchor_count": 0,
    }
    staged_text = None
    staged_bytes = None
    if engineer.is_file():
        original = engineer.read_bytes()
        source, newline, has_bom = detect_text(original)
        checks["already_integrated"] = MARKER in source
        checks["analyze_signature_count"] = source.count(ANALYZE_SIGNATURE)
        checks["verified_analyze_anchor_count"] = source.replace("\r\n", "\n").count(
            ANALYZE_SIGNATURE + "\n" + NORMALIZE_LINE
        )
        staged_text, _changes = patch_engineer_source(source, newline)
        staged_bytes = encode_text(staged_text, has_bom=has_bom)
    return checks, staged_text, staged_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Install FOXAI Engineering Workshop V1.2 analyze-route integration")
    parser.add_argument("--foxai-root", default=r"Z:\FOXAI")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    root = Path(args.foxai_root).expanduser().resolve(strict=False)
    engineer = root / "core" / "engineer_agent.py"
    webui = root / "core" / "foxai_web.py"

    try:
        checks, _staged_text, staged_bytes = preflight(root)
    except Exception as exc:
        print(json.dumps({"result": "blocked_nothing_changed", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2

    engineer_before = sha256(engineer) if engineer.is_file() else None
    webui_before = sha256(webui) if webui.is_file() else None
    preview = {
        "schema": "foxai.engineering.workshop.v1_2.preview",
        "target_root": str(root),
        "checks": checks,
        "file_targeted": "core/engineer_agent.py",
        "files_explicitly_not_targeted": [
            "core/foxai_web.py",
            "core/server.py",
            "Engine/llama-server.exe",
            "Models/**",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/**",
        ],
        "current_hashes": {
            "core/engineer_agent.py": engineer_before,
            "core/foxai_web.py": webui_before,
        },
        "deletions": 0,
        "network": False,
        "packages_installed": False,
        "model_started_or_stopped": False,
        "approved": args.approve,
    }
    print(json.dumps(preview, indent=2))

    required = [
        checks["root_exists"],
        checks["engineer_agent_exists"],
        checks["workshop_bridge_exists"],
        checks["workshop_engine_exists"],
        checks["foxai_web_exists_for_unchanged_hash"],
    ]
    if not all(required):
        print("Required files are missing. Nothing changed.")
        return 2
    if checks["already_integrated"]:
        print("Engineering Workshop V1.2 analyze route is already present. Nothing changed.")
        return 0
    if not args.approve:
        print("Preview only. Re-run with --approve only after reviewing this one-file target.")
        return 0
    if staged_bytes is None:
        print("No staged patch was produced. Nothing changed.")
        return 2

    backup_dir = root / "System" / "EngineeringWorkshop" / "InstallBackups" / utc_stamp()
    archive, backup_receipt = make_backup(root, engineer, backup_dir)
    validations: list[dict] = []
    result = "failed_rolled_back"
    error = None
    try:
        # Refuse to apply if the file changed after preview was computed in this process.
        if sha256(engineer) != engineer_before:
            raise RuntimeError("core/engineer_agent.py changed during installation; refusing to apply")
        atomic_write(engineer, staged_bytes)
        validations = run_validation(root)
        if not validations or any(item["returncode"] != 0 for item in validations):
            raise RuntimeError("Post-install Workshop route validation failed")
        if sha256(webui) != webui_before:
            raise RuntimeError("core/foxai_web.py changed unexpectedly; restoring Engineer patch")
        result = "installed_verified"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        restore(root, archive)

    receipt = {
        "schema": "foxai.engineering.workshop.v1_2.receipt",
        "result": result,
        "timestamp": utc_stamp(),
        "target_root": str(root),
        "diagnosis": (
            "FOXAI WebUI routes explicit Engineer requests to EngineerAgent.analyze(). "
            "V1.2 therefore intercepts only explicit 'workshop' commands inside analyze, "
            "without modifying the WebUI or model runtime."
        ),
        "backup": backup_receipt,
        "changes": [
            {
                "path": "core/engineer_agent.py",
                "before_sha256": engineer_before,
                "after_sha256": sha256(engineer),
            }
        ],
        "untouched_hash_check": {
            "path": "core/foxai_web.py",
            "before_sha256": webui_before,
            "after_sha256": sha256(webui),
            "unchanged": sha256(webui) == webui_before,
        },
        "validations": validations,
        "error": error,
        "deletions": 0,
        "network_used": False,
        "packages_installed": False,
        "model_started_or_stopped": False,
        "receipt_path": str(backup_dir / "install_receipt.json"),
    }
    (backup_dir / "install_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    if result == "installed_verified":
        print("Engineering Workshop V1.2 analyze route installed and verified.")
        return 0
    print("Installation failed and core/engineer_agent.py was restored from backup.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
