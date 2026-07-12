from pathlib import Path
import shutil
import datetime
import importlib.util
import py_compile

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature006_before_core_working_{STAMP}"

CORE_PY = 'from pathlib import Path\nimport json\nimport datetime\nimport urllib.request\n\nROOT = Path(__file__).resolve().parents[1]\nGATEWAY = ROOT / "AI" / "Gateway"\nSTATE = GATEWAY / "core_working_state.json"\nCONFIG = GATEWAY / "core_working_config.json"\n\nFOXAI = Path("Z:/FOXAI")\nANYTHING_PATHS = [\n    Path("Z:/Apps/AnythingLLM/AnythingLLM.exe"),\n    Path("Z:/Apps/New folder/AnythingLLM/AnythingLLM.exe"),\n    Path("Z:/AnythingLLM/AnythingLLM.exe"),\n    ROOT / "Apps" / "AnythingLLM" / "AnythingLLM.exe",\n]\nKOBOLD_PATHS = [\n    ROOT / "Engine" / "KoboldCpp" / "koboldcpp.exe",\n    FOXAI / "Engine" / "koboldcpp.exe",\n    FOXAI / "koboldcpp.exe",\n]\nCOMFY_PATHS = [\n    FOXAI / "ComfyUI" / "run_nvidia_gpu.bat",\n    FOXAI / "ComfyUI" / "run_cpu.bat",\n    FOXAI / "ComfyUI" / "main.py",\n]\n\nSAFE_MODEL = FOXAI / "Models" / "Chat" / "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"\n\ndef first_existing(paths):\n    for p in paths:\n        if p.exists():\n            return p\n    return None\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef probe(url, timeout=2):\n    try:\n        with urllib.request.urlopen(url, timeout=timeout) as res:\n            return {"ok": True, "status": res.status}\n    except Exception as exc:\n        return {"ok": False, "error": str(exc)}\n\ndef status():\n    anything = first_existing(ANYTHING_PATHS)\n    kobold = first_existing(KOBOLD_PATHS)\n    comfy = first_existing(COMFY_PATHS)\n\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 006 - Core Working Launch Cleanup",\n        "root": str(ROOT),\n        "anythingllm": {\n            "found": bool(anything),\n            "path": str(anything) if anything else None,\n            "health": probe("http://127.0.0.1:3001")\n        },\n        "koboldcpp": {\n            "found": bool(kobold),\n            "path": str(kobold) if kobold else None,\n            "model": str(SAFE_MODEL) if SAFE_MODEL.exists() else None,\n            "health": probe("http://127.0.0.1:5001")\n        },\n        "comfyui": {\n            "found": bool(comfy),\n            "path": str(comfy) if comfy else None,\n            "health": probe("http://127.0.0.1:8188")\n        },\n        "notes": [\n            "FIRST_CONTACT_START_RUNTIME.bat is now legacy and delegates to START_CORE_WORKING.bat.",\n            "No launcher should call llama-batched-bench.exe.",\n            "AnythingLLM handles project/code/document scanning.",\n            "ComfyUI remains the creative engine in FOXAI.",\n            "KoboldCpp or another runtime can be used later for chat models."\n        ]\n    }\n\ndef quote(p):\n    return \'"\' + str(p).replace(\'"\', \'\') + \'"\'\n\ndef write_launchers():\n    GATEWAY.mkdir(parents=True, exist_ok=True)\n\n    anything = first_existing(ANYTHING_PATHS)\n    kobold = first_existing(KOBOLD_PATHS)\n    comfy = first_existing(COMFY_PATHS)\n\n    core = f"""@echo off\ntitle KayocktheOS Core Working Launcher\ncolor 0A\ncd /d "{ROOT}"\n\necho ==========================================\necho KayocktheOS Core Working Launcher\necho ==========================================\necho.\necho This is the clean startup path.\necho It does NOT call llama-batched-bench.exe.\necho.\necho 1. Start AnythingLLM\necho 2. Start KoboldCpp runtime\necho 3. Start ComfyUI / FOXAI\necho 4. Show status\necho 5. Exit\necho.\nset /p choice=Choose option: \n\nif "%choice%"=="1" goto anything\nif "%choice%"=="2" goto kobold\nif "%choice%"=="3" goto comfy\nif "%choice%"=="4" goto status\ngoto end\n\n:anything\necho.\n"""\n    if anything:\n        core += f\'start "" {quote(anything)}\\n\'\n    else:\n        core += \'echo AnythingLLM not found. Expected Z:\\\\Apps\\\\AnythingLLM or Z:\\\\Apps\\\\New folder\\\\AnythingLLM.\\n\'\n    core += "pause\\ngoto end\\n\\n:kobold\\n"\n    if kobold and SAFE_MODEL.exists():\n        core += f\'start "KayocktheOS KoboldCpp" {quote(kobold)} --model {quote(SAFE_MODEL)} --port 5001 --contextsize 4096\\n\'\n    elif kobold:\n        core += f\'echo KoboldCpp found at {kobold}, but safe model was not found.\\n\'\n    else:\n        core += \'echo KoboldCpp not found. Put koboldcpp.exe in Z:\\\\KayocktheOS\\\\Engine\\\\KoboldCpp\\\\.\\n\'\n    core += "pause\\ngoto end\\n\\n:comfy\\n"\n    if comfy:\n        if comfy.suffix.lower() == ".bat":\n            core += f\'start "FOXAI ComfyUI" {quote(comfy)}\\n\'\n        else:\n            core += f\'echo ComfyUI main.py found at {comfy}. Use your existing FOXAI ComfyUI launcher.\\n\'\n    else:\n        core += \'echo ComfyUI launcher not found under Z:\\\\FOXAI\\\\ComfyUI.\\n\'\n    core += "pause\\ngoto end\\n\\n:status\\n"\n    core += \'python AI\\\\core_working.py\\n\'\n    core += "pause\\ngoto end\\n\\n:end\\nexit /b\\n"\n\n    (GATEWAY / "START_CORE_WORKING.bat").write_text(core, encoding="utf-8")\n\n    legacy = """@echo off\ntitle KayocktheOS First Contact Runtime - Legacy Redirect\ncolor 0E\necho ==========================================\necho KayocktheOS First Contact Runtime\necho ==========================================\necho.\necho This old launcher has been disabled because it was calling\necho llama-batched-bench.exe, which is not a chat server.\necho.\necho Redirecting to the Core Working Launcher...\necho.\ncall "%~dp0START_CORE_WORKING.bat"\n"""\n    (GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat").write_text(legacy, encoding="utf-8")\n\n    anything_bat = "@echo off\\n"\n    anything_bat += "title KayocktheOS AnythingLLM\\ncolor 0A\\n"\n    if anything:\n        anything_bat += f\'start "" {quote(anything)}\\n\'\n    else:\n        anything_bat += \'echo AnythingLLM not found.\\n\'\n        anything_bat += \'echo Expected: Z:\\\\Apps\\\\AnythingLLM\\\\AnythingLLM.exe\\n\'\n        anything_bat += \'echo Or:       Z:\\\\Apps\\\\New folder\\\\AnythingLLM\\\\AnythingLLM.exe\\npause\\n\'\n    (GATEWAY / "START_ANYTHINGLLM.bat").write_text(anything_bat, encoding="utf-8")\n\n    state = status()\n    save_json(STATE, state)\n    save_json(CONFIG, {\n        "primary_launcher": str(GATEWAY / "START_CORE_WORKING.bat"),\n        "legacy_first_contact_redirect": str(GATEWAY / "FIRST_CONTACT_START_RUNTIME.bat"),\n        "anythingllm_launcher": str(GATEWAY / "START_ANYTHINGLLM.bat"),\n        "created_at": datetime.datetime.now().isoformat(timespec="seconds")\n    })\n    return state\n\nif __name__ == "__main__":\n    print(json.dumps(write_launchers(), indent=2))\n'

STYLE_APPEND = r"""
/* Feature 006 - Core Working */
.coreWorkingPanel {
  border: 1px solid rgba(0,255,102,.28);
  background: linear-gradient(135deg, rgba(0,255,102,.07), rgba(0,0,0,.25));
}
.coreLauncherList {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}
.coreLauncherItem {
  padding: 12px;
  border-radius: 14px;
  background: rgba(0,0,0,.22);
  border: 1px solid rgba(149,215,149,.14);
}
.coreLauncherItem strong {
  color: var(--accent);
}
"""

RENDERER_PATCH = r"""
// Feature 006 Core Working Panel
async function fetchCoreWorkingStatus() {
  try { return await fetchJson('/api/core-working'); } catch { return null; }
}

function renderCoreWorkingShell() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('coreWorkingPanel')) return;

  const panel = document.createElement('article');
  panel.id = 'coreWorkingPanel';
  panel.className = 'card chatCard coreWorkingPanel';
  panel.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Core</p>
        <h4>Core Working Launcher</h4>
      </div>
      <span id="coreWorkingBadge" class="badge">Checking</span>
    </div>
    <p class="roomIntro">Clean startup path. The broken First Contact launcher now redirects here instead of calling llama-batched-bench.exe.</p>
    <div id="coreWorkingDetails" class="smallList"></div>
    <div class="coreLauncherList">
      <div class="coreLauncherItem"><strong>Main Launcher</strong><br><span class="pathText">Z:\\KayocktheOS\\AI\\Gateway\\START_CORE_WORKING.bat</span></div>
      <div class="coreLauncherItem"><strong>AnythingLLM</strong><br><span>Engineering knowledge, code scanning, project reports.</span></div>
      <div class="coreLauncherItem"><strong>ComfyUI / FOXAI</strong><br><span>Creative engine remains in FOXAI.</span></div>
    </div>
  `;

  const first = document.getElementById('anythingLLMPanel') || document.getElementById('koboldEnginePanel') || document.getElementById('firstContactPanel');
  if (first) first.insertAdjacentElement('beforebegin', panel);
  else {
    const chatCard = document.querySelector('#home .chatCard');
    if (chatCard) home.insertBefore(panel, chatCard);
    else home.appendChild(panel);
  }
}

async function renderCoreWorkingPanel() {
  renderCoreWorkingShell();
  const badge = document.getElementById('coreWorkingBadge');
  const details = document.getElementById('coreWorkingDetails');
  if (!badge || !details) return;

  const st = await fetchCoreWorkingStatus();
  if (!st) {
    badge.textContent = 'Core Restart Needed';
    details.innerHTML = item('Core Working API', 'Restart KayocktheOS Core after installing Feature 006.', 'wait');
    return;
  }

  const anything = st.anythingllm?.found;
  const comfy = st.comfyui?.found;
  const kobold = st.koboldcpp?.found;

  badge.textContent = (anything || comfy || kobold) ? 'Ready' : 'Needs Tool Paths';

  details.innerHTML = [
    item('AnythingLLM', st.anythingllm?.path || 'Not found yet', anything ? 'ok' : 'wait'),
    item('ComfyUI / FOXAI', st.comfyui?.path || 'Not found yet', comfy ? 'ok' : 'wait'),
    item('KoboldCpp', st.koboldcpp?.path || 'Optional / not found', kobold ? 'ok' : 'wait'),
    item('Legacy First Contact', 'Disabled and redirected to START_CORE_WORKING.bat', 'ok')
  ].join('');
}
"""

def info(msg):
    print(f"[Feature 006 Core Working] {msg}")

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
    for item in ["AI", "Bridge", "System/API/core_api.py", "Foundry", "Docs", "Forge", "00_START_HERE", "manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_core():
    write_text("AI/core_working.py", CORE_PY)
    py_compile.compile(str(ROOT / "AI/core_working.py"), doraise=True)
    spec = importlib.util.spec_from_file_location("core_working", ROOT / "AI/core_working.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.write_launchers()
    info("Primary launcher: AI\\Gateway\\START_CORE_WORKING.bat")
    info("Legacy First Contact redirected.")
    info("AnythingLLM found: " + str(state.get("anythingllm", {}).get("found")))
    info("ComfyUI found: " + str(state.get("comfyui", {}).get("found")))

def patch_core_api():
    path = ROOT / "System" / "API" / "core_api.py"
    if not path.exists():
        info("Core API not found; skipped route patch.")
        return

    text = path.read_text(encoding="utf-8", errors="replace")

    if "def core_working_status(" not in text:
        insert = """
def core_working_status():
    try:
        core = ROOT / "AI" / "core_working.py"
        if core.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("core_working", core)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "Core Working missing"}
"""
        text = text.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"core_working": core_working_status(),' not in text:
        for marker in ['"anythingllm": anythingllm_status(),', '"model_profiles": model_profiles_status(),', '"kobold_adapter": kobold_adapter_status(),']:
            if marker in text:
                text = text.replace(marker, marker + '\n        "core_working": core_working_status(),')
                break

    if 'elif path == "/api/core-working":' not in text:
        for old, new in [
            ('elif path == "/api/anythingllm":\n            self._json(anythingllm_status())',
             'elif path == "/api/anythingllm":\n            self._json(anythingllm_status())\n        elif path == "/api/core-working":\n            self._json(core_working_status())'),
            ('elif path == "/api/model-profiles":\n            self._json(model_profiles_status())',
             'elif path == "/api/model-profiles":\n            self._json(model_profiles_status())\n        elif path == "/api/core-working":\n            self._json(core_working_status())'),
            ('elif path == "/api/kobold":\n            self._json(kobold_adapter_status())',
             'elif path == "/api/kobold":\n            self._json(kobold_adapter_status())\n        elif path == "/api/core-working":\n            self._json(core_working_status())'),
        ]:
            if old in text:
                text = text.replace(old, new)
                break

    path.write_text(text, encoding="utf-8")
    py_compile.compile(str(path), doraise=True)
    info("Core API route /api/core-working patched and syntax checked.")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"

    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 006 - Core Working" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")

    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 006 Core Working Panel" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderCoreWorkingPanel();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderCoreWorkingPanel();")
        renderer.write_text(old, encoding="utf-8")

    info("Bridge Core Working panel patched.")

def docs():
    write_text("Docs/FEATURE_006_CORE_WORKING.md", """# Feature 006 - Core Working Launch Cleanup

This patch creates one clean startup path and disables the broken legacy First Contact launcher.

## Primary Launcher

```text
Z:\\KayocktheOS\\AI\\Gateway\\START_CORE_WORKING.bat
```

## What changed

- `FIRST_CONTACT_START_RUNTIME.bat` now redirects to the Core Working Launcher.
- It should no longer call `llama-batched-bench.exe`.
- AnythingLLM is treated as the engineering/code/document brain.
- ComfyUI remains in FOXAI for creative workflows.
- KoboldCpp remains optional for local GGUF runtime.
""")
    write_text("Forge/Decisions/0041_core_working_launch_cleanup.md", """# Decision 0041 - Core Working Launch Cleanup

Stop expanding features until the startup path is reliable.

Disable the old First Contact benchmark launcher and route through a single Core Working launcher.
""")
    write_text("Foundry/Releases/feature006_core_working_launch_cleanup_notes.md", "# Feature 006 - Core Working\n\nAdds clean launcher and redirects broken First Contact path.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 006 - Core Working Launch Cleanup\n\n- Added `AI/core_working.py`.\n- Added `AI/Gateway/START_CORE_WORKING.bat`.\n- Redirected `FIRST_CONTACT_START_RUNTIME.bat` away from `llama-batched-bench.exe`.\n- Added `/api/core-working` status route where Core API patch is available.\n- Added Bridge Core Working status panel.\n"
    if "Feature 006 - Core Working Launch Cleanup" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_core()
    patch_core_api()
    patch_bridge()
    docs()
    changelog()
    info("Feature 006 Core Working complete.")
    info("Run AI\\Gateway\\START_CORE_WORKING.bat.")

if __name__ == "__main__":
    main()
