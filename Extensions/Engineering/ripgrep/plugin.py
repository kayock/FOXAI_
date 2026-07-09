from __future__ import annotations

import subprocess
from pathlib import Path

from core_v10.extension_hooks import hookimpl


def _exe(context, manifest) -> Path | None:
    return context.find_manifest_executable(manifest)


@hookimpl
def extension_health(context, manifest):
    if manifest.get("key") != "ripgrep":
        return None
    rg = _exe(context, manifest)
    if not rg:
        return {"key": "ripgrep", "ok": False, "status": "missing", "message": "rg.exe not found in executable inventory."}
    try:
        out = subprocess.run([str(rg), "--version"], capture_output=True, text=True, timeout=3)
        first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else "ripgrep found"
        return {"key": "ripgrep", "ok": True, "status": "ready", "message": first, "path": str(rg)}
    except Exception as exc:
        return {"key": "ripgrep", "ok": False, "status": "error", "message": str(exc), "path": str(rg)}


@hookimpl
def extension_launch(context, manifest, key):
    if key != "ripgrep":
        return None
    return {"key": "ripgrep", "ok": False, "message": "ripgrep is a command-line shuttle pod. Use invoke search."}


@hookimpl
def extension_invoke(context, manifest, key, action, payload):
    if key != "ripgrep":
        return None

    rg = _exe(context, manifest)
    if not rg:
        return {"key": key, "ok": False, "message": "rg.exe not found."}

    if action != "search":
        return {"key": key, "ok": False, "message": f"Unsupported ripgrep action: {action}"}

    pattern = str(payload.get("pattern", "")).strip()
    target = Path(str(payload.get("target", context.foxai_root)))

    if not pattern:
        return {"key": key, "ok": False, "message": "Missing search pattern."}
    if not target.exists():
        return {"key": key, "ok": False, "message": f"Target not found: {target}"}

    cmd = [str(rg), "--line-number", "--hidden", "--glob", "!*.gguf", "--glob", "!*.safetensors", pattern, str(target)]

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        text = (out.stdout or out.stderr or "").strip()
        return {
            "key": key,
            "ok": out.returncode in (0, 1),
            "status": "complete",
            "returncode": out.returncode,
            "command": cmd,
            "output": text[:8000],
            "message": "Search complete." if text else "No matches.",
        }
    except Exception as exc:
        return {"key": key, "ok": False, "message": str(exc)}
