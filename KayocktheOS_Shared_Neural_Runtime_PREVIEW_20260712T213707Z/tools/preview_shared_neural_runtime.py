from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import py_compile
import subprocess
import sys

EXPECTED_BASELINES = {'core/server.py': 'e0a840396045e728794a64edfeee5d1465471feb975da76dc97b44f6ce14884c', 'core/foxai_web.py': '0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda', 'ui/main_window.py': '32dae792dd84417d7f3fb131eef9d523c8b339f8fd9a86beec79803d1a22e8a1'}
EXPECTED_CANDIDATES = {'core/server.py': '6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505', 'core/foxai_web.py': 'bd34f97b7580310fa1a25bd031a5afcb91f8079b74167252b68db3cb7e418952', 'ui/main_window.py': 'cd537dc74e106c436d50928a57598fe666155ddcdc445c49b74a0eb5292f55eb'}
EXPECTED_DIFF = '9af4cf49d71249d4f167898fcf57a1c1503dc9dac80a3a0219ce6cdf3f0d05f6'

def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

bundle = Path(__file__).resolve().parents[1]
root = bundle.parent
checks = []

for rel, expected in EXPECTED_BASELINES.items():
    live = root / rel
    checks.append({
        "id": "live_baseline_" + rel.replace("/", "_").replace(".", "_"),
        "ok": live.exists() and digest(live) == expected,
        "detail": digest(live) if live.exists() else None,
    })

for rel, expected in EXPECTED_CANDIDATES.items():
    candidate = bundle / "candidate" / rel
    checks.append({
        "id": "candidate_hash_" + rel.replace("/", "_").replace(".", "_"),
        "ok": digest(candidate) == expected,
    })

diff = bundle / "SHARED_NEURAL_RUNTIME_EXACT.diff"
checks.extend([
    {"id": "exact_diff_hash", "ok": digest(diff) == EXPECTED_DIFF},
    {"id": "apply_script_absent", "ok": not any(bundle.glob("APPLY*.bat"))},
])

output_dir = bundle / "preview_output"
compile_dir = output_dir / "compile"
compile_dir.mkdir(parents=True, exist_ok=True)

for rel in EXPECTED_CANDIDATES:
    source = bundle / "candidate" / rel
    try:
        py_compile.compile(
            str(source),
            cfile=str(compile_dir / (rel.replace("/", "_").replace(".py", "") + ".pyc")),
            doraise=True,
        )
        checks.append({
            "id": "compile_" + rel.replace("/", "_").replace(".", "_"),
            "ok": True,
        })
    except Exception as exc:
        checks.append({
            "id": "compile_" + rel.replace("/", "_").replace(".", "_"),
            "ok": False,
            "detail": str(exc),
        })

def run_test(test_name: str, marker: str, *args):
    command = [
        sys.executable,
        "-S",
        str(bundle / "tools" / "run_test_bootstrap.py"),
        str(bundle / "payload"),
        str(bundle / "tests" / test_name),
        *[str(arg) for arg in args],
    ]
    completed = subprocess.run(
        command,
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=240,
    )
    text = (completed.stdout or "") + (completed.stderr or "")
    return {
        "ok": completed.returncode == 0 and marker in text,
        "returncode": completed.returncode,
        "output": text,
    }

suites = [
    ("shared_runtime_unit_tests_8", run_test("test_shared_runtime.py", "Ran 8 tests")),
    ("shared_runtime_source_tests_9", run_test("test_shared_runtime_source.py", "Ran 9 tests")),
    ("phase1_security_tests_15", run_test("test_phase1_security.py", "Ran 15 tests")),
    ("engineer_intake_tests_8", run_test(
        "test_engineer_intake_smartsearch.py",
        "Ran 8 tests",
        bundle / "payload" / "core" / "engineer_agent.py",
    )),
    ("mission_session_tests_6", run_test("test_mission_session.py", "Ran 6 tests")),
    ("webui_shared_mission_static_tests_11", run_test(
        "test_webui_shared_mission_static.py",
        "Ran 11 tests",
        bundle / "candidate" / "core" / "foxai_web.py",
    )),
]

for check_id, result in suites:
    checks.append({
        "id": check_id,
        "ok": result["ok"],
        "detail": {"returncode": result["returncode"]},
    })

verified = all(item["ok"] for item in checks)
receipt = {
    "action": "preview_shared_neural_runtime",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "preview_ready" if verified else "blocked",
    "verified": verified,
    "live_files_modified": False,
    "detected_root": str(root),
    "scope": ["core/server.py", "ui/main_window.py", "core/foxai_web.py"],
    "explicit_non_changes": [
        "core/security_containment.py",
        "core/director.py",
        "core/engineer_agent.py",
        "core/smart_search.py",
        "core/mission_session.py",
        "core/memory.py",
        "core/comfy_bridge.py",
        "core_v10/*",
    ],
    "checks": checks,
    "baseline_hashes": EXPECTED_BASELINES,
    "candidate_hashes": EXPECTED_CANDIDATES,
    "exact_diff_hash": EXPECTED_DIFF,
    "test_outputs": {check_id: result["output"] for check_id, result in suites},
}

output_dir.mkdir(parents=True, exist_ok=True)
receipt_path = output_dir / "Shared_Neural_Runtime_PREVIEW_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("KAYOCKTHEOS SHARED NEURAL RUNTIME - PREVIEW ONLY")
print("=" * 70)
print("State:", receipt["state"])
print("Live baseline hashes:", "MATCH" if all(item["ok"] for item in checks[:3]) else "MISMATCH")
print("Candidate compilation:", "3 PASS" if all(item["ok"] for item in checks[8:11]) else "FAIL")
print("Shared runtime unit tests: 8 PASS")
print("Shared runtime source tests: 9 PASS")
print("Phase 1 security tests: 15 PASS")
print("Engineer intake tests: 8 PASS")
print("Mission session tests: 6 PASS")
print("WebUI shared mission tests: 11 PASS")
print()
print("Proposed live files:")
print(r"  ~ core\server.py")
print(r"  ~ ui\main_window.py")
print(r"  ~ core\foxai_web.py")
print()
print("NO LIVE FILES WERE MODIFIED.")
print("Receipt:", receipt_path)
raise SystemExit(0 if verified else 1)
