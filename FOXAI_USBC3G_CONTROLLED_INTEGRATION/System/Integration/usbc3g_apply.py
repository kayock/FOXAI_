#!/usr/bin/env python3
"""USB C3G controlled no-launch integration apply.

Applies only the eight exact C3F-reviewed integration files after verifying the
accepted C3F evidence, the committed C3E isolated target, the current live
source hashes, and the sealed C3G candidate payload. No launcher or application
is executed. Any partial apply is rolled back to the exact backups before exit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE_NAME = "FOXAI_USBC3G_CONTROLLED_INTEGRATION"
EXPECTED_C3F_RUN = "20260718T031624Z"
EXPECTED_C3F_FILES = {
    "evidence_integrity.json": (175907, "169ed0b698cc9247ab1f565ff62cb78000ade8c9348e839cc50370ed325b43ed"),
    "classification.json": (318, "24aa30939f19087afecf96256b3534580e141f9f9dc7eaa7d382d66dd830d536"),
    "isolated_target_reverification.json": (465, "d3c83570662f50b8c54a991d337aea88310a7a8fe95cb77b0b29b6d0a7203aa3"),
    "portable_activation_probe.json": (9565, "48b7af4ca451cc648b137211ce0b27052bfe717c7de9a68587c4138bc1565f85"),
    "proposed_c3g_summary.json": (1607, "9e501878c9dc5cbd8d08b23b8410d923f841ea53d0ee0a33790b5013d30095e2"),
    "PROPOSED_C3G_CHANGESET/PATCH_INDEX.json": (1394, "fd07ffaf5a2680c5ce7699e0fde43f980907a646e56a5a779935b3cc9c29aa3b"),
    "PROPOSED_C3G_CHANGESET/ACTIVATION_CONTRACT.json": (839, "9941d25b71914d1ed4222d1ee0a28dec598307b9d99917020d31211bbf819acc"),
}
EXPECTED_C3E_INVENTORY_REL = (
    "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL/INSTALL_OUTPUT/"
    "20260718T023211Z/installed_file_inventory_final.json"
)
EXPECTED_C3E_INVENTORY_SIZE = 7_272_613
EXPECTED_C3E_INVENTORY_SHA256 = "d55a3d8c8c81c1ce0aaf3ebb98a5c8345c8d3be75915a450786c29cb3b66f16b"
EXPECTED_TARGET_COUNT = 39_046
EXPECTED_TARGET_BYTES = 1_520_221_467
EXPECTED_TARGET_TREE_SHA256 = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"
SUCCESS_CLASSIFICATION = "C3G_INTEGRATED_VERIFIED_NO_LAUNCH_READY_FOR_C3H_APPROVAL"
ALREADY_CLASSIFICATION = "C3G_ALREADY_INTEGRATED_VERIFIED_NO_LAUNCH_READY_FOR_C3H_APPROVAL"
ROLLED_BACK_CLASSIFICATION = "C3G_BLOCKED_ROLLED_BACK_NO_LAUNCH"
PARTIAL_CLASSIFICATION = "C3G_BLOCKED_PARTIAL_STATE_REQUIRES_MANUAL_REVIEW"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")


def verify_exact_file(path: Path, size: int, digest: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Required exact file missing or unsafe: {path}")
    actual_size = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_size != size or actual_hash != digest:
        raise RuntimeError(
            f"Exact file mismatch: {path} size={actual_size}/{size} "
            f"sha256={actual_hash}/{digest}"
        )
    return {"path": str(path), "size_bytes": actual_size, "sha256": actual_hash, "verified": True}


def verify_package(package_root: Path) -> dict[str, Any]:
    integrity_path = package_root / "PACKAGE_INTEGRITY.json"
    manifest = json.loads(integrity_path.read_text(encoding="utf-8"))
    rows = []
    for record in manifest["files"]:
        path = package_root / PurePosixPath(record["path"])
        rows.append(verify_exact_file(path, int(record["size_bytes"]), record["sha256"]))
    return {"verified": True, "file_count": len(rows), "files": rows}


def verify_c3f(root: Path) -> dict[str, Any]:
    base = root / "FOXAI_USBC3F_CONTROLLED_ACTIVATION_PREFLIGHT" / "PREFLIGHT_OUTPUT" / EXPECTED_C3F_RUN
    rows = []
    for relative, (size, digest) in EXPECTED_C3F_FILES.items():
        rows.append(verify_exact_file(base / PurePosixPath(relative), size, digest))
    classification = json.loads((base / "classification.json").read_text(encoding="utf-8"))
    target_summary = json.loads((base / "isolated_target_reverification.json").read_text(encoding="utf-8"))
    probe = json.loads((base / "portable_activation_probe.json").read_text(encoding="utf-8"))
    if classification.get("mode") != "C3F_READY_FOR_C3G_CONTROLLED_INTEGRATION_APPROVAL" or not classification.get("verified"):
        raise RuntimeError("Exact C3F evidence is not approved for C3G")
    if classification.get("launcher_change") or classification.get("network_access") or classification.get("comfyui_launched"):
        raise RuntimeError("Exact C3F safety classification is inconsistent")
    if not target_summary.get("verified") or target_summary.get("actual_tree_sha256") != EXPECTED_TARGET_TREE_SHA256:
        raise RuntimeError("C3F exact target summary is not the accepted target")
    if not probe.get("verified") or not probe.get("no_launch") or probe.get("network_access") or probe.get("process_launch") or probe.get("server_bind"):
        raise RuntimeError("C3F activation probe safety result is not accepted")
    return {"verified": True, "base": str(base), "files": rows, "classification": classification["mode"]}


def load_c3e_inventory(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / PurePosixPath(EXPECTED_C3E_INVENTORY_REL)
    verify_exact_file(path, EXPECTED_C3E_INVENTORY_SIZE, EXPECTED_C3E_INVENTORY_SHA256)
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not data.get("verified")
        or data.get("file_count") != EXPECTED_TARGET_COUNT
        or data.get("total_bytes") != EXPECTED_TARGET_BYTES
        or data.get("tree_sha256") != EXPECTED_TARGET_TREE_SHA256
        or len(data.get("files", [])) != EXPECTED_TARGET_COUNT
    ):
        raise RuntimeError("Exact C3E installed inventory does not match the accepted target")
    return path, data


def verify_target(root: Path, inventory: dict[str, Any], phase: str) -> dict[str, Any]:
    target = root / "Runtime" / "ComfyUI" / "site-packages"
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError(f"Committed isolated target missing or unsafe: {target}")

    expected_paths: set[str] = set()
    seen_casefold: set[str] = set()
    digest = hashlib.sha256()
    total = 0
    mismatches: list[dict[str, Any]] = []
    symlinks: list[str] = []

    for record in inventory["files"]:
        relative = record["path"]
        folded = relative.casefold()
        if folded in seen_casefold:
            raise RuntimeError(f"Duplicate case-insensitive target inventory path: {relative}")
        seen_casefold.add(folded)
        expected_paths.add(relative)
        path = target / PurePosixPath(relative)
        if path.is_symlink():
            symlinks.append(relative)
            continue
        if not path.is_file():
            mismatches.append({"path": relative, "issue": "missing"})
            continue
        size = path.stat().st_size
        actual_hash = sha256_file(path)
        total += size
        if size != int(record["size_bytes"]) or actual_hash != record["sha256"]:
            mismatches.append({
                "path": relative,
                "issue": "size_or_sha256",
                "expected_size": record["size_bytes"],
                "actual_size": size,
                "expected_sha256": record["sha256"],
                "actual_sha256": actual_hash,
            })
        digest.update(relative.casefold().encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(actual_hash.encode("ascii"))
        digest.update(b"\n")

    actual_paths: set[str] = set()
    for path in target.rglob("*"):
        if path.is_symlink():
            symlinks.append(path.relative_to(target).as_posix())
        elif path.is_file():
            actual_paths.add(path.relative_to(target).as_posix())
    unexpected = sorted(actual_paths - expected_paths, key=str.casefold)
    missing = sorted(expected_paths - actual_paths, key=str.casefold)
    actual_tree = digest.hexdigest()
    result = {
        "verified": not mismatches and not symlinks and not unexpected and not missing
        and len(actual_paths) == EXPECTED_TARGET_COUNT
        and total == EXPECTED_TARGET_BYTES
        and actual_tree == EXPECTED_TARGET_TREE_SHA256,
        "phase": phase,
        "target": str(target),
        "file_count": len(actual_paths),
        "total_bytes": total,
        "tree_sha256": actual_tree,
        "expected_file_count": EXPECTED_TARGET_COUNT,
        "expected_total_bytes": EXPECTED_TARGET_BYTES,
        "expected_tree_sha256": EXPECTED_TARGET_TREE_SHA256,
        "missing": missing,
        "unexpected": unexpected,
        "mismatches": mismatches,
        "symlinks": sorted(set(symlinks), key=str.casefold),
    }
    if not result["verified"]:
        raise RuntimeError(f"Isolated target verification failed during {phase}")
    return result


def validate_candidate_payload(package_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    candidate_root = package_root / "Candidates"
    rows = []
    for record in manifest["files"]:
        path = candidate_root / PurePosixPath(record["path"])
        rows.append(verify_exact_file(path, int(record["candidate_size_bytes"]), record["candidate_sha256"]))

    web = (candidate_root / "core" / "foxai_web.py").read_text(encoding="utf-8")
    helper = (candidate_root / "System" / "PortableRuntime" / "launch_comfyui_isolated.py").read_text(encoding="utf-8")
    compile(web, "core/foxai_web.py", "exec")
    compile(helper, "System/PortableRuntime/launch_comfyui_isolated.py", "exec")
    if web.count("def comfy_isolated_cmd():") != 1 or web.count("launch(comfy_isolated_cmd()") != 2:
        raise RuntimeError("Candidate foxai_web isolated-launch integration markers are not exact")
    if "launch(pycmd()+[str(COMFY_MAIN),'--cpu']" in web:
        raise RuntimeError("Candidate foxai_web still contains the reviewed legacy direct launch")
    if "runpy.run_path(str(main_py), run_name=\"__main__\")" not in helper:
        raise RuntimeError("Candidate isolated activator launch boundary is incomplete")

    launch_bats = [
        "START_COMFYUI_ISOLATED.bat",
        "Start ComfyUI CPU.bat",
        "Launch FOXAI Workshop.bat",
        "START_FOXAI_CLEAN.bat",
        "START_FOXAI_WORKSHOP_PORTABLE.bat",
    ]
    for relative in launch_bats:
        text = (candidate_root / relative).read_text(encoding="utf-8").casefold()
        if "launch_comfyui_isolated.py" not in text or "--cpu" not in text:
            raise RuntimeError(f"Candidate launcher lacks isolated CPU activation: {relative}")
        if "python main.py --cpu" in text:
            raise RuntimeError(f"Candidate launcher retains bare host-Python launch: {relative}")
    installer = (candidate_root / "Install ComfyUI Requirements.bat").read_text(encoding="utf-8").casefold()
    if "-m pip install" in installer or "pip.exe install" in installer:
        raise RuntimeError("Legacy dependency mutation surface is not disabled")
    return {"verified": True, "file_count": len(rows), "files": rows, "python_compile": True, "static_launcher_review": True}


def current_integration_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    statuses = []
    for record in manifest["files"]:
        live = root / PurePosixPath(record["path"])
        if live.is_symlink():
            raise RuntimeError(f"Integration path is a symlink: {live}")
        exists = live.is_file()
        actual_hash = sha256_file(live) if exists else None
        if record["action"] == "replace":
            if exists and actual_hash == record["expected_before_sha256"]:
                status = "before"
            elif exists and actual_hash == record["candidate_sha256"]:
                status = "after"
            else:
                status = "unexpected"
        else:
            if not exists:
                status = "before"
            elif actual_hash == record["candidate_sha256"]:
                status = "after"
            else:
                status = "unexpected"
        statuses.append(status)
        rows.append({"path": record["path"], "action": record["action"], "exists": exists, "sha256": actual_hash, "status": status})
    if any(status == "unexpected" for status in statuses):
        raise RuntimeError("One or more integration paths differ from both the exact before and exact approved state")
    if all(status == "before" for status in statuses):
        mode = "ready_to_apply"
    elif all(status == "after" for status in statuses):
        mode = "already_applied"
    else:
        mode = "mixed_partial_state"
        raise RuntimeError("Integration paths are in a mixed before/after state; manual review is required")
    return {"verified": True, "mode": mode, "files": rows}


def snapshot_protected(root: Path) -> dict[str, Any]:
    sentinels = [
        root / "Runtime" / "Desktop" / "python" / "python.exe",
        root / "ComfyUI" / "main.py",
    ]
    rows = []
    for path in sentinels:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Protected sentinel missing or unsafe: {path}")
        rows.append({"path": str(path.relative_to(root)).replace("\\", "/"), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"verified": True, "files": rows}


def compare_protected(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    verified = before == after
    result = {"verified": verified, "before": before, "after": after}
    if not verified:
        raise RuntimeError("Protected sentinel changed during C3G")
    return result


def backup_sources(root: Path, output: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    backup_root = output / "BACKUP"
    rows = []
    for record in manifest["files"]:
        if record["action"] != "replace":
            continue
        live = root / PurePosixPath(record["path"])
        backup = backup_root / PurePosixPath(record["path"])
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, backup)
        if sha256_file(backup) != record["expected_before_sha256"]:
            raise RuntimeError(f"Backup verification failed: {record['path']}")
        rows.append({"path": record["path"], "backup": str(backup), "sha256": record["expected_before_sha256"], "size_bytes": backup.stat().st_size})
    return {"verified": True, "backup_root": str(backup_root), "file_count": len(rows), "files": rows}


def stage_candidates(root: Path, package_root: Path, manifest: dict[str, Any], rid: str) -> dict[str, Any]:
    rows = []
    for index, record in enumerate(manifest["files"], start=1):
        live = root / PurePosixPath(record["path"])
        live.parent.mkdir(parents=True, exist_ok=True)
        temporary = live.parent / f".{live.name}.C3G_NEW_{rid}_{index:02d}"
        if temporary.exists() or temporary.is_symlink():
            raise RuntimeError(f"C3G staging path already exists: {temporary}")
        source = package_root / "Candidates" / PurePosixPath(record["path"])
        shutil.copy2(source, temporary)
        if sha256_file(temporary) != record["candidate_sha256"]:
            raise RuntimeError(f"Staged candidate hash mismatch: {record['path']}")
        rows.append({"path": record["path"], "temporary": str(temporary), "candidate_sha256": record["candidate_sha256"]})
    return {"verified": True, "file_count": len(rows), "files": rows}


def cleanup_staging(staging: dict[str, Any]) -> None:
    for row in staging.get("files", []):
        path = Path(row["temporary"])
        if path.exists() and path.is_file() and not path.is_symlink():
            path.unlink()


def commit_files(root: Path, manifest: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    by_path = {row["path"]: Path(row["temporary"]) for row in staging["files"]}
    # Helper first, direct operator launcher second, legacy/dependent surfaces next, WebUI last.
    order = [
        "System/PortableRuntime/launch_comfyui_isolated.py",
        "START_COMFYUI_ISOLATED.bat",
        "Install ComfyUI Requirements.bat",
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
        os.replace(by_path[relative], live)
        actual_hash = sha256_file(live)
        if actual_hash != record["candidate_sha256"]:
            raise RuntimeError(f"Post-replace hash mismatch: {relative}")
        rows.append({"path": relative, "action": record["action"], "sha256": actual_hash, "committed": True})
    return {"verified": True, "method": "same-volume os.replace per exact file", "files": rows}


def verify_applied(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for record in manifest["files"]:
        live = root / PurePosixPath(record["path"])
        rows.append(verify_exact_file(live, int(record["candidate_size_bytes"]), record["candidate_sha256"]))
    web = (root / "core" / "foxai_web.py").read_text(encoding="utf-8")
    helper = (root / "System" / "PortableRuntime" / "launch_comfyui_isolated.py").read_text(encoding="utf-8")
    compile(web, "core/foxai_web.py", "exec")
    compile(helper, "System/PortableRuntime/launch_comfyui_isolated.py", "exec")
    return {"verified": True, "file_count": len(rows), "files": rows, "python_compile": True}


def rollback(root: Path, output: Path, manifest: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    actions = []
    issues = []
    cleanup_staging(staging)
    for record in reversed(manifest["files"]):
        live = root / PurePosixPath(record["path"])
        try:
            if record["action"] == "replace":
                backup = output / "BACKUP" / PurePosixPath(record["path"])
                if not backup.is_file() or sha256_file(backup) != record["expected_before_sha256"]:
                    raise RuntimeError("exact backup missing or mismatched")
                restore_temp = live.parent / f".{live.name}.C3G_ROLLBACK"
                if restore_temp.exists():
                    restore_temp.unlink()
                shutil.copy2(backup, restore_temp)
                os.replace(restore_temp, live)
                if sha256_file(live) != record["expected_before_sha256"]:
                    raise RuntimeError("restored hash mismatch")
                actions.append({"path": record["path"], "action": "restored", "verified": True})
            else:
                if live.exists():
                    if not live.is_file() or live.is_symlink() or sha256_file(live) != record["candidate_sha256"]:
                        raise RuntimeError("added path cannot be safely removed")
                    live.unlink()
                actions.append({"path": record["path"], "action": "removed_added_file", "verified": not live.exists()})
        except Exception as exc:  # noqa: BLE001
            issues.append({"path": record["path"], "error": str(exc)})
    verified = not issues
    return {"verified": verified, "actions": actions, "issues": issues}


def make_evidence_integrity(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C3G_REVIEW.zip"}:
            continue
        relative = path.relative_to(output).as_posix()
        rows.append({"file": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def make_review_zip(output: Path) -> Path:
    destination = output / "UPLOAD_THIS_C3G_REVIEW.zip"
    include = []
    for path in sorted(output.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path == destination or "BACKUP" in path.relative_to(output).parts:
            continue
        include.append(path)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in include:
            archive.write(path, path.relative_to(output).as_posix())
    return destination


def final_report(output: Path, classification: str, verified: bool, details: dict[str, Any]) -> None:
    lines = [
        "# FOXAI USB C3G — Controlled No-Launch Integration",
        "",
        f"- Classification: `{classification}`",
        f"- Verified: `{verified}`",
        f"- Launcher/source files integrated: **{details.get('write_path_count', 0)}**",
        "- ComfyUI launched: **False**",
        "- Network access: **False**",
        "- Package installation: **False**",
        "",
        "The committed isolated target was not modified. The first actual ComfyUI start remains deferred to C3H and requires fresh explicit operator approval.",
    ]
    write_path = output / "report.md"
    write_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package-root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    package_root = Path(args.package_root).resolve(strict=True)
    if package_root.name != PACKAGE_NAME or package_root.parent != root:
        raise RuntimeError("C3G package must be extracted directly under the FOXAI root")

    rid = run_id()
    output = package_root / "APPLY_OUTPUT" / rid
    output.mkdir(parents=True, exist_ok=False)
    started = now_utc()
    classification = "C3G_BLOCKED_FAIL_CLOSED_NO_LAUNCH"
    verified = False
    staging: dict[str, Any] = {"files": []}
    manifest: dict[str, Any] = {}
    apply_started = False
    rollback_result: dict[str, Any] | None = None

    try:
        package_verification = verify_package(package_root)
        write_json(output / "package_verification.json", package_verification)
        manifest = json.loads((package_root / "C3G_APPLY_MANIFEST.json").read_text(encoding="utf-8"))
        if manifest.get("write_path_count") != 8 or manifest.get("replace_count") != 6 or manifest.get("add_count") != 2:
            raise RuntimeError("C3G exact write manifest is not the approved 6 replacements plus 2 additions")
        write_json(output / "operator_approval.json", {
            "verified": True,
            "approval_text": manifest["operator_approval_text"],
            "approval_context": manifest["operator_approval_context"],
            "no_launch": True,
        })

        c3f = verify_c3f(root)
        write_json(output / "c3f_input_verification.json", c3f)
        inventory_path, inventory = load_c3e_inventory(root)
        write_json(output / "c3e_inventory_binding.json", {
            "verified": True,
            "path": str(inventory_path),
            "size_bytes": EXPECTED_C3E_INVENTORY_SIZE,
            "sha256": EXPECTED_C3E_INVENTORY_SHA256,
        })
        target_before = verify_target(root, inventory, "before_integration")
        write_json(output / "isolated_target_before.json", target_before)
        protected_before = snapshot_protected(root)
        write_json(output / "protected_before.json", protected_before)
        candidate_verification = validate_candidate_payload(package_root, manifest)
        write_json(output / "candidate_verification.json", candidate_verification)
        state_before = current_integration_state(root, manifest)
        write_json(output / "integration_state_before.json", state_before)

        if state_before["mode"] == "already_applied":
            applied = verify_applied(root, manifest)
            target_after = verify_target(root, inventory, "already_integrated_review")
            protected_after = snapshot_protected(root)
            protected_comparison = compare_protected(protected_before, protected_after)
            write_json(output / "applied_file_verification.json", applied)
            write_json(output / "isolated_target_after.json", target_after)
            write_json(output / "protected_after.json", protected_after)
            write_json(output / "protected_comparison.json", protected_comparison)
            classification = ALREADY_CLASSIFICATION
            verified = True
        else:
            backup = backup_sources(root, output, manifest)
            write_json(output / "backup_manifest.json", backup)
            staging = stage_candidates(root, package_root, manifest, rid)
            write_json(output / "staging_manifest.json", staging)
            apply_started = True
            commit = commit_files(root, manifest, staging)
            write_json(output / "commit_receipt.json", commit)
            applied = verify_applied(root, manifest)
            write_json(output / "applied_file_verification.json", applied)
            target_after = verify_target(root, inventory, "after_integration")
            write_json(output / "isolated_target_after.json", target_after)
            protected_after = snapshot_protected(root)
            write_json(output / "protected_after.json", protected_after)
            protected_comparison = compare_protected(protected_before, protected_after)
            write_json(output / "protected_comparison.json", protected_comparison)
            classification = SUCCESS_CLASSIFICATION
            verified = True

        c3h_contract = {
            "verified": True,
            "next_gate": "C3H controlled first-start",
            "requires_fresh_explicit_operator_approval": True,
            "no_launch_performed_by_c3g": True,
            "recommended_first_start": {
                "python": "Runtime/Desktop/python/python.exe",
                "activator": "System/PortableRuntime/launch_comfyui_isolated.py",
                "arguments": ["--cpu", "--disable-all-custom-nodes", "--listen", "127.0.0.1", "--port", "8188"],
                "health_endpoint": "http://127.0.0.1:8188",
            },
            "forbidden_before_c3h_review": [
                "Do not launch ComfyUI",
                "Do not modify Runtime/ComfyUI/site-packages",
                "Do not run the legacy requirements installer",
                "Do not edit the applied integration files",
            ],
        }
        write_json(output / "C3H_FIRST_START_CONTRACT.json", c3h_contract)

    except Exception as exc:  # noqa: BLE001
        error = {
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "apply_started": apply_started,
            "timestamp": now_utc(),
        }
        write_json(output / "failure.json", error)
        if apply_started and manifest:
            rollback_result = rollback(root, output, manifest, staging)
            write_json(output / "rollback_receipt.json", rollback_result)
            if rollback_result["verified"]:
                classification = ROLLED_BACK_CLASSIFICATION
            else:
                classification = PARTIAL_CLASSIFICATION
        else:
            cleanup_staging(staging)
        verified = False

    completed = now_utc()
    receipt = {
        "action": "foxai_usbc3g_controlled_no_launch_integration",
        "state": "integrated_verified_ready_for_c3h_review" if verified else "blocked_fail_closed",
        "started": started,
        "completed": completed,
        "root": str(root),
        "output": str(output),
        "verified": verified,
        "classification": classification,
        "write_path_count": manifest.get("write_path_count", 0) if manifest else 0,
        "replace_count": manifest.get("replace_count", 0) if manifest else 0,
        "add_count": manifest.get("add_count", 0) if manifest else 0,
        "automatic_rollback_performed": rollback_result is not None,
        "automatic_rollback_verified": rollback_result.get("verified") if rollback_result else None,
        "launcher_files_integrated": verified,
        "runtime_target_modified": False,
        "package_install": False,
        "package_uninstall": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "next_gate": "C3H controlled first-start requires fresh explicit operator approval" if verified else "Review failure evidence before any further action",
    }
    write_json(output / "receipt.json", receipt)
    write_json(output / "classification.json", {
        "mode": classification,
        "verified": verified,
        "launcher_change": verified,
        "network_access": False,
        "comfyui_launched": False,
        "next_gate": receipt["next_gate"],
    })
    final_report(output, classification, verified, receipt)
    make_evidence_integrity(output)
    make_review_zip(output)

    if verified:
        print(f"[COMPLETE] {classification}")
        print("C3G applied and verified the isolated integration without launching ComfyUI.")
        print("Upload UPLOAD_THIS_C3G_REVIEW.zip before C3H.")
        return 0
    print(f"[STOPPED] {classification}")
    print("C3G made no launch. Review the evidence bundle before continuing.")
    return 19


if __name__ == "__main__":
    raise SystemExit(main())
