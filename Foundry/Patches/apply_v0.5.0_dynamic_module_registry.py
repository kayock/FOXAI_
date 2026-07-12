from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.5.0_before_dynamic_registry_{STAMP}"

REGISTRY_BUILDER = 'from pathlib import Path\nimport json\n\nROOT = Path(__file__).resolve().parents[2]\nREGISTRY_DIR = ROOT / "System" / "Registry" / "modules"\nDISCOVERY_PATHS = [\n    "Academy",\n    "Knowledge",\n    "RepairBay",\n    "CreativeStudio",\n    "AI",\n    "Shell/KayockBrowser",\n    "System",\n    "Forge",\n    "Foundry",\n]\n\ndef parse_simple_yaml(path):\n    data = {}\n    text = path.read_text(encoding="utf-8", errors="replace")\n    for line in text.splitlines():\n        if not line.strip() or line.strip().startswith("#") or ":" not in line:\n            continue\n        key, value = line.split(":", 1)\n        data[key.strip()] = value.strip()\n    return data\n\ndef discover_modules():\n    modules = []\n    seen = set()\n    for rel in DISCOVERY_PATHS:\n        base = ROOT / rel\n        if not base.exists():\n            continue\n        candidates = []\n        direct = base / "module.yaml"\n        if direct.exists():\n            candidates.append(direct)\n        candidates.extend(base.rglob("*.module.yaml"))\n        for manifest in candidates:\n            try:\n                item = parse_simple_yaml(manifest)\n                module_id = item.get("id") or manifest.parent.name.lower().replace(" ", "_")\n                if module_id in seen:\n                    continue\n                seen.add(module_id)\n                item.setdefault("id", module_id)\n                item.setdefault("name", module_id.replace("_", " ").title())\n                item.setdefault("status", "planned")\n                item.setdefault("owner", rel.split("/")[0])\n                item.setdefault("path", str(manifest.parent.relative_to(ROOT)).replace("\\\\", "/"))\n                item.setdefault("description", "")\n                item.setdefault("icon", "□")\n                modules.append(item)\n            except Exception as exc:\n                modules.append({\n                    "id": f"error_{manifest.parent.name}",\n                    "name": f"Manifest Error: {manifest.parent.name}",\n                    "status": "error",\n                    "owner": rel,\n                    "path": str(manifest.relative_to(ROOT)).replace("\\\\", "/"),\n                    "description": str(exc),\n                    "icon": "!"\n                })\n    return modules\n\ndef write_registry():\n    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)\n    modules = discover_modules()\n    for old in REGISTRY_DIR.glob("*.module.yaml"):\n        old.unlink()\n    for item in modules:\n        module_id = item.get("id", "unknown")\n        lines = [\n            f"id: {module_id}",\n            f"name: {item.get(\'name\',\'\')}",\n            f"status: {item.get(\'status\',\'planned\')}",\n            f"owner: {item.get(\'owner\',\'\')}",\n            f"path: {item.get(\'path\',\'\')}",\n            f"icon: {item.get(\'icon\',\'□\')}",\n            f"description: {item.get(\'description\',\'\')}",\n            f"version: {item.get(\'version\',\'\')}",\n            f"entry: {item.get(\'entry\',\'none\')}",\n        ]\n        (REGISTRY_DIR / f"{module_id}.module.yaml").write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n    (REGISTRY_DIR / "modules.json").write_text(json.dumps(modules, indent=2), encoding="utf-8")\n    return modules\n\nif __name__ == "__main__":\n    mods = write_registry()\n    print(f"Discovered {len(mods)} modules.")\n    for mod in mods:\n        print(f"- {mod.get(\'icon\',\'□\')} {mod.get(\'name\')} [{mod.get(\'status\')}]")\n'

DEPARTMENTS = [
    {"id":"academy","name":"Academy","status":"planned","owner":"Academy","path":"Academy","icon":"🎓","description":"Professors, colleges, lessons, and understanding-first AI."},
    {"id":"iron_library","name":"Iron Library","status":"planned","owner":"Knowledge","path":"Knowledge","icon":"📚","description":"Books, PDFs, manuals, comics, notes, code references, and searchable documents."},
    {"id":"repair_bay","name":"Repair Bay","status":"planned","owner":"RepairBay","path":"RepairBay","icon":"🛠","description":"Read-only diagnostics, machine reports, and future repair assistance."},
    {"id":"creative_studio","name":"Creative Studio","status":"planned","owner":"CreativeStudio","path":"CreativeStudio","icon":"🎨","description":"Images, video, audio, comics, prompts, and creative outputs."},
    {"id":"ai_engines","name":"AI Engines","status":"planned","owner":"AI","path":"AI","icon":"🤖","description":"Local models, model references, routing, and AI runtime engines."},
    {"id":"shell","name":"Kayock Browser Shell","status":"enabled","owner":"Shell","path":"Shell/KayockBrowser","icon":"🌐","description":"Operator-facing desktop environment built on Kayock Browser."},
    {"id":"core_system","name":"Core System","status":"enabled","owner":"System","path":"System","icon":"⚙","description":"Launchers, Core API, configuration, logging, health checks, and registry."},
    {"id":"forge","name":"Forge","status":"enabled","owner":"Forge","path":"Forge","icon":"🔨","description":"Charters, journal, decisions, milestones, and project memory."},
    {"id":"foundry","name":"Foundry","status":"enabled","owner":"Foundry","path":"Foundry","icon":"🏛","description":"Patch tools, releases, packaging, builds, and backup automation."},
]

def info(msg):
    print(f"[KayocktheOS v0.5.0] {msg}")

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
    for item in ["manifest.yaml","System","Shell","Academy","Knowledge","RepairBay","CreativeStudio","AI","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def create_department_manifests():
    info("Writing department module manifests...")
    for dep in DEPARTMENTS:
        folder = ROOT / dep["path"]
        folder.mkdir(parents=True, exist_ok=True)
        content = f"""id: {dep['id']}
name: {dep['name']}
status: {dep['status']}
owner: {dep['owner']}
path: {dep['path']}
icon: {dep['icon']}
description: {dep['description']}
version: 0.5.0
entry: none
"""
        (folder / "module.yaml").write_text(content, encoding="utf-8")

def create_registry_builder():
    write_text("System/Registry/build_registry.py", REGISTRY_BUILDER)

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; registry builder installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")
    if "build_registry.py" in old and "modules.json" in old:
        info("Core API already appears to include dynamic registry support.")
        return
    new_func = """def modules():
    try:
        registry_builder = ROOT / "System/Registry/build_registry.py"
        if registry_builder.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_registry_builder", registry_builder)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_registry()
    except Exception:
        pass

    out = []
    reg = ROOT / "System/Registry/modules"
    for file in sorted(reg.glob("*.module.yaml")):
        text = read_text(file)
        item = {}
        for key in ["id", "name", "status", "owner", "path", "description", "icon", "version", "entry"]:
            item[key] = simple_yaml_value(text, key, "")
        out.append(item)
    return out
"""
    pattern = re.compile(r"def modules\(\):\n(?:    .*\n)+?(?=\ndef |\nclass |\ndef health|\ndef recent_logs|\ndef status_payload)", re.MULTILINE)
    if pattern.search(old):
        updated = pattern.sub(new_func + "\n", old)
        path.write_text(updated, encoding="utf-8")
        info("Patched Core API modules() for dynamic registry.")
    else:
        info("Could not safely patch modules(); API keeps previous module reading.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 0.5.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Dynamic Module Registry", text, count=1)
        if "dynamic_module_registry: enabled" not in text:
            text += "\n  dynamic_module_registry: enabled\n" if "features:" in text else "\nfeatures:\n  dynamic_module_registry: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/DYNAMIC_MODULE_REGISTRY.md", """# Dynamic Module Registry

v0.5.0 introduces department-level `module.yaml` files.

The Core can discover modules from major departments and build:

```text
System/Registry/modules/
System/Registry/modules/modules.json
```

Run manually:

```bat
python System\\Registry\\build_registry.py
```

## Why

Departments should advertise themselves. The Bridge should not depend on hardcoded module lists forever.
""")
    write_text("Forge/Decisions/0005_dynamic_module_registry.md", """# Decision 0005 - Dynamic Module Registry

Departments advertise themselves with `module.yaml`.

Adding a department should require adding a manifest, not editing Core launcher logic.
""")
    write_text("Foundry/Releases/v0.5.0_release_notes.md", """# v0.5.0 Release Notes - Dynamic Module Registry

Adds module discovery using department `module.yaml` files.
""")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.5.0 - Dynamic Module Registry\n\n- Added department `module.yaml` manifests.\n- Added `System/Registry/build_registry.py`.\n- Core API can now discover modules dynamically where safe.\n- Added documentation and Forge decision record.\n"
    if "v0.5.0 - Dynamic Module Registry" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def run_registry_builder():
    try:
        spec = importlib.util.spec_from_file_location("kayock_registry_builder", ROOT / "System/Registry/build_registry.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mods = mod.write_registry()
        info(f"Registry built with {len(mods)} modules.")
    except Exception as exc:
        info(f"Registry build skipped/error: {exc}")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    create_department_manifests()
    create_registry_builder()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    run_registry_builder()
    info("v0.5.0 Dynamic Module Registry patch complete.")
    info("Restart KayocktheOS and check /api/status.")

if __name__ == "__main__":
    main()
