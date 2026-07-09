from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003_before_first_contact_{STAMP}"

FIRST_CONTACT_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "gateway_config.json"\nSTATE = GATEWAY / "first_contact_state.json"\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef scan_models():\n    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"\n    data = load_json(inv, {})\n    models = data.get("assets", {}).get("llms", [])\n    if models:\n        return models\n    if not FOXAI.exists():\n        return []\n    out = []\n    for p in FOXAI.rglob("*.gguf"):\n        try:\n            out.append({"name": p.name, "path": str(p), "size_gb": round(p.stat().st_size/(1024**3), 3), "capabilities": infer_caps(p.name)})\n        except Exception:\n            pass\n    return sorted(out, key=lambda m: m["name"].lower())\n\ndef infer_caps(name):\n    n = name.lower()\n    caps = ["chat"]\n    if "deepseek" in n or "r1" in n: caps.append("reasoning")\n    if "coder" in n or "code" in n: caps.append("coding")\n    if "vl" in n or "vision" in n: caps.append("vision")\n    return sorted(set(caps))\n\ndef choose_model():\n    models = scan_models()\n    if not models:\n        return None\n    scored = []\n    for m in models:\n        n = m.get("name","").lower()\n        score = 0\n        if "deepseek" in n and "14b" in n: score += 50\n        if "qwen" in n and ("8b" in n or "q4" in n): score += 40\n        if "q4" in n: score += 20\n        if "q8" in n: score += 10\n        if "32b" in n or "30b" in n: score -= 10\n        if "coder" in n: score += 5\n        scored.append((score, m))\n    return sorted(scored, key=lambda x: (-x[0], x[1].get("size_gb", 999)))[0][1]\n\ndef scan_runtimes():\n    if not FOXAI.exists():\n        return []\n    found = []\n    for exe in FOXAI.rglob("*.exe"):\n        n = exe.name.lower()\n        if "llama" in n or "llamafile" in n or n in ("server.exe", "koboldcpp.exe"):\n            found.append({"name": exe.name, "path": str(exe)})\n    return sorted(found, key=lambda r: (0 if "llamafile" in r["name"].lower() else 1, r["name"].lower()))\n\ndef choose_runtime():\n    rts = scan_runtimes()\n    return rts[0] if rts else None\n\ndef runtime_health():\n    base = "http://127.0.0.1:8845"\n    for url in [base + "/v1/models", base + "/health", base]:\n        try:\n            with urllib.request.urlopen(url, timeout=2) as res:\n                return {"online": True, "base": base, "message": f"responded at {url}"}\n        except Exception:\n            pass\n    return {"online": False, "base": base, "message": "offline"}\n\ndef configure():\n    model = choose_model()\n    runtime = choose_runtime()\n    cfg = load_json(CONFIG, {})\n    cfg.update({\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n        "active_runtime": "openai_compatible",\n        "runtime_base": "http://127.0.0.1:8845",\n        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n        "active_chat_model": model["name"] if model else "local-model",\n        "selected_model_path": model["path"] if model else None,\n        "selected_runtime_path": runtime["path"] if runtime else None,\n        "temperature": 0.4,\n        "max_tokens": 1200,\n        "timeout_seconds": 240\n    })\n    save_json(CONFIG, cfg)\n    return cfg\n\ndef quote(arg):\n    return \'"\' + str(arg).replace(\'"\',\'\') + \'"\'\n\ndef write_launcher():\n    cfg = configure()\n    model = cfg.get("selected_model_path")\n    runtime = cfg.get("selected_runtime_path")\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    if not model or not runtime:\n        text = """@echo off\ntitle KayocktheOS First Contact Runtime\ncolor 0C\necho First Contact cannot launch yet.\necho.\necho Missing model or runtime.\necho.\necho Need:\necho   - At least one .gguf model under Z:\\\\FOXAI\necho   - A runtime exe under Z:\\\\FOXAI, such as llamafile.exe or llama-server.exe\necho.\npause\n"""\n    else:\n        exe_name = Path(runtime).name.lower()\n        if "llamafile" in exe_name:\n            cmd = f\'{quote(runtime)} -m {quote(model)} --server --host 127.0.0.1 --port 8845\'\n        else:\n            cmd = f\'{quote(runtime)} -m {quote(model)} --host 127.0.0.1 --port 8845\'\n        text = f"""@echo off\ntitle KayocktheOS First Contact Runtime\ncolor 0A\necho ==========================================\necho KayocktheOS First Contact Runtime\necho ==========================================\necho.\necho Runtime:\necho {runtime}\necho.\necho Model:\necho {model}\necho.\necho Leave this window open.\necho When the server is loaded, return to the Bridge and ask the Academy.\necho.\n{cmd}\npause\n"""\n    path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"\n    path.write_text(text, encoding="utf-8")\n    return str(path)\n\ndef chat(prompt):\n    cfg = configure()\n    payload = {\n        "model": cfg.get("active_chat_model", "local-model"),\n        "messages": [\n            {"role": "system", "content": "You are a local professor inside KayocktheOS. You are advisor-only. Do not claim to edit files. Explain clearly and wait for Operator approval before changes."},\n            {"role": "user", "content": prompt}\n        ],\n        "temperature": cfg.get("temperature", 0.4),\n        "max_tokens": cfg.get("max_tokens", 1200),\n        "stream": False\n    }\n    try:\n        req = urllib.request.Request(cfg["chat_endpoint"], data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")\n        with urllib.request.urlopen(req, timeout=int(cfg.get("timeout_seconds",240))) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n        data = json.loads(raw)\n        content = data.get("choices", [{}])[0].get("message", {}).get("content", raw)\n        return {"ok": True, "response": content, "raw": data}\n    except Exception as exc:\n        return {"ok": False, "message": "First Contact failed. Start FIRST_CONTACT_START_RUNTIME.bat, wait for the model to load, then try again.", "error": str(exc)}\n\ndef status():\n    cfg = configure()\n    launcher = write_launcher()\n    payload = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 003 - First Contact",\n        "model": cfg.get("active_chat_model"),\n        "model_path": cfg.get("selected_model_path"),\n        "runtime_path": cfg.get("selected_runtime_path"),\n        "runtime": runtime_health(),\n        "launcher": launcher,\n        "ready_for_contact": bool(cfg.get("selected_model_path") and cfg.get("selected_runtime_path")),\n        "instructions": [\n            "Run AI\\\\Gateway\\\\FIRST_CONTACT_START_RUNTIME.bat",\n            "Wait until the model server finishes loading.",\n            "Open the Bridge.",\n            "Ask the Academy."\n        ]\n    }\n    save_json(STATE, payload)\n    return payload\n\nif __name__ == "__main__":\n    print(json.dumps(status(), indent=2))\n'
BRIDGE_NOTICE = "\n// Feature 003 First Contact Bridge notice\nfunction renderFirstContactNotice() {\n  const wall = document.getElementById('workshopWall') || document.getElementById('foundryWorkshopWall');\n  if (!wall || document.getElementById('firstContactNotice')) return;\n  const div = document.createElement('div');\n  div.id = 'firstContactNotice';\n  div.className = 'item ok';\n  div.innerHTML = '<strong>Feature 003</strong><span>First Contact installed. Run AI\\\\\\\\Gateway\\\\\\\\FIRST_CONTACT_START_RUNTIME.bat, then Ask the Academy.</span>';\n  wall.prepend(div);\n}\n"

def info(msg):
    print(f"[Feature 003 First Contact] {msg}")

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
    for item in ["AI","System","Bridge","manifest.yaml","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_first_contact():
    write_text("AI/first_contact.py", FIRST_CONTACT_PY)
    spec = importlib.util.spec_from_file_location("kayock_first_contact", ROOT / "AI/first_contact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s = mod.status()
    info("Selected model: " + str(s.get("model")))
    info("Runtime path: " + str(s.get("runtime_path")))
    info("Launcher: AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; installed files but skipped API patch.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def first_contact_status(" not in old:
        insert = """
def first_contact_status():
    try:
        fc = ROOT / "AI" / "first_contact.py"
        if fc.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_first_contact", fc)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ready_for_contact": False, "error": str(exc)}
    return {"ready_for_contact": False, "message": "First Contact missing"}

def first_contact_chat(prompt=""):
    try:
        fc = ROOT / "AI" / "first_contact.py"
        if fc.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_first_contact", fc)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "First Contact missing"}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"first_contact": first_contact_status(),' not in old:
        if '"local_chat": local_chat_status(),' in old:
            old = old.replace('"local_chat": local_chat_status(),', '"local_chat": local_chat_status(),\n        "first_contact": first_contact_status(),')
        elif '"local_runtime": local_runtime_health(),' in old:
            old = old.replace('"local_runtime": local_runtime_health(),', '"local_runtime": local_runtime_health(),\n        "first_contact": first_contact_status(),')

    if 'elif path == "/api/first-contact":' not in old:
        if 'elif path == "/api/local-chat":' in old:
            old = old.replace('elif path == "/api/local-chat":\n            self._json(local_chat_status())',
                              'elif path == "/api/local-chat":\n            self._json(local_chat_status())\n        elif path == "/api/first-contact":\n            self._json(first_contact_status())')
        elif 'elif path == "/api/runtime":' in old:
            old = old.replace('elif path == "/api/runtime":\n            self._json(local_runtime_health())',
                              'elif path == "/api/runtime":\n            self._json(local_runtime_health())\n        elif path == "/api/first-contact":\n            self._json(first_contact_status())')

    old = old.replace('self._json(ai_chat(payload.get("prompt", ""), payload.get("context")))',
                      'self._json(first_contact_chat(payload.get("prompt", "")))')
    old = old.replace('self._json(ai_chat_placeholder(payload.get("prompt", ""), payload.get("context")))',
                      'self._json(first_contact_chat(payload.get("prompt", "")))')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/first-contact and First Contact chat.")

def patch_bridge():
    renderer = ROOT / "Bridge" / "renderer.js"
    if not renderer.exists():
        return
    old = renderer.read_text(encoding="utf-8", errors="replace")
    if "Feature 003 First Contact Bridge notice" not in old:
        old = old.rstrip() + "\n\n" + BRIDGE_NOTICE
    if "renderFirstContactNotice();" not in old:
        old = old.replace("renderNotifications();", "renderNotifications();\n  renderFirstContactNotice();")
    renderer.write_text(old, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003_first_contact: enabled" not in text:
        text += "\n  feature_003_first_contact: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003_first_contact: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_003_FIRST_CONTACT.md", """# Feature 003 - First Contact

First Contact connects the Bridge chat path to a real local model server.

## Steps

1. Run:

```text
Z:\\KayocktheOS\\AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat
```

2. Wait for the model to finish loading.

3. Open:

```text
Z:\\KayocktheOS\\Launch_KayocktheOS_Workshop.bat
```

4. Ask the Academy.

## API

```text
GET  /api/first-contact
POST /api/chat
```

## Safety

Advisor-only. No file writes. No command execution. Operator approval required for changes.
""")
    write_text("Forge/Decisions/0029_first_contact.md", """# Decision 0029 - First Contact

The first real AI conversation should use the existing Bridge and AI Gateway path.

The local model is a professor specialist, not the identity of KayocktheOS.
""")
    write_text("Foundry/Releases/feature003_first_contact_notes.md", "# Feature 003 - First Contact\n\nConnects Bridge chat to local model runtime via First Contact layer.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003 - First Contact\n\n- Added `AI/first_contact.py`.\n- Added `AI/Gateway/FIRST_CONTACT_START_RUNTIME.bat`.\n- Added `/api/first-contact`.\n- Routed `/api/chat` through First Contact.\n- Advisor-only local AI conversation path established.\n"
    if "Feature 003 - First Contact" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_first_contact()
    patch_core_api()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 003 First Contact complete.")
    info("Next: run AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat.")

if __name__ == "__main__":
    main()
