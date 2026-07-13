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
import time
import traceback
import urllib.error
import urllib.request

BASELINE_HASH = "5feb632c5d44d260dba706019beeacf2f5e210ab5a495b9ede3fbe287a6b899e"
CANDIDATE_HASH = "4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43"
SECURITY_HASH = "ea45ef5d4a201adc2cf8f337d776a81946d85febe3180e635a9cff4928bdd7e8"
URL = "http://127.0.0.1:8765/"
APPROVAL_PHRASE = "APPLY PORTABLE PYTHON FIX"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def probe_http(timeout: float = 1.0) -> dict:
    try:
        with urllib.request.urlopen(URL, timeout=timeout) as response:
            data = response.read(1_500_000).decode("utf-8", errors="replace")
            navigation_markers = {
                "command_palette_function": "openCommandPalette()" in data,
                "keyboard_shortcut": "Ctrl+K" in data,
                "navigation_shell": "navsearch" in data,
            }
            return {
                "reachable": True,
                "status": int(getattr(response, "status", 200)),
                "welcome_marker": "Welcome back, Commander." in data,
                "navigation_marker": all(navigation_markers.values()),
                "navigation_markers": navigation_markers,
                "bytes": len(data.encode("utf-8", errors="replace")),
            }
    except Exception as error:
        return {
            "reachable": False,
            "error": f"{type(error).__name__}: {error}",
        }

def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass

def atomic_copy(source: Path, target: Path) -> None:
    temporary = target.with_name(target.name + ".portable_fix_tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

bundle = Path(__file__).resolve().parents[1]
candidate_file = bundle / "candidate" / "core" / "foxai_web.py"
baseline_file = bundle / "baseline" / "core" / "foxai_web.py"
security_file = bundle / "candidate" / "core" / "security_containment.py"
test_file = bundle / "tests" / "test_phase1_security.py"

root = None
live = None
root_candidates = [bundle.parent, bundle]
detection = []
for possible_root in root_candidates:
    possible_live = possible_root / "core" / "foxai_web.py"
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
    "action": "portable_python_compatibility_apply",
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
    if root is not None:
        report_dir = root / "Reports" / "SecurityMilestone"
    else:
        report_dir = bundle / "apply_output"
    report_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = report_dir / f"PortablePythonFix_Apply_Receipt_{timestamp}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    bundle_output = bundle / "apply_output"
    bundle_output.mkdir(parents=True, exist_ok=True)
    (bundle_output / receipt_path.name).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt_path

print()
print("KAYOCKTHEOS PORTABLE PYTHON COMPATIBILITY FIX")
print("=" * 68)
print("This applies only the reviewed core\\foxai_web.py compatibility change.")
print("It will back up the live file, test the portable-Python launch,")
print("verify HTTP content, stop the temporary test server, and roll back on failure.")
print()

if root is None or live is None:
    check("foxai_root_detected", False, "No reviewed baseline/candidate hash was found.")
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Could not safely identify the FOXAI root.")
    print("Receipt:", path)
    sys.exit(1)

receipt["root"] = str(root)
receipt["live_file"] = str(live)
check("foxai_root_detected", True, str(root))

# Bundle integrity checks happen before approval or modification.
bundle_ok = True
for check_id, path, expected in [
    ("bundled_baseline_hash", baseline_file, BASELINE_HASH),
    ("bundled_candidate_hash", candidate_file, CANDIDATE_HASH),
    ("bundled_security_module_hash", security_file, SECURITY_HASH),
]:
    exists = path.exists()
    digest = sha256(path) if exists else None
    bundle_ok &= check(check_id, exists and digest == expected, digest or "missing")

if not bundle_ok:
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Bundle integrity verification failed.")
    print("Receipt:", path)
    sys.exit(1)

live_before_hash = sha256(live)
receipt["before_sha256"] = live_before_hash
if live_before_hash == CANDIDATE_HASH:
    print("The compatibility change is already present.")
    already_applied = True
elif live_before_hash == BASELINE_HASH:
    already_applied = False
else:
    check("live_hash_is_reviewed_version", False, live_before_hash)
    receipt["state"] = "blocked"
    path = write_receipt()
    print("BLOCKED: Live file does not match the reviewed baseline or candidate.")
    print("Receipt:", path)
    sys.exit(1)
check("live_hash_is_reviewed_version", True, live_before_hash)

# An existing server would make the test ambiguous. Never terminate it automatically.
pre_probe = probe_http()
receipt["pre_apply_http_probe"] = pre_probe
if pre_probe.get("reachable"):
    check("port_8765_free_before_apply", False, pre_probe)
    receipt["state"] = "blocked_existing_server"
    path = write_receipt()
    print("BLOCKED: A server is already responding at 127.0.0.1:8765.")
    print("Close the temporary working server window, then rerun this apply command.")
    print("No file was modified.")
    print("Receipt:", path)
    sys.exit(2)
check("port_8765_free_before_apply", True, pre_probe)

typed = input(f"Type exactly {APPROVAL_PHRASE} to continue: ")
if typed != APPROVAL_PHRASE:
    check("operator_approval_phrase", False, typed)
    receipt["state"] = "cancelled"
    path = write_receipt()
    print("Approval phrase did not match. No changes made.")
    print("Receipt:", path)
    sys.exit(3)
check("operator_approval_phrase", True, typed)

backup_dir = root / "Backups" / "SecurityMilestone" / f"PortablePythonFix_{timestamp}"
backup_file = backup_dir / "core" / "foxai_web.py"
backup_file.parent.mkdir(parents=True, exist_ok=False)
shutil.copy2(live, backup_file)
backup_hash = sha256(backup_file)
receipt["backup"] = str(backup_dir)
receipt["backup_sha256"] = backup_hash
if not check("backup_created_and_verified", backup_hash == live_before_hash, str(backup_file)):
    receipt["state"] = "failed_before_modification"
    path = write_receipt()
    print("FAILED: Backup could not be verified. No source change was attempted.")
    print("Receipt:", path)
    sys.exit(4)

server_proc = None
log_handle = None
modified = False

try:
    if not already_applied:
        atomic_copy(candidate_file, live)
        modified = True
        receipt["modified_files"].append("core/foxai_web.py")

    live_after_hash = sha256(live)
    receipt["after_sha256"] = live_after_hash
    if not check("candidate_installed_hash", live_after_hash == CANDIDATE_HASH, live_after_hash):
        raise RuntimeError("Installed file hash did not match the reviewed candidate.")

    compile_dir = backup_dir / "verification"
    compile_dir.mkdir(parents=True, exist_ok=True)
    py_compile.compile(
        str(live),
        cfile=str(compile_dir / "foxai_web.pyc"),
        doraise=True,
    )
    check("python_compile", True, str(compile_dir / "foxai_web.pyc"))

    regression = subprocess.run(
        [sys.executable, str(test_file)],
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=120,
    )
    regression_output = (regression.stdout or "") + (regression.stderr or "")
    receipt["security_test_output"] = regression_output
    if not check("phase1_security_tests_15", regression.returncode == 0 and "Ran 15 tests" in regression_output and "OK" in regression_output, regression.returncode):
        raise RuntimeError("Phase 1 security regression tests failed.")

    log_path = backup_dir / "verification" / "portable_launch_test.log"
    log_handle = log_path.open("wb")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    server_proc = subprocess.Popen(
        [sys.executable, "-u", str(live)],
        cwd=str(root),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    receipt["test_server_pid"] = server_proc.pid
    receipt["test_server_log"] = str(log_path)

    deadline = time.monotonic() + 35
    probe = {"reachable": False, "error": "not attempted"}
    while time.monotonic() < deadline:
        if server_proc.poll() is not None:
            probe = {
                "reachable": False,
                "error": f"server exited with code {server_proc.returncode}",
            }
            break
        probe = probe_http(timeout=1.5)
        if (
            probe.get("reachable")
            and probe.get("status") == 200
            and probe.get("welcome_marker")
            and probe.get("navigation_marker")
        ):
            break
        time.sleep(0.75)

    receipt["http_verification"] = probe
    http_ok = (
        probe.get("reachable")
        and probe.get("status") == 200
        and probe.get("welcome_marker")
        and probe.get("navigation_marker")
    )
    if not check("portable_python_http_launch", http_ok, probe):
        raise RuntimeError("Portable Python launch did not pass HTTP content verification.")

    # The launch was a verification run only. Stop it cleanly so the normal launcher can be used.
    stop_process(server_proc)
    server_proc = None
    if log_handle is not None:
        log_handle.close()
        log_handle = None

    # Confirm the temporary test server actually stopped.
    time.sleep(0.5)
    post_stop = probe_http(timeout=0.75)
    receipt["post_test_server_stop_probe"] = post_stop
    check("temporary_test_server_stopped", not post_stop.get("reachable"), post_stop)

    final_hash = sha256(live)
    receipt["final_sha256"] = final_hash
    if not check("final_live_hash", final_hash == CANDIDATE_HASH, final_hash):
        raise RuntimeError("Final live hash changed after verification.")

    receipt["state"] = "verified"
    receipt["verified"] = all(item["ok"] for item in receipt["checks"])
    path = write_receipt()

    print()
    print("PORTABLE PYTHON FIX APPLIED AND VERIFIED")
    print("Live file:", live)
    print("Backup:", backup_file)
    print("Receipt:", path)
    print("The temporary verification server was stopped.")
    print("You may now launch FOXAI normally with START_FOXAI_WEB.bat.")
    sys.exit(0 if receipt["verified"] else 5)

except Exception as error:
    receipt["failure"] = {
        "type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
    }
    stop_process(server_proc)
    if log_handle is not None:
        try:
            log_handle.close()
        except Exception:
            pass

    rollback_ok = False
    try:
        atomic_copy(backup_file, live)
        restored_hash = sha256(live)
        receipt["rollback_restored_sha256"] = restored_hash
        rollback_ok = restored_hash == live_before_hash
        check("automatic_rollback_hash", rollback_ok, restored_hash)
    except Exception as rollback_error:
        receipt["rollback_error"] = f"{type(rollback_error).__name__}: {rollback_error}"
        check("automatic_rollback_hash", False, receipt["rollback_error"])

    receipt["state"] = "rolled_back" if rollback_ok else "rollback_failed"
    receipt["verified"] = False
    path = write_receipt()

    print()
    print("APPLY FAILED.")
    print("Rollback state:", receipt["state"])
    print("Receipt:", path)
    print("Failure:", f"{type(error).__name__}: {error}")
    sys.exit(10)
