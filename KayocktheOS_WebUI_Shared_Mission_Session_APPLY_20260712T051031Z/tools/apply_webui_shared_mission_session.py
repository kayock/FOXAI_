from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import py_compile
import shutil
import socket
import subprocess
import sys
import traceback

BASELINE_WEB_HASH = "4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43"
ENGINEER_HASH = "a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a"
CANDIDATE_WEB_HASH = "0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda"
CANDIDATE_SESSION_HASH = "d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a"
DIFF_HASH = "334198bc2289929cb56cd77ebc66cacdad1b40c5f9d84068f15a31a163a2a5b1"
PREVIEW_RECEIPT_HASH = "ac1c7a5fc9b34029dd5f283df76e42f791164cf7edd21bd3736e6f34c047e20c"
APPROVAL_PHRASE = "APPLY WEBUI SHARED MISSION SESSION"

def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_copy(source: Path, target: Path, suffix: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + suffix)
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(("127.0.0.1", port)) == 0

bundle = Path(__file__).resolve().parents[1]
baseline_web = bundle / "baseline" / "core" / "foxai_web.py"
baseline_engineer = bundle / "baseline" / "core" / "engineer_agent.py"
candidate_web = bundle / "candidate" / "core" / "foxai_web.py"
candidate_session = bundle / "candidate" / "core" / "mission_session.py"
exact_diff = bundle / "WEBUI_SHARED_MISSION_SESSION_EXACT.diff"
approved_preview_receipt = bundle / "APPROVED_PREVIEW_RECEIPT.json"

tests = {
    "mission_session": bundle / "tests" / "test_mission_session.py",
    "webui_static": bundle / "tests" / "test_webui_shared_mission_static.py",
    "phase1": bundle / "tests" / "test_phase1_security.py",
    "engineer_intake": bundle / "tests" / "test_engineer_intake_smartsearch.py",
    "http_smoke": bundle / "tests" / "test_webui_shared_mission_http_smoke.py",
}

root = None
live_web = None
live_engineer = None
live_session = None
root_detection = []

for possible_root in [bundle.parent, bundle]:
    web = possible_root / "core" / "foxai_web.py"
    engineer = possible_root / "core" / "engineer_agent.py"
    session = possible_root / "core" / "mission_session.py"
    web_hash = digest(web) if web.exists() else None
    engineer_hash = digest(engineer) if engineer.exists() else None
    session_hash = digest(session) if session.exists() else None
    item = {
        "root": str(possible_root),
        "web_exists": web.exists(),
        "web_sha256": web_hash,
        "engineer_exists": engineer.exists(),
        "engineer_sha256": engineer_hash,
        "mission_session_exists": session.exists(),
        "mission_session_sha256": session_hash,
    }
    root_detection.append(item)
    reviewed_web = web_hash in {BASELINE_WEB_HASH, CANDIDATE_WEB_HASH}
    reviewed_session = session_hash in {None, CANDIDATE_SESSION_HASH}
    if reviewed_web and engineer_hash == ENGINEER_HASH and reviewed_session:
        root = possible_root
        live_web = web
        live_engineer = engineer
        live_session = session
        break

created = datetime.now(timezone.utc)
timestamp = created.strftime("%Y%m%dT%H%M%SZ")
receipt = {
    "action": "webui_shared_mission_session_apply",
    "created": created.isoformat(timespec="seconds"),
    "state": "initializing",
    "verified": False,
    "scope": ["core/foxai_web.py", "core/mission_session.py"],
    "explicit_non_changes": [
        "core/memory.py",
        "ui/main_window.py",
        "core_v10/*",
        "core/director.py",
        "core/engineer_agent.py",
        "core/security_containment.py",
    ],
    "root_detection": root_detection,
    "checks": [],
    "modified_files": [],
}

def add_check(check_id: str, ok: bool, detail=None) -> bool:
    receipt["checks"].append({"id": check_id, "ok": bool(ok), "detail": detail})
    return bool(ok)

def write_receipt() -> Path:
    local_output = bundle / "apply_output"
    local_output.mkdir(parents=True, exist_ok=True)
    filename = f"WebUISharedMission_Apply_Receipt_{timestamp}.json"
    local_path = local_output / filename
    local_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if root is None:
        return local_path
    report_dir = root / "Reports" / "SecurityMilestone"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / filename
    report_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return report_path

print()
print("KAYOCKTHEOS WEBUI SHARED MISSION SESSION APPLY")
print("=" * 76)
print("Approved scope:")
print("  ~ core\\foxai_web.py")
print("  + core\\mission_session.py")
print()
print("This does not modify the desktop Mission Console or core_v10.")
print("Close the START_FOXAI_WEB console before continuing.")
print()

if root is None or live_web is None or live_engineer is None or live_session is None:
    add_check("foxai_root_and_reviewed_dependencies_detected", False, "No safe reviewed FOXAI root was found.")
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Could not safely detect the reviewed FOXAI root.")
    print("Receipt:", path)
    raise SystemExit(1)

receipt["root"] = str(root)
receipt["live_web"] = str(live_web)
receipt["live_mission_session"] = str(live_session)
add_check("foxai_root_and_reviewed_dependencies_detected", True, str(root))

bundle_integrity = True
for check_id, path, expected in [
    ("bundled_baseline_web_hash", baseline_web, BASELINE_WEB_HASH),
    ("bundled_engineer_dependency_hash", baseline_engineer, ENGINEER_HASH),
    ("bundled_candidate_web_hash", candidate_web, CANDIDATE_WEB_HASH),
    ("bundled_candidate_session_hash", candidate_session, CANDIDATE_SESSION_HASH),
    ("approved_exact_diff_hash", exact_diff, DIFF_HASH),
    ("approved_preview_receipt_hash", approved_preview_receipt, PREVIEW_RECEIPT_HASH),
]:
    actual = digest(path) if path.exists() else None
    bundle_integrity &= add_check(check_id, actual == expected, actual or "missing")

if not bundle_integrity:
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Apply-bundle integrity verification failed.")
    print("Receipt:", path)
    raise SystemExit(2)

live_web_before = digest(live_web)
live_engineer_hash = digest(live_engineer)
session_existed_before = live_session.exists()
live_session_before = digest(live_session) if session_existed_before else None
receipt["before"] = {
    "core/foxai_web.py": live_web_before,
    "core/engineer_agent.py": live_engineer_hash,
    "core/mission_session.py": live_session_before,
    "mission_session_existed": session_existed_before,
}

safe_live_state = (
    live_web_before in {BASELINE_WEB_HASH, CANDIDATE_WEB_HASH}
    and live_engineer_hash == ENGINEER_HASH
    and live_session_before in {None, CANDIDATE_SESSION_HASH}
)
if not add_check("live_state_is_reviewed", safe_live_state, receipt["before"]):
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: A live file does not match the reviewed baseline/candidate state.")
    print("Receipt:", path)
    raise SystemExit(3)

if port_open(8765):
    add_check("webui_port_closed", False, "127.0.0.1:8765 is accepting connections.")
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: The WebUI server is still running on port 8765.")
    print("Close the START_FOXAI_WEB console, then run this apply file again.")
    print("Receipt:", path)
    raise SystemExit(4)
add_check("webui_port_closed", True, "Port 8765 is not accepting connections.")

already_applied = (
    live_web_before == CANDIDATE_WEB_HASH
    and live_session_before == CANDIDATE_SESSION_HASH
)
receipt["already_applied"] = already_applied

if not already_applied:
    typed = input(f"Type exactly {APPROVAL_PHRASE} to continue: ")
    if typed != APPROVAL_PHRASE:
        add_check("operator_approval_phrase", False, typed)
        receipt["state"] = "cancelled"
        path = write_receipt()
        print("Approval phrase did not match. No live files were changed.")
        print("Receipt:", path)
        raise SystemExit(5)
    add_check("operator_approval_phrase", True, typed)
else:
    add_check("operator_approval_phrase", True, "Reviewed candidate already installed; verification-only run.")

backup_dir = root / "Backups" / "SecurityMilestone" / f"WebUISharedMission_{timestamp}"
backup_core = backup_dir / "core"
backup_core.mkdir(parents=True, exist_ok=False)
backup_web = backup_core / "foxai_web.py"
shutil.copy2(live_web, backup_web)

backup_session = backup_core / "mission_session.py"
if session_existed_before:
    shutil.copy2(live_session, backup_session)

rollback_manifest = {
    "created": created.isoformat(timespec="seconds"),
    "before_web_sha256": live_web_before,
    "mission_session_existed": session_existed_before,
    "before_mission_session_sha256": live_session_before,
    "backup_web": str(backup_web),
    "backup_mission_session": str(backup_session) if session_existed_before else None,
}
manifest_path = backup_dir / "rollback_manifest.json"
manifest_path.write_text(json.dumps(rollback_manifest, indent=2), encoding="utf-8")

backup_ok = (
    digest(backup_web) == live_web_before
    and (
        (session_existed_before and backup_session.exists() and digest(backup_session) == live_session_before)
        or (not session_existed_before and not backup_session.exists())
    )
)
receipt["backup"] = str(backup_dir)
if not add_check("backup_created_and_verified", backup_ok, rollback_manifest):
    receipt["state"] = "failed_before_modification"
    path = write_receipt()
    print("FAILED: Backup verification failed. No install was attempted.")
    print("Receipt:", path)
    raise SystemExit(6)

def restore_before_state() -> bool:
    atomic_copy(backup_web, live_web, ".webui_shared_rollback_tmp")
    if session_existed_before:
        atomic_copy(backup_session, live_session, ".webui_shared_rollback_tmp")
    elif live_session.exists():
        live_session.unlink()
    restored_web = digest(live_web)
    restored_session = digest(live_session) if live_session.exists() else None
    return (
        restored_web == live_web_before
        and restored_session == live_session_before
        and live_session.exists() == session_existed_before
    )

try:
    # Install the dependency first, then the WebUI that imports it.
    if live_session_before != CANDIDATE_SESSION_HASH:
        atomic_copy(candidate_session, live_session, ".webui_shared_install_tmp")
        receipt["modified_files"].append("core/mission_session.py")
    if live_web_before != CANDIDATE_WEB_HASH:
        atomic_copy(candidate_web, live_web, ".webui_shared_install_tmp")
        receipt["modified_files"].append("core/foxai_web.py")

    installed_web_hash = digest(live_web)
    installed_session_hash = digest(live_session)
    receipt["installed"] = {
        "core/foxai_web.py": installed_web_hash,
        "core/mission_session.py": installed_session_hash,
    }
    if not add_check("candidate_web_installed_hash", installed_web_hash == CANDIDATE_WEB_HASH, installed_web_hash):
        raise RuntimeError("Installed WebUI hash does not match the approved candidate.")
    if not add_check("candidate_session_installed_hash", installed_session_hash == CANDIDATE_SESSION_HASH, installed_session_hash):
        raise RuntimeError("Installed MissionSession hash does not match the approved candidate.")

    verification_dir = backup_dir / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    py_compile.compile(
        str(live_web),
        cfile=str(verification_dir / "foxai_web.pyc"),
        doraise=True,
    )
    py_compile.compile(
        str(live_session),
        cfile=str(verification_dir / "mission_session.pyc"),
        doraise=True,
    )
    add_check("portable_python_compile_web_and_session", True, str(verification_dir))

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(bundle / "payload")

    def run_test(name: str, command: list[str], timeout: int, marker: str) -> None:
        completed = subprocess.run(
            command,
            cwd=str(bundle),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        receipt[name + "_output"] = output
        ok = completed.returncode == 0 and marker in output
        if not add_check(name, ok, {"returncode": completed.returncode, "marker": marker}):
            raise RuntimeError(f"{name} failed.")

    run_test(
        "mission_session_functional_tests_6",
        [sys.executable, "-S", str(tests["mission_session"])],
        120,
        "Ran 6 tests",
    )
    run_test(
        "webui_routing_archive_source_tests_11",
        [sys.executable, "-S", str(tests["webui_static"]), str(live_web)],
        120,
        "Ran 11 tests",
    )
    run_test(
        "phase1_security_regression_tests_15",
        [sys.executable, "-S", str(tests["phase1"])],
        120,
        "Ran 15 tests",
    )
    run_test(
        "engineer_intake_regression_tests_8",
        [sys.executable, "-S", str(tests["engineer_intake"]), str(live_engineer)],
        120,
        "Ran 8 tests",
    )

    smoke_root = verification_dir / "http_smoke_root"
    smoke_root.mkdir(parents=True, exist_ok=True)
    smoke = subprocess.run(
        [
            sys.executable,
            "-S",
            str(tests["http_smoke"]),
            str(root),
            str(live_web),
            str(smoke_root),
        ],
        cwd=str(root),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    smoke_output = (smoke.stdout or "") + (smoke.stderr or "")
    receipt["http_smoke_output"] = smoke_output
    smoke_markers = [
        "webui_http_smoke=PASS",
        "ordinary_model_contract_route=PASS",
        "claim_guard_http_route=PASS",
        "explicit_engineer_http_route=PASS",
        "webui_engineer_write_denial=PASS",
        "stable_archive_path=PASS",
        "archive_readback=PASS",
    ]
    smoke_ok = smoke.returncode == 0 and all(marker in smoke_output for marker in smoke_markers)
    if not add_check(
        "portable_python_real_http_smoke",
        smoke_ok,
        {"returncode": smoke.returncode, "required_markers": smoke_markers},
    ):
        raise RuntimeError("Real portable-Python HTTP routing/archive smoke test failed.")

    final_web_hash = digest(live_web)
    final_session_hash = digest(live_session)
    receipt["final"] = {
        "core/foxai_web.py": final_web_hash,
        "core/mission_session.py": final_session_hash,
    }
    if not add_check("final_live_web_hash", final_web_hash == CANDIDATE_WEB_HASH, final_web_hash):
        raise RuntimeError("Final WebUI hash changed during verification.")
    if not add_check("final_live_session_hash", final_session_hash == CANDIDATE_SESSION_HASH, final_session_hash):
        raise RuntimeError("Final MissionSession hash changed during verification.")

    receipt["state"] = "verified"
    receipt["verified"] = all(item["ok"] for item in receipt["checks"])
    path = write_receipt()

    print()
    print("WEBUI SHARED MISSION SESSION APPLIED AND VERIFIED")
    print("Live WebUI:", live_web)
    print("Live mission service:", live_session)
    print("Backup:", backup_dir)
    print("Receipt:", path)
    print()
    print("Verified:")
    print("  6 MissionSession tests")
    print("  11 WebUI routing/archive source tests")
    print("  15 Phase 1 containment tests")
    print("  8 Engineer intake tests")
    print("  Real HTTP Agent Fox + claim guard + Engineer + archive read-back smoke")
    print()
    print("Restart START_FOXAI_WEB.bat before using the WebUI.")
    raise SystemExit(0 if receipt["verified"] else 7)

except Exception as error:
    receipt["failure"] = {
        "type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
    }
    rollback_ok = False
    try:
        rollback_ok = restore_before_state()
        add_check(
            "automatic_rollback_restored_exact_before_state",
            rollback_ok,
            {
                "restored_web_sha256": digest(live_web) if live_web.exists() else None,
                "restored_session_sha256": digest(live_session) if live_session.exists() else None,
                "restored_session_exists": live_session.exists(),
            },
        )
    except Exception as rollback_error:
        receipt["rollback_error"] = f"{type(rollback_error).__name__}: {rollback_error}"
        add_check("automatic_rollback_restored_exact_before_state", False, receipt["rollback_error"])

    receipt["state"] = "rolled_back" if rollback_ok else "rollback_failed"
    receipt["verified"] = False
    path = write_receipt()

    print()
    print("APPLY FAILED.")
    print("Rollback state:", receipt["state"])
    print("Failure:", f"{type(error).__name__}: {error}")
    print("Receipt:", path)
    raise SystemExit(10)
