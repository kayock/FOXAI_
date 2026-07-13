from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import py_compile
import subprocess
import sys

BASELINE_HASH = "be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c"
CANDIDATE_HASH = "f9b6d67557d0038725c8b05f293f303e639c95f57c73df260ea012d6e44c4efd"
DIFF_HASH = "ca5aa9c1edb1805760862de3ec1a47bb47f41ae82fd47541e3f4d80166f015c6"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


bundle = Path(__file__).resolve().parents[1]
root = bundle.parent
live = root / "core" / "smart_search.py"
candidate = bundle / "candidate" / "core" / "smart_search.py"
diff = bundle / "SMARTSEARCH_ROOT_STAGING_CLEANUP_EXACT.diff"

checks = [
    {
        "id": "live_baseline_hash",
        "ok": live.exists() and digest(live) == BASELINE_HASH,
        "detail": digest(live) if live.exists() else None,
    },
    {
        "id": "candidate_hash",
        "ok": digest(candidate) == CANDIDATE_HASH,
    },
    {
        "id": "exact_diff_hash",
        "ok": digest(diff) == DIFF_HASH,
    },
    {
        "id": "apply_script_absent",
        "ok": not any(bundle.glob("APPLY*.bat")),
    },
]

output_dir = bundle / "preview_output"
output_dir.mkdir(parents=True, exist_ok=True)
compile_dir = output_dir / "compile"
compile_dir.mkdir(parents=True, exist_ok=True)

try:
    py_compile.compile(
        str(candidate),
        cfile=str(compile_dir / "smart_search.pyc"),
        doraise=True,
    )
    checks.append({"id": "candidate_compile", "ok": True})
except Exception as exc:
    checks.append({
        "id": "candidate_compile",
        "ok": False,
        "detail": str(exc),
    })

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
    text = (completed.stdout or "") + (completed.stderr or "")
    return {
        "ok": completed.returncode == 0 and marker in text,
        "returncode": completed.returncode,
        "output": text,
    }

targeted = run_test(
    "test_smart_search_root_staging_cleanup.py",
    "Ran 8 tests",
)
phase1 = run_test(
    "test_phase1_security.py",
    "Ran 15 tests",
)
checks.extend([
    {
        "id": "targeted_root_staging_tests_8",
        "ok": targeted["ok"],
    },
    {
        "id": "phase1_security_regression_tests_15",
        "ok": phase1["ok"],
    },
])

verified = all(item["ok"] for item in checks)
receipt = {
    "action": "preview_smartsearch_root_staging_cleanup",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "preview_ready" if verified else "blocked",
    "verified": verified,
    "live_files_modified": False,
    "detected_root": str(root),
    "scope": ["core/smart_search.py"],
    "checks": checks,
    "baseline_hash": BASELINE_HASH,
    "candidate_hash": CANDIDATE_HASH,
    "exact_diff_hash": DIFF_HASH,
    "targeted_test_output": targeted["output"],
    "phase1_test_output": phase1["output"],
}
receipt_path = (
    output_dir
    / "SmartSearch_Root_Staging_Cleanup_PREVIEW_RECEIPT.json"
)
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("SMARTSEARCH ROOT STAGING CLEANUP - PREVIEW ONLY")
print("=" * 66)
print("State:", receipt["state"])
print("Live baseline hash:", "MATCH" if checks[0]["ok"] else "MISMATCH")
print("Candidate compile:", "PASS" if checks[4]["ok"] else "FAIL")
print("Targeted root staging tests:", "8 PASS" if targeted["ok"] else "FAIL")
print("Phase 1 containment tests:", "15 PASS" if phase1["ok"] else "FAIL")
print()
print("Proposed additional exclusions:")
print("  - root candidate/")
print("  - root payload/")
print("  - root baseline/")
print()
print("NO LIVE FILES WERE MODIFIED.")
print("Receipt:", receipt_path)
raise SystemExit(0 if verified else 1)
