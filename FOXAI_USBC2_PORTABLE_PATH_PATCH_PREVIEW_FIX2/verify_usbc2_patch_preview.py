
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import traceback

EXPECTED_PLAN_ID = "391f401ad6b95565f775d0f232581b0667c46dadbcd4bfa3ffc3aa5822a0b0c4"
EXPECTED_APPROVAL = "APPROVE USBC2 391F401AD6B9"
EXPECTED_LIVE = {
    "COMMISSION_FOXAI_USB.bat": "3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b",
    "System/Commissioning/commission_usb.py": "cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869",
    "00_START_HERE/USB_COMMISSIONING_GUIDE.md": "bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30",
}
EXPECTED_PROPOSED = {
    "COMMISSION_FOXAI_USB.bat": "253fda6a7b57271e688063374bd6be8507671a540a42984c60a40dc9b8ce5663",
    "System/Commissioning/commission_usb.py": "39785314b4dca4e8fc51076cea97e8e7f73c2c655613d61acfa4dcdf72954654",
}


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


def live_integrity(root: Path):
    items = []
    for relative, expected in EXPECTED_LIVE.items():
        path = root / relative
        actual = sha256_file(path)
        items.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    return {
        "items": items,
        "passed": all(item["matches_expected"] for item in items),
    }


def verify_evidence(bundle: Path):
    directory = bundle / "CAPTURE_EVIDENCE"
    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    source = json.loads(
        (directory / "source_integrity.json").read_text(encoding="utf-8")
    )
    modules = json.loads(
        (directory / "module_probe.json").read_text(encoding="utf-8")
    )

    checks = {
        "capture_state": (
            receipt.get("state")
            == "capture_verified_ready_for_exact_patch_design"
        ),
        "capture_verified": receipt.get("verified") is True,
        "capture_read_only": receipt.get("read_only_capture") is True,
        "capture_no_live_changes": receipt.get("live_files_modified") is False,
        "source_integrity": source.get("passed") is True,
        "module_probe": modules.get("passed") is True,
        "customtkinter_usb": (
            modules.get("modules", {})
            .get("customtkinter", {})
            .get("origin_expected_location")
            is True
        ),
        "pil_usb": (
            modules.get("modules", {})
            .get("PIL", {})
            .get("origin_expected_location")
            is True
        ),
        "requests_usb": (
            modules.get("modules", {})
            .get("requests", {})
            .get("origin_expected_location")
            is True
        ),
        "psutil_usb": (
            modules.get("modules", {})
            .get("psutil", {})
            .get("origin_expected_location")
            is True
        ),
    }
    return {"checks": checks, "passed": all(checks.values())}


def verify_plan(bundle: Path):
    plan = json.loads((bundle / "EXACT_PATCH_PLAN.json").read_text(encoding="utf-8"))
    checks = {
        "plan_id": plan.get("plan_id") == EXPECTED_PLAN_ID,
        "plan_hash": canonical_plan_hash(plan) == EXPECTED_PLAN_ID,
        "approval_phrase": plan.get("approval_phrase") == EXPECTED_APPROVAL,
        "two_actions": len(plan.get("actions") or []) == 2,
        "no_additions": not plan.get("files_to_add"),
        "no_deletions": not plan.get("files_to_delete"),
        "guide_unchanged": plan.get("guide_changed") is False,
    }

    proposed = bundle / "PROPOSED_FILES_NOT_APPLIED"
    proposed_items = []
    for relative, expected in EXPECTED_PROPOSED.items():
        path = proposed / relative
        actual = sha256_file(path)
        proposed_items.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    checks["proposed_hashes"] = all(
        item["matches_expected"] for item in proposed_items
    )

    python_path = (
        proposed
        / "System"
        / "Commissioning"
        / "commission_usb.py"
    )
    ast.parse(python_path.read_text(encoding="utf-8"))
    checks["proposed_python_syntax"] = True

    return {
        "checks": checks,
        "proposed_files": proposed_items,
        "passed": all(checks.values()),
        "plan": plan,
    }


def report_text(receipt, plan):
    lines = [
        "# FOXAI USB C2",
        "## Portable Path Exact Patch Preview",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Root: `{receipt.get('root')}`",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Live files modified: **False**",
        "- Install/repair/launch performed: **False**",
        "",
    ]
    if plan:
        lines += [
            "## Exact scope",
            "",
            "- `COMMISSION_FOXAI_USB.bat`",
            "- `System\\Commissioning\\commission_usb.py`",
            "",
            "The commissioning guide and every other FOXAI file remain unchanged.",
            "",
            "## Approval",
            "",
            f"- Plan ID: `{plan.get('plan_id')}`",
            f"- Exact phrase: **`{plan.get('approval_phrase')}`**",
            "",
            "**No apply capability is present.**",
        ]
    if receipt.get("failure"):
        lines += ["", f"- Failure: `{receipt['failure']['message']}`"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = bundle / "PREVIEW_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    upload = output / "UPLOAD_THIS"
    upload.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_usbc2_portable_path_exact_patch_preview",
        "created": started.isoformat(),
        "root": str(root),
        "state": "stopped_fail_closed",
        "verified": False,
        "preview_only": True,
        "apply_capability_present": False,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "writes_limited_to": str(output),
    }
    plan = None
    rc = 1

    try:
        package = verify_package(bundle)
        receipt["package_integrity"] = package
        if not package["passed"]:
            raise RuntimeError("Preview package integrity failed.")

        evidence = verify_evidence(bundle)
        receipt["capture_evidence"] = evidence
        if not evidence["passed"]:
            raise RuntimeError("Capture evidence verification failed.")

        live = live_integrity(root)
        receipt["live_integrity_before"] = live
        if not live["passed"]:
            failed = [
                item["path"] for item in live["items"]
                if not item["matches_expected"]
            ]
            raise RuntimeError(
                "Live commissioning files differ from the captured baseline: "
                + ", ".join(failed)
            )

        plan_check = verify_plan(bundle)
        receipt["plan_validation"] = {
            "checks": plan_check["checks"],
            "proposed_files": plan_check["proposed_files"],
            "passed": plan_check["passed"],
        }
        if not plan_check["passed"]:
            raise RuntimeError("Exact patch plan validation failed.")
        plan = plan_check["plan"]

        live_after = live_integrity(root)
        receipt["live_integrity_after"] = live_after
        if not live_after["passed"]:
            raise RuntimeError("Live commissioning files changed during preview.")

        receipt.update({
            "state": "patch_preview_verified_ready_for_operator_review",
            "verified": True,
            "plan_id": EXPECTED_PLAN_ID,
            "approval_phrase": EXPECTED_APPROVAL,
        })
        rc = 0

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    finally:
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
            report_text(receipt, plan),
            encoding="utf-8",
        )
        for name in (
            "EXACT_PATCH_PLAN.json",
            "EXACT_PATCH.diff",
            "README_FIRST.md",
        ):
            shutil.copy2(bundle / name, upload / name)
        proposed_output = upload / "PROPOSED_FILES_NOT_APPLIED"
        shutil.copytree(
            bundle / "PROPOSED_FILES_NOT_APPLIED",
            proposed_output,
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "No live FOXAI file was modified and no patch was applied.\n",
            encoding="utf-8",
        )

        print()
        print("USB C2 preview state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("approval_phrase"):
            print("Approval phrase:", receipt["approval_phrase"])
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No apply capability is present.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
