from __future__ import annotations

from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parent
EXTENSIONS = ROOT / "Extensions"

SAFE_GENERIC_LAUNCHER = 'from __future__ import annotations\n\nimport subprocess\nfrom pathlib import Path\n\nfrom core_v10.extension_hooks import hookimpl\n\n\ndef _exe(context, manifest) -> Path | None:\n    return context.find_manifest_executable(manifest)\n\n\n@hookimpl\ndef extension_health(context, manifest):\n    # SAFE HEALTH CHECK: never launches GUI apps.\n    exe = _exe(context, manifest)\n    key = manifest.get("key")\n    if not exe:\n        return {\n            "key": key,\n            "ok": False,\n            "status": "missing",\n            "message": f"No executable found for {manifest.get(\'executables\', [])}."\n        }\n\n    return {\n        "key": key,\n        "ok": True,\n        "status": "ready",\n        "message": f"{manifest.get(\'name\')} found.",\n        "path": str(exe)\n    }\n\n\n@hookimpl\ndef extension_launch(context, manifest, key):\n    # EXPLICIT LAUNCH ONLY.\n    if key != manifest.get("key"):\n        return None\n\n    exe = _exe(context, manifest)\n    if not exe:\n        return {"key": key, "ok": False, "message": "Executable not found."}\n\n    try:\n        subprocess.Popen([str(exe)], cwd=str(exe.parent))\n        return {"key": key, "ok": True, "message": f"Launched {manifest.get(\'name\')}."}\n    except Exception as exc:\n        return {"key": key, "ok": False, "message": str(exc)}\n\n\n@hookimpl\ndef extension_invoke(context, manifest, key, action, payload):\n    if key != manifest.get("key"):\n        return None\n    return {\n        "key": key,\n        "ok": False,\n        "message": f"{manifest.get(\'name\')} does not support invoke action yet."\n    }\n'
SAFE_GENERIC_CLI = 'from __future__ import annotations\n\nimport subprocess\nfrom pathlib import Path\n\nfrom core_v10.extension_hooks import hookimpl\n\n\ndef _exe(context, manifest) -> Path | None:\n    return context.find_manifest_executable(manifest)\n\n\n@hookimpl\ndef extension_health(context, manifest):\n    # SAFE CLI HEALTH CHECK: --version is okay for terminal tools.\n    exe = _exe(context, manifest)\n    key = manifest.get("key")\n    if not exe:\n        return {\n            "key": key,\n            "ok": False,\n            "status": "missing",\n            "message": f"No executable found for {manifest.get(\'executables\', [])}."\n        }\n\n    try:\n        out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=5)\n        first = (out.stdout or out.stderr or f"{manifest.get(\'name\')} found").splitlines()[0]\n        return {"key": key, "ok": True, "status": "ready", "message": first, "path": str(exe)}\n    except Exception:\n        return {"key": key, "ok": True, "status": "ready", "message": f"{manifest.get(\'name\')} found.", "path": str(exe)}\n\n\n@hookimpl\ndef extension_launch(context, manifest, key):\n    if key != manifest.get("key"):\n        return None\n    return {"key": key, "ok": False, "message": f"{manifest.get(\'name\')} is a command-line shuttle pod."}\n\n\n@hookimpl\ndef extension_invoke(context, manifest, key, action, payload):\n    if key != manifest.get("key"):\n        return None\n    return {"key": key, "ok": False, "message": f"{manifest.get(\'name\')} invoke action not implemented yet."}\n'


def backup(path: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b = path.with_name(f"{path.stem}_backup_before_safe_fleet_{stamp}{path.suffix}")
    shutil.copy2(path, b)
    return b


def patch_plugin(key: str, safe_text: str) -> dict:
    for manifest_path in EXTENSIONS.rglob("extension.json"):
        try:
            text = manifest_path.read_text(encoding="utf-8", errors="replace")
            if f'"key": "{key}"' not in text and f'"key":"{key}"' not in text:
                continue

            plugin_path = manifest_path.parent / "plugin.py"
            if not plugin_path.exists():
                return {"key": key, "ok": False, "message": f"No plugin.py found beside {manifest_path}"}

            b = backup(plugin_path)
            plugin_path.write_text(safe_text, encoding="utf-8")
            return {"key": key, "ok": True, "message": f"Patched {plugin_path}", "backup": str(b)}
        except Exception as exc:
            return {"key": key, "ok": False, "message": str(exc)}

    return {"key": key, "ok": False, "message": "Extension manifest not found."}


def main() -> int:
    if not EXTENSIONS.exists():
        print("[ERROR] Extensions folder not found.")
        return 1

    print("FOXAI CM v2.3a Safe Fleet Operations")
    print("====================================")
    print()

    results = [
        patch_plugin("everything", SAFE_GENERIC_LAUNCHER),
        patch_plugin("winmerge", SAFE_GENERIC_LAUNCHER),
        patch_plugin("tree_sitter", SAFE_GENERIC_CLI),
    ]

    for r in results:
        print(f"{r['key']}: {r['message']}")
        if r.get("backup"):
            print(f"  backup: {r['backup']}")

    print()
    print("Now run TEST_FLEET_REGISTRY.bat again.")
    print("Expected: Fleet Registry refreshes without opening WinMerge or other GUI apps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
