from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import py_compile
import subprocess
import sys

EXPECTED_BASELINE = "f87ff40820e70067ad562ce1ffb57afcb60a3085dcac176deab4d26c4e427d18"
EXPECTED_CANDIDATE = "be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c"
EXPECTED_DIFF = "c32349b345fc32347877e3d8d39d30d89df49ee5fb20ac9397515e169dbd57b3"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


bundle = Path(__file__).resolve().parents[1]
root = None
root_checks = []

for possible in [bundle.parent, bundle]:
    live = possible / "core" / "smart_search.py"
    if not live.exists():
        root_checks.append({"root": str(possible), "exists": False})
        continue
    live_hash = digest(live)
    item = {
        "root": str(possible),
        "exists": True,
        "live_hash": live_hash,
        "baseline_match": live_hash == EXPECTED_BASELINE,
    }
    root_checks.append(item)
    if item["baseline_match"]:
        root = possible
        break

candidate = bundle / "candidate" / "core" / "smart_search.py"
diff = bundle / "SMARTSEARCH_EVIDENCE_CLEANUP_EXACT.diff"
checks = [
    {"id": "candidate_hash", "ok": digest(candidate) == EXPECTED_CANDIDATE},
    {"id": "exact_diff_hash", "ok": digest(diff) == EXPECTED_DIFF},
    {"id": "apply_bundle_absent", "ok": not any(bundle.glob("APPLY*.bat"))},
]

compile_dir = bundle / "preview_output" / "compile"
compile_dir.mkdir(parents=True, exist_ok=True)
try:
    py_compile.compile(
        str(candidate),
        cfile=str(compile_dir / "smart_search.pyc"),
        doraise=True,
    )
    checks.append({"id": "candidate_compile", "ok": True})
except Exception as exc:
    checks.append({"id": "candidate_compile", "ok": False, "detail": str(exc)})

def run_test(test_name: str, marker: str):
    command = [
        sys.executable,
        "-S",
        str(bundle / "tools" / "run_test_bootstrap.py"),
        str(bundle / "payload"),
        str(bundle / "tests" / test_name),
    ]
    completed = subprocess.run(
        command,
        cwd=str(bundle),
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return {
        "returncode": completed.returncode,
        "marker": marker,
        "ok": completed.returncode == 0 and marker in output,
        "output": output,
    }

targeted = run_test("test_smart_search_evidence_cleanup.py", "Ran 7 tests")
phase1 = run_test("test_phase1_security.py", "Ran 15 tests")
checks.extend([
    {"id": "targeted_cleanup_tests_7", "ok": targeted["ok"]},
    {"id": "phase1_security_regression_tests_15", "ok": phase1["ok"]},
])

verified = bool(root) and all(item["ok"] for item in checks)
receipt = {
    "action": "preview_smartsearch_evidence_cleanup",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "preview_ready" if verified else "blocked",
    "verified": verified,
    "live_files_modified": False,
    "detected_root": str(root) if root else None,
    "root_checks": root_checks,
    "checks": checks,
    "proposed_live_changes": ["update core/smart_search.py"],
    "explicit_non_changes": [
        "core/engineer_agent.py",
        "core/security_containment.py",
        "core/director.py",
        "core/foxai_web.py",
        "core/mission_session.py",
        "ui/main_window.py",
        "core_v10/*",
    ],
    "baseline_hash": EXPECTED_BASELINE,
    "candidate_hash": EXPECTED_CANDIDATE,
    "exact_diff_hash": EXPECTED_DIFF,
    "targeted_test_output": targeted["output"],
    "phase1_test_output": phase1["output"],
}

output = bundle / "preview_output"
output.mkdir(parents=True, exist_ok=True)
receipt_path = output / "SmartSearch_Evidence_Cleanup_PREVIEW_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("KAYOCKTHEOS SMARTSEARCH EVIDENCE CLEANUP - PREVIEW ONLY")
print("=" * 72)
if verified:
    print("FOXAI root:", root)
    print("Live SmartSearch baseline hash: MATCH")
    print("Candidate hash: VERIFIED")
    print("Exact diff hash: VERIFIED")
    print("Targeted cleanup tests: 7 PASS")
    print("Phase 1 containment tests: 15 PASS")
    print("State: preview_ready")
    print()
    print("Proposed live change:")
    print(r"  ~ core\smart_search.py")
    print()
    print("Behavior:")
    print("  - Exclude root Backup/Backups trees.")
    print("  - Exclude generated KayocktheOS apply/preview/patch/checkpoint bundles.")
    print("  - Treat Memory/*.py as project memory, not executable source.")
else:
    print("State: blocked")
    print("One or more baseline, hash, compile, or test checks failed.")
print()
print("NO LIVE FILES WERE MODIFIED.")
print("Exact diff:", diff)
print("Receipt:", receipt_path)
raise SystemExit(0 if verified else 1)
