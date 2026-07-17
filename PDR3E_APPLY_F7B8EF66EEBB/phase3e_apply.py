from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import traceback

EXPECTED_PLAN_ID = "f7b8ef66eebbd5d7e960da9a0019e828ed2b0908fa2ce4d06cd6de30a19bd808"
EXPECTED_APPROVAL_PHRASE = "APPROVE PDR3E F7B8EF66EEBB"
EXPECTED_DESTINATION_NAME = "START_FOXAI_DESKTOP_PORTABLE.bat"

def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def canonical_plan_hash(plan):
    core = {
        key: value
        for key, value in plan.items()
        if key not in ("plan_id", "approval_phrase")
    }
    encoded = json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def snapshot_protected(root: Path, preview_receipt):
    expected_baselines = {
        row["path"]: row["expected_sha256"]
        for row in preview_receipt["protected_after"]["baselines"]
    }
    expected_shortcuts = {
        key: {
            "filename": Path(item["path"]).name,
            "sha256": item["expected_sha256"],
        }
        for key, item in preview_receipt["protected_after"]["shortcuts"].items()
    }

    baselines = []
    for relative, expected in sorted(expected_baselines.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        baselines.append({
            "path": relative,
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = {}
    for key, item in expected_shortcuts.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcuts[key] = {
            "path": str(path),
            "exists": path.is_file(),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == item["sha256"],
        }

    return {
        "baselines": baselines,
        "shortcuts": shortcuts,
        "passed": (
            all(item["matches_expected"] for item in baselines)
            and all(item["matches_expected"] for item in shortcuts.values())
        ),
    }

def validate_plan(plan, preview_receipt, root: Path, bundle: Path):
    action = plan.get("action") or {}
    destination = PureWindowsPath(action.get("destination", ""))
    planned_root = PureWindowsPath(plan.get("foxai_root", ""))

    checks = {
        "format": plan.get("format") == "foxai_pdr_phase3e_launcher_plan_v1",
        "plan_id_field": plan.get("plan_id") == EXPECTED_PLAN_ID,
        "plan_hash": canonical_plan_hash(plan) == EXPECTED_PLAN_ID,
        "approval_phrase": plan.get("approval_phrase") == EXPECTED_APPROVAL_PHRASE,
        "preview_state": (
            preview_receipt.get("state")
            == "launcher_preview_verified_ready_for_operator_review"
        ),
        "preview_verified": preview_receipt.get("verified") is True,
        "preview_plan_id": preview_receipt.get("plan_id") == EXPECTED_PLAN_ID,
        "action_kind": action.get("kind") == "portable_desktop_launcher",
        "destination_status_add": action.get("destination_status") == "ADD",
        "no_existing_modifications": not plan.get("existing_files_to_modify"),
        "no_deletions": not plan.get("files_to_delete"),
        "no_shortcut_changes": not plan.get("shortcuts_to_change"),
        "no_existing_launcher_changes": not plan.get("existing_launchers_to_change"),
        "payload_exists": (
            bundle / "PAYLOAD" / EXPECTED_DESTINATION_NAME
        ).is_file(),
    }

    try:
        relative = destination.relative_to(planned_root)
        checks["destination_exact"] = (
            len(relative.parts) == 1
            and relative.name == EXPECTED_DESTINATION_NAME
        )
    except ValueError:
        checks["destination_exact"] = False

    payload = bundle / "PAYLOAD" / EXPECTED_DESTINATION_NAME
    checks["payload_hash"] = (
        sha256_file(payload) == action.get("expected_sha256")
    )
    checks["payload_size"] = (
        payload.stat().st_size == action.get("size_bytes")
        if payload.is_file() else False
    )

    actual_destination = root / EXPECTED_DESTINATION_NAME
    checks["actual_root_matches_planned_root_name"] = (
        PureWindowsPath(str(root)).name.lower() == planned_root.name.lower()
    )
    checks["destination_absent"] = not actual_destination.exists()

    return {
        "checks": checks,
        "passed": all(checks.values()),
    }

def make_report(receipt):
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3E-A",
        "## Approved Separate Launcher Apply",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Plan ID: `{receipt.get('plan_id')}`",
        f"- Operator approval verified: **{receipt.get('operator_approval_verified')}**",
        f"- New launcher added: **{receipt.get('new_launcher_added')}**",
        f"- Existing files modified: **{receipt.get('existing_files_modified')}**",
        f"- Existing files overwritten: **{receipt.get('existing_files_overwritten')}**",
        f"- Shortcut changes: **{receipt.get('shortcut_changes')}**",
        f"- FOXAI or ComfyUI launched: **False**",
        "",
    ]
    if receipt.get("state") == "launcher_applied_verified":
        lines += [
            "## Applied file",
            "",
            f"- `{receipt.get('destination')}`",
            f"- SHA-256: `{receipt.get('destination_sha256')}`",
            "",
            "## Explicit non-changes",
            "",
            "- Both USB-root shortcuts remained unchanged.",
            "- Existing launchers and FOXAI source remained unchanged.",
            "- Protected baselines remained unchanged.",
            "- The new launcher was not run.",
            "",
            "## Next gate",
            "",
            "Upload this receipt for review before running the new portable launcher.",
        ]
    else:
        lines += [
            "## Stop information",
            "",
            f"- Failure: `{(receipt.get('failure') or {}).get('message')}`",
            f"- Net live changes remain: **{receipt.get('net_live_changes')}**",
        ]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = utc_now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = bundle / "APPLY_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    work = bundle / "W" / started.strftime("%Y%m%dT%H%M%SZ")
    upload.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3e_approved_separate_launcher_apply",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "plan_id": EXPECTED_PLAN_ID,
        "approval_phrase_required": EXPECTED_APPROVAL_PHRASE,
        "operator_approval_verified": False,
        "apply_capability_present": True,
        "live_apply_performed": False,
        "new_launcher_added": False,
        "existing_files_modified": False,
        "existing_files_overwritten": False,
        "files_deleted": False,
        "shortcut_changes": False,
        "existing_launcher_changes": False,
        "source_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "launcher_run": False,
        "recursive_drive_scan": False,
        "net_live_changes": False,
    }
    exit_code = 1
    destination = root / EXPECTED_DESTINATION_NAME

    try:
        plan = json.loads(
            (bundle / "EXACT_APPROVED_LAUNCHER_PLAN.json").read_text(encoding="utf-8")
        )
        preview_receipt = json.loads(
            (bundle / "PREVIEW_RECEIPT.json").read_text(encoding="utf-8")
        )
        payload = bundle / "PAYLOAD" / EXPECTED_DESTINATION_NAME

        validation = validate_plan(plan, preview_receipt, root, bundle)
        receipt["plan_validation"] = validation
        if not validation["passed"]:
            failed = [name for name, ok in validation["checks"].items() if not ok]
            raise RuntimeError("Approved launcher plan validation failed: " + ", ".join(failed))

        print("Exact local confirmation is required before adding the launcher.")
        print("Type this phrase exactly:")
        print(EXPECTED_APPROVAL_PHRASE)
        entered = input("> ").strip()
        if entered != EXPECTED_APPROVAL_PHRASE:
            raise RuntimeError("Local operator approval phrase did not match.")
        receipt["operator_approval_verified"] = True

        protected_before = snapshot_protected(root, preview_receipt)
        receipt["protected_before"] = protected_before
        if not protected_before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before launcher apply.")

        foxai_expected = plan.get("foxai_entrypoint_sha256")
        foxai_actual = sha256_file(root / "foxai.py")
        receipt["foxai_entrypoint_before"] = {
            "expected_sha256": foxai_expected,
            "actual_sha256": foxai_actual,
            "matches_expected": foxai_actual == foxai_expected,
        }
        if foxai_actual != foxai_expected:
            raise RuntimeError("foxai.py changed after the launcher preview.")

        if destination.exists():
            raise RuntimeError("Launcher destination is no longer absent.")

        source_hash = sha256_file(payload)
        source_size = payload.stat().st_size
        action = plan["action"]
        if (
            source_hash != action["expected_sha256"]
            or source_size != action["size_bytes"]
        ):
            raise RuntimeError("Bundled launcher payload failed hash or size verification.")

        stage = work / EXPECTED_DESTINATION_NAME
        work.mkdir(parents=True, exist_ok=False)
        with payload.open("rb") as src, stage.open("xb") as dst:
            shutil.copyfileobj(src, dst)

        if (
            sha256_file(stage) != action["expected_sha256"]
            or stage.stat().st_size != action["size_bytes"]
        ):
            raise RuntimeError("Staged launcher failed verification.")

        protected_precommit = snapshot_protected(root, preview_receipt)
        receipt["protected_precommit"] = protected_precommit
        if not protected_precommit["passed"]:
            raise RuntimeError("Protected FOXAI state changed during staging.")
        if destination.exists():
            raise RuntimeError("Launcher destination appeared during staging.")

        os.rename(stage, destination)
        receipt["live_apply_performed"] = True
        receipt["new_launcher_added"] = True
        receipt["net_live_changes"] = True

        destination_hash = sha256_file(destination)
        destination_size = destination.stat().st_size
        if (
            destination_hash != action["expected_sha256"]
            or destination_size != action["size_bytes"]
        ):
            # Roll back only the file created by this run, while still hash-identical.
            if destination.is_file() and sha256_file(destination) == destination_hash:
                destination.unlink()
                receipt["new_launcher_added"] = False
                receipt["net_live_changes"] = False
            raise RuntimeError("Live launcher verification failed; add-only file rolled back.")

        protected_after = snapshot_protected(root, preview_receipt)
        receipt["protected_after"] = protected_after
        if not protected_after["passed"]:
            if destination.is_file() and sha256_file(destination) == action["expected_sha256"]:
                destination.unlink()
                receipt["new_launcher_added"] = False
                receipt["net_live_changes"] = False
            raise RuntimeError("Protected FOXAI state failed after apply; launcher rolled back.")

        foxai_after = sha256_file(root / "foxai.py")
        receipt["foxai_entrypoint_after"] = {
            "expected_sha256": foxai_expected,
            "actual_sha256": foxai_after,
            "matches_expected": foxai_after == foxai_expected,
        }
        if foxai_after != foxai_expected:
            if destination.is_file() and sha256_file(destination) == action["expected_sha256"]:
                destination.unlink()
                receipt["new_launcher_added"] = False
                receipt["net_live_changes"] = False
            raise RuntimeError("foxai.py changed during apply; launcher rolled back.")

        receipt["destination"] = str(destination)
        receipt["destination_sha256"] = destination_hash
        receipt["destination_size_bytes"] = destination_size
        receipt["state"] = "launcher_applied_verified"
        receipt["verified"] = True
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
            if (bundle / "PREVIEW_RECEIPT.json").is_file():
                preview_receipt = json.loads(
                    (bundle / "PREVIEW_RECEIPT.json").read_text(encoding="utf-8")
                )
                receipt["protected_final"] = snapshot_protected(root, preview_receipt)
        except Exception as final_exc:
            receipt["protected_final_error"] = (
                f"{type(final_exc).__name__}: {final_exc}"
            )

        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)

        (upload / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (upload / "report.md").write_text(make_report(receipt), encoding="utf-8")
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder. "
            "Do not run the new launcher until this apply receipt is reviewed.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3E-A state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        elif receipt["verified"]:
            print("The new launcher was not run. Upload the receipt first.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
