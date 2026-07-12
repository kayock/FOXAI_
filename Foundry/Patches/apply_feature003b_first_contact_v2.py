from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003b_before_first_contact_v2_{STAMP}"

FIRST_CONTACT_V2 = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nENGINE = FOXAI / "Engine"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "gateway_config.json"\nSTATE = GATEWAY / "first_contact_state.json"\n\nSERVER_PRIORITY = [\n    "llama-server.exe",\n    "llamafile.exe",\n    "koboldcpp.exe",\n    "llama-cli.exe"\n]\n\nBLOCKED_RUNTIME_NAMES = {\n    "llama-batched-bench.exe",\n    "llama-bench.exe",\n    "llama-perplexity.exe",\n    "llama-results.exe",\n    "llama-fit-params.exe",\n    "llama-quantize.exe",\n    "llama-tokenize.exe",\n    "llama-gguf-split.exe",\n    "llama-imatrix.exe"\n}\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef scan_models():\n    models = []\n    chat_dir = FOXAI / "Models" / "Chat"\n    if chat_dir.exists():\n        for p in chat_dir.glob("*.gguf"):\n            models.append(model_record(p))\n    vision_dir = FOXAI / "Models" / "Vision"\n    if vision_dir.exists():\n        for p in vision_dir.glob("*.gguf"):\n            models.append(model_record(p))\n    if not models:\n        for p in FOXAI.rglob("*.gguf") if FOXAI.exists() else []:\n            models.append(model_record(p))\n    return sorted(models, key=lambda m: m["name"].lower())\n\ndef model_record(path):\n    try:\n        size = round(path.stat().st_size / (1024**3), 3)\n    except Exception:\n        size = None\n    return {\n        "name": path.name,\n        "path": str(path),\n        "size_gb": size,\n        "capabilities": infer_caps(path.name)\n    }\n\ndef infer_caps(name):\n    n = name.lower()\n    caps = ["chat"]\n    if "deepseek" in n or "r1" in n:\n        caps.append("reasoning")\n    if "coder" in n or "code" in n:\n        caps.append("coding")\n    if "vl" in n or "vision" in n:\n        caps.append("vision")\n    return sorted(set(caps))\n\ndef choose_model():\n    models = scan_models()\n    if not models:\n        return None\n    scored = []\n    for m in models:\n        n = m.get("name", "").lower()\n        score = 0\n        if "deepseek" in n and "14b" in n:\n            score += 60\n        if "qwen3vl-8b" in n and "q4" in n:\n            score += 50\n        if "qwen" in n and "8b" in n:\n            score += 40\n        if "q4_k_m" in n:\n            score += 25\n        if "q8" in n:\n            score += 10\n        if "coder" in n:\n            score += 8\n        if "32b" in n or "30b" in n:\n            score -= 15\n        if "vision" in (m.get("capabilities") or []):\n            score -= 5\n        scored.append((score, m))\n    return sorted(scored, key=lambda x: (-x[0], x[1].get("size_gb") or 999))[0][1]\n\ndef scan_runtimes():\n    found = []\n    search_roots = [ENGINE, FOXAI]\n    seen = set()\n    for root in search_roots:\n        if not root.exists():\n            continue\n        for exe in root.rglob("*.exe"):\n            name = exe.name.lower()\n            if name in seen:\n                continue\n            seen.add(name)\n            if name in BLOCKED_RUNTIME_NAMES:\n                continue\n            if name in SERVER_PRIORITY or name == "server.exe" or "llamafile" in name or name == "koboldcpp.exe":\n                found.append({\n                    "name": exe.name,\n                    "path": str(exe),\n                    "priority": runtime_priority(exe.name)\n                })\n    return sorted(found, key=lambda r: (r["priority"], r["name"].lower()))\n\ndef runtime_priority(name):\n    n = name.lower()\n    for idx, preferred in enumerate(SERVER_PRIORITY):\n        if n == preferred:\n            return idx\n    if "server" in n:\n        return 20\n    return 99\n\ndef choose_runtime():\n    runtimes = scan_runtimes()\n    return runtimes[0] if runtimes else None\n\ndef runtime_health():\n    base = "http://127.0.0.1:8845"\n    for url in [base + "/v1/models", base + "/health", base]:\n        try:\n            with urllib.request.urlopen(url, timeout=2) as res:\n                return {"online": True, "base": base, "message": f"responded at {url}"}\n        except Exception:\n            pass\n    return {"online": False, "base": base, "message": "offline"}\n\ndef configure():\n    model = choose_model()\n    runtime = choose_runtime()\n    cfg = load_json(CONFIG, {})\n    cfg.update({\n        "mode": "advisor_only",\n        "write_access": False,\n        "operator_approval_required": True,\n        "active_runtime": "llama_server_openai_compatible",\n        "runtime_base": "http://127.0.0.1:8845",\n        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n        "active_chat_model": model["name"] if model else "local-model",\n        "selected_model_path": model["path"] if model else None,\n        "selected_runtime_path": runtime["path"] if runtime else None,\n        "temperature": 0.4,\n        "max_tokens": 1200,\n        "timeout_seconds": 240\n    })\n    save_json(CONFIG, cfg)\n    return cfg\n\ndef quote(arg):\n    return \'"\' + str(arg).replace(\'"\', \'\') + \'"\'\n\ndef launch_command(runtime, model):\n    exe = Path(runtime).name.lower()\n    if exe == "llama-server.exe":\n        return f\'{quote(runtime)} -m {quote(model)} --host 127.0.0.1 --port 8845\'\n    if "llamafile" in exe:\n        return f\'{quote(runtime)} -m {quote(model)} --server --host 127.0.0.1 --port 8845\'\n    if exe == "koboldcpp.exe":\n        return f\'{quote(runtime)} --model {quote(model)} --host 127.0.0.1 --port 8845\'\n    if exe == "llama-cli.exe":\n        return f\'echo llama-cli.exe is interactive, not a server. Please use llama-server.exe instead. && pause\'\n    return f\'{quote(runtime)} -m {quote(model)} --host 127.0.0.1 --port 8845\'\n\ndef write_launcher():\n    cfg = configure()\n    model = cfg.get("selected_model_path")\n    runtime = cfg.get("selected_runtime_path")\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    if not model or not runtime:\n        text = """@echo off\ntitle KayocktheOS First Contact v2 Runtime\ncolor 0C\necho First Contact v2 cannot launch yet.\necho.\necho Missing model or server runtime.\necho.\necho Expected:\necho   Z:\\\\FOXAI\\\\Engine\\\\llama-server.exe\necho   Z:\\\\FOXAI\\\\Models\\\\Chat\\\\*.gguf\necho.\npause\n"""\n    else:\n        cmd = launch_command(runtime, model)\n        text = f"""@echo off\ntitle KayocktheOS First Contact v2 Runtime\ncolor 0A\necho ==========================================\necho KayocktheOS First Contact v2 Runtime\necho ==========================================\necho.\necho Correct runtime selected:\necho {runtime}\necho.\necho Model:\necho {model}\necho.\necho Server:\necho http://127.0.0.1:8845\necho.\necho Leave this window open.\necho When the server says it is listening, return to the Bridge and ask the Academy.\necho.\n{cmd}\npause\n"""\n    path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"\n    path.write_text(text, encoding="utf-8")\n    return str(path)\n\ndef status():\n    cfg = configure()\n    launcher = write_launcher()\n    payload = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 003B - First Contact v2",\n        "model": cfg.get("active_chat_model"),\n        "model_path": cfg.get("selected_model_path"),\n        "runtime_path": cfg.get("selected_runtime_path"),\n        "runtime": runtime_health(),\n        "launcher": launcher,\n        "ready_for_contact": bool(cfg.get("selected_model_path") and cfg.get("selected_runtime_path")),\n        "blocked_runtime_names": sorted(BLOCKED_RUNTIME_NAMES),\n        "runtime_candidates": scan_runtimes(),\n        "model_candidates": scan_models()[:12],\n        "instructions": [\n            "Run AI\\\\Gateway\\\\FIRST_CONTACT_START_RUNTIME.bat",\n            "Wait until llama-server finishes loading.",\n            "Open the Bridge.",\n            "Ask the Academy."\n        ]\n    }\n    save_json(STATE, payload)\n    return payload\n\nif __name__ == "__main__":\n    print(json.dumps(status(), indent=2))\n'

def info(msg):
    print(f"[Feature 003B First Contact v2] {msg}")

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

def install_first_contact_v2():
    write_text("AI/first_contact.py", FIRST_CONTACT_V2)
    spec = importlib.util.spec_from_file_location("kayock_first_contact", ROOT / "AI/first_contact.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s = mod.status()
    info("Selected model: " + str(s.get("model")))
    info("Runtime path: " + str(s.get("runtime_path")))
    info("Launcher rewritten: AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003b_first_contact_v2: enabled" not in text:
        text += "\n  feature_003b_first_contact_v2: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003b_first_contact_v2: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_003B_FIRST_CONTACT_V2.md", """# Feature 003B - First Contact v2

Fixes the runtime selector.

## Important

Use:

```text
Z:\\FOXAI\\Engine\\llama-server.exe
```

Ignore benchmark/developer utilities:

```text
llama-batched-bench.exe
llama-bench.exe
llama-perplexity.exe
llama-results.exe
```

## Run

```text
Z:\\KayocktheOS\\AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat
```

Then ask the Academy from the Bridge.
""")
    write_text("Forge/Decisions/0030_first_contact_v2_runtime_selection.md", """# Decision 0030 - First Contact v2 Runtime Selection

First Contact must prefer `llama-server.exe`.

Benchmark tools are never valid chat runtimes.
""")
    write_text("Foundry/Releases/feature003b_first_contact_v2_notes.md", "# Feature 003B - First Contact v2\n\nCorrects runtime selection to prefer llama-server.exe and ignore benchmark tools.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003B - First Contact v2\n\n- Corrected runtime selector to prefer `llama-server.exe`.\n- Blocked benchmark/developer executables from runtime selection.\n- Preserved FOXAI as external engine/model warehouse.\n- Rewrote `FIRST_CONTACT_START_RUNTIME.bat`.\n"
    if "Feature 003B - First Contact v2" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_first_contact_v2()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 003B First Contact v2 complete.")
    info("Run AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat again.")

if __name__ == "__main__":
    main()
