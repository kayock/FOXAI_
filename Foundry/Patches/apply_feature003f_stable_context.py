from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003f_before_stable_context_{STAMP}"

FIX_PY = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nLLAMA_SERVER = FOXAI / "Engine" / "llama-server.exe"\nMODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"\nFALLBACK_MODEL = FOXAI / "Models" / "Chat" / "Qwen3VL-8B-Instruct-Q4_K_M.gguf"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "gateway_config.json"\nSTATE = GATEWAY / "first_contact_stable_context_state.json"\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef choose_model():\n    if MODEL.exists():\n        return MODEL\n    if FALLBACK_MODEL.exists():\n        return FALLBACK_MODEL\n    chat = FOXAI / "Models" / "Chat"\n    if chat.exists():\n        models = sorted(chat.glob("*.gguf"), key=lambda p: p.name.lower())\n        if models:\n            return models[0]\n    return None\n\ndef quote(path):\n    return \'"\' + str(path).replace(\'"\', \'\') + \'"\'\n\ndef apply_fix():\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n    model = choose_model()\n\n    cfg = load_json(CONFIG, {})\n    cfg.update({\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n        "active_runtime": "llama_server_openai_compatible",\n        "runtime_base": "http://127.0.0.1:8845",\n        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n        "active_chat_model": model.name if model else "local-model",\n        "selected_model_path": str(model) if model else None,\n        "selected_runtime_path": str(LLAMA_SERVER) if LLAMA_SERVER.exists() else None,\n        "context_tokens": 4096,\n        "temperature": 0.4,\n        "max_tokens": 1200,\n        "timeout_seconds": 240\n    })\n    save_json(CONFIG, cfg)\n\n    if not LLAMA_SERVER.exists():\n        launcher = """@echo off\ntitle KayocktheOS First Contact Runtime\ncolor 0C\necho Missing:\necho Z:\\\\FOXAI\\\\Engine\\\\llama-server.exe\npause\n"""\n    elif not model:\n        launcher = """@echo off\ntitle KayocktheOS First Contact Runtime\ncolor 0C\necho No GGUF model found in:\necho Z:\\\\FOXAI\\\\Models\\\\Chat\npause\n"""\n    else:\n        cmd = f\'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845 -c 4096\'\n        launcher = f"""@echo off\ntitle KayocktheOS First Contact Runtime - Stable Context\ncolor 0A\necho ==========================================\necho KayocktheOS First Contact Runtime\necho Stable Context: 4096\necho ==========================================\necho.\necho Runtime:\necho {LLAMA_SERVER}\necho.\necho Model:\necho {model}\necho.\necho Server:\necho http://127.0.0.1:8845\necho.\necho This launcher uses -c 4096 to avoid KV cache memory failure.\necho Leave this window open.\necho When llama-server says it is listening, return to the Bridge and Ask the Academy.\necho.\n{cmd}\npause\n"""\n    launcher_path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"\n    launcher_path.write_text(launcher, encoding="utf-8")\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 003F - First Contact Stable Context",\n        "runtime": str(LLAMA_SERVER),\n        "model": str(model) if model else None,\n        "context_tokens": 4096,\n        "launcher": str(launcher_path),\n        "known_good_command": f\'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845 -c 4096\' if model else None\n    }\n    save_json(STATE, state)\n    return state\n\nif __name__ == "__main__":\n    print(json.dumps(apply_fix(), indent=2))\n'

def info(msg):
    print(f"[Feature 003F Stable Context] {msg}")

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

def install_fix():
    write_text("AI/first_contact_stable_context.py", FIX_PY)
    spec = importlib.util.spec_from_file_location("fcstable", ROOT / "AI/first_contact_stable_context.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.apply_fix()
    info("Stable context applied: -c 4096")
    info("Model: " + str(state.get("model")))
    info("Launcher rewritten: AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003f_first_contact_stable_context: enabled" not in text:
        text += "\n  feature_003f_first_contact_stable_context: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003f_first_contact_stable_context: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_003F_FIRST_CONTACT_STABLE_CONTEXT.md", """# Feature 003F - First Contact Stable Context

This patch applies the known-good runtime command:

```text
Z:\\FOXAI\\Engine\\llama-server.exe -m Z:\\FOXAI\\Models\\Chat\\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf --host 127.0.0.1 --port 8845 -c 4096
```

The important fix is:

```text
-c 4096
```

This prevents the KV cache allocation failure caused by the huge default context.
""")
    write_text("Forge/Decisions/0034_first_contact_stable_context.md", """# Decision 0034 - First Contact Stable Context

First Contact must launch local GGUF models with a safe context size.

Known-good default for this machine is `-c 4096`.
""")
    write_text("Foundry/Releases/feature003f_first_contact_stable_context_notes.md", "# Feature 003F - Stable Context\n\nAdds `-c 4096` to First Contact launcher.\n")

def changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003F - First Contact Stable Context\n\n- Updated First Contact runtime launcher with `-c 4096`.\n- Preserved llama-server runtime path.\n- Preserved DeepSeek 14B model selection.\n- Prevents KV cache memory failure from default context size.\n"
    if "Feature 003F - First Contact Stable Context" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_fix()
    update_manifest()
    docs()
    changelog()
    info("Feature 003F Stable Context complete.")
    info("Run AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat.")

if __name__ == "__main__":
    main()
