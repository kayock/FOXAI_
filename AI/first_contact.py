from pathlib import Path
import json
import datetime
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FOXAI = Path("Z:/FOXAI")
GATEWAY = ROOT / "AI" / "Gateway"
CONFIG = GATEWAY / "gateway_config.json"
STATE = GATEWAY / "first_contact_state.json"

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

def scan_models():
    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"
    data = load_json(inv, {})
    models = data.get("assets", {}).get("llms", [])
    if models:
        return models
    if not FOXAI.exists():
        return []
    out = []
    for p in FOXAI.rglob("*.gguf"):
        try:
            out.append({"name": p.name, "path": str(p), "size_gb": round(p.stat().st_size/(1024**3), 3), "capabilities": infer_caps(p.name)})
        except Exception:
            pass
    return sorted(out, key=lambda m: m["name"].lower())

def infer_caps(name):
    n = name.lower()
    caps = ["chat"]
    if "deepseek" in n or "r1" in n: caps.append("reasoning")
    if "coder" in n or "code" in n: caps.append("coding")
    if "vl" in n or "vision" in n: caps.append("vision")
    return sorted(set(caps))

def choose_model():
    models = scan_models()
    if not models:
        return None
    scored = []
    for m in models:
        n = m.get("name","").lower()
        score = 0
        if "deepseek" in n and "14b" in n: score += 50
        if "qwen" in n and ("8b" in n or "q4" in n): score += 40
        if "q4" in n: score += 20
        if "q8" in n: score += 10
        if "32b" in n or "30b" in n: score -= 10
        if "coder" in n: score += 5
        scored.append((score, m))
    return sorted(scored, key=lambda x: (-x[0], x[1].get("size_gb", 999)))[0][1]

def scan_runtimes():
    if not FOXAI.exists():
        return []
    found = []
    for exe in FOXAI.rglob("*.exe"):
        n = exe.name.lower()
        if "llama" in n or "llamafile" in n or n in ("server.exe", "koboldcpp.exe"):
            found.append({"name": exe.name, "path": str(exe)})
    return sorted(found, key=lambda r: (0 if "llamafile" in r["name"].lower() else 1, r["name"].lower()))

def choose_runtime():
    rts = scan_runtimes()
    return rts[0] if rts else None

def runtime_health():
    base = "http://127.0.0.1:8845"
    for url in [base + "/v1/models", base + "/health", base]:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                return {"online": True, "base": base, "message": f"responded at {url}"}
        except Exception:
            pass
    return {"online": False, "base": base, "message": "offline"}

def configure():
    model = choose_model()
    runtime = choose_runtime()
    cfg = load_json(CONFIG, {})
    cfg.update({
        "mode": "advisor_only",
        "write_access": False,
        "operator_approval_required": True,
        "active_runtime": "openai_compatible",
        "runtime_base": "http://127.0.0.1:8845",
        "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",
        "active_chat_model": model["name"] if model else "local-model",
        "selected_model_path": model["path"] if model else None,
        "selected_runtime_path": runtime["path"] if runtime else None,
        "temperature": 0.4,
        "max_tokens": 1200,
        "timeout_seconds": 240
    })
    save_json(CONFIG, cfg)
    return cfg

def quote(arg):
    return '"' + str(arg).replace('"','') + '"'

def write_launcher():
    cfg = configure()
    model = cfg.get("selected_model_path")
    runtime = cfg.get("selected_runtime_path")
    GATEWAY.mkdir(parents=True, exist_ok=True)

    if not model or not runtime:
        text = """@echo off
title KayocktheOS First Contact Runtime
color 0C
echo First Contact cannot launch yet.
echo.
echo Missing model or runtime.
echo.
echo Need:
echo   - At least one .gguf model under Z:\\FOXAI
echo   - A runtime exe under Z:\\FOXAI, such as llamafile.exe or llama-server.exe
echo.
pause
"""
    else:
        exe_name = Path(runtime).name.lower()
        if "llamafile" in exe_name:
            cmd = f'{quote(runtime)} -m {quote(model)} --server --host 127.0.0.1 --port 8845'
        else:
            cmd = f'{quote(runtime)} -m {quote(model)} --host 127.0.0.1 --port 8845'
        text = f"""@echo off
title KayocktheOS First Contact Runtime
color 0A
echo ==========================================
echo KayocktheOS First Contact Runtime
echo ==========================================
echo.
echo Runtime:
echo {runtime}
echo.
echo Model:
echo {model}
echo.
echo Leave this window open.
echo When the server is loaded, return to the Bridge and ask the Academy.
echo.
{cmd}
pause
"""
    path = GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"
    path.write_text(text, encoding="utf-8")
    return str(path)

def chat(prompt):
    cfg = configure()
    payload = {
        "model": cfg.get("active_chat_model", "local-model"),
        "messages": [
            {"role": "system", "content": "You are a local professor inside KayocktheOS. You are advisor-only. Do not claim to edit files. Explain clearly and wait for Operator approval before changes."},
            {"role": "user", "content": prompt}
        ],
        "temperature": cfg.get("temperature", 0.4),
        "max_tokens": cfg.get("max_tokens", 1200),
        "stream": False
    }
    try:
        req = urllib.request.Request(cfg["chat_endpoint"], data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=int(cfg.get("timeout_seconds",240))) as res:
            raw = res.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", raw)
        return {"ok": True, "response": content, "raw": data}
    except Exception as exc:
        return {"ok": False, "message": "First Contact failed. Start FIRST_CONTACT_START_RUNTIME.bat, wait for the model to load, then try again.", "error": str(exc)}

def status():
    cfg = configure()
    launcher = write_launcher()
    payload = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 003 - First Contact",
        "model": cfg.get("active_chat_model"),
        "model_path": cfg.get("selected_model_path"),
        "runtime_path": cfg.get("selected_runtime_path"),
        "runtime": runtime_health(),
        "launcher": launcher,
        "ready_for_contact": bool(cfg.get("selected_model_path") and cfg.get("selected_runtime_path")),
        "instructions": [
            "Run AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat",
            "Wait until the model server finishes loading.",
            "Open the Bridge.",
            "Ask the Academy."
        ]
    }
    save_json(STATE, payload)
    return payload

if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
