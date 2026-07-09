from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002g_v2_before_creative_studio_{STAMP}"

STYLE_APPEND = '\n/* Feature 002G v2 - Creative Studio Room */\n.creativeHero { margin-bottom: 18px; }\n\n.studioGrid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));\n  gap: 14px;\n}\n\n.studioCard {\n  background: rgba(0,0,0,.22);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 16px;\n  padding: 16px;\n}\n\n.studioCard h5 {\n  color: var(--accent);\n  margin: 8px 0;\n  font-size: 18px;\n}\n\n.studioCard p {\n  color: var(--muted);\n  margin: 0;\n}\n\n.promptBox {\n  width: 100%;\n  min-height: 120px;\n  resize: vertical;\n  background: rgba(0,0,0,.35);\n  color: var(--text);\n  border: 1px solid rgba(149,215,149,.2);\n  border-radius: 12px;\n  padding: 13px;\n  font-family: inherit;\n}\n\n.promptActions {\n  display: flex;\n  gap: 10px;\n  margin-top: 12px;\n  flex-wrap: wrap;\n}\n\n.workflowList {\n  display: grid;\n  gap: 8px;\n  max-height: 330px;\n  overflow: auto;\n}\n\n.modelPill {\n  display: inline-block;\n  border: 1px solid rgba(0,255,102,.22);\n  border-radius: 999px;\n  padding: 7px 10px;\n  color: var(--accent);\n  background: rgba(0,255,102,.06);\n  margin: 4px 4px 0 0;\n  font-size: 13px;\n}\n\n.creativeNotice {\n  border-left: 4px solid var(--warn);\n  background: rgba(255,209,102,.06);\n  border-radius: 12px;\n  padding: 12px;\n  color: var(--muted);\n}\n'
RENDERER_PATCH = '\n// Feature 002G v2 Creative Studio upgrade\nfunction renderCreativeStudioUpgrade() {\n  const workshop = document.getElementById(\'workshop\');\n  if (!workshop || workshop.dataset.creativeStudio === \'true\') return;\n  workshop.dataset.creativeStudio = \'true\';\n\n  const studio = document.createElement(\'article\');\n  studio.className = \'card wide chatCard creativeHero\';\n  studio.innerHTML = `\n    <div class="sectionHeader">\n      <div>\n        <p class="eyebrow">Creative Studio</p>\n        <h4>Image Generation, Workflows, and Creative Assets</h4>\n      </div>\n      <span id="creativeStudioStatus" class="badge">Scanning</span>\n    </div>\n    <p class="roomIntro">Creative Studio reads FOXAI\'s image assets and prepares the path to ComfyUI generation directly from the Bridge.</p>\n    <div class="studioGrid" id="creativeStudioCards"></div>\n  `;\n\n  const prompt = document.createElement(\'article\');\n  prompt.className = \'card wide chatCard\';\n  prompt.innerHTML = `\n    <div class="sectionHeader">\n      <div>\n        <p class="eyebrow">Prompt Bench</p>\n        <h4>Draft an Image Prompt</h4>\n      </div>\n      <span class="badge">Operator approval required</span>\n    </div>\n    <textarea id="creativePrompt" class="promptBox" placeholder="Describe an image to generate later through ComfyUI..."></textarea>\n    <div class="promptActions">\n      <button id="savePromptBtn" class="primaryBtn" type="button">Save Prompt Draft</button>\n      <button id="askDaVinciBtn" class="primaryBtn" type="button">Ask Professor Da Vinci</button>\n    </div>\n    <div id="creativePromptNotice" class="creativeNotice chatCard">\n      Generation is not enabled yet. This room prepares the prompt and workflow layer first.\n    </div>\n  `;\n\n  const workflow = document.createElement(\'article\');\n  workflow.className = \'card wide chatCard\';\n  workflow.innerHTML = `\n    <h4>ComfyUI Workflows</h4>\n    <div id="creativeWorkflowList" class="workflowList"></div>\n  `;\n\n  workshop.appendChild(studio);\n  workshop.appendChild(prompt);\n  workshop.appendChild(workflow);\n\n  document.getElementById(\'savePromptBtn\')?.addEventListener(\'click\', () => {\n    const promptText = document.getElementById(\'creativePrompt\')?.value || \'\';\n    if (!promptText.trim()) {\n      notify(\'Creative Studio\', \'Prompt draft is empty.\', \'wait\');\n      renderNotifications();\n      return;\n    }\n    localStorage.setItem(\'kayock_creative_prompt_draft\', promptText);\n    notify(\'Creative Studio\', \'Prompt draft saved locally in the Bridge.\', \'ok\');\n    renderNotifications();\n    document.getElementById(\'creativePromptNotice\').textContent = \'Prompt draft saved locally. Next build will add prompt history on disk.\';\n  });\n\n  document.getElementById(\'askDaVinciBtn\')?.addEventListener(\'click\', () => {\n    const promptText = document.getElementById(\'creativePrompt\')?.value || \'\';\n    const ask = promptText.trim()\n      ? `Professor Da Vinci, improve this image prompt for ComfyUI: ${promptText}`\n      : \'Professor Da Vinci, help me design an image prompt for KayocktheOS.\';\n    openRoom(\'home\');\n    document.getElementById(\'chatInput\').value = ask;\n  });\n}\n\nfunction renderCreativeStudioData() {\n  renderCreativeStudioUpgrade();\n  const fox = state.foxai || {};\n  const assets = fox.assets || {};\n  const images = assets.image_models || [];\n  const workflows = assets.workflows || [];\n  const llms = assets.llms || [];\n  const vision = llms.filter(m => (m.capabilities || []).includes(\'vision\'));\n\n  const status = document.getElementById(\'creativeStudioStatus\');\n  if (status) status.textContent = images.length ? \'Assets Ready\' : \'Waiting\';\n\n  const cards = document.getElementById(\'creativeStudioCards\');\n  if (cards) {\n    cards.innerHTML = [\n      studioCard(\'🎨\', \'Image Models\', images.length, images.slice(0, 6).map(m => m.name)),\n      studioCard(\'🧩\', \'Workflows\', workflows.length, workflows.slice(0, 6).map(w => w.name)),\n      studioCard(\'👁\', \'Vision Assist\', vision.length, vision.slice(0, 4).map(m => m.name)),\n      studioCard(\'🔌\', \'ComfyUI\', workflows.length || images.length ? \'Detected assets\' : \'Not connected yet\', [\'Generation endpoint will be wired later\'])\n    ].join(\'\');\n  }\n\n  const wf = document.getElementById(\'creativeWorkflowList\');\n  if (wf) {\n    if (workflows.length) {\n      wf.innerHTML = workflows.slice(0, 50).map(w =>\n        item(w.name, `${w.path || \'\'}`, \'ok\')\n      ).join(\'\');\n    } else {\n      wf.innerHTML = [\n        item(\'No workflows discovered yet\', \'Place ComfyUI workflow JSON files under Z:\\\\FOXAI\\\\ComfyUI.\', \'wait\'),\n        item(\'Next build\', \'Add ComfyUI API detection and generation submit button.\', \'wait\')\n      ].join(\'\');\n    }\n  }\n\n  const saved = localStorage.getItem(\'kayock_creative_prompt_draft\');\n  const promptBox = document.getElementById(\'creativePrompt\');\n  if (promptBox && saved && !promptBox.value) promptBox.value = saved;\n}\n\nfunction studioCard(icon, title, count, names) {\n  const nameList = Array.isArray(names) && names.length\n    ? names.map(n => `<span class="modelPill">${escapeHtml(n)}</span>`).join(\'\')\n    : \'<p>No assets yet.</p>\';\n  return `\n    <div class="studioCard">\n      <div class="shelfIcon">${icon}</div>\n      <h5>${escapeHtml(title)}</h5>\n      <p><strong>${escapeHtml(count)}</strong></p>\n      <div>${nameList}</div>\n    </div>\n  `;\n}\n'

def info(msg):
    print(f"[Feature 002G v2 Creative Studio] {msg}")

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
    for item in ["Bridge","manifest.yaml","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_bridge():
    style = ROOT / "Bridge" / "style.css"
    renderer = ROOT / "Bridge" / "renderer.js"
    if style.exists():
        old = style.read_text(encoding="utf-8", errors="replace")
        if "Feature 002G v2 - Creative Studio Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002G v2 Creative Studio upgrade" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderCreativeStudioData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderCreativeStudioData();")
        renderer.write_text(old, encoding="utf-8")
    info("Creative Studio upgraded in Workshop room.")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002g_creative_studio_room_v2: enabled" not in text:
        text += "\n  feature_002g_creative_studio_room_v2: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002g_creative_studio_room_v2: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002G_CREATIVE_STUDIO_ROOM_V2.md", """# Feature 002G v2 - Creative Studio Room

Creative Studio now appears inside the Workshop room with real FOXAI image/workflow awareness.

## Adds

- Image model cards
- Workflow list
- Vision assist model awareness
- Prompt Bench
- Local prompt draft saving in Bridge localStorage
- Ask Professor Da Vinci prompt helper

## Next

Connect to ComfyUI API and submit a workflow from the Bridge.
""")
    write_text("Forge/Decisions/0024_creative_studio_room_v2.md", """# Decision 0024 - Creative Studio Room

Creative Studio should create tangible outputs, but generation must remain explicit and Operator-approved.

The room first discovers assets, then drafts prompts, then later submits to ComfyUI.
""")
    write_text("Foundry/Releases/feature002g_creative_studio_room_v2_notes.md", "# Feature 002G v2 - Creative Studio Room\n\nAdds visible Creative Studio asset and prompt panels.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002G v2 - Creative Studio Room\n\n- Added visible Creative Studio section in Workshop.\n- Added image model and workflow cards.\n- Added Prompt Bench and Professor Da Vinci helper.\n- Prepared ComfyUI generation workflow for the next build.\n"
    if "Feature 002G v2 - Creative Studio Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002G v2 Creative Studio Room complete.")
    info("Restart Start_Bridge.bat and open Workshop.")

if __name__ == "__main__":
    main()
