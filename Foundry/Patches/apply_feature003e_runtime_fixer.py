from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003e_before_runtime_fixer_{STAMP}"

FIXER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nLLAMA_SERVER = FOXAI / "Engine" / "llama-server.exe"\nCHAT_MODELS = FOXAI / "Models" / "Chat"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "gateway_config.json"\nSTATE = GATEWAY / "first_contact_runtime_fixer_state.json"\n\nMODEL_PRIORITY = [\n    "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",\n    "Qwen3VL-8B-Instruct-Q4_K_M.gguf",\n    "Qwen3VL-8B-Instruct-Q8_0.gguf",\n    "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",\n    "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf"\n]\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef choose_model():\n    if CHAT_MODELS.exists():\n        existing = {p.name: p for p in CHAT_MODELS.glob("*.gguf")}\n        for name in MODEL_PRIORITY:\n            if name in existing:\n                return existing[name]\n        models = sorted(CHAT_MODELS.glob("*.gguf"), key=lambda p: p.name.lower())\n        if models:\n            return models[0]\n    all_models = sorted(FOXAI.rglob("*.gguf"), key=lambda p: p.name.lower()) if FOXAI.exists() else []\n    return all_models[0] if all_models else None\n\ndef runtime_health():\n    base = "http://127.0.0.1:8845"\n    for url in [base + "/v1/models", base + "/health", base]:\n        try:\n            with urllib.request.urlopen(url, timeout=2) as res:\n                return {"online": True, "message": f"responded at {url}", "base": base}\n        except Exception:\n            pass\n    return {"online": False, "message": "offline", "base": base}\n\ndef quote(path):\n    return \'"\' + str(path).replace(\'"\',\'\') + \'"\'\n\ndef write_all():\n    model = choose_model()\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    cfg = load_json(CONFIG, {})\n    cfg.update({\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n        "active_runtime": "llama_server_openai_compatible",\n        "runtime_base": "http://127.0.0.1:8845",\n        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n        "active_chat_model": model.name if model else "local-model",\n        "selected_model_path": str(model) if model else None,\n        "selected_runtime_path": str(LLAMA_SERVER) if LLAMA_SERVER.exists() else None,\n        "temperature": 0.4,\n        "max_tokens": 1200,\n        "timeout_seconds": 240\n    })\n    save_json(CONFIG, cfg)\n\n    if not LLAMA_SERVER.exists():\n        launcher = """@echo off\ntitle KayocktheOS First Contact Runtime Fixer\ncolor 0C\necho llama-server.exe was not found at:\necho Z:\\\\FOXAI\\\\Engine\\\\llama-server.exe\necho.\necho FOXAI Engine appears incomplete or moved.\npause\n"""\n    elif not model:\n        launcher = """@echo off\ntitle KayocktheOS First Contact Runtime Fixer\ncolor 0C\necho No GGUF chat model found.\necho Expected:\necho Z:\\\\FOXAI\\\\Models\\\\Chat\\\\*.gguf\npause\n"""\n    else:\n        command = f\'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845\'\n        launcher = f"""@echo off\ntitle KayocktheOS First Contact Runtime - llama-server\ncolor 0A\necho ==========================================\necho KayocktheOS First Contact Runtime\necho ==========================================\necho.\necho Runtime locked to:\necho {LLAMA_SERVER}\necho.\necho Model selected:\necho {model}\necho.\necho Server:\necho http://127.0.0.1:8845\necho.\necho Leave this window open.\necho Wait until llama-server says it is listening.\necho Then open the Bridge and Ask the Academy.\necho.\n{command}\npause\n"""\n    launcher_path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"\n    launcher_path.write_text(launcher, encoding="utf-8")\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 003E - First Contact Runtime Fixer",\n        "runtime_locked_to": str(LLAMA_SERVER),\n        "runtime_exists": LLAMA_SERVER.exists(),\n        "model_selected": model.name if model else None,\n        "model_path": str(model) if model else None,\n        "launcher": str(launcher_path),\n        "runtime": runtime_health(),\n        "note": "This fixer intentionally ignores benchmark executables."\n    }\n    save_json(STATE, state)\n    return state\n\nif __name__ == "__main__":\n    print(json.dumps(write_all(), indent=2))\n'

def info(msg):
    print(f"[Feature 003E Runtime Fixer] {msg}")

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
    for item in ["AI","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install():
    write_text("AI/first_contact_runtime_fixer.py", FIXER_PY)
    spec = importlib.util.spec_from_file_location("fcfix", ROOT / "AI/first_contact_runtime_fixer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_all()
    info("Runtime locked to: " + str(state.get("runtime_locked_to")))
    info("Runtime exists: " + str(state.get("runtime_exists")))
    info("Model selected: " + str(state.get("model_selected")))
    info("Launcher rewritten: AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003e_first_contact_runtime_fixer: enabled" not in text:
        text += "\n  feature_003e_first_contact_runtime_fixer: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003e_first_contact_runtime_fixer: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_003E_FIRST_CONTACT_RUNTIME_FIXER.md", """# Feature 003E - First Contact Runtime Fixer

This patch hard-locks First Contact to:

```text
Z:\\FOXAI\\Engine\\llama-server.exe
```

It chooses a chat model from:

```text
Z:\\FOXAI\\Models\\Chat
```

Preferred model:

```text
DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
```

Then it rewrites:

```text
AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat
```

Run that BAT after installing this patch.
""")
    write_text("Forge/Decisions/0033_runtime_fixer.md", """# Decision 0033 - First Contact Runtime Fixer

First Contact should not guess among all llama executables.

Known-good path is `Z:\FOXAI\Engine\llama-server.exe`.
""")
    write_text("Foundry/Releases/feature003e_first_contact_runtime_fixer_notes.md", "# Feature 003E - Runtime Fixer\n\nLocks First Contact to FOXAI Engine llama-server.exe.\n")

def changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003E - First Contact Runtime Fixer\n\n- Hard-locked First Contact runtime to `Z:\\FOXAI\\Engine\\llama-server.exe`.\n- Preferred `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`.\n- Rewrote `AI/Gateway/FIRST_CONTACT_START_RUNTIME.bat`.\n- Removed runtime guessing risk from benchmark executables.\n"
    if "Feature 003E - First Contact Runtime Fixer" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install()
    update_manifest()
    docs()
    changelog()
    info("Feature 003E First Contact Runtime Fixer complete.")
    info("Run AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat.")

if __name__ == "__main__":
    main()
