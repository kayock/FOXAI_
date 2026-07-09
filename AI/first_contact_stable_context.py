from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[1]
FOXAI = Path("Z:/FOXAI")
LLAMA_SERVER = FOXAI / "Engine" / "llama-server.exe"
MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
FALLBACK_MODEL = FOXAI / "Models" / "Chat" / "Qwen3VL-8B-Instruct-Q4_K_M.gguf"
GATEWAY = ROOT / "AI" / "Gateway"
CONFIG = GATEWAY / "gateway_config.json"
STATE = GATEWAY / "first_contact_stable_context_state.json"

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
    if MODEL.exists():
        return MODEL
    if FALLBACK_MODEL.exists():
        return FALLBACK_MODEL
    chat = FOXAI / "Models" / "Chat"
    if chat.exists():
        models = sorted(chat.glob("*.gguf"), key=lambda p: p.name.lower())
        if models:
            return models[0]
    return None

def quote(path):
    return '"' + str(path).replace('"', '') + '"'

def apply_fix():
    GATEWAY.mkdir(parents=True, exist_ok=True)
    model = choose_model()

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
        "context_tokens": 4096,
        "temperature": 0.4,
        "max_tokens": 1200,
        "timeout_seconds": 240
    })
    save_json(CONFIG, cfg)

    if not LLAMA_SERVER.exists():
        launcher = """@echo off
title KayocktheOS First Contact Runtime
color 0C
echo Missing:
echo Z:\\FOXAI\\Engine\\llama-server.exe
pause
"""
    elif not model:
        launcher = """@echo off
title KayocktheOS First Contact Runtime
color 0C
echo No GGUF model found in:
echo Z:\\FOXAI\\Models\\Chat
pause
"""
    else:
        cmd = f'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845 -c 4096'
        launcher = f"""@echo off
title KayocktheOS First Contact Runtime - Stable Context
color 0A
echo ==========================================
echo KayocktheOS First Contact Runtime
echo Stable Context: 4096
echo ==========================================
echo.
echo Runtime:
echo {LLAMA_SERVER}
echo.
echo Model:
echo {model}
echo.
echo Server:
echo http://127.0.0.1:8845
echo.
echo This launcher uses -c 4096 to avoid KV cache memory failure.
echo Leave this window open.
echo When llama-server says it is listening, return to the Bridge and Ask the Academy.
echo.
{cmd}
pause
"""
    launcher_path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"
    launcher_path.write_text(launcher, encoding="utf-8")

    state = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 003F - First Contact Stable Context",
        "runtime": str(LLAMA_SERVER),
        "model": str(model) if model else None,
        "context_tokens": 4096,
        "launcher": str(launcher_path),
        "known_good_command": f'{quote(LLAMA_SERVER)} -m {quote(model)} --host 127.0.0.1 --port 8845 -c 4096' if model else None
    }
    save_json(STATE, state)
    return state

if __name__ == "__main__":
    print(json.dumps(apply_fix(), indent=2))
