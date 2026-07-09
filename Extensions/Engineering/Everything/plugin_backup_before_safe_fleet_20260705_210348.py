from __future__ import annotations

import subprocess
from pathlib import Path

from core_v10.extension_hooks import hookimpl


def _exe(context, manifest) -> Path | None:
    return context.find_manifest_executable(manifest)


@hookimpl
def extension_health(context, manifest):
    exe = _exe(context, manifest)
    key = manifest.get("key")
    if not exe:
        return {"key": key, "ok": False, "status": "missing", "message": f"No executable found for {manifest.get('executables', [])}."}
    return {"key": key, "ok": True, "status": "ready", "message": f"{manifest.get('name')} found.", "path": str(exe)}


@hookimpl
def extension_launch(context, manifest, key):
    if key != manifest.get("key"):
        return None
    exe = _exe(context, manifest)
    if not exe:
        return {"key": key, "ok": False, "message": "Executable not found."}
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
        return {"key": key, "ok": True, "message": f"Launched {manifest.get('name')}."}
    except Exception as exc:
        return {"key": key, "ok": False, "message": str(exc)}


@hookimpl
def extension_invoke(context, manifest, key, action, payload):
    if key != manifest.get("key"):
        return None
    return {"key": key, "ok": False, "message": f"{manifest.get('name')} does not support invoke action yet."}
