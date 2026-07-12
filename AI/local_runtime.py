from pathlib import Path
import json
import urllib.request
import urllib.error
import datetime

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "AI" / "Gateway"
CONFIG_PATH = CONFIG_DIR / "gateway_config.json"

DEFAULT_CONFIG = {
    "mode": "advisor_only",
    "write_access": False,
    "operator_approval_required": True,
    "active_runtime": "openai_compatible",
    "chat_endpoint": "http://127.0.0.1:8845/v1/chat/completions",
    "active_chat_model": "local-model",
    "timeout_seconds": 120,
    "temperature": 0.4,
    "max_tokens": 1024
}

def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_CONFIG, **loaded}
            CONFIG_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            return merged
        except Exception:
            pass
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG.copy()

def runtime_health():
    config = load_config()
    endpoint = config.get("chat_endpoint")
    base = endpoint.rsplit("/v1/", 1)[0] if endpoint and "/v1/" in endpoint else "http://127.0.0.1:8845"
    health = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "configured": bool(endpoint),
        "endpoint": endpoint,
        "base": base,
        "runtime": config.get("active_runtime"),
        "online": False,
        "message": "offline"
    }

    for test_url in [base + "/v1/models", base + "/health", base]:
        try:
            req = urllib.request.Request(test_url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as res:
                health["online"] = True
                health["message"] = f"responded at {test_url}"
                try:
                    health["probe"] = json.loads(res.read().decode("utf-8", errors="replace"))
                except Exception:
                    health["probe"] = "non-json response"
                return health
        except Exception:
            continue
    return health

def chat(prompt, context=None):
    config = load_config()
    endpoint = config.get("chat_endpoint")
    if not endpoint:
        return {
            "ok": False,
            "message": "No local runtime endpoint configured.",
            "next_step": "Set AI/Gateway/gateway_config.json chat_endpoint."
        }

    messages = []
    messages.append({
        "role": "system",
        "content": (
            "You are the local KayocktheOS AI advisor. "
            "You are advisor-only. Do not claim you changed files. "
            "When proposing project changes, describe them clearly and wait for Operator approval."
        )
    })
    if context:
        messages.append({"role": "system", "content": "Context: " + json.dumps(context)[:4000]})
    messages.append({"role": "user", "content": str(prompt or "")})

    payload = {
        "model": config.get("active_chat_model") or "local-model",
        "messages": messages,
        "temperature": config.get("temperature", 0.4),
        "max_tokens": config.get("max_tokens", 1024),
        "stream": False
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=int(config.get("timeout_seconds", 120))) as res:
            raw = res.read().decode("utf-8", errors="replace")
            try:
                response = json.loads(raw)
            except Exception:
                return {"ok": True, "raw": raw}

        text = ""
        try:
            text = response["choices"][0]["message"]["content"]
        except Exception:
            text = json.dumps(response)[:4000]

        return {
            "ok": True,
            "runtime": config.get("active_runtime"),
            "endpoint": endpoint,
            "model": payload["model"],
            "response": text,
            "raw": response
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "message": "Local model runtime is not reachable.",
            "error": str(exc),
            "next_step": "Start llamafile or llama.cpp server on port 8845."
        }
    except Exception as exc:
        return {"ok": False, "message": "Local chat request failed.", "error": str(exc)}

if __name__ == "__main__":
    print(json.dumps(runtime_health(), indent=2))
