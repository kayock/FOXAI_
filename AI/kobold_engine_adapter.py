from pathlib import Path
import json
import datetime
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
FOXAI = Path("Z:/FOXAI")
ENGINE_DIR = ROOT / "Engine" / "KoboldCpp"
GATEWAY = ROOT / "AI" / "Gateway"
CONFIG = GATEWAY / "engine_adapter_config.json"
STATE = GATEWAY / "kobold_adapter_state.json"

HOST = "127.0.0.1"
PORT = 5001
CONTEXT = 4096
BASE_URL = f"http://{HOST}:{PORT}"

KOBOLD_EXE_CANDIDATES = [
    ENGINE_DIR / "koboldcpp.exe",
    FOXAI / "Engine" / "koboldcpp.exe",
    FOXAI / "koboldcpp.exe",
]

KNOWN_GOOD_MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"

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

def quote(value):
    return '"' + str(value).replace('"', '') + '"'

def find_kobold_exe():
    for p in KOBOLD_EXE_CANDIDATES:
        if p.exists():
            return p
    for base in [ENGINE_DIR, FOXAI]:
        if base.exists():
            for p in base.rglob("koboldcpp*.exe"):
                return p
    return None

def find_model():
    if KNOWN_GOOD_MODEL.exists():
        return KNOWN_GOOD_MODEL
    chat = FOXAI / "Models" / "Chat"
    if chat.exists():
        # Avoid choosing vision models as the default chat engine.
        candidates = [p for p in chat.glob("*.gguf") if "vl" not in p.name.lower() and "vision" not in p.name.lower()]
        if candidates:
            return sorted(candidates, key=lambda x: x.name.lower())[0]
        models = sorted(chat.glob("*.gguf"), key=lambda x: x.name.lower())
        if models:
            return models[0]
    if FOXAI.exists():
        models = sorted(FOXAI.rglob("*.gguf"), key=lambda x: x.name.lower())
        if models:
            return models[0]
    return None

def probe(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw[:800]
            return {"ok": True, "status": res.status, "response": parsed}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def post_json(url, payload, timeout=180):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"text": raw}

def kobold_health():
    checks = {
        "root": probe(BASE_URL),
        "kobold_model": probe(BASE_URL + "/api/v1/model"),
        "kobold_version": probe(BASE_URL + "/api/v1/info/version"),
        "openai_models": probe(BASE_URL + "/v1/models"),
    }
    online = any(v.get("ok") for v in checks.values())
    return {"online": online, "base": BASE_URL, "checks": checks}

def write_config_and_launcher():
    exe = find_kobold_exe()
    model = find_model()

    config = {
        "adapter": "koboldcpp",
        "engine_name": "KoboldCpp",
        "host": HOST,
        "port": PORT,
        "base_url": BASE_URL,
        "openai_base_url": BASE_URL + "/v1",
        "kobold_api_url": BASE_URL + "/api/v1",
        "selected_engine_path": str(exe) if exe else None,
        "selected_model_path": str(model) if model else None,
        "context_tokens": CONTEXT,
        "mode": "advisor_only",
        "write_access": False,
        "operator_approval_required": True,
    }
    save_json(CONFIG, config)
    GATEWAY.mkdir(parents=True, exist_ok=True)

    if not exe:
        launcher = f"""@echo off
title KayocktheOS KoboldCpp Engine
color 0C
echo KoboldCpp was not found.
echo.
echo Put koboldcpp.exe here:
echo {ENGINE_DIR}\\koboldcpp.exe
echo.
pause
"""
    elif not model:
        launcher = """@echo off
title KayocktheOS KoboldCpp Engine
color 0C
echo No GGUF model found.
echo Expected model folder:
echo Z:\FOXAI\Models\Chat
pause
"""
    else:
        # Common KoboldCpp CLI form. If a specific KoboldCpp release uses a different flag,
        # this file is the only adapter layer we need to update.
        cmd = f'{quote(exe)} --model {quote(model)} --port {PORT} --contextsize {CONTEXT}'
        launcher = f"""@echo off
title KayocktheOS KoboldCpp Engine
color 0A
echo ==========================================
echo KayocktheOS KoboldCpp Engine Adapter
echo ==========================================
echo.
echo Engine:
echo {exe}
echo.
echo Model:
echo {model}
echo.
echo Server:
echo {BASE_URL}
echo.
echo Context:
echo {CONTEXT}
echo.
echo Leave this window open.
echo When KoboldCpp finishes loading, return to the Bridge.
echo.
{cmd}
pause
"""
    launcher_path = GATEWAY / "START_KOBOLD_ENGINE.bat"
    launcher_path.write_text(launcher, encoding="utf-8")

    state = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 004C - Kobold Core Repair",
        "engine_path": str(exe) if exe else None,
        "engine_exists": bool(exe),
        "model_path": str(model) if model else None,
        "model_exists": bool(model),
        "launcher": str(launcher_path),
        "health": kobold_health(),
        "config": str(CONFIG),
    }
    save_json(STATE, state)
    return state

def chat(prompt):
    cfg = load_json(CONFIG, {})
    base = cfg.get("base_url", BASE_URL)
    model_name = Path(cfg.get("selected_model_path") or "koboldcpp").name

    system = "You are a helpful local professor inside KayocktheOS. Be clear, practical, and advisor-only."
    openai_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 800,
        "stream": False
    }

    try:
        data = post_json(base + "/v1/chat/completions", openai_payload)
        text = data.get("choices", [{}])[0].get("message", {}).get("content")
        if text:
            return {"ok": True, "response": text, "raw": data, "engine": "koboldcpp-openai"}
    except Exception as openai_exc:
        openai_error = str(openai_exc)

    native_payload = {
        "prompt": f"{system}\n\nOperator: {prompt}\nProfessor:",
        "max_length": 800,
        "temperature": 0.4
    }

    try:
        data = post_json(base + "/api/v1/generate", native_payload)
        text = ""
        results = data.get("results") if isinstance(data, dict) else None
        if isinstance(results, list) and results:
            text = results[0].get("text", "")
        text = text or (data.get("text") if isinstance(data, dict) else "") or json.dumps(data)[:1200]
        return {"ok": True, "response": text, "raw": data, "engine": "koboldcpp-native"}
    except Exception as native_exc:
        return {
            "ok": False,
            "message": "KoboldCpp did not answer. Start AI\\Gateway\\START_KOBOLD_ENGINE.bat and wait for loading to complete.",
            "openai_error": openai_error,
            "native_error": str(native_exc),
        }

if __name__ == "__main__":
    print(json.dumps(write_config_and_launcher(), indent=2))
