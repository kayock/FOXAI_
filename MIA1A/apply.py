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


APPROVAL_PHRASE = "APPROVE MISSION IMAGE ATTACHMENTS PHASE 1 APPLY"

TARGETS = {
    "core/foxai_web.py": {
        "baseline": "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb",
        "candidate": "3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d",
        "payload": "payload/foxai_web.py",
    },
    "core/server.py": {
        "baseline": "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
        "candidate": "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81",
        "payload": "payload/server.py",
    },
}

LIVE_VERIFY_RECEIPT_SHA256 = "8e9bf569561564755ca4213c87d45e42a4f887ef55351ed87967696b58045e76"
PREVIEW_RECEIPT_SHA256 = "910aaa89f53d53260947ccb29deda268dfcd19a04f8bd7265c8748e546765991"

PORTS_REQUIRED_CLOSED = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8098: "Vision benchmark",
    8099: "Other benchmark",
}

REQUIRED_LIVE_CHECKS = {
    "package_manifest",
    "exact_artifacts",
    "live_baselines",
    "vision_assets",
    "node_and_browser",
    "image_helpers",
    "model_filter",
    "profile_contract",
    "server_runtime",
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
            "size": 0,
            "mtime_ns": None,
            "sha256": None,
        }
    stat = path.stat()
    return {
        "exists": path.is_file(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256(path) if path.is_file() else None,
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
        r"FOXAI root not found. Extract the complete MIA1A folder directly inside Z:\FOXAI."
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
    module_name = "mia1a_approved_preview_verifier"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def validate_live_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/live_verify_receipt.json"
    actual_hash = sha256(path) if path.is_file() else None
    if actual_hash != LIVE_VERIFY_RECEIPT_SHA256:
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
            == ["core/foxai_web.py", "core/server.py"],
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
    }
    if not all(conditions.values()):
        raise ApplyError(
            "Approved live-verification receipt is incomplete."
        )
    return {
        "passed": True,
        "sha256": actual_hash,
        "conditions": conditions,
    }


def validate_preview_receipt(package: Path) -> dict[str, Any]:
    path = package / "approved/preview_receipt.json"
    actual_hash = sha256(path) if path.is_file() else None
    if actual_hash != PREVIEW_RECEIPT_SHA256:
        raise ApplyError("Approved preview receipt hash changed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    conditions = {
        "state": data.get("state") == "exact_preview_ready",
        "verified": data.get("verified") is True,
        "live_unmodified":
            data.get("live_files_modified") is False,
        "candidate_created":
            data.get("candidate_created") is True,
        "no_apply_capability":
            data.get("apply_capability_present") is False,
        "exact_scope":
            data.get("changed_files_proposed")
            == ["core/foxai_web.py", "core/server.py"],
        "no_deletes":
            data.get("delete_operations") == [],
    }
    if not all(conditions.values()):
        raise ApplyError("Approved preview receipt is incomplete.")
    return {
        "passed": True,
        "sha256": actual_hash,
        "conditions": conditions,
    }


def exact_payload_check(package: Path) -> dict[str, Any]:
    checks = {}
    for relative, contract in TARGETS.items():
        live_baseline = (
            package
            / (
                "approved/foxai_web.baseline.py"
                if relative.endswith("foxai_web.py")
                else "approved/server.baseline.py"
            )
        )
        diff = (
            package
            / (
                "approved/foxai_web.diff"
                if relative.endswith("foxai_web.py")
                else "approved/server.diff"
            )
        )
        payload = package / contract["payload"]
        checks[relative] = {
            "baseline_sha256":
                sha256(live_baseline) == contract["baseline"],
            "candidate_sha256":
                sha256(payload) == contract["candidate"],
            "diff_sha256":
                sha256(diff)
                == (
                    "511be5afd5d901b43adbeeb89427d3dccc534c07bdfe566119c52a5158131d9f"
                    if relative.endswith("foxai_web.py")
                    else "c75524f02cec963f950f4d23b14c19e2ba9deef91cece3e3549a2a344007eb70"
                ),
        }
        if not all(checks[relative].values()):
            raise ApplyError(
                f"Exact artifact identity failed for {relative}."
            )
    return {"passed": True, "files": checks}


def target_snapshot(root: Path) -> dict[str, Any]:
    return {
        relative: file_state(root / relative)
        for relative in TARGETS
    }


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
    package: Path,
    root: Path,
    preview_path: Path,
    label: str,
) -> dict[str, Any]:
    result = {
        "preview_manifest":
            verifier.package_manifest(preview_path),
        "exact_artifacts":
            verifier.exact_artifacts(preview_path),
        "vision_assets":
            verifier.vision_assets(root),
        "node_and_browser":
            verifier.node_checks(preview_path),
        "image_helpers":
            verifier.helper_harness(preview_path),
        "model_filter":
            verifier.model_filter_harness(preview_path),
        "profile_contract":
            verifier.profile_contract_harness(preview_path),
        "server_runtime":
            verifier.server_harness(preview_path, root),
        "static_contract":
            verifier.static_contract(preview_path),
        "boundary_watch":
            verifier.boundary_watch(root),
    }
    result["passed"] = all(
        isinstance(value, dict) and value.get("passed") is True
        for value in result.values()
        if isinstance(value, dict)
    )
    if result["passed"] is not True:
        raise ApplyError(f"{label} verification suite failed.")
    return result


def live_candidate_package(
    source_preview: Path,
    root: Path,
    temporary: Path,
) -> Path:
    target = temporary / "preview"
    shutil.copytree(source_preview, target)
    shutil.copy2(
        root / "core/foxai_web.py",
        target / "candidate/core/foxai_web.py",
    )
    shutil.copy2(
        root / "core/server.py",
        target / "candidate/core/server.py",
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
        / f"MIA1_{stamp}"
    )
    if backup_root.exists():
        raise ApplyError(
            f"Backup folder already exists: {backup_root}"
        )
    checks = {}
    for relative, contract in TARGETS.items():
        source = root / relative
        target = backup_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        actual = sha256(target)
        checks[relative] = {
            "path": str(target),
            "expected": contract["baseline"],
            "actual": actual,
            "ok": actual == contract["baseline"],
        }
    if not all(item["ok"] for item in checks.values()):
        raise ApplyError("Backup verification failed.")
    return backup_root, {
        "passed": True,
        "root": str(backup_root),
        "files": checks,
    }


def install_candidates(
    root: Path,
    package: Path,
) -> dict[str, Any]:
    staged: dict[str, Path] = {}
    replaced: list[str] = []
    try:
        for relative, contract in TARGETS.items():
            payload = package / contract["payload"]
            target = root / relative
            stage = target.with_name(
                f".{target.name}.mia1.{os.getpid()}.new"
            )
            copy_fsync(payload, stage)
            actual = sha256(stage)
            if actual != contract["candidate"]:
                raise ApplyError(
                    f"Staged candidate hash failed for {relative}."
                )
            staged[relative] = stage

        # Replace server first so projector-aware runtime exists before
        # the WebUI can request it. Both files are rolled back together
        # on any later failure.
        for relative in (
            "core/server.py",
            "core/foxai_web.py",
        ):
            os.replace(staged[relative], root / relative)
            replaced.append(relative)

        final = {}
        for relative, contract in TARGETS.items():
            actual = sha256(root / relative)
            final[relative] = {
                "expected": contract["candidate"],
                "actual": actual,
                "ok": actual == contract["candidate"],
            }
        if not all(item["ok"] for item in final.values()):
            raise ApplyError("Installed candidate hash failed.")
        return {
            "passed": True,
            "replaced": replaced,
            "files": final,
        }
    finally:
        for stage in staged.values():
            try:
                stage.unlink(missing_ok=True)
            except Exception:
                pass


def rollback_all(
    verifier,
    root: Path,
    backup: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": True,
        "succeeded": False,
        "files": {},
        "boundary_watch": None,
        "failure": None,
    }
    staged: dict[str, Path] = {}
    try:
        for relative, contract in TARGETS.items():
            backup_path = Path(
                backup["files"][relative]["path"]
            )
            target = root / relative
            stage = target.with_name(
                f".{target.name}.mia1.rollback.{os.getpid()}"
            )
            copy_fsync(backup_path, stage)
            if sha256(stage) != contract["baseline"]:
                raise ApplyError(
                    f"Rollback stage hash failed for {relative}."
                )
            staged[relative] = stage

        for relative in (
            "core/server.py",
            "core/foxai_web.py",
        ):
            os.replace(staged[relative], root / relative)

        for relative, contract in TARGETS.items():
            actual = sha256(root / relative)
            result["files"][relative] = {
                "expected": contract["baseline"],
                "actual": actual,
                "ok": actual == contract["baseline"],
            }
            compile(
                (root / relative).read_text(encoding="utf-8"),
                str(root / relative),
                "exec",
            )
        if not all(item["ok"] for item in result["files"].values()):
            raise ApplyError("Rollback final hash failed.")

        result["boundary_watch"] = verifier.boundary_watch(root)
        result["succeeded"] = True
    except Exception as exc:
        result["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        for stage in staged.values():
            try:
                stage.unlink(missing_ok=True)
            except Exception:
                pass
    return result


def checkpoint(
    output: Path,
    receipt: dict[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stage = output / "receipt.json.tmp"
    stage.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    os.replace(stage, output / "receipt.json")


def write_report(
    output: Path,
    receipt: dict[str, Any],
) -> None:
    lines = [
        "# FOXAI Mission Image Attachments Phase 1",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Operator approved: **{receipt['operator_approved']}**",
        f"- Changed files: **{receipt['changed_files']}**",
        f"- Delete operations: **{receipt['delete_operations']}**",
        f"- Rollback performed: **{receipt['rollback_performed']}**",
        f"- Failure: **{receipt.get('failure')}**",
        "",
        "Allowed live scope:",
        "",
        "- `core/foxai_web.py`",
        "- `core/server.py`",
        "",
        "Nothing is installed unless the receipt says",
        "`State: applied_verified` and `Verified: True`.",
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
    verifier = load_verifier(package)
    preview = package / "approved_preview"

    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package / f"MIA1_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    before = protected_snapshot(verifier, root)
    original_targets = target_snapshot(root)
    candidate_install_started = False
    backup = None

    receipt: dict[str, Any] = {
        "action":
            "mission_image_attachments_phase1_transactional_apply",
        "created": created.isoformat(),
        "root": str(root),
        "state": "running",
        "verified": False,
        "operator_approved": False,
        "approval_phrase_required": APPROVAL_PHRASE,
        "allowed_targets": list(TARGETS.keys()),
        "changed_files": [],
        "delete_operations": [],
        "rollback_performed": False,
        "rollback": None,
        "live_files_modified": False,
        "backup": None,
        "final_hashes": {
            relative: state["sha256"]
            for relative, state in original_targets.items()
        },
        "checks": {},
        "failure": None,
    }
    checkpoint(output, receipt)

    try:
        receipt["checks"]["package_manifest"] = (
            package_manifest(package)
        )
        receipt["checks"]["approved_preview_manifest"] = (
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
        receipt["checks"]["vision_assets"] = (
            verifier.vision_assets(root)
        )
        receipt["checks"]["candidate_preflight"] = (
            verification_suite(
                verifier,
                package,
                root,
                preview,
                "candidate preflight",
            )
        )
        checkpoint(output, receipt)

        print()
        print("=" * 72)
        print("FOXAI MISSION IMAGE ATTACHMENTS — PHASE 1")
        print("TRANSACTIONAL APPLY")
        print("=" * 72)
        print()
        print("Preflight verified.")
        print("Allowed live targets:")
        print("  core/foxai_web.py")
        print("  core/server.py")
        print("Delete operations: none")
        print("Verified two-file backup and rollback are mandatory.")
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
                "live_files_modified": False,
                "changed_files": [],
                "final_hashes": {
                    relative: sha256(root / relative)
                    for relative in TARGETS
                },
            })
            checkpoint(output, receipt)
        else:
            receipt["operator_approved"] = True
            _, backup = create_backup(root, stamp)
            receipt["backup"] = backup
            checkpoint(output, receipt)

            candidate_install_started = True
            receipt["checks"]["installation"] = (
                install_candidates(root, package)
            )
            receipt["changed_files"] = list(TARGETS.keys())
            receipt["live_files_modified"] = True
            receipt["final_hashes"] = {
                relative: sha256(root / relative)
                for relative in TARGETS
            }
            checkpoint(output, receipt)

            with tempfile.TemporaryDirectory(
                prefix="mia1_postflight_"
            ) as temporary:
                live_preview = live_candidate_package(
                    preview,
                    root,
                    Path(temporary),
                )
                receipt["checks"]["postflight"] = (
                    verification_suite(
                        verifier,
                        package,
                        root,
                        live_preview,
                        "live postflight",
                    )
                )

            after = protected_snapshot(verifier, root)
            changes = changed_paths(before, after)
            protected_changes = [
                path for path in changes
                if path not in TARGETS
            ]
            expected_target_changes = sorted(
                path for path in changes
                if path in TARGETS
            )
            receipt["checks"]["protected_immutability"] = {
                "passed": not protected_changes,
                "protected_changes": protected_changes,
                "target_changes": expected_target_changes,
            }
            if protected_changes:
                raise ApplyError(
                    "A protected non-target, projector, or security "
                    f"log changed: {protected_changes}"
                )
            if expected_target_changes != sorted(TARGETS):
                raise ApplyError(
                    "The exact two-file target change set was not observed."
                )

            final_hashes = {
                relative: sha256(root / relative)
                for relative in TARGETS
            }
            if any(
                final_hashes[relative]
                != TARGETS[relative]["candidate"]
                for relative in TARGETS
            ):
                raise ApplyError("Final candidate hash verification failed.")

            receipt.update({
                "state": "applied_verified",
                "verified": True,
                "operator_approved": True,
                "changed_files": list(TARGETS.keys()),
                "delete_operations": [],
                "rollback_performed": False,
                "live_files_modified": True,
                "final_hashes": final_hashes,
            })
            checkpoint(output, receipt)

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if candidate_install_started and backup is not None:
            rollback_result = rollback_all(
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
                    "final_hashes": {
                        relative: sha256(root / relative)
                        for relative in TARGETS
                    },
                })
                receipt["checks"]["rollback_final_state"] = {
                    "passed": not changes,
                    "protected_changes": changes,
                }
            else:
                receipt.update({
                    "state": "rollback_failed",
                    "verified": False,
                    "final_hashes": {
                        relative: (
                            sha256(root / relative)
                            if (root / relative).is_file()
                            else None
                        )
                        for relative in TARGETS
                    },
                })
        else:
            after = protected_snapshot(verifier, root)
            changes = changed_paths(before, after)
            targets_unchanged = (
                target_snapshot(root) == original_targets
            )
            receipt.update({
                "state": "stopped_fail_closed",
                "verified": not changes and targets_unchanged,
                "changed_files": [],
                "live_files_modified": bool(changes),
                "final_hashes": {
                    relative: (
                        sha256(root / relative)
                        if (root / relative).is_file()
                        else None
                    )
                    for relative in TARGETS
                },
            })
            receipt["checks"]["fail_closed_final_state"] = {
                "passed": not changes and targets_unchanged,
                "protected_changes": changes,
                "targets_unchanged": targets_unchanged,
            }
        checkpoint(output, receipt)

    write_report(output, receipt)
    checkpoint(output, receipt)
    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("FOXAI MISSION IMAGE ATTACHMENTS — PHASE 1")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Operator approved:", receipt["operator_approved"])
    print("Changed files:", receipt["changed_files"])
    print("Delete operations:", receipt["delete_operations"])
    print("Rollback performed:", receipt["rollback_performed"])
    print("Final hashes:", receipt["final_hashes"])
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
