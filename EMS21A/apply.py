from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVAL_PHRASE = (
    "APPROVE EXTENSION MANAGER OPERATOR CLARITY PHASE 2.1 APPLY"
)

TARGET = "core/foxai_web.py"
BASELINE_SHA256 = "5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548"
CANDIDATE_SHA256 = "e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525"
DIFF_SHA256 = "01e9c29f794536092daefd706ae52afd73dd6baee31fb4860f1c6a8e25712e14"
LIVE_VERIFY_RECEIPT_SHA256 = "9a6bd073e9b4408d4fa3dc7357ffbf695ec20808973cb5402d1f3ec357fe24ef"
PREVIEW_RECEIPT_SHA256 = "0db39c0a04fa5c6f693f7be2a3c66b895ae7dbe5294bed6c2c4e5c1a190c3c05"

UNCHANGED_HASHES = {
    "core/server.py": "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81",
    "Config/application_registry.json": "6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022",
    "Config/fleet_registry.json": "18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6",
    "core/service_registry.py": "cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b",
}

RUNTIME_STATE_PATHS = [
    "Config/extension_state.json",
    "Backups/ExtensionState",
    "Reports/ExtensionState",
]

PORTS_REQUIRED_CLOSED = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8098: "Vision benchmark",
    8099: "Other benchmark",
}

REQUIRED_LIVE_CHECKS = {
    "package_manifest",
    "phase2_applied_receipt",
    "exact_artifacts",
    "live_baselines",
    "node_and_browser",
    "backend_regression",
    "live_inventory_preview",
    "state_logic_unchanged",
    "static_contract",
    "boundary_watch",
}


class ApplyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "kind": None,
            "sha256": None,
            "size": 0,
        }
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "kind": "file",
            "sha256": sha256(path),
            "size": stat.st_size,
        }
    if path.is_dir():
        files = {}
        for item in sorted(path.rglob("*")):
            if item.is_file():
                relative = str(item.relative_to(path)).replace("\\", "/")
                files[relative] = {
                    "sha256": sha256(item),
                    "size": item.stat().st_size,
                }
        return {
            "exists": True,
            "kind": "directory",
            "files": files,
        }
    return {
        "exists": True,
        "kind": "other",
    }


def runtime_state_snapshot(root: Path) -> dict[str, Any]:
    return {
        relative: file_state(root / relative)
        for relative in RUNTIME_STATE_PATHS
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Config/application_registry.json").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise ApplyError(
        r"FOXAI root not found. Extract the complete EMS21A folder directly inside Z:\FOXAI."
    )


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def package_manifest(package: Path) -> dict[str, Any]:
    manifest = package / "sums.txt"
    if not manifest.is_file():
        raise ApplyError("Package manifest is missing.")
    checks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": digest,
            "actual": actual,
            "ok": actual == digest,
        })
    if not checks or not all(item["ok"] for item in checks):
        raise ApplyError("Package manifest verification failed.")
    return {"passed": True, "files": checks}


def load_verifier(package: Path):
    path = package / "approved_preview/verify_preview.py"
    module_name = "ems21a_approved_preview_verifier"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def validate_live_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/live_verify_receipt.json"
    actual = sha256(path) if path.is_file() else None
    if actual != LIVE_VERIFY_RECEIPT_SHA256:
        raise ApplyError("Approved live-verification receipt hash changed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = data.get("checks") or {}
    conditions = {
        "state": data.get("state") == "exact_preview_verified",
        "verified": data.get("verified") is True,
        "live_unmodified": data.get("live_files_modified") is False,
        "no_apply_capability": data.get("apply_capability_present") is False,
        "exact_scope": data.get("changed_files_proposed") == ["core/foxai_web.py"],
        "unchanged_scope": data.get("unchanged_files_explicit") == [
            "core/server.py",
            "Config/application_registry.json",
            "Config/fleet_registry.json",
            "core/service_registry.py",
            "Config/extension_state.json",
        ],
        "no_deletes": data.get("delete_operations") == [],
        "protected_changes_empty": data.get("protected_changes") == [],
        "required_checks_present": REQUIRED_LIVE_CHECKS.issubset(set(checks.keys())),
        "required_checks_passed": all(
            isinstance(checks.get(name), dict) and checks[name].get("passed") is True
            for name in REQUIRED_LIVE_CHECKS
        ),
        "state_file_absent": (checks.get("live_baselines") or {}).get("extension_state_absent") is True,
    }
    if not all(conditions.values()):
        raise ApplyError("Approved live-verification receipt is incomplete.")
    return {"passed": True, "sha256": actual, "conditions": conditions}

def validate_preview_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/preview_receipt.json"
    actual = sha256(path) if path.is_file() else None
    if actual != PREVIEW_RECEIPT_SHA256:
        raise ApplyError("Approved preview receipt hash changed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    conditions = {
        "state": data.get("state") == "exact_preview_ready",
        "verified": data.get("verified") is True,
        "live_unmodified": data.get("live_files_modified") is False,
        "candidate_created": data.get("candidate_created") is True,
        "no_apply_capability": data.get("apply_capability_present") is False,
        "exact_scope": data.get("changed_files_proposed") == ["core/foxai_web.py"],
        "no_deletes": data.get("delete_operations") == [],
        "candidate_unchanged": data.get("candidate_and_diff_unchanged") is True,
        "portable_diff": data.get("portable_diff_verification") == "pure_python_unified_diff",
        "external_patch_not_required": data.get("external_patch_required") is False,
        "verifier_revision": data.get("verifier_revision") == 2,
    }
    if not all(conditions.values()):
        raise ApplyError("Approved preview receipt is incomplete.")
    return {"passed": True, "sha256": actual, "conditions": conditions}

def exact_payload_check(package: Path) -> dict[str, Any]:
    baseline = package / "approved/foxai_web.baseline.py"
    candidate = package / "payload/foxai_web.py"
    diff = package / "approved/foxai_web.diff"
    checks = {
        "baseline_sha256":
            sha256(baseline) == BASELINE_SHA256,
        "candidate_sha256":
            sha256(candidate) == CANDIDATE_SHA256,
        "diff_sha256":
            sha256(diff) == DIFF_SHA256,
    }
    if not all(checks.values()):
        raise ApplyError("Exact payload identity failed.")
    return {"passed": True, "checks": checks}


def unchanged_contracts(root: Path) -> dict[str, Any]:
    checks = []
    for relative, expected in UNCHANGED_HASHES.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": relative,
            "expected": expected,
            "actual": actual,
            "ok": actual == expected,
        })
    if not all(item["ok"] for item in checks):
        raise ApplyError(
            "An explicitly unchanged server or registry changed."
        )
    return {"passed": True, "files": checks}


def protected_snapshot(verifier, root: Path) -> dict[str, Any]:
    return verifier.snapshot(root)

def changed_paths(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    return [
        key
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def verification_suite(
    verifier,
    preview: Path,
    root: Path,
    label: str,
) -> dict[str, Any]:
    result = {
        "preview_manifest": verifier.package_manifest(preview),
        "phase2_applied_receipt": verifier.applied(preview),
        "exact_artifacts": verifier.exact(preview),
        "node_and_browser": verifier.node_browser(preview),
        "backend_regression": verifier.backend(preview),
        "live_inventory_preview": verifier.backend(preview, root),
        "state_logic_unchanged": verifier.state_logic_unchanged(preview),
        "static_contract": verifier.static(preview),
        "boundary_watch": verifier.boundary(root),
    }
    result["passed"] = all(
        isinstance(value, dict) and value.get("passed") is True
        for value in result.values()
        if isinstance(value, dict)
    )
    if result["passed"] is not True:
        raise ApplyError(f"{label} verification suite failed.")
    return result

def live_preview_copy(
    source_preview: Path,
    root: Path,
    temporary: Path,
) -> Path:
    target = temporary / "preview"
    shutil.copytree(source_preview, target)
    shutil.copy2(
        root / TARGET,
        target / "candidate/core/foxai_web.py",
    )
    return target


def copy_fsync(source: Path, target: Path) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def create_backup(
    root: Path,
    stamp: str,
) -> tuple[Path, dict[str, Any]]:
    backup_root = (
        root
        / "Backups/SecurityMilestone"
        / f"EMS21_{stamp}"
    )
    if backup_root.exists():
        raise ApplyError(
            f"Backup folder already exists: {backup_root}"
        )
    backup_path = backup_root / TARGET
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / TARGET, backup_path)
    actual = sha256(backup_path)
    if actual != BASELINE_SHA256:
        raise ApplyError("Backup verification failed.")
    return backup_root, {
        "passed": True,
        "root": str(backup_root),
        "path": str(backup_path),
        "expected": BASELINE_SHA256,
        "actual": actual,
    }


def install_candidate(root: Path, package: Path) -> dict[str, Any]:
    payload = package / "payload/foxai_web.py"
    target = root / TARGET
    stage = target.with_name(
        f".{target.name}.ems21.{os.getpid()}.new"
    )
    try:
        copy_fsync(payload, stage)
        stage_hash = sha256(stage)
        if stage_hash != CANDIDATE_SHA256:
            raise ApplyError("Staged candidate hash failed.")
        os.replace(stage, target)
        final_hash = sha256(target)
        if final_hash != CANDIDATE_SHA256:
            raise ApplyError("Installed candidate hash failed.")
        return {
            "passed": True,
            "stage_sha256": stage_hash,
            "final_sha256": final_hash,
        }
    finally:
        try:
            stage.unlink(missing_ok=True)
        except Exception:
            pass


def rollback(
    verifier,
    root: Path,
    backup: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": True,
        "succeeded": False,
        "final_sha256": None,
        "boundary_watch": None,
        "failure": None,
    }
    target = root / TARGET
    stage = target.with_name(
        f".{target.name}.ems21.rollback.{os.getpid()}"
    )
    try:
        copy_fsync(Path(backup["path"]), stage)
        if sha256(stage) != BASELINE_SHA256:
            raise ApplyError("Rollback stage hash failed.")
        os.replace(stage, target)
        result["final_sha256"] = sha256(target)
        if result["final_sha256"] != BASELINE_SHA256:
            raise ApplyError("Rollback final hash failed.")
        compile(
            target.read_text(encoding="utf-8"),
            str(target),
            "exec",
        )
        result["boundary_watch"] = verifier.boundary(root)
        result["succeeded"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        try:
            stage.unlink(missing_ok=True)
        except Exception:
            pass
    return result


def checkpoint(output: Path, receipt: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stage = output / "receipt.json.tmp"
    stage.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    os.replace(stage, output / "receipt.json")


def write_report(output: Path, receipt: dict[str, Any]) -> None:
    lines = [
        "# Extension Manager Operator Clarity Phase 2.1",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Operator approved: **{receipt['operator_approved']}**",
        f"- Changed files: **{receipt['changed_files']}**",
        f"- Runtime state created by source apply: "
        f"**{receipt['runtime_state_created']}**",
        f"- Delete operations: **{receipt['delete_operations']}**",
        f"- Rollback performed: **{receipt['rollback_performed']}**",
        f"- Final live SHA-256: `{receipt.get('final_live_sha256')}`",
        f"- Failure: **{receipt.get('failure')}**",
        "",
        "Allowed live source scope: `core/foxai_web.py` only.",
        "",
        "This source apply does not enable, disable, or restore any extension.",
        "",
        "Success requires `State: applied_verified` and `Verified: True`.",
    ]
    (output / "report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def zip_output(output: Path) -> Path:
    target = output.with_suffix(".zip")
    stage = target.with_suffix(".zip.tmp")
    target.unlink(missing_ok=True)
    stage.unlink(missing_ok=True)
    with zipfile.ZipFile(
        stage,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(
                    file,
                    arcname=f"{output.name}/{file.relative_to(output)}",
                )
    os.replace(stage, target)
    return target


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    preview = package / "approved_preview"
    verifier = load_verifier(package)

    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package / f"EMS21_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    before = protected_snapshot(verifier, root)
    before_runtime_state = runtime_state_snapshot(root)
    original_target = file_state(root / TARGET)
    candidate_install_started = False
    backup = None

    receipt: dict[str, Any] = {
        "action":
            "extension_manager_operator_clarity_phase2_1_transactional_apply",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "approval_phrase_required": APPROVAL_PHRASE,
        "allowed_target": TARGET,
        "explicitly_unchanged": list(UNCHANGED_HASHES.keys()),
        "runtime_state_paths_must_remain_unchanged": RUNTIME_STATE_PATHS,
        "changed_files": [],
        "runtime_state_created": False,
        "delete_operations": [],
        "rollback_performed": False,
        "rollback": None,
        "live_files_modified": False,
        "backup": None,
        "final_live_sha256": original_target.get("sha256"),
        "checks": {},
        "failure": None,
    }
    checkpoint(output, receipt)

    try:
        receipt["checks"]["package_manifest"] = (
            package_manifest(package)
        )
        receipt["checks"]["preview_manifest"] = (
            verifier.package_manifest(preview)
        )
        receipt["checks"]["preview_receipt"] = (
            validate_preview_receipt(package)
        )
        receipt["checks"]["live_verify_receipt"] = (
            validate_live_receipt(package)
        )
        receipt["checks"]["exact_payload"] = (
            exact_payload_check(package)
        )

        active_ports = [
            {"port": port, "label": label}
            for port, label in PORTS_REQUIRED_CLOSED.items()
            if port_open(port)
        ]
        if active_ports:
            raise ApplyError(
                "Close FOXAI WebUI, Chat Engine, and benchmark "
                f"servers before applying: {active_ports}"
            )
        receipt["checks"]["ports_closed"] = {
            "passed": True,
            "ports": PORTS_REQUIRED_CLOSED,
        }

        receipt["checks"]["live_baselines"] = (
            verifier.live_baselines(root)
        )
        receipt["checks"]["unchanged_contracts"] = (
            unchanged_contracts(root)
        )
        receipt["checks"]["runtime_state_preflight"] = {
            "passed": True,
            "snapshot": before_runtime_state,
        }
        receipt["checks"]["preflight"] = (
            verification_suite(
                verifier,
                preview,
                root,
                "candidate preflight",
            )
        )
        checkpoint(output, receipt)

        print()
        print("=" * 72)
        print("FOXAI EXTENSION MANAGER — OPERATOR CLARITY")
        print("PHASE 2.1 TRANSACTIONAL SOURCE APPLY")
        print("=" * 72)
        print()
        print("Preflight verified.")
        print("Allowed live source target:", TARGET)
        print("This apply will NOT change extension state.")
        print("This apply will NOT create extension_state.json.")
        print("This apply adds help and clarity only; it will NOT enable or disable an extension.")
        print("Delete operations: none")
        print("Verified backup and automatic rollback are mandatory.")
        print()
        print("Enter the exact approval phrase:")
        print(APPROVAL_PHRASE)
        print()
        entered = input("> ").strip()

        if entered != APPROVAL_PHRASE:
            receipt.update({
                "state": "stopped_not_approved",
                "verified": True,
                "operator_approved": False,
                "changed_files": [],
                "runtime_state_created": False,
                "live_files_modified": False,
                "final_live_sha256": sha256(root / TARGET),
            })
            checkpoint(output, receipt)
        else:
            receipt["operator_approved"] = True
            _, backup = create_backup(root, stamp)
            receipt["backup"] = backup
            checkpoint(output, receipt)

            candidate_install_started = True
            receipt["checks"]["installation"] = (
                install_candidate(root, package)
            )
            receipt["changed_files"] = [TARGET]
            receipt["live_files_modified"] = True
            receipt["final_live_sha256"] = sha256(root / TARGET)
            checkpoint(output, receipt)

            with tempfile.TemporaryDirectory(
                prefix="ems21_postflight_"
            ) as temporary:
                live_preview = live_preview_copy(
                    preview,
                    root,
                    Path(temporary),
                )
                receipt["checks"]["postflight"] = (
                    verification_suite(
                        verifier,
                        live_preview,
                        root,
                        "live postflight",
                    )
                )

            receipt["checks"]["unchanged_contracts_postflight"] = (
                unchanged_contracts(root)
            )

            after_runtime_state = runtime_state_snapshot(root)
            runtime_state_unchanged = (
                before_runtime_state == after_runtime_state
            )
            receipt["checks"]["runtime_state_immutability"] = {
                "passed": runtime_state_unchanged,
                "before": before_runtime_state,
                "after": after_runtime_state,
            }
            receipt["runtime_state_created"] = not runtime_state_unchanged
            if not runtime_state_unchanged:
                raise ApplyError(
                    "The source apply changed extension runtime state."
                )

            after = protected_snapshot(verifier, root)
            changes = changed_paths(before, after)
            protected_changes = [
                path for path in changes
                if path != TARGET
            ]
            target_changed = TARGET in changes
            receipt["checks"]["protected_immutability"] = {
                "passed": (
                    not protected_changes and target_changed
                ),
                "protected_changes": protected_changes,
                "target_changed": target_changed,
                "observed_changes": changes,
            }
            if protected_changes:
                raise ApplyError(
                    "A protected non-target, registry, extension state, "
                    f"or security log changed: {protected_changes}"
                )
            if not target_changed:
                raise ApplyError(
                    "The approved source target change was not observed."
                )

            final_hash = sha256(root / TARGET)
            if final_hash != CANDIDATE_SHA256:
                raise ApplyError(
                    "Final candidate hash verification failed."
                )

            receipt.update({
                "state": "applied_verified",
                "verified": True,
                "operator_approved": True,
                "changed_files": [TARGET],
                "runtime_state_created": False,
                "delete_operations": [],
                "rollback_performed": False,
                "live_files_modified": True,
                "final_live_sha256": final_hash,
            })
            checkpoint(output, receipt)

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if candidate_install_started and backup is not None:
            rollback_result = rollback(
                verifier,
                root,
                backup,
            )
            receipt["rollback_performed"] = True
            receipt["rollback"] = rollback_result
            if rollback_result.get("succeeded") is True:
                after = protected_snapshot(verifier, root)
                changes = changed_paths(before, after)
                runtime_restored = (
                    runtime_state_snapshot(root) == before_runtime_state
                )
                receipt.update({
                    "state": "rolled_back_verified",
                    "verified": not changes and runtime_restored,
                    "changed_files": [],
                    "runtime_state_created": not runtime_restored,
                    "live_files_modified": bool(changes),
                    "final_live_sha256": sha256(root / TARGET),
                })
                receipt["checks"]["rollback_final_state"] = {
                    "passed": not changes and runtime_restored,
                    "protected_changes": changes,
                    "runtime_state_restored": runtime_restored,
                }
            else:
                receipt.update({
                    "state": "rollback_failed",
                    "verified": False,
                    "final_live_sha256": (
                        sha256(root / TARGET)
                        if (root / TARGET).is_file()
                        else None
                    ),
                })
        else:
            after = protected_snapshot(verifier, root)
            changes = changed_paths(before, after)
            target_unchanged = (
                file_state(root / TARGET) == original_target
            )
            runtime_unchanged = (
                runtime_state_snapshot(root) == before_runtime_state
            )
            receipt.update({
                "state": "stopped_fail_closed",
                "verified": (
                    not changes
                    and target_unchanged
                    and runtime_unchanged
                ),
                "changed_files": [],
                "runtime_state_created": not runtime_unchanged,
                "live_files_modified": bool(changes),
                "final_live_sha256": (
                    sha256(root / TARGET)
                    if (root / TARGET).is_file()
                    else None
                ),
            })
            receipt["checks"]["fail_closed_final_state"] = {
                "passed": (
                    not changes
                    and target_unchanged
                    and runtime_unchanged
                ),
                "protected_changes": changes,
                "target_unchanged": target_unchanged,
                "runtime_state_unchanged": runtime_unchanged,
            }
        checkpoint(output, receipt)

    write_report(output, receipt)
    checkpoint(output, receipt)
    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("FOXAI EXTENSION MANAGER — OPERATOR CLARITY")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Changed files:", receipt["changed_files"])
    print("Runtime state created:", receipt["runtime_state_created"])
    print("Delete operations:", receipt["delete_operations"])
    print("Rollback performed:", receipt["rollback_performed"])
    print("Final live SHA-256:", receipt["final_live_sha256"])
    print("Output ZIP:", output_zip)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    print("Nothing is considered installed unless the receipt says:")
    print("  State: applied_verified")
    print("  Verified: True")
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] == "applied_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
