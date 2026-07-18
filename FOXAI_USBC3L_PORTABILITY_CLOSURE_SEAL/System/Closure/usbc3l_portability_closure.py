from __future__ import annotations

import argparse
import hashlib
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

SUCCESS = "C3L_PORTABILITY_CLOSED_KNOWN_GOOD_BASELINE_SEALED"
FAILURE = "C3L_BLOCKED_FAIL_CLOSED"


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


def verify_package(package: Path) -> dict[str, Any]:
    manifest_path = package / "PACKAGE_INTEGRITY.json"
    manifest = read_json(manifest_path)
    rows = []
    issues = []
    for record in manifest["files"]:
        path = package / Path(record["path"])
        if not path.is_file() or path.is_symlink() or not within(path, package):
            issues.append(f"missing or unsafe package file: {record['path']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == record["size_bytes"] and digest == record["sha256"]
        rows.append({"path": record["path"], "size_bytes": size, "sha256": digest, "verified": ok})
        if not ok:
            issues.append(f"package file changed: {record['path']}")
    if issues:
        raise RuntimeError(f"C3L package integrity failed: {issues[:10]}")
    return {"verified": True, "file_count": len(rows), "files": rows}


def verify_c3k(root: Path, accepted: dict[str, Any]) -> dict[str, Any]:
    base = root / Path(accepted["accepted_c3k_output_relative"])
    if not base.is_dir() or base.is_symlink():
        raise RuntimeError(f"Exact accepted C3K output is missing or unsafe: {base}")
    rows = []
    issues = []
    for record in accepted["evidence_files"]:
        path = base / Path(record["file"])
        if not path.is_file() or path.is_symlink() or not within(path, base):
            issues.append(f"missing or unsafe C3K evidence: {record['file']}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == record["size_bytes"] and digest == record["sha256"]
        rows.append({"file": record["file"], "size_bytes": size, "sha256": digest, "verified": ok})
        if not ok:
            issues.append(f"changed C3K evidence: {record['file']}")
    classification = read_json(base / "classification.json")
    receipt = read_json(base / "receipt.json")
    final_status = read_json(base / "final_status_result.json")
    source_boundary = read_json(base / "source_boundary_comparison.json")
    checks = {
        "evidence_count": len(rows) == accepted["evidence_file_count"],
        "classification": classification.get("mode") == accepted["classification"] and classification.get("verified") is True,
        "receipt_verified": receipt.get("verified") is True,
        "sequence": receipt.get("sequence") == accepted["lifecycle"]["sequence"],
        "no_browser": receipt.get("browser_opened") is False,
        "custom_nodes_disabled": receipt.get("custom_nodes_disabled") is True,
        "loopback": receipt.get("listen") == "127.0.0.1:8188",
        "no_force_kill": receipt.get("force_kill") is False,
        "no_external_network": receipt.get("network_external") is False,
        "not_left_running": receipt.get("comfyui_left_running") is False,
        "final_stopped": final_status.get("state") == "STOPPED" and final_status.get("ok") is True,
        "source_unchanged": source_boundary.get("verified") is True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if issues or failed:
        raise RuntimeError(f"Accepted C3K binding failed: issues={issues[:10]} failed={failed}")
    return {"verified": True, "base": str(base), "file_count": len(rows), "files": rows, "checks": checks}


def verify_rows(root: Path, rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
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
        if not path.is_file() or path.is_symlink() or not within(path, root):
            issues.append(f"missing or unsafe {label} file: {rel}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == row["size_bytes"] and digest == row["sha256"]
        output.append({"relative_path": rel, "size_bytes": size, "sha256": digest, "verified": ok})
        if not ok:
            issues.append(f"changed {label} file: {rel}")
    if issues:
        raise RuntimeError(f"{label} verification failed: {issues[:10]}")
    return {"verified": True, "file_count": len(output), "files": output}


def inventory_target(root: Path, accepted: dict[str, Any], phase: str) -> dict[str, Any]:
    target = root / Path(accepted["isolated_target"]["relative_path"])
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError(f"Isolated target is missing or unsafe: {target}")
    rows = []
    total = 0
    issues = []
    paths = sorted(target.rglob("*"), key=lambda p: str(p).casefold())
    print(f"[{phase}] Hashing the isolated target...", flush=True)
    for path in paths:
        if path.is_symlink():
            issues.append(f"symlink not allowed: {path}")
            continue
        if not path.is_file():
            continue
        if not within(path, target):
            issues.append(f"file escapes target: {path}")
            continue
        rel = path.relative_to(target).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        rows.append({"path": rel, "size_bytes": size, "sha256": digest})
        total += size
        if len(rows) % 1000 == 0:
            print(f"  {phase}: {len(rows):,}/{accepted['isolated_target']['file_count']:,} files", flush=True)
    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(row["path"].casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    result = {
        "verified": not issues,
        "phase": phase,
        "relative_path": accepted["isolated_target"]["relative_path"],
        "file_count": len(rows),
        "total_bytes": total,
        "tree_sha256": aggregate.hexdigest(),
        "issues": issues,
        "files": rows,
    }
    expected = accepted["isolated_target"]
    exact = (
        result["verified"]
        and result["file_count"] == expected["file_count"]
        and result["total_bytes"] == expected["total_bytes"]
        and result["tree_sha256"] == expected["tree_sha256"]
    )
    result["verified"] = exact
    if not exact:
        raise RuntimeError(
            "Isolated target differs from accepted C3K: "
            f"count={result['file_count']} bytes={result['total_bytes']} tree={result['tree_sha256']}"
        )
    return result


def verify_stopped(root: Path) -> dict[str, Any]:
    state_path = root / "Runtime/ComfyUI/state/normal_instance.json"
    if not state_path.is_file() or state_path.is_symlink():
        raise RuntimeError(f"Normal lifecycle state is missing or unsafe: {state_path}")
    state = read_json(state_path)
    if state.get("status") != "STOPPED":
        raise RuntimeError(f"Normal controller state is not STOPPED: {state.get('status')}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", 8188))
        port_free = True
    except OSError as exc:
        raise RuntimeError(f"Port 8188 is not free: {exc}") from exc
    finally:
        sock.close()
    return {"verified": True, "state_path": str(state_path), "status": state.get("status"), "port_8188_free": port_free}


def baseline_tree(path: Path) -> dict[str, Any]:
    rows = []
    issues = []
    for item in sorted(path.rglob("*"), key=lambda p: p.relative_to(path).as_posix().casefold()):
        if item.is_symlink():
            issues.append(f"symlink not allowed: {item}")
            continue
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        rows.append({"path": rel, "size_bytes": item.stat().st_size, "sha256": sha256_file(item)})
    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(row["path"].casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {"verified": not issues, "file_count": len(rows), "tree_sha256": aggregate.hexdigest(), "issues": issues, "files": rows}


def build_baseline(staging: Path, root: Path, accepted: dict[str, Any], pre_inventory: dict[str, Any], integrated: dict[str, Any], protected: dict[str, Any], c3k: dict[str, Any]) -> dict[str, Any]:
    staging.mkdir(parents=True)
    write_json(staging / "ISOLATED_TARGET_MANIFEST.json", pre_inventory)
    write_json(staging / "INTEGRATED_FILES_MANIFEST.json", integrated)
    write_json(staging / "PROTECTED_FILES_MANIFEST.json", protected)
    evidence_chain = {
        "schema": 1,
        "baseline_id": accepted["baseline_id"],
        "accepted_chain": [
            {"phase": "C3A", "result": "dependency compatibility preflight accepted"},
            {"phase": "C3B", "result": "exact 96-package closure accepted"},
            {"phase": "C3C-R3", "result": "96 wheels cryptographically staged"},
            {"phase": "C3D-R1", "result": "offline install dry run accepted", "output": "FOXAI_USBC3D_EXACT_ISOLATED_INSTALL_PLAN/PLAN_OUTPUT/20260717T202101Z"},
            {"phase": "C3E-R2", "result": "isolated target installed and committed", "output": "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL/INSTALL_OUTPUT/20260718T023211Z"},
            {"phase": "C3F-R2", "result": "no-launch activation preflight accepted", "output": "FOXAI_USBC3F_CONTROLLED_ACTIVATION_PREFLIGHT/PREFLIGHT_OUTPUT/20260718T031624Z"},
            {"phase": "C3G-R1", "result": "isolated launcher integration accepted", "output": "FOXAI_USBC3G_CONTROLLED_INTEGRATION/APPLY_OUTPUT/20260718T034126Z"},
            {"phase": "C3H", "result": "controlled first start verified and stopped", "output": "FOXAI_USBC3H_CONTROLLED_FIRST_START/START_OUTPUT/20260718T040138Z"},
            {"phase": "C3I", "result": "normal enablement policy accepted", "output": "FOXAI_USBC3I_NORMAL_ENABLEMENT_REVIEW/REVIEW_OUTPUT/20260718T041549Z"},
            {"phase": "C3J", "result": "normal lifecycle integration accepted", "output": "FOXAI_USBC3J_NORMAL_ENABLEMENT_APPLY/APPLY_OUTPUT/20260718T044323Z"},
            {"phase": "C3K", "result": "normal STOPPED-HEALTHY-STOPPED lifecycle accepted", "output": accepted["accepted_c3k_output_relative"]},
        ],
        "exact_c3k_evidence": c3k,
    }
    write_json(staging / "EVIDENCE_CHAIN.json", evidence_chain)
    lifecycle = {
        "verified": True,
        "policy_id": "FOXAI_COMFYUI_SAFE_NORMAL_CPU_V1",
        "normal_commands": {
            "start": "START_COMFYUI_NORMAL.bat",
            "status": "STATUS_COMFYUI_NORMAL.bat",
            "stop": "STOP_COMFYUI_NORMAL.bat",
            "verify": "VERIFY_COMFYUI_KNOWN_GOOD.bat",
        },
        "profile": {
            "python": "Runtime/Desktop/python/python.exe",
            "runtime": "Runtime/ComfyUI/site-packages",
            "mode": "CPU",
            "custom_nodes": "disabled by default",
            "listen": "127.0.0.1:8188",
            "direct_start_browser": "open only after verified health",
            "stop": "graceful controller-owned stop; no automatic force-kill",
        },
        "accepted_c3k": accepted["lifecycle"],
    }
    write_json(staging / "LIFECYCLE_PROOF.json", lifecycle)
    routine = f'''FOXAI COMFYUI — ROUTINE USE\n\nKnown-good baseline: {accepted['baseline_id']}\n\nSTART\n  Double-click START_COMFYUI_NORMAL.bat\n  The browser opens only after the local service passes its health check.\n\nSTATUS\n  Double-click STATUS_COMFYUI_NORMAL.bat\n\nSTOP\n  Double-click STOP_COMFYUI_NORMAL.bat\n  It stops only the exact controller-owned ComfyUI process.\n\nVERIFY AFTER MOVING THE USB OR WHEN SOMETHING SEEMS WRONG\n  Double-click VERIFY_COMFYUI_KNOWN_GOOD.bat\n  This performs a full offline verification of all 39,046 dependency files.\n\nNORMAL SAFETY PROFILE\n  CPU only; custom nodes disabled; localhost 127.0.0.1:8188 only.\n  No automatic log deletion and no automatic force-kill.\n\nLOGS\n  Runtime\\ComfyUI\\logs\\normal\\<run-id>\n  A warning is planned after 100 runs or 1 GiB, but cleanup is never automatic.\n'''
    (staging / "ROUTINE_USE_GUIDE.txt").write_text(routine, encoding="utf-8", newline="\r\n")
    rollback = f'''FOXAI COMFYUI — RECOVERY AND ROLLBACK REFERENCE\n\nBaseline: {accepted['baseline_id']}\n\nThis baseline is verification metadata, not a second 1.5 GB runtime copy.\nNever edit files inside the baseline directory.\n\nIF VERIFICATION FAILS\n  1. Stop ComfyUI with STOP_COMFYUI_NORMAL.bat.\n  2. Do not run pip install/uninstall against Desktop, Core, host Python, or the target.\n  3. Preserve Runtime\\ComfyUI\\state and Runtime\\ComfyUI\\logs.\n  4. Preserve the C3C staging wheelhouse and every C3 evidence folder.\n  5. Rebuild only through a new reviewed staging transaction; never merge into the target.\n\nLAUNCHER ROLLBACK REFERENCES\n  C3G backups: FOXAI_USBC3G_CONTROLLED_INTEGRATION\\APPLY_OUTPUT\\20260718T034126Z\\BACKUP\n  C3J backups: FOXAI_USBC3J_NORMAL_ENABLEMENT_APPLY\\APPLY_OUTPUT\\20260718T044323Z\\BACKUP\n\nDEPENDENCY ACQUISITION SOURCE\n  FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\\STAGING_WHEELHOUSE\n\nISOLATED TARGET\n  Runtime\\ComfyUI\\site-packages\n  Expected: 39,046 files, 1,520,221,467 bytes\n  Tree SHA-256: {accepted['isolated_target']['tree_sha256']}\n'''
    (staging / "ROLLBACK_AND_RECOVERY_GUIDE.txt").write_text(rollback, encoding="utf-8", newline="\r\n")
    closure = {
        "schema": 1,
        "baseline_id": accepted["baseline_id"],
        "portability_mode": "PORTABLE_READY",
        "creative_studio_mode": "USB_OWNED_ISOLATED_CPU_READY",
        "routine_use_ready": True,
        "custom_nodes_default": "disabled",
        "network_binding": "127.0.0.1:8188",
        "isolated_target": accepted["isolated_target"],
        "normal_lifecycle_verified": True,
        "evidence_chain_complete_through": "C3K",
    }
    write_json(staging / "PORTABILITY_CLOSURE.json", closure)
    content_rows = []
    for path in sorted(staging.rglob("*"), key=lambda p: p.relative_to(staging).as_posix().casefold()):
        if path.is_file():
            content_rows.append({"path": path.relative_to(staging).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(staging / "BASELINE_CONTENT_HASHES.json", {"verified": True, "files": content_rows})
    content_hash = sha256_file(staging / "BASELINE_CONTENT_HASHES.json")
    seal = {
        "schema": 1,
        "baseline_id": accepted["baseline_id"],
        "classification": SUCCESS,
        "sealed_utc": utc_now().isoformat(),
        "operator_approval": "Proceed to USB C3L portability closure and known-good baseline seal under the accepted C3K results.",
        "isolated_target": accepted["isolated_target"],
        "integrated_file_count": len(integrated["files"]),
        "protected_file_count": len(protected["files"]),
        "content_hash_manifest_sha256": content_hash,
        "immutable_by_contract": True,
        "note": "Do not edit this directory. Create a new reviewed baseline for future changes.",
    }
    write_json(staging / "BASELINE_SEAL.json", seal)
    tree = baseline_tree(staging)
    if not tree["verified"]:
        raise RuntimeError(f"Staged baseline tree failed: {tree['issues']}")
    return tree


def copy_atomic(source: Path, staged: Path) -> None:
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, staged)


def exact_file(path: Path, expected_size: int, expected_hash: str) -> bool:
    return path.is_file() and not path.is_symlink() and path.stat().st_size == expected_size and sha256_file(path) == expected_hash


def make_review_zip(output: Path, baseline: Path) -> Path:
    review_copy = output / "BASELINE_REVIEW_COPY"
    if review_copy.exists():
        shutil.rmtree(review_copy)
    shutil.copytree(baseline, review_copy)
    evidence_files = []
    for path in sorted(output.rglob("*"), key=lambda p: p.relative_to(output).as_posix().casefold()):
        if path.is_file() and path.name not in {"UPLOAD_THIS_C3L_REVIEW.zip", "evidence_integrity.json"}:
            evidence_files.append({"file": path.relative_to(output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(output / "evidence_integrity.json", {"verified": True, "file_count": len(evidence_files), "files": evidence_files})
    archive = output / "UPLOAD_THIS_C3L_REVIEW.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in sorted(output.rglob("*"), key=lambda p: p.relative_to(output).as_posix().casefold()):
            if path.is_file() and path != archive:
                handle.write(path, path.relative_to(output).as_posix())
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    package = args.package.resolve()
    started = utc_now()
    run_id = stamp(started)
    output = package / "SEAL_OUTPUT" / run_id
    output.mkdir(parents=True, exist_ok=False)
    committed: list[tuple[Path, str, int]] = []
    staged_artifacts: list[Path] = []
    created_dirs: list[Path] = []
    try:
        if package.parent.resolve() != root:
            raise RuntimeError(f"Package must be directly under the FOXAI root: package={package} root={root}")
        package_result = verify_package(package)
        write_json(output / "package_verification.json", package_result)
        approval = read_json(package / "OPERATOR_APPROVAL.json")
        if approval.get("approved") is not True:
            raise RuntimeError("Operator approval is missing")
        accepted = read_json(package / "KNOWN_ACCEPTED_C3K_STATE.json")
        c3k = verify_c3k(root, accepted)
        write_json(output / "c3k_input_verification.json", c3k)
        stopped = verify_stopped(root)
        write_json(output / "preseal_stopped_state.json", stopped)
        integrated = verify_rows(root, accepted["integrated_files"], "integrated")
        protected = verify_rows(root, accepted["protected_files"], "protected")
        write_json(output / "integrated_files_before.json", integrated)
        write_json(output / "protected_files_before.json", protected)
        pre_inventory = inventory_target(root, accepted, "PRE-SEAL")
        write_json(output / "isolated_target_before_summary.json", {k: v for k, v in pre_inventory.items() if k != "files"})

        portability = root / "System/Portability"
        baselines_parent = portability / "Baselines"
        final_baseline = baselines_parent / accepted["baseline_id"]
        pointer_final = portability / "COMFYUI_KNOWN_GOOD_CURRENT.json"
        verifier_final = portability / "verify_comfyui_known_good.py"
        verify_bat_final = root / "VERIFY_COMFYUI_KNOWN_GOOD.bat"
        ready_final = root / "COMFYUI_PORTABILITY_READY.txt"
        finals = [final_baseline, pointer_final, verifier_final, verify_bat_final, ready_final]
        existing = [str(path) for path in finals if path.exists() or path.is_symlink()]
        if existing:
            raise RuntimeError(f"C3L final paths must be absent before sealing: {existing}")

        baseline_build = output / "BASELINE_BUILD"
        baseline_tree_result = build_baseline(baseline_build, root, accepted, pre_inventory, integrated, protected, c3k)
        write_json(output / "baseline_build_tree.json", baseline_tree_result)
        pointer = {
            "schema": 1,
            "baseline_id": accepted["baseline_id"],
            "baseline_relative_path": final_baseline.relative_to(root).as_posix(),
            "baseline_file_count": baseline_tree_result["file_count"],
            "baseline_tree_sha256": baseline_tree_result["tree_sha256"],
            "classification": SUCCESS,
            "isolated_target": accepted["isolated_target"],
            "created_by": "USB C3L portability closure and known-good baseline seal",
        }
        pointer_candidate = output / "CANDIDATES/COMFYUI_KNOWN_GOOD_CURRENT.json"
        write_json(pointer_candidate, pointer)
        verifier_candidate = package / "Payload/System/Portability/verify_comfyui_known_good.py"
        bat_candidate = package / "Payload/VERIFY_COMFYUI_KNOWN_GOOD.bat"
        ready_candidate = output / "CANDIDATES/COMFYUI_PORTABILITY_READY.txt"
        ready_text = f'''FOXAI COMFYUI PORTABILITY: READY\n\nKnown-good baseline: {accepted['baseline_id']}\nStatus: {SUCCESS}\n\nRoutine controls:\n  START_COMFYUI_NORMAL.bat\n  STATUS_COMFYUI_NORMAL.bat\n  STOP_COMFYUI_NORMAL.bat\n\nFull offline verification:\n  VERIFY_COMFYUI_KNOWN_GOOD.bat\n\nProfile: CPU only, custom nodes disabled, localhost 127.0.0.1:8188.\nBaseline metadata:\n  {final_baseline.relative_to(root)}\n'''
        ready_candidate.parent.mkdir(parents=True, exist_ok=True)
        ready_candidate.write_text(ready_text, encoding="utf-8", newline="\r\n")

        for parent in [portability, baselines_parent]:
            if not parent.exists():
                parent.mkdir()
                created_dirs.append(parent)
            elif not parent.is_dir() or parent.is_symlink():
                raise RuntimeError(f"Unsafe C3L parent: {parent}")

        staged_baseline = baselines_parent / f".{accepted['baseline_id']}.C3L_STAGING_{run_id}"
        shutil.copytree(baseline_build, staged_baseline)
        staged_artifacts.append(staged_baseline)
        if baseline_tree(staged_baseline)["tree_sha256"] != baseline_tree_result["tree_sha256"]:
            raise RuntimeError("Adjacent staged baseline hash mismatch")
        staged_files = []
        for source, final in [
            (pointer_candidate, pointer_final),
            (verifier_candidate, verifier_final),
            (bat_candidate, verify_bat_final),
            (ready_candidate, ready_final),
        ]:
            staged = final.with_name(final.name + f".C3L_STAGED_{run_id}")
            copy_atomic(source, staged)
            staged_artifacts.append(staged)
            if sha256_file(staged) != sha256_file(source):
                raise RuntimeError(f"Staged candidate hash mismatch: {final}")
            staged_files.append((staged, final))

        os.rename(staged_baseline, final_baseline)
        staged_artifacts.remove(staged_baseline)
        final_baseline_tree = baseline_tree(final_baseline)
        if final_baseline_tree["tree_sha256"] != baseline_tree_result["tree_sha256"]:
            raise RuntimeError("Committed baseline tree mismatch")
        committed.append((final_baseline, final_baseline_tree["tree_sha256"], -1))
        for staged, final in staged_files:
            os.replace(staged, final)
            staged_artifacts.remove(staged)
            committed.append((final, sha256_file(final), final.stat().st_size))

        # The output-side build tree is no longer needed after exact commit.
        shutil.rmtree(baseline_build)

        # Full post-seal verification. Metadata writes must not alter the runtime.
        post_inventory = inventory_target(root, accepted, "POST-SEAL")
        integrated_after = verify_rows(root, accepted["integrated_files"], "integrated")
        protected_after = verify_rows(root, accepted["protected_files"], "protected")
        stopped_after = verify_stopped(root)
        if post_inventory["tree_sha256"] != pre_inventory["tree_sha256"]:
            raise RuntimeError("Isolated target changed during baseline sealing")
        if baseline_tree(final_baseline)["tree_sha256"] != pointer["baseline_tree_sha256"]:
            raise RuntimeError("Final baseline no longer matches pointer")
        write_json(output / "isolated_target_after_summary.json", {k: v for k, v in post_inventory.items() if k != "files"})
        write_json(output / "integrated_files_after.json", integrated_after)
        write_json(output / "protected_files_after.json", protected_after)
        write_json(output / "postseal_stopped_state.json", stopped_after)
        write_json(output / "baseline_commit_receipt.json", {
            "committed": True,
            "baseline": str(final_baseline),
            "pointer": str(pointer_final),
            "verifier": str(verifier_final),
            "verify_bat": str(verify_bat_final),
            "ready_notice": str(ready_final),
            "baseline_file_count": pointer["baseline_file_count"],
            "baseline_tree_sha256": pointer["baseline_tree_sha256"],
            "runtime_content_modified": False,
            "launcher_modified": False,
            "network_access": False,
            "process_launch": False,
            "comfyui_launch": False,
        })
        completed = utc_now()
        receipt = {
            "action": "foxai_usbc3l_portability_closure_known_good_seal",
            "started": started.isoformat(),
            "completed": completed.isoformat(),
            "elapsed_seconds": round((completed - started).total_seconds(), 3),
            "verified": True,
            "classification": SUCCESS,
            "baseline_id": accepted["baseline_id"],
            "baseline_path": str(final_baseline),
            "isolated_target": accepted["isolated_target"],
            "integrated_file_count": len(accepted["integrated_files"]),
            "protected_file_count": len(accepted["protected_files"]),
            "normal_state": "STOPPED",
            "routine_use_ready": True,
            "network_access": False,
            "launcher_change": False,
            "runtime_content_change": False,
            "package_change": False,
            "comfyui_launched": False,
            "blocking_findings": [],
        }
        write_json(output / "receipt.json", receipt)
        write_json(output / "classification.json", {
            "mode": SUCCESS,
            "verified": True,
            "blocking_findings": [],
            "routine_use_ready": True,
            "next_state": "Use START/STATUS/STOP_COMFYUI_NORMAL and preserve the sealed baseline.",
        })
        report = f'''# FOXAI USB C3L — Portability Closure\n\n- Classification: `{SUCCESS}`\n- Verified: `True`\n- Baseline: `{accepted['baseline_id']}`\n- Isolated target files: **{accepted['isolated_target']['file_count']}**\n- Isolated target bytes: **{accepted['isolated_target']['total_bytes']}**\n- Runtime tree SHA-256: `{accepted['isolated_target']['tree_sha256']}`\n- Routine use ready: **True**\n\nC3L added only compact baseline metadata, an offline verifier, and operating/recovery documentation. It did not launch anything or modify the isolated runtime or launch policy.\n'''
        (output / "report.md").write_text(report, encoding="utf-8", newline="\n")
        archive = make_review_zip(output, final_baseline)
        print(f"[COMPLETE] C3L sealed the known-good portability baseline.", flush=True)
        print(f"Review ZIP: {archive}", flush=True)
        return 0
    except Exception as exc:
        # Remove uncommitted staging artifacts first.
        staging_cleanup = []
        for staged in reversed(staged_artifacts):
            try:
                if staged.is_dir() and not staged.is_symlink():
                    shutil.rmtree(staged)
                    staging_cleanup.append({"path": str(staged), "removed": True})
                elif staged.is_file() and not staged.is_symlink():
                    staged.unlink()
                    staging_cleanup.append({"path": str(staged), "removed": True})
            except Exception as stage_exc:
                staging_cleanup.append({"path": str(staged), "removed": False, "error": f"{type(stage_exc).__name__}: {stage_exc}"})
        # Remove only exact C3L additions. Never touch runtime/source/launchers.
        rollback = []
        for path, digest, size in reversed(committed):
            try:
                if path.is_dir() and not path.is_symlink():
                    current = baseline_tree(path)
                    if current["tree_sha256"] == digest:
                        shutil.rmtree(path)
                        rollback.append({"path": str(path), "removed": True})
                    else:
                        rollback.append({"path": str(path), "removed": False, "reason": "changed after commit"})
                elif size >= 0 and exact_file(path, size, digest):
                    path.unlink()
                    rollback.append({"path": str(path), "removed": True})
                else:
                    rollback.append({"path": str(path), "removed": False, "reason": "missing or changed"})
            except Exception as rollback_exc:
                rollback.append({"path": str(path), "removed": False, "error": f"{type(rollback_exc).__name__}: {rollback_exc}"})
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
            "staging_cleanup": staging_cleanup,
            "rollback": rollback,
            "runtime_content_change": False,
            "launcher_change": False,
            "network_access": False,
            "comfyui_launched": False,
        }
        write_json(output / "classification.json", failure)
        write_json(output / "receipt.json", failure)
        (output / "report.md").write_text(f"# C3L stopped fail-closed\n\n{failure['error']}\n", encoding="utf-8", newline="\n")
        try:
            make_review_zip(output, output / "NONEXISTENT_BASELINE") if False else None
            evidence_files = []
            for path in sorted(output.rglob("*"), key=lambda p: p.relative_to(output).as_posix().casefold()):
                if path.is_file() and path.name not in {"UPLOAD_THIS_C3L_REVIEW.zip", "evidence_integrity.json"}:
                    evidence_files.append({"file": path.relative_to(output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
            write_json(output / "evidence_integrity.json", {"verified": True, "file_count": len(evidence_files), "files": evidence_files})
            archive = output / "UPLOAD_THIS_C3L_REVIEW.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
                for path in sorted(output.rglob("*"), key=lambda p: p.relative_to(output).as_posix().casefold()):
                    if path.is_file() and path != archive:
                        handle.write(path, path.relative_to(output).as_posix())
        except Exception:
            pass
        print(f"[STOPPED] C3L failed closed: {type(exc).__name__}: {exc}", flush=True)
        return 19


if __name__ == "__main__":
    raise SystemExit(main())
