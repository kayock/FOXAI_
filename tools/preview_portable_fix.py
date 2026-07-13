from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import sys

EXPECTED = "5feb632c5d44d260dba706019beeacf2f5e210ab5a495b9ede3fbe287a6b899e"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

bundle = Path(__file__).resolve().parents[1]

# Supports both safe layouts:
# 1. Z:\FOXAI\<bundle folder>\...
# 2. Files accidentally extracted directly into Z:\FOXAI\...
root_candidates = [bundle, bundle.parent]
root = None
live = None
candidate_details = []

for possible_root in root_candidates:
    possible_live = possible_root / "core" / "foxai_web.py"
    exists = possible_live.exists()
    live_hash = sha256(possible_live) if exists else None
    candidate_details.append({
        "root": str(possible_root),
        "live": str(possible_live),
        "exists": exists,
        "sha256": live_hash,
    })
    if exists and live_hash == EXPECTED:
        root = possible_root
        live = possible_live
        break

baseline = bundle / "baseline" / "core" / "foxai_web.py"
candidate = bundle / "candidate" / "core" / "foxai_web.py"
out = bundle / "preview_output"
out.mkdir(parents=True, exist_ok=True)

receipt = {
    "action": "portable_python_compatibility_preview",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "bundle": str(bundle),
    "root_candidates": candidate_details,
    "modified": False,
    "checks": [],
}

def check(check_id: str, ok: bool, detail: str) -> None:
    receipt["checks"].append({"id": check_id, "ok": bool(ok), "detail": detail})

check("foxai_root_detected", root is not None, str(root) if root else "No candidate matched the reviewed Phase 1 hash.")

if root is not None and live is not None:
    receipt["root"] = str(root)
    receipt["live_file"] = str(live)
    check("live_file_exists", True, str(live))
    live_hash = sha256(live)
    check("live_hash_matches_reviewed_phase1", live_hash == EXPECTED, live_hash)
else:
    live_hash = None

baseline_exists = baseline.exists()
candidate_exists = candidate.exists()
check("bundled_baseline_exists", baseline_exists, str(baseline))
check("bundled_candidate_exists", candidate_exists, str(candidate))

if baseline_exists:
    baseline_hash = sha256(baseline)
    check("bundled_baseline_hash", baseline_hash == EXPECTED, baseline_hash)
else:
    baseline_hash = None

ready = (
    root is not None
    and live is not None
    and live_hash == EXPECTED
    and baseline_exists
    and baseline_hash == EXPECTED
    and candidate_exists
)

if ready:
    old = live.read_text(encoding="utf-8")
    new = candidate.read_text(encoding="utf-8")
    exact = "".join(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="a/core/foxai_web.py",
        tofile="b/core/foxai_web.py",
        n=4,
    ))
    diff_path = out / "PORTABLE_PYTHON_COMPATIBILITY_EXACT.diff"
    diff_path.write_text(exact, encoding="utf-8")
    check("exact_diff_generated", bool(exact), str(diff_path))
    receipt["state"] = "preview_ready"
    receipt["candidate_sha256"] = sha256(candidate)
    receipt["diff"] = str(diff_path)
else:
    receipt["state"] = "blocked"

receipt["verified"] = receipt["state"] == "preview_ready" and all(c["ok"] for c in receipt["checks"])
receipt_path = out / "PREVIEW_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("PORTABLE PYTHON COMPATIBILITY FIX - PREVIEW ONLY")
print("=" * 62)
for item in receipt["checks"]:
    print(("PASS" if item["ok"] else "FAIL") + "  " + item["id"] + "  " + item["detail"])
print()
print("Detected FOXAI root:", receipt.get("root", "NOT FOUND"))
print("State:", receipt["state"])
print("Modified live files: NO")
print("Receipt:", receipt_path)
if receipt.get("diff"):
    print("Exact diff:", receipt["diff"])
    print()
    print(Path(receipt["diff"]).read_text(encoding="utf-8"))
sys.exit(0 if receipt["verified"] else 1)
