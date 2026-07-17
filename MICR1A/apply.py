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
    "APPROVE MISSION IMAGE CONTINUITY LEAKAGE REPAIR PHASE 1 APPLY"
)

TARGET = "core/foxai_web.py"
BASELINE_SHA256 = "3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d"
CANDIDATE_SHA256 = "7fcbddeae22904af7f9aa75e9546e3e28721d455222fbfc42c27c5186ba45180"
DIFF_SHA256 = "2a847670fc10575b9eb3c1e25c305dbd087784ceccb3f488b4d07626422a2165"
SERVER_SHA256 = "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81"
LIVE_VERIFY_RECEIPT_SHA256 = "36a7f429e055bd593400d0022c9c606158927f7cb89cde1cd0ac8f02ff1ae12d"
PREVIEW_RECEIPT_SHA256 = "dfe0dc34f4098756b985ef779c56356ea7f1595ec0f33605d56dd5e072af7a50"

PORTS_REQUIRED_CLOSED = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8098: "Vision benchmark",
    8099: "Other benchmark",
}

REQUIRED_LIVE_CHECKS = {
    "package_manifest",
    "applied_baseline_receipt",
    "exact_artifacts",
    "live_baselines",
    "vision_assets",
    "node_and_browser",
    "continuity_and_leakage_helpers",
    "static_contract",
    "boundary_watch",
    "existing_payload_scan",
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
            "sha256": None,
            "size": 0,
            "mtime_ns": None,
        }
    stat = path.stat()
    return {
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "core/server.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise ApplyError(
        r"FOXAI root not found. Extract the complete MICR1A folder directly inside Z:\FOXAI."
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
    module_name = "micr1a_approved_preview_verifier"
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
        "state":
            data.get("state") == "exact_preview_verified",
        "verified":
            data.get("verified") is True,
        "live_unmodified":
            data.get("live_files_modified") is False,
        "no_apply_in_preview":
            data.get("apply_capability_present") is False,
        "exact_scope":
            data.get("changed_files_proposed")
            == ["core/foxai_web.py"],
        "server_unchanged":
            data.get("unchanged_files_explicit")
            == ["core/server.py"],
        "no_deletes":
            data.get("delete_operations") == [],
        "protected_changes_empty":
            data.get("protected_changes") == [],
        "required_checks_present":
            REQUIRED_LIVE_CHECKS.issubset(set(checks.keys())),
        "required_checks_passed":
            all(
                isinstance(checks.get(name), dict)
                and checks[name].get("passed") is True
                for name in REQUIRED_LIVE_CHECKS
            ),
        "no_persisted_payload_findings":
            (
                checks.get("existing_payload_scan") or {}
            ).get("finding_count") == 0,
    }
    if not all(conditions.values()):
        raise ApplyError(
            "Approved live-verification receipt is incomplete."
        )
    return {
        "passed": True,
        "sha256": actual,
        "conditions": conditions,
    }


def validate_preview_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/preview_receipt.json"
    actual = sha256(path) if path.is_file() else None
    if actual != PREVIEW_RECEIPT_SHA256:
        raise ApplyError("Approved preview receipt hash changed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    conditions = {
        "state":
            data.get("state") == "exact_preview_ready",
        "verified":
            data.get("verified") is True,
        "live_unmodified":
            data.get("live_files_modified") is False,
        "candidate_created":
            data.get("candidate_created") is True,
        "no_apply_capability":
            data.get("apply_capability_present") is False,
        "exact_scope":
            data.get("changed_files_proposed")
            == ["core/foxai_web.py"],
        "server_unchanged":
            data.get("unchanged_files_explicit")
            == ["core/server.py"],
        "no_deletes":
            data.get("delete_operations") == [],
    }
    if not all(conditions.values()):
        raise ApplyError("Approved preview receipt is incomplete.")
    return {
        "passed": True,
        "sha256": actual,
        "conditions": conditions,
    }


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


def protected_snapshot(verifier, root: Path) -> dict[str, Any]:
    return verifier.protected_snapshot(root)


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
        "preview_manifest":
            verifier.package_manifest(preview),
        "applied_baseline_receipt":
            verifier.applied_receipt(preview),
        "exact_artifacts":
            verifier.exact_artifacts(preview),
        "vision_assets":
            verifier.vision_assets(root),
        "node_and_browser":
            verifier.node_and_browser(preview),
        "continuity_and_leakage_helpers":
            verifier.helper_harness(preview),
        "static_contract":
            verifier.static_contract(preview),
        "boundary_watch":
            verifier.boundary_watch(root),
        "existing_payload_scan":
            verifier.existing_payload_scan(root),
    }
    result["no_persisted_payload_findings"] = (
        result["existing_payload_scan"].get("finding_count") == 0
    )
    result["passed"] = (
        all(
            isinstance(value, dict)
            and value.get("passed") is True
            for value in result.values()
            if isinstance(value, dict)
        )
        and result["no_persisted_payload_findings"]
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
        / f"MICR1_{stamp}"
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
        f".{target.name}.micr1.{os.getpid()}.new"
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
        f".{target.name}.micr1.rollback.{os.getpid()}"
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
        result["boundary_watch"] = verifier.boundary_watch(root)
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
        "# Mission Image Continuity + Payload Leakage Repair",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Operator approved: **{receipt['operator_approved']}**",
        f"- Changed files: **{receipt['changed_files']}**",
        f"- Delete operations: **{receipt['delete_operations']}**",
        f"- Rollback performed: **{receipt['rollback_performed']}**",
        f"- Final live SHA-256: `{receipt.get('final_live_sha256')}`",
        f"- Failure: **{receipt.get('failure')}**",
        "",
        "Allowed live scope: `core/foxai_web.py` only.",
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
    output = package / f"MICR1_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    before = protected_snapshot(verifier, root)
    original_target = file_state(root / TARGET)
    candidate_install_started = False
    backup = None

    receipt: dict[str, Any] = {
        "action":
            "mission_image_continuity_leakage_repair_phase1_transactional_apply",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "approval_phrase_required": APPROVAL_PHRASE,
        "allowed_target": TARGET,
        "explicitly_unchanged": ["core/server.py"],
        "changed_files": [],
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
        print("FOXAI MISSION IMAGE CONTINUITY + PAYLOAD LEAKAGE REPAIR")
        print("PHASE 1 TRANSACTIONAL APPLY")
        print("=" * 72)
        print()
        print("Preflight verified.")
        print("Allowed live target:", TARGET)
        print("Explicitly unchanged: core/server.py")
        print("Persisted payload findings: 0")
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
                prefix="micr1_postflight_"
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
                    "A protected non-target, projector, or security "
                    f"log changed: {protected_changes}"
                )
            if not target_changed:
                raise ApplyError(
                    "The approved target change was not observed."
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
                receipt.update({
                    "state": "rolled_back_verified",
                    "verified": not changes,
                    "changed_files": [],
                    "live_files_modified": bool(changes),
                    "final_live_sha256": sha256(root / TARGET),
                })
                receipt["checks"]["rollback_final_state"] = {
                    "passed": not changes,
                    "protected_changes": changes,
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
            receipt.update({
                "state": "stopped_fail_closed",
                "verified": not changes and target_unchanged,
                "changed_files": [],
                "live_files_modified": bool(changes),
                "final_live_sha256": (
                    sha256(root / TARGET)
                    if (root / TARGET).is_file()
                    else None
                ),
            })
            receipt["checks"]["fail_closed_final_state"] = {
                "passed": not changes and target_unchanged,
                "protected_changes": changes,
                "target_unchanged": target_unchanged,
            }
        checkpoint(output, receipt)

    write_report(output, receipt)
    checkpoint(output, receipt)
    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("FOXAI MISSION IMAGE CONTINUITY + PAYLOAD LEAKAGE REPAIR")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Changed files:", receipt["changed_files"])
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
