from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[1]
FOXAI = Path("Z:/FOXAI")
GATEWAY = ROOT / "AI" / "Gateway"
PROFILES = GATEWAY / "model_profiles.json"
ACTIVE = GATEWAY / "active_model_profile.json"
CONFIG = GATEWAY / "engine_adapter_config.json"

DEFAULT_PROFILES = {
    "safe": {
        "label": "Safe Portable",
        "description": "Best default for this USB and midrange machines.",
        "model": "Z:/FOXAI/Models/Chat/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "context_tokens": 4096,
        "purpose": ["chat", "reasoning", "architecture"],
        "default": True
    },
    "power": {
        "label": "Power Workstation",
        "description": "For stronger computers with more RAM/VRAM.",
        "model": "Z:/FOXAI/Models/Chat/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        "context_tokens": 4096,
        "purpose": ["coding", "engineering", "large reasoning"],
        "default": False
    },
    "vision": {
        "label": "Vision",
        "description": "For image/vision tasks. Not the default chat model.",
        "model": "Z:/FOXAI/Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf",
        "context_tokens": 2048,
        "purpose": ["vision", "image analysis"],
        "default": False
    }
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

def materialize_profiles():
    profiles = load_json(PROFILES, DEFAULT_PROFILES)
    changed = False

    for key, val in DEFAULT_PROFILES.items():
        if key not in profiles:
            profiles[key] = val
            changed = True

    # Add existence flags dynamically.
    for key, val in profiles.items():
        p = Path(val.get("model", ""))
        val["model_exists"] = p.exists()
        val["model_name"] = p.name if p.name else "Unknown"

    if changed or not PROFILES.exists():
        save_json(PROFILES, profiles)

    active = load_json(ACTIVE, {})
    if not active.get("profile"):
        active = {"profile": "safe", "updated_at": datetime.datetime.now().isoformat(timespec="seconds")}
        save_json(ACTIVE, active)

    return profiles, active

def get_active_profile():
    profiles, active = materialize_profiles()
    key = active.get("profile", "safe")
    if key not in profiles:
        key = "safe"
    return key, profiles[key], profiles

def set_profile(profile):
    profiles, _ = materialize_profiles()
    if profile not in profiles:
        return {"ok": False, "error": f"Unknown profile: {profile}", "available": list(profiles.keys())}
    save_json(ACTIVE, {"profile": profile, "updated_at": datetime.datetime.now().isoformat(timespec="seconds")})
    apply_active_profile()
    return {"ok": True, "profile": profile, "active": profiles[profile]}

def apply_active_profile():
    key, profile, profiles = get_active_profile()
    cfg = load_json(CONFIG, {})
    cfg.update({
        "model_profile": key,
        "active_chat_model": profile.get("model_name") or Path(profile.get("model", "")).name,
        "selected_model_path": profile.get("model"),
        "context_tokens": profile.get("context_tokens", 4096),
        "model_profile_label": profile.get("label"),
        "model_profile_description": profile.get("description"),
    })
    save_json(CONFIG, cfg)
    rewrite_launcher(cfg)
    return {"ok": True, "profile": key, "config": cfg, "profiles": profiles}

def quote(value):
    return '"' + str(value).replace('"', '') + '"'

def rewrite_launcher(cfg):
    engine = cfg.get("selected_engine_path") or "Z:/KayocktheOS/Engine/KoboldCpp/koboldcpp.exe"
    model = cfg.get("selected_model_path")
    context = cfg.get("context_tokens", 4096)
    port = cfg.get("port", 5001)

    launcher_path = GATEWAY / "START_KOBOLD_ENGINE.bat"
    if not model:
        text = """@echo off
title KayocktheOS KoboldCpp Engine
color 0C
echo No active model profile selected.
pause
"""
    else:
        text = f"""@echo off
title KayocktheOS KoboldCpp Engine - {cfg.get('model_profile_label', 'Profile')}
color 0A
echo ==========================================
echo KayocktheOS KoboldCpp Engine Adapter
echo Profile: {cfg.get('model_profile_label', 'Unknown')}
echo ==========================================
echo.
echo Engine:
echo {engine}
echo.
echo Model:
echo {model}
echo.
echo Context:
echo {context}
echo.
echo Server:
echo http://127.0.0.1:{port}
echo.
echo Leave this window open.
echo.
{quote(engine)} --model {quote(model)} --port {port} --contextsize {context}
pause
"""
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(text, encoding="utf-8")

def status():
    profiles, active = materialize_profiles()
    applied = apply_active_profile()
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "feature": "Feature 004D - Model Profiles",
        "active": active,
        "profiles": profiles,
        "applied": applied
    }

if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
