from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import sys
import traceback

EXPECTED_PLAN_ID = "7123a2a06aa7fa0451151dc0689bb2730e11b2ff7c1d6edc18fe438ab0210424"
EXPECTED_APPROVAL_PHRASE = "APPROVE PDR3D 7123A2A06AA7"
ALLOWED_KINDS = {
    "runtime",
    "desktop_package",
    "runtime_manifest",
    "diagnostic_verifier",
    "diagnostic_launcher",
}
PAYLOAD_KIND_PATHS = {
    "runtime_manifest": Path("PAYLOAD/Runtime/Desktop/DESKTOP_RUNTIME_MANIFEST.json"),
    "diagnostic_verifier": Path("PAYLOAD/System/PortableRuntime/verify_desktop_runtime.py"),
    "diagnostic_launcher": Path("PAYLOAD/START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat"),
}

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

def windows_relative(planned_path: str, planned_root: str):
    path = PureWindowsPath(planned_path)
    root = PureWindowsPath(planned_root)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"Planned path is outside the approved FOXAI root: {planned_path}"
        ) from exc
    if ".." in relative.parts or not relative.parts:
        raise RuntimeError(f"Unsafe approved relative path: {planned_path}")
    return Path(*relative.parts)

def is_ephemeral_cache(path: Path):
    lower_parts = [part.lower() for part in path.parts]
    lower_name = path.name.lower()
    return (
        "__pycache__" in lower_parts
        or lower_name.endswith(".pyc")
        or lower_name.endswith(".pyo")
    )

def allowed_destination(relative: Path, kind: str):
    parts = relative.parts
    normalized = "/".join(parts).lower()

    if is_ephemeral_cache(relative):
        return False

    if kind == "runtime":
        return len(parts) >= 4 and parts[:3] == ("Runtime", "Desktop", "python")
    if kind == "desktop_package":
        return len(parts) >= 4 and parts[:3] == (
            "Runtime", "Desktop", "site-packages"
        )
    if kind == "runtime_manifest":
        return normalized == "runtime/desktop/desktop_runtime_manifest.json"
    if kind == "diagnostic_verifier":
        return normalized == "system/portableruntime/verify_desktop_runtime.py"
    if kind == "diagnostic_launcher":
        return normalized == "start_foxai_desktop_portable_diagnostic.bat"
    return False

def source_for_action(action, plan, root: Path, bundle: Path):
    kind = action["kind"]
    if kind in PAYLOAD_KIND_PATHS:
        return bundle / PAYLOAD_KIND_PATHS[kind]

    planned_source = PureWindowsPath(action["source"])
    planned_root = PureWindowsPath(plan["foxai_root"])
    try:
        relative = planned_source.relative_to(planned_root)
    except ValueError as exc:
        raise RuntimeError(
            f"Quarantine source escaped the approved FOXAI root: {action['source']}"
        ) from exc

    expected_prefix = (
        "PDR3C_QUARANTINE",
        "Q",
        plan["phase3c_run"],
        "quarantine",
        "Runtime",
        "Desktop",
    )
    if tuple(relative.parts[:6]) != expected_prefix:
        raise RuntimeError(
            f"Unexpected quarantine source location: {action['source']}"
        )
    return root.joinpath(*relative.parts)

def snapshot_protected(root: Path, protected):
    baselines = []
    for relative, expected in sorted(protected["protected_baselines"].items()):
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
    for key, item in protected["protected_shortcuts"].items():
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

def validate_plan(plan, protected, root: Path, bundle: Path):
    checks = {}

    checks["format"] = plan.get("format") == "foxai_pdr_phase3d_exact_apply_plan_v2"
    checks["plan_id_field"] = plan.get("plan_id") == EXPECTED_PLAN_ID
    checks["plan_hash"] = canonical_plan_hash(plan) == EXPECTED_PLAN_ID
    checks["approval_phrase"] = plan.get("approval_phrase") == EXPECTED_APPROVAL_PHRASE
    checks["protected_plan_id"] = protected.get("plan_id") == EXPECTED_PLAN_ID
    checks["protected_approval_phrase"] = (
        protected.get("approval_phrase") == EXPECTED_APPROVAL_PHRASE
    )
    checks["zero_preview_conflicts"] = (
        plan.get("summary", {}).get("conflict_count") == 0
        and not plan.get("conflicts")
    )
    checks["no_existing_modifications"] = not plan.get("existing_files_to_modify")
    checks["no_deletions"] = (
        not plan.get("files_to_delete")
        and not plan.get("directories_to_remove")
    )
    checks["no_shortcut_changes"] = not plan.get("protected_shortcuts_to_change")
    checks["no_launcher_changes"] = not plan.get("existing_launchers_to_change")
    checks["all_preview_actions_add"] = all(
        action.get("destination_status") == "ADD"
        for action in plan.get("actions") or []
    )
    checks["action_count"] = (
        len(plan.get("actions") or [])
        == plan.get("summary", {}).get("planned_file_count")
        == 3520
    )

    destinations = set()
    structural_errors = []
    for index, action in enumerate(plan.get("actions") or []):
        kind = action.get("kind")
        if kind not in ALLOWED_KINDS:
            structural_errors.append(f"Action {index}: unexpected kind {kind!r}")
            continue

        try:
            relative = windows_relative(action["destination"], plan["foxai_root"])
        except Exception as exc:
            structural_errors.append(f"Action {index}: {exc}")
            continue

        if not allowed_destination(relative, kind):
            structural_errors.append(
                f"Action {index}: destination outside approved scope: {relative}"
            )

        key = os.path.normcase(str(relative))
        if key in destinations:
            structural_errors.append(f"Action {index}: duplicate destination {relative}")
        destinations.add(key)

        try:
            source = source_for_action(action, plan, root, bundle)
        except Exception as exc:
            structural_errors.append(f"Action {index}: {exc}")
            continue

        if is_ephemeral_cache(relative):
            structural_errors.append(f"Action {index}: cache file in plan {relative}")

        if action.get("size_bytes", -1) < 0:
            structural_errors.append(f"Action {index}: invalid size")

        if not isinstance(action.get("expected_sha256"), str) or len(
            action["expected_sha256"]
        ) != 64:
            structural_errors.append(f"Action {index}: invalid SHA-256")

    checks["exact_scope_structure"] = not structural_errors
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "structural_errors": structural_errors,
    }

def check_destinations_absent(plan, root: Path):
    conflicts = []
    destinations = []
    for action in plan["actions"]:
        relative = windows_relative(action["destination"], plan["foxai_root"])
        destination = root / relative
        destinations.append((action, relative, destination))
        if destination.exists():
            conflicts.append({
                "destination": str(destination),
                "is_file": destination.is_file(),
                "sha256": sha256_file(destination),
            })
    return destinations, conflicts

def verify_sources(plan, root: Path, bundle: Path):
    verified = []
    total = len(plan["actions"])
    print(f"Stage 1/5: verifying {total} exact approved source files...", flush=True)
    for index, action in enumerate(plan["actions"], start=1):
        source = source_for_action(action, plan, root, bundle)
        actual_hash = sha256_file(source)
        actual_size = source.stat().st_size if source.is_file() else None
        ok = (
            source.is_file()
            and actual_hash == action["expected_sha256"]
            and actual_size == action["size_bytes"]
        )
        record = {
            "kind": action["kind"],
            "source": str(source),
            "expected_sha256": action["expected_sha256"],
            "actual_sha256": actual_hash,
            "expected_size_bytes": action["size_bytes"],
            "actual_size_bytes": actual_size,
            "verified": ok,
        }
        verified.append(record)
        if not ok:
            raise RuntimeError(
                f"Approved source verification failed: {source}"
            )
        if index == 1 or index % 250 == 0 or index == total:
            print(f"  Source verification: {index}/{total}", flush=True)
    return verified

def copy_to_stage(plan, root: Path, bundle: Path, stage_root: Path):
    staged = []
    total = len(plan["actions"])
    print(f"Stage 2/5: staging and re-hashing {total} files...", flush=True)

    for index, action in enumerate(plan["actions"], start=1):
        relative = windows_relative(action["destination"], plan["foxai_root"])
        source = source_for_action(action, plan, root, bundle)
        staged_path = stage_root / relative
        staged_path.parent.mkdir(parents=True, exist_ok=True)

        with source.open("rb") as src, staged_path.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)

        staged_hash = sha256_file(staged_path)
        staged_size = staged_path.stat().st_size
        if (
            staged_hash != action["expected_sha256"]
            or staged_size != action["size_bytes"]
        ):
            raise RuntimeError(f"Staged file verification failed: {staged_path}")

        staged.append({
            "action": action,
            "relative": relative,
            "staged": staged_path,
            "sha256": staged_hash,
        })
        if index == 1 or index % 250 == 0 or index == total:
            print(f"  Staging: {index}/{total}", flush=True)
    return staged

def ensure_parent(root: Path, parent: Path, created_dirs: set[Path]):
    root = root.resolve()
    parent = parent.resolve()
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"Destination parent escaped FOXAI root: {parent}") from exc

    current = root
    for part in relative.parts:
        current = current / part
        if not current.exists():
            current.mkdir()
            created_dirs.add(current)
        elif not current.is_dir():
            raise RuntimeError(f"Destination parent is not a directory: {current}")

def commit_priority(item):
    kind = item["action"]["kind"]
    order = {
        "runtime": 10,
        "desktop_package": 20,
        "diagnostic_verifier": 30,
        "runtime_manifest": 40,
        "diagnostic_launcher": 50,
    }
    return (order[kind], str(item["relative"]).lower())

def rollback_created(committed, created_dirs):
    issues = []
    removed_files = 0

    for item in reversed(committed):
        destination = item["destination"]
        expected = item["sha256"]
        try:
            if not destination.exists():
                continue
            if not destination.is_file():
                issues.append(f"Rollback found non-file destination: {destination}")
                continue
            actual = sha256_file(destination)
            if actual != expected:
                issues.append(
                    f"Rollback refused changed file: {destination}; "
                    f"expected {expected}, found {actual}"
                )
                continue
            destination.unlink()
            removed_files += 1
        except Exception as exc:
            issues.append(f"Rollback file error {destination}: {type(exc).__name__}: {exc}")

    removed_dirs = 0
    for directory in sorted(
        created_dirs, key=lambda path: len(path.parts), reverse=True
    ):
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                removed_dirs += 1
        except Exception as exc:
            issues.append(f"Rollback directory error {directory}: {type(exc).__name__}: {exc}")

    return {
        "completed": not issues,
        "removed_created_files": removed_files,
        "removed_empty_created_directories": removed_dirs,
        "issues": issues,
    }

def commit_staged(staged, root: Path):
    committed = []
    created_dirs = set()
    ordered = sorted(staged, key=commit_priority)
    total = len(ordered)
    print(f"Stage 3/5: committing {total} new files add-only...", flush=True)

    try:
        for index, item in enumerate(ordered, start=1):
            destination = root / item["relative"]
            if destination.exists():
                raise FileExistsError(
                    f"Destination appeared after preflight: {destination}"
                )
            ensure_parent(root, destination.parent, created_dirs)

            # On Windows, os.rename fails rather than replacing an existing file.
            os.rename(item["staged"], destination)
            actual = sha256_file(destination)
            if actual != item["sha256"]:
                raise RuntimeError(f"Committed file hash mismatch: {destination}")

            committed.append({
                "destination": destination,
                "sha256": item["sha256"],
                "kind": item["action"]["kind"],
            })
            if index == 1 or index % 250 == 0 or index == total:
                print(f"  Commit: {index}/{total}", flush=True)
    except Exception:
        rollback = rollback_created(committed, created_dirs)
        raise ApplyCommitError(
            "Commit failed; rollback attempted.",
            rollback=rollback,
            committed_count=len(committed),
        )

    return committed, created_dirs

class ApplyCommitError(RuntimeError):
    def __init__(self, message, rollback, committed_count):
        super().__init__(message)
        self.rollback = rollback
        self.committed_count = committed_count

def verify_live_additions(plan, root: Path):
    failures = []
    checked = []
    print("Stage 4/5: verifying all live additions...", flush=True)
    for index, action in enumerate(plan["actions"], start=1):
        relative = windows_relative(action["destination"], plan["foxai_root"])
        destination = root / relative
        actual = sha256_file(destination)
        ok = (
            destination.is_file()
            and actual == action["expected_sha256"]
            and destination.stat().st_size == action["size_bytes"]
        )
        record = {
            "destination": str(destination),
            "kind": action["kind"],
            "expected_sha256": action["expected_sha256"],
            "actual_sha256": actual,
            "verified": ok,
        }
        checked.append(record)
        if not ok:
            failures.append(record)
        if index == 1 or index % 500 == 0 or index == len(plan["actions"]):
            print(f"  Live verification: {index}/{len(plan['actions'])}", flush=True)
    return {
        "checked": len(checked),
        "failed": failures,
        "passed": not failures,
    }

def make_report(receipt):
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3D-A",
        "## Approved Add-Only Runtime Apply",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Plan ID: `{receipt.get('plan_id')}`",
        f"- Operator approval verified: **{receipt.get('operator_approval_verified')}**",
        f"- Live apply performed: **{receipt.get('live_apply_performed')}**",
        f"- New live files added: **{receipt.get('new_live_files_added', 0)}**",
        f"- Existing live files modified: **{receipt.get('existing_live_files_modified')}**",
        f"- Existing files overwritten: **{receipt.get('existing_files_overwritten')}**",
        f"- Protected state passed after: **{receipt.get('protected_after', {}).get('passed')}**",
        f"- FOXAI or ComfyUI launched: **False**",
        "",
    ]

    if receipt.get("state") == "applied_verified":
        lines += [
            "## Applied scope",
            "",
            "- `Runtime\\Desktop\\python\\**`",
            "- `Runtime\\Desktop\\site-packages\\**`",
            "- `Runtime\\Desktop\\DESKTOP_RUNTIME_MANIFEST.json`",
            "- `System\\PortableRuntime\\verify_desktop_runtime.py`",
            "- `START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat`",
            "",
            "## Explicit non-changes",
            "",
            "- Both USB-root shortcuts remained unchanged.",
            "- Existing launchers and FOXAI source remained unchanged.",
            "- Runtime/Core, Config, ComfyUI, Models, and protected baselines remained unchanged.",
            "- The new diagnostic was not run.",
            "",
            "## Next gate",
            "",
            "Upload this receipt for review before running the diagnostic launcher.",
        ]
    else:
        lines += [
            "## Stop information",
            "",
            f"- Failure: `{(receipt.get('failure') or {}).get('message')}`",
            f"- Rollback completed: **{(receipt.get('rollback') or {}).get('completed')}**",
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
    stage = work / "stage"
    upload.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3d_approved_add_only_apply",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "plan_id": EXPECTED_PLAN_ID,
        "approval_phrase_required": EXPECTED_APPROVAL_PHRASE,
        "operator_approval_verified": False,
        "apply_capability_present": True,
        "live_apply_performed": False,
        "new_live_files_added": 0,
        "existing_live_files_modified": False,
        "existing_files_overwritten": False,
        "files_deleted_from_preexisting_live_state": False,
        "shortcut_changes": False,
        "existing_launcher_changes": False,
        "source_changes": False,
        "runtime_core_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "diagnostic_run": False,
        "recursive_drive_scan": False,
        "rollback_policy": (
            "On commit failure, remove only add-only files created by this run "
            "when their hashes still match the approved plan."
        ),
        "net_live_changes": False,
    }
    exit_code = 1
    committed = []
    created_dirs = set()

    try:
        plan = json.loads(
            (bundle / "EXACT_APPROVED_PLAN.json").read_text(encoding="utf-8")
        )
        protected = json.loads(
            (bundle / "PROTECTED_STATE.json").read_text(encoding="utf-8")
        )

        validation = validate_plan(plan, protected, root, bundle)
        receipt["plan_validation"] = validation
        if not validation["passed"]:
            raise RuntimeError(
                "Approved plan validation failed: "
                + ", ".join(
                    name for name, ok in validation["checks"].items() if not ok
                )
            )

        print("Exact local confirmation is required before live additions.")
        print("Type this phrase exactly:")
        print(EXPECTED_APPROVAL_PHRASE)
        entered = input("> ").strip()
        if entered != EXPECTED_APPROVAL_PHRASE:
            raise RuntimeError("Local operator approval phrase did not match.")
        receipt["operator_approval_verified"] = True

        protected_before = snapshot_protected(root, protected)
        receipt["protected_before"] = protected_before
        if not protected_before["passed"]:
            raise RuntimeError("Protected FOXAI state failed before apply.")

        destinations, conflicts = check_destinations_absent(plan, root)
        receipt["destination_preflight"] = {
            "checked": len(destinations),
            "conflict_count": len(conflicts),
            "conflicts": conflicts[:100],
        }
        if conflicts:
            raise RuntimeError(
                f"{len(conflicts)} destination conflict(s) appeared after preview."
            )

        required = plan["summary"]["required_bytes_with_margin"]
        free = shutil.disk_usage(root).free
        receipt["space_preflight"] = {
            "required_bytes_with_margin": required,
            "free_bytes": free,
            "passed": free >= required,
        }
        if free < required:
            raise RuntimeError("Insufficient free space for approved apply and margin.")

        source_verification = verify_sources(plan, root, bundle)
        receipt["approved_sources_verified"] = len(source_verification)

        stage.mkdir(parents=True, exist_ok=False)
        staged = copy_to_stage(plan, root, bundle, stage)
        receipt["staged_files_verified"] = len(staged)

        # Recheck protected state and destinations immediately before commit.
        protected_precommit = snapshot_protected(root, protected)
        receipt["protected_precommit"] = protected_precommit
        if not protected_precommit["passed"]:
            raise RuntimeError("Protected FOXAI state changed during staging.")

        _, late_conflicts = check_destinations_absent(plan, root)
        if late_conflicts:
            receipt["late_destination_conflicts"] = late_conflicts[:100]
            raise RuntimeError(
                f"{len(late_conflicts)} destination conflict(s) appeared during staging."
            )

        committed, created_dirs = commit_staged(staged, root)
        receipt["live_apply_performed"] = True
        receipt["new_live_files_added"] = len(committed)
        receipt["net_live_changes"] = True

        live_verification = verify_live_additions(plan, root)
        receipt["live_addition_verification"] = live_verification
        if not live_verification["passed"]:
            rollback = rollback_created(committed, created_dirs)
            receipt["rollback"] = rollback
            receipt["net_live_changes"] = not rollback["completed"]
            receipt["new_live_files_added"] = (
                0 if rollback["completed"] else len(committed)
            )
            raise RuntimeError(
                f"{len(live_verification['failed'])} live addition(s) failed verification."
            )

        protected_after = snapshot_protected(root, protected)
        receipt["protected_after"] = protected_after
        if not protected_after["passed"]:
            rollback = rollback_created(committed, created_dirs)
            receipt["rollback"] = rollback
            receipt["net_live_changes"] = not rollback["completed"]
            receipt["new_live_files_added"] = (
                0 if rollback["completed"] else len(committed)
            )
            raise RuntimeError("Protected FOXAI state failed after apply.")

        receipt["state"] = "applied_verified"
        receipt["verified"] = True
        receipt["net_live_changes"] = True
        exit_code = 0
        print("Stage 5/5: approved add-only apply verified.", flush=True)

    except ApplyCommitError as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "committed_before_failure": exc.committed_count,
        }
        receipt["rollback"] = exc.rollback
        receipt["net_live_changes"] = not exc.rollback["completed"]
        receipt["new_live_files_added"] = (
            0 if exc.rollback["completed"] else exc.committed_count
        )
        receipt["state"] = (
            "apply_failed_rolled_back"
            if exc.rollback["completed"]
            else "rollback_incomplete_needs_attention"
        )
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        if receipt.get("state") == "stopped_fail_closed":
            receipt["state"] = "stopped_fail_closed"
    finally:
        try:
            if work.exists():
                shutil.rmtree(work)
        except Exception as cleanup_exc:
            receipt["temporary_cleanup_error"] = (
                f"{type(cleanup_exc).__name__}: {cleanup_exc}"
            )

        try:
            protected_path = bundle / "PROTECTED_STATE.json"
            if protected_path.is_file():
                protected = json.loads(protected_path.read_text(encoding="utf-8"))
                receipt["protected_final"] = snapshot_protected(root, protected)
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
            "Do not run the new diagnostic until the apply receipt is reviewed.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3D-A state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        elif receipt["verified"]:
            print("The diagnostic was not run. Upload the apply receipt first.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
