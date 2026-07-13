from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import traceback

BASELINE_HASH = "bf32b0ab80b6cc3a177698101a5c2121a4224d0bf55bbe78c047f541fb3a6339"
CANDIDATE_HASH = "a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a"
APPROVAL_PHRASE = "APPLY ENGINEER INTAKE REPAIR"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_copy(source: Path, target: Path) -> None:
    temporary = target.with_name(target.name + ".engineer_intake_tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

bundle = Path(__file__).resolve().parents[1]
baseline = bundle / "baseline" / "core" / "engineer_agent.py"
candidate = bundle / "candidate" / "core" / "engineer_agent.py"
targeted_test = bundle / "tests" / "test_engineer_intake_smartsearch.py"
functional_test = bundle / "tests" / "test_engineer_functional_search.py"
phase1_test = bundle / "tests" / "test_phase1_security.py"

root = None
live = None
detection = []
for possible_root in [bundle.parent, bundle]:
    possible_live = possible_root / "core" / "engineer_agent.py"
    exists = possible_live.exists()
    digest = sha256(possible_live) if exists else None
    detection.append({
        "root": str(possible_root),
        "live": str(possible_live),
        "exists": exists,
        "sha256": digest,
    })
    if exists and digest in {BASELINE_HASH, CANDIDATE_HASH}:
        root = possible_root
        live = possible_live
        break

created = datetime.now(timezone.utc)
timestamp = created.strftime("%Y%m%dT%H%M%SZ")
receipt = {
    "action": "engineer_intake_smartsearch_apply",
    "created": created.isoformat(timespec="seconds"),
    "state": "initializing",
    "verified": False,
    "modified_files": [],
    "root_detection": detection,
    "checks": [],
}

def check(check_id: str, ok: bool, detail=None) -> bool:
    receipt["checks"].append({"id": check_id, "ok": bool(ok), "detail": detail})
    return bool(ok)

def write_receipt() -> Path:
    output = bundle / "apply_output"
    output.mkdir(parents=True, exist_ok=True)
    if root is None:
        path = output / f"EngineerIntake_Apply_Receipt_{timestamp}.json"
    else:
        report_dir = root / "Reports" / "SecurityMilestone"
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / f"EngineerIntake_Apply_Receipt_{timestamp}.json"
        (output / path.name).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return path

print()
print("KAYOCKTHEOS ENGINEER INTAKE + SMARTSEARCH REPAIR")
print("=" * 70)
print("This changes only core\\engineer_agent.py.")
print("Engineer remains read-only. Repair Chamber authority is not added.")
print()

if root is None or live is None:
    check("foxai_root_detected", False, "No reviewed live Engineer file was found.")
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Could not safely detect FOXAI root.")
    print("Receipt:", path)
    raise SystemExit(1)

receipt["root"] = str(root)
receipt["live_file"] = str(live)
check("foxai_root_detected", True, str(root))

bundle_ok = True
for cid, path, expected in [
    ("bundled_baseline_hash", baseline, BASELINE_HASH),
    ("bundled_candidate_hash", candidate, CANDIDATE_HASH),
]:
    digest = sha256(path) if path.exists() else None
    bundle_ok &= check(cid, digest == expected, digest or "missing")

if not bundle_ok:
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Bundle integrity verification failed.")
    print("Receipt:", path)
    raise SystemExit(2)

live_before = sha256(live)
receipt["before_sha256"] = live_before
if live_before not in {BASELINE_HASH, CANDIDATE_HASH}:
    check("live_hash_is_reviewed_version", False, live_before)
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Live file does not match reviewed baseline or candidate.")
    print("Receipt:", path)
    raise SystemExit(3)
check("live_hash_is_reviewed_version", True, live_before)

already_applied = live_before == CANDIDATE_HASH
if already_applied:
    print("The reviewed Engineer intake repair is already present.")
else:
    typed = input(f"Type exactly {APPROVAL_PHRASE} to continue: ")
    if typed != APPROVAL_PHRASE:
        check("operator_approval_phrase", False, typed)
        receipt["state"] = "cancelled"
        path = write_receipt()
        print("Approval phrase did not match. No changes made.")
        print("Receipt:", path)
        raise SystemExit(4)
    check("operator_approval_phrase", True, typed)

backup_dir = root / "Backups" / "SecurityMilestone" / f"EngineerIntake_{timestamp}"
backup_file = backup_dir / "core" / "engineer_agent.py"
backup_file.parent.mkdir(parents=True, exist_ok=False)
shutil.copy2(live, backup_file)
backup_hash = sha256(backup_file)
receipt["backup"] = str(backup_dir)
receipt["backup_sha256"] = backup_hash

if not check("backup_created_and_verified", backup_hash == live_before, str(backup_file)):
    receipt["state"] = "failed_before_modification"
    path = write_receipt()
    print("FAILED: Backup verification failed. No source change attempted.")
    print("Receipt:", path)
    raise SystemExit(5)

try:
    if not already_applied:
        atomic_copy(candidate, live)
        receipt["modified_files"].append("core/engineer_agent.py")

    installed_hash = sha256(live)
    receipt["after_sha256"] = installed_hash
    if not check("candidate_installed_hash", installed_hash == CANDIDATE_HASH, installed_hash):
        raise RuntimeError("Installed Engineer file hash does not match reviewed candidate.")

    verification_dir = backup_dir / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    py_compile.compile(
        str(live),
        cfile=str(verification_dir / "engineer_agent.pyc"),
        doraise=True,
    )
    check("python_compile", True, str(verification_dir / "engineer_agent.pyc"))

    targeted = subprocess.run(
        [sys.executable, "-S", str(targeted_test), str(live)],
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=120,
    )
    targeted_output = (targeted.stdout or "") + (targeted.stderr or "")
    receipt["targeted_test_output"] = targeted_output
    targeted_ok = (
        targeted.returncode == 0
        and "Ran 8 tests" in targeted_output
        and "OK" in targeted_output
    )
    if not check("targeted_engineer_tests_8", targeted_ok, targeted.returncode):
        raise RuntimeError("Targeted Engineer intake tests failed.")

    phase1 = subprocess.run(
        [sys.executable, "-S", str(phase1_test)],
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=120,
    )
    phase1_output = (phase1.stdout or "") + (phase1.stderr or "")
    receipt["phase1_security_test_output"] = phase1_output
    phase1_ok = (
        phase1.returncode == 0
        and "Ran 15 tests" in phase1_output
        and "OK" in phase1_output
    )
    if not check("phase1_security_regression_tests_15", phase1_ok, phase1.returncode):
        raise RuntimeError("Phase 1 security regression tests failed.")

    functional = subprocess.run(
        [sys.executable, "-S", str(functional_test), str(root), str(live)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
    )
    functional_output = (functional.stdout or "") + (functional.stderr or "")
    receipt["functional_search_test_output"] = functional_output
    functional_ok = (
        functional.returncode == 0
        and "functional_engineer_search=PASS" in functional_output
        and "vendor_path_leak=NONE" in functional_output
    )
    if not check("live_functional_smartsearch", functional_ok, functional.returncode):
        raise RuntimeError("Live Engineer SmartSearch functional test failed.")

    final_hash = sha256(live)
    receipt["final_sha256"] = final_hash
    if not check("final_live_hash", final_hash == CANDIDATE_HASH, final_hash):
        raise RuntimeError("Final live Engineer hash changed during verification.")

    receipt["state"] = "verified"
    receipt["verified"] = all(item["ok"] for item in receipt["checks"])
    path = write_receipt()

    print()
    print("ENGINEER INTAKE REPAIR APPLIED AND VERIFIED")
    print("Live file:", live)
    print("Backup:", backup_file)
    print("Receipt:", path)
    print("Tests passed: 8 targeted + 15 Phase 1 + live SmartSearch functional test.")
    print("Restart the FOXAI desktop UI before testing /engineer commands.")
    raise SystemExit(0 if receipt["verified"] else 6)

except Exception as error:
    receipt["failure"] = {
        "type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
    }

    rollback_ok = False
    try:
        atomic_copy(backup_file, live)
        restored = sha256(live)
        receipt["rollback_restored_sha256"] = restored
        rollback_ok = restored == live_before
        check("automatic_rollback_hash", rollback_ok, restored)
    except Exception as rollback_error:
        receipt["rollback_error"] = f"{type(rollback_error).__name__}: {rollback_error}"
        check("automatic_rollback_hash", False, receipt["rollback_error"])

    receipt["state"] = "rolled_back" if rollback_ok else "rollback_failed"
    receipt["verified"] = False
    path = write_receipt()

    print()
    print("APPLY FAILED.")
    print("Rollback state:", receipt["state"])
    print("Failure:", f"{type(error).__name__}: {error}")
    print("Receipt:", path)
    raise SystemExit(10)
