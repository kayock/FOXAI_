from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002f_before_library_room_{STAMP}"

STYLE_APPEND = '\n/* Feature 002F - Library Room */\n.libraryShelf {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));\n  gap: 14px;\n}\n\n.shelfCard {\n  background: rgba(0,0,0,.22);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 16px;\n  padding: 16px;\n}\n\n.shelfIcon {\n  font-size: 30px;\n  margin-bottom: 8px;\n}\n\n.shelfCard h5 {\n  margin: 0 0 8px;\n  color: var(--accent);\n  font-size: 18px;\n}\n\n.shelfCard p {\n  color: var(--muted);\n  margin: 0;\n}\n\n.libraryPath {\n  font-family: Consolas, monospace;\n  color: var(--warn);\n  word-break: break-all;\n}\n\n.libraryHero {\n  margin-bottom: 18px;\n}\n'
RENDERER_PATCH = '\n// Feature 002F Library room upgrade\nfunction renderLibraryUpgrade() {\n  const library = document.getElementById(\'library\');\n  if (!library || library.dataset.upgraded === \'true\') return;\n  library.dataset.upgraded = \'true\';\n  library.innerHTML = `\n    <article class="card wide libraryHero">\n      <div class="sectionHeader">\n        <div>\n          <p class="eyebrow">Iron Library</p>\n          <h4>Knowledge, Manuals, Notes, Comics</h4>\n        </div>\n        <span id="libraryStatus" class="badge">Checking</span>\n      </div>\n      <p class="roomIntro">The Library is where KayocktheOS will store, index, search, and explain your documents. This room prepares the visible foundation for searchable knowledge.</p>\n    </article>\n\n    <div class="roomSplit">\n      <div>\n        <article class="card">\n          <h4>Library Shelf</h4>\n          <div id="libraryShelf" class="libraryShelf"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Library Readiness</h4>\n          <div id="libraryReadiness" class="smallList"></div>\n        </article>\n      </div>\n\n      <div>\n        <article class="card">\n          <h4>What to Index Next</h4>\n          <div id="libraryGuidance" class="smallList"></div>\n        </article>\n\n        <article class="card chatCard">\n          <h4>Future Library Tools</h4>\n          <div id="libraryFuture" class="smallList"></div>\n        </article>\n      </div>\n    </div>\n  `;\n}\n\nfunction renderLibraryData() {\n  renderLibraryUpgrade();\n\n  const assets = state.status?.system?.assets || {};\n  const knowledgeFiles = assets.knowledge_files ?? 0;\n  const status = document.getElementById(\'libraryStatus\');\n  if (status) status.textContent = knowledgeFiles ? `${knowledgeFiles} files` : \'Empty / Unknown\';\n\n  const shelf = document.getElementById(\'libraryShelf\');\n  if (shelf) {\n    const cards = [\n      [\'📄\', \'Documents\', knowledgeFiles ? `${knowledgeFiles} known files` : \'Waiting for files\', \'PDFs, DOCX, TXT, Markdown, HTML\'],\n      [\'🐧\', \'Linux Shelf\', \'Ready for import\', \'Linux Bible, commands, manuals\'],\n      [\'🧠\', \'Project Memory\', \'Planned\', \'Architecture laws, decisions, changelog\'],\n      [\'🎭\', \'Comics & Stories\', \'Planned\', \'Creative references and motion comic source\'],\n      [\'🔎\', \'Search Index\', \'Not built yet\', \'Semantic search comes in a future feature\'],\n      [\'👁\', \'OCR\', \'Not built yet\', \'Scanned PDFs and images need OCR support\']\n    ];\n    shelf.innerHTML = cards.map(([icon,title,value,detail]) => `\n      <div class="shelfCard">\n        <div class="shelfIcon">${icon}</div>\n        <h5>${escapeHtml(title)}</h5>\n        <p><strong>${escapeHtml(value)}</strong></p>\n        <p>${escapeHtml(detail)}</p>\n      </div>\n    `).join(\'\');\n  }\n\n  const readiness = document.getElementById(\'libraryReadiness\');\n  if (readiness) {\n    readiness.innerHTML = [\n      item(\'Knowledge Folder\', \'Knowledge/\', \'ok\'),\n      item(\'Known Files\', String(knowledgeFiles), knowledgeFiles ? \'ok\' : \'wait\'),\n      item(\'Index Engine\', \'Not installed yet\', \'wait\'),\n      item(\'OCR\', \'Not installed yet\', \'wait\'),\n      item(\'Semantic Search\', \'Planned complete feature\', \'wait\')\n    ].join(\'\');\n  }\n\n  const guidance = document.getElementById(\'libraryGuidance\');\n  if (guidance) {\n    const rows = [];\n    if (!knowledgeFiles) rows.push(item(\'Add documents\', \'Copy manuals, books, notes, or PDFs into Knowledge/.\', \'wait\'));\n    rows.push(item(\'Linux Bible\', \'Good first import for the Iron Library.\', \'ok\'));\n    rows.push(item(\'Project Docs\', \'Index Docs/ and Forge/ to let the Academy explain KayocktheOS.\', \'ok\'));\n    rows.push(item(\'Comics\', \'Future Creative Studio can use story/comic references.\', \'wait\'));\n    rows.push(item(\'Next complete feature\', \'Build Library Indexer with search from the Bridge.\', \'wait\'));\n    guidance.innerHTML = rows.join(\'\');\n  }\n\n  const future = document.getElementById(\'libraryFuture\');\n  if (future) {\n    future.innerHTML = [\n      item(\'Read PDF\', \'Extract text from PDFs.\', \'wait\'),\n      item(\'Search Library\', \'Keyword and semantic search.\', \'wait\'),\n      item(\'Ask Library\', \'Answer questions using local documents.\', \'wait\'),\n      item(\'Cite Sources\', \'Show where an answer came from.\', \'wait\'),\n      item(\'OCR Scans\', \'Read scanned manuals and images.\', \'wait\')\n    ].join(\'\');\n  }\n}\n'

def info(msg):
    print(f"[Feature 002F Library] {msg}")

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
        if "Feature 002F - Library Room" not in old:
            style.write_text(old.rstrip() + "\n\n" + STYLE_APPEND, encoding="utf-8")
    if renderer.exists():
        old = renderer.read_text(encoding="utf-8", errors="replace")
        if "Feature 002F Library room upgrade" not in old:
            old = old.rstrip() + "\n\n" + RENDERER_PATCH + "\n"
        if "renderLibraryData();" not in old:
            old = old.replace("renderNotifications();", "renderNotifications();\n  renderLibraryData();")
        renderer.write_text(old, encoding="utf-8")
    info("Library room upgraded.")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text and "feature_002f_library_room: enabled" not in text:
        text += "\n  feature_002f_library_room: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002f_library_room: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002F_LIBRARY_ROOM.md", """# Feature 002F - Library Room

The Iron Library room now has visible shelves, readiness, and next-index guidance.

## Adds

- Library shelf cards
- Knowledge file count
- Readiness panel
- Future Library tool list
- Guidance for what to index next

## Run

```bat
Start_Bridge.bat
```

Open the Library room.
""")
    write_text("Forge/Decisions/0023_library_room.md", """# Decision 0023 - Library Room

The Library should be a visible room, not a hidden document folder.

Its goal is to become the Operator's searchable second brain.
""")
    write_text("Foundry/Releases/feature002f_library_room_notes.md", "# Feature 002F - Library Room\n\nAdds Iron Library shelves and indexing guidance.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002F - Library Room\n\n- Added Iron Library shelf cards.\n- Added knowledge-file readiness panel.\n- Added future Library tools and next-index guidance.\n"
    if "Feature 002F - Library Room" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_bridge()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002F Library Room complete.")
    info("Restart Start_Bridge.bat and open Library.")

if __name__ == "__main__":
    main()
