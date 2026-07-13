from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import sys

EXPECTED_BASELINE = "bf32b0ab80b6cc3a177698101a5c2121a4224d0bf55bbe78c047f541fb3a6339"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

bundle = Path(__file__).resolve().parents[1]
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
    if exists and digest == EXPECTED_BASELINE:
        root = possible_root
        live = possible_live
        break

baseline = bundle / "baseline" / "core" / "engineer_agent.py"
candidate = bundle / "candidate" / "core" / "engineer_agent.py"
out = bundle / "preview_output"
out.mkdir(parents=True, exist_ok=True)

receipt = {
    "action": "engineer_intake_smartsearch_preview",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "modified": False,
    "root_detection": detection,
    "checks": [],
}

def check(cid, ok, detail):
    receipt["checks"].append({"id": cid, "ok": bool(ok), "detail": detail})

check("foxai_root_detected", root is not None, str(root) if root else "not found")
baseline_ok = baseline.exists() and sha256(baseline) == EXPECTED_BASELINE
check("bundled_baseline_hash", baseline_ok, sha256(baseline) if baseline.exists() else "missing")
check("bundled_candidate_exists", candidate.exists(), str(candidate))

if root is not None and live is not None and baseline_ok and candidate.exists():
    live_hash = sha256(live)
    check("live_hash_matches_reviewed_phase1", live_hash == EXPECTED_BASELINE, live_hash)
    old = live.read_text(encoding="utf-8")
    new = candidate.read_text(encoding="utf-8")
    exact = "".join(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="a/core/engineer_agent.py",
        tofile="b/core/engineer_agent.py",
        n=5,
    ))
    diff_path = out / "ENGINEER_INTAKE_SMARTSEARCH_EXACT.diff"
    diff_path.write_text(exact, encoding="utf-8")
    check("exact_diff_generated", bool(exact), str(diff_path))
    receipt["state"] = "preview_ready" if all(x["ok"] for x in receipt["checks"]) else "blocked"
    receipt["candidate_sha256"] = sha256(candidate)
    receipt["diff"] = str(diff_path)
else:
    receipt["state"] = "blocked"

receipt["verified"] = receipt["state"] == "preview_ready"
receipt_path = out / "PREVIEW_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("ENGINEER INTAKE + SMARTSEARCH REPAIR - PREVIEW ONLY")
print("=" * 68)
for item in receipt["checks"]:
    print(("PASS" if item["ok"] else "FAIL"), item["id"], item["detail"])
print()
print("State:", receipt["state"])
print("Modified live files: NO")
print("Receipt:", receipt_path)
if receipt.get("diff"):
    print("Exact diff:", receipt["diff"])
    print()
    print(Path(receipt["diff"]).read_text(encoding="utf-8"))
sys.exit(0 if receipt["verified"] else 1)
