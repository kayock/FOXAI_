#!/usr/bin/env python3
"""USB C3I read-only normal enablement and retention review.

This stage performs no operational launch, network access, source edit, package
change, log pruning, or runtime mutation. It writes evidence only beneath its
own REVIEW_OUTPUT folder.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
from typing import Any, Iterable

C3H_RUN = "20260718T040138Z"
C3E_RUN = "20260718T023211Z"
C3H_CLASSIFICATION = "C3H_FIRST_START_VERIFIED_STOPPED_READY_FOR_C3I_REVIEW"
SUCCESS_CLASSIFICATION = "C3I_READY_FOR_C3J_NORMAL_ENABLEMENT_APPROVAL"
C3H_INTEGRITY_SHA256 = "8f5bfa5cc745dd63e300672238beae64f212d80a63bbc1641f68214c5476c6d9"
C3E_INVENTORY_SHA256 = "d55a3d8c8c81c1ce0aaf3ebb98a5c8345c8d3be75915a450786c29cb3b66f16b"
TARGET_REL = Path("Runtime/ComfyUI/site-packages")
EXPECTED_TARGET_COUNT = 39046
EXPECTED_TARGET_BYTES = 1520221467
EXPECTED_TARGET_TREE = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def verify_package(package_root: Path) -> dict[str, Any]:
    manifest_path = package_root / "PACKAGE_INTEGRITY.json"
    if not manifest_path.is_file():
        raise RuntimeError("C3I PACKAGE_INTEGRITY.json is missing")
    manifest = read_json(manifest_path)
    rows = manifest.get("files") or []
    verified_rows = []
    for row in rows:
        relative = str(row["path"])
        path = package_root / Path(relative)
        exists = path.is_file()
        size = path.stat().st_size if exists else None
        digest = sha256_file(path) if exists else None
        ok = exists and size == int(row["size_bytes"]) and digest == row["sha256"]
        verified_rows.append({
            "path": relative,
            "exists": exists,
            "size_bytes": size,
            "sha256": digest,
            "verified": ok,
        })
    result = {
        "verified": bool(rows) and all(row["verified"] for row in verified_rows),
        "file_count": len(rows),
        "files": verified_rows,
    }
    if not result["verified"]:
        raise RuntimeError("C3I package integrity verification failed")
    return result


def verify_c3h_evidence(root: Path) -> tuple[Path, dict[str, Any]]:
    folder = root / "FOXAI_USBC3H_CONTROLLED_FIRST_START" / "START_OUTPUT" / C3H_RUN
    if not folder.is_dir():
        raise RuntimeError(f"Exact accepted C3H output is missing: {folder}")
    integrity_path = folder / "evidence_integrity.json"
    if sha256_file(integrity_path) != C3H_INTEGRITY_SHA256:
        raise RuntimeError("C3H evidence-integrity manifest hash changed")
    manifest = read_json(integrity_path)
    rows = []
    for item in manifest.get("files") or []:
        path = folder / str(item["file"])
        exists = path.is_file()
        size = path.stat().st_size if exists else None
        digest = sha256_file(path) if exists else None
        ok = exists and size == int(item["size_bytes"]) and digest == item["sha256"]
        rows.append({
            "file": item["file"],
            "size_bytes": size,
            "sha256": digest,
            "verified": ok,
        })
    classification = read_json(folder / "classification.json")
    receipt = read_json(folder / "receipt.json")
    health = read_json(folder / "health_verification.json")
    network = read_json(folder / "network_observation.json")
    stop = read_json(folder / "stop_receipt.json")
    source = read_json(folder / "source_boundary_comparison.json")
    target = read_json(folder / "isolated_target_after.json")
    result = {
        "verified": (
            manifest.get("verified") is True
            and int(manifest.get("file_count", 0)) == 21
            and len(rows) == 21
            and all(row["verified"] for row in rows)
            and classification.get("verified") is True
            and classification.get("mode") == C3H_CLASSIFICATION
            and receipt.get("verified") is True
            and receipt.get("health_verified") is True
            and receipt.get("left_running") is False
            and health.get("verified") is True
            and not network.get("violations")
            and stop.get("graceful") is True
            and source.get("verified") is True
            and target.get("verified") is True
        ),
        "folder": str(folder),
        "evidence_file_count": len(rows),
        "evidence_files": rows,
        "classification": classification.get("mode"),
        "health_success_count": health.get("success_count"),
        "health_stability_seconds": health.get("stability_seconds"),
        "listen": classification.get("listen"),
        "custom_nodes_disabled": classification.get("custom_nodes_disabled"),
        "external_network_observed": classification.get("external_network_observed"),
        "stopped": classification.get("comfyui_stopped"),
    }
    if not result["verified"]:
        raise RuntimeError("Exact C3H accepted evidence did not reverify")
    return folder, result


def load_c3e_inventory(root: Path) -> tuple[Path, dict[str, Any]]:
    path = (
        root
        / "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL"
        / "INSTALL_OUTPUT"
        / C3E_RUN
        / "installed_file_inventory_final.json"
    )
    if not path.is_file():
        raise RuntimeError(f"Exact accepted C3E installed inventory is missing: {path}")
    if sha256_file(path) != C3E_INVENTORY_SHA256:
        raise RuntimeError("C3E installed inventory hash changed")
    inventory = read_json(path)
    if (
        inventory.get("verified") is not True
        or int(inventory.get("file_count", 0)) != EXPECTED_TARGET_COUNT
        or int(inventory.get("total_bytes", 0)) != EXPECTED_TARGET_BYTES
        or inventory.get("tree_sha256") != EXPECTED_TARGET_TREE
        or len(inventory.get("files") or []) != EXPECTED_TARGET_COUNT
    ):
        raise RuntimeError("C3E installed inventory metadata changed")
    return path, inventory


def verify_target(root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    target = root / TARGET_REL
    if not target.is_dir():
        raise RuntimeError(f"Committed isolated target is missing: {target}")
    expected_rows = inventory.get("files") or []
    expected = {str(item["path"]).casefold(): item for item in expected_rows}
    if len(expected) != len(expected_rows):
        raise RuntimeError("C3E inventory contains duplicate case-insensitive paths")

    actual: dict[str, Path] = {}
    symlinks: list[str] = []
    for path in sorted(target.rglob("*"), key=lambda p: str(p).casefold()):
        if path.is_symlink():
            symlinks.append(path.relative_to(target).as_posix())
        elif path.is_file():
            relative = path.relative_to(target).as_posix()
            key = relative.casefold()
            if key in actual:
                raise RuntimeError(f"Duplicate case-insensitive live path: {relative}")
            actual[key] = path

    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatches = []
    aggregate = hashlib.sha256()
    total_bytes = 0
    verified_count = 0
    for item in expected_rows:
        relative = str(item["path"])
        path = actual.get(relative.casefold())
        if path is None:
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == int(item["size_bytes"]) and digest == str(item["sha256"])
        if not ok and len(mismatches) < 100:
            mismatches.append({
                "path": relative,
                "expected_size": item["size_bytes"],
                "actual_size": size,
                "expected_sha256": item["sha256"],
                "actual_sha256": digest,
            })
        verified_count += int(ok)
        total_bytes += size
        aggregate.update(relative.casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")

    result = {
        "verified": (
            not symlinks
            and not missing
            and not unexpected
            and not mismatches
            and len(actual) == EXPECTED_TARGET_COUNT
            and verified_count == EXPECTED_TARGET_COUNT
            and total_bytes == EXPECTED_TARGET_BYTES
            and aggregate.hexdigest() == EXPECTED_TARGET_TREE
        ),
        "target": str(target),
        "expected_file_count": EXPECTED_TARGET_COUNT,
        "actual_file_count": len(actual),
        "verified_file_count": verified_count,
        "expected_bytes": EXPECTED_TARGET_BYTES,
        "actual_bytes": total_bytes,
        "expected_tree_sha256": EXPECTED_TARGET_TREE,
        "actual_tree_sha256": aggregate.hexdigest(),
        "missing": missing[:100],
        "unexpected": unexpected[:100],
        "mismatches": mismatches,
        "symlinks": symlinks[:100],
    }
    if not result["verified"]:
        raise RuntimeError("Committed isolated target no longer matches accepted C3E inventory")
    return result


def verify_live_surfaces(c3h_folder: Path) -> dict[str, Any]:
    source = read_json(c3h_folder / "live_and_protected_after.json")
    rows = []
    for item in source.get("files") or []:
        path = Path(str(item["path"]))
        exists = path.is_file()
        size = path.stat().st_size if exists else None
        digest = sha256_file(path) if exists else None
        ok = exists and size == int(item["size_bytes"]) and digest == item["sha256"]
        rows.append({
            "path": str(path),
            "size_bytes": size,
            "sha256": digest,
            "verified": ok,
        })
    result = {
        "verified": source.get("verified") is True and len(rows) == 10 and all(row["verified"] for row in rows),
        "file_count": len(rows),
        "files": rows,
    }
    if not result["verified"]:
        raise RuntimeError("C3G-integrated live surfaces changed after accepted C3H")
    return result


def text_markers(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.casefold()
    markers = {
        "uses_isolated_activator": "launch_comfyui_isolated.py" in lower,
        "cpu_flag": "--cpu" in lower,
        "disable_custom_nodes_flag": "--disable-all-custom-nodes" in lower,
        "loopback_flag": "127.0.0.1" in lower,
        "port_8188": "8188" in lower,
        "health_check": "system_stats" in lower or "invoke-webrequest" in lower or "check('http://127.0.0.1:8188')" in lower,
        "browser_open": "start http://127.0.0.1:8188" in lower or "webbrowser" in lower or "openurl('http://127.0.0.1:8188')" in lower,
        "explicit_stop_control": "stop_comfyui" in lower or "/api/stop/comfy" in lower or "ctrl_break" in lower,
        "legacy_pip_disabled": "legacy pip installer is intentionally disabled" in lower,
        "keeps_console_open": "cmd /k" in lower or "pause" in lower,
    }
    excerpts = []
    for number, line in enumerate(text.splitlines(), 1):
        line_lower = line.casefold()
        if any(token in line_lower for token in (
            "launch_comfyui_isolated.py", "--cpu", "--disable-all-custom-nodes",
            "127.0.0.1", "8188", "launch/comfy", "open-url/comfy",
            "invoke-webrequest", "legacy pip installer", "cmd /k",
        )):
            excerpts.append({"line": number, "text": line[:500]})
            if len(excerpts) >= 80:
                break
    return {"markers": markers, "excerpts": excerpts}


def review_launch_surfaces(root: Path) -> dict[str, Any]:
    relative_files = [
        "START_COMFYUI_ISOLATED.bat",
        "Start ComfyUI CPU.bat",
        "Launch FOXAI Workshop.bat",
        "START_FOXAI_CLEAN.bat",
        "START_FOXAI_WORKSHOP_PORTABLE.bat",
        "Install ComfyUI Requirements.bat",
        "core/foxai_web.py",
        "System/PortableRuntime/launch_comfyui_isolated.py",
    ]
    rows = []
    for relative in relative_files:
        path = root / Path(relative)
        if not path.is_file():
            raise RuntimeError(f"Required integrated launch surface is missing: {relative}")
        markers = text_markers(path)
        rows.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            **markers,
        })

    direct = [row for row in rows if row["path"].casefold() in {
        "start_comfyui_isolated.bat", "start comfyui cpu.bat",
        "launch foxai workshop.bat", "start_foxai_clean.bat",
        "start_foxai_workshop_portable.bat", "core/foxai_web.py",
    }]
    findings = {
        "direct_surface_count": len(direct),
        "all_use_isolated_activator": all(row["markers"]["uses_isolated_activator"] for row in direct),
        "all_request_cpu": all(row["markers"]["cpu_flag"] for row in direct),
        "all_disable_custom_nodes": all(row["markers"]["disable_custom_nodes_flag"] for row in direct),
        "all_explicit_loopback": all(row["markers"]["loopback_flag"] for row in direct),
        "all_explicit_port": all(row["markers"]["port_8188"] for row in direct),
        "all_have_health_wait": all(row["markers"]["health_check"] for row in direct),
        "any_explicit_stop_control": any(row["markers"]["explicit_stop_control"] for row in direct),
        "legacy_pip_disabled": next(row for row in rows if row["path"] == "Install ComfyUI Requirements.bat")["markers"]["legacy_pip_disabled"],
    }
    return {"verified": True, "surfaces": rows, "summary": findings}


def directory_summary(path: Path, suffixes: set[str] | None = None) -> dict[str, Any]:
    files = 0
    bytes_total = 0
    oldest = None
    newest = None
    symlinks = []
    examples = []
    if not path.exists():
        return {"path": str(path), "exists": False, "file_count": 0, "bytes": 0, "symlinks": []}
    for current_root, dirs, names in os.walk(path, followlinks=False):
        base = Path(current_root)
        dirs[:] = [name for name in dirs if not (base / name).is_symlink()]
        for name in names:
            file_path = base / name
            if file_path.is_symlink():
                symlinks.append(str(file_path))
                continue
            if suffixes and file_path.suffix.casefold() not in suffixes:
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue
            files += 1
            bytes_total += stat.st_size
            oldest = stat.st_mtime if oldest is None else min(oldest, stat.st_mtime)
            newest = stat.st_mtime if newest is None else max(newest, stat.st_mtime)
            if len(examples) < 25:
                examples.append(str(file_path.relative_to(path)))
    def iso(value: float | None) -> str | None:
        if value is None:
            return None
        return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()
    return {
        "path": str(path),
        "exists": True,
        "file_count": files,
        "bytes": bytes_total,
        "oldest_utc": iso(oldest),
        "newest_utc": iso(newest),
        "symlinks": symlinks[:100],
        "examples": examples,
    }


def inventory_logs(root: Path) -> dict[str, Any]:
    candidates = [
        root / "Logs",
        root / "Runtime/ComfyUI/Logs",
        root / "Runtime/ComfyUI/logs",
        root / "ComfyUI/user",
    ]
    rows = []
    for path in candidates:
        suffixes = {".log", ".txt", ".json", ".jsonl"} if path.name.casefold() == "user" else None
        rows.append(directory_summary(path, suffixes=suffixes))
    return {
        "verified": True,
        "directories": rows,
        "total_files": sum(int(row["file_count"]) for row in rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "automatic_deletion_performed": False,
    }


def inventory_custom_nodes(root: Path) -> dict[str, Any]:
    folder = root / "ComfyUI/custom_nodes"
    entries = []
    recursive_files = 0
    recursive_bytes = 0
    symlinks = []
    if folder.is_dir():
        for child in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
            entries.append({
                "name": child.name,
                "type": "symlink" if child.is_symlink() else "directory" if child.is_dir() else "file",
            })
        for current_root, dirs, names in os.walk(folder, followlinks=False):
            base = Path(current_root)
            keep_dirs = []
            for name in dirs:
                candidate = base / name
                if candidate.is_symlink():
                    symlinks.append(str(candidate.relative_to(folder)))
                else:
                    keep_dirs.append(name)
            dirs[:] = keep_dirs
            for name in names:
                candidate = base / name
                if candidate.is_symlink():
                    symlinks.append(str(candidate.relative_to(folder)))
                    continue
                try:
                    recursive_files += 1
                    recursive_bytes += candidate.stat().st_size
                except OSError:
                    pass
    return {
        "verified": True,
        "path": str(folder),
        "exists": folder.is_dir(),
        "top_level_entry_count": len(entries),
        "top_level_entries": entries,
        "recursive_file_count": recursive_files,
        "recursive_bytes": recursive_bytes,
        "symlinks": symlinks[:100],
        "executed_or_imported": False,
        "c3h_tested_with_custom_nodes": False,
    }


def recommended_policy() -> dict[str, Any]:
    return {
        "policy_id": "FOXAI_COMFYUI_SAFE_NORMAL_CPU_V1",
        "status": "recommended_for_C3J_operator_approval",
        "default_profile": "Safe Normal CPU",
        "runtime": {
            "python": "Runtime/Desktop/python/python.exe",
            "activator": "System/PortableRuntime/launch_comfyui_isolated.py",
            "site_packages": "Runtime/ComfyUI/site-packages",
            "arguments": [
                "--cpu", "--disable-all-custom-nodes", "--listen", "127.0.0.1", "--port", "8188"
            ],
            "bind": "127.0.0.1",
            "port": 8188,
            "external_bind_allowed": False,
            "telemetry_environment_disabled": True,
        },
        "lifecycle": {
            "stay_running_after_verified_start": True,
            "startup_timeout_seconds": 300,
            "required_consecutive_health_checks": 3,
            "health_interval_seconds": 1,
            "health_endpoints": ["/", "/system_stats"],
            "duplicate_start": "Return already-running only when state, PID identity, command fingerprint, and localhost health all agree.",
            "unknown_port_owner": "Refuse to start or stop and show a clear conflict report.",
            "stale_state": "Preserve the stale state and logs, mark them stale, and require exact PID/creation-time validation before replacement.",
        },
        "browser": {
            "direct_user_start_default": "Open the default browser only after verified health.",
            "webui_start_default": "Do not auto-open; keep the existing separate Open action.",
            "url": "http://127.0.0.1:8188",
            "no_browser_option": True,
        },
        "custom_nodes": {
            "default": "disabled",
            "reason": "C3H verified only the no-custom-node path.",
            "enablement": "Requires a separate read-only inventory, compatibility audit, and operator-approved allowlist gate.",
            "automatic_enablement": False,
        },
        "stop_control": {
            "normal": "A controller-owned supervisor requests graceful child shutdown and waits up to 15 seconds.",
            "identity_requirements": [
                "recorded PID", "process creation time", "portable python executable path",
                "root path", "command fingerprint", "localhost port ownership"
            ],
            "force_kill_default": False,
            "force_kill_requires_explicit_operator_action": True,
            "unknown_process_never_killed": True,
        },
        "state": {
            "directory": "Runtime/ComfyUI/state",
            "active_state": "Runtime/ComfyUI/state/normal_instance.json",
            "atomic_write": True,
            "preserve_last_failure": True,
        },
        "logs": {
            "directory": "Runtime/ComfyUI/logs/normal/<UTC-run-id>",
            "files": ["stdout.log", "stderr.log", "start_receipt.json", "health_receipt.json", "stop_receipt.json"],
            "initial_retention": "retain_all_no_automatic_deletion",
            "warning_thresholds": {"run_count": 100, "total_bytes": 1073741824},
            "on_threshold": "Warn and prepare a preview-only prune manifest; do not delete automatically.",
            "preserve_failures": True,
            "never_prune": ["C3A-C3I evidence", "user input/output", "models", "workflows", "source", "runtime packages"],
        },
    }


def proposed_c3j_scope(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "USB C3J",
        "mode": "controlled_write_no_launch_fail_closed",
        "fresh_explicit_approval_required": True,
        "goal": "Apply the reviewed normal lifecycle controller and launcher wiring without performing a normal ComfyUI start.",
        "proposed_additions": [
            "System/PortableRuntime/manage_comfyui_normal.py",
            "System/PortableRuntime/COMFYUI_NORMAL_POLICY.json",
            "START_COMFYUI_NORMAL.bat",
            "STOP_COMFYUI_NORMAL.bat",
            "STATUS_COMFYUI_NORMAL.bat",
        ],
        "proposed_replacements": [
            "START_COMFYUI_ISOLATED.bat",
            "Start ComfyUI CPU.bat",
            "Launch FOXAI Workshop.bat",
            "START_FOXAI_CLEAN.bat",
            "START_FOXAI_WORKSHOP_PORTABLE.bat",
            "core/foxai_web.py",
        ],
        "unchanged": [
            "Install ComfyUI Requirements.bat remains disabled",
            "Runtime/ComfyUI/site-packages",
            "Runtime/Desktop/python",
            "ComfyUI source",
            "custom_nodes contents",
            "models, workflows, input, output, and user files",
            "all archived milestone copies",
        ],
        "c3j_apply_must": [
            "verify exact current hashes before writing",
            "make exact backups of replaced live files",
            "stage all candidates beside destinations",
            "compile Python candidates without running them",
            "perform static no-network/no-launch validation",
            "apply atomically with rollback on partial failure",
            "not launch ComfyUI",
            "not create normal state/log directories until the later controlled normal-start gate",
        ],
        "next_live_gate_after_c3j": "C3K controlled normal lifecycle start/status/stop test",
        "policy": policy,
    }


def make_review_zip(output: Path) -> Path:
    zip_path = output / "UPLOAD_THIS_C3I_REVIEW.zip"
    excluded = {zip_path.name}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.rglob("*"), key=lambda p: str(p).casefold()):
            if path.is_file() and path.name not in excluded:
                archive.write(path, path.relative_to(output).as_posix())
    return zip_path


def evidence_manifest(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*"), key=lambda p: str(p).casefold()):
        if path.is_file() and path.name not in {"evidence_integrity.json", "UPLOAD_THIS_C3I_REVIEW.zip"}:
            rows.append({
                "file": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return {"verified": True, "file_count": len(rows), "files": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    args = parser.parse_args()

    package_root = Path(args.package_root).resolve(strict=True)
    root = package_root.parent.resolve(strict=True)
    output = package_root / "REVIEW_OUTPUT" / run_id()
    output.mkdir(parents=True, exist_ok=False)
    started = utc_now()

    try:
        print("[1/8] Verifying C3I package integrity...")
        package_result = verify_package(package_root)
        write_json(output / "package_verification.json", package_result)

        print("[2/8] Re-verifying the exact accepted C3H evidence...")
        c3h_folder, c3h_result = verify_c3h_evidence(root)
        write_json(output / "c3h_input_verification.json", c3h_result)

        print("[3/8] Binding to the accepted C3E installed-file inventory...")
        inventory_path, inventory = load_c3e_inventory(root)
        write_json(output / "c3e_inventory_binding.json", {
            "verified": True,
            "path": str(inventory_path),
            "size_bytes": inventory_path.stat().st_size,
            "sha256": sha256_file(inventory_path),
            "file_count": inventory.get("file_count"),
            "total_bytes": inventory.get("total_bytes"),
            "tree_sha256": inventory.get("tree_sha256"),
        })

        print("[4/8] Re-hashing 39,046 isolated target files. This may take a minute...")
        target_result = verify_target(root, inventory)
        write_json(output / "isolated_target_reverification.json", target_result)

        print("[5/8] Verifying current integrated launch surfaces...")
        live_before = verify_live_surfaces(c3h_folder)
        write_json(output / "live_surface_verification_before.json", live_before)

        print("[6/8] Reviewing normal-start, health, browser, and stop behavior...")
        launch_review = review_launch_surfaces(root)
        write_json(output / "current_launch_surface_review.json", launch_review)

        print("[7/8] Inventorying custom nodes and existing logs without executing or deleting anything...")
        custom_nodes = inventory_custom_nodes(root)
        write_json(output / "custom_node_inventory.json", custom_nodes)

        logs = inventory_logs(root)
        write_json(output / "existing_log_inventory.json", logs)

        print("[8/8] Generating the proposed C3J policy and exact no-launch apply scope...")
        policy = recommended_policy()
        write_json(output / "recommended_normal_policy.json", policy)
        write_json(output / "retention_policy_review.json", {
            "verified": True,
            "current_inventory": logs,
            "recommendation": policy["logs"],
            "deletion_or_pruning_performed": False,
        })

        changeset = output / "PROPOSED_C3J_CHANGESET"
        changeset.mkdir()
        write_json(changeset / "NORMAL_LAUNCH_CONTRACT.json", policy)
        write_json(changeset / "REQUIRED_CHANGES.json", proposed_c3j_scope(policy))
        write_json(changeset / "CUSTOM_NODE_POLICY.json", policy["custom_nodes"])
        write_json(changeset / "RETENTION_POLICY.json", policy["logs"])
        write_json(changeset / "UI_BEHAVIOR.json", {
            "direct_start": policy["browser"]["direct_user_start_default"],
            "webui_start": policy["browser"]["webui_start_default"],
            "status": "Show STARTING, HEALTHY, STOPPING, STOPPED, STALE, or CONFLICT with verified receipts.",
            "stop": "Expose a Stop control only for an exact controller-owned verified instance.",
            "custom_nodes": "Show Safe Mode / Custom Nodes Disabled until a later audited allowlist gate.",
        })
        write_text(changeset / "README.txt", (
            "C3J PROPOSAL ONLY — NOTHING IN THIS FOLDER HAS BEEN APPLIED.\n\n"
            "C3J requires fresh explicit approval. It must remain no-launch and apply only the\n"
            "reviewed lifecycle-controller and launcher-wiring changes. The first normal\n"
            "stay-running lifecycle test occurs later in C3K.\n"
        ))

        live_after = verify_live_surfaces(c3h_folder)
        write_json(output / "live_surface_verification_after.json", live_after)
        live_unchanged = {
            "verified": live_before == live_after,
            "changes": [] if live_before == live_after else ["Live-surface evidence changed during C3I"],
        }
        if not live_unchanged["verified"]:
            raise RuntimeError("Live surfaces changed during C3I review")
        write_json(output / "live_surface_comparison.json", live_unchanged)

        classification = {
            "mode": SUCCESS_CLASSIFICATION,
            "verified": True,
            "blocking_findings": [],
            "launch_performed": False,
            "network_access": False,
            "live_change": False,
            "runtime_change": False,
            "package_change": False,
            "custom_nodes_executed": False,
            "logs_deleted": False,
            "recommended_default": policy["policy_id"],
            "next_gate": "C3J controlled normal-enablement apply requires fresh explicit operator approval and remains no-launch.",
        }
        write_json(output / "classification.json", classification)

        receipt = {
            "action": "foxai_usbc3i_normal_enablement_retention_review",
            "state": "review_complete_ready_for_exact_review",
            "started": started,
            "completed": utc_now(),
            "verified": True,
            "classification": SUCCESS_CLASSIFICATION,
            "root": str(root),
            "output": str(output),
            "isolated_target_verified": True,
            "live_surfaces_verified": True,
            "custom_node_entries_observed": custom_nodes["top_level_entry_count"],
            "existing_log_files_observed": logs["total_files"],
            "existing_log_bytes_observed": logs["total_bytes"],
            "launch_performed": False,
            "network_access": False,
            "source_change": False,
            "runtime_change": False,
            "package_install": False,
            "package_uninstall": False,
            "log_deletion": False,
        }
        write_json(output / "receipt.json", receipt)

        report = (
            "# FOXAI USB C3I — Normal Enablement and Retention Review\n\n"
            f"- Classification: `{SUCCESS_CLASSIFICATION}`\n"
            "- Verified: `True`\n"
            f"- Isolated target files: **{target_result['actual_file_count']}**\n"
            f"- Isolated target bytes: **{target_result['actual_bytes']}**\n"
            f"- Current launch surfaces reviewed: **{len(launch_review['surfaces'])}**\n"
            f"- Custom-node top-level entries observed without execution: **{custom_nodes['top_level_entry_count']}**\n"
            f"- Existing log files observed: **{logs['total_files']}**\n"
            "- Live files changed: **No**\n"
            "- ComfyUI launched: **No**\n"
            "- Network accessed: **No**\n\n"
            "## Recommended default\n\n"
            "Safe Normal CPU: isolated portable Python, CPU mode, custom nodes disabled, "
            "localhost-only port 8188, verified health before browser open, stay running, "
            "exact controller-owned stop, and retain logs without automatic deletion.\n"
        )
        write_text(output / "report.md", report)

        integrity = evidence_manifest(output)
        write_json(output / "evidence_integrity.json", integrity)
        zip_path = make_review_zip(output)
        print(f"[COMPLETE] C3I classification: {SUCCESS_CLASSIFICATION}")
        print(f"Review ZIP: {zip_path}")
        return 0
    except Exception as exc:
        failure = {
            "mode": "C3I_BLOCKED_FAIL_CLOSED",
            "verified": False,
            "blocking_findings": [f"{type(exc).__name__}: {exc}"],
            "launch_performed": False,
            "network_access": False,
            "live_change": False,
            "runtime_change": False,
            "logs_deleted": False,
        }
        write_json(output / "classification.json", failure)
        write_json(output / "receipt.json", {
            "action": "foxai_usbc3i_normal_enablement_retention_review",
            "state": "blocked_fail_closed",
            "started": started,
            "completed": utc_now(),
            "verified": False,
            "classification": "C3I_BLOCKED_FAIL_CLOSED",
            "error": f"{type(exc).__name__}: {exc}",
            "launch_performed": False,
            "network_access": False,
            "live_change": False,
            "runtime_change": False,
            "logs_deleted": False,
        })
        write_text(output / "report.md", (
            "# FOXAI USB C3I — BLOCKED FAIL CLOSED\n\n"
            f"- Error: `{type(exc).__name__}: {exc}`\n"
            "- Nothing was launched or changed.\n"
        ))
        integrity = evidence_manifest(output)
        write_json(output / "evidence_integrity.json", integrity)
        make_review_zip(output)
        print(f"[STOPPED] C3I failed closed: {type(exc).__name__}: {exc}")
        return 19


if __name__ == "__main__":
    raise SystemExit(main())
