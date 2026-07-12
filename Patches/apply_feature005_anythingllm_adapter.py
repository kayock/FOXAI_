from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature005_before_anythingllm_adapter_{STAMP}"

ADAPTER_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nAPP_DIR = ROOT / "Apps" / "AnythingLLM"\nGATEWAY = ROOT / "AI" / "Gateway"\nCONFIG = GATEWAY / "anythingllm_adapter_config.json"\nSTATE = GATEWAY / "anythingllm_adapter_state.json"\n\nHOST = "127.0.0.1"\nCOMMON_PORTS = [3001, 3000, 8888]\n\nSCAN_TARGETS = [\n    str(ROOT),\n    "Z:/FOXAI",\n    "Z:/FOXAI/Library",\n    "Z:/FOXAI/Prompts",\n    "Z:/FOXAI/Mission Archive",\n]\n\nEXCLUDE_GUIDANCE = [\n    "node_modules",\n    ".git",\n    "__pycache__",\n    ".venv",\n    "venv",\n    "ComfyUI/models",\n    "Models/Images",\n    "*.safetensors",\n    "*.gguf",\n    "*.ckpt",\n    "*.bin",\n    "*.pt",\n    "*.pth",\n]\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef find_anythingllm():\n    candidates = [\n        APP_DIR / "AnythingLLM.exe",\n        FOXAI / "Apps" / "AnythingLLM" / "AnythingLLM.exe",\n        FOXAI / "AnythingLLM" / "AnythingLLM.exe",\n    ]\n    for p in candidates:\n        if p.exists():\n            return p\n    for base in [APP_DIR, FOXAI]:\n        if base.exists():\n            for p in base.rglob("AnythingLLM*.exe"):\n                return p\n    return None\n\ndef probe(url):\n    try:\n        with urllib.request.urlopen(url, timeout=3) as res:\n            return {"ok": True, "status": res.status}\n    except Exception as exc:\n        return {"ok": False, "error": str(exc)}\n\ndef health():\n    checks = {}\n    for port in COMMON_PORTS:\n        url = f"http://{HOST}:{port}"\n        checks[str(port)] = probe(url)\n    online = any(v.get("ok") for v in checks.values())\n    active_port = None\n    for port, result in checks.items():\n        if result.get("ok"):\n            active_port = int(port)\n            break\n    return {"online": online, "active_port": active_port, "checks": checks}\n\ndef write_all():\n    exe = find_anythingllm()\n    APP_DIR.mkdir(parents=True, exist_ok=True)\n    h = health()\n\n    cfg = {\n        "adapter": "anythingllm",\n        "purpose": "code_project_document_scanning",\n        "app_dir": str(APP_DIR),\n        "exe_path": str(exe) if exe else None,\n        "health": h,\n        "scan_targets": SCAN_TARGETS,\n        "exclude_guidance": EXCLUDE_GUIDANCE,\n        "role_in_kayocktheos": "AnythingLLM handles document/code scanning. KayocktheOS orchestrates and presents the Academy overlay.",\n        "created_at": datetime.datetime.now().isoformat(timespec="seconds")\n    }\n    save_json(CONFIG, cfg)\n\n    if exe:\n        launcher = f"""@echo off\ntitle KayocktheOS AnythingLLM Adapter\ncolor 0A\necho ==========================================\necho KayocktheOS AnythingLLM Adapter\necho ==========================================\necho.\necho Launching AnythingLLM:\necho {exe}\necho.\nstart "" "{exe}"\necho.\necho After it opens:\necho 1. Create a KayocktheOS workspace.\necho 2. Add project/code folders carefully.\necho 3. Exclude models, ComfyUI model folders, node_modules, and cache folders.\necho.\npause\n"""\n    else:\n        launcher = f"""@echo off\ntitle KayocktheOS AnythingLLM Adapter\ncolor 0E\necho ==========================================\necho KayocktheOS AnythingLLM Adapter\necho ==========================================\necho.\necho AnythingLLM was not found yet.\necho.\necho Recommended install location:\necho {APP_DIR}\necho.\necho Put the AnythingLLM app or shortcut here, then rerun this patch.\necho.\necho Use AnythingLLM for:\necho - Project/code search\necho - Document scanning\necho - Library Q/A\necho - Assistant-assisted engineering review\necho.\npause\n"""\n    launcher_path = GATEWAY / "START_ANYTHINGLLM.bat"\n    launcher_path.parent.mkdir(parents=True, exist_ok=True)\n    launcher_path.write_text(launcher, encoding="utf-8")\n\n    guide = {\n        "workspace_name": "KayocktheOS / FOXAI Workshop",\n        "recommended_first_ingest": [\n            "Z:/KayocktheOS/Bridge",\n            "Z:/KayocktheOS/System",\n            "Z:/KayocktheOS/AI",\n            "Z:/KayocktheOS/Docs",\n            "Z:/FOXAI/Library",\n            "Z:/FOXAI/Prompts",\n        ],\n        "do_not_ingest_initially": EXCLUDE_GUIDANCE,\n        "operator_note": "Start small. Index source/docs first, not huge model files."\n    }\n    save_json(GATEWAY / "anythingllm_workspace_guide.json", guide)\n\n    state = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 005 - AnythingLLM Swiss Army Adapter",\n        "exe_path": str(exe) if exe else None,\n        "exe_exists": bool(exe),\n        "launcher": str(launcher_path),\n        "config": str(CONFIG),\n        "workspace_guide": str(GATEWAY / "anythingllm_workspace_guide.json"),\n        "health": h\n    }\n    save_json(STATE, state)\n    return state\n\nif __name__ == "__main__":\n    print(json.dumps(write_all(), indent=2))\n'

STYLE_APPEND = r"""
/* Feature 005 - AnythingLLM Swiss Army Adapter */
.anythingPanel {
  border: 1px solid rgba(149,215,149,.22);
  background: linear-gradient(135deg, rgba(0,255,102,.05), rgba(0,0,0,.24));
}
.anythingGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}
.anythingCard {
  background: rgba(0,0,0,.22);
  border: 1px solid rgba(149,215,149,.14);
  border-radius: 16px;
  padding: 14px;
}
.anythingCard h5 {
  margin: 0 0 8px;
  color: var(--accent);
}
.anythingCard p {
  margin: 0;
  color: var(--muted);
}
"""

RENDERER_PATCH = r"""
// Feature 005 AnythingLLM Adapter Panel
async function fetchAnythingStatus() {
  try { return await fetchJson('/api/anythingllm'); } catch { return null; }
}

function renderAnythingShell() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('anythingLLMPanel')) return;

  const panel = document.createElement('article');
  panel.id = 'anythingLLMPanel';
  panel.className = 'card chatCard anythingPanel';
  panel.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Feature 005</p>
        <h4>AnythingLLM Code & Document Brain</h4>
      </div>
      <span id="anythingBadge" class="badge">Checking</span>
    </div>
    <p class="roomIntro">AnythingLLM becomes the Swiss Army search brain: code scanning, document Q/A, and project memory. KayocktheOS remains the Academy overlay.</p>
    <div id="anythingDetails" class="smallList"></div>
    <div class="anythingGrid">
      <div class="anythingCard">
        <h5>Recommended First Workspace</h5>
        <p class="pathText">KayocktheOS / FOXAI Workshop</p>
      </div>
      <div class="anythingCard">
        <h5>Start Here</h5>
        <p class="pathText">Z:\\KayocktheOS\\AI\\Gateway\\START_ANYTHINGLLM.bat</p>
      </div>
      <div class="anythingCard">
        <h5>Index First</h5>
        <p>Bridge, System, AI, Docs, FOXAI Library, Prompts.</p>
      </div>
      <div class="anythingCard">
        <h5>Skip First</h5>
        <p>GGUF, safetensors, node_modules, cache folders, ComfyUI model folders.</p>
      </div>
    </div>
  `;

  const kobold = document.getElementById('koboldEnginePanel');
  if (kobold) kobold.insertAdjacentElement('afterend', panel);
  else {
    const chatCard = document.querySelector('#home .chatCard');
    if (chatCard) home.insertBefore(panel, chatCard);
    else home.appendChild(panel);
  }
}

async function renderAnythingPanel() {
  renderAnythingShell();
  const badge = document.getElementById('anythingBadge');
  const details = document.getElementById('anythingDetails');
  if (!badge || !details) return;

  const data = await fetchAnythingStatus();
  if (!data) {
    badge.textContent = 'Core Restart Needed';
    details.innerHTML = item('AnythingLLM Adapter', 'Restart KayocktheOS Core after installing Feature 005.', 'wait');
    return;
  }

  badge.textContent = data.exe_exists ? (data.health?.online ? 'Online' : 'Installed') : 'Not Installed Yet';
  details.innerHTML = [
    item('AnythingLLM EXE', data.exe_path || 'Place AnythingLLM in Apps\\AnythingLLM', data.exe_exists ? 'ok' : 'wait'),
    item('Launcher', data.launcher || 'AI\\Gateway\\START_ANYTHINGLLM.bat', 'ok'),
    item('Workspace Guide', data.workspace_guide || 'AI\\Gateway\\anythingllm_workspace_guide.json', 'ok'),
    item('Status', data.health?.online ? 'Online' : 'Launch AnythingLLM manually when needed', data.health?.online ? 'ok' : 'wait')
  ].join('');
}
"""

def info(msg):
    print(f"[Feature 005 AnythingLLM Adapter] {msg}")

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
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["AI","Apps","Bridge","System/API/core_api.py","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_adapter():
    write_text("AI/anythingllm_adapter.py", ADAPTER_PY)
    (ROOT / "Apps" / "AnythingLLM").mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("anythingllm_adapter", ROOT / "AI/anythingllm_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_all()
    info("AnythingLLM path: " + str(state.get("exe_path")))
    info("Launcher: AI\\Gateway\\START_ANYTHINGLLM.bat")

def patch_core_api():
    path = ROOT / "System" / "API" / "core_api.py"
    if not path.exists():
        info("Core API missing; skipped route.")
        return
    text = path.read_text(encoding="utf-8", errors="replace")

    if "def anythingllm_status(" not in text:
        insert = """
def anythingllm_status():
    try:
        adapter = ROOT / "AI" / "anythingllm_adapter.py"
        if adapter.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("anythingllm_adapter", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_all()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "AnythingLLM adapter missing"}
"""
        text = text.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"anythingllm": anythingllm_status(),' not in text:
        if '"model_profiles": model_profiles_status(),' in text:
            text = text.replace('"model_profiles": model_profiles_status(),', '"model_profiles": model_profiles_status(),\n        "anythingllm": anythingllm_status(),')
        elif '"kobold_adapter": kobold_adapter_status(),' in text:
            text = text.replace('"kobold_adapter": kobold_adapter_status(),', '"kobold_adapter": kobold_adapter_status(),\n        "anythingllm": anythingllm_status(),')

    if 'elif path == "/api/anythingllm":' not in text:
        if 'elif path == "/api/model-profiles":' in text:
            text = text.replace('elif path == "/api/model-profiles":\n            self._json(model_profiles_status())',
                                'elif path == "/api/model-profiles":\n            self._json(model_profiles_status())\n        elif path == "/api/anythingllm":\n            self._json(anythingllm_status())')
        elif 'elif path == "/api/kobold":' in text:
            text = text.replace('elif path == "/api/kobold":\n            self._json(kobold_adapter_status())',
                                'elif path == "/api/kobold":\n            self._json(kobold_adapter_status())\n        elif path == "/api/anythingllm":\n            self._json(anythingllm_status())')

    path.write_text(text, encoding="utf-8")
    info("Core API AnythingLLM route patched.")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 005 - AnythingLLM Swiss Army Adapter" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 005 AnythingLLM Adapter Panel" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderAnythingPanel();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderAnythingPanel();")
        renderer.write_text(old, encoding="utf-8")
    info("Bridge AnythingLLM panel patched.")

def docs():
    write_text("Docs/FEATURE_005_ANYTHINGLLM_SWISS_ARMY_ADAPTER.md", """# Feature 005 - AnythingLLM Swiss Army Adapter

AnythingLLM becomes the code/project/document scanning brain.

## Role Split

```text
AnythingLLM = code scan, document Q/A, project RAG
ComfyUI = images and creative workflows
FOXAI = model/library warehouse
KayocktheOS = Academy overlay, launch, route, monitor, orchestrate
```

## Recommended first workspace

```text
KayocktheOS / FOXAI Workshop
```

## Index first

```text
Z:\\KayocktheOS\\Bridge
Z:\\KayocktheOS\\System
Z:\\KayocktheOS\\AI
Z:\\KayocktheOS\\Docs
Z:\\FOXAI\\Library
Z:\\FOXAI\\Prompts
```

## Avoid first

```text
*.gguf
*.safetensors
node_modules
cache folders
ComfyUI model folders
```
""")
    write_text("Forge/Decisions/0040_anythingllm_swiss_army_drive.md", """# Decision 0040 - AnythingLLM Swiss Army Drive

Use mature tools first. AnythingLLM owns project/code/document scanning; KayocktheOS owns the custom Academy experience.
""")
    write_text("Foundry/Releases/feature005_anythingllm_adapter_notes.md", "# Feature 005 - AnythingLLM Adapter\n\nAdds AnythingLLM launcher, config, workspace guide, and Bridge panel.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 005 - AnythingLLM Swiss Army Adapter\n\n- Added `AI/anythingllm_adapter.py`.\n- Added `AI/Gateway/START_ANYTHINGLLM.bat`.\n- Added workspace guide for code/project scanning.\n- Added Bridge panel for AnythingLLM status and guidance.\n"
    if "Feature 005 - AnythingLLM Swiss Army Adapter" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_adapter()
    patch_core_api()
    patch_bridge()
    docs()
    changelog()
    info("Feature 005 AnythingLLM Swiss Army Adapter complete.")

if __name__ == "__main__":
    main()
