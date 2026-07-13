from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import sys
import urllib.request

BASELINE_HASH = "5feb632c5d44d260dba706019beeacf2f5e210ab5a495b9ede3fbe287a6b899e"
CANDIDATE_HASH = "4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43"
PHRASE = "ROLLBACK PORTABLE PYTHON FIX"
URL = "http://127.0.0.1:8765/"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_copy(source: Path, target: Path) -> None:
    temporary = target.with_name(target.name + ".portable_rollback_tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

def server_reachable() -> bool:
    try:
        urllib.request.urlopen(URL, timeout=1).close()
        return True
    except Exception:
        return False

bundle = Path(__file__).resolve().parents[1]
root = None
for possible_root in [bundle.parent, bundle]:
    live = possible_root / "core" / "foxai_web.py"
    if live.exists() and sha256(live) in {BASELINE_HASH, CANDIDATE_HASH}:
        root = possible_root
        break

if root is None:
    print("BLOCKED: FOXAI root could not be safely detected.")
    sys.exit(1)

live = root / "core" / "foxai_web.py"
if server_reachable():
    print("BLOCKED: Close FOXAI before rollback.")
    sys.exit(2)

current_hash = sha256(live)
if current_hash != CANDIDATE_HASH:
    print("BLOCKED: Live file is not the reviewed compatibility candidate.")
    print("Current SHA-256:", current_hash)
    sys.exit(3)

backup_root = root / "Backups" / "SecurityMilestone"
backups = sorted(
    backup_root.glob("PortablePythonFix_*/core/foxai_web.py"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
backup = next((p for p in backups if sha256(p) == BASELINE_HASH), None)
if backup is None:
    print("BLOCKED: No verified baseline backup was found.")
    sys.exit(4)

typed = input(f"Type exactly {PHRASE} to continue: ")
if typed != PHRASE:
    print("Approval phrase did not match. No changes made.")
    sys.exit(5)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
preserve = backup_root / f"PortablePythonFix_RollbackLive_{stamp}" / "core" / "foxai_web.py"
preserve.parent.mkdir(parents=True, exist_ok=False)
shutil.copy2(live, preserve)
if sha256(preserve) != CANDIDATE_HASH:
    print("FAILED: Could not verify preservation copy. No rollback attempted.")
    sys.exit(6)

atomic_copy(backup, live)
restored = sha256(live)
receipt = {
    "action": "portable_python_compatibility_manual_rollback",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "verified" if restored == BASELINE_HASH else "failed",
    "verified": restored == BASELINE_HASH,
    "restored_from": str(backup),
    "preserved_candidate": str(preserve),
    "restored_sha256": restored,
}
report_dir = root / "Reports" / "SecurityMilestone"
report_dir.mkdir(parents=True, exist_ok=True)
path = report_dir / f"PortablePythonFix_Rollback_Receipt_{stamp}.json"
path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("Rollback state:", receipt["state"])
print("Receipt:", path)
sys.exit(0 if receipt["verified"] else 7)
