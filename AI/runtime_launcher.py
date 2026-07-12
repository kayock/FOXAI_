from pathlib import Path
import json
import datetime
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FOXAI_ROOT = Path("Z:/FOXAI")
GATEWAY_DIR = ROOT / "AI" / "Gateway"
CONFIG_PATH = GATEWAY_DIR / "gateway_config.json"
STATE_PATH = GATEWAY_DIR / "runtime_launcher_state.json"

RUNTIME_NAMES = ["llamafile.exe", "llama-server.exe", "server.exe", "llama.cpp.exe"]

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
    return load_json(CONFIG_PATH, {})

def find_runtimes():
    found = []
    if not FOXAI_ROOT.exists():
        return found
    for exe in FOXAI_ROOT.rglob("*.exe"):
        name = exe.name.lower()
        if name in RUNTIME_NAMES or "llama" in name or "llamafile" in name:
            try:
                found.append({
                    "name": exe.name,
                    "path": str(exe),
                    "modified": datetime.datetime.fromtimestamp(exe.stat().st_mtime).isoformat(timespec="seconds")
                })
            except Exception:
                pass
    return sorted(found, key=lambda x: x["name"].lower())

def selected_model():
    cfg = load_config()
    p = cfg.get("selected_model_path")
    if p and Path(p).exists():
        return {"name": Path(p).name, "path": p}
    inv = ROOT / "AI" / "Inventory" / "foxai_inventory.json"
    data = load_json(inv, {})
    models = data.get("assets", {}).get("llms", [])
    if models:
        m = models[0]
        return {"name": m.get("name"), "path": m.get("path")}
    return None

def runtime_health():
    base = load_config().get("runtime_base", "http://127.0.0.1:8845")
    for url in [base + "/v1/models", base + "/health", base]:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                return {"online": True, "message": f"responded at {url}", "base": base}
        except Exception:
            pass
    return {"online": False, "message": "runtime offline", "base": base}

def choose_runtime():
    runtimes = find_runtimes()
    if not runtimes:
        return None
    for rt in runtimes:
        if "llamafile" in rt["name"].lower():
            return rt
    for rt in runtimes:
        if "llama-server" in rt["name"].lower():
            return rt
    return runtimes[0]

def build_command():
    rt = choose_runtime()
    model = selected_model()
    if not rt or not model:
        return None

    exe = rt["path"]
    model_path = model["path"]
    lower = Path(exe).name.lower()

    if "llamafile" in lower:
        args = [exe, "-m", model_path, "--server", "--host", "127.0.0.1", "--port", "8845"]
    else:
        args = [exe, "-m", model_path, "--host", "127.0.0.1", "--port", "8845"]

    return {
        "runtime": rt,
        "model": model,
        "args": args,
        "display": " ".join(f'"{a}"' if " " in a else a for a in args)
    }

def write_launcher_bat():
    cmd = build_command()
    GATEWAY_DIR.mkdir(parents=True, exist_ok=True)
    if not cmd:
        content = (
            "@echo off\n"
            "title KayocktheOS Runtime Launcher\n"
            "color 0C\n"
            "echo Runtime or model not found.\n"
            "echo.\n"
            "echo Put llamafile.exe or llama-server.exe somewhere under Z:\\FOXAI.\n"
            "echo Make sure FOXAI Discovery found at least one GGUF model.\n"
            "pause\n"
        )
        (GATEWAY_DIR / "LAUNCH_SELECTED_MODEL_RUNTIME.bat").write_text(content, encoding="utf-8")
        return {"ok": False, "message": "runtime or model missing"}

    lines = [
        "@echo off",
        "title KayocktheOS Selected Model Runtime",
        "color 0A",
        "echo ==========================================",
        "echo KayocktheOS Local AI Runtime",
        "echo ==========================================",
        "echo.",
        f"echo Runtime: {cmd['runtime']['name']}",
        f"echo Model: {cmd['model']['name']}",
        "echo Port: 8845",
        "echo.",
        "echo Leave this window open while chatting.",
        "echo.",
        cmd["display"],
        "pause",
        ""
    ]
    (GATEWAY_DIR / "LAUNCH_SELECTED_MODEL_RUNTIME.bat").write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "launcher": "AI/Gateway/LAUNCH_SELECTED_MODEL_RUNTIME.bat", "command": cmd}

def status():
    launch = write_launcher_bat()
    payload = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 001B - Runtime Auto Launcher",
        "foxai_root": str(FOXAI_ROOT),
        "runtimes_found": find_runtimes(),
        "selected_runtime": choose_runtime(),
        "selected_model": selected_model(),
        "launch": launch,
        "health": runtime_health()
    }
    save_json(STATE_PATH, payload)
    return payload

if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
