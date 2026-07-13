from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

BASELINE_HASHES = {'core/server.py': 'e0a840396045e728794a64edfeee5d1465471feb975da76dc97b44f6ce14884c', 'core/foxai_web.py': '0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda', 'ui/main_window.py': '32dae792dd84417d7f3fb131eef9d523c8b339f8fd9a86beec79803d1a22e8a1'}
SCOPE = ['core/server.py', 'ui/main_window.py', 'core/foxai_web.py']

def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_restore(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=str(destination.parent),
        prefix=destination.name + ".rollback.",
        suffix=".tmp",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(source.read_bytes())
    temp_path.replace(destination)

if len(sys.argv) != 3:
    raise SystemExit("usage: rollback_shared_neural_runtime.py FOXAI_ROOT BACKUP_DIR")

root = Path(sys.argv[1]).resolve()
backup_dir = Path(sys.argv[2]).resolve()

for rel in SCOPE:
    backup_file = backup_dir / rel
    if not backup_file.exists():
        raise SystemExit(f"Backup file not found: {backup_file}")
    if digest(backup_file) != BASELINE_HASHES[rel]:
        raise SystemExit(f"Backup hash mismatch: {rel}")

for rel in SCOPE:
    atomic_restore(backup_dir / rel, root / rel)

restored = {rel: digest(root / rel) for rel in SCOPE}
verified = restored == BASELINE_HASHES
receipt = {
    "action": "rollback_shared_neural_runtime",
    "state": "rolled_back" if verified else "failed",
    "verified": verified,
    "root": str(root),
    "backup": str(backup_dir),
    "restored_hashes": restored,
}
receipt_path = backup_dir / "manual_rollback_receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print("Rollback state:", receipt["state"])
for rel, value in restored.items():
    print(f"{rel}: {value}")
print("Receipt:", receipt_path)
raise SystemExit(0 if verified else 1)
