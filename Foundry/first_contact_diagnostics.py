from pathlib import Path
import json
import datetime
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "Foundry" / "Reports"
CONFIG = ROOT / "AI" / "Gateway" / "gateway_config.json"

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"_error": str(exc), **default}
    return default

def probe(url, method="GET", data=None):
    try:
        body = None
        headers = {}
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw[:1000]
            return {"ok": True, "status": res.status, "response": parsed}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def run_diagnostics():
    cfg = load_json(CONFIG, {})
    base = cfg.get("runtime_base", "http://127.0.0.1:8845")
    endpoint = cfg.get("chat_endpoint", base + "/v1/chat/completions")
    model = cfg.get("active_chat_model", "local-model")

    test_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a KayocktheOS First Contact diagnostic responder. Answer briefly."},
            {"role": "user", "content": "Say: First Contact diagnostic successful."}
        ],
        "temperature": 0.2,
        "max_tokens": 80,
        "stream": False
    }

    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "config": {
            "runtime_base": base,
            "chat_endpoint": endpoint,
            "active_chat_model": model,
            "selected_runtime_path": cfg.get("selected_runtime_path"),
            "selected_model_path": cfg.get("selected_model_path")
        },
        "checks": {
            "runtime_base": probe(base),
            "models_endpoint": probe(base + "/v1/models"),
            "chat_endpoint": probe(endpoint, "POST", test_payload),
            "kayock_core_ping": probe("http://127.0.0.1:8844/api/ping"),
            "kayock_first_contact": probe("http://127.0.0.1:8844/api/first-contact")
        }
    }

    report["overall"] = "ok" if report["checks"]["chat_endpoint"]["ok"] else "needs_review"
    return report

def write_report():
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = run_diagnostics()
    (REPORTS / "first_contact_diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# First Contact Diagnostics",
        "",
        f"Generated: {report['generated_at']}",
        f"Overall: {report['overall']}",
        "",
        "## Config",
        "",
        f"- Runtime: `{report['config'].get('selected_runtime_path')}`",
        f"- Model: `{report['config'].get('selected_model_path')}`",
        f"- Endpoint: `{report['config'].get('chat_endpoint')}`",
        "",
        "## Checks",
        ""
    ]

    for name, result in report["checks"].items():
        mark = "✅" if result.get("ok") else "❌"
        detail = result.get("error") or ("HTTP " + str(result.get("status")))
        lines.append(f"- {mark} **{name}** — {detail}")

    lines += [
        "",
        "## Next Step",
        "",
        "If `chat_endpoint` is failing, make sure `AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat` is still running and that it selected `llama-server.exe`.",
        ""
    ]
    (REPORTS / "FIRST_CONTACT_DIAGNOSTICS.md").write_text("\n".join(lines), encoding="utf-8")
    return report

if __name__ == "__main__":
    result = write_report()
    print(json.dumps({"overall": result["overall"], "report": "Foundry/Reports/FIRST_CONTACT_DIAGNOSTICS.md"}, indent=2))
