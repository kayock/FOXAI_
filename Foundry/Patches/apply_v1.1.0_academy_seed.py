from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.1.0_before_academy_seed_{STAMP}"

ACADEMY_PY = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nACADEMY = ROOT / "Academy"\nDATA = ACADEMY / "academy.json"\n\nDEFAULT_ACADEMY = {\n    "generated_at": None,\n    "name": "KayocktheOS Academy",\n    "charter": "The purpose of the Academy is not to produce answers. It is to produce understanding.",\n    "startup_greeting": "The Academy is open. Today\'s lesson awaits.",\n    "colleges": [\n        {\n            "id": "practical_curiosity",\n            "name": "College of Practical Curiosity",\n            "professor": "Professor Kayock",\n            "motto": "Wonder is a tool. Build with it.",\n            "domains": ["operator guidance", "project building", "practical problem solving"]\n        },\n        {\n            "id": "scientific_curiosity",\n            "name": "College of Scientific Curiosity",\n            "professor": "Professor Carl Sagan",\n            "motto": "Extraordinary claims require extraordinary evidence.",\n            "domains": ["science", "evidence", "skepticism", "cosmology"]\n        },\n        {\n            "id": "artificial_minds",\n            "name": "College of Artificial Minds",\n            "professor": "Professor Asimov",\n            "motto": "An intelligent machine earns trust by revealing its reasoning.",\n            "domains": ["AI", "safety", "reasoning", "trustworthy systems"]\n        },\n        {\n            "id": "optimistic_futures",\n            "name": "College of Optimistic Futures",\n            "professor": "Professor Roddenberry",\n            "motto": "Technology reaches its highest purpose when it enlarges humanity.",\n            "domains": ["future design", "humanism", "ethics", "hopeful technology"]\n        },\n        {\n            "id": "meta_creativity",\n            "name": "College of Meta Creativity",\n            "professor": "Professor Deadpool",\n            "motto": "The best stories know they\'re being told.",\n            "domains": ["storytelling", "humor", "creative critique", "self-aware media"]\n        },\n        {\n            "id": "linux",\n            "name": "College of Linux",\n            "professor": "Linux Chair",\n            "motto": "Everything is a file until it proves otherwise.",\n            "domains": ["Linux", "filesystems", "shell", "permissions"]\n        },\n        {\n            "id": "macos",\n            "name": "College of macOS",\n            "professor": "macOS Chair",\n            "motto": "The system has an opinion. Understand it before changing it.",\n            "domains": ["macOS", "system design", "defaults", "Apple ecosystem"]\n        },\n        {\n            "id": "networking",\n            "name": "College of Networking",\n            "professor": "Networking Chair",\n            "motto": "Packets never lie.",\n            "domains": ["networking", "diagnostics", "routing", "latency"]\n        },\n        {\n            "id": "software_design",\n            "name": "College of Software Design",\n            "professor": "Software Design Chair",\n            "motto": "Optimization begins only after understanding.",\n            "domains": ["architecture", "code quality", "maintainability"]\n        }\n    ],\n    "lessons": [\n        {\n            "id": "welcome_to_the_academy",\n            "title": "Welcome to the Academy",\n            "college": "practical_curiosity",\n            "summary": "KayocktheOS uses an Academy model so knowledge is organized by domains of expertise, not loose tools."\n        }\n    ]\n}\n\ndef ensure_academy():\n    ACADEMY.mkdir(parents=True, exist_ok=True)\n    (ACADEMY / "Professors").mkdir(parents=True, exist_ok=True)\n    (ACADEMY / "Colleges").mkdir(parents=True, exist_ok=True)\n    (ACADEMY / "Lessons").mkdir(parents=True, exist_ok=True)\n    (ACADEMY / "Charter").mkdir(parents=True, exist_ok=True)\n\n    academy = DEFAULT_ACADEMY.copy()\n    academy["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")\n    DATA.write_text(json.dumps(academy, indent=2), encoding="utf-8")\n\n    (ACADEMY / "Charter" / "ACADEMY_CHARTER.md").write_text(\n        "# Academy Charter\\n\\n"\n        + academy["charter"]\n        + "\\n\\n## Startup Greeting\\n\\n"\n        + academy["startup_greeting"]\n        + "\\n",\n        encoding="utf-8"\n    )\n\n    for college in academy["colleges"]:\n        safe = college["id"]\n        md = [\n            f"# {college[\'name\']}",\n            "",\n            f"Professor: **{college[\'professor\']}**",\n            "",\n            f"Motto: *{college[\'motto\']}*",\n            "",\n            "## Domains",\n            ""\n        ]\n        md += [f"- {d}" for d in college["domains"]]\n        (ACADEMY / "Colleges" / f"{safe}.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")\n\n    return academy\n\ndef academy_status():\n    if not DATA.exists():\n        return ensure_academy()\n    try:\n        return json.loads(DATA.read_text(encoding="utf-8"))\n    except Exception:\n        return ensure_academy()\n\nif __name__ == "__main__":\n    data = ensure_academy()\n    print(json.dumps({"colleges": len(data["colleges"]), "lessons": len(data["lessons"])}, indent=2))\n'

def info(msg):
    print(f"[KayocktheOS v1.1.0] {msg}")

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
    for item in ["manifest.yaml","System","Academy","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_academy():
    write_text("Academy/academy.py", ACADEMY_PY)
    spec = importlib.util.spec_from_file_location("kayock_academy", ROOT / "Academy/academy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = mod.ensure_academy()
    info(f"Academy seeded with {len(data['colleges'])} college(s).")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; Academy installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def academy_status(" not in old:
        insert = """
def academy_status():
    try:
        academy = ROOT / "Academy" / "academy.py"
        if academy.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_academy", academy)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.academy_status()
    except Exception as exc:
        return {"error": str(exc), "colleges": []}
    return {"colleges": [], "lessons": []}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"academy": academy_status(),' not in old:
        old = old.replace('"services": service_bus(),', '"services": service_bus(),\n        "academy": academy_status(),')

    if 'elif path == "/api/academy":' not in old:
        old = old.replace(
            'elif path == "/api/bridge":\n            self._json(bridge_payload())',
            'elif path == "/api/bridge":\n            self._json(bridge_payload())\n        elif path == "/api/academy":\n            self._json(academy_status())'
        )
        old = old.replace('"/api/bridge"]', '"/api/bridge", "/api/academy"]')
        old = old.replace('"/api/bridge", "/api/release-check"]', '"/api/bridge", "/api/academy", "/api/release-check"]')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/academy support.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 1.1.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Academy Seed", text, count=1)
        if "academy_seed: enabled" not in text:
            text += "\n  academy_seed: enabled\n" if "features:" in text else "\nfeatures:\n  academy_seed: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/ACADEMY_SEED.md", """# Academy Seed

v1.1.0 creates the first real Academy data model.

## API endpoint

```text
http://127.0.0.1:8844/api/academy
```

## Includes

- Academy Charter
- Colleges
- Professors
- Mottoes
- Starter lesson

This is not AI inference yet. It is the Academy structure that future AI behavior plugs into.
""")
    write_text("Forge/Decisions/0012_academy_seed.md", """# Decision 0012 - Academy Seed

KayocktheOS organizes expertise through an Academy model.

Domains are represented as Colleges and Professors, not loose tool modules.
""")
    write_text("Foundry/Releases/v1.1.0_release_notes.md", "# v1.1.0 Release Notes - Academy Seed\n\nCreates the first Academy data model and `/api/academy`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.1.0 - Academy Seed\n\n- Added `Academy/academy.py`.\n- Added Academy Charter, Colleges, Professors, and mottoes.\n- Added `/api/academy`.\n- Established Academy data model for future AI behavior.\n"
    if "v1.1.0 - Academy Seed" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_academy()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v1.1.0 Academy Seed patch complete.")
    info("Restart KayocktheOS and test /api/academy.")

if __name__ == "__main__":
    main()
