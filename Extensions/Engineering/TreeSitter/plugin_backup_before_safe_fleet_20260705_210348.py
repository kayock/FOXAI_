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
    try:
        out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=5)
        first = (out.stdout or out.stderr or f"{manifest.get('name')} found").splitlines()[0]
        return {"key": key, "ok": True, "status": "ready", "message": first, "path": str(exe)}
    except Exception:
        return {"key": key, "ok": True, "status": "ready", "message": f"{manifest.get('name')} found.", "path": str(exe)}


@hookimpl
def extension_launch(context, manifest, key):
    if key != manifest.get("key"):
        return None
    return {"key": key, "ok": False, "message": f"{manifest.get('name')} is a command-line shuttle pod."}


@hookimpl
def extension_invoke(context, manifest, key, action, payload):
    if key != manifest.get("key"):
        return None
    return {"key": key, "ok": False, "message": f"{manifest.get('name')} invoke action not implemented yet."}
