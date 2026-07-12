from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.3.0_before_ai_gateway_stub_{STAMP}"

GATEWAY_PY = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nCONFIG_DIR = ROOT / "AI" / "Gateway"\nCONFIG_PATH = CONFIG_DIR / "gateway_config.json"\n\nDEFAULT_CONFIG = {\n    "generated_at": None,\n    "mode": "advisor_only",\n    "write_access": False,\n    "operator_approval_required": True,\n    "active_chat_model": None,\n    "active_runtime": None,\n    "chat_endpoint": None,\n    "safety_rules": [\n        "No project file writes without Operator approval.",\n        "No shell commands without Operator approval.",\n        "No deleting, moving, or overwriting files automatically.",\n        "All proposed code changes must be shown as a diff or patch first."\n    ],\n    "supported_runtimes": [\n        {"id": "llamafile", "name": "Llamafile", "status": "planned", "default_port": 8845},\n        {"id": "llama_cpp_server", "name": "llama.cpp server", "status": "planned", "default_port": 8845},\n        {"id": "ollama", "name": "Ollama", "status": "future", "default_port": 11434}\n    ]\n}\n\ndef ensure_config():\n    CONFIG_DIR.mkdir(parents=True, exist_ok=True)\n    if CONFIG_PATH.exists():\n        try:\n            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))\n        except Exception:\n            pass\n    config = DEFAULT_CONFIG.copy()\n    config["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")\n    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")\n    return config\n\ndef load_foxai_inventory():\n    path = ROOT / "AI" / "Inventory" / "foxai_inventory.json"\n    if not path.exists():\n        return None\n    try:\n        return json.loads(path.read_text(encoding="utf-8"))\n    except Exception:\n        return None\n\ndef recommend_chat_models(limit=8):\n    inv = load_foxai_inventory()\n    if not inv:\n        return []\n    models = inv.get("assets", {}).get("llms", [])\n    scored = []\n    for model in models:\n        caps = set(model.get("capabilities", []))\n        score = 0\n        name = model.get("name", "").lower()\n        if "chat" in caps:\n            score += 2\n        if "reasoning" in caps:\n            score += 3\n        if "coding" in caps:\n            score += 2\n        if "vision" in caps:\n            score += 1\n        if "q4" in name:\n            score += 2\n        if "8b" in name or "14b" in name:\n            score += 2\n        if "32b" in name or "30b" in name:\n            score -= 1\n        scored.append({**model, "gateway_score": score})\n    return sorted(scored, key=lambda x: (-x["gateway_score"], x["size_gb"], x["name"]))[:limit]\n\ndef gateway_status():\n    config = ensure_config()\n    candidates = recommend_chat_models()\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "status": "configured",\n        "mode": config.get("mode", "advisor_only"),\n        "write_access": bool(config.get("write_access")),\n        "operator_approval_required": bool(config.get("operator_approval_required", True)),\n        "active_chat_model": config.get("active_chat_model"),\n        "active_runtime": config.get("active_runtime"),\n        "chat_endpoint": config.get("chat_endpoint"),\n        "supported_runtimes": config.get("supported_runtimes", []),\n        "recommended_chat_models": candidates,\n        "safety_rules": config.get("safety_rules", [])\n    }\n\ndef chat_placeholder(prompt, context=None):\n    return {\n        "ok": False,\n        "mode": "placeholder",\n        "message": "AI Gateway is installed, but no local model runtime is connected yet.",\n        "next_step": "Connect llamafile or llama.cpp server on localhost:8845.",\n        "received_prompt_preview": str(prompt or "")[:500],\n        "gateway": gateway_status()\n    }\n\nif __name__ == "__main__":\n    print(json.dumps(gateway_status(), indent=2))\n'
POST_METHOD = '    def do_POST(self):\n        path = urllib.parse.urlparse(self.path).path\n        length = int(self.headers.get("Content-Length", "0") or "0")\n        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"\n        try:\n            payload = json.loads(raw)\n        except Exception:\n            payload = {"prompt": raw}\n        if path == "/api/chat":\n            self._json(ai_chat_placeholder(payload.get("prompt", ""), payload.get("context")))\n        else:\n            self._json({"error": "not found", "available": ["/api/chat"]}, 404)\n\n'

def info(msg):
    print(f"[KayocktheOS v1.3.0] {msg}")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

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

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_gateway():
    write_text("AI/ai_gateway.py", GATEWAY_PY)
    spec = importlib.util.spec_from_file_location("kayock_ai_gateway", ROOT / "AI/ai_gateway.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    status = mod.gateway_status()
    info(f"AI Gateway installed. Recommended model candidates: {len(status['recommended_chat_models'])}")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; AI Gateway installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def ai_gateway_status(" not in old:
        insert = """
def ai_gateway_status():
    try:
        gateway = ROOT / "AI" / "ai_gateway.py"
        if gateway.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_ai_gateway", gateway)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.gateway_status()
    except Exception as exc:
        return {"error": str(exc), "status": "error"}
    return {"status": "missing"}

def ai_chat_placeholder(prompt="", context=None):
    try:
        gateway = ROOT / "AI" / "ai_gateway.py"
        if gateway.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_ai_gateway", gateway)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat_placeholder(prompt, context)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "AI Gateway missing."}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"ai_gateway": ai_gateway_status(),' not in old:
        if '"foxai": foxai_status(),' in old:
            old = old.replace('"foxai": foxai_status(),', '"foxai": foxai_status(),\n        "ai_gateway": ai_gateway_status(),')
        elif '"ai_assets": ai_assets(),' in old:
            old = old.replace('"ai_assets": ai_assets(),', '"ai_assets": ai_assets(),\n        "ai_gateway": ai_gateway_status(),')
        elif '"system": system_scan(),' in old:
            old = old.replace('"system": system_scan(),', '"system": system_scan(),\n        "ai_gateway": ai_gateway_status(),')

    if 'elif path == "/api/ai-gateway":' not in old:
        if 'elif path == "/api/foxai":' in old:
            old = old.replace(
                'elif path == "/api/foxai":\n            self._json(foxai_status())',
                'elif path == "/api/foxai":\n            self._json(foxai_status())\n        elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())'
            )
        else:
            old = old.replace(
                'elif path == "/api/system":\n            self._json(system_scan())',
                'elif path == "/api/system":\n            self._json(system_scan())\n        elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())'
            )

    if "def do_POST(self):" not in old:
        old = old.replace("    def log_message(self, format, *args):", POST_METHOD + "    def log_message(self, format, *args):")

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/ai-gateway and POST /api/chat placeholder.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 1.3.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: AI Gateway Stub", text, count=1)
        if "ai_gateway_stub: enabled" not in text:
            text += "\n  ai_gateway_stub: enabled\n" if "features:" in text else "\nfeatures:\n  ai_gateway_stub: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/AI_GATEWAY.md", """# AI Gateway

v1.3.0 creates the safe AI Gateway layer.

## Endpoints

```text
GET  http://127.0.0.1:8844/api/ai-gateway
POST http://127.0.0.1:8844/api/chat
```

`/api/chat` is a placeholder until a local model runtime is connected.

## Safety

- Advisor-only mode by default
- No write access
- Operator approval required
- No automatic project edits
""")
    write_text("Forge/Decisions/0014_ai_gateway_stub.md", """# Decision 0014 - AI Gateway Stub

KayocktheOS modules talk to one AI Gateway instead of directly talking to models.

The first gateway is safe and advisor-only.
""")
    write_text("Foundry/Releases/v1.3.0_release_notes.md", "# v1.3.0 Release Notes - AI Gateway Stub\n\nAdds `AI/ai_gateway.py`, `/api/ai-gateway`, and guarded placeholder `/api/chat`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.3.0 - AI Gateway Stub\n\n- Added `AI/ai_gateway.py`.\n- Added AI Gateway config.\n- Added `/api/ai-gateway`.\n- Added guarded placeholder `POST /api/chat`.\n- No local model execution yet.\n"
    if "v1.3.0 - AI Gateway Stub" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_gateway()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v1.3.0 AI Gateway Stub patch complete.")
    info("Restart KayocktheOS and test /api/ai-gateway.")

if __name__ == "__main__":
    main()
