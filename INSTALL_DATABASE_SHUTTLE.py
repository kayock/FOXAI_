from pathlib import Path
import shutil

root = Path(__file__).resolve().parent

src_manifest = root / "core_v10" / "database_extension.json"
dst_dir = root / "Extensions" / "Engineering" / "Database"
dst_dir.mkdir(parents=True, exist_ok=True)

shutil.copy2(src_manifest, dst_dir / "extension.json")

plugin = """from __future__ import annotations

from core_v10.extension_hooks import hookimpl


@hookimpl
def extension_health(context, manifest):
    if manifest.get("key") != "database":
        return None
    return {
        "key": "database",
        "ok": True,
        "status": "ready",
        "message": "FOXAI Vault database uses Python sqlite3 and is ready.",
        "path": str(context.foxai_root / "Vault" / "FOXAI.db"),
    }


@hookimpl
def extension_launch(context, manifest, key):
    if key != "database":
        return None
    return {"key": "database", "ok": False, "message": "USS Database Shuttle is a service, not a GUI app."}


@hookimpl
def extension_invoke(context, manifest, key, action, payload):
    if key != "database":
        return None
    return {"key": "database", "ok": False, "message": "Database invoke is restricted to Mission Bus write APIs."}
"""

(dst_dir / "plugin.py").write_text(plugin, encoding="utf-8")

print("USS Database Shuttle installed:")
print(dst_dir)
print()
print("Next run TEST_VAULT_DATABASE_SHUTTLE.bat")
