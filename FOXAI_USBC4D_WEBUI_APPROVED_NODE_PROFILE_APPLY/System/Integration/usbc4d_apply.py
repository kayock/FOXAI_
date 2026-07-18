#!/usr/bin/env python3
"""USB C4D controlled WebUI approved-node profile apply, with no launch.

Replaces exactly three reviewed live files and adds one explicit approved-profile
BAT. Safe Normal CPU remains the default. Any partial write is rolled back to
exact verified backups. No candidate is executed by C4D.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import site
import traceback
from datetime import datetime, timezone
from typing import Any
import zipfile

PACKAGE_NAME = "FOXAI_USBC4D_WEBUI_APPROVED_NODE_PROFILE_APPLY"
C4C_RUN = "20260718T063916Z"
C4C_INTEGRITY_SHA256 = "7673333df9567c0ac47cacdfb591637e0220c0827a88607b2309ea982520ee8e"
C4C_CLASSIFICATION = "C4C_READY_FOR_C4D_WEBUI_PROFILE_APPLY_APPROVAL"
CONTRACT_ID = "FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1"
DEFAULT_PROFILE_ID = "safe-normal-cpu"
APPROVED_PROFILE_ID = "approved-custom-nodes-cpu"
APPROVED_NODE_REL = "ComfyUI/custom_nodes/websocket_image_save.py"
APPROVED_NODE_SIZE = 1348
APPROVED_NODE_SHA256 = "0b66b69eb7dab007d55bf63c5bd0f1343dcfbc2f5a350983f906ba2cd3dd5d23"
C3E_RUN = "20260718T023211Z"
C3E_INVENTORY_SHA256 = "d55a3d8c8c81c1ce0aaf3ebb98a5c8345c8d3be75915a450786c29cb3b66f16b"
EXPECTED_TARGET_COUNT = 39046
EXPECTED_TARGET_BYTES = 1520221467
EXPECTED_TARGET_TREE = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"
SUCCESS = "C4D_WEBUI_PROFILE_APPLIED_VERIFIED_NO_LAUNCH_READY_FOR_C4E_APPROVAL"
ALREADY = "C4D_ALREADY_APPLIED_VERIFIED_NO_LAUNCH_READY_FOR_C4E_APPROVAL"
ROLLED_BACK = "C4D_BLOCKED_ROLLED_BACK_NO_LAUNCH"
PARTIAL = "C4D_BLOCKED_PARTIAL_STATE_REQUIRES_MANUAL_REVIEW"
BLOCKED = "C4D_BLOCKED_FAIL_CLOSED_NO_LAUNCH"


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
        raise RuntimeError("C4D PACKAGE_INTEGRITY.json is missing")
    manifest = read_json(manifest_path)
    rows = []
    for record in manifest.get("files") or []:
        rows.append(verify_exact_file(
            package_root / PurePosixPath(str(record["path"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
        ))
    if not rows:
        raise RuntimeError("C4D package-integrity manifest is empty")
    return {"verified": True, "file_count": len(rows), "files": rows}


def verify_c4c(root: Path) -> dict[str, Any]:
    base = root / "FOXAI_USBC4C_WEBUI_APPROVED_NODE_PROFILE_REVIEW" / "REVIEW_OUTPUT" / C4C_RUN
    integrity_path = base / "evidence_integrity.json"
    if sha256_file(integrity_path) != C4C_INTEGRITY_SHA256:
        raise RuntimeError("Exact C4C evidence-integrity hash changed")
    integrity = read_json(integrity_path)
    rows = []
    for record in integrity.get("files") or []:
        rows.append(verify_exact_file(
            base / PurePosixPath(str(record["file"])),
            int(record["size_bytes"]),
            str(record["sha256"]),
        ))
    classification = read_json(base / "classification.json")
    node = read_json(base / "approved_node_verification.json")
    target = read_json(base / "isolated_target_reverification.json")
    surface = read_json(base / "current_webui_profile_surface.json")
    live = read_json(base / "live_surfaces_after.json")
    contract = read_json(base / "PROPOSED_C4D_CHANGESET/APPROVED_NODE_PROFILE_CONTRACT.json")
    scope = read_json(base / "PROPOSED_C4D_CHANGESET/C4D_APPLY_SCOPE.json")
    if (
        integrity.get("verified") is not True
        or int(integrity.get("file_count", 0)) != 17
        or len(rows) != 17
        or classification.get("verified") is not True
        or classification.get("mode") != C4C_CLASSIFICATION
        or classification.get("live_change")
        or classification.get("comfyui_launched")
        or classification.get("network_access")
        or node.get("verified") is not True
        or node.get("sha256") != APPROVED_NODE_SHA256
        or int(node.get("size_bytes", 0)) != APPROVED_NODE_SIZE
        or target.get("verified") is not True
        or target.get("tree_sha256") != EXPECTED_TARGET_TREE
        or surface.get("verified") is not True
        or surface.get("safe_profile_is_default") is not True
        or surface.get("manager_has_profile_selector") is not False
        or live.get("verified") is not True
        or contract.get("contract_id") != CONTRACT_ID
        or contract.get("default_profile_id") != DEFAULT_PROFILE_ID
        or scope.get("stage") != "C4D controlled WebUI profile apply (no launch)"
    ):
        raise RuntimeError("Exact accepted C4C evidence did not reverify")
    return {
        "verified": True,
        "base": str(base),
        "evidence_file_count": len(rows),
        "classification": classification.get("mode"),
        "contract_id": contract.get("contract_id"),
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
    site.addsitedir(str(root / "Runtime/ComfyUI/site-packages"))
    import psutil  # type: ignore
    return psutil


def process_safety(root: Path) -> dict[str, Any]:
    psutil = activate_psutil(root)
    forbidden = (
        "launch_comfyui_isolated.py", "manage_comfyui_normal.py",
        "comfyui\\main.py", "comfyui/main.py", "foxai_web.py",
    )
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
        raise RuntimeError("C4D requires FOXAI WebUI and ComfyUI lifecycle processes to be stopped")
    return result


def verify_node(root: Path) -> dict[str, Any]:
    path = root / APPROVED_NODE_REL
    return verify_exact_file(path, APPROVED_NODE_SIZE, APPROVED_NODE_SHA256)


def inventory_tree(root: Path, relatives: tuple[str, ...]) -> dict[str, Any]:
    rows = []
    for relative_root in relatives:
        base = root / PurePosixPath(relative_root)
        if not base.exists():
            rows.append({"path": relative_root, "kind": "missing"})
            continue
        if base.is_symlink():
            raise RuntimeError(f"Boundary path is a symlink: {relative_root}")
        if base.is_file():
            rows.append({"path": relative_root, "kind": "file", "size_bytes": base.stat().st_size, "sha256": sha256_file(base)})
            continue
        rows.append({"path": relative_root, "kind": "directory"})
        for path in sorted(base.rglob("*"), key=lambda item: item.as_posix().casefold()):
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise RuntimeError(f"Boundary tree contains a symlink: {rel}")
            if path.is_file():
                rows.append({"path": rel, "kind": "file", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
            elif path.is_dir():
                rows.append({"path": rel, "kind": "directory"})
    return {"verified": True, "rows": rows}


def protected_snapshot(root: Path) -> dict[str, Any]:
    rows = []
    for relative in (
        "START_COMFYUI_NORMAL.bat",
        "STATUS_COMFYUI_NORMAL.bat",
        "STOP_COMFYUI_NORMAL.bat",
        "System/PortableRuntime/launch_comfyui_isolated.py",
        "ComfyUI/main.py",
        APPROVED_NODE_REL,
        "Install ComfyUI Requirements.bat",
    ):
        path = root / PurePosixPath(relative)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Protected sentinel is missing or unsafe: {relative}")
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"verified": True, "files": rows}


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
    bat_text = (candidate_root / "START_COMFYUI_APPROVED_NODES.bat").read_text(encoding="utf-8", errors="replace")
    compile(manager_text, "manage_comfyui_normal.py", "exec")
    compile(web_text, "core/foxai_web.py", "exec")
    required_manager = (
        CONTRACT_ID, DEFAULT_PROFILE_ID, APPROVED_PROFILE_ID,
        APPROVED_NODE_SHA256, "--whitelist-custom-nodes",
        "Approved custom node changed; startup refused",
        "Profile switch refused", "PROFILE_CONFLICT",
        "CTRL_BREAK_EVENT", "force-kill was not performed",
    )
    for marker in required_manager:
        if marker.casefold() not in manager_text.casefold():
            raise RuntimeError(f"Candidate manager is missing required marker: {marker}")
    for marker in ("taskkill", ".kill()", "requests.get(", "http://0.0.0.0"):
        if marker.casefold() in manager_text.casefold():
            raise RuntimeError(f"Candidate manager contains forbidden behavior: {marker}")
    if policy.get("policy_id") != CONTRACT_ID or policy.get("default_profile_id") != DEFAULT_PROFILE_ID:
        raise RuntimeError("Candidate dual-profile policy identity or default changed")
    profiles = policy.get("profiles") or []
    if [item.get("id") for item in profiles] != [DEFAULT_PROFILE_ID, APPROVED_PROFILE_ID]:
        raise RuntimeError("Candidate policy does not contain the exact ordered two-profile set")
    approved = profiles[1].get("approved_nodes") or []
    if len(approved) != 1 or approved[0].get("sha256") != APPROVED_NODE_SHA256:
        raise RuntimeError("Candidate approved-profile node hash changed")
    for marker in (
        "/api/launch/comfy/profile", "id=comfyProfile",
        "approved-custom-nodes-cpu", "Safe Normal CPU",
        "Approved Custom Nodes CPU", "Unknown ComfyUI profile",
    ):
        if marker not in web_text:
            raise RuntimeError(f"Candidate WebUI is missing profile marker: {marker}")
    if web_text.count("def comfy_normal_call(") != 1 or web_text.count("/api/launch/comfy/profile") != 2:
        raise RuntimeError("Candidate WebUI profile route/helper count is unexpected")
    if "start --profile approved-custom-nodes-cpu --source direct" not in bat_text:
        raise RuntimeError("Candidate approved-profile BAT does not request the exact profile")
    return {"verified": True, "file_count": len(rows), "files": rows, "python_compile": True, "static_policy_review": True}


def current_apply_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    statuses = []
    for record in manifest["files"]:
        live = root / PurePosixPath(record["path"])
        if live.is_symlink():
            raise RuntimeError(f"C4D write path is a symlink: {live}")
        exists = live.is_file()
        digest = sha256_file(live) if exists else None
        if record["action"] == "replace":
            status = "before" if exists and digest == record["expected_before_sha256"] else "after" if exists and digest == record["candidate_sha256"] else "unexpected"
        else:
            status = "before" if not exists else "after" if digest == record["candidate_sha256"] else "unexpected"
        rows.append({"path": record["path"], "action": record["action"], "exists": exists, "sha256": digest, "status": status})
        statuses.append(status)
    if any(item == "unexpected" for item in statuses):
        raise RuntimeError("One or more C4D paths differ from both exact before and approved candidate states")
    if all(item == "before" for item in statuses):
        mode = "ready_to_apply"
    elif all(item == "after" for item in statuses):
        mode = "already_applied"
    else:
        raise RuntimeError("C4D paths are in a mixed partial state and require manual review")
    return {"verified": True, "mode": mode, "files": rows}


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
        temporary = live.parent / f".{live.name}.C4D_NEW_{rid}_{index:02d}"
        if temporary.exists() or temporary.is_symlink():
            raise RuntimeError(f"C4D staging path already exists: {temporary}")
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
        "START_COMFYUI_APPROVED_NODES.bat",
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
                temporary = live.parent / f".{live.name}.C4D_ROLLBACK"
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
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C4D_REVIEW.zip"}:
            continue
        relative = path.relative_to(output).as_posix()
        rows.append({"file": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def review_zip(output: Path) -> Path:
    destination = output / "UPLOAD_THIS_C4D_REVIEW.zip"
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
        raise RuntimeError("C4D package must be extracted directly under the FOXAI root")

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
        print("[C4D] Verifying sealed package and approved four-file scope...")
        package_result = verify_package(package_root)
        write_json(output / "package_verification.json", package_result)
        manifest = read_json(package_root / "C4D_APPLY_MANIFEST.json")
        if manifest.get("write_path_count") != 4 or manifest.get("replace_count") != 3 or manifest.get("add_count") != 1:
            raise RuntimeError("C4D manifest is not the approved three replacements plus one addition")
        if manifest.get("contract_id") != CONTRACT_ID or not manifest.get("no_launch") or manifest.get("network_access"):
            raise RuntimeError("C4D approval, contract, or no-launch boundary changed")
        write_json(output / "operator_approval.json", {
            "verified": True,
            "approval_text": manifest["operator_approval_text"],
            "contract_id": CONTRACT_ID,
            "default_profile_id": DEFAULT_PROFILE_ID,
            "no_launch": True,
        })
        print("[C4D] Revalidating exact accepted C4C evidence...")
        c4c = verify_c4c(root)
        write_json(output / "c4c_input_verification.json", c4c)
        print("[C4D] Confirming FOXAI WebUI and ComfyUI are stopped...")
        process_result = process_safety(root)
        write_json(output / "process_safety.json", process_result)
        node_before = verify_node(root)
        write_json(output / "approved_node_before.json", node_before)
        inventory_path, inventory = load_c3e_inventory(root)
        write_json(output / "c3e_inventory_binding.json", {"verified": True, "path": str(inventory_path), "sha256": C3E_INVENTORY_SHA256})
        target_before = verify_target(root, inventory, "before_c4d")
        write_json(output / "isolated_target_before.json", target_before)
        protected_before = protected_snapshot(root)
        write_json(output / "protected_before.json", protected_before)
        operational_before = inventory_tree(root, ("Runtime/ComfyUI/state", "Runtime/ComfyUI/logs/normal"))
        write_json(output / "operational_storage_before.json", operational_before)
        print("[C4D] Validating four exact candidates without executing them...")
        candidate_result = verify_candidate_payload(package_root, manifest)
        write_json(output / "candidate_verification.json", candidate_result)
        state_before = current_apply_state(root, manifest)
        write_json(output / "apply_state_before.json", state_before)

        if state_before["mode"] == "already_applied":
            applied = verify_applied(root, manifest)
            write_json(output / "applied_file_verification.json", applied)
            classification = ALREADY
        else:
            print("[C4D] Creating exact backups for three replacements...")
            backup = backup_sources(root, output, manifest)
            write_json(output / "backup_manifest.json", backup)
            staging = stage_candidates(root, package_root, manifest, rid)
            write_json(output / "staging_manifest.json", staging)
            apply_started = True
            print("[C4D] Applying one addition and three replacements atomically...")
            commit = commit_files(root, manifest, staging)
            write_json(output / "commit_receipt.json", commit)
            applied = verify_applied(root, manifest)
            write_json(output / "applied_file_verification.json", applied)
            classification = SUCCESS

        node_after = verify_node(root)
        write_json(output / "approved_node_after.json", node_after)
        target_after = verify_target(root, inventory, "after_c4d")
        write_json(output / "isolated_target_after.json", target_after)
        protected_after = protected_snapshot(root)
        write_json(output / "protected_after.json", protected_after)
        operational_after = inventory_tree(root, ("Runtime/ComfyUI/state", "Runtime/ComfyUI/logs/normal"))
        write_json(output / "operational_storage_after.json", operational_after)
        if node_after != node_before:
            raise RuntimeError("Approved node changed during C4D")
        if protected_after != protected_before:
            raise RuntimeError("Protected sentinels changed during C4D")
        if operational_after != operational_before:
            raise RuntimeError("C4D changed normal lifecycle state or logs")
        verified = True
        write_json(output / "C4E_TEST_CONTRACT.json", {
            "verified": True,
            "next_gate": "USB C4E controlled WebUI two-profile lifecycle test",
            "fresh_explicit_operator_approval_required": True,
            "test_sequence": [
                "legacy GET starts Safe Normal CPU",
                "stop",
                "POST starts Approved Custom Nodes CPU",
                "verify SaveImageWebsocket and node hash state",
                "refuse profile switch while healthy",
                "stop",
                "final status STOPPED",
            ],
            "browser_open": False,
            "leave_running": False,
            "no_launch_performed_by_c4d": True,
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
        "action": "foxai_usbc4d_webui_approved_node_profile_apply",
        "state": "webui_profile_applied_verified_no_launch" if verified else "blocked_fail_closed",
        "started": started,
        "completed": now_utc(),
        "root": str(root),
        "output": str(output),
        "verified": verified,
        "classification": classification,
        "contract_id": CONTRACT_ID,
        "default_profile_id": DEFAULT_PROFILE_ID,
        "write_path_count": manifest.get("write_path_count", 0) if manifest else 0,
        "replace_count": manifest.get("replace_count", 0) if manifest else 0,
        "add_count": manifest.get("add_count", 0) if manifest else 0,
        "automatic_rollback_performed": rollback_result is not None,
        "automatic_rollback_verified": rollback_result.get("verified") if rollback_result else None,
        "runtime_target_modified": False,
        "approved_node_modified": False,
        "state_or_log_modified": False,
        "package_install": False,
        "package_uninstall": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "next_gate": "C4E controlled WebUI two-profile lifecycle test requires fresh explicit operator approval" if verified else "Review failure evidence before continuing",
    }
    write_json(output / "receipt.json", receipt)
    write_json(output / "classification.json", {
        "mode": classification,
        "verified": verified,
        "live_change": verified,
        "network_access": False,
        "comfyui_launched": False,
        "default_profile_id": DEFAULT_PROFILE_ID,
        "approved_profile_id": APPROVED_PROFILE_ID,
        "next_gate": receipt["next_gate"],
    })
    report = [
        "# FOXAI USB C4D — WebUI Approved Custom Node Profile Apply",
        "",
        f"- Classification: `{classification}`",
        f"- Verified: `{verified}`",
        f"- Contract: `{CONTRACT_ID}`",
        f"- Default profile: `{DEFAULT_PROFILE_ID}`",
        f"- Exact live files integrated: **{receipt['write_path_count']}**",
        "- ComfyUI launched: **False**",
        "- FOXAI WebUI launched: **False**",
        "- Network access: **False**",
        "",
        "The first WebUI two-profile lifecycle test remains deferred to C4E and requires fresh explicit operator approval.",
    ]
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    evidence_integrity(output)
    review_zip(output)
    if verified:
        print(f"[COMPLETE] {classification}")
        print("C4D applied and verified the WebUI profile integration without launching ComfyUI or FOXAI.")
        print("Upload UPLOAD_THIS_C4D_REVIEW.zip before C4E.")
        return 0
    print(f"[STOPPED] {classification}")
    print("C4D launched nothing. Review the evidence bundle before continuing.")
    return 19


if __name__ == "__main__":
    raise SystemExit(main())
