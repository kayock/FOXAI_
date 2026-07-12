from pathlib import Path
import shutil
import datetime
import importlib.util
import py_compile

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature004c_before_kobold_core_repair_{STAMP}"

ADAPTER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\nimport urllib.error\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nENGINE_DIR = ROOT / "Engine" / "KoboldCpp"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "engine_adapter_config.json"\nSTATE = GATEWAY / "kobold_adapter_state.json"\n\nHOST = "127.0.0.1"\nPORT = 5001\nCONTEXT = 4096\nBASE_URL = f"http://{HOST}:{PORT}"\n\nKOBOLD_EXE_CANDIDATES = [\n    ENGINE_DIR / "koboldcpp.exe",\n    FOXAI / "Engine" / "koboldcpp.exe",\n    FOXAI / "koboldcpp.exe",\n]\n\nKNOWN_GOOD_MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef quote(value):\n    return \'"\' + str(value).replace(\'"\', \'\') + \'"\'\n\ndef find_kobold_exe():\n    for p in KOBOLD_EXE_CANDIDATES:\n        if p.exists():\n            return p\n    for base in [ENGINE_DIR, FOXAI]:\n        if base.exists():\n            for p in base.rglob("koboldcpp*.exe"):\n                return p\n    return None\n\ndef find_model():\n    if KNOWN_GOOD_MODEL.exists():\n        return KNOWN_GOOD_MODEL\n    chat = FOXAI / "Models" / "Chat"\n    if chat.exists():\n        # Avoid choosing vision models as the default chat engine.\n        candidates = [p for p in chat.glob("*.gguf") if "vl" not in p.name.lower() and "vision" not in p.name.lower()]\n        if candidates:\n            return sorted(candidates, key=lambda x: x.name.lower())[0]\n        models = sorted(chat.glob("*.gguf"), key=lambda x: x.name.lower())\n        if models:\n            return models[0]\n    if FOXAI.exists():\n        models = sorted(FOXAI.rglob("*.gguf"), key=lambda x: x.name.lower())\n        if models:\n            return models[0]\n    return None\n\ndef probe(url, timeout=3):\n    try:\n        with urllib.request.urlopen(url, timeout=timeout) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n            try:\n                parsed = json.loads(raw)\n            except Exception:\n                parsed = raw[:800]\n            return {"ok": True, "status": res.status, "response": parsed}\n    except Exception as exc:\n        return {"ok": False, "error": str(exc)}\n\ndef post_json(url, payload, timeout=180):\n    req = urllib.request.Request(\n        url,\n        data=json.dumps(payload).encode("utf-8"),\n        headers={"Content-Type": "application/json"},\n        method="POST"\n    )\n    with urllib.request.urlopen(req, timeout=timeout) as res:\n        raw = res.read().decode("utf-8", errors="replace")\n    try:\n        return json.loads(raw)\n    except Exception:\n        return {"text": raw}\n\ndef kobold_health():\n    checks = {\n        "root": probe(BASE_URL),\n        "kobold_model": probe(BASE_URL + "/api/v1/model"),\n        "kobold_version": probe(BASE_URL + "/api/v1/info/version"),\n        "openai_models": probe(BASE_URL + "/v1/models"),\n    }\n    online = any(v.get("ok") for v in checks.values())\n    return {"online": online, "base": BASE_URL, "checks": checks}\n\ndef write_config_and_launcher():\n    exe = find_kobold_exe()\n    model = find_model()\n\n    config = {\n        "adapter": "koboldcpp",\n        "engine_name": "KoboldCpp",\n        "host": HOST,\n        "port": PORT,\n        "base_url": BASE_URL,\n        "openai_base_url": BASE_URL + "/v1",\n        "kobold_api_url": BASE_URL + "/api/v1",\n        "selected_engine_path": str(exe) if exe else None,\n        "selected_model_path": str(model) if model else None,\n        "context_tokens": CONTEXT,\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n    }\n    save_json(CONFIG, config)\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    if not exe:\n        launcher = f"""@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0C\necho KoboldCpp was not found.\necho.\necho Put koboldcpp.exe here:\necho {ENGINE_DIR}\\\\koboldcpp.exe\necho.\npause\n"""\n    elif not model:\n        launcher = """@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0C\necho No GGUF model found.\necho Expected model folder:\necho Z:\\FOXAI\\Models\\Chat\npause\n"""\n    else:\n        # Common KoboldCpp CLI form. If a specific KoboldCpp release uses a different flag,\n        # this file is the only adapter layer we need to update.\n        cmd = f\'{quote(exe)} --model {quote(model)} --port {PORT} --contextsize {CONTEXT}\'\n        launcher = f"""@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0A\necho ==========================================\necho KayocktheOS KoboldCpp Engine Adapter\necho ==========================================\necho.\necho Engine:\necho {exe}\necho.\necho Model:\necho {model}\necho.\necho Server:\necho {BASE_URL}\necho.\necho Context:\necho {CONTEXT}\necho.\necho Leave this window open.\necho When KoboldCpp finishes loading, return to the Bridge.\necho.\n{cmd}\npause\n"""\n    launcher_path = GATEWAY / "START_KOBOLD_ENGINE.bat"\n    launcher_path.write_text(launcher, encoding="utf-8")\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 004C - Kobold Core Repair",\n        "engine_path": str(exe) if exe else None,\n        "engine_exists": bool(exe),\n        "model_path": str(model) if model else None,\n        "model_exists": bool(model),\n        "launcher": str(launcher_path),\n        "health": kobold_health(),\n        "config": str(CONFIG),\n    }\n    save_json(STATE, state)\n    return state\n\ndef chat(prompt):\n    cfg = load_json(CONFIG, {})\n    base = cfg.get("base_url", BASE_URL)\n    model_name = Path(cfg.get("selected_model_path") or "koboldcpp").name\n\n    system = "You are a helpful local professor inside KayocktheOS. Be clear, practical, and advisor-only."\n    openai_payload = {\n        "model": model_name,\n        "messages": [\n            {"role": "system", "content": system},\n            {"role": "user", "content": prompt}\n        ],\n        "temperature": 0.4,\n        "max_tokens": 800,\n        "stream": False\n    }\n\n    try:\n        data = post_json(base + "/v1/chat/completions", openai_payload)\n        text = data.get("choices", [{}])[0].get("message", {}).get("content")\n        if text:\n            return {"ok": True, "response": text, "raw": data, "engine": "koboldcpp-openai"}\n    except Exception as openai_exc:\n        openai_error = str(openai_exc)\n\n    native_payload = {\n        "prompt": f"{system}\\n\\nOperator: {prompt}\\nProfessor:",\n        "max_length": 800,\n        "temperature": 0.4\n    }\n\n    try:\n        data = post_json(base + "/api/v1/generate", native_payload)\n        text = ""\n        results = data.get("results") if isinstance(data, dict) else None\n        if isinstance(results, list) and results:\n            text = results[0].get("text", "")\n        text = text or (data.get("text") if isinstance(data, dict) else "") or json.dumps(data)[:1200]\n        return {"ok": True, "response": text, "raw": data, "engine": "koboldcpp-native"}\n    except Exception as native_exc:\n        return {\n            "ok": False,\n            "message": "KoboldCpp did not answer. Start AI\\\\Gateway\\\\START_KOBOLD_ENGINE.bat and wait for loading to complete.",\n            "openai_error": openai_error,\n            "native_error": str(native_exc),\n        }\n\nif __name__ == "__main__":\n    print(json.dumps(write_config_and_launcher(), indent=2))\n'

def info(msg):
    print(f"[Feature 004C Kobold Core Repair] {msg}")

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
    for item in ["AI/kobold_engine_adapter.py", "System/API/core_api.py", "Bridge/renderer.js", "Foundry", "Docs", "Forge", "00_START_HERE", "manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_adapter():
    write_text("AI/kobold_engine_adapter.py", ADAPTER_PY)
    spec = importlib.util.spec_from_file_location("kobold_adapter", ROOT / "AI/kobold_engine_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_config_and_launcher()
    info("Adapter repaired.")
    info("Engine path: " + str(state.get("engine_path")))
    info("Model path: " + str(state.get("model_path")))

def patch_core_api():
    path = ROOT / "System" / "API" / "core_api.py"
    if not path.exists():
        info("Core API missing; skipped.")
        return

    text = path.read_text(encoding="utf-8", errors="replace")

    # Fix accidental doubled braces from earlier patch templating.
    text = text.replace('return {{"online": False, "error": str(exc)}}', 'return {"online": False, "error": str(exc)}')
    text = text.replace('return {{"online": False, "message": "Kobold adapter missing"}}', 'return {"online": False, "message": "Kobold adapter missing"}')
    text = text.replace('return {{"ok": False, "error": str(exc)}}', 'return {"ok": False, "error": str(exc)}')
    text = text.replace('return {{"ok": False, "message": "Kobold adapter missing"}}', 'return {"ok": False, "message": "Kobold adapter missing"}')

    # Ensure /api/chat uses Kobold adapter now that this feature exists.
    text = text.replace('self._json(first_contact_chat(payload.get("prompt", "")))',
                        'self._json(kobold_adapter_chat(payload.get("prompt", "")))')
    text = text.replace('self._json(ai_chat(payload.get("prompt", ""), payload.get("context")))',
                        'self._json(kobold_adapter_chat(payload.get("prompt", "")))')

    path.write_text(text, encoding="utf-8")
    py_compile.compile(str(path), doraise=True)
    info("Core API repaired and syntax checked.")

def clean_renderer_duplicate_calls():
    path = ROOT / "Bridge" / "renderer.js"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    # Avoid stacking multiple renderKoboldPanel calls immediately after repeated notification renders.
    text = text.replace("renderNotifications();\n  renderKoboldPanel();\n  renderKoboldPanel();", "renderNotifications();\n  renderKoboldPanel();")
    path.write_text(text, encoding="utf-8")
    info("Bridge renderer duplicate Kobold render calls cleaned where found.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_004c_kobold_core_repair: enabled" not in text:
        text += "\n  feature_004c_kobold_core_repair: enabled\n" if "features:" in text else "\nfeatures:\n  feature_004c_kobold_core_repair: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_004C_KOBOLD_CORE_REPAIR.md", """# Feature 004C - Kobold Core Repair

This patch is based on the uploaded KayocktheOS source tree.

## Fixes

- Repairs malformed Core API Kobold return values.
- Replaces the Kobold adapter with a cleaner single source of truth.
- Makes `/api/chat` prefer the Kobold adapter.
- Tries OpenAI-compatible Kobold chat first, then native Kobold generate.
- Rewrites `AI/Gateway/START_KOBOLD_ENGINE.bat`.

## After install

1. Put `koboldcpp.exe` at:

```text
Z:\\KayocktheOS\\Engine\\KoboldCpp\\koboldcpp.exe
```

2. Run:

```text
Z:\\KayocktheOS\\AI\\Gateway\\START_KOBOLD_ENGINE.bat
```

3. Restart KayocktheOS Core and Bridge.
""")
    write_text("Forge/Decisions/0038_kobold_core_repair.md", """# Decision 0038 - Kobold Core Repair

The Core API should talk to a single engine adapter instead of accumulating launcher-specific chat paths.
""")
    write_text("Foundry/Releases/feature004c_kobold_core_repair_notes.md", "# Feature 004C - Kobold Core Repair\n\nRepairs Core API Kobold adapter integration.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 004C - Kobold Core Repair\n\n- Repaired Core API Kobold return values.\n- Replaced `AI/kobold_engine_adapter.py` with cleaner adapter implementation.\n- `/api/chat` now prefers the Kobold adapter.\n- Adapter tries OpenAI-compatible Kobold endpoint, then native Kobold endpoint.\n"
    if "Feature 004C - Kobold Core Repair" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_adapter()
    patch_core_api()
    clean_renderer_duplicate_calls()
    update_manifest()
    docs()
    changelog()
    info("Feature 004C Kobold Core Repair complete.")

if __name__ == "__main__":
    main()
