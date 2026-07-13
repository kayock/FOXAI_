from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

EXPECTED_WEB = "4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43"
EXPECTED_ENGINEER = "a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a"
CANDIDATE_WEB = "0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda"
CANDIDATE_SESSION = "d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a"


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
    live_web = possible / "core" / "foxai_web.py"
    live_engineer = possible / "core" / "engineer_agent.py"
    if not live_web.exists() or not live_engineer.exists():
        root_checks.append({"root": str(possible), "exists": False})
        continue
    web_hash = digest(live_web)
    engineer_hash = digest(live_engineer)
    item = {
        "root": str(possible),
        "exists": True,
        "web_hash": web_hash,
        "engineer_hash": engineer_hash,
        "web_match": web_hash == EXPECTED_WEB,
        "engineer_match": engineer_hash == EXPECTED_ENGINEER,
    }
    root_checks.append(item)
    if item["web_match"] and item["engineer_match"]:
        root = possible
        break

bundled_candidate_checks = [
    {"id": "candidate_web_hash", "ok": digest(bundle / "candidate" / "core" / "foxai_web.py") == CANDIDATE_WEB},
    {"id": "candidate_session_hash", "ok": digest(bundle / "candidate" / "core" / "mission_session.py") == CANDIDATE_SESSION},
    {"id": "exact_diff_present", "ok": (bundle / "WEBUI_SHARED_MISSION_SESSION_EXACT.diff").is_file()},
    {"id": "apply_command_absent", "ok": not any(bundle.glob("APPLY*.bat"))},
]
verified = bool(root) and all(item["ok"] for item in bundled_candidate_checks)
receipt = {
    "action": "preview_webui_shared_mission_session",
    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "state": "preview_ready" if verified else "blocked",
    "verified": verified,
    "live_files_modified": False,
    "detected_root": str(root) if root else None,
    "root_checks": root_checks,
    "bundle_checks": bundled_candidate_checks,
    "proposed_live_changes": [
        "create core/mission_session.py",
        "update core/foxai_web.py",
    ],
    "explicit_non_changes": [
        "core/memory.py",
        "ui/main_window.py",
        "core_v10/*",
        "core/director.py",
        "core/engineer_agent.py",
        "core/security_containment.py",
    ],
    "candidate_hashes": {
        "core/foxai_web.py": CANDIDATE_WEB,
        "core/mission_session.py": CANDIDATE_SESSION,
    },
}

output = bundle / "preview_output"
output.mkdir(parents=True, exist_ok=True)
receipt_path = output / "WebUI_Shared_Mission_Session_PREVIEW_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

print()
print("KAYOCKTHEOS WEBUI SHARED MISSION SESSION - PREVIEW ONLY")
print("=" * 72)
if verified:
    print("FOXAI root:", root)
    print("Live WebUI baseline hash: MATCH")
    print("Live Engineer baseline hash: MATCH")
    print("Bundled candidate hashes: VERIFIED")
    print("State: preview_ready")
    print()
    print("Proposed changes:")
    print(r"  + core\mission_session.py")
    print(r"  ~ core\foxai_web.py")
    print()
    print("Explicitly untouched:")
    print(r"  core\memory.py")
    print(r"  ui\main_window.py")
    print(r"  core_v10\*")
    print(r"  core\director.py")
    print(r"  core\engineer_agent.py")
    print(r"  core\security_containment.py")
else:
    print("State: blocked")
    print("The live baseline or bundled candidate failed verification.")
print()
print("NO LIVE FILES WERE MODIFIED.")
print("Exact diff:", bundle / "WEBUI_SHARED_MISSION_SESSION_EXACT.diff")
print("Receipt:", receipt_path)
raise SystemExit(0 if verified else 1)
