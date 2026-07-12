from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature001_before_local_chat_{STAMP}"

LOCAL_CHAT_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport subprocess\nimport sys\nimport urllib.request\nimport urllib.error\nimport time\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI_ROOT = Path("Z:/FOXAI")\nGATEWAY_DIR = ROOT / "AI" / "Gateway"\nCONFIG_PATH = GATEWAY_DIR / "gateway_config.json"\nCHAT_STATE = GATEWAY_DIR / "local_chat_state.json"\n\nDEFAULT_CONFIG = {\n    "mode": "advisor_only",\n    "write_access": False,\n    "operator_approval_required": True,\n    "active_runtime": "openai_compatible",\n    "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n    "runtime_base": "http://127.0.0.1:8845",\n    "active_chat_model": "local-model",\n    "selected_model_path": None,\n    "timeout_seconds": 180,\n    "temperature": 0.4,\n    "max_tokens": 1024,\n    "runtime_command": None\n}\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef load_config():\n    config = {**DEFAULT_CONFIG, **load_json(CONFIG_PATH, {})}\n    save_json(CONFIG_PATH, config)\n    return config\n\ndef foxai_models():\n    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"\n    data = load_json(inv, None)\n    if data:\n        return data.get("assets", {}).get("llms", [])\n    if not FOXAI_ROOT.exists():\n        return []\n    models = []\n    for p in FOXAI_ROOT.rglob("*.gguf"):\n        try:\n            models.append({\n                "name": p.name,\n                "path": str(p),\n                "size_gb": round(p.stat().st_size / (1024**3), 3),\n                "capabilities": infer_caps(p.name)\n            })\n        except Exception:\n            pass\n    return sorted(models, key=lambda x: x["name"].lower())\n\ndef infer_caps(name):\n    n = name.lower()\n    caps = ["chat"]\n    if "coder" in n or "code" in n:\n        caps.append("coding")\n    if "deepseek" in n or "r1" in n:\n        caps.append("reasoning")\n    if "vl" in n or "vision" in n:\n        caps.append("vision")\n    return sorted(set(caps))\n\ndef recommend_default_model():\n    models = foxai_models()\n    if not models:\n        return None\n    scored = []\n    for m in models:\n        name = m.get("name","").lower()\n        score = 0\n        if "deepseek" in name and "14b" in name:\n            score += 10\n        if "qwen" in name and ("8b" in name or "q4" in name):\n            score += 8\n        if "q4" in name:\n            score += 5\n        if "coder" in name:\n            score += 3\n        if "32b" in name or "30b" in name:\n            score -= 4\n        scored.append((score, m))\n    return sorted(scored, key=lambda x: (-x[0], x[1].get("size_gb", 999)))[0][1]\n\ndef configure_default():\n    config = load_config()\n    if not config.get("selected_model_path"):\n        model = recommend_default_model()\n        if model:\n            config["selected_model_path"] = model["path"]\n            config["active_chat_model"] = model["name"]\n    save_json(CONFIG_PATH, config)\n    return config\n\ndef runtime_health():\n    config = load_config()\n    base = config.get("runtime_base") or "http://127.0.0.1:8845"\n    for url in [base + "/v1/models", base + "/health", base]:\n        try:\n            with urllib.request.urlopen(url, timeout=2) as res:\n                return {"online": True, "message": f"responded at {url}", "base": base}\n        except Exception:\n            pass\n    return {"online": False, "message": "runtime offline", "base": base}\n\ndef write_launch_files():\n    config = configure_default()\n    model_path = config.get("selected_model_path") or "PASTE_MODEL_PATH_HERE.gguf"\n    launch_dir = ROOT / "AI" / "Gateway"\n    launch_dir.mkdir(parents=True, exist_ok=True)\n\n    bat = f\'\'\'@echo off\ntitle KayocktheOS Local Chat Runtime\ncolor 0A\necho ==========================================\necho KayocktheOS Local Chat Runtime\necho ==========================================\necho.\necho This starter expects an OpenAI-compatible local server on port 8845.\necho.\necho Selected model:\necho {model_path}\necho.\necho Option A: If using llamafile, run something like:\necho llamafile.exe -m "{model_path}" --server --host 127.0.0.1 --port 8845\necho.\necho Option B: If using llama.cpp server, run something like:\necho llama-server.exe -m "{model_path}" --host 127.0.0.1 --port 8845\necho.\necho After the runtime is started, test:\necho http://127.0.0.1:8844/api/runtime\necho.\npause\n\'\'\'\n    (launch_dir / "START_LOCAL_CHAT_RUNTIME.bat").write_text(bat, encoding="utf-8")\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "selected_model_path": model_path,\n        "selected_model_name": config.get("active_chat_model"),\n        "runtime_base": config.get("runtime_base"),\n        "health": runtime_health(),\n        "note": "This feature creates launch guidance first. Automatic process launch comes after we confirm the runtime executable path."\n    }\n    save_json(CHAT_STATE, state)\n    return state\n\ndef chat_status():\n    config = configure_default()\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 001 - Local Chat",\n        "configured": bool(config.get("selected_model_path")),\n        "selected_model": config.get("active_chat_model"),\n        "selected_model_path": config.get("selected_model_path"),\n        "runtime": runtime_health(),\n        "available_models": foxai_models()[:20],\n        "launch_helper": "AI/Gateway/START_LOCAL_CHAT_RUNTIME.bat"\n    }\n\nif __name__ == "__main__":\n    write_launch_files()\n    print(json.dumps(chat_status(), indent=2))\n'

def info(msg):
    print(f"[Feature 001 Local Chat] {msg}")

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
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE","Shell"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_feature():
    write_text("AI/local_chat.py", LOCAL_CHAT_PY)
    spec = importlib.util.spec_from_file_location("kayock_local_chat", ROOT / "AI/local_chat.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_launch_files()
    info("Local Chat launch helper written.")
    info("Selected model: " + str(state.get("selected_model_name")))

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; Local Chat installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def local_chat_status(" not in old:
        insert = """
def local_chat_status():
    try:
        feature = ROOT / "AI" / "local_chat.py"
        if feature.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_chat", feature)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat_status()
    except Exception as exc:
        return {"error": str(exc), "configured": False}
    return {"configured": False, "message": "Local Chat feature missing"}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"local_chat": local_chat_status(),' not in old:
        if '"local_runtime": local_runtime_health(),' in old:
            old = old.replace('"local_runtime": local_runtime_health(),', '"local_runtime": local_runtime_health(),\n        "local_chat": local_chat_status(),')
        elif '"ai_gateway": ai_gateway_status(),' in old:
            old = old.replace('"ai_gateway": ai_gateway_status(),', '"ai_gateway": ai_gateway_status(),\n        "local_chat": local_chat_status(),')

    if 'elif path == "/api/local-chat":' not in old:
        if 'elif path == "/api/runtime":' in old:
            old = old.replace(
                'elif path == "/api/runtime":\n            self._json(local_runtime_health())',
                'elif path == "/api/runtime":\n            self._json(local_runtime_health())\n        elif path == "/api/local-chat":\n            self._json(local_chat_status())'
            )
        else:
            old = old.replace(
                'elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())',
                'elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())\n        elif path == "/api/local-chat":\n            self._json(local_chat_status())'
            )

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/local-chat.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        if "feature_001_local_chat: enabled" not in text:
            text += "\n  feature_001_local_chat: enabled\n" if "features:" in text else "\nfeatures:\n  feature_001_local_chat: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_001_LOCAL_CHAT.md", """# Feature 001 - Local Chat

This is the first complete feature target for KayocktheOS.

## Goal

A local model answers through:

```text
POST http://127.0.0.1:8844/api/chat
```

## What this patch adds

- `AI/local_chat.py`
- `/api/local-chat`
- `AI/Gateway/START_LOCAL_CHAT_RUNTIME.bat`
- automatic suggested model selection from FOXAI inventory

## Manual runtime start

Open:

```text
Z:\\KayocktheOS\\AI\\Gateway\\START_LOCAL_CHAT_RUNTIME.bat
```

It shows the exact model selected and the expected llamafile or llama.cpp command shape.

## Next confirmation needed

We still need the actual runtime executable path, such as:

```text
Z:\\FOXAI\\llamafile.exe
```

or:

```text
Z:\\FOXAI\\llama.cpp\\llama-server.exe
```
""")
    write_text("Forge/Decisions/0016_feature_001_local_chat.md", """# Decision 0016 - Feature 001 Local Chat

The first complete feature is Local Chat.

It must be visible through the Bridge, use the AI Gateway, and require no automatic project writes.
""")
    write_text("Foundry/Releases/feature001_local_chat_notes.md", "# Feature 001 - Local Chat\n\nAdds model selection status and runtime launch helper.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 001 - Local Chat\n\n- Added `AI/local_chat.py`.\n- Added `/api/local-chat`.\n- Added local runtime launch helper.\n- Starts the first integrated, demonstrable feature milestone.\n"
    if "Feature 001 - Local Chat" not in old:
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
    info("Feature 001 Local Chat patch complete.")
    info("Restart KayocktheOS and test /api/local-chat.")
    info("Then open AI\\Gateway\\START_LOCAL_CHAT_RUNTIME.bat.")

if __name__ == "__main__":
    main()
