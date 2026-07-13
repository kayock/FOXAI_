from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import socket

CANDIDATE_WEB_HASH = "0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda"
CANDIDATE_SESSION_HASH = "d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a"
PHRASE = "ROLLBACK WEBUI SHARED MISSION SESSION"

def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_copy(source: Path, target: Path) -> None:
    temporary = target.with_name(target.name + ".webui_shared_manual_rollback_tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    os.replace(temporary, target)

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(("127.0.0.1", port)) == 0

bundle = Path(__file__).resolve().parents[1]
root = None
live_web = None
live_session = None

for possible_root in [bundle.parent, bundle]:
    web = possible_root / "core" / "foxai_web.py"
    session = possible_root / "core" / "mission_session.py"
    if (
        web.exists()
        and session.exists()
        and digest(web) == CANDIDATE_WEB_HASH
        and digest(session) == CANDIDATE_SESSION_HASH
    ):
        root = possible_root
        live_web = web
        live_session = session
        break

if root is None or live_web is None or live_session is None:
    print("BLOCKED: The approved WebUI Shared Mission Session candidate is not installed.")
    raise SystemExit(1)

if port_open(8765):
    print("BLOCKED: The WebUI server is still running on port 8765.")
    print("Close the START_FOXAI_WEB console before rollback.")
    raise SystemExit(2)

backup_root = root / "Backups" / "SecurityMilestone"
manifests = sorted(
    backup_root.glob("WebUISharedMission_*/rollback_manifest.json"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
selected = None
metadata = None
for manifest in manifests:
    try:
        item = json.loads(manifest.read_text(encoding="utf-8"))
        backup_web = Path(item["backup_web"])
        if not backup_web.exists():
            continue
        if digest(backup_web) != item.get("before_web_sha256"):
            continue
        if item.get("mission_session_existed"):
            backup_session = Path(item["backup_mission_session"])
            if not backup_session.exists():
                continue
            if digest(backup_session) != item.get("before_mission_session_sha256"):
                continue
        selected = manifest
        metadata = item
        break
    except Exception:
        continue

if selected is None or metadata is None:
    print("BLOCKED: No verified WebUI Shared Mission Session backup was found.")
    raise SystemExit(3)

typed = input(f"Type exactly {PHRASE} to continue: ")
if typed != PHRASE:
    print("Approval phrase did not match. No files were changed.")
    raise SystemExit(4)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
preserve = backup_root / f"WebUISharedMission_RollbackLive_{timestamp}" / "core"
preserve.mkdir(parents=True, exist_ok=False)
preserve_web = preserve / "foxai_web.py"
preserve_session = preserve / "mission_session.py"
shutil.copy2(live_web, preserve_web)
shutil.copy2(live_session, preserve_session)

if digest(preserve_web) != CANDIDATE_WEB_HASH or digest(preserve_session) != CANDIDATE_SESSION_HASH:
    print("FAILED: Could not verify the preservation copy. No rollback attempted.")
    raise SystemExit(5)

atomic_copy(Path(metadata["backup_web"]), live_web)
if metadata.get("mission_session_existed"):
    atomic_copy(Path(metadata["backup_mission_session"]), live_session)
else:
    live_session.unlink()

restored_web_hash = digest(live_web)
restored_session_exists = live_session.exists()
restored_session_hash = digest(live_session) if restored_session_exists else None
verified = (
    restored_web_hash == metadata.get("before_web_sha256")
    and restored_session_exists == bool(metadata.get("mission_session_existed"))
    and restored_session_hash == metadata.get("before_mission_session_sha256")
)

receipt = {
    "action": "webui_shared_mission_session_manual_rollback",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "verified" if verified else "failed",
    "verified": verified,
    "restored_from_manifest": str(selected),
    "preserved_candidate_folder": str(preserve),
    "restored_web_sha256": restored_web_hash,
    "restored_mission_session_exists": restored_session_exists,
    "restored_mission_session_sha256": restored_session_hash,
}
report_dir = root / "Reports" / "SecurityMilestone"
report_dir.mkdir(parents=True, exist_ok=True)
receipt_path = report_dir / f"WebUISharedMission_Rollback_Receipt_{timestamp}.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print("Rollback state:", receipt["state"])
print("Receipt:", receipt_path)
print("Restart START_FOXAI_WEB.bat before testing.")
raise SystemExit(0 if verified else 6)
