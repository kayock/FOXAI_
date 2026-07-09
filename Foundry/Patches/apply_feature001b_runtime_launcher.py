from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature001b_before_runtime_launcher_{STAMP}"

RUNTIME_LAUNCHER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI_ROOT = Path("Z:/FOXAI")\nGATEWAY_DIR = ROOT / "AI" / "Gateway"\nCONFIG_PATH = GATEWAY_DIR / "gateway_config.json"\nSTATE_PATH = GATEWAY_DIR / "runtime_launcher_state.json"\n\nRUNTIME_NAMES = ["llamafile.exe", "llama-server.exe", "server.exe", "llama.cpp.exe"]\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef load_config():\n    return load_json(CONFIG_PATH, {})\n\ndef find_runtimes():\n    found = []\n    if not FOXAI_ROOT.exists():\n        return found\n    for exe in FOXAI_ROOT.rglob("*.exe"):\n        name = exe.name.lower()\n        if name in RUNTIME_NAMES or "llama" in name or "llamafile" in name:\n            try:\n                found.append({\n                    "name": exe.name,\n                    "path": str(exe),\n                    "modified": datetime.datetime.fromtimestamp(exe.stat().st_mtime).isoformat(timespec="seconds")\n                })\n            except Exception:\n                pass\n    return sorted(found, key=lambda x: x["name"].lower())\n\ndef selected_model():\n    cfg = load_config()\n    p = cfg.get("selected_model_path")\n    if p and Path(p).exists():\n        return {"name": Path(p).name, "path": p}\n    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"\n    data = load_json(inv, {})\n    models = data.get("assets", {}).get("llms", [])\n    if models:\n        m = models[0]\n        return {"name": m.get("name"), "path": m.get("path")}\n    return None\n\ndef runtime_health():\n    base = load_config().get("runtime_base", "http://127.0.0.1:8845")\n    for url in [base + "/v1/models", base + "/health", base]:\n        try:\n            with urllib.request.urlopen(url, timeout=2) as res:\n                return {"online": True, "message": f"responded at {url}", "base": base}\n        except Exception:\n            pass\n    return {"online": False, "message": "runtime offline", "base": base}\n\ndef choose_runtime():\n    runtimes = find_runtimes()\n    if not runtimes:\n        return None\n    for rt in runtimes:\n        if "llamafile" in rt["name"].lower():\n            return rt\n    for rt in runtimes:\n        if "llama-server" in rt["name"].lower():\n            return rt\n    return runtimes[0]\n\ndef build_command():\n    rt = choose_runtime()\n    model = selected_model()\n    if not rt or not model:\n        return None\n\n    exe = rt["path"]\n    model_path = model["path"]\n    lower = Path(exe).name.lower()\n\n    if "llamafile" in lower:\n        args = [exe, "-m", model_path, "--server", "--host", "127.0.0.1", "--port", "8845"]\n    else:\n        args = [exe, "-m", model_path, "--host", "127.0.0.1", "--port", "8845"]\n\n    return {\n        "runtime": rt,\n        "model": model,\n        "args": args,\n        "display": " ".join(f\'"{a}"\' if " " in a else a for a in args)\n    }\n\ndef write_launcher_bat():\n    cmd = build_command()\n    GATEWAY_DIR.mkdir(parents=True, exist_ok=True)\n    if not cmd:\n        content = (\n            "@echo off\\n"\n            "title KayocktheOS Runtime Launcher\\n"\n            "color 0C\\n"\n            "echo Runtime or model not found.\\n"\n            "echo.\\n"\n            "echo Put llamafile.exe or llama-server.exe somewhere under Z:\\\\FOXAI.\\n"\n            "echo Make sure FOXAI Discovery found at least one GGUF model.\\n"\n            "pause\\n"\n        )\n        (GATEWAY_DIR / "LAUNCH_SELECTED_MODEL_RUNTIME.bat").write_text(content, encoding="utf-8")\n        return {"ok": False, "message": "runtime or model missing"}\n\n    lines = [\n        "@echo off",\n        "title KayocktheOS Selected Model Runtime",\n        "color 0A",\n        "echo ==========================================",\n        "echo KayocktheOS Local AI Runtime",\n        "echo ==========================================",\n        "echo.",\n        f"echo Runtime: {cmd[\'runtime\'][\'name\']}",\n        f"echo Model: {cmd[\'model\'][\'name\']}",\n        "echo Port: 8845",\n        "echo.",\n        "echo Leave this window open while chatting.",\n        "echo.",\n        cmd["display"],\n        "pause",\n        ""\n    ]\n    (GATEWAY_DIR / "LAUNCH_SELECTED_MODEL_RUNTIME.bat").write_text("\\n".join(lines), encoding="utf-8")\n    return {"ok": True, "launcher": "AI/Gateway/LAUNCH_SELECTED_MODEL_RUNTIME.bat", "command": cmd}\n\ndef status():\n    launch = write_launcher_bat()\n    payload = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 001B - Runtime Auto Launcher",\n        "foxai_root": str(FOXAI_ROOT),\n        "runtimes_found": find_runtimes(),\n        "selected_runtime": choose_runtime(),\n        "selected_model": selected_model(),\n        "launch": launch,\n        "health": runtime_health()\n    }\n    save_json(STATE_PATH, payload)\n    return payload\n\nif __name__ == "__main__":\n    print(json.dumps(status(), indent=2))\n'

def info(msg):
    print(f"[Feature 001B Runtime Launcher] {msg}")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def copy_item(src_rel):
    src = ROOT / src_rel
    if not src.exists():
        return
    dst = BACKUP_DIR / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_feature():
    write_text("AI/runtime_launcher.py", RUNTIME_LAUNCHER_PY)
    spec = importlib.util.spec_from_file_location("kayock_runtime_launcher", ROOT / "AI/runtime_launcher.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    payload = mod.status()
    info(f"Runtime candidates found: {len(payload['runtimes_found'])}")
    info("Launch helper written: AI\\Gateway\\LAUNCH_SELECTED_MODEL_RUNTIME.bat")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; Runtime Launcher installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def runtime_launcher_status(" not in old:
        insert = """
def runtime_launcher_status():
    try:
        feature = ROOT / "AI" / "runtime_launcher.py"
        if feature.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_runtime_launcher", feature)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"error": str(exc), "configured": False}
    return {"configured": False, "message": "Runtime launcher missing"}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"runtime_launcher": runtime_launcher_status(),' not in old:
        if '"local_chat": local_chat_status(),' in old:
            old = old.replace('"local_chat": local_chat_status(),', '"local_chat": local_chat_status(),\n        "runtime_launcher": runtime_launcher_status(),')
        elif '"local_runtime": local_runtime_health(),' in old:
            old = old.replace('"local_runtime": local_runtime_health(),', '"local_runtime": local_runtime_health(),\n        "runtime_launcher": runtime_launcher_status(),')

    if 'elif path == "/api/runtime-launcher":' not in old:
        if 'elif path == "/api/local-chat":' in old:
            old = old.replace(
                'elif path == "/api/local-chat":\n            self._json(local_chat_status())',
                'elif path == "/api/local-chat":\n            self._json(local_chat_status())\n        elif path == "/api/runtime-launcher":\n            self._json(runtime_launcher_status())'
            )
        elif 'elif path == "/api/runtime":' in old:
            old = old.replace(
                'elif path == "/api/runtime":\n            self._json(local_runtime_health())',
                'elif path == "/api/runtime":\n            self._json(local_runtime_health())\n        elif path == "/api/runtime-launcher":\n            self._json(runtime_launcher_status())'
            )

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/runtime-launcher.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_001b_runtime_launcher: enabled" not in text:
        text += "\n  feature_001b_runtime_launcher: enabled\n" if "features:" in text else "\nfeatures:\n  feature_001b_runtime_launcher: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_001B_RUNTIME_LAUNCHER.md", """# Feature 001B - Runtime Auto Launcher

This feature searches `Z:\\FOXAI` for runtime executables and creates a launch helper.

## API

```text
http://127.0.0.1:8844/api/runtime-launcher
```

## Launch helper

```text
Z:\\KayocktheOS\\AI\\Gateway\\LAUNCH_SELECTED_MODEL_RUNTIME.bat
```

Run that BAT, leave the runtime window open, then test chat through `/api/chat`.

## Notes

This does not silently start executables. The Operator launches the runtime explicitly.
""")
    write_text("Forge/Decisions/0017_feature_001b_runtime_launcher.md", """# Decision 0017 - Feature 001B Runtime Launcher

Runtime startup remains Operator-visible.

KayocktheOS can generate the command, but the Operator launches the model runtime until we have a GUI approval flow.
""")
    write_text("Foundry/Releases/feature001b_runtime_launcher_notes.md", "# Feature 001B - Runtime Launcher\n\nAdds runtime discovery and launch helper.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 001B - Runtime Auto Launcher\n\n- Added `AI/runtime_launcher.py`.\n- Added `/api/runtime-launcher`.\n- Added `AI/Gateway/LAUNCH_SELECTED_MODEL_RUNTIME.bat`.\n- Runtime launch remains Operator-visible.\n"
    if "Feature 001B - Runtime Auto Launcher" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_feature()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 001B Runtime Launcher patch complete.")
    info("Restart KayocktheOS and test /api/runtime-launcher.")
    info("Then run AI\\Gateway\\LAUNCH_SELECTED_MODEL_RUNTIME.bat.")

if __name__ == "__main__":
    main()
