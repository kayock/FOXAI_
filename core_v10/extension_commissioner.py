from __future__ import annotations

from pathlib import Path
from typing import Any

from .extension_context import ExtensionContext
from .extension_manifest import write_manifest


SIGNATURES = [
    {
        "match": ["rg.exe"],
        "key": "ripgrep",
        "folder": "ripgrep",
        "name": "ripgrep",
        "callsign": "USS Search Shuttle",
        "department": "Engineering",
        "category": "Code Search",
        "priority": 10,
        "executables": ["rg.exe"],
        "capabilities": ["code_search", "text_search", "regex_search", "repo_search"],
        "description": "Fast local text and code search specialist.",
        "plugin": "ripgrep",
    },
    {
        "match": ["Everything.exe", "Everything64.exe"],
        "key": "everything",
        "folder": "Everything",
        "name": "Everything",
        "callsign": "USS Filefinder Shuttle",
        "department": "Engineering",
        "category": "File Search",
        "priority": 20,
        "executables": ["Everything.exe", "Everything64.exe"],
        "capabilities": ["file_search", "instant_file_search", "find_files"],
        "description": "Fast local file search specialist.",
        "plugin": "generic_launcher",
    },
    {
        "match": ["WinMergeU.exe", "WinMerge.exe"],
        "key": "winmerge",
        "folder": "WinMerge",
        "name": "WinMerge",
        "callsign": "USS Compare Shuttle",
        "department": "Engineering",
        "category": "Diff and Compare",
        "priority": 30,
        "executables": ["WinMergeU.exe", "WinMerge.exe"],
        "capabilities": ["file_compare", "folder_compare", "diff"],
        "description": "File and folder comparison specialist.",
        "plugin": "generic_launcher",
    },
    {
        "match": ["tree-sitter.exe"],
        "key": "tree_sitter",
        "folder": "TreeSitter",
        "name": "tree-sitter",
        "callsign": "USS Syntax Shuttle",
        "department": "Engineering",
        "category": "Syntax and AST",
        "priority": 40,
        "executables": ["tree-sitter.exe"],
        "capabilities": ["ast_parse", "syntax_tree", "code_structure", "symbol_analysis"],
        "description": "Code syntax tree and AST parsing specialist.",
        "plugin": "generic_cli",
    },
]


GENERIC_LAUNCHER = 'from __future__ import annotations\n\nimport subprocess\nfrom pathlib import Path\n\nfrom core_v10.extension_hooks import hookimpl\n\n\ndef _exe(context, manifest) -> Path | None:\n    return context.find_manifest_executable(manifest)\n\n\n@hookimpl\ndef extension_health(context, manifest):\n    exe = _exe(context, manifest)\n    key = manifest.get("key")\n    if not exe:\n        return {"key": key, "ok": False, "status": "missing", "message": f"No executable found for {manifest.get(\'executables\', [])}."}\n    return {"key": key, "ok": True, "status": "ready", "message": f"{manifest.get(\'name\')} found.", "path": str(exe)}\n\n\n@hookimpl\ndef extension_launch(context, manifest, key):\n    if key != manifest.get("key"):\n        return None\n    exe = _exe(context, manifest)\n    if not exe:\n        return {"key": key, "ok": False, "message": "Executable not found."}\n    try:\n        subprocess.Popen([str(exe)], cwd=str(exe.parent))\n        return {"key": key, "ok": True, "message": f"Launched {manifest.get(\'name\')}."}\n    except Exception as exc:\n        return {"key": key, "ok": False, "message": str(exc)}\n\n\n@hookimpl\ndef extension_invoke(context, manifest, key, action, payload):\n    if key != manifest.get("key"):\n        return None\n    return {"key": key, "ok": False, "message": f"{manifest.get(\'name\')} does not support invoke action yet."}\n'
GENERIC_CLI = 'from __future__ import annotations\n\nimport subprocess\nfrom pathlib import Path\n\nfrom core_v10.extension_hooks import hookimpl\n\n\ndef _exe(context, manifest) -> Path | None:\n    return context.find_manifest_executable(manifest)\n\n\n@hookimpl\ndef extension_health(context, manifest):\n    exe = _exe(context, manifest)\n    key = manifest.get("key")\n    if not exe:\n        return {"key": key, "ok": False, "status": "missing", "message": f"No executable found for {manifest.get(\'executables\', [])}."}\n    try:\n        out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=5)\n        first = (out.stdout or out.stderr or f"{manifest.get(\'name\')} found").splitlines()[0]\n        return {"key": key, "ok": True, "status": "ready", "message": first, "path": str(exe)}\n    except Exception:\n        return {"key": key, "ok": True, "status": "ready", "message": f"{manifest.get(\'name\')} found.", "path": str(exe)}\n\n\n@hookimpl\ndef extension_launch(context, manifest, key):\n    if key != manifest.get("key"):\n        return None\n    return {"key": key, "ok": False, "message": f"{manifest.get(\'name\')} is a command-line shuttle pod."}\n\n\n@hookimpl\ndef extension_invoke(context, manifest, key, action, payload):\n    if key != manifest.get("key"):\n        return None\n    return {"key": key, "ok": False, "message": f"{manifest.get(\'name\')} invoke action not implemented yet."}\n'
RIPGREP_PLUGIN = 'from __future__ import annotations\n\nimport subprocess\nfrom pathlib import Path\n\nfrom core_v10.extension_hooks import hookimpl\n\n\ndef _exe(context, manifest) -> Path | None:\n    return context.find_manifest_executable(manifest)\n\n\n@hookimpl\ndef extension_health(context, manifest):\n    if manifest.get("key") != "ripgrep":\n        return None\n    rg = _exe(context, manifest)\n    if not rg:\n        return {"key": "ripgrep", "ok": False, "status": "missing", "message": "rg.exe not found in executable inventory."}\n    try:\n        out = subprocess.run([str(rg), "--version"], capture_output=True, text=True, timeout=3)\n        first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else "ripgrep found"\n        return {"key": "ripgrep", "ok": True, "status": "ready", "message": first, "path": str(rg)}\n    except Exception as exc:\n        return {"key": "ripgrep", "ok": False, "status": "error", "message": str(exc), "path": str(rg)}\n\n\n@hookimpl\ndef extension_launch(context, manifest, key):\n    if key != "ripgrep":\n        return None\n    return {"key": "ripgrep", "ok": False, "message": "ripgrep is a command-line shuttle pod. Use invoke search."}\n\n\n@hookimpl\ndef extension_invoke(context, manifest, key, action, payload):\n    if key != "ripgrep":\n        return None\n\n    rg = _exe(context, manifest)\n    if not rg:\n        return {"key": key, "ok": False, "message": "rg.exe not found."}\n\n    if action != "search":\n        return {"key": key, "ok": False, "message": f"Unsupported ripgrep action: {action}"}\n\n    pattern = str(payload.get("pattern", "")).strip()\n    target = Path(str(payload.get("target", context.foxai_root)))\n\n    if not pattern:\n        return {"key": key, "ok": False, "message": "Missing search pattern."}\n    if not target.exists():\n        return {"key": key, "ok": False, "message": f"Target not found: {target}"}\n\n    cmd = [str(rg), "--line-number", "--hidden", "--glob", "!*.gguf", "--glob", "!*.safetensors", pattern, str(target)]\n\n    try:\n        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)\n        text = (out.stdout or out.stderr or "").strip()\n        return {\n            "key": key,\n            "ok": out.returncode in (0, 1),\n            "status": "complete",\n            "returncode": out.returncode,\n            "command": cmd,\n            "output": text[:8000],\n            "message": "Search complete." if text else "No matches.",\n        }\n    except Exception as exc:\n        return {"key": key, "ok": False, "message": str(exc)}\n'


def _plugin_text(kind: str) -> str:
    if kind == "ripgrep":
        return RIPGREP_PLUGIN
    if kind == "generic_cli":
        return GENERIC_CLI
    return GENERIC_LAUNCHER


def _inventory_names(context: ExtensionContext) -> set[str]:
    return {item["name"].lower() for item in context.executable_inventory()}


def commission_known_extensions(foxai_root: Path, overwrite: bool = False) -> dict[str, Any]:
    context = ExtensionContext(Path(foxai_root).resolve())
    context.ensure_roots()

    inventory_names = _inventory_names(context)
    created = []
    skipped = []
    missing = []

    for sig in SIGNATURES:
        found = any(name.lower() in inventory_names for name in sig["match"])
        if not found:
            missing.append({"key": sig["key"], "name": sig["name"], "reason": "signature executable not found"})
            continue

        ext_dir = context.extensions / sig["department"] / sig["folder"]
        manifest_path = ext_dir / "extension.json"
        plugin_path = ext_dir / "plugin.py"

        if manifest_path.exists() and not overwrite:
            skipped.append({"key": sig["key"], "name": sig["name"], "reason": "already commissioned"})
            continue

        manifest = {
            "schema": 1,
            "key": sig["key"],
            "name": sig["name"],
            "callsign": sig["callsign"],
            "department": sig["department"],
            "category": sig["category"],
            "priority": sig["priority"],
            "portable": True,
            "reserved": False,
            "executables": sig["executables"],
            "capabilities": sig["capabilities"],
            "version": "auto",
            "status": "auto",
            "description": sig["description"],
        }

        write_manifest(manifest_path, manifest)
        plugin_path.write_text(_plugin_text(sig["plugin"]), encoding="utf-8")
        created.append({"key": sig["key"], "name": sig["name"], "callsign": sig["callsign"], "path": str(ext_dir)})

    return {
        "ok": True,
        "created": created,
        "skipped": skipped,
        "missing": missing,
        "inventory_count": len(inventory_names),
    }
