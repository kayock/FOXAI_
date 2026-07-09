from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "extension_manager.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"conversation_invoke_arbiter_{STAMP}"
BACKUP_FILE = BACKUP_DIR / "core_v10" / "extension_manager.py"

OLD = """    def invoke(self, key: str, action: str, payload: dict | None = None) -> dict[str, Any]:
        manifest = self.manifests.get(key)
        if not manifest:
            self.discover_plugins()
            manifest = self.manifests.get(key)
        if not manifest:
            return {"ok": False, "key": key, "message": f"Unknown extension: {key}"}

        results = self.plugin_manager.hook.extension_invoke(context=self.context, manifest=manifest, key=key, action=action, payload=payload or {})
        for result in results:
            if isinstance(result, dict) and result.get("key") == key:
                return result

        return {"ok": False, "key": key, "message": f"No invoke handler responded for extension: {key}.{action}"}
"""

NEW = """    def invoke(self, key: str, action: str, payload: dict | None = None) -> dict[str, Any]:
        manifest = self.manifests.get(key)
        if not manifest:
            self.discover_plugins()
            manifest = self.manifests.get(key)
        if not manifest:
            return {"ok": False, "key": key, "message": f"Unknown extension: {key}"}

        results = self.plugin_manager.hook.extension_invoke(
            context=self.context,
            manifest=manifest,
            key=key,
            action=action,
            payload=payload or {},
        )

        matches: list[dict[str, Any]] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            if result.get("key") != key:
                continue
            matches.append(result)

        if not matches:
            return {
                "ok": False,
                "key": key,
                "message": f"No invoke handler responded for extension: {key}.{action}",
                "invoke_candidates": [],
                "selected_by": "none",
            }

        def score(item: dict[str, Any]) -> int:
            if item.get("ok") is True:
                return 100
            msg = str(item.get("message", "")).lower()
            status = str(item.get("status", "")).lower()
            if status in ("complete", "ready", "success"):
                return 90
            if "unsupported" in msg or "does not support" in msg or "not implemented" in msg:
                return 5
            return 10

        chosen = sorted(matches, key=score, reverse=True)[0]
        chosen = dict(chosen)
        chosen["invoke_candidates"] = [
            {
                "ok": m.get("ok"),
                "status": m.get("status"),
                "message": m.get("message"),
                "provider": m.get("provider"),
                "model": m.get("model"),
            }
            for m in matches
        ]
        chosen["selected_by"] = "extension_invoke_arbiter"
        return chosen
"""


def main() -> None:
    print("FOXAI CM v3.8 Conversation Invoke Arbiter Patch")
    print("===============================================")
    print()

    if not TARGET.exists():
        print(f"ERROR: target file not found: {TARGET}")
        raise SystemExit(1)

    BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, BACKUP_FILE)

    marker = ROOT / "Config" / "last_conversation_invoke_arbiter_backup.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(BACKUP_DIR), encoding="utf-8")

    text = TARGET.read_text(encoding="utf-8")

    if "extension_invoke_arbiter" in text:
        print("Patch appears to already be installed.")
    elif OLD not in text:
        print("ERROR: Could not find expected invoke() block.")
        print("Backup was still created:")
        print(BACKUP_FILE)
        print()
        print("No changes made.")
        raise SystemExit(1)
    else:
        TARGET.write_text(text.replace(OLD, NEW), encoding="utf-8")
        print("[PATCHED] core_v10\\extension_manager.py")
        print("[BACKUP]", BACKUP_FILE)

    print()
    print("Running mission executor tests...")
    print()

    for test_name in ["TEST_MISSION_EXECUTOR.py"]:
        test = ROOT / test_name
        if test.exists():
            print("=" * 72)
            print(f"RUNNING {test.name}")
            print("=" * 72)
            subprocess.run([sys.executable, str(test)], cwd=str(ROOT))
            print()
        else:
            print(f"[SKIP] {test.name} not found.")

    custom = ROOT / "EXECUTE_MISSION.py"
    if custom.exists():
        print("=" * 72)
        print("RUNNING EXECUTE_MISSION.py toaster test")
        print("=" * 72)
        subprocess.run([sys.executable, str(custom), "Tell me a joke about a toaster joining Starfleet."], cwd=str(ROOT))

    print()
    print("Patch complete.")
    print("If needed, run RESTORE_CONVERSATION_INVOKE_ARBITER.bat.")


if __name__ == "__main__":
    main()
