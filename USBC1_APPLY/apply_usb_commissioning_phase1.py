from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone

APPROVAL_PHRASE = "APPROVE USB COMMISSIONING PHASE 1 APPLY"
EXPECTED_RECEIPT_SHA = "b644c7e2865a128ee27893520554918a1d58653b252de9088d6c6f114ce2a37e"
EXPECTED_LIVE = {
    "core/foxai_web.py": "e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525",
    "core/server.py": "238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81",
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "Config/application_registry.json": "6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022",
    "Config/fleet_registry.json": "18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "START_FOXAI_WEB_PORTABLE.bat": "dcd4115c1db4e11996b794fae3e40f8efc743868049c04adf93cd0a9c9157705",
    "START_FOXAI_WEB.bat": "286b586363ab9fb323dce6d8f5a7d71383144c10d87fb2137237a4996d49b498",
    "Start FoxAI.bat": "44a3631da95b0db4adc7ea12e358677fbffa591e6d45b5b8208d081b0b354c1b",
    "Start_KayocktheOS.bat": "bfa9ee6cc5ec5bf94852b55a3fe462f935d69744cfa66c52d9196351ecd18620",
    "requirements.txt": "ab55b33a0a31d51be2a81a4f51430dd0b58a9e6c85a884f600b1315b12240447",
    "USB_TREE.txt": "495df4266ca52a3b3542f4f0d15807cd2bd42cb4e7aff4a61874a3df93dc46ee",
    "System/Launchers/launch.py": "1bbb6873f11ebccc8a12ceb9c5c8dfd29087d44c25b987c106dbb606e27252a5",
    "env/python/python314._pth": "e5e2f410d50987906471dc221849354947e5d8a5781234089b133285eced37a8",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
}
EXPECTED_CANDIDATE = {
    "COMMISSION_FOXAI_USB.bat": "3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b",
    "System/Commissioning/commission_usb.py": "cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869",
    "00_START_HERE/USB_COMMISSIONING_GUIDE.md": "bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30",
}


class ApplyError(RuntimeError):
    pass


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_root(package: Path) -> Path:
    for candidate in (package.parent, *package.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
            and (candidate / "Config/FoxAI.ini").is_file()
        ):
            return candidate
    raise ApplyError(
        "FOXAI root not found. Extract USBC1_APPLY directly inside the FOXAI root."
    )


def verify_manifest(package: Path) -> list[dict]:
    manifest = package / "PACKAGE_SHA256SUMS.txt"
    if not manifest.is_file():
        raise ApplyError("Package manifest is missing.")
    results = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        results.append({"path": relative, "expected": expected, "actual": actual, "ok": actual == expected})
    if not results or not all(item["ok"] for item in results):
        raise ApplyError("Apply package identity check failed.")
    return results


def verify_preview_receipt(package: Path) -> dict:
    path = package / "grounding/LIVE_VERIFY_RECEIPT_R4.json"
    if not path.is_file() or sha256(path) != EXPECTED_RECEIPT_SHA:
        raise ApplyError("Verified R4 receipt identity failed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    boundary = ((data.get("checks") or {}).get("boundary_watch") or {})
    conditions = [
        data.get("state") == "exact_preview_verified",
        data.get("verified") is True,
        data.get("live_files_modified") is False,
        data.get("apply_capability_present") is False,
        data.get("failure") is None,
        boundary.get("passed") is True,
        boundary.get("tests") == 5,
    ]
    if not all(conditions):
        raise ApplyError("R4 receipt is not an approved exact-preview receipt.")
    return {"sha256": sha256(path), "state": data.get("state"), "boundary_watch_tests": boundary.get("tests")}


def verify_live(root: Path) -> list[dict]:
    results = []
    for relative, expected in EXPECTED_LIVE.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        results.append({"path": relative, "expected": expected, "actual": actual, "ok": actual == expected})
    if not all(item["ok"] for item in results):
        bad = [item["path"] for item in results if not item["ok"]]
        raise ApplyError("Live baseline changed; stopped fail-closed: " + ", ".join(bad))
    return results


def verify_candidate(package: Path) -> list[dict]:
    results = []
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = package / "candidate" / relative
        actual = sha256(path) if path.is_file() else None
        results.append({"path": relative, "expected": expected, "actual": actual, "ok": actual == expected})
    if not all(item["ok"] for item in results):
        raise ApplyError("Candidate identity check failed.")
    source = (package / "candidate/System/Commissioning/commission_usb.py").read_text(encoding="utf-8")
    compile(source, "commission_usb.py", "exec")
    return results


def target_state(root: Path) -> dict[str, dict]:
    state = {}
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = root / relative
        if not path.exists():
            state[relative] = {"state": "missing"}
        elif path.is_file():
            actual = sha256(path)
            state[relative] = {"state": "exact" if actual == expected else "conflict", "sha256": actual}
        else:
            state[relative] = {"state": "conflict", "kind": "not_file"}
    conflicts = [relative for relative, item in state.items() if item["state"] == "conflict"]
    if conflicts:
        raise ApplyError("Target conflict; nothing changed: " + ", ".join(conflicts))
    return state


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp.{os.getpid()}")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def prepare_receipt_dirs(root: Path, stamp: str) -> tuple[Path, Path]:
    backup = root / "Backups/SecurityMilestone" / f"USBC1_{stamp}"
    report = root / "Reports/Commissioning" / f"USBC1_{stamp}"
    if backup.exists() or report.exists():
        raise ApplyError("Receipt directory collision; retry the apply.")
    backup.mkdir(parents=True)
    report.mkdir(parents=True)
    return backup, report


def save_pre_state(root: Path, backup: Path, state: dict) -> None:
    originals = backup / "original"
    copied = []
    for relative, item in state.items():
        if item["state"] == "exact":
            source = root / relative
            destination = originals / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(relative)
    write_json_atomic(backup / "PRE_APPLY_STATE.json", {
        "created": utc_now(),
        "targets": state,
        "preexisting_exact_targets_copied": copied,
        "expected_absent_targets": [key for key, value in state.items() if value["state"] == "missing"],
    })


def transaction_apply(package: Path, root: Path, state: dict) -> list[str]:
    staged: list[tuple[Path, Path]] = []
    created: list[str] = []
    try:
        for relative, expected in EXPECTED_CANDIDATE.items():
            if state[relative]["state"] == "exact":
                continue
            source = package / "candidate" / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + f".usbc1-stage.{os.getpid()}")
            shutil.copy2(source, temp)
            if sha256(temp) != expected:
                raise ApplyError("Staged hash failed: " + relative)
            staged.append((temp, target))
        for temp, target in staged:
            os.replace(temp, target)
            created.append(target.relative_to(root).as_posix())
        return created
    except Exception:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)
        for relative in reversed(created):
            target = root / relative
            expected = EXPECTED_CANDIDATE.get(relative)
            if target.is_file() and expected and sha256(target) == expected:
                target.unlink()
        raise


def rollback_created(root: Path, created: list[str]) -> list[str]:
    removed = []
    for relative in reversed(created):
        target = root / relative
        expected = EXPECTED_CANDIDATE[relative]
        if target.is_file() and sha256(target) == expected:
            target.unlink()
            removed.append(relative)
    return removed


def verify_installed(root: Path) -> list[dict]:
    results = []
    for relative, expected in EXPECTED_CANDIDATE.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        results.append({"path": relative, "expected": expected, "actual": actual, "ok": actual == expected})
    if not all(item["ok"] for item in results):
        raise ApplyError("Installed candidate verification failed.")
    return results


def run_commissioning(root: Path) -> dict:
    python = root / "env/python/python.exe"
    script = root / "System/Commissioning/commission_usb.py"
    process = subprocess.run(
        [str(python), str(script), "--root", str(root), "--no-write", "--json", "--noninteractive"],
        cwd=str(root), capture_output=True, text=True, timeout=180,
    )
    if process.returncode not in (0, 2):
        raise ApplyError("Post-apply commissioning failed: " + process.stderr[-1800:])
    try:
        data = json.loads(process.stdout)
    except Exception as exc:
        raise ApplyError("Post-apply commissioning returned invalid JSON: " + str(exc))
    conditions = {
        "read_only_check": data.get("read_only_check") is True,
        "reports_written": data.get("reports_written") is False,
        "automatic_install": data.get("automatic_install") is False,
        "automatic_repair": data.get("automatic_repair") is False,
        "automatic_launch": data.get("automatic_launch") is False,
        "primary_launcher": data.get("primary_launcher") == "START_FOXAI_WEB_PORTABLE.bat",
        "overall_status": data.get("overall_status") in ("READY", "READY_WITH_NOTES", "NEEDS_ATTENTION"),
    }
    if not all(conditions.values()):
        raise ApplyError("Post-apply commissioning contract failed.")
    return {"passed": True, "returncode": process.returncode, "conditions": conditions, "overall_status": data.get("overall_status"), "profiles": {key: value.get("status") for key, value in (data.get("profiles") or {}).items()}}


def run_boundary_watch(root: Path) -> dict:
    python = root / "env/python/python.exe"
    test = root / "tests/test_boundary_watch.py"
    runner = (
        "import sys,unittest;"
        "root=sys.argv[1];"
        "tests=sys.argv[2];"
        "sys.path.insert(0,root);"
        "suite=unittest.defaultTestLoader.discover(start_dir=tests,pattern='test_boundary_watch.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run([str(python), "-c", runner, str(root), str(root / "tests")], cwd=str(root), capture_output=True, text=True, timeout=120)
    combined = (process.stdout or "") + "\n" + (process.stderr or "")
    passed = process.returncode == 0 and "Ran 5 tests" in combined and "\nOK" in combined
    if not passed:
        raise ApplyError("Boundary Watch failed: " + combined[-2200:])
    return {"passed": True, "tests": 5, "test_sha256": sha256(test), "returncode": process.returncode, "stderr": process.stderr}


def write_receipts(backup: Path, report: Path, receipt: dict) -> None:
    write_json_atomic(backup / "APPLY_RECEIPT.json", receipt)
    write_json_atomic(report / "APPLY_RECEIPT.json", receipt)
    lines = [
        "# FOXAI USB Commissioning Phase 1 — Apply Receipt",
        "",
        f"State: **{receipt.get('state')}**",
        f"Verified: **{receipt.get('verified')}**",
        f"Created: `{receipt.get('created')}`",
        "",
        "## Installed files",
    ]
    for item in receipt.get("installed_files") or []:
        lines.append(f"- `{item['path']}` — `{item['sha256']}`")
    lines += ["", "## Runtime verification", f"- Commissioning status: **{((receipt.get('checks') or {}).get('commissioning') or {}).get('overall_status')}**", f"- Boundary Watch: **{((receipt.get('checks') or {}).get('boundary_watch') or {}).get('tests')} tests passed**", "", "No existing FOXAI source, configuration, launcher, model, or security file was modified."]
    text = "\n".join(lines) + "\n"
    (backup / "APPLY_REPORT.md").write_text(text, encoding="utf-8")
    (report / "APPLY_REPORT.md").write_text(text, encoding="utf-8")


def main() -> int:
    package = Path(__file__).resolve().parent
    root = find_root(package)
    receipt = {
        "action": "foxai_usb_commissioning_phase1_apply",
        "created": utc_now(),
        "state": "preflight",
        "verified": False,
        "root": str(root),
        "operator_approval_required": APPROVAL_PHRASE,
        "protected_changes": [],
        "delete_operations": [],
        "checks": {},
    }
    created: list[str] = []
    backup = None
    report = None
    try:
        receipt["checks"]["package_manifest"] = verify_manifest(package)
        receipt["checks"]["preview_receipt"] = verify_preview_receipt(package)
        receipt["checks"]["live_baselines_before"] = verify_live(root)
        receipt["checks"]["candidate"] = verify_candidate(package)
        state = target_state(root)
        receipt["target_state_before"] = state

        print("\nFOXAI USB Commissioning Phase 1 — guarded apply")
        print("Proposed additions: 3")
        print("Existing files modified: 0")
        print("Deletes: 0")
        print("Automatic launch/install/repair: none")
        print("\nType the exact approval phrase to continue:")
        typed = input("> ").strip()
        if typed != APPROVAL_PHRASE:
            raise ApplyError("Approval phrase did not match. Nothing changed.")
        receipt["operator_approval_verified"] = True

        stamp = utc_stamp()
        backup, report = prepare_receipt_dirs(root, stamp)
        receipt["backup_folder"] = str(backup)
        receipt["report_folder"] = str(report)
        save_pre_state(root, backup, state)

        created = transaction_apply(package, root, state)
        receipt["created_files_this_run"] = created
        receipt["checks"]["installed_files"] = verify_installed(root)
        receipt["checks"]["live_baselines_after"] = verify_live(root)
        receipt["checks"]["commissioning"] = run_commissioning(root)
        receipt["checks"]["boundary_watch"] = run_boundary_watch(root)

        receipt["installed_files"] = [
            {"path": relative, "sha256": sha256(root / relative)}
            for relative in EXPECTED_CANDIDATE
        ]
        receipt["state"] = "applied_verified"
        receipt["verified"] = True
        receipt["live_files_modified"] = False
        receipt["new_files_added"] = list(EXPECTED_CANDIDATE)
        receipt["failure"] = None
        write_receipts(backup, report, receipt)

        print("\nState: applied_verified")
        print("Verified: True")
        print("Existing files modified: 0")
        print("New commissioning files: 3")
        print("Commissioning status:", receipt["checks"]["commissioning"]["overall_status"])
        print("Boundary Watch: 5/5 passed")
        print("Receipt:", report / "APPLY_RECEIPT.json")
        return 0
    except Exception as exc:
        removed = rollback_created(root, created) if created else []
        receipt["state"] = "stopped_fail_closed"
        receipt["verified"] = False
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        receipt["automatic_rollback"] = {"created_files_removed": removed}
        destination = (report / "APPLY_RECEIPT.json") if report else (package / "LAST_APPLY_RECEIPT.json")
        try:
            write_json_atomic(destination, receipt)
            if backup:
                write_json_atomic(backup / "APPLY_RECEIPT.json", receipt)
        except Exception:
            pass
        print("\nState: stopped_fail_closed")
        print("Verified: False")
        print("Reason:", exc)
        print("Created files rolled back:", len(removed))
        print("Existing protected files changed: 0")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
