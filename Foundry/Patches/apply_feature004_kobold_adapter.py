from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature004_before_kobold_adapter_{STAMP}"

KOBOLD_ADAPTER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nENGINE_DIR = ROOT / "Engine" / "KoboldCpp"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "engine_adapter_config.json"\nSTATE = GATEWAY / "kobold_adapter_state.json"\n\nKOBOLD_EXE_CANDIDATES = [\n    ENGINE_DIR / "koboldcpp.exe",\n    FOXAI / "Engine" / "koboldcpp.exe",\n    FOXAI / "koboldcpp.exe",\n]\n\nKNOWN_GOOD_MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"\nFALLBACK_MODELS = [\n    FOXAI / "Models" / "Chat" / "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",\n    FOXAI / "Models" / "Chat" / "Qwen3VL-8B-Instruct-Q4_K_M.gguf",\n]\n\nHOST = "127.0.0.1"\nPORT = 5001\nCONTEXT = 4096\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef quote(value):\n    return \'"\' + str(value).replace(\'"\', \'\') + \'"\'\n\ndef find_kobold_exe():\n    for p in KOBOLD_EXE_CANDIDATES:\n        if p.exists():\n            return p\n    for base in [ENGINE_DIR, FOXAI]:\n        if base.exists():\n            for p in base.rglob("koboldcpp*.exe"):\n                return p\n    return None\n\ndef find_model():\n    if KNOWN_GOOD_MODEL.exists():\n        return KNOWN_GOOD_MODEL\n    for p in FALLBACK_MODELS:\n        if p.exists():\n            return p\n    chat = FOXAI / "Models" / "Chat"\n    if chat.exists():\n        models = sorted(chat.glob("*.gguf"), key=lambda x: x.name.lower())\n        if models:\n            return models[0]\n    if FOXAI.exists():\n        models = sorted(FOXAI.rglob("*.gguf"), key=lambda x: x.name.lower())\n        if models:\n            return models[0]\n    return None\n\ndef probe(url):\n    try:\n        with urllib.request.urlopen(url, timeout=3) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n            try:\n                parsed = json.loads(raw)\n            except Exception:\n                parsed = raw[:800]\n            return {"ok": True, "status": res.status, "response": parsed}\n    except Exception as exc:\n        return {"ok": False, "error": str(exc)}\n\ndef kobold_health():\n    base = f"http://{HOST}:{PORT}"\n    checks = {\n        "root": probe(base),\n        "api_v1_model": probe(base + "/api/v1/model"),\n        "api_v1_info_version": probe(base + "/api/v1/info/version"),\n        "openai_models": probe(base + "/v1/models"),\n    }\n    online = any(v.get("ok") for v in checks.values())\n    return {"online": online, "base": base, "checks": checks}\n\ndef write_config_and_launcher():\n    exe = find_kobold_exe()\n    model = find_model()\n    base = f"http://{HOST}:{PORT}"\n\n    config = {\n        "adapter": "koboldcpp",\n        "engine_name": "KoboldCpp",\n        "host": HOST,\n        "port": PORT,\n        "base_url": base,\n        "openai_base_url": base + "/v1",\n        "kobold_api_url": base + "/api/v1",\n        "selected_engine_path": str(exe) if exe else None,\n        "selected_model_path": str(model) if model else None,\n        "context_tokens": CONTEXT,\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n        "notes": "KayocktheOS talks through this adapter. KoboldCpp owns GGUF runtime loading."\n    }\n    save_json(CONFIG, config)\n\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    if not exe:\n        launcher = f"""@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0C\necho KoboldCpp was not found.\necho.\necho Put koboldcpp.exe here:\necho {ENGINE_DIR}\necho.\npause\n"""\n    elif not model:\n        launcher = """@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0C\necho No GGUF model found.\necho Expected model folder:\necho Z:\\FOXAI\\Models\\Chat\npause\n"""\n    else:\n        cmd = f\'{quote(exe)} --model {quote(model)} --host {HOST} --port {PORT} --contextsize {CONTEXT}\'\n        launcher = f"""@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0A\necho ==========================================\necho KayocktheOS KoboldCpp Engine Adapter\necho ==========================================\necho.\necho Engine:\necho {exe}\necho.\necho Model:\necho {model}\necho.\necho Server:\necho {base}\necho.\necho Context:\necho {CONTEXT}\necho.\necho Leave this window open.\necho When KoboldCpp finishes loading, return to the Bridge.\necho.\n{cmd}\npause\n"""\n    launcher_path = GATEWAY / "START_KOBOLD_ENGINE.bat"\n    launcher_path.write_text(launcher, encoding="utf-8")\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 004 - Kobold Engine Adapter",\n        "engine_path": str(exe) if exe else None,\n        "engine_exists": bool(exe),\n        "model_path": str(model) if model else None,\n        "model_exists": bool(model),\n        "launcher": str(launcher_path),\n        "health": kobold_health(),\n        "config": str(CONFIG),\n        "manual_install_note": "Download/copy koboldcpp.exe into Z:\\\\KayocktheOS\\\\Engine\\\\KoboldCpp\\\\koboldcpp.exe if not found."\n    }\n    save_json(STATE, state)\n    return state\n\ndef chat(prompt):\n    cfg = load_json(CONFIG, {})\n    base = cfg.get("base_url", f"http://{HOST}:{PORT}")\n    payload = {"prompt": prompt, "max_length": 512, "temperature": 0.4}\n    try:\n        req = urllib.request.Request(\n            base + "/api/v1/generate",\n            data=json.dumps(payload).encode("utf-8"),\n            headers={"Content-Type": "application/json"},\n            method="POST"\n        )\n        with urllib.request.urlopen(req, timeout=180) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n        data = json.loads(raw)\n        text = ""\n        if isinstance(data, dict):\n            results = data.get("results")\n            if isinstance(results, list) and results:\n                text = results[0].get("text", "")\n            text = text or data.get("text", "") or raw\n        return {"ok": True, "response": text, "raw": data, "engine": "koboldcpp"}\n    except Exception as exc:\n        return {"ok": False, "message": "KoboldCpp did not answer. Start AI\\\\Gateway\\\\START_KOBOLD_ENGINE.bat and wait for loading to complete.", "error": str(exc)}\n\nif __name__ == "__main__":\n    print(json.dumps(write_config_and_launcher(), indent=2))\n'
BRIDGE_NOTICE = '\n// Feature 004 Kobold Engine Adapter notice\nfunction renderKoboldAdapterNotice() {\n  const panel = document.getElementById(\'firstContactPanel\');\n  if (!panel || document.getElementById(\'koboldAdapterNotice\')) return;\n  const div = document.createElement(\'div\');\n  div.id = \'koboldAdapterNotice\';\n  div.className = \'diagnosticHint\';\n  div.innerHTML = \'<strong>Kobold Engine Adapter:</strong> Run <span class="pathText">Z:\\\\\\\\KayocktheOS\\\\\\\\AI\\\\\\\\Gateway\\\\\\\\START_KOBOLD_ENGINE.bat</span>, then ask the Academy.\';\n  panel.appendChild(div);\n}\n'

def info(msg):
    print(f"[Feature 004 Kobold Adapter] {msg}")

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

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["AI","Engine","Bridge","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_adapter():
    write_text("AI/kobold_engine_adapter.py", KOBOLD_ADAPTER_PY)
    (ROOT / "Engine" / "KoboldCpp").mkdir(parents=True, exist_ok=True)

    spec = importlib.util.spec_from_file_location("kobold_adapter", ROOT / "AI/kobold_engine_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_config_and_launcher()

    info("Engine path: " + str(state.get("engine_path")))
    info("Model path: " + str(state.get("model_path")))
    info("Launcher: AI\\Gateway\\START_KOBOLD_ENGINE.bat")

def patch_core_api():
    path = ROOT / "System" / "API" / "core_api.py"
    if not path.exists():
        info("Core API not found; adapter installed without API patch.")
        return

    old = path.read_text(encoding="utf-8", errors="replace")

    if "def kobold_adapter_status(" not in old:
        insert = """
def kobold_adapter_status():
    try:
        adapter = ROOT / "AI" / "kobold_engine_adapter.py"
        if adapter.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kobold_adapter", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_config_and_launcher()
    except Exception as exc:
        return {{"online": False, "error": str(exc)}}
    return {{"online": False, "message": "Kobold adapter missing"}}

def kobold_adapter_chat(prompt=""):
    try:
        adapter = ROOT / "AI" / "kobold_engine_adapter.py"
        if adapter.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kobold_adapter", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt)
    except Exception as exc:
        return {{"ok": False, "error": str(exc)}}
    return {{"ok": False, "message": "Kobold adapter missing"}}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"kobold_adapter": kobold_adapter_status(),' not in old:
        if '"first_contact": first_contact_status(),' in old:
            old = old.replace('"first_contact": first_contact_status(),', '"first_contact": first_contact_status(),\n        "kobold_adapter": kobold_adapter_status(),')
        elif '"local_chat": local_chat_status(),' in old:
            old = old.replace('"local_chat": local_chat_status(),', '"local_chat": local_chat_status(),\n        "kobold_adapter": kobold_adapter_status(),')

    if 'elif path == "/api/kobold":' not in old:
        if 'elif path == "/api/first-contact":' in old:
            old = old.replace('elif path == "/api/first-contact":\n            self._json(first_contact_status())',
                              'elif path == "/api/first-contact":\n            self._json(first_contact_status())\n        elif path == "/api/kobold":\n            self._json(kobold_adapter_status())')
        elif 'elif path == "/api/runtime":' in old:
            old = old.replace('elif path == "/api/runtime":\n            self._json(local_runtime_health())',
                              'elif path == "/api/runtime":\n            self._json(local_runtime_health())\n        elif path == "/api/kobold":\n            self._json(kobold_adapter_status())')

    old = old.replace('self._json(first_contact_chat(payload.get("prompt", "")))',
                      'self._json(kobold_adapter_chat(payload.get("prompt", "")))')
    old = old.replace('self._json(ai_chat(payload.get("prompt", ""), payload.get("context")))',
                      'self._json(kobold_adapter_chat(payload.get("prompt", "")))')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/kobold and Kobold-backed /api/chat.")

def patch_bridge():
    renderer = ROOT / "Bridge" / "renderer.js"
    if not renderer.exists():
        return
    old = renderer.read_text(encoding="utf-8", errors="replace")
    if "Feature 004 Kobold Engine Adapter notice" not in old:
        old = old.rstrip() + "\n\n" + BRIDGE_NOTICE
    if "renderKoboldAdapterNotice();" not in old:
        old = old.replace("renderNotifications();", "renderNotifications();\n  renderKoboldAdapterNotice();")
    renderer.write_text(old, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_004_kobold_engine_adapter: enabled" not in text:
        text += "\n  feature_004_kobold_engine_adapter: enabled\n" if "features:" in text else "\nfeatures:\n  feature_004_kobold_engine_adapter: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_004_KOBOLD_ENGINE_ADAPTER.md", """# Feature 004 - Kobold Engine Adapter

This pivots KayocktheOS away from owning the AI runtime directly.

## Design

```text
KayocktheOS Bridge
    ↓
Core API
    ↓
Engine Adapter
    ↓
KoboldCpp
    ↓
GGUF Models in FOXAI
```

## Expected engine path

```text
Z:\\KayocktheOS\\Engine\\KoboldCpp\\koboldcpp.exe
```

## Launcher

```text
Z:\\KayocktheOS\\AI\\Gateway\\START_KOBOLD_ENGINE.bat
```
""")
    write_text("Forge/Decisions/0036_kobold_engine_adapter.md", """# Decision 0036 - Kobold Engine Adapter

KayocktheOS should not depend on one runtime.

The engine should be replaceable through adapters. First supported adapter: KoboldCpp.
""")
    write_text("Foundry/Releases/feature004_kobold_engine_adapter_notes.md", "# Feature 004 - Kobold Engine Adapter\n\nAdds KoboldCpp adapter, launcher, config, and API route.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 004 - Kobold Engine Adapter\n\n- Added `AI/kobold_engine_adapter.py`.\n- Added `AI/Gateway/START_KOBOLD_ENGINE.bat`.\n- Added adapter config `AI/Gateway/engine_adapter_config.json`.\n- Added `/api/kobold` where Core API patch is available.\n- Routed `/api/chat` toward Kobold adapter where possible.\n"
    if "Feature 004 - Kobold Engine Adapter" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_adapter()
    patch_core_api()
    patch_bridge()
    update_manifest()
    docs()
    changelog()
    info("Feature 004 Kobold Engine Adapter complete.")
    info("Next: put koboldcpp.exe in Engine\\KoboldCpp if missing, then run AI\\Gateway\\START_KOBOLD_ENGINE.bat.")

if __name__ == "__main__":
    main()
