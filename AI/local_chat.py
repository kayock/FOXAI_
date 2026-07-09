from pathlib import Path
import json
import datetime
import subprocess
import sys
import urllib.request
import urllib.error
import time

ROOT = Path(__file__).resolve().parents[1]
FOXAI_ROOT = Path("Z:/FOXAI")
GATEWAY_DIR = ROOT / "AI" / "Gateway"
CONFIG_PATH = GATEWAY_DIR / "gateway_config.json"
CHAT_STATE = GATEWAY_DIR / "local_chat_state.json"

DEFAULT_CONFIG = {
    "mode": "advisor_only",
    "write_access": False,
    "operator_approval_required": True,
    "active_runtime": "openai_compatible",
    "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",
    "runtime_base": "http://127.0.0.1:8845",
    "active_chat_model": "local-model",
    "selected_model_path": None,
    "timeout_seconds": 180,
    "temperature": 0.4,
    "max_tokens": 1024,
    "runtime_command": None
}

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_config():
    config = {**DEFAULT_CONFIG, **load_json(CONFIG_PATH, {})}
    save_json(CONFIG_PATH, config)
    return config

def foxai_models():
    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"
    data = load_json(inv, None)
    if data:
        return data.get("assets", {}).get("llms", [])
    if not FOXAI_ROOT.exists():
        return []
    models = []
    for p in FOXAI_ROOT.rglob("*.gguf"):
        try:
            models.append({
                "name": p.name,
                "path": str(p),
                "size_gb": round(p.stat().st_size / (1024**3), 3),
                "capabilities": infer_caps(p.name)
            })
        except Exception:
            pass
    return sorted(models, key=lambda x: x["name"].lower())

def infer_caps(name):
    n = name.lower()
    caps = ["chat"]
    if "coder" in n or "code" in n:
        caps.append("coding")
    if "deepseek" in n or "r1" in n:
        caps.append("reasoning")
    if "vl" in n or "vision" in n:
        caps.append("vision")
    return sorted(set(caps))

def recommend_default_model():
    models = foxai_models()
    if not models:
        return None
    scored = []
    for m in models:
        name = m.get("name","").lower()
        score = 0
        if "deepseek" in name and "14b" in name:
            score += 10
        if "qwen" in name and ("8b" in name or "q4" in name):
            score += 8
        if "q4" in name:
            score += 5
        if "coder" in name:
            score += 3
        if "32b" in name or "30b" in name:
            score -= 4
        scored.append((score, m))
    return sorted(scored, key=lambda x: (-x[0], x[1].get("size_gb", 999)))[0][1]

def configure_default():
    config = load_config()
    if not config.get("selected_model_path"):
        model = recommend_default_model()
        if model:
            config["selected_model_path"] = model["path"]
            config["active_chat_model"] = model["name"]
    save_json(CONFIG_PATH, config)
    return config

def runtime_health():
    config = load_config()
    base = config.get("runtime_base") or "http://127.0.0.1:8845"
    for url in [base + "/v1/models", base + "/health", base]:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                return {"online": True, "message": f"responded at {url}", "base": base}
        except Exception:
            pass
    return {"online": False, "message": "runtime offline", "base": base}

def write_launch_files():
    config = configure_default()
    model_path = config.get("selected_model_path") or "PASTE_MODEL_PATH_HERE.gguf"
    launch_dir = ROOT / "AI" / "Gateway"
    launch_dir.mkdir(parents=True, exist_ok=True)

    bat = f'''@echo off
title KayocktheOS Local Chat Runtime
color 0A
echo ==========================================
echo KayocktheOS Local Chat Runtime
echo ==========================================
echo.
echo This starter expects an OpenAI-compatible local server on port 8845.
echo.
echo Selected model:
echo {model_path}
echo.
echo Option A: If using llamafile, run something like:
echo llamafile.exe -m "{model_path}" --server --host 127.0.0.1 --port 8845
echo.
echo Option B: If using llama.cpp server, run something like:
echo llama-server.exe -m "{model_path}" --host 127.0.0.1 --port 8845
echo.
echo After the runtime is started, test:
echo http://127.0.0.1:8844/api/runtime
echo.
pause
'''
    (launch_dir / "START_LOCAL_CHAT_RUNTIME.bat").write_text(bat, encoding="utf-8")

    state = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "selected_model_path": model_path,
        "selected_model_name": config.get("active_chat_model"),
        "runtime_base": config.get("runtime_base"),
        "health": runtime_health(),
        "note": "This feature creates launch guidance first. Automatic process launch comes after we confirm the runtime executable path."
    }
    save_json(CHAT_STATE, state)
    return state

def chat_status():
    config = configure_default()
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 001 - Local Chat",
        "configured": bool(config.get("selected_model_path")),
        "selected_model": config.get("active_chat_model"),
        "selected_model_path": config.get("selected_model_path"),
        "runtime": runtime_health(),
        "available_models": foxai_models()[:20],
        "launch_helper": "AI/Gateway/START_LOCAL_CHAT_RUNTIME.bat"
    }

if __name__ == "__main__":
    write_launch_files()
    print(json.dumps(chat_status(), indent=2))
