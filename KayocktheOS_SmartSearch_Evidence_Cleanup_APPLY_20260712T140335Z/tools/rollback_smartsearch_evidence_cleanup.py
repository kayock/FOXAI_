from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import sys

BASELINE_HASH = "f87ff40820e70067ad562ce1ffb57afcb60a3085dcac176deab4d26c4e427d18"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if len(sys.argv) != 3:
    raise SystemExit(
        "usage: rollback_smartsearch_evidence_cleanup.py FOXAI_ROOT BACKUP_DIR"
    )

root = Path(sys.argv[1]).resolve()
backup_dir = Path(sys.argv[2]).resolve()
live = root / "core" / "smart_search.py"
backup = backup_dir / "core" / "smart_search.py"

if not backup.exists():
    raise SystemExit(f"Backup file not found: {backup}")
if digest(backup) != BASELINE_HASH:
    raise SystemExit("Backup hash does not match the reviewed baseline.")

with tempfile.NamedTemporaryFile(
    mode="wb",
    delete=False,
    dir=str(live.parent),
    prefix="smart_search.rollback.",
    suffix=".tmp",
) as handle:
    temp_path = Path(handle.name)
    handle.write(backup.read_bytes())

temp_path.replace(live)

restored = digest(live)
if restored != BASELINE_HASH:
    raise SystemExit("Rollback verification failed.")

receipt = {
    "state": "rolled_back",
    "verified": True,
    "restored": str(live),
    "restored_sha256": restored,
    "backup": str(backup),
}
receipt_path = backup_dir / "rollback_receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print("Rollback state: rolled_back")
print("Restored:", live)
print("SHA-256:", restored)
print("Receipt:", receipt_path)
