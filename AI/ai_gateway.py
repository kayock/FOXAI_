from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "AI" / "Gateway"
CONFIG_PATH = CONFIG_DIR / "gateway_config.json"

DEFAULT_CONFIG = {
    "generated_at": None,
    "mode": "advisor_only",
    "write_access": False,
    "operator_approval_required": True,
    "active_chat_model": None,
    "active_runtime": None,
    "chat_endpoint": None,
    "safety_rules": [
        "No project file writes without Operator approval.",
        "No shell commands without Operator approval.",
        "No deleting, moving, or overwriting files automatically.",
        "All proposed code changes must be shown as a diff or patch first."
    ],
    "supported_runtimes": [
        {"id": "llamafile", "name": "Llamafile", "status": "planned", "default_port": 8845},
        {"id": "llama_cpp_server", "name": "llama.cpp server", "status": "planned", "default_port": 8845},
        {"id": "ollama", "name": "Ollama", "status": "future", "default_port": 11434}
    ]
}

def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    config = DEFAULT_CONFIG.copy()
    config["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config

def load_foxai_inventory():
    path = ROOT / "AI" / "Inventory" / "foxai_inventory.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def recommend_chat_models(limit=8):
    inv = load_foxai_inventory()
    if not inv:
        return []
    models = inv.get("assets", {}).get("llms", [])
    scored = []
    for model in models:
        caps = set(model.get("capabilities", []))
        score = 0
        name = model.get("name", "").lower()
        if "chat" in caps:
            score += 2
        if "reasoning" in caps:
            score += 3
        if "coding" in caps:
            score += 2
        if "vision" in caps:
            score += 1
        if "q4" in name:
            score += 2
        if "8b" in name or "14b" in name:
            score += 2
        if "32b" in name or "30b" in name:
            score -= 1
        scored.append({**model, "gateway_score": score})
    return sorted(scored, key=lambda x: (-x["gateway_score"], x["size_gb"], x["name"]))[:limit]

def gateway_status():
    config = ensure_config()
    candidates = recommend_chat_models()
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "status": "configured",
        "mode": config.get("mode", "advisor_only"),
        "write_access": bool(config.get("write_access")),
        "operator_approval_required": bool(config.get("operator_approval_required", True)),
        "active_chat_model": config.get("active_chat_model"),
        "active_runtime": config.get("active_runtime"),
        "chat_endpoint": config.get("chat_endpoint"),
        "supported_runtimes": config.get("supported_runtimes", []),
        "recommended_chat_models": candidates,
        "safety_rules": config.get("safety_rules", [])
    }

def chat_placeholder(prompt, context=None):
    return {
        "ok": False,
        "mode": "placeholder",
        "message": "AI Gateway is installed, but no local model runtime is connected yet.",
        "next_step": "Connect llamafile or llama.cpp server on localhost:8845.",
        "received_prompt_preview": str(prompt or "")[:500],
        "gateway": gateway_status()
    }

if __name__ == "__main__":
    print(json.dumps(gateway_status(), indent=2))
