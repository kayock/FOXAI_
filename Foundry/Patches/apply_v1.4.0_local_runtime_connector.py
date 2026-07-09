from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.4.0_before_runtime_connector_{STAMP}"

RUNTIME_PY = 'from pathlib import Path\nimport json\nimport urllib.request\nimport urllib.error\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nCONFIG_DIR = ROOT / "AI" / "Gateway"\nCONFIG_PATH = CONFIG_DIR / "gateway_config.json"\n\nDEFAULT_CONFIG = {\n    "mode": "advisor_only",\n    "write_access": False,\n    "operator_approval_required": True,\n    "active_runtime": "openai_compatible",\n    "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",\n    "active_chat_model": "local-model",\n    "timeout_seconds": 120,\n    "temperature": 0.4,\n    "max_tokens": 1024\n}\n\ndef load_config():\n    CONFIG_DIR.mkdir(parents=True, exist_ok=True)\n    if CONFIG_PATH.exists():\n        try:\n            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))\n            merged = {**DEFAULT_CONFIG, **loaded}\n            CONFIG_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")\n            return merged\n        except Exception:\n            pass\n    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")\n    return DEFAULT_CONFIG.copy()\n\ndef runtime_health():\n    config = load_config()\n    endpoint = config.get("chat_endpoint")\n    base = endpoint.rsplit("/v1/", 1)[0] if endpoint and "/v1/" in endpoint else "http://127.0.0.1:8845"\n    health = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "configured": bool(endpoint),\n        "endpoint": endpoint,\n        "base": base,\n        "runtime": config.get("active_runtime"),\n        "online": False,\n        "message": "offline"\n    }\n\n    for test_url in [base + "/v1/models", base + "/health", base]:\n        try:\n            req = urllib.request.Request(test_url, method="GET")\n            with urllib.request.urlopen(req, timeout=2) as res:\n                health["online"] = True\n                health["message"] = f"responded at {test_url}"\n                try:\n                    health["probe"] = json.loads(res.read().decode("utf-8", errors="replace"))\n                except Exception:\n                    health["probe"] = "non-json response"\n                return health\n        except Exception:\n            continue\n    return health\n\ndef chat(prompt, context=None):\n    config = load_config()\n    endpoint = config.get("chat_endpoint")\n    if not endpoint:\n        return {\n            "ok": False,\n            "message": "No local runtime endpoint configured.",\n            "next_step": "Set AI/Gateway/gateway_config.json chat_endpoint."\n        }\n\n    messages = []\n    messages.append({\n        "role": "system",\n        "content": (\n            "You are the local KayocktheOS AI advisor. "\n            "You are advisor-only. Do not claim you changed files. "\n            "When proposing project changes, describe them clearly and wait for Operator approval."\n        )\n    })\n    if context:\n        messages.append({"role": "system", "content": "Context: " + json.dumps(context)[:4000]})\n    messages.append({"role": "user", "content": str(prompt or "")})\n\n    payload = {\n        "model": config.get("active_chat_model") or "local-model",\n        "messages": messages,\n        "temperature": config.get("temperature", 0.4),\n        "max_tokens": config.get("max_tokens", 1024),\n        "stream": False\n    }\n\n    try:\n        data = json.dumps(payload).encode("utf-8")\n        req = urllib.request.Request(\n            endpoint,\n            data=data,\n            headers={"Content-Type": "application/json"},\n            method="POST"\n        )\n        with urllib.request.urlopen(req, timeout=int(config.get("timeout_seconds", 120))) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n            try:\n                response = json.loads(raw)\n            except Exception:\n                return {"ok": True, "raw": raw}\n\n        text = ""\n        try:\n            text = response["choices"][0]["message"]["content"]\n        except Exception:\n            text = json.dumps(response)[:4000]\n\n        return {\n            "ok": True,\n            "runtime": config.get("active_runtime"),\n            "endpoint": endpoint,\n            "model": payload["model"],\n            "response": text,\n            "raw": response\n        }\n    except urllib.error.URLError as exc:\n        return {\n            "ok": False,\n            "message": "Local model runtime is not reachable.",\n            "error": str(exc),\n            "next_step": "Start llamafile or llama.cpp server on port 8845."\n        }\n    except Exception as exc:\n        return {"ok": False, "message": "Local chat request failed.", "error": str(exc)}\n\nif __name__ == "__main__":\n    print(json.dumps(runtime_health(), indent=2))\n'

def info(msg):
    print(f"[KayocktheOS v1.4.0] {msg}")

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

def install_runtime_connector():
    write_text("AI/local_runtime.py", RUNTIME_PY)
    write_text("AI/Gateway/README_LOCAL_RUNTIME.md", """# Local Runtime Connector

Default endpoint:

```text
http://127.0.0.1:8845/v1/chat/completions
```

Start a compatible model server there, then KayocktheOS can use `POST /api/chat`.

Compatible targets later:
- llamafile OpenAI-compatible server
- llama.cpp server
- other OpenAI-compatible local server
""")
    spec = importlib.util.spec_from_file_location("kayock_local_runtime", ROOT / "AI/local_runtime.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    health = mod.runtime_health()
    info("Local runtime connector installed. Online: " + str(health.get("online")))

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; runtime connector installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def local_runtime_health(" not in old:
        insert = """
def local_runtime_health():
    try:
        runtime = ROOT / "AI" / "local_runtime.py"
        if runtime.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_runtime", runtime)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.runtime_health()
    except Exception as exc:
        return {"online": False, "error": str(exc)}
    return {"online": False, "message": "local runtime connector missing"}

def ai_chat(prompt="", context=None):
    try:
        runtime = ROOT / "AI" / "local_runtime.py"
        if runtime.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_runtime", runtime)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt, context)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return ai_chat_placeholder(prompt, context)
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"local_runtime": local_runtime_health(),' not in old:
        if '"ai_gateway": ai_gateway_status(),' in old:
            old = old.replace('"ai_gateway": ai_gateway_status(),', '"ai_gateway": ai_gateway_status(),\n        "local_runtime": local_runtime_health(),')
        else:
            old = old.replace('"system": system_scan(),', '"system": system_scan(),\n        "local_runtime": local_runtime_health(),')

    # Change POST /api/chat handler from placeholder to runtime connector if present.
    old = old.replace("self._json(ai_chat_placeholder(payload.get(\"prompt\", \"\"), payload.get(\"context\")))", "self._json(ai_chat(payload.get(\"prompt\", \"\"), payload.get(\"context\")))")

    if 'elif path == "/api/runtime":' not in old:
        if 'elif path == "/api/ai-gateway":' in old:
            old = old.replace(
                'elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())',
                'elif path == "/api/ai-gateway":\n            self._json(ai_gateway_status())\n        elif path == "/api/runtime":\n            self._json(local_runtime_health())'
            )

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/runtime and runtime-backed POST /api/chat.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 1.4.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Local Runtime Connector", text, count=1)
        if "local_runtime_connector: enabled" not in text:
            text += "\n  local_runtime_connector: enabled\n" if "features:" in text else "\nfeatures:\n  local_runtime_connector: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/LOCAL_RUNTIME_CONNECTOR.md", """# Local Runtime Connector

v1.4.0 connects the AI Gateway to an OpenAI-compatible local model runtime.

## Endpoints

```text
GET  http://127.0.0.1:8844/api/runtime
POST http://127.0.0.1:8844/api/chat
```

## Expected local model runtime

```text
http://127.0.0.1:8845/v1/chat/completions
```

If no model runtime is running, `/api/chat` fails safely and explains what to start.
""")
    write_text("Forge/Decisions/0015_local_runtime_connector.md", """# Decision 0015 - Local Runtime Connector

KayocktheOS uses a stable `/api/chat` endpoint.

The actual model runtime may change, but the Shell and Academy should not need to know.
""")
    write_text("Foundry/Releases/v1.4.0_release_notes.md", "# v1.4.0 Release Notes - Local Runtime Connector\n\nAdds `AI/local_runtime.py`, `/api/runtime`, and runtime-backed `/api/chat`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.4.0 - Local Runtime Connector\n\n- Added `AI/local_runtime.py`.\n- Added `/api/runtime`.\n- Updated `POST /api/chat` to call a localhost OpenAI-compatible runtime when available.\n- Safe fallback remains when no runtime is online.\n"
    if "v1.4.0 - Local Runtime Connector" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_runtime_connector()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v1.4.0 Local Runtime Connector patch complete.")
    info("Restart KayocktheOS and test /api/runtime.")

if __name__ == "__main__":
    main()
