from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import py_compile
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback

BASELINE_HASH = "be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c"
CANDIDATE_HASH = "f9b6d67557d0038725c8b05f293f303e639c95f57c73df260ea012d6e44c4efd"
DIFF_HASH = "ca5aa9c1edb1805760862de3ec1a47bb47f41ae82fd47541e3f4d80166f015c6"
APPROVAL_PHRASE = "APPLY SMARTSEARCH ROOT STAGING CLEANUP"


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


bundle = Path(__file__).resolve().parents[1]
root = bundle.parent

live = root / "core" / "smart_search.py"
candidate = bundle / "candidate" / "core" / "smart_search.py"
exact_diff = bundle / "SMARTSEARCH_ROOT_STAGING_CLEANUP_EXACT.diff"
preview_receipt = bundle / "evidence" / "VERIFIED_PREVIEW_RECEIPT.json"

checks = []
modified_files = []
backup_dir = None
before_hash = None

def add_check(check_id: str, ok: bool, detail=None):
    item = {"id": check_id, "ok": bool(ok)}
    if detail is not None:
        item["detail"] = detail
    checks.append(item)
    if not ok:
        raise RuntimeError(f"Check failed: {check_id}")

def write_receipt(state: str, verified: bool, failure=None):
    reports = root / "Reports" / "SecurityMilestone"
    reports.mkdir(parents=True, exist_ok=True)
    receipt_path = reports / (
        "SmartSearch_Root_Staging_Cleanup_Apply_Receipt_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )

    data = {
        "action": "smartsearch_root_staging_cleanup_apply",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "state": state,
        "verified": verified,
        "scope": ["core/smart_search.py"],
        "explicit_non_changes": [
            "core/engineer_agent.py",
            "core/security_containment.py",
            "core/director.py",
            "core/foxai_web.py",
            "core/mission_session.py",
            "ui/main_window.py",
            "core_v10/*",
        ],
        "checks": checks,
        "modified_files": modified_files,
        "root": str(root),
        "live_file": str(live),
        "before_sha256": before_hash,
        "backup": str(backup_dir) if backup_dir else None,
        "final_sha256": digest(live) if live.exists() else None,
    }
    if failure is not None:
        data["failure"] = failure

    receipt_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return receipt_path

try:
    add_check("foxai_root_detected", live.exists(), str(root))

    before_hash = digest(live)
    add_check("live_baseline_hash", before_hash == BASELINE_HASH, before_hash)
    add_check("candidate_hash", digest(candidate) == CANDIDATE_HASH, digest(candidate))
    add_check("exact_diff_hash", digest(exact_diff) == DIFF_HASH, digest(exact_diff))

    preview = json.loads(preview_receipt.read_text(encoding="utf-8"))
    preview_checks = {
        item.get("id"): item.get("ok")
        for item in preview.get("checks", [])
    }
    add_check(
        "verified_preview_receipt",
        preview.get("action") == "preview_smartsearch_root_staging_cleanup"
        and preview.get("state") == "preview_ready"
        and preview.get("verified") is True
        and preview.get("live_files_modified") is False
        and preview.get("baseline_hash") == BASELINE_HASH
        and preview.get("candidate_hash") == CANDIDATE_HASH
        and preview.get("exact_diff_hash") == DIFF_HASH
        and preview_checks.get("targeted_root_staging_tests_8") is True
        and preview_checks.get("phase1_security_regression_tests_15") is True,
    )

    web_open = port_open(8765)
    engine_open = port_open(8080)
    add_check(
        "service_ports_closed",
        not web_open and not engine_open,
        {
            "webui_8765_open": web_open,
            "chat_engine_8080_open": engine_open,
        },
    )

    print()
    print("KAYOCKTHEOS SMARTSEARCH ROOT STAGING CLEANUP - APPLY")
    print("=" * 72)
    print("Scope: core\\smart_search.py only")
    print("Candidate SHA-256:", CANDIDATE_HASH)
    print()
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
        / (
            "SmartSearchRootStagingCleanup_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
    )
    backup_file = backup_dir / "core" / "smart_search.py"
    backup_file.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(live, backup_file)

    add_check(
        "backup_created_and_verified",
        digest(backup_file) == BASELINE_HASH,
        str(backup_file),
    )

    verification_dir = backup_dir / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)

    py_compile.compile(
        str(candidate),
        cfile=str(verification_dir / "candidate_smart_search.pyc"),
        doraise=True,
    )
    add_check("candidate_compile", True)

    def run_test(test_name: str, marker: str):
        completed = subprocess.run(
            [
                sys.executable,
                "-S",
                str(bundle / "tools" / "run_test_bootstrap.py"),
                str(bundle / "payload"),
                str(bundle / "tests" / test_name),
            ],
            cwd=str(bundle),
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        (verification_dir / f"{test_name}.txt").write_text(
            output,
            encoding="utf-8",
        )
        return completed.returncode, marker in output

    rc, marker_ok = run_test(
        "test_smart_search_root_staging_cleanup.py",
        "Ran 8 tests",
    )
    add_check(
        "targeted_root_staging_tests_8",
        rc == 0 and marker_ok,
        {"returncode": rc, "marker": "Ran 8 tests"},
    )

    rc, marker_ok = run_test(
        "test_phase1_security.py",
        "Ran 15 tests",
    )
    add_check(
        "phase1_security_regression_tests_15",
        rc == 0 and marker_ok,
        {"returncode": rc, "marker": "Ran 15 tests"},
    )

    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=str(live.parent),
        prefix="smart_search.apply.",
        suffix=".tmp",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(candidate.read_bytes())

    temp_path.replace(live)
    modified_files.append("core/smart_search.py")

    add_check(
        "candidate_installed_hash",
        digest(live) == CANDIDATE_HASH,
        digest(live),
    )

    py_compile.compile(
        str(live),
        cfile=str(verification_dir / "live_smart_search.pyc"),
        doraise=True,
    )
    add_check("live_compile", True)

    smoke = subprocess.run(
        [
            sys.executable,
            "-S",
            str(bundle / "tests" / "test_live_smartsearch_root_staging_cleanup.py"),
            str(root),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
    )
    smoke_output = (smoke.stdout or "") + (smoke.stderr or "")
    (verification_dir / "live_smoke_output.txt").write_text(
        smoke_output,
        encoding="utf-8",
    )

    required_markers = [
        "live_root_candidate_exclusion=PASS",
        "live_root_payload_exclusion=PASS",
        "live_root_baseline_exclusion=PASS",
        "live_named_bundle_exclusion=PASS",
        "live_source_priority=PASS",
        "live_memory_classification=PASS",
        "live_policy_disclosure=PASS",
    ]
    add_check(
        "real_live_root_staging_smoke",
        smoke.returncode == 0
        and all(marker in smoke_output for marker in required_markers),
        {
            "returncode": smoke.returncode,
            "required_markers": required_markers,
        },
    )

    add_check("final_live_hash", digest(live) == CANDIDATE_HASH, digest(live))

    receipt_path = write_receipt("verified", True)
    print()
    print("APPLY VERIFIED.")
    print("State: verified")
    print("Live SHA-256:", digest(live))
    print("Backup:", backup_dir)
    print("Receipt:", receipt_path)

except Exception as exc:
    failure = {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }

    rollback_ok = False
    rollback_detail = None

    if (
        backup_dir is not None
        and (backup_dir / "core" / "smart_search.py").exists()
    ):
        try:
            backup_file = backup_dir / "core" / "smart_search.py"
            with tempfile.NamedTemporaryFile(
                mode="wb",
                delete=False,
                dir=str(live.parent),
                prefix="smart_search.autorollback.",
                suffix=".tmp",
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(backup_file.read_bytes())

            temp_path.replace(live)
            rollback_ok = digest(live) == BASELINE_HASH
            rollback_detail = {
                "restored_sha256": digest(live),
                "backup": str(backup_file),
            }
        except Exception as rollback_exc:
            rollback_detail = {
                "error": type(rollback_exc).__name__,
                "message": str(rollback_exc),
            }

    checks.append(
        {
            "id": "automatic_rollback_restored_exact_before_state",
            "ok": rollback_ok,
            "detail": rollback_detail,
        }
    )

    receipt_path = write_receipt(
        "rolled_back" if rollback_ok else "failed",
        False,
        failure=failure,
    )

    print()
    print("APPLY FAILED.")
    print("Rollback state:", "rolled_back" if rollback_ok else "failed")
    print("Failure:", f"{type(exc).__name__}: {exc}")
    print("Receipt:", receipt_path)
    raise SystemExit(1)
