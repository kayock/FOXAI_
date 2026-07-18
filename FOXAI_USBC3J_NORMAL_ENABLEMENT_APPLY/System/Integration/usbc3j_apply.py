#!/usr/bin/env python3
"""USB C3J controlled normal-enablement apply, with no ComfyUI launch.

Applies only the accepted C3I normal lifecycle policy and exact live wiring.
No candidate launcher/controller is executed. No state or normal-log directory
is created. Any partial write is rolled back to exact verified backups.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import site
import sys
import traceback
from datetime import datetime, timezone
from typing import Any
import zipfile

PACKAGE_NAME = "FOXAI_USBC3J_NORMAL_ENABLEMENT_APPLY"
C3I_RUN = "20260718T041549Z"
C3I_INTEGRITY_SHA256 = "f5de7dac604002bb3111d7abba67933941574358a7ba45db91ebf4313e069714"
C3I_CLASSIFICATION = "C3I_READY_FOR_C3J_NORMAL_ENABLEMENT_APPROVAL"
POLICY_ID = "FOXAI_COMFYUI_SAFE_NORMAL_CPU_V1"
C3E_RUN = "20260718T023211Z"
C3E_INVENTORY_SHA256 = "d55a3d8c8c81c1ce0aaf3ebb98a5c8345c8d3be75915a450786c29cb3b66f16b"
EXPECTED_TARGET_COUNT = 39046
EXPECTED_TARGET_BYTES = 1520221467
EXPECTED_TARGET_TREE = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"
SUCCESS = "C3J_NORMAL_ENABLEMENT_APPLIED_VERIFIED_NO_LAUNCH_READY_FOR_C3K_APPROVAL"
ALREADY = "C3J_ALREADY_APPLIED_VERIFIED_NO_LAUNCH_READY_FOR_C3K_APPROVAL"
ROLLED_BACK = "C3J_BLOCKED_ROLLED_BACK_NO_LAUNCH"
PARTIAL = "C3J_BLOCKED_PARTIAL_STATE_REQUIRES_MANUAL_REVIEW"
BLOCKED = "C3J_BLOCKED_FAIL_CLOSED_NO_LAUNCH"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8", newline="\n")


def verify_exact_file(path: Path, size: int, digest: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Required exact file is missing or unsafe: {path}")
    actual_size = path.stat().st_size
    actual_digest = sha256_file(path)
    if actual_size != int(size) or actual_digest != digest:
        raise RuntimeError(
            f"Exact file mismatch: {path} size={actual_size}/{size} "
            f"sha256={actual_digest}/{digest}"
        )
    return {"path": str(path), "size_bytes": actual_size, "sha256": actual_digest, "verified": True}


def verify_package(package_root: Path) -> dict[str, Any]:
    manifest_path = package_root / "PACKAGE_INTEGRITY.json"
    if not manifest_path.is_file():
        raise RuntimeError("C3J PACKAGE_INTEGRITY.json is missing")
    manifest = read_json(manifest_path)
    rows = []
    for record in manifest.get("files") or []:
        rows.append(verify_exact_file(
            package_root / PurePosixPath(str(record["path"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
        ))
    if not rows:
        raise RuntimeError("C3J package-integrity manifest is empty")
    return {"verified": True, "file_count": len(rows), "files": rows}


def verify_c3i(root: Path) -> dict[str, Any]:
    base = root / "FOXAI_USBC3I_NORMAL_ENABLEMENT_REVIEW" / "REVIEW_OUTPUT" / C3I_RUN
    integrity_path = base / "evidence_integrity.json"
    if sha256_file(integrity_path) != C3I_INTEGRITY_SHA256:
        raise RuntimeError("Exact C3I evidence-integrity hash changed")
    integrity = read_json(integrity_path)
    rows = []
    for record in integrity.get("files") or []:
        rows.append(verify_exact_file(
            base / PurePosixPath(str(record["file"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
        ))
    classification = read_json(base / "classification.json")
    policy = read_json(base / "recommended_normal_policy.json")
    target = read_json(base / "isolated_target_reverification.json")
    live = read_json(base / "live_surface_verification_after.json")
    if (
        integrity.get("verified") is not True
        or int(integrity.get("file_count", 0)) != 21
        or len(rows) != 21
        or classification.get("verified") is not True
        or classification.get("mode") != C3I_CLASSIFICATION
        or classification.get("launch_performed")
        or classification.get("live_change")
        or classification.get("network_access")
        or policy.get("policy_id") != POLICY_ID
        or target.get("verified") is not True
        or target.get("actual_tree_sha256") != EXPECTED_TARGET_TREE
        or live.get("verified") is not True
    ):
        raise RuntimeError("Exact accepted C3I evidence did not reverify")
    return {
        "verified": True,
        "base": str(base),
        "evidence_file_count": len(rows),
        "classification": classification.get("mode"),
        "policy_id": policy.get("policy_id"),
        "files": rows,
    }


def load_c3e_inventory(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL" / "INSTALL_OUTPUT" / C3E_RUN / "installed_file_inventory_final.json"
    if sha256_file(path) != C3E_INVENTORY_SHA256:
        raise RuntimeError("Exact C3E installed inventory hash changed")
    inventory = read_json(path)
    if (
        inventory.get("verified") is not True
        or int(inventory.get("file_count", 0)) != EXPECTED_TARGET_COUNT
        or int(inventory.get("total_bytes", 0)) != EXPECTED_TARGET_BYTES
        or inventory.get("tree_sha256") != EXPECTED_TARGET_TREE
        or len(inventory.get("files") or []) != EXPECTED_TARGET_COUNT
    ):
        raise RuntimeError("Exact C3E inventory metadata changed")
    return path, inventory


def verify_target(root: Path, inventory: dict[str, Any], phase: str) -> dict[str, Any]:
    target = root / "Runtime/ComfyUI/site-packages"
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError("Committed isolated target is missing or unsafe")
    expected_rows = inventory.get("files") or []
    expected = {str(row["path"]).casefold(): row for row in expected_rows}
    if len(expected) != len(expected_rows):
        raise RuntimeError("C3E inventory contains duplicate case-insensitive paths")
    actual: dict[str, Path] = {}
    symlinks = []
    for path in target.rglob("*"):
        if path.is_symlink():
            symlinks.append(path.relative_to(target).as_posix())
        elif path.is_file():
            relative = path.relative_to(target).as_posix()
            key = relative.casefold()
            if key in actual:
                raise RuntimeError(f"Duplicate case-insensitive live target path: {relative}")
            actual[key] = path
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatches = []
    total = 0
    verified_count = 0
    aggregate = hashlib.sha256()
    print(f"[VERIFY] Rehashing isolated target during {phase}: {len(expected_rows):,} files...")
    for index, row in enumerate(expected_rows, 1):
        relative = str(row["path"])
        path = actual.get(relative.casefold())
        if path is None:
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == int(row["size_bytes"]) and digest == str(row["sha256"])
        if not ok and len(mismatches) < 100:
            mismatches.append({"path": relative, "size_bytes": size, "sha256": digest})
        total += size
        verified_count += int(ok)
        aggregate.update(relative.casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        if index % 5000 == 0 or index == len(expected_rows):
            print(f"[VERIFY] {phase}: {index:,}/{len(expected_rows):,} files verified")
    result = {
        "verified": (
            not missing and not unexpected and not mismatches and not symlinks
            and len(actual) == EXPECTED_TARGET_COUNT
            and verified_count == EXPECTED_TARGET_COUNT
            and total == EXPECTED_TARGET_BYTES
            and aggregate.hexdigest() == EXPECTED_TARGET_TREE
        ),
        "phase": phase,
        "file_count": len(actual),
        "verified_file_count": verified_count,
        "total_bytes": total,
        "tree_sha256": aggregate.hexdigest(),
        "missing": missing[:100],
        "unexpected": unexpected[:100],
        "mismatches": mismatches,
        "symlinks": symlinks[:100],
    }
    if not result["verified"]:
        raise RuntimeError(f"Isolated target verification failed during {phase}")
    return result


def activate_psutil(root: Path):
    target = root / "Runtime/ComfyUI/site-packages"
    site.addsitedir(str(target))
    import psutil  # type: ignore
    return psutil


def process_safety(root: Path) -> dict[str, Any]:
    psutil = activate_psutil(root)
    forbidden = ("launch_comfyui_isolated.py", "manage_comfyui_normal.py", "comfyui\\main.py", "comfyui/main.py", "foxai_web.py")
    findings = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(str(item) for item in (proc.info.get("cmdline") or []))
            folded = cmdline.casefold()
            if any(marker in folded for marker in forbidden):
                findings.append({"pid": proc.info.get("pid"), "name": proc.info.get("name"), "exe": proc.info.get("exe"), "cmdline": cmdline})
        except Exception:
            continue
    listeners = []
    for connection in psutil.net_connections(kind="tcp"):
        local = getattr(connection, "laddr", None)
        if not local:
            continue
        port = getattr(local, "port", local[1] if len(local) > 1 else 0)
        status = str(getattr(connection, "status", ""))
        if int(port or 0) == 8188 and status.upper() == "LISTEN":
            ip = getattr(local, "ip", local[0] if len(local) else "")
            listeners.append({"ip": str(ip), "port": 8188, "pid": getattr(connection, "pid", None), "status": status})
    result = {"verified": not findings and not listeners, "matching_processes": findings, "port_8188_listeners": listeners}
    if not result["verified"]:
        raise RuntimeError("C3J requires FOXAI WebUI and ComfyUI lifecycle processes to be stopped")
    return result


def verify_candidate_payload(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    candidate_root = package_root / "Candidates"
    rows = []
    for record in manifest["files"]:
        rows.append(verify_exact_file(
            candidate_root / PurePosixPath(record["path"]),
            int(record["candidate_size_bytes"]),
            str(record["candidate_sha256"]),
        ))
    manager_text = (candidate_root / "System/PortableRuntime/manage_comfyui_normal.py").read_text(encoding="utf-8")
    web_text = (candidate_root / "core/foxai_web.py").read_text(encoding="utf-8")
    policy = read_json(candidate_root / "System/PortableRuntime/COMFYUI_NORMAL_POLICY.json")
    compile(manager_text, "manage_comfyui_normal.py", "exec")
    compile(web_text, "core/foxai_web.py", "exec")
    required_manager = (
        "--disable-all-custom-nodes", "127.0.0.1", "8188", "CTRL_BREAK_EVENT",
        "unknown process", "force-kill was not performed", "normal_instance.json",
        "health_receipt.json", "stop_receipt.json",
    )
    for marker in required_manager:
        if marker.casefold() not in manager_text.casefold():
            raise RuntimeError(f"Normal manager is missing required marker: {marker}")
    forbidden_manager = ("taskkill", ".kill()", "subprocess.call(", "requests.get(", "http://0.0.0.0")
    for marker in forbidden_manager:
        if marker.casefold() in manager_text.casefold():
            raise RuntimeError(f"Normal manager contains forbidden behavior: {marker}")
    if policy.get("policy_id") != POLICY_ID:
        raise RuntimeError("Candidate normal policy identity changed")
    if web_text.count("def comfy_normal_call(") != 1:
        raise RuntimeError("Candidate WebUI normal-controller helper is not exact")
    for route in ("/api/launch/comfy", "/api/status/comfy", "/api/stop/comfy"):
        if route not in web_text:
            raise RuntimeError(f"Candidate WebUI is missing route {route}")
    if "launch(comfy_isolated_cmd()" in web_text:
        raise RuntimeError("Candidate WebUI retains a direct unmanaged ComfyUI launch")
    for relative in (
        "START_COMFYUI_NORMAL.bat", "STOP_COMFYUI_NORMAL.bat", "STATUS_COMFYUI_NORMAL.bat",
        "START_COMFYUI_ISOLATED.bat", "Start ComfyUI CPU.bat", "Launch FOXAI Workshop.bat",
        "START_FOXAI_CLEAN.bat", "START_FOXAI_WORKSHOP_PORTABLE.bat",
    ):
        text = (candidate_root / relative).read_text(encoding="utf-8", errors="replace").casefold()
        if relative in {"START_COMFYUI_ISOLATED.bat", "Start ComfyUI CPU.bat"}:
            if "start_comfyui_normal.bat" not in text:
                raise RuntimeError(f"Compatibility launcher does not delegate to normal controller: {relative}")
        elif "manage_comfyui_normal.py" not in text:
            raise RuntimeError(f"Candidate launcher does not use normal controller: {relative}")
        if "launch_comfyui_isolated.py\" --root" in text:
            raise RuntimeError(f"Candidate launcher retains direct activator execution: {relative}")
    return {"verified": True, "file_count": len(rows), "files": rows, "python_compile": True, "static_policy_review": True}


def current_apply_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    statuses = []
    for record in manifest["files"]:
        live = root / PurePosixPath(record["path"])
        if live.is_symlink():
            raise RuntimeError(f"C3J write path is a symlink: {live}")
        exists = live.is_file()
        digest = sha256_file(live) if exists else None
        if record["action"] == "replace":
            status = "before" if exists and digest == record["expected_before_sha256"] else "after" if exists and digest == record["candidate_sha256"] else "unexpected"
        else:
            status = "before" if not exists else "after" if digest == record["candidate_sha256"] else "unexpected"
        rows.append({"path": record["path"], "action": record["action"], "exists": exists, "sha256": digest, "status": status})
        statuses.append(status)
    if any(item == "unexpected" for item in statuses):
        raise RuntimeError("One or more C3J paths differ from both exact before and approved candidate states")
    if all(item == "before" for item in statuses):
        mode = "ready_to_apply"
    elif all(item == "after" for item in statuses):
        mode = "already_applied"
    else:
        raise RuntimeError("C3J paths are in a mixed partial state and require manual review")
    return {"verified": True, "mode": mode, "files": rows}


def lifecycle_storage_snapshot(root: Path) -> dict[str, Any]:
    rows = []
    for relative in ("Runtime/ComfyUI/state", "Runtime/ComfyUI/logs/normal"):
        path = root / relative
        rows.append({"path": relative, "exists": path.exists(), "is_dir": path.is_dir(), "is_symlink": path.is_symlink()})
    return {"verified": all(not row["exists"] for row in rows), "paths": rows}


def protected_snapshot(root: Path) -> dict[str, Any]:
    rows = []
    for relative in (
        "Runtime/Desktop/python/python.exe",
        "ComfyUI/main.py",
        "System/PortableRuntime/launch_comfyui_isolated.py",
        "Install ComfyUI Requirements.bat",
    ):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Protected sentinel is missing or unsafe: {relative}")
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"verified": True, "files": rows}


def backup_sources(root: Path, output: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for record in manifest["files"]:
        if record["action"] != "replace":
            continue
        live = root / PurePosixPath(record["path"])
        backup = output / "BACKUP" / PurePosixPath(record["path"])
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, backup)
        if sha256_file(backup) != record["expected_before_sha256"]:
            raise RuntimeError(f"Backup verification failed: {record['path']}")
        rows.append({"path": record["path"], "backup": str(backup), "size_bytes": backup.stat().st_size, "sha256": record["expected_before_sha256"]})
    return {"verified": True, "file_count": len(rows), "files": rows}


def stage_candidates(root: Path, package_root: Path, manifest: dict[str, Any], rid: str) -> dict[str, Any]:
    rows = []
    for index, record in enumerate(manifest["files"], 1):
        live = root / PurePosixPath(record["path"])
        if not live.parent.is_dir() or live.parent.is_symlink():
            raise RuntimeError(f"Destination parent is missing or unsafe: {live.parent}")
        temporary = live.parent / f".{live.name}.C3J_NEW_{rid}_{index:02d}"
        if temporary.exists() or temporary.is_symlink():
            raise RuntimeError(f"C3J staging path already exists: {temporary}")
        shutil.copy2(package_root / "Candidates" / PurePosixPath(record["path"]), temporary)
        if sha256_file(temporary) != record["candidate_sha256"]:
            raise RuntimeError(f"Staged candidate hash mismatch: {record['path']}")
        rows.append({"path": record["path"], "temporary": str(temporary), "sha256": record["candidate_sha256"]})
    return {"verified": True, "file_count": len(rows), "files": rows}


def cleanup_staging(staging: dict[str, Any]) -> None:
    for row in staging.get("files", []):
        path = Path(row["temporary"])
        if path.is_file() and not path.is_symlink():
            path.unlink()


def commit_files(root: Path, manifest: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    staged = {row["path"]: Path(row["temporary"]) for row in staging["files"]}
    order = [
        "System/PortableRuntime/COMFYUI_NORMAL_POLICY.json",
        "System/PortableRuntime/manage_comfyui_normal.py",
        "STATUS_COMFYUI_NORMAL.bat",
        "STOP_COMFYUI_NORMAL.bat",
        "START_COMFYUI_NORMAL.bat",
        "START_COMFYUI_ISOLATED.bat",
        "Start ComfyUI CPU.bat",
        "Launch FOXAI Workshop.bat",
        "START_FOXAI_CLEAN.bat",
        "START_FOXAI_WORKSHOP_PORTABLE.bat",
        "core/foxai_web.py",
    ]
    rows = []
    for relative in order:
        record = next(item for item in manifest["files"] if item["path"] == relative)
        live = root / PurePosixPath(relative)
        os.replace(staged[relative], live)
        digest = sha256_file(live)
        if digest != record["candidate_sha256"]:
            raise RuntimeError(f"Post-commit hash mismatch: {relative}")
        rows.append({"path": relative, "action": record["action"], "sha256": digest, "committed": True})
    return {"verified": True, "method": "same-volume os.replace per exact file", "files": rows}


def verify_applied(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for record in manifest["files"]:
        rows.append(verify_exact_file(root / PurePosixPath(record["path"]), int(record["candidate_size_bytes"]), record["candidate_sha256"]))
    manager = (root / "System/PortableRuntime/manage_comfyui_normal.py").read_text(encoding="utf-8")
    web = (root / "core/foxai_web.py").read_text(encoding="utf-8")
    compile(manager, "manage_comfyui_normal.py", "exec")
    compile(web, "core/foxai_web.py", "exec")
    return {"verified": True, "file_count": len(rows), "files": rows, "python_compile": True}


def rollback(root: Path, output: Path, manifest: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    cleanup_staging(staging)
    actions = []
    issues = []
    for record in reversed(manifest["files"]):
        live = root / PurePosixPath(record["path"])
        try:
            if record["action"] == "replace":
                backup = output / "BACKUP" / PurePosixPath(record["path"])
                if not backup.is_file() or sha256_file(backup) != record["expected_before_sha256"]:
                    raise RuntimeError("Exact backup is missing or mismatched")
                temporary = live.parent / f".{live.name}.C3J_ROLLBACK"
                if temporary.exists():
                    temporary.unlink()
                shutil.copy2(backup, temporary)
                os.replace(temporary, live)
                if sha256_file(live) != record["expected_before_sha256"]:
                    raise RuntimeError("Restored hash mismatch")
                actions.append({"path": record["path"], "action": "restored", "verified": True})
            else:
                if live.exists():
                    if not live.is_file() or live.is_symlink() or sha256_file(live) != record["candidate_sha256"]:
                        raise RuntimeError("Added path cannot be safely removed")
                    live.unlink()
                actions.append({"path": record["path"], "action": "removed_added_file", "verified": not live.exists()})
        except Exception as exc:
            issues.append({"path": record["path"], "error": str(exc)})
    return {"verified": not issues, "actions": actions, "issues": issues}


def evidence_integrity(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C3J_REVIEW.zip"}:
            continue
        relative = path.relative_to(output).as_posix()
        rows.append({"file": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def review_zip(output: Path) -> Path:
    destination = output / "UPLOAD_THIS_C3J_REVIEW.zip"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if not path.is_file() or path == destination or "BACKUP" in path.relative_to(output).parts:
                continue
            archive.write(path, path.relative_to(output).as_posix())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package-root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    package_root = Path(args.package_root).resolve(strict=True)
    if package_root.name != PACKAGE_NAME or package_root.parent != root:
        raise RuntimeError("C3J package must be extracted directly under the FOXAI root")

    rid = run_id()
    output = package_root / "APPLY_OUTPUT" / rid
    output.mkdir(parents=True, exist_ok=False)
    started = now_utc()
    classification = BLOCKED
    verified = False
    apply_started = False
    rollback_result = None
    manifest: dict[str, Any] = {}
    staging: dict[str, Any] = {"files": []}
    try:
        print("[C3J] Verifying sealed package and operator-approved scope...")
        package_result = verify_package(package_root)
        write_json(output / "package_verification.json", package_result)
        manifest = read_json(package_root / "C3J_APPLY_MANIFEST.json")
        if manifest.get("write_path_count") != 11 or manifest.get("replace_count") != 6 or manifest.get("add_count") != 5:
            raise RuntimeError("C3J manifest is not the approved 6 replacements plus 5 additions")
        if manifest.get("policy_id") != POLICY_ID or not manifest.get("no_launch"):
            raise RuntimeError("C3J approval or policy identity changed")
        write_json(output / "operator_approval.json", {
            "verified": True,
            "approval_text": manifest["operator_approval_text"],
            "policy_id": POLICY_ID,
            "no_launch": True,
        })
        print("[C3J] Revalidating exact accepted C3I evidence...")
        c3i = verify_c3i(root)
        write_json(output / "c3i_input_verification.json", c3i)
        print("[C3J] Confirming FOXAI WebUI and ComfyUI lifecycle processes are stopped...")
        process_result = process_safety(root)
        write_json(output / "process_safety.json", process_result)
        inventory_path, inventory = load_c3e_inventory(root)
        write_json(output / "c3e_inventory_binding.json", {"verified": True, "path": str(inventory_path), "sha256": C3E_INVENTORY_SHA256})
        target_before = verify_target(root, inventory, "before_c3j")
        write_json(output / "isolated_target_before.json", target_before)
        storage_before = lifecycle_storage_snapshot(root)
        write_json(output / "lifecycle_storage_before.json", storage_before)
        if not storage_before["verified"]:
            raise RuntimeError("Normal lifecycle state/log directories already exist; exact review is required before C3J")
        protected_before = protected_snapshot(root)
        write_json(output / "protected_before.json", protected_before)
        print("[C3J] Validating all 11 exact candidates without executing them...")
        candidate_result = verify_candidate_payload(package_root, manifest)
        write_json(output / "candidate_verification.json", candidate_result)
        state_before = current_apply_state(root, manifest)
        write_json(output / "apply_state_before.json", state_before)

        if state_before["mode"] == "already_applied":
            applied = verify_applied(root, manifest)
            write_json(output / "applied_file_verification.json", applied)
            target_after = verify_target(root, inventory, "already_applied_review")
            write_json(output / "isolated_target_after.json", target_after)
            storage_after = lifecycle_storage_snapshot(root)
            write_json(output / "lifecycle_storage_after.json", storage_after)
            protected_after = protected_snapshot(root)
            write_json(output / "protected_after.json", protected_after)
            if protected_after != protected_before or not storage_after["verified"]:
                raise RuntimeError("Protected or lifecycle-storage boundary changed")
            classification = ALREADY
            verified = True
        else:
            print("[C3J] Creating exact backups for six replacements...")
            backup = backup_sources(root, output, manifest)
            write_json(output / "backup_manifest.json", backup)
            staging = stage_candidates(root, package_root, manifest, rid)
            write_json(output / "staging_manifest.json", staging)
            apply_started = True
            print("[C3J] Applying five additions and six replacements atomically...")
            commit = commit_files(root, manifest, staging)
            write_json(output / "commit_receipt.json", commit)
            applied = verify_applied(root, manifest)
            write_json(output / "applied_file_verification.json", applied)
            target_after = verify_target(root, inventory, "after_c3j")
            write_json(output / "isolated_target_after.json", target_after)
            storage_after = lifecycle_storage_snapshot(root)
            write_json(output / "lifecycle_storage_after.json", storage_after)
            protected_after = protected_snapshot(root)
            write_json(output / "protected_after.json", protected_after)
            if protected_after != protected_before:
                raise RuntimeError("Protected sentinels changed during C3J")
            if not storage_after["verified"] or storage_after != storage_before:
                raise RuntimeError("C3J created or changed normal lifecycle storage")
            classification = SUCCESS
            verified = True

        write_json(output / "C3K_TEST_CONTRACT.json", {
            "verified": True,
            "next_gate": "USB C3K controlled normal lifecycle start/status/stop test",
            "fresh_explicit_operator_approval_required": True,
            "profile": POLICY_ID,
            "test_sequence": ["status STOPPED", "start no-browser", "status HEALTHY", "stop", "status STOPPED"],
            "custom_nodes_disabled": True,
            "listen": "127.0.0.1:8188",
            "leave_running": False,
            "no_launch_performed_by_c3j": True,
        })
    except Exception as exc:
        write_json(output / "failure.json", {"error": str(exc), "traceback": traceback.format_exc(), "apply_started": apply_started, "timestamp": now_utc()})
        if apply_started and manifest:
            rollback_result = rollback(root, output, manifest, staging)
            write_json(output / "rollback_receipt.json", rollback_result)
            classification = ROLLED_BACK if rollback_result["verified"] else PARTIAL
        else:
            cleanup_staging(staging)
        verified = False

    receipt = {
        "action": "foxai_usbc3j_normal_enablement_apply",
        "state": "normal_enablement_applied_verified_no_launch" if verified else "blocked_fail_closed",
        "started": started,
        "completed": now_utc(),
        "root": str(root),
        "output": str(output),
        "verified": verified,
        "classification": classification,
        "policy_id": POLICY_ID,
        "write_path_count": manifest.get("write_path_count", 0) if manifest else 0,
        "replace_count": manifest.get("replace_count", 0) if manifest else 0,
        "add_count": manifest.get("add_count", 0) if manifest else 0,
        "automatic_rollback_performed": rollback_result is not None,
        "automatic_rollback_verified": rollback_result.get("verified") if rollback_result else None,
        "state_or_log_directory_created": False,
        "runtime_target_modified": False,
        "package_install": False,
        "package_uninstall": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "next_gate": "C3K controlled normal lifecycle test requires fresh explicit operator approval" if verified else "Review failure evidence before continuing",
    }
    write_json(output / "receipt.json", receipt)
    write_json(output / "classification.json", {
        "mode": classification,
        "verified": verified,
        "live_change": verified,
        "network_access": False,
        "comfyui_launched": False,
        "next_gate": receipt["next_gate"],
    })
    report = [
        "# FOXAI USB C3J — Normal Enablement Apply",
        "",
        f"- Classification: `{classification}`",
        f"- Verified: `{verified}`",
        f"- Policy: `{POLICY_ID}`",
        f"- Exact live files integrated: **{receipt['write_path_count']}**",
        "- ComfyUI launched: **False**",
        "- Normal state/log directories created: **False**",
        "- Network access: **False**",
        "",
        "The first normal lifecycle start/status/stop test remains deferred to C3K and requires fresh explicit operator approval.",
    ]
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    evidence_integrity(output)
    review_zip(output)
    if verified:
        print(f"[COMPLETE] {classification}")
        print("C3J applied and verified the normal lifecycle wiring without launching ComfyUI.")
        print("Upload UPLOAD_THIS_C3J_REVIEW.zip before C3K.")
        return 0
    print(f"[STOPPED] {classification}")
    print("C3J did not launch ComfyUI. Review the evidence bundle before continuing.")
    return 19


if __name__ == "__main__":
    raise SystemExit(main())
