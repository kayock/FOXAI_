from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "core_v10" / "extension_manager.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"extension_health_arbiter_{STAMP}"
BACKUP_FILE = BACKUP_DIR / "core_v10" / "extension_manager.py"

OLD = """    def _service_health(self, manifest: dict[str, Any]) -> dict[str, Any]:
        results = self.plugin_manager.hook.extension_health(context=self.context, manifest=manifest)
        for result in results:
            if isinstance(result, dict) and result.get("key") == manifest.get("key"):
                return result
        return {
            "key": manifest.get("key"),
            "ok": False,
            "status": "missing",
            "message": "Service has no health handler.",
            "path": f"internal://{manifest.get('key')}",
        }
"""

NEW = """    def _service_health(self, manifest: dict[str, Any]) -> dict[str, Any]:
        \"\"\"
        Run extension_health hooks and arbitrate all matching responses.

        Pluggy calls every registered hook implementation. Generic executable
        plugins may return a matching key with status=missing before a
        specialized service plugin returns status=ready. Therefore we must not
        accept the first matching response blindly.

        Selection priority:
        1. ok=True / ready / installed / online
        2. degraded
        3. offline
        4. error
        5. missing
        \"\"\"
        results = self.plugin_manager.hook.extension_health(context=self.context, manifest=manifest)
        key = manifest.get("key")
        matches: list[dict[str, Any]] = []

        for result in results:
            if not isinstance(result, dict):
                continue
            if result.get("key") != key:
                continue
            matches.append(result)

        if not matches:
            return {
                "key": key,
                "ok": False,
                "status": "missing",
                "message": "Service has no health handler.",
                "path": f"internal://{key}",
                "health_candidates": [],
                "selected_by": "none",
            }

        def score(item: dict[str, Any]) -> int:
            status = str(item.get("status", "")).lower()
            if item.get("ok") is True:
                return 100
            if status in ("ready", "installed", "online"):
                return 90
            if status == "degraded":
                return 70
            if status == "offline":
                return 50
            if status == "error":
                return 20
            if status == "missing":
                return 10
            return 0

        chosen = sorted(matches, key=score, reverse=True)[0]
        chosen = dict(chosen)
        chosen["health_candidates"] = [
            {
                "ok": m.get("ok"),
                "status": m.get("status"),
                "message": m.get("message"),
                "path": m.get("path"),
            }
            for m in matches
        ]
        chosen["selected_by"] = "extension_health_arbiter"
        return chosen
"""


def main() -> None:
    print("FOXAI CM v3.6 Extension Health Arbiter Patch")
    print("============================================")
    print()

    if not TARGET.exists():
        print(f"ERROR: target file not found: {TARGET}")
        raise SystemExit(1)

    BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, BACKUP_FILE)

    marker = ROOT / "Config" / "last_extension_health_arbiter_backup.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(BACKUP_DIR), encoding="utf-8")

    text = TARGET.read_text(encoding="utf-8")

    if "extension_health_arbiter" in text:
        print("Patch appears to already be installed.")
    elif OLD not in text:
        print("ERROR: Could not find expected _service_health block.")
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
    print("Running tests...")
    print()

    tests = [
        ROOT / "PLUGIN_DIAGNOSTICS.py",
        ROOT / "STEVEDORE_INSPECTOR.py",
        ROOT / "TEST_SERVICE_SHUTTLE_ARCHITECTURE.py",
        ROOT / "TEST_FLEET_SYNC_CONVERSATION.py",
    ]

    for test in tests:
        if test.exists():
            print("=" * 72)
            print(f"RUNNING {test.name}")
            print("=" * 72)
            subprocess.run([sys.executable, str(test)], cwd=str(ROOT))
            print()
        else:
            print(f"[SKIP] {test.name} not found.")

    print()
    print("Patch complete.")
    print("If needed, run RESTORE_EXTENSION_HEALTH_ARBITER.bat.")


if __name__ == "__main__":
    main()
