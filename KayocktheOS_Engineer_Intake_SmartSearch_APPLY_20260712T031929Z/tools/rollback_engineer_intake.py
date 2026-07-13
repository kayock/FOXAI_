from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import sys

BASELINE_HASH = "bf32b0ab80b6cc3a177698101a5c2121a4224d0bf55bbe78c047f541fb3a6339"
CANDIDATE_HASH = "a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a"
PHRASE = "ROLLBACK ENGINEER INTAKE REPAIR"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_copy(source: Path, target: Path) -> None:
    temporary = target.with_name(target.name + ".engineer_intake_rollback_tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

bundle = Path(__file__).resolve().parents[1]
root = None
live = None
for possible_root in [bundle.parent, bundle]:
    possible_live = possible_root / "core" / "engineer_agent.py"
    if possible_live.exists() and sha256(possible_live) in {BASELINE_HASH, CANDIDATE_HASH}:
        root = possible_root
        live = possible_live
        break

if root is None or live is None:
    print("BLOCKED: FOXAI root could not be safely detected.")
    raise SystemExit(1)

current = sha256(live)
if current != CANDIDATE_HASH:
    print("BLOCKED: Live Engineer file is not the reviewed repair candidate.")
    print("Current SHA-256:", current)
    raise SystemExit(2)

backup_root = root / "Backups" / "SecurityMilestone"
backups = sorted(
    backup_root.glob("EngineerIntake_*/core/engineer_agent.py"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
backup = next((p for p in backups if sha256(p) == BASELINE_HASH), None)
if backup is None:
    print("BLOCKED: No verified Engineer baseline backup was found.")
    raise SystemExit(3)

typed = input(f"Type exactly {PHRASE} to continue: ")
if typed != PHRASE:
    print("Approval phrase did not match. No changes made.")
    raise SystemExit(4)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
preserve = (
    backup_root
    / f"EngineerIntake_RollbackLive_{timestamp}"
    / "core"
    / "engineer_agent.py"
)
preserve.parent.mkdir(parents=True, exist_ok=False)
shutil.copy2(live, preserve)
if sha256(preserve) != CANDIDATE_HASH:
    print("FAILED: Could not verify preservation copy. No rollback attempted.")
    raise SystemExit(5)

atomic_copy(backup, live)
restored = sha256(live)
verified = restored == BASELINE_HASH

receipt = {
    "action": "engineer_intake_smartsearch_manual_rollback",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "verified" if verified else "failed",
    "verified": verified,
    "restored_from": str(backup),
    "preserved_candidate": str(preserve),
    "restored_sha256": restored,
}
report_dir = root / "Reports" / "SecurityMilestone"
report_dir.mkdir(parents=True, exist_ok=True)
path = report_dir / f"EngineerIntake_Rollback_Receipt_{timestamp}.json"
path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print("Rollback state:", receipt["state"])
print("Receipt:", path)
print("Restart the FOXAI desktop UI before testing.")
raise SystemExit(0 if verified else 6)
