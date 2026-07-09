from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature003d_before_first_contact_diagnostics_{STAMP}"

DIAG_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\nimport urllib.error\n\nROOT = Path(__file__).resolve().parents[1]\nREPORTS = ROOT / "Foundry" / "Reports"\nCONFIG = ROOT / "AI" / "Gateway" / "gateway_config.json"\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception as exc:\n            return {"_error": str(exc), **default}\n    return default\n\ndef probe(url, method="GET", data=None):\n    try:\n        body = None\n        headers = {}\n        if data is not None:\n            body = json.dumps(data).encode("utf-8")\n            headers["Content-Type"] = "application/json"\n        req = urllib.request.Request(url, data=body, headers=headers, method=method)\n        with urllib.request.urlopen(req, timeout=10) as res:\n            raw = res.read().decode("utf-8", errors="replace")\n            try:\n                parsed = json.loads(raw)\n            except Exception:\n                parsed = raw[:1000]\n            return {"ok": True, "status": res.status, "response": parsed}\n    except Exception as exc:\n        return {"ok": False, "error": str(exc)}\n\ndef run_diagnostics():\n    cfg = load_json(CONFIG, {})\n    base = cfg.get("runtime_base", "http://127.0.0.1:8845")\n    endpoint = cfg.get("chat_endpoint", base + "/v1/chat/completions")\n    model = cfg.get("active_chat_model", "local-model")\n\n    test_payload = {\n        "model": model,\n        "messages": [\n            {"role": "system", "content": "You are a KayocktheOS First Contact diagnostic responder. Answer briefly."},\n            {"role": "user", "content": "Say: First Contact diagnostic successful."}\n        ],\n        "temperature": 0.2,\n        "max_tokens": 80,\n        "stream": False\n    }\n\n    report = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "config": {\n            "runtime_base": base,\n            "chat_endpoint": endpoint,\n            "active_chat_model": model,\n            "selected_runtime_path": cfg.get("selected_runtime_path"),\n            "selected_model_path": cfg.get("selected_model_path")\n        },\n        "checks": {\n            "runtime_base": probe(base),\n            "models_endpoint": probe(base + "/v1/models"),\n            "chat_endpoint": probe(endpoint, "POST", test_payload),\n            "kayock_core_ping": probe("http://127.0.0.1:8844/api/ping"),\n            "kayock_first_contact": probe("http://127.0.0.1:8844/api/first-contact")\n        }\n    }\n\n    report["overall"] = "ok" if report["checks"]["chat_endpoint"]["ok"] else "needs_review"\n    return report\n\ndef write_report():\n    REPORTS.mkdir(parents=True, exist_ok=True)\n    report = run_diagnostics()\n    (REPORTS / "first_contact_diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")\n\n    lines = [\n        "# First Contact Diagnostics",\n        "",\n        f"Generated: {report[\'generated_at\']}",\n        f"Overall: {report[\'overall\']}",\n        "",\n        "## Config",\n        "",\n        f"- Runtime: `{report[\'config\'].get(\'selected_runtime_path\')}`",\n        f"- Model: `{report[\'config\'].get(\'selected_model_path\')}`",\n        f"- Endpoint: `{report[\'config\'].get(\'chat_endpoint\')}`",\n        "",\n        "## Checks",\n        ""\n    ]\n\n    for name, result in report["checks"].items():\n        mark = "✅" if result.get("ok") else "❌"\n        detail = result.get("error") or ("HTTP " + str(result.get("status")))\n        lines.append(f"- {mark} **{name}** — {detail}")\n\n    lines += [\n        "",\n        "## Next Step",\n        "",\n        "If `chat_endpoint` is failing, make sure `AI\\\\Gateway\\\\FIRST_CONTACT_START_RUNTIME.bat` is still running and that it selected `llama-server.exe`.",\n        ""\n    ]\n    (REPORTS / "FIRST_CONTACT_DIAGNOSTICS.md").write_text("\\n".join(lines), encoding="utf-8")\n    return report\n\nif __name__ == "__main__":\n    result = write_report()\n    print(json.dumps({"overall": result["overall"], "report": "Foundry/Reports/FIRST_CONTACT_DIAGNOSTICS.md"}, indent=2))\n'
STYLE_APPEND = '\n/* Feature 003D - First Contact Diagnostics */\n.diagnosticHint {\n  border-left: 4px solid var(--warn);\n  background: rgba(255,209,102,.06);\n  border-radius: 12px;\n  padding: 12px;\n  color: var(--muted);\n  margin-top: 12px;\n}\n'
RENDERER_PATCH = '\n// Feature 003D First Contact Diagnostics hint\nfunction renderFirstContactDiagnosticsHint() {\n  const panel = document.getElementById(\'firstContactPanel\');\n  if (!panel || document.getElementById(\'firstContactDiagnosticsHint\')) return;\n  const div = document.createElement(\'div\');\n  div.id = \'firstContactDiagnosticsHint\';\n  div.className = \'diagnosticHint\';\n  div.innerHTML = \'<strong>Diagnostics:</strong> Run <span class="pathText">Z:\\\\\\\\KayocktheOS\\\\\\\\Foundry\\\\\\\\first_contact_diagnostics.bat</span> if First Contact does not answer.\';\n  panel.appendChild(div);\n}\n'

def info(msg):
    print(f"[Feature 003D First Contact Diagnostics] {msg}")

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

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["AI","Bridge","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_diagnostics():
    write_text("Foundry/first_contact_diagnostics.py", DIAG_PY)
    write_text("Foundry/first_contact_diagnostics.bat", """@echo off
title KayocktheOS First Contact Diagnostics
color 0A
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\first_contact_diagnostics.py
) else (
    py Foundry\first_contact_diagnostics.py
)

echo.
echo Report:
echo Foundry\Reports\FIRST_CONTACT_DIAGNOSTICS.md
echo.
pause
""")
    info("Diagnostic script installed.")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 003D - First Contact Diagnostics" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 003D First Contact Diagnostics hint" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderFirstContactDiagnosticsHint();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderFirstContactDiagnosticsHint();")
        renderer.write_text(old, encoding="utf-8")
    info("Bridge diagnostics hint added.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_003d_first_contact_diagnostics: enabled" not in text:
        text += "\n  feature_003d_first_contact_diagnostics: enabled\n" if "features:" in text else "\nfeatures:\n  feature_003d_first_contact_diagnostics: enabled\n"
        path.write_text(text, encoding="utf-8")

def docs():
    write_text("Docs/FEATURE_003D_FIRST_CONTACT_DIAGNOSTICS.md", """# Feature 003D - First Contact Diagnostics

Adds a diagnostic script for First Contact.

## Run

```text
Z:\\KayocktheOS\\Foundry\\first_contact_diagnostics.bat
```

## Output

```text
Foundry\\Reports\\FIRST_CONTACT_DIAGNOSTICS.md
Foundry\\Reports\\first_contact_diagnostics.json
```
""")
    write_text("Forge/Decisions/0032_first_contact_diagnostics.md", """# Decision 0032 - First Contact Diagnostics

First Contact needs a simple diagnostic report so runtime issues can be fixed without guessing.
""")
    write_text("Foundry/Releases/feature003d_first_contact_diagnostics_notes.md", "# Feature 003D - First Contact Diagnostics\n\nAdds diagnostic script and Bridge hint.\n")

def changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 003D - First Contact Diagnostics\n\n- Added `Foundry/first_contact_diagnostics.py`.\n- Added `Foundry/first_contact_diagnostics.bat`.\n- Added diagnostic reports for runtime, `/v1/models`, `/api/first-contact`, and `/api/chat`.\n- Added Bridge hint near First Contact panel.\n"
    if "Feature 003D - First Contact Diagnostics" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_diagnostics()
    patch_bridge()
    update_manifest()
    docs()
    changelog()
    info("Feature 003D First Contact Diagnostics complete.")

if __name__ == "__main__":
    main()
