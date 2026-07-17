
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import traceback

EXPECTED_PLAN_ID = "391f401ad6b95565f775d0f232581b0667c46dadbcd4bfa3ffc3aa5822a0b0c4"
EXPECTED_APPROVAL = "APPROVE USBC2 391F401AD6B9"
TARGETS = (
    Path("COMMISSION_FOXAI_USB.bat"),
    Path("System") / "Commissioning" / "commission_usb.py",
)
EXPECTED_BEFORE = {
    "COMMISSION_FOXAI_USB.bat": "3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b",
    "System/Commissioning/commission_usb.py": "cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869",
}
EXPECTED_AFTER = {
    "COMMISSION_FOXAI_USB.bat": "253fda6a7b57271e688063374bd6be8507671a540a42984c60a40dc9b8ce5663",
    "System/Commissioning/commission_usb.py": "39785314b4dca4e8fc51076cea97e8e7f73c2c655613d61acfa4dcdf72954654",
}
GUIDE_RELATIVE = Path("00_START_HERE") / "USB_COMMISSIONING_GUIDE.md"
GUIDE_SHA256 = "bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30"


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


def verify_manifest(bundle: Path):
    manifest_path = bundle / "PACKAGE_MANIFEST.json"
    result = {"checked": 0, "failures": [], "passed": False}
    if not manifest_path.is_file():
        result["failures"].append("PACKAGE_MANIFEST.json missing")
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        path = bundle / relative
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


def snapshot(root: Path, expected):
    items = []
    for relative, expected_hash in expected.items():
        path = root / relative
        actual = sha256_file(path)
        items.append({
            "path": relative,
            "expected_sha256": expected_hash,
            "actual_sha256": actual,
            "exists": path.is_file(),
            "matches_expected": actual == expected_hash,
        })
    return {
        "items": items,
        "passed": all(item["matches_expected"] for item in items),
    }


def verify_plan(plan, preview_receipt, bundle: Path, root: Path):
    checks = {
        "format": plan.get("format") == "foxai_usbc2_portable_path_patch_plan_v1",
        "plan_id": plan.get("plan_id") == EXPECTED_PLAN_ID,
        "plan_hash": canonical_plan_hash(plan) == EXPECTED_PLAN_ID,
        "approval_phrase": plan.get("approval_phrase") == EXPECTED_APPROVAL,
        "preview_state": (
            preview_receipt.get("state")
            == "patch_preview_verified_ready_for_operator_review"
        ),
        "preview_verified": preview_receipt.get("verified") is True,
        "preview_plan_id": preview_receipt.get("plan_id") == EXPECTED_PLAN_ID,
        "two_actions": len(plan.get("actions") or []) == 2,
        "no_additions": not plan.get("files_to_add"),
        "no_deletions": not plan.get("files_to_delete"),
        "guide_unchanged": plan.get("guide_changed") is False,
        "guide_hash": sha256_file(root / GUIDE_RELATIVE) == GUIDE_SHA256,
    }

    action_map = {
        action["relative_destination"]: action
        for action in plan.get("actions") or []
    }
    for relative in EXPECTED_BEFORE:
        action = action_map.get(relative) or {}
        payload = bundle / "PAYLOAD" / relative
        checks[f"{relative}:before"] = (
            action.get("expected_before_sha256") == EXPECTED_BEFORE[relative]
        )
        checks[f"{relative}:after"] = (
            action.get("expected_after_sha256") == EXPECTED_AFTER[relative]
        )
        checks[f"{relative}:payload"] = (
            sha256_file(payload) == EXPECTED_AFTER[relative]
        )
        checks[f"{relative}:live"] = (
            sha256_file(root / relative) == EXPECTED_BEFORE[relative]
        )

    return {"checks": checks, "passed": all(checks.values())}


def backup_file(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Backup destination already exists: {destination}")
    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def stage_payload(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Staging destination already exists: {destination}")
    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def restore_all(root: Path, backup_root: Path, expected_current):
    result = {"attempted": True, "completed": False, "items": []}
    ok = True
    for relative in reversed(tuple(EXPECTED_BEFORE)):
        live = root / relative
        backup = backup_root / relative
        item = {
            "path": relative,
            "live_before_restore": sha256_file(live),
            "backup_hash": sha256_file(backup),
            "restored": False,
            "reason": None,
        }
        if item["live_before_restore"] != expected_current[relative]:
            item["reason"] = "Live file no longer matches the approved patched hash."
            ok = False
        elif item["backup_hash"] != EXPECTED_BEFORE[relative]:
            item["reason"] = "Backup hash is invalid."
            ok = False
        else:
            stage = backup_root / "_rollback" / relative
            stage.parent.mkdir(parents=True, exist_ok=True)
            if stage.exists():
                stage.unlink()
            stage_payload(backup, stage)
            os.replace(stage, live)
            item["restored"] = (
                sha256_file(live) == EXPECTED_BEFORE[relative]
            )
            if not item["restored"]:
                item["reason"] = "Restored file hash did not match baseline."
                ok = False
        result["items"].append(item)
    result["completed"] = ok
    return result


def report_text(receipt):
    lines = [
        "# FOXAI USB C2-A",
        "## Approved Portable Path Commissioning Patch Apply",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Plan ID: `{receipt.get('plan_id')}`",
        f"- Operator approval verified: **{receipt.get('operator_approval_verified')}**",
        f"- Files modified: **{receipt.get('files_modified_count')}**",
        f"- Backups created: **{receipt.get('backups_created_count')}**",
        "- Other FOXAI files changed: **False**",
        "- Install/repair/launch/network performed: **False**",
        "",
    ]
    if receipt.get("state") == "patch_applied_verified":
        lines += [
            "## Applied files",
            "",
            "- `COMMISSION_FOXAI_USB.bat`",
            "- `System\\Commissioning\\commission_usb.py`",
            "",
            f"- Backup root: `{receipt.get('backup_root')}`",
            "",
            "Upload this receipt before rerunning commissioning.",
        ]
    else:
        lines += [
            "## Stop information",
            "",
            f"- Failure: `{(receipt.get('failure') or {}).get('message')}`",
            f"- Rollback completed: **{(receipt.get('rollback') or {}).get('completed')}**",
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
    work = bundle / "WORK" / started.strftime("%Y%m%dT%H%M%SZ")
    upload.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_usbc2_approved_portable_path_patch_apply",
        "created": started.isoformat(),
        "root": str(root),
        "state": "stopped_fail_closed",
        "verified": False,
        "plan_id": EXPECTED_PLAN_ID,
        "approval_phrase_required": EXPECTED_APPROVAL,
        "operator_approval_verified": False,
        "apply_capability_present": True,
        "live_patch_performed": False,
        "files_modified_count": 0,
        "backups_created_count": 0,
        "files_deleted": False,
        "files_added_outside_backup": False,
        "guide_changed": False,
        "other_files_modified": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "net_live_patch_remains": False,
    }
    backup_root = None
    rc = 1

    try:
        plan = json.loads(
            (bundle / "EXACT_APPROVED_PATCH_PLAN.json").read_text(encoding="utf-8")
        )
        preview_receipt = json.loads(
            (bundle / "PREVIEW_RECEIPT.json").read_text(encoding="utf-8")
        )
        protected = json.loads(
            (bundle / "PROTECTED_STATE.json").read_text(encoding="utf-8")
        )

        package = verify_manifest(bundle)
        receipt["package_integrity"] = package
        if not package["passed"]:
            raise RuntimeError("Apply package integrity failed.")

        validation = verify_plan(plan, preview_receipt, bundle, root)
        receipt["plan_validation"] = validation
        if not validation["passed"]:
            failed = [name for name, ok in validation["checks"].items() if not ok]
            raise RuntimeError("Approved plan validation failed: " + ", ".join(failed))

        print("Exact local confirmation is required before modifying commissioning files.")
        print("Type this phrase exactly:")
        print(EXPECTED_APPROVAL)
        entered = input("> ").strip()
        if entered != EXPECTED_APPROVAL:
            raise RuntimeError("Local operator approval phrase did not match.")
        receipt["operator_approval_verified"] = True

        before = snapshot(root, protected["before"])
        receipt["integrity_before"] = before
        if not before["passed"]:
            raise RuntimeError("Protected commissioning state failed before apply.")

        work.mkdir(parents=True, exist_ok=False)
        stages = {}
        for relative in EXPECTED_AFTER:
            payload = bundle / "PAYLOAD" / relative
            stage = work / relative
            stage_payload(payload, stage)
            if sha256_file(stage) != EXPECTED_AFTER[relative]:
                raise RuntimeError(f"Staged payload failed verification: {relative}")
            stages[relative] = stage

        ast.parse(
            stages["System/Commissioning/commission_usb.py"]
            .read_text(encoding="utf-8")
        )

        stamp = started.strftime("%Y%m%dT%H%M%SZ")
        backup_root = root / "Backups" / "USBC2_Commissioning" / stamp
        for relative in EXPECTED_BEFORE:
            backup_file(root / relative, backup_root / relative)
            if sha256_file(backup_root / relative) != EXPECTED_BEFORE[relative]:
                raise RuntimeError(f"Backup hash verification failed: {relative}")
            receipt["backups_created_count"] += 1

        receipt["backup_root"] = str(backup_root)

        precommit = snapshot(root, protected["before"])
        receipt["integrity_precommit"] = precommit
        if not precommit["passed"]:
            raise RuntimeError("Protected commissioning state changed during staging.")

        for relative in EXPECTED_AFTER:
            os.replace(stages[relative], root / relative)
            receipt["files_modified_count"] += 1

        receipt["live_patch_performed"] = True
        receipt["net_live_patch_remains"] = True

        after = snapshot(root, protected["after"])
        receipt["integrity_after"] = after
        if not after["passed"]:
            receipt["rollback"] = restore_all(root, backup_root, EXPECTED_AFTER)
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError("Patched commissioning files failed hash verification.")

        try:
            ast.parse(
                (root / "System" / "Commissioning" / "commission_usb.py")
                .read_text(encoding="utf-8")
            )
        except Exception:
            receipt["rollback"] = restore_all(root, backup_root, EXPECTED_AFTER)
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError("Patched commissioning Python failed syntax validation.")

        if sha256_file(root / GUIDE_RELATIVE) != GUIDE_SHA256:
            receipt["rollback"] = restore_all(root, backup_root, EXPECTED_AFTER)
            receipt["net_live_patch_remains"] = not receipt["rollback"]["completed"]
            raise RuntimeError("Commissioning guide changed unexpectedly.")

        receipt["state"] = "patch_applied_verified"
        receipt["verified"] = True
        rc = 0

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
            expected_final = (
                protected["after"]
                if all(
                    sha256_file(root / relative) == EXPECTED_AFTER[relative]
                    for relative in EXPECTED_AFTER
                )
                else protected["before"]
            )
            receipt["integrity_final"] = snapshot(root, expected_final)
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
            report_text(receipt),
            encoding="utf-8",
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "Do not rerun commissioning until this receipt has been reviewed.\n",
            encoding="utf-8",
        )

        print()
        print("USB C2-A state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("backup_root"):
            print("Backup root:", receipt["backup_root"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("Commissioning was not rerun automatically. Upload the receipt first.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
