from __future__ import annotations

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
