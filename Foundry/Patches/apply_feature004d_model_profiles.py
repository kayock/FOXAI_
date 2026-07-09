from pathlib import Path
import shutil
import datetime
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature004d_before_model_profiles_{STAMP}"

PROFILES_PY = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI = Path("Z:/FOXAI")\nGATEWAY = ROOT / "AI" / "Gateway"\nPROFILES = GATEWAY / "model_profiles.json"\nACTIVE = GATEWAY / "active_model_profile.json"\nCONFIG = GATEWAY / "engine_adapter_config.json"\n\nDEFAULT_PROFILES = {\n    "safe": {\n        "label": "Safe Portable",\n        "description": "Best default for this USB and midrange machines.",\n        "model": "Z:/FOXAI/Models/Chat/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",\n        "context_tokens": 4096,\n        "purpose": ["chat", "reasoning", "architecture"],\n        "default": True\n    },\n    "power": {\n        "label": "Power Workstation",\n        "description": "For stronger computers with more RAM/VRAM.",\n        "model": "Z:/FOXAI/Models/Chat/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",\n        "context_tokens": 4096,\n        "purpose": ["coding", "engineering", "large reasoning"],\n        "default": False\n    },\n    "vision": {\n        "label": "Vision",\n        "description": "For image/vision tasks. Not the default chat model.",\n        "model": "Z:/FOXAI/Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf",\n        "context_tokens": 2048,\n        "purpose": ["vision", "image analysis"],\n        "default": False\n    }\n}\n\ndef load_json(path, default):\n    if path.exists():\n        try:\n            return json.loads(path.read_text(encoding="utf-8"))\n        except Exception:\n            return default\n    return default\n\ndef save_json(path, data):\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(data, indent=2), encoding="utf-8")\n\ndef materialize_profiles():\n    profiles = load_json(PROFILES, DEFAULT_PROFILES)\n    changed = False\n\n    for key, val in DEFAULT_PROFILES.items():\n        if key not in profiles:\n            profiles[key] = val\n            changed = True\n\n    # Add existence flags dynamically.\n    for key, val in profiles.items():\n        p = Path(val.get("model", ""))\n        val["model_exists"] = p.exists()\n        val["model_name"] = p.name if p.name else "Unknown"\n\n    if changed or not PROFILES.exists():\n        save_json(PROFILES, profiles)\n\n    active = load_json(ACTIVE, {})\n    if not active.get("profile"):\n        active = {"profile": "safe", "updated_at": datetime.datetime.now().isoformat(timespec="seconds")}\n        save_json(ACTIVE, active)\n\n    return profiles, active\n\ndef get_active_profile():\n    profiles, active = materialize_profiles()\n    key = active.get("profile", "safe")\n    if key not in profiles:\n        key = "safe"\n    return key, profiles[key], profiles\n\ndef set_profile(profile):\n    profiles, _ = materialize_profiles()\n    if profile not in profiles:\n        return {"ok": False, "error": f"Unknown profile: {profile}", "available": list(profiles.keys())}\n    save_json(ACTIVE, {"profile": profile, "updated_at": datetime.datetime.now().isoformat(timespec="seconds")})\n    apply_active_profile()\n    return {"ok": True, "profile": profile, "active": profiles[profile]}\n\ndef apply_active_profile():\n    key, profile, profiles = get_active_profile()\n    cfg = load_json(CONFIG, {})\n    cfg.update({\n        "model_profile": key,\n        "active_chat_model": profile.get("model_name") or Path(profile.get("model", "")).name,\n        "selected_model_path": profile.get("model"),\n        "context_tokens": profile.get("context_tokens", 4096),\n        "model_profile_label": profile.get("label"),\n        "model_profile_description": profile.get("description"),\n    })\n    save_json(CONFIG, cfg)\n    rewrite_launcher(cfg)\n    return {"ok": True, "profile": key, "config": cfg, "profiles": profiles}\n\ndef quote(value):\n    return \'"\' + str(value).replace(\'"\', \'\') + \'"\'\n\ndef rewrite_launcher(cfg):\n    engine = cfg.get("selected_engine_path") or "Z:/KayocktheOS/Engine/KoboldCpp/koboldcpp.exe"\n    model = cfg.get("selected_model_path")\n    context = cfg.get("context_tokens", 4096)\n    port = cfg.get("port", 5001)\n\n    launcher_path = GATEWAY / "START_KOBOLD_ENGINE.bat"\n    if not model:\n        text = """@echo off\ntitle KayocktheOS KoboldCpp Engine\ncolor 0C\necho No active model profile selected.\npause\n"""\n    else:\n        text = f"""@echo off\ntitle KayocktheOS KoboldCpp Engine - {cfg.get(\'model_profile_label\', \'Profile\')}\ncolor 0A\necho ==========================================\necho KayocktheOS KoboldCpp Engine Adapter\necho Profile: {cfg.get(\'model_profile_label\', \'Unknown\')}\necho ==========================================\necho.\necho Engine:\necho {engine}\necho.\necho Model:\necho {model}\necho.\necho Context:\necho {context}\necho.\necho Server:\necho http://127.0.0.1:{port}\necho.\necho Leave this window open.\necho.\n{quote(engine)} --model {quote(model)} --port {port} --contextsize {context}\npause\n"""\n    launcher_path.parent.mkdir(parents=True, exist_ok=True)\n    launcher_path.write_text(text, encoding="utf-8")\n\ndef status():\n    profiles, active = materialize_profiles()\n    applied = apply_active_profile()\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "feature": "Feature 004D - Model Profiles",\n        "active": active,\n        "profiles": profiles,\n        "applied": applied\n    }\n\nif __name__ == "__main__":\n    print(json.dumps(status(), indent=2))\n'

STYLE_APPEND = r"""
/* Feature 004D - Model Profiles */
.profileGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}
.profileCard {
  border: 1px solid rgba(149,215,149,.16);
  background: rgba(0,0,0,.22);
  border-radius: 16px;
  padding: 14px;
}
.profileCard h5 {
  margin: 0 0 8px;
  color: var(--accent);
}
.profileCard p {
  margin: 0 0 8px;
  color: var(--muted);
}
"""

RENDERER_PATCH = r"""
// Feature 004D Model Profiles
async function fetchModelProfiles() {
  try { return await fetchJson('/api/model-profiles'); } catch { return null; }
}

function renderModelProfilesShell() {
  const panel = document.getElementById('koboldEnginePanel');
  if (!panel || document.getElementById('modelProfilesPanel')) return;
  const card = document.createElement('article');
  card.id = 'modelProfilesPanel';
  card.className = 'card chatCard';
  card.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Engine Profiles</p>
        <h4>Model Profiles</h4>
      </div>
      <span class="badge">Safe / Power / Vision</span>
    </div>
    <div id="modelProfilesGrid" class="profileGrid"></div>
  `;
  panel.insertAdjacentElement('afterend', card);
}

async function renderModelProfiles() {
  renderModelProfilesShell();
  const grid = document.getElementById('modelProfilesGrid');
  if (!grid) return;

  const data = await fetchModelProfiles();
  if (!data || !data.profiles) {
    grid.innerHTML = '<div class="profileCard"><h5>Profiles unavailable</h5><p>Restart KayocktheOS Core after installing Feature 004D.</p></div>';
    return;
  }

  const active = data.active?.profile || 'safe';
  grid.innerHTML = Object.entries(data.profiles).map(([key, p]) => `
    <div class="profileCard">
      <h5>${escapeHtml(p.label || key)} ${key === active ? '✓' : ''}</h5>
      <p>${escapeHtml(p.description || '')}</p>
      <p><strong>Model:</strong><br><span class="pathText">${escapeHtml(p.model_name || p.model || '')}</span></p>
      <p><strong>Context:</strong> ${escapeHtml(String(p.context_tokens || ''))}</p>
      <p><strong>Status:</strong> ${p.model_exists ? 'Found' : 'Missing'}</p>
    </div>
  `).join('');
}
"""

def info(msg):
    print(f"[Feature 004D Model Profiles] {msg}")

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
    for item in ["AI","Bridge","System/API/core_api.py","Foundry","Docs","Forge","00_START_HERE","manifest.yaml"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_profiles():
    write_text("AI/model_profiles.py", PROFILES_PY)
    spec = importlib.util.spec_from_file_location("model_profiles", ROOT / "AI/model_profiles.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    state = mod.status()
    info("Active profile: " + str(state.get("active", {}).get("profile")))

def patch_core_api():
    path = ROOT / "System" / "API" / "core_api.py"
    if not path.exists():
        info("Core API missing; skipped API route.")
        return
    text = path.read_text(encoding="utf-8", errors="replace")

    if "def model_profiles_status(" not in text:
        insert = """
def model_profiles_status():
    try:
        profiles = ROOT / "AI" / "model_profiles.py"
        if profiles.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("model_profiles", profiles)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "Model profiles missing"}
"""
        text = text.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"model_profiles": model_profiles_status(),' not in text:
        if '"kobold_adapter": kobold_adapter_status(),' in text:
            text = text.replace('"kobold_adapter": kobold_adapter_status(),', '"kobold_adapter": kobold_adapter_status(),\n        "model_profiles": model_profiles_status(),')

    if 'elif path == "/api/model-profiles":' not in text:
        if 'elif path == "/api/kobold":' in text:
            text = text.replace('elif path == "/api/kobold":\n            self._json(kobold_adapter_status())',
                                'elif path == "/api/kobold":\n            self._json(kobold_adapter_status())\n        elif path == "/api/model-profiles":\n            self._json(model_profiles_status())')

    path.write_text(text, encoding="utf-8")
    info("Core API model profile route patched.")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 004D - Model Profiles" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 004D Model Profiles" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderModelProfiles();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderModelProfiles();")
        renderer.write_text(old, encoding="utf-8")
    info("Bridge model profiles panel patched.")

def docs():
    write_text("Docs/FEATURE_004D_MODEL_PROFILES.md", """# Feature 004D - Model Profiles

Adds Safe / Power / Vision model profiles.

## Profiles

- Safe Portable: DeepSeek 14B Q4, context 4096
- Power Workstation: Qwen Coder 30B, context 4096
- Vision: Qwen3VL 8B, context 2048

Default remains Safe Portable.
""")
    write_text("Forge/Decisions/0039_model_profiles.md", """# Decision 0039 - Model Profiles

DeepSeek 14B is the safe portable default, but KayocktheOS must preserve larger models for stronger computers.
""")
    write_text("Foundry/Releases/feature004d_model_profiles_notes.md", "# Feature 004D - Model Profiles\n\nAdds Safe / Power / Vision model profile config.\n")

def changelog():
    path = ROOT / "00_START_HERE" / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 004D - Model Profiles\n\n- Added Safe / Power / Vision model profiles.\n- Safe profile remains DeepSeek 14B Q4.\n- Power profile preserves Qwen Coder 30B for stronger computers.\n- Vision profile preserves Qwen3VL for image tasks.\n"
    if "Feature 004D - Model Profiles" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_profiles()
    patch_core_api()
    patch_bridge()
    docs()
    changelog()
    info("Feature 004D Model Profiles complete.")

if __name__ == "__main__":
    main()
