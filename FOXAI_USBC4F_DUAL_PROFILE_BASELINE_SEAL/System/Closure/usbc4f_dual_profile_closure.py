from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUCCESS = "C4F_DUAL_PROFILE_KNOWN_GOOD_BASELINE_SEALED_C4_CLOSED"
FAILURE = "C4F_BLOCKED_FAIL_CLOSED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(value: datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8", newline="\n")


def within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def exact_file(path: Path, size: int, digest: str) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_size == size
        and sha256_file(path) == digest
    )


def verify_package(package: Path) -> dict[str, Any]:
    manifest = read_json(package / "PACKAGE_INTEGRITY.json")
    rows = []
    issues = []
    for record in manifest["files"]:
        path = package / Path(record["path"])
        if (
            not path.is_file()
            or path.is_symlink()
            or not within(path, package)
        ):
            issues.append(f"missing or unsafe package file: {record['path']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == record["size_bytes"] and digest == record["sha256"]
        rows.append(
            {
                "path": record["path"],
                "size_bytes": size,
                "sha256": digest,
                "verified": ok,
            }
        )
        if not ok:
            issues.append(f"package file changed: {record['path']}")
    if issues:
        raise RuntimeError(f"C4F package integrity failed: {issues[:10]}")
    return {"verified": True, "file_count": len(rows), "files": rows}


def baseline_tree(path: Path) -> dict[str, Any]:
    rows = []
    issues = []
    if not path.is_dir() or path.is_symlink():
        return {
            "verified": False,
            "file_count": 0,
            "tree_sha256": "",
            "issues": ["baseline missing or unsafe"],
            "files": [],
        }
    for item in sorted(
        path.rglob("*"),
        key=lambda p: p.relative_to(path).as_posix().casefold(),
    ):
        if item.is_symlink():
            issues.append(f"symlink not allowed: {item}")
            continue
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        rows.append(
            {
                "path": rel,
                "size_bytes": item.stat().st_size,
                "sha256": sha256_file(item),
            }
        )
    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(row["path"].casefold().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "verified": not issues,
        "file_count": len(rows),
        "tree_sha256": aggregate.hexdigest(),
        "issues": issues,
        "files": rows,
    }


def verify_rows(
    root: Path,
    rows: list[dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    output = []
    issues = []
    seen = set()
    for row in rows:
        rel = str(row["relative_path"]).replace("\\", "/")
        key = rel.casefold()
        if key in seen:
            issues.append(f"duplicate {label} path: {rel}")
            continue
        seen.add(key)
        path = root / Path(rel)
        if (
            not path.is_file()
            or path.is_symlink()
            or not within(path, root)
        ):
            issues.append(f"missing or unsafe {label} file: {rel}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == row["size_bytes"] and digest == row["sha256"]
        output.append(
            {
                "relative_path": rel,
                "size_bytes": size,
                "sha256": digest,
                "verified": ok,
            }
        )
        if not ok:
            issues.append(f"changed {label} file: {rel}")
    if issues:
        raise RuntimeError(f"{label} verification failed: {issues[:10]}")
    return {"verified": True, "file_count": len(output), "files": output}


def verify_c4e(root: Path, accepted: dict[str, Any]) -> dict[str, Any]:
    base = root / Path(accepted["accepted_output_relative"])
    if not base.is_dir() or base.is_symlink():
        raise RuntimeError(f"Exact accepted C4E output is missing: {base}")
    rows = []
    issues = []
    for record in accepted["evidence_files"]:
        path = base / Path(record["file"])
        if (
            not path.is_file()
            or path.is_symlink()
            or not within(path, base)
        ):
            issues.append(f"missing or unsafe C4E evidence: {record['file']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == record["size_bytes"] and digest == record["sha256"]
        rows.append(
            {
                "file": record["file"],
                "size_bytes": size,
                "sha256": digest,
                "verified": ok,
            }
        )
        if not ok:
            issues.append(f"changed C4E evidence: {record['file']}")
    classification = read_json(base / "classification.json")
    receipt = read_json(base / "receipt.json")
    lifecycle = read_json(base / "lifecycle_summary.json")
    audit = read_json(base / "webui_audit_summary.json")
    final_safety = read_json(base / "final_process_safety.json")
    target = read_json(base / "isolated_target_after.json")
    boundaries = read_json(base / "live_boundaries_after.json")
    node = read_json(base / "approved_node_after.json")
    checks = {
        "evidence_count": len(rows) == accepted["evidence_file_count"],
        "classification": (
            classification.get("mode") == accepted["classification"]
            and classification.get("verified") is True
        ),
        "receipt_verified": receipt.get("verified") is True,
        "receipt_exit_zero": receipt.get("exit_code") == 0,
        "safe_profile": (
            receipt.get("safe_default_profile") == "safe-normal-cpu"
        ),
        "approved_profile": (
            receipt.get("approved_profile") == "approved-custom-nodes-cpu"
        ),
        "node_hash": (
            receipt.get("approved_node_sha256")
            == accepted["approved_node"]["sha256"]
        ),
        "sequence": lifecycle.get("sequence") == accepted["lifecycle_sequence"],
        "safe_default_verified": lifecycle.get("safe_default_preserved") is True,
        "profile_switch_refused": lifecycle.get("profile_switch_refused") is True,
        "no_browser": receipt.get("browser_open") is False,
        "no_external_network": receipt.get("external_network_access") is False,
        "not_left_running": (
            receipt.get("webui_left_running") is False
            and receipt.get("comfyui_left_running") is False
        ),
        "audit_verified": audit.get("verified") is True,
        "audit_pairing": audit.get("manager_event_pairing_verified") is True,
        "audit_no_denials": not audit.get("denied_events"),
        "final_process_safety": (
            final_safety.get("verified") is True
            and not final_safety.get("matching_processes")
            and not final_safety.get("listeners", {}).get("webui")
            and not final_safety.get("listeners", {}).get("comfyui")
        ),
        "target_exact": (
            target.get("verified") is True
            and target.get("file_count")
            == accepted["isolated_target"]["file_count"]
            and target.get("total_bytes")
            == accepted["isolated_target"]["total_bytes"]
            and target.get("tree_sha256")
            == accepted["isolated_target"]["tree_sha256"]
        ),
        "boundaries_verified": boundaries.get("verified") is True,
        "node_exact": (
            node.get("verified") is True
            and node.get("sha256") == accepted["approved_node"]["sha256"]
        ),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if issues or failed:
        raise RuntimeError(
            f"Accepted C4E binding failed: issues={issues[:10]} failed={failed}"
        )
    return {
        "verified": True,
        "base": str(base),
        "file_count": len(rows),
        "files": rows,
        "checks": checks,
    }


def verify_historical_c3(
    root: Path,
    state: dict[str, Any],
    require_pointer: bool,
) -> dict[str, Any]:
    baseline = root / Path(state["baseline_relative_path"])
    tree = baseline_tree(baseline)
    issues = []
    if not (
        tree["verified"]
        and tree["file_count"] == state["baseline_file_count"]
        and tree["tree_sha256"] == state["baseline_tree_sha256"]
    ):
        issues.append("historical C3 baseline tree mismatch")
    expected_files = {
        row["path"].casefold(): row for row in state["baseline_files"]
    }
    actual_files = {
        row["path"].casefold(): row for row in tree["files"]
    }
    if set(expected_files) != set(actual_files):
        issues.append("historical C3 baseline file set mismatch")
    else:
        for key, expected in expected_files.items():
            actual = actual_files[key]
            if (
                actual["size_bytes"] != expected["size_bytes"]
                or actual["sha256"] != expected["sha256"]
            ):
                issues.append(f"historical C3 file changed: {expected['path']}")
    pointer_result = None
    if require_pointer:
        row = state["pointer"]
        path = root / Path(row["relative_path"])
        pointer_result = {
            "relative_path": row["relative_path"],
            "verified": exact_file(path, row["size_bytes"], row["sha256"]),
        }
        if not pointer_result["verified"]:
            issues.append("current pointer no longer matches accepted C3 pointer")
    if issues:
        raise RuntimeError(f"Historical C3 verification failed: {issues[:10]}")
    return {
        "verified": True,
        "baseline": str(baseline),
        "tree": {k: v for k, v in tree.items() if k != "files"},
        "pointer": pointer_result,
    }


def inventory_target(
    root: Path,
    accepted: dict[str, Any],
    historical_baseline: Path,
    phase: str,
) -> dict[str, Any]:
    manifest = read_json(historical_baseline / "ISOLATED_TARGET_MANIFEST.json")
    expected = accepted["isolated_target"]
    if not (
        manifest.get("relative_path") == expected["relative_path"]
        and manifest.get("file_count") == expected["file_count"]
        and manifest.get("total_bytes") == expected["total_bytes"]
        and manifest.get("tree_sha256") == expected["tree_sha256"]
    ):
        raise RuntimeError("Historical runtime manifest differs from C4E target")
    rows = manifest["files"]
    target = root / Path(expected["relative_path"])
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError(f"Isolated target missing or unsafe: {target}")
    actual_rows = []
    total = 0
    seen = set()
    print(f"[{phase}] Hashing the isolated runtime...", flush=True)
    for index, row in enumerate(rows, 1):
        rel = str(row["path"]).replace("\\", "/")
        key = rel.casefold()
        if key in seen:
            raise RuntimeError(f"duplicate runtime manifest path: {rel}")
        seen.add(key)
        path = target / Path(rel)
        if not path.is_file() or path.is_symlink() or not within(path, target):
            raise RuntimeError(f"missing or unsafe runtime file: {rel}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != row["size_bytes"] or digest != row["sha256"]:
            raise RuntimeError(f"runtime file mismatch: {rel}")
        actual_rows.append({"path": rel, "size_bytes": size, "sha256": digest})
        total += size
        if index % 1000 == 0:
            print(f"  {phase}: {index:,}/{len(rows):,} files", flush=True)
    actual_set = {
        p.relative_to(target).as_posix().casefold()
        for p in target.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    if actual_set != seen:
        missing = sorted(seen - actual_set)
        unexpected = sorted(actual_set - seen)
        raise RuntimeError(
            f"runtime file set mismatch: missing={missing[:5]} "
            f"unexpected={unexpected[:5]}"
        )
    aggregate = hashlib.sha256()
    for row in actual_rows:
        aggregate.update(row["path"].casefold().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    result = {
        "verified": True,
        "phase": phase,
        "relative_path": expected["relative_path"],
        "file_count": len(actual_rows),
        "total_bytes": total,
        "tree_sha256": aggregate.hexdigest(),
        "files": actual_rows,
    }
    if not (
        result["file_count"] == expected["file_count"]
        and result["total_bytes"] == expected["total_bytes"]
        and result["tree_sha256"] == expected["tree_sha256"]
    ):
        raise RuntimeError("isolated runtime aggregate mismatch")
    return result


def port_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def verify_stopped(root: Path) -> dict[str, Any]:
    state_path = root / "Runtime/ComfyUI/state/normal_instance.json"
    if not state_path.is_file() or state_path.is_symlink():
        raise RuntimeError(f"normal controller state missing or unsafe: {state_path}")
    state = read_json(state_path)
    if state.get("status") != "STOPPED":
        raise RuntimeError(f"normal controller state is not STOPPED: {state.get('status')}")
    checks = {
        "comfyui_state_stopped": True,
        "port_8188_free": port_free(8188),
        "port_8765_free": port_free(8765),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError(f"application ports are not stopped: {failed}")
    return {
        "verified": True,
        "state_path": str(state_path),
        "state_status": state.get("status"),
        **checks,
    }


def snapshot_operational(root: Path) -> dict[str, Any]:
    roots = [
        root / "Runtime/ComfyUI/state",
        root / "Runtime/ComfyUI/logs",
        root / "Logs/web_gui.log",
    ]
    rows = []
    for item in roots:
        candidates = [item] if item.is_file() else (
            sorted(item.rglob("*"), key=lambda p: str(p).casefold())
            if item.is_dir()
            else []
        )
        for path in candidates:
            if path.is_symlink():
                raise RuntimeError(f"operational symlink not allowed: {path}")
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            rows.append(
                {
                    "path": rel,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {"verified": True, "file_count": len(rows), "files": rows}


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = {row["path"].casefold(): row for row in before["files"]}
    right = {row["path"].casefold(): row for row in after["files"]}
    added = [right[key] for key in sorted(set(right) - set(left))]
    removed = [left[key] for key in sorted(set(left) - set(right))]
    changed = []
    for key in sorted(set(left) & set(right)):
        if (
            left[key]["size_bytes"] != right[key]["size_bytes"]
            or left[key]["sha256"] != right[key]["sha256"]
        ):
            changed.append({"before": left[key], "after": right[key]})
    return {
        "verified": not added and not removed and not changed,
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def build_baseline(
    staging: Path,
    accepted: dict[str, Any],
    historical: dict[str, Any],
    historical_baseline: Path,
    c4e_verification: dict[str, Any],
) -> dict[str, Any]:
    staging.mkdir(parents=True, exist_ok=False)
    old_manifest = read_json(historical_baseline / "ISOLATED_TARGET_MANIFEST.json")
    runtime_manifest = {
        "schema": 2,
        "relative_path": accepted["isolated_target"]["relative_path"],
        "file_count": accepted["isolated_target"]["file_count"],
        "total_bytes": accepted["isolated_target"]["total_bytes"],
        "tree_sha256": accepted["isolated_target"]["tree_sha256"],
        "inherited_from_baseline_id": historical["baseline_id"],
        "files": old_manifest["files"],
    }
    write_json(staging / "ISOLATED_TARGET_MANIFEST.json", runtime_manifest)
    write_json(
        staging / "INTEGRATED_FILES_MANIFEST.json",
        {"schema": 1, "files": accepted["integrated_files"]},
    )
    write_json(
        staging / "PROTECTED_FILES_MANIFEST.json",
        {"schema": 1, "files": accepted["protected_files"]},
    )
    write_json(
        staging / "DUAL_PROFILE_POLICY.json",
        {
            "schema": 1,
            "contract_id": "FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1",
            "default_profile_id": "safe-normal-cpu",
            "default_profile_name": "Safe Normal CPU",
            "default_profile": {
                "cpu": True,
                "custom_nodes": "disabled",
                "listen": "127.0.0.1:8188",
                "explicit_selection_required": False,
            },
            "approved_profile_id": "approved-custom-nodes-cpu",
            "approved_profile_name": "Approved Custom Nodes CPU",
            "approved_profile": {
                "cpu": True,
                "custom_nodes": "disabled except exact allowlist",
                "whitelist": ["websocket_image_save.py"],
                "listen": "127.0.0.1:8188",
                "explicit_selection_required": True,
                "remember_selection": False,
            },
            "approved_node": accepted["approved_node"],
            "profile_switch_while_healthy": "refuse with PROFILE_CONFLICT",
            "browser_open": "separate explicit action after health",
        },
    )
    write_json(
        staging / "WEBUI_LIFECYCLE_PROOF.json",
        {
            "schema": 1,
            "verified": True,
            "accepted_c4e_run_id": accepted["accepted_run_id"],
            "sequence": accepted["lifecycle_sequence"],
            "safe_default_verified": True,
            "approved_profile_verified": True,
            "approved_node_registration_verified": True,
            "profile_switch_refusal_verified": True,
            "webui_listen": "127.0.0.1:8765",
            "comfyui_listen": "127.0.0.1:8188",
            "browser_open": False,
            "external_network_access": False,
            "left_running": False,
            "audit": accepted["audit"],
        },
    )
    write_json(
        staging / "HISTORICAL_BASELINE_CHAIN.json",
        {
            "schema": 1,
            "current_baseline_id": accepted["baseline_id"],
            "historical_baselines": [
                {
                    "baseline_id": historical["baseline_id"],
                    "baseline_relative_path": historical["baseline_relative_path"],
                    "baseline_file_count": historical["baseline_file_count"],
                    "baseline_tree_sha256": historical["baseline_tree_sha256"],
                    "classification": historical["classification"],
                    "preserved_unchanged": True,
                }
            ],
            "rule": (
                "Never edit a sealed baseline. Future approved changes create "
                "a new content-addressed baseline and preserve this chain."
            ),
        },
    )
    evidence_chain = {
        "schema": 1,
        "baseline_id": accepted["baseline_id"],
        "accepted_chain": [
            {"phase": "C3L", "result": "portable CPU baseline sealed", "baseline_id": historical["baseline_id"]},
            {"phase": "C4A", "result": "custom-node static Airlock accepted", "output": "FOXAI_USBC4A_CUSTOM_NODE_AIRLOCK_PREFLIGHT/PREFLIGHT_OUTPUT/20260718T054520Z"},
            {"phase": "C4B-R1", "result": "exact allowlisted node lifecycle accepted", "output": "FOXAI_USBC4B_ALLOWLISTED_NODE_LIFECYCLE_TEST/TEST_OUTPUT/20260718T062450Z"},
            {"phase": "C4C", "result": "dual-profile WebUI design accepted", "output": "FOXAI_USBC4C_WEBUI_APPROVED_NODE_PROFILE_REVIEW/REVIEW_OUTPUT/20260718T063916Z"},
            {"phase": "C4D", "result": "four-file WebUI profile integration accepted", "output": "FOXAI_USBC4D_WEBUI_APPROVED_NODE_PROFILE_APPLY/APPLY_OUTPUT/20260718T065850Z"},
            {"phase": "C4E-R4", "result": "two-profile WebUI lifecycle accepted", "output": accepted["accepted_output_relative"]},
        ],
        "exact_c4e_evidence": c4e_verification,
    }
    write_json(staging / "EVIDENCE_CHAIN.json", evidence_chain)
    write_json(
        staging / "PORTABILITY_CLOSURE.json",
        {
            "schema": 2,
            "baseline_id": accepted["baseline_id"],
            "portability_mode": "PORTABLE_READY",
            "creative_studio_mode": "USB_OWNED_ISOLATED_CPU_READY",
            "webui_mode": "DUAL_PROFILE_WEBUI_READY",
            "approved_custom_node_mode": "HASH_LOCKED_ALLOWLIST_READY",
            "routine_use_ready": True,
            "safe_default_profile": "safe-normal-cpu",
            "approved_profile": "approved-custom-nodes-cpu",
            "network_binding": "127.0.0.1 only",
            "isolated_target": accepted["isolated_target"],
            "evidence_chain_complete_through": "C4E",
            "c4_closed": True,
        },
    )
    routine = f"""FOXAI COMFYUI — C4 DUAL-PROFILE ROUTINE USE\n\nKnown-good baseline: {accepted['baseline_id']}\n\nWEBUI\n  Start FOXAI with START_FOXAI_WEB_PORTABLE.bat.\n  Safe Normal CPU is selected by default whenever the page loads.\n  Approved Custom Nodes CPU must be selected explicitly and is not remembered.\n\nSAFE DIRECT START\n  START_COMFYUI_NORMAL.bat\n\nAPPROVED-NODE DIRECT START\n  START_COMFYUI_APPROVED_NODES.bat\n\nSTATUS / STOP\n  STATUS_COMFYUI_NORMAL.bat\n  STOP_COMFYUI_NORMAL.bat\n\nVERIFY\n  VERIFY_COMFYUI_KNOWN_GOOD.bat\n  This performs a complete offline 39,046-file verification.\n\nAPPROVED NODE\n  ComfyUI\\custom_nodes\\websocket_image_save.py\n  SHA-256: {accepted['approved_node']['sha256']}\n\nSAFETY\n  CPU only; localhost only; no automatic force-kill; no automatic log deletion.\n  A changed approved-node hash fails closed and requires a new Airlock review.\n"""
    (staging / "ROUTINE_USE_GUIDE.txt").write_text(
        routine, encoding="utf-8", newline="\r\n"
    )
    recovery = f"""FOXAI COMFYUI — C4 RECOVERY AND ROLLBACK REFERENCE\n\nCurrent baseline: {accepted['baseline_id']}\nHistorical C3 baseline: {historical['baseline_id']}\n\nNever edit either sealed baseline directory.\n\nIF VERIFICATION FAILS\n  1. Stop with STOP_COMFYUI_NORMAL.bat.\n  2. Preserve Runtime\\ComfyUI\\state and Runtime\\ComfyUI\\logs.\n  3. Do not run pip install/uninstall against Desktop, host Python, or the target.\n  4. Do not overwrite the approved node. A changed hash requires re-audit.\n  5. Repair only through a new reviewed staging transaction.\n\nC4D BACKUPS\n  FOXAI_USBC4D_WEBUI_APPROVED_NODE_PROFILE_APPLY\\APPLY_OUTPUT\\20260718T065850Z\\BACKUP\n\nEARLIER LAUNCHER BACKUPS\n  C3G: FOXAI_USBC3G_CONTROLLED_INTEGRATION\\APPLY_OUTPUT\\20260718T034126Z\\BACKUP\n  C3J: FOXAI_USBC3J_NORMAL_ENABLEMENT_APPLY\\APPLY_OUTPUT\\20260718T044323Z\\BACKUP\n\nISOLATED TARGET\n  Runtime\\ComfyUI\\site-packages\n  Files: {accepted['isolated_target']['file_count']}\n  Bytes: {accepted['isolated_target']['total_bytes']}\n  Tree SHA-256: {accepted['isolated_target']['tree_sha256']}\n"""
    (staging / "ROLLBACK_AND_RECOVERY_GUIDE.txt").write_text(
        recovery, encoding="utf-8", newline="\r\n"
    )
    content_rows = []
    for path in sorted(
        staging.rglob("*"),
        key=lambda p: p.relative_to(staging).as_posix().casefold(),
    ):
        if not path.is_file():
            continue
        content_rows.append(
            {
                "path": path.relative_to(staging).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    write_json(
        staging / "BASELINE_CONTENT_HASHES.json",
        {"verified": True, "files": content_rows},
    )
    content_hash = sha256_file(staging / "BASELINE_CONTENT_HASHES.json")
    write_json(
        staging / "BASELINE_SEAL.json",
        {
            "schema": 2,
            "baseline_id": accepted["baseline_id"],
            "classification": SUCCESS,
            "sealed_utc": utc_now().isoformat(),
            "operator_approval": (
                "Proceed to USB C4F dual-profile known-good baseline seal "
                "and C4 closure under the accepted C4E results."
            ),
            "historical_baseline_preserved": historical["baseline_id"],
            "isolated_target": accepted["isolated_target"],
            "integrated_file_count": len(accepted["integrated_files"]),
            "protected_file_count": len(accepted["protected_files"]),
            "approved_node_sha256": accepted["approved_node"]["sha256"],
            "content_hash_manifest_sha256": content_hash,
            "immutable_by_contract": True,
            "c4_closed": True,
            "note": (
                "Do not edit this directory. Create a new reviewed baseline "
                "for future changes."
            ),
        },
    )
    tree = baseline_tree(staging)
    if not tree["verified"]:
        raise RuntimeError(f"new baseline build is unsafe: {tree['issues']}")
    return tree


def make_review_zip(output: Path, baseline: Path) -> Path:
    review_copy = output / "BASELINE_REVIEW_COPY"
    if review_copy.exists():
        shutil.rmtree(review_copy)
    shutil.copytree(baseline, review_copy)
    evidence = []
    for path in sorted(
        output.rglob("*"),
        key=lambda p: p.relative_to(output).as_posix().casefold(),
    ):
        if (
            path.is_file()
            and path.name not in {
                "UPLOAD_THIS_C4F_REVIEW.zip",
                "evidence_integrity.json",
            }
        ):
            evidence.append(
                {
                    "file": path.relative_to(output).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    write_json(
        output / "evidence_integrity.json",
        {"verified": True, "file_count": len(evidence), "files": evidence},
    )
    archive_path = output / "UPLOAD_THIS_C4F_REVIEW.zip"
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(
            output.rglob("*"),
            key=lambda p: p.relative_to(output).as_posix().casefold(),
        ):
            if path.is_file() and path != archive_path:
                archive.write(path, path.relative_to(output).as_posix())
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seal FOXAI's C4 dual-profile known-good baseline."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    package = args.package.resolve()
    started = utc_now()
    run_id = stamp(started)
    output = package / "SEAL_OUTPUT" / run_id
    output.mkdir(parents=True, exist_ok=False)
    committed_baseline: Path | None = None
    committed_files: list[dict[str, Any]] = []
    created_dirs: list[Path] = []
    try:
        if package.parent.resolve() != root:
            raise RuntimeError("C4F package must be directly under the FOXAI root")
        accepted = read_json(package / "KNOWN_ACCEPTED_C4E_STATE.json")
        historical = read_json(package / "KNOWN_C3_BASELINE_STATE.json")
        package_result = verify_package(package)
        write_json(output / "package_verification.json", package_result)
        c4e_result = verify_c4e(root, accepted)
        write_json(output / "c4e_input_verification.json", c4e_result)
        historical_before = verify_historical_c3(
            root, historical, require_pointer=True
        )
        write_json(output / "historical_c3_baseline_before.json", historical_before)
        # Verify all legacy metadata before replacing it.
        metadata_before = verify_rows(
            root, historical["metadata_files"], "historical metadata"
        )
        write_json(output / "historical_metadata_before.json", metadata_before)
        stopped_before = verify_stopped(root)
        write_json(output / "preseal_stopped_state.json", stopped_before)
        operational_before = snapshot_operational(root)
        write_json(output / "operational_storage_before.json", operational_before)
        historical_baseline = root / Path(historical["baseline_relative_path"])
        pre_inventory = inventory_target(
            root, accepted, historical_baseline, "PRE-SEAL"
        )
        write_json(
            output / "isolated_target_before_summary.json",
            {k: v for k, v in pre_inventory.items() if k != "files"},
        )
        integrated_before = verify_rows(
            root, accepted["integrated_files"], "C4 integrated"
        )
        protected_before = verify_rows(
            root, accepted["protected_files"], "protected"
        )
        node_before = verify_rows(
            root, [accepted["approved_node"]], "approved node"
        )
        write_json(output / "integrated_files_before.json", integrated_before)
        write_json(output / "protected_files_before.json", protected_before)
        write_json(output / "approved_node_before.json", node_before)

        portability = root / "System/Portability"
        baselines_parent = portability / "Baselines"
        for parent in (portability, baselines_parent):
            if not parent.exists():
                parent.mkdir()
                created_dirs.append(parent)
            elif not parent.is_dir() or parent.is_symlink():
                raise RuntimeError(f"unsafe portability directory: {parent}")

        final_baseline = baselines_parent / accepted["baseline_id"]
        if final_baseline.exists():
            raise RuntimeError(f"new baseline already exists: {final_baseline}")
        baseline_build = output / "BASELINE_BUILD"
        build_tree = build_baseline(
            baseline_build,
            accepted,
            historical,
            historical_baseline,
            c4e_result,
        )
        write_json(
            output / "baseline_build_tree.json",
            {k: v for k, v in build_tree.items() if k != "files"},
        )

        pointer = {
            "schema": 2,
            "baseline_id": accepted["baseline_id"],
            "baseline_relative_path": (
                "System/Portability/Baselines/" + accepted["baseline_id"]
            ),
            "baseline_file_count": build_tree["file_count"],
            "baseline_tree_sha256": build_tree["tree_sha256"],
            "classification": SUCCESS,
            "isolated_target": accepted["isolated_target"],
            "profile_contract_id": "FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1",
            "default_profile_id": "safe-normal-cpu",
            "approved_profile_id": "approved-custom-nodes-cpu",
            "approved_node_sha256": accepted["approved_node"]["sha256"],
            "historical_baselines": [
                {
                    "baseline_id": historical["baseline_id"],
                    "baseline_relative_path": historical["baseline_relative_path"],
                    "baseline_file_count": historical["baseline_file_count"],
                    "baseline_tree_sha256": historical["baseline_tree_sha256"],
                    "classification": historical["classification"],
                }
            ],
            "created_by": (
                "USB C4F dual-profile known-good baseline seal and C4 closure"
            ),
        }
        candidates = output / "CANDIDATES"
        pointer_candidate = candidates / "COMFYUI_KNOWN_GOOD_CURRENT.json"
        write_json(pointer_candidate, pointer)
        verifier_candidate = (
            package
            / "Payload/System/Portability/verify_comfyui_known_good.py"
        )
        bat_candidate = package / "Payload/VERIFY_COMFYUI_KNOWN_GOOD.bat"
        # Compile and AST-parse the exact candidate before staging.
        source_text = verifier_candidate.read_text(encoding="utf-8")
        compile(source_text, str(verifier_candidate), "exec")
        ast.parse(source_text)
        ready_candidate = candidates / "COMFYUI_PORTABILITY_READY.txt"
        ready_text = f"""FOXAI COMFYUI PORTABILITY AND C4: READY\n\nCurrent known-good baseline:\n  {accepted['baseline_id']}\n\nStatus:\n  {SUCCESS}\n\nFOXAI WEBUI PROFILES\n  Safe Normal CPU — default on every page load\n  Approved Custom Nodes CPU — explicit selection, not remembered\n\nAPPROVED NODE\n  ComfyUI\\custom_nodes\\websocket_image_save.py\n  SHA-256: {accepted['approved_node']['sha256']}\n\nDIRECT CONTROLS\n  START_COMFYUI_NORMAL.bat\n  START_COMFYUI_APPROVED_NODES.bat\n  STATUS_COMFYUI_NORMAL.bat\n  STOP_COMFYUI_NORMAL.bat\n\nFULL OFFLINE VERIFICATION\n  VERIFY_COMFYUI_KNOWN_GOOD.bat\n\nHistorical C3 baseline preserved unchanged:\n  {historical['baseline_id']}\n\nCPU only; localhost only; no automatic force-kill or log deletion.\n"""
        ready_candidate.parent.mkdir(parents=True, exist_ok=True)
        ready_candidate.write_text(
            ready_text, encoding="utf-8", newline="\r\n"
        )

        pointer_final = portability / "COMFYUI_KNOWN_GOOD_CURRENT.json"
        verifier_final = portability / "verify_comfyui_known_good.py"
        bat_final = root / "VERIFY_COMFYUI_KNOWN_GOOD.bat"
        ready_final = root / "COMFYUI_PORTABILITY_READY.txt"
        replacements = [
            (pointer_candidate, pointer_final),
            (verifier_candidate, verifier_final),
            (bat_candidate, bat_final),
            (ready_candidate, ready_final),
        ]
        backup_root = output / "BACKUP"
        backup_rows = []
        for _, final in replacements:
            if not final.is_file() or final.is_symlink() or not within(final, root):
                raise RuntimeError(f"metadata replacement target missing or unsafe: {final}")
            backup = backup_root / final.relative_to(root)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(final, backup)
            backup_rows.append(
                {
                    "relative_path": final.relative_to(root).as_posix(),
                    "size_bytes": backup.stat().st_size,
                    "sha256": sha256_file(backup),
                }
            )
        write_json(
            output / "backup_manifest.json",
            {"verified": True, "files": backup_rows},
        )

        staged_baseline = baselines_parent / (
            f".{accepted['baseline_id']}.C4F_STAGING_{run_id}"
        )
        shutil.copytree(baseline_build, staged_baseline)
        staged_tree = baseline_tree(staged_baseline)
        if staged_tree["tree_sha256"] != build_tree["tree_sha256"]:
            raise RuntimeError("staged baseline hash mismatch")
        staged_files = []
        for source, final in replacements:
            staged = final.with_name(final.name + f".C4F_STAGED_{run_id}")
            copy_atomic(source, staged)
            if sha256_file(staged) != sha256_file(source):
                raise RuntimeError(f"staged metadata hash mismatch: {final}")
            staged_files.append((source, staged, final))

        os.rename(staged_baseline, final_baseline)
        committed_baseline = final_baseline
        final_tree = baseline_tree(final_baseline)
        if final_tree["tree_sha256"] != build_tree["tree_sha256"]:
            raise RuntimeError("committed C4 baseline tree mismatch")
        for source, staged, final in staged_files:
            candidate_hash = sha256_file(source)
            candidate_size = source.stat().st_size
            os.replace(staged, final)
            committed_files.append(
                {
                    "final": final,
                    "candidate_sha256": candidate_hash,
                    "candidate_size": candidate_size,
                    "backup": backup_root / final.relative_to(root),
                }
            )
            if not exact_file(final, candidate_size, candidate_hash):
                raise RuntimeError(f"committed metadata mismatch: {final}")

        # Run the committed verifier in-process in quick mode. No child process.
        spec = importlib.util.spec_from_file_location(
            "foxai_c4f_verifier", verifier_final
        )
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            raise RuntimeError("unable to load committed verifier")
        spec.loader.exec_module(module)
        quick_result = module.verify_known_good(root, quick=True)
        if not quick_result.get("verified"):
            raise RuntimeError(f"committed verifier failed: {quick_result}")
        write_json(output / "committed_verifier_quick_result.json", quick_result)

        post_inventory = inventory_target(
            root, accepted, historical_baseline, "POST-SEAL"
        )
        if post_inventory["tree_sha256"] != pre_inventory["tree_sha256"]:
            raise RuntimeError("isolated runtime changed during C4 sealing")
        write_json(
            output / "isolated_target_after_summary.json",
            {k: v for k, v in post_inventory.items() if k != "files"},
        )
        integrated_after = verify_rows(
            root, accepted["integrated_files"], "C4 integrated"
        )
        protected_after = verify_rows(
            root, accepted["protected_files"], "protected"
        )
        node_after = verify_rows(
            root, [accepted["approved_node"]], "approved node"
        )
        write_json(output / "integrated_files_after.json", integrated_after)
        write_json(output / "protected_files_after.json", protected_after)
        write_json(output / "approved_node_after.json", node_after)
        historical_after = verify_historical_c3(
            root, historical, require_pointer=False
        )
        write_json(output / "historical_c3_baseline_after.json", historical_after)
        if (
            historical_after["tree"]["tree_sha256"]
            != historical_before["tree"]["tree_sha256"]
        ):
            raise RuntimeError("historical C3 baseline changed during C4F")
        stopped_after = verify_stopped(root)
        write_json(output / "postseal_stopped_state.json", stopped_after)
        operational_after = snapshot_operational(root)
        write_json(output / "operational_storage_after.json", operational_after)
        storage_changes = compare_snapshots(operational_before, operational_after)
        write_json(output / "operational_storage_changes.json", storage_changes)
        if not storage_changes["verified"]:
            raise RuntimeError("operational state or logs changed during C4F")
        current_tree = baseline_tree(final_baseline)
        if current_tree["tree_sha256"] != pointer["baseline_tree_sha256"]:
            raise RuntimeError("current C4 baseline no longer matches pointer")

        completed = utc_now()
        commit_receipt = {
            "committed": True,
            "new_baseline": str(final_baseline),
            "new_baseline_file_count": pointer["baseline_file_count"],
            "new_baseline_tree_sha256": pointer["baseline_tree_sha256"],
            "historical_c3_baseline": historical["baseline_id"],
            "historical_c3_preserved": True,
            "pointer": str(pointer_final),
            "verifier": str(verifier_final),
            "verify_bat": str(bat_final),
            "ready_notice": str(ready_final),
            "runtime_content_modified": False,
            "launcher_modified": False,
            "approved_node_modified": False,
            "state_or_logs_modified": False,
            "network_access": False,
            "child_process_launch": False,
            "foxai_or_comfyui_launch": False,
        }
        write_json(output / "baseline_commit_receipt.json", commit_receipt)
        receipt = {
            "action": "foxai_usbc4f_dual_profile_known_good_seal_and_c4_closure",
            "started": started.isoformat(),
            "completed": completed.isoformat(),
            "elapsed_seconds": round((completed - started).total_seconds(), 3),
            "verified": True,
            "classification": SUCCESS,
            "baseline_id": accepted["baseline_id"],
            "baseline_path": str(final_baseline),
            "historical_baseline_preserved": historical["baseline_id"],
            "isolated_target": accepted["isolated_target"],
            "integrated_file_count": len(accepted["integrated_files"]),
            "protected_file_count": len(accepted["protected_files"]),
            "approved_node_sha256": accepted["approved_node"]["sha256"],
            "safe_default_profile": "safe-normal-cpu",
            "approved_profile": "approved-custom-nodes-cpu",
            "normal_state": "STOPPED",
            "webui_port_free": True,
            "comfyui_port_free": True,
            "routine_use_ready": True,
            "c4_closed": True,
            "network_access": False,
            "launcher_change": False,
            "runtime_content_change": False,
            "package_change": False,
            "approved_node_change": False,
            "state_or_log_change": False,
            "foxai_or_comfyui_launched": False,
            "blocking_findings": [],
        }
        write_json(output / "receipt.json", receipt)
        write_json(
            output / "classification.json",
            {
                "mode": SUCCESS,
                "verified": True,
                "blocking_findings": [],
                "routine_use_ready": True,
                "dual_profile_webui_ready": True,
                "approved_custom_node_ready": True,
                "historical_c3_baseline_preserved": True,
                "c4_closed": True,
                "next_state": (
                    "Routine Creative Studio use through the FOXAI WebUI; "
                    "future changes require a new reviewed baseline."
                ),
            },
        )
        report = f"""# FOXAI USB C4F — Dual-Profile Baseline and C4 Closure\n\n- Classification: `{SUCCESS}`\n- Verified: `True`\n- Current baseline: `{accepted['baseline_id']}`\n- Historical C3 baseline preserved: `{historical['baseline_id']}`\n- Isolated target files: **{accepted['isolated_target']['file_count']}**\n- Isolated target bytes: **{accepted['isolated_target']['total_bytes']}**\n- Runtime tree SHA-256: `{accepted['isolated_target']['tree_sha256']}`\n- Safe Normal CPU default: **True**\n- Approved Custom Nodes CPU ready: **True**\n- C4 closed: **True**\n\nC4F added only compact baseline metadata and updated the current verification pointer. It did not launch FOXAI or ComfyUI, change the runtime, edit launchers, alter the approved node, or access the external network.\n"""
        (output / "report.md").write_text(
            report, encoding="utf-8", newline="\n"
        )
        archive = make_review_zip(output, final_baseline)
        print("[COMPLETE] C4F sealed the dual-profile known-good baseline.", flush=True)
        print(f"Review ZIP: {archive}", flush=True)
        return 0
    except Exception as exc:
        rollback = []
        # Restore exact metadata replacements only when the committed file still
        # matches the C4F candidate. Never overwrite an independently changed file.
        for row in reversed(committed_files):
            final = row["final"]
            backup = row["backup"]
            try:
                if exact_file(
                    final,
                    row["candidate_size"],
                    row["candidate_sha256"],
                ) and backup.is_file():
                    copy_atomic(backup, final)
                    rollback.append({"path": str(final), "restored": True})
                else:
                    rollback.append(
                        {
                            "path": str(final),
                            "restored": False,
                            "reason": "missing or changed after commit",
                        }
                    )
            except Exception as rollback_exc:
                rollback.append(
                    {
                        "path": str(final),
                        "restored": False,
                        "error": (
                            f"{type(rollback_exc).__name__}: {rollback_exc}"
                        ),
                    }
                )
        if committed_baseline is not None:
            try:
                if committed_baseline.is_dir() and not committed_baseline.is_symlink():
                    shutil.rmtree(committed_baseline)
                    rollback.append(
                        {"path": str(committed_baseline), "removed": True}
                    )
            except Exception as rollback_exc:
                rollback.append(
                    {
                        "path": str(committed_baseline),
                        "removed": False,
                        "error": (
                            f"{type(rollback_exc).__name__}: {rollback_exc}"
                        ),
                    }
                )
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        failure = {
            "mode": FAILURE,
            "verified": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "rollback": rollback,
            "historical_c3_baseline_intentionally_untouched": True,
            "runtime_content_change": False,
            "launcher_change": False,
            "approved_node_change": False,
            "network_access": False,
            "foxai_or_comfyui_launched": False,
        }
        write_json(output / "classification.json", failure)
        write_json(output / "receipt.json", failure)
        (output / "report.md").write_text(
            f"# C4F stopped fail-closed\n\n{failure['error']}\n",
            encoding="utf-8",
            newline="\n",
        )
        try:
            evidence = []
            for path in sorted(
                output.rglob("*"),
                key=lambda p: p.relative_to(output).as_posix().casefold(),
            ):
                if (
                    path.is_file()
                    and path.name not in {
                        "UPLOAD_THIS_C4F_REVIEW.zip",
                        "evidence_integrity.json",
                    }
                ):
                    evidence.append(
                        {
                            "file": path.relative_to(output).as_posix(),
                            "size_bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                        }
                    )
            write_json(
                output / "evidence_integrity.json",
                {"verified": True, "file_count": len(evidence), "files": evidence},
            )
            archive = output / "UPLOAD_THIS_C4F_REVIEW.zip"
            with zipfile.ZipFile(
                archive,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as handle:
                for path in sorted(
                    output.rglob("*"),
                    key=lambda p: p.relative_to(output).as_posix().casefold(),
                ):
                    if path.is_file() and path != archive:
                        handle.write(path, path.relative_to(output).as_posix())
        except Exception:
            pass
        print(
            f"[STOPPED] C4F failed closed: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return 19


if __name__ == "__main__":
    raise SystemExit(main())
