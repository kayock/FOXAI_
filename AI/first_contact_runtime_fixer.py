from pathlib import Path
import json
import datetime
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FOXAI = Path("Z:/FOXAI")
LLAMA_SERVER = FOXAI / "Engine" / "llama-server.exe"
CHAT_MODELS = FOXAI / "Models" / "Chat"
GATEWAY = ROOT / "AI" / "Gateway"
CONFIG = GATEWAY / "gateway_config.json"
STATE = GATEWAY / "first_contact_runtime_fixer_state.json"

MODEL_PRIORITY = [
    "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
    "Qwen3VL-8B-Instruct-Q4_K_M.gguf",
    "Qwen3VL-8B-Instruct-Q8_0.gguf",
    "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
    "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf"
]

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

def choose_model():
    if CHAT_MODELS.exists():
        existing = {p.name: p for p in CHAT_MODELS.glob("*.gguf")}
        for name in MODEL_PRIORITY:
            if name in existing:
                return existing[name]
        models = sorted(CHAT_MODELS.glob("*.gguf"), key=lambda p: p.name.lower())
        if models:
            return models[0]
    all_models = sorted(FOXAI.rglob("*.gguf"), key=lambda p: p.name.lower()) if FOXAI.exists() else []
    return all_models[0] if all_models else None

def runtime_health():
    base = "http://127.0.0.1:8845"
    for url in [base + "/v1/models", base + "/health", base]:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                return {"online": True, "message": f"responded at {url}", "base": base}
        except Exception:
            pass
    return {"online": False, "message": "offline", "base": base}

def quote(path):
    return '"' + str(path).replace('"','') + '"'

def write_all():
    model = choose_model()
    GATEWAY.mkdir(parents=True, exist_ok=True)

    cfg = load_json(CONFIG, {})
    cfg.update({
        "mode": "advisor_only",
        "write_access": False,
        "operator_approval_required": True,
        "active_runtime": "llama_server_openai_compatible",
        "runtime_base": "http://127.0.0.1:8845",
        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",
        "active_chat_model": model.name if model else "local-model",
        "selected_model_path": str(model) if model else None,
        "selected_runtime_path": str(LLAMA_SERVER) if LLAMA_SERVER.exists() else None,
        "temperature": 0.4,
        "max_tokens": 1200,
        "timeout_seconds": 240
    })
    save_json(CONFIG, cfg)

    if not LLAMA_SERVER.exists():
        launcher = """@echo off
title KayocktheOS First Contact Runtime Fixer
color 0C
echo llama-server.exe was not found at:
echo Z:\\FOXAI\\Engine\\llama-server.exe
echo.
echo FOXAI Engine appears incomplete or moved.
pause
"""
    elif not model:
        launcher = """@echo off
title KayocktheOS First Contact Runtime Fixer
color 0C
echo No GGUF chat model found.
echo Expected:
echo Z:\\FOXAI\\Models\\Chat\\*.gguf
pause
"""
    else:
        command = f'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845'
        launcher = f"""@echo off
title KayocktheOS First Contact Runtime - llama-server
color 0A
echo ==========================================
echo KayocktheOS First Contact Runtime
echo ==========================================
echo.
echo Runtime locked to:
echo {LLAMA_SERVER}
echo.
echo Model selected:
echo {model}
echo.
echo Server:
echo http://127.0.0.1:8845
echo.
echo Leave this window open.
echo Wait until llama-server says it is listening.
echo Then open the Bridge and Ask the Academy.
echo.
{command}
pause
"""
    launcher_path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"
    launcher_path.write_text(launcher, encoding="utf-8")

    state = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 003E - First Contact Runtime Fixer",
        "runtime_locked_to": str(LLAMA_SERVER),
        "runtime_exists": LLAMA_SERVER.exists(),
        "model_selected": model.name if model else None,
        "model_path": str(model) if model else None,
        "launcher": str(launcher_path),
        "runtime": runtime_health(),
        "note": "This fixer intentionally ignores benchmark executables."
    }
    save_json(STATE, state)
    return state

if __name__ == "__main__":
    print(json.dumps(write_all(), indent=2))
