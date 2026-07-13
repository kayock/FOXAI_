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
import tempfile
import traceback

BASELINE_HASHES = {'core/server.py': 'e0a840396045e728794a64edfeee5d1465471feb975da76dc97b44f6ce14884c', 'core/foxai_web.py': '0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda', 'ui/main_window.py': '32dae792dd84417d7f3fb131eef9d523c8b339f8fd9a86beec79803d1a22e8a1'}
CANDIDATE_HASHES = {'core/server.py': '6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505', 'core/foxai_web.py': 'bd34f97b7580310fa1a25bd031a5afcb91f8079b74167252b68db3cb7e418952', 'ui/main_window.py': 'cd537dc74e106c436d50928a57598fe666155ddcdc445c49b74a0eb5292f55eb'}
DIFF_HASH = "9af4cf49d71249d4f167898fcf57a1c1503dc9dac80a3a0219ce6cdf3f0d05f6"
APPROVAL_PHRASE = "APPLY SHARED NEURAL RUNTIME"
SCOPE = ['core/server.py', 'ui/main_window.py', 'core/foxai_web.py']
EXPLICIT_NON_CHANGES = [
    "core/security_containment.py",
    "core/director.py",
    "core/engineer_agent.py",
    "core/smart_search.py",
    "core/mission_session.py",
    "core/memory.py",
    "core/comfy_bridge.py",
    "core_v10/*",
]

def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0

def atomic_install(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=str(destination.parent),
        prefix=destination.name + ".apply.",
        suffix=".tmp",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(source.read_bytes())
    temp_path.replace(destination)

bundle = Path(__file__).resolve().parents[1]
root = bundle.parent
checks = []
modified_files = []
test_outputs = {}
backup_dir = None
before_hashes = {}
installation_started = False

def add_check(check_id: str, ok: bool, detail=None):
    item = {"id": check_id, "ok": bool(ok)}
    if detail is not None:
        item["detail"] = detail
    checks.append(item)
    if not ok:
        raise RuntimeError(f"Check failed: {check_id}")

def run_test(check_id, payload_root, test_name, marker, *args, env=None):
    command = [
        sys.executable,
        "-S",
        str(bundle / "tools" / "run_test_bootstrap.py"),
        str(payload_root),
        str(bundle / "tests" / test_name),
        *[str(arg) for arg in args],
    ]
    completed = subprocess.run(
        command,
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    test_outputs[check_id] = output
    add_check(
        check_id,
        completed.returncode == 0 and marker in output,
        {"returncode": completed.returncode, "marker": marker},
    )

def restore_backup():
    if backup_dir is None:
        return False, {"reason": "backup_not_created"}
    restored = {}
    errors = {}
    for rel in SCOPE:
        try:
            atomic_install(backup_dir / rel, root / rel)
            restored[rel] = digest(root / rel)
        except Exception as exc:
            errors[rel] = f"{type(exc).__name__}: {exc}"
    ok = not errors and restored == BASELINE_HASHES
    return ok, {"restored_hashes": restored, "errors": errors}

def write_receipt(state, verified, failure=None, rollback=None):
    reports = root / "Reports" / "SecurityMilestone"
    reports.mkdir(parents=True, exist_ok=True)
    receipt_path = reports / (
        "Shared_Neural_Runtime_Apply_Receipt_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    final_hashes = {
        rel: digest(root / rel) if (root / rel).exists() else None
        for rel in SCOPE
    }
    data = {
        "action": "shared_neural_runtime_apply",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "state": state,
        "verified": verified,
        "scope": SCOPE,
        "explicit_non_changes": EXPLICIT_NON_CHANGES,
        "checks": checks,
        "modified_files": modified_files,
        "root": str(root),
        "before_hashes": before_hashes,
        "backup": str(backup_dir) if backup_dir else None,
        "final_hashes": final_hashes,
        "shared_state_path": str(root / "Logs" / "shared_llama_runtime.json"),
        "shared_lock_path": str(root / "Logs" / "shared_llama_runtime.lock"),
        "test_outputs": test_outputs,
    }
    if failure is not None:
        data["failure"] = failure
    if rollback is not None:
        data["rollback"] = rollback
    receipt_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return receipt_path

try:
    for rel, expected in BASELINE_HASHES.items():
        live = root / rel
        add_check(f"live_file_exists_{rel}", live.exists(), str(live))
        before_hashes[rel] = digest(live)
        add_check(f"live_baseline_hash_{rel}", before_hashes[rel] == expected, before_hashes[rel])

    for rel, expected in CANDIDATE_HASHES.items():
        candidate = bundle / "candidate" / rel
        add_check(
            f"candidate_hash_{rel}",
            candidate.exists() and digest(candidate) == expected,
            digest(candidate) if candidate.exists() else None,
        )

    diff = bundle / "SHARED_NEURAL_RUNTIME_EXACT.diff"
    add_check(
        "exact_diff_hash",
        diff.exists() and digest(diff) == DIFF_HASH,
        digest(diff) if diff.exists() else None,
    )

    preview = json.loads(
        (bundle / "evidence" / "VERIFIED_PREVIEW_RECEIPT.json").read_text(encoding="utf-8")
    )
    add_check(
        "verified_preview_receipt",
        preview.get("action") == "preview_shared_neural_runtime"
        and preview.get("state") == "preview_ready"
        and preview.get("verified") is True
        and preview.get("live_files_modified") is False
        and preview.get("baseline_hashes") == BASELINE_HASHES
        and preview.get("candidate_hashes") == CANDIDATE_HASHES
        and preview.get("exact_diff_hash") == DIFF_HASH,
    )

    service_detail = {
        "webui_8765_open": port_open(8765),
        "llama_8080_open": port_open(8080),
        "runtime_lock_exists": (root / "Logs" / "shared_llama_runtime.lock").exists(),
    }
    add_check(
        "services_closed",
        not service_detail["webui_8765_open"]
        and not service_detail["llama_8080_open"]
        and not service_detail["runtime_lock_exists"],
        service_detail,
    )

    print()
    print("KAYOCKTHEOS SHARED NEURAL RUNTIME - APPLY")
    print("=" * 72)
    print("Scope:")
    for rel in SCOPE:
        print("  ~", rel)
    print()
    print("Close the Desktop UI, WebUI, and llama-server console before continuing.")
    typed = input(
        "Type the exact approval phrase to continue:\n"
        + APPROVAL_PHRASE
        + "\n> "
    ).strip()
    add_check("operator_approval_phrase", typed == APPROVAL_PHRASE, typed)

    backup_dir = (
        root
        / "Backups"
        / "SecurityMilestone"
        / ("SharedNeuralRuntime_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    )
    backup_dir.mkdir(parents=True, exist_ok=False)

    for rel in SCOPE:
        destination = backup_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, destination)
        add_check(
            f"backup_hash_{rel}",
            digest(destination) == BASELINE_HASHES[rel],
            str(destination),
        )

    shutil.copy2(diff, backup_dir / "SHARED_NEURAL_RUNTIME_EXACT.diff")
    shutil.copy2(
        bundle / "evidence" / "VERIFIED_PREVIEW_RECEIPT.json",
        backup_dir / "VERIFIED_PREVIEW_RECEIPT.json",
    )
    (backup_dir / "backup_manifest.json").write_text(
        json.dumps(
            {
                "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": SCOPE,
                "baseline_hashes": BASELINE_HASHES,
                "candidate_hashes": CANDIDATE_HASHES,
                "exact_diff_hash": DIFF_HASH,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    verification_dir = backup_dir / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)

    for rel in SCOPE:
        source = bundle / "candidate" / rel
        py_compile.compile(
            str(source),
            cfile=str(verification_dir / (rel.replace("/", "_").replace(".py", "") + "_candidate.pyc")),
            doraise=True,
        )
    add_check("candidate_compile_3", True)

    run_test("pre_shared_runtime_unit_tests_8", bundle / "payload", "test_shared_runtime.py", "Ran 8 tests")
    run_test("pre_shared_runtime_source_tests_9", bundle / "payload", "test_shared_runtime_source.py", "Ran 9 tests")
    run_test("pre_phase1_security_tests_15", bundle / "payload", "test_phase1_security.py", "Ran 15 tests")
    run_test(
        "pre_engineer_intake_tests_8",
        bundle / "payload",
        "test_engineer_intake_smartsearch.py",
        "Ran 8 tests",
        bundle / "payload" / "core" / "engineer_agent.py",
    )
    run_test("pre_mission_session_tests_6", bundle / "payload", "test_mission_session.py", "Ran 6 tests")
    run_test(
        "pre_webui_shared_mission_tests_11",
        bundle / "payload",
        "test_webui_shared_mission_static.py",
        "Ran 11 tests",
        bundle / "candidate" / "core" / "foxai_web.py",
    )

    installation_started = True
    for rel in SCOPE:
        atomic_install(bundle / "candidate" / rel, root / rel)
        modified_files.append(rel)

    for rel, expected in CANDIDATE_HASHES.items():
        add_check(f"installed_hash_{rel}", digest(root / rel) == expected, digest(root / rel))

    for rel in SCOPE:
        py_compile.compile(
            str(root / rel),
            cfile=str(verification_dir / (rel.replace("/", "_").replace(".py", "") + "_live.pyc")),
            doraise=True,
        )
    add_check("live_compile_3", True)

    live_env = os.environ.copy()
    live_env["FOXAI_LIVE_ROOT"] = str(root)

    run_test("post_live_shared_runtime_unit_tests_8", root, "test_live_shared_runtime.py", "Ran 8 tests", env=live_env)
    run_test("post_live_shared_runtime_source_tests_9", root, "test_live_shared_runtime_source.py", "Ran 9 tests", env=live_env)
    run_test("post_live_phase1_security_tests_15", root, "test_phase1_security_live.py", "Ran 15 tests", env=live_env)
    run_test(
        "post_live_engineer_intake_tests_8",
        root,
        "test_engineer_intake_smartsearch.py",
        "Ran 8 tests",
        root / "core" / "engineer_agent.py",
        env=live_env,
    )
    run_test("post_live_mission_session_tests_6", root, "test_mission_session.py", "Ran 6 tests", env=live_env)
    run_test(
        "post_live_webui_shared_mission_tests_11",
        root,
        "test_webui_shared_mission_static.py",
        "Ran 11 tests",
        root / "core" / "foxai_web.py",
        env=live_env,
    )

    final_hashes = {rel: digest(root / rel) for rel in SCOPE}
    add_check("final_live_hashes", final_hashes == {rel: CANDIDATE_HASHES[rel] for rel in SCOPE}, final_hashes)

    runtime_artifacts = {
        "state_exists": (root / "Logs" / "shared_llama_runtime.json").exists(),
        "lock_exists": (root / "Logs" / "shared_llama_runtime.lock").exists(),
        "llama_8080_open": port_open(8080),
    }
    add_check(
        "apply_did_not_launch_runtime",
        not runtime_artifacts["state_exists"]
        and not runtime_artifacts["lock_exists"]
        and not runtime_artifacts["llama_8080_open"],
        runtime_artifacts,
    )

    receipt_path = write_receipt("verified", True)
    print()
    print("APPLY VERIFIED.")
    print("State: verified")
    for rel, value in final_hashes.items():
        print(f"{rel}: {value}")
    print("Backup:", backup_dir)
    print("Receipt:", receipt_path)

except Exception as exc:
    failure = {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
    rollback_ok = False
    rollback_detail = {"reason": "installation_not_started"}

    if backup_dir is not None and installation_started:
        rollback_ok, rollback_detail = restore_backup()
        checks.append(
            {
                "id": "automatic_rollback_restored_exact_baselines",
                "ok": rollback_ok,
                "detail": rollback_detail,
            }
        )

    receipt_path = write_receipt(
        "rolled_back" if rollback_ok else "failed",
        False,
        failure=failure,
        rollback=rollback_detail,
    )
    print()
    print("APPLY FAILED.")
    print("Rollback state:", "rolled_back" if rollback_ok else "not_required_or_failed")
    print("Failure:", f"{type(exc).__name__}: {exc}")
    print("Receipt:", receipt_path)
    raise SystemExit(1)
