
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import traceback

EXPECTED_PLAN_ID = "729af0685c9c323e186fb2d8122aff0216da4daa53ee84e3735919b23e38575a"
EXPECTED_APPROVAL_PHRASE = "APPROVE FOXAI4C 729AF0685C9C"
EXPECTED_BEFORE_SHA256 = "ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7"
EXPECTED_AFTER_SHA256 = "2ec7aff76529a9c9a477d247753227bde9f03930f1d3bd05111b3b9a2fd3be2f"
EXPECTED_DIFF_SHA256 = "281e02a280cce33a38031c4438c8e08c28abd9f1635c874fc6ae20b5b2444d5a"
TARGET_RELATIVE = Path("core") / "foxai_web.py"


def now():
    return dt.datetime.now(dt.timezone.utc)


def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_plan_hash(plan):
    core = {
        key: value
        for key, value in plan.items()
        if key not in ("plan_id", "approval_phrase")
    }
    raw = json.dumps(
        core,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_package(bundle: Path):
    manifest_path = bundle / "PACKAGE_MANIFEST.json"
    result = {"checked": 0, "failures": [], "passed": False}
    if not manifest_path.is_file():
        result["failures"].append("PACKAGE_MANIFEST.json missing")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        path = bundle / Path(relative)
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size if path.is_file() else None
        result["checked"] += 1
        if not (
            path.is_file()
            and actual_hash == expected["sha256"]
            and actual_size == expected["size_bytes"]
        ):
            result["failures"].append({
                "path": relative,
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": actual_size,
            })
    result["passed"] = not result["failures"]
    return result


def snapshot(root: Path, expected_files, shortcuts):
    files = []
    for relative, expected in sorted(expected_files.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        files.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "exists": path.is_file(),
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcut_items = []
    for name, item in shortcuts.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcut_items.append({
            "name": name,
            "path": str(path),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "exists": path.is_file(),
            "matches_expected": actual == item["sha256"],
        })

    return {
        "files": files,
        "shortcuts": shortcut_items,
        "passed": (
            all(item["matches_expected"] for item in files)
            and all(item["matches_expected"] for item in shortcut_items)
        ),
    }


def validate_plan(plan, preview_receipt, root: Path, bundle: Path):
    action = plan.get("action") or {}
    planned_root = PureWindowsPath(plan.get("foxai_root", ""))
    destination = PureWindowsPath(action.get("destination", ""))
    payload = bundle / "PAYLOAD" / TARGET_RELATIVE
    diff_path = bundle / "EXACT_PATCH.diff"

    checks = {
        "format": plan.get("format") == "foxai_phase4c_webui_comfy_patch_plan_v1",
        "plan_id_field": plan.get("plan_id") == EXPECTED_PLAN_ID,
        "plan_hash": canonical_plan_hash(plan) == EXPECTED_PLAN_ID,
        "approval_phrase": plan.get("approval_phrase") == EXPECTED_APPROVAL_PHRASE,
        "preview_state": (
            preview_receipt.get("state")
            == "patch_preview_verified_ready_for_operator_review"
        ),
        "preview_verified": preview_receipt.get("verified") is True,
        "preview_plan_id": preview_receipt.get("plan_id") == EXPECTED_PLAN_ID,
        "action_kind": action.get("kind") == "modify_existing_source",
        "before_hash": action.get("expected_before_sha256") == EXPECTED_BEFORE_SHA256,
        "after_hash": action.get("expected_after_sha256") == EXPECTED_AFTER_SHA256,
        "backup_required": action.get("backup_required_before_apply") is True,
        "one_modified_file": plan.get("existing_files_to_modify") == ["core/foxai_web.py"],
        "no_additions": not plan.get("files_to_add"),
        "no_deletions": not plan.get("files_to_delete"),
        "no_shortcut_changes": not plan.get("shortcuts_to_change"),
        "no_launcher_changes": not plan.get("launchers_to_change"),
        "payload_hash": sha256_file(payload) == EXPECTED_AFTER_SHA256,
        "payload_size": (
            payload.stat().st_size == action.get("expected_after_size_bytes")
            if payload.is_file() else False
        ),
        "diff_hash": sha256_file(diff_path) == EXPECTED_DIFF_SHA256,
        "live_before_hash": sha256_file(root / TARGET_RELATIVE) == EXPECTED_BEFORE_SHA256,
    }

    try:
        relative = destination.relative_to(planned_root)
        checks["destination_exact"] = (
            tuple(part.lower() for part in relative.parts)
            == ("core", "foxai_web.py")
        )
    except ValueError:
        checks["destination_exact"] = False

    return {"checks": checks, "passed": all(checks.values())}


def exclusive_copy(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=False)
    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def restore_from_backup(
    target: Path,
    backup: Path,
    work: Path,
    expected_live_hash: str,
):
    result = {
        "attempted": True,
        "completed": False,
        "target_hash_before_restore": sha256_file(target),
        "backup_hash": sha256_file(backup),
        "reason": None,
    }

    if result["target_hash_before_restore"] != expected_live_hash:
        result["reason"] = (
            "Rollback refused because the live target no longer matches the "
            "approved patched hash."
        )
        return result
    if result["backup_hash"] != EXPECTED_BEFORE_SHA256:
        result["reason"] = "Rollback refused because the backup hash is invalid."
        return result

    rollback_stage = work / "rollback_foxai_web.py"
    with backup.open("rb") as src, rollback_stage.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    if sha256_file(rollback_stage) != EXPECTED_BEFORE_SHA256:
        result["reason"] = "Rollback staging verification failed."
        return result

    os.replace(rollback_stage, target)
    result["target_hash_after_restore"] = sha256_file(target)
    result["completed"] = (
        result["target_hash_after_restore"] == EXPECTED_BEFORE_SHA256
    )
    if not result["completed"]:
        result["reason"] = "Rollback replacement did not restore the expected hash."
    return result


def report_text(receipt):
    lines = [
        "# FOXAI Phase 4C-A",
        "## Approved WebUI ComfyUI Patch Apply",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Plan ID: `{receipt.get('plan_id')}`",
        f"- Operator approval verified: **{receipt.get('operator_approval_verified')}**",
        f"- Live patch performed: **{receipt.get('live_patch_performed')}**",
        f"- Existing source files modified: **{receipt.get('existing_source_files_modified')}**",
        f"- Backup created: **{receipt.get('backup_created')}**",
        "- Launchers/shortcuts changed: **False**",
        "- Services launched: **False**",
        "",
    ]

    if receipt.get("state") == "patch_applied_verified":
        lines += [
            "## Applied modification",
            "",
            f"- File: `{receipt.get('target_path')}`",
            f"- Before SHA-256: `{EXPECTED_BEFORE_SHA256}`",
            f"- After SHA-256: `{receipt.get('target_sha256_after')}`",
            f"- Backup: `{receipt.get('backup_path')}`",
            "",
            "## Next gate",
            "",
            "Upload this receipt before launching the WebUI and testing its ComfyUI control.",
        ]
    else:
        lines += [
            "## Stop information",
            "",
            f"- Failure: `{(receipt.get('failure') or {}).get('message')}`",
            f"- Rollback completed: **{(receipt.get('rollback') or {}).get('completed')}**",
            f"- Net live patch remains: **{receipt.get('net_live_patch_remains')}**",
        ]

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = bundle / "APPLY_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    work = bundle / "W" / started.strftime("%Y%m%dT%H%M%SZ")
    upload.mkdir(parents=True, exist_ok=True)

    target = root / TARGET_RELATIVE
    receipt = {
        "action": "foxai_phase4c_approved_webui_comfy_patch_apply",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "plan_id": EXPECTED_PLAN_ID,
        "approval_phrase_required": EXPECTED_APPROVAL_PHRASE,
        "operator_approval_verified": False,
        "apply_capability_present": True,
        "live_patch_performed": False,
        "existing_source_files_modified": 0,
        "backup_created": False,
        "files_added_outside_backup": False,
        "files_deleted": False,
        "files_overwritten_other_than_approved_target": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "comfyui_source_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "model_loaded": False,
        "net_live_patch_remains": False,
    }
    exit_code = 1
    backup_path = None

    try:
        plan = json.loads(
            (bundle / "EXACT_APPROVED_PATCH_PLAN.json").read_text(
                encoding="utf-8"
            )
        )
        preview_receipt = json.loads(
            (bundle / "PREVIEW_RECEIPT.json").read_text(encoding="utf-8")
        )
        protected = json.loads(
            (bundle / "PROTECTED_STATE.json").read_text(encoding="utf-8")
        )
        payload = bundle / "PAYLOAD" / TARGET_RELATIVE

        package_check = verify_package(bundle)
        receipt["package_integrity"] = package_check
        if not package_check["passed"]:
            raise RuntimeError("Apply package integrity failed.")

        validation = validate_plan(
            plan, preview_receipt, root, bundle
        )
        receipt["plan_validation"] = validation
        if not validation["passed"]:
            failed = [
                name
                for name, passed in validation["checks"].items()
                if not passed
            ]
            raise RuntimeError(
                "Approved patch plan validation failed: "
                + ", ".join(failed)
            )

        ast.parse(payload.read_text(encoding="utf-8"))

        print("Exact local confirmation is required before modifying the source.")
        print("Type this phrase exactly:")
        print(EXPECTED_APPROVAL_PHRASE)
        entered = input("> ").strip()
        if entered != EXPECTED_APPROVAL_PHRASE:
            raise RuntimeError("Local operator approval phrase did not match.")
        receipt["operator_approval_verified"] = True

        before = snapshot(
            root,
            protected["before"],
            protected["shortcuts"],
        )
        receipt["integrity_before"] = before
        if not before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before patch apply.")

        work.mkdir(parents=True, exist_ok=False)
        stage = work / "foxai_web.py"
        with payload.open("rb") as src, stage.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)

        if (
            sha256_file(stage) != EXPECTED_AFTER_SHA256
            or stage.stat().st_size
            != plan["action"]["expected_after_size_bytes"]
        ):
            raise RuntimeError("Staged patch failed hash or size verification.")
        ast.parse(stage.read_text(encoding="utf-8"))

        backup_run = started.strftime("%Y%m%dT%H%M%SZ")
        backup_path = (
            root
            / "Backups"
            / "Phase4C_WebUI_Comfy"
            / backup_run
            / TARGET_RELATIVE
        )
        exclusive_copy(target, backup_path)
        if sha256_file(backup_path) != EXPECTED_BEFORE_SHA256:
            raise RuntimeError("Backup hash verification failed.")
        receipt["backup_created"] = True
        receipt["backup_path"] = str(backup_path)
        receipt["backup_sha256"] = sha256_file(backup_path)

        precommit = snapshot(
            root,
            protected["before"],
            protected["shortcuts"],
        )
        receipt["integrity_precommit"] = precommit
        if not precommit["passed"]:
            raise RuntimeError("Protected FOXAI state changed during staging.")

        os.replace(stage, target)
        receipt["live_patch_performed"] = True
        receipt["existing_source_files_modified"] = 1
        receipt["net_live_patch_remains"] = True

        target_hash = sha256_file(target)
        receipt["target_path"] = str(target)
        receipt["target_sha256_after"] = target_hash
        receipt["target_size_after"] = target.stat().st_size

        if (
            target_hash != EXPECTED_AFTER_SHA256
            or target.stat().st_size
            != plan["action"]["expected_after_size_bytes"]
        ):
            receipt["rollback"] = restore_from_backup(
                target,
                backup_path,
                work,
                EXPECTED_AFTER_SHA256,
            )
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError(
                "Live patched source failed hash or size verification."
            )

        try:
            ast.parse(target.read_text(encoding="utf-8"))
        except Exception:
            receipt["rollback"] = restore_from_backup(
                target,
                backup_path,
                work,
                EXPECTED_AFTER_SHA256,
            )
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError("Live patched source failed Python syntax validation.")

        after = snapshot(
            root,
            protected["after"],
            protected["shortcuts"],
        )
        receipt["integrity_after"] = after
        if not after["passed"]:
            receipt["rollback"] = restore_from_backup(
                target,
                backup_path,
                work,
                EXPECTED_AFTER_SHA256,
            )
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError(
                "Protected FOXAI state failed after patch apply."
            )

        receipt["state"] = "patch_applied_verified"
        receipt["verified"] = True
        receipt["net_live_patch_remains"] = True
        exit_code = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        try:
            if work.exists():
                shutil.rmtree(work)
        except Exception as cleanup_exc:
            receipt["temporary_cleanup_error"] = (
                f"{type(cleanup_exc).__name__}: {cleanup_exc}"
            )

        try:
            if (bundle / "PROTECTED_STATE.json").is_file():
                protected = json.loads(
                    (bundle / "PROTECTED_STATE.json").read_text(
                        encoding="utf-8"
                    )
                )
                expected_final = (
                    protected["after"]
                    if sha256_file(target) == EXPECTED_AFTER_SHA256
                    else protected["before"]
                )
                receipt["integrity_final"] = snapshot(
                    root,
                    expected_final,
                    protected["shortcuts"],
                )
        except Exception as final_exc:
            receipt["integrity_final_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )

        completed = now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round(
            (completed - started).total_seconds(), 2
        )

        (upload / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (upload / "report.md").write_text(
            report_text(receipt), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "Do not launch the WebUI or test ComfyUI until this receipt is reviewed.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 4C-A state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("backup_path"):
            print("Backup:", receipt["backup_path"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("The WebUI and ComfyUI were not launched. Upload the receipt first.")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
