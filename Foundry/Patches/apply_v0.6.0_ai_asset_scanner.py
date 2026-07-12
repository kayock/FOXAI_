from pathlib import Path
import shutil
import datetime
import json
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.6.0_before_ai_asset_scanner_{STAMP}"

SCANNER_CODE = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[1]\nMODEL_PATTERNS = ["*.gguf","*.safetensors","*.ckpt","*.bin","*.onnx","*.pt","*.pth"]\n\ndef parse_model_refs():\n    refs = []\n    ref_file = ROOT / "AI" / "Model_Links" / "FoxAI_Model_References.txt"\n    if not ref_file.exists():\n        return refs\n    for line in ref_file.read_text(encoding="utf-8", errors="replace").splitlines():\n        line = line.strip()\n        if not line or line.startswith("#") or "=" not in line:\n            continue\n        key, value = line.split("=", 1)\n        refs.append({"name": key.strip(), "path": value.strip().strip(\'"\')})\n    return refs\n\ndef resolve_ref_path(value):\n    p = Path(value)\n    if not p.is_absolute():\n        p = (ROOT / p).resolve()\n    return p\n\ndef scan_folder(folder):\n    folder = Path(folder)\n    models = []\n    if not folder.exists():\n        return models\n    for pattern in MODEL_PATTERNS:\n        for file in folder.rglob(pattern):\n            try:\n                stat = file.stat()\n                try:\n                    rel = str(file.relative_to(ROOT))\n                except Exception:\n                    rel = str(file)\n                models.append({\n                    "name": file.name,\n                    "path": str(file),\n                    "relative_path": rel,\n                    "extension": file.suffix.lower(),\n                    "size_gb": round(stat.st_size / (1024 ** 3), 3),\n                    "size_mb": round(stat.st_size / (1024 ** 2), 1),\n                    "source": "local" if str(file).startswith(str(ROOT)) else "reference"\n                })\n            except Exception:\n                pass\n    return models\n\ndef build_ai_assets():\n    local_models = scan_folder(ROOT / "AI" / "Models")\n    refs = parse_model_refs()\n    referenced_models = []\n    for ref in refs:\n        referenced_models.extend(scan_folder(resolve_ref_path(ref["path"])))\n\n    all_models = local_models + referenced_models\n    by_ext = {}\n    total_gb = 0\n    for model in all_models:\n        by_ext[model["extension"]] = by_ext.get(model["extension"], 0) + 1\n        total_gb += model.get("size_gb", 0)\n\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "local_model_root": str(ROOT / "AI" / "Models"),\n        "references": refs,\n        "summary": {\n            "total_models": len(all_models),\n            "local_models": len(local_models),\n            "referenced_models": len(referenced_models),\n            "total_size_gb": round(total_gb, 3),\n            "by_extension": by_ext\n        },\n        "models": sorted(all_models, key=lambda x: (x["extension"], x["name"].lower()))\n    }\n\ndef write_inventory():\n    assets = build_ai_assets()\n    out = ROOT / "AI" / "Inventory"\n    out.mkdir(parents=True, exist_ok=True)\n    (out / "ai_assets.json").write_text(json.dumps(assets, indent=2), encoding="utf-8")\n    md = ["# AI Asset Inventory", "", f"Generated: {assets[\'generated_at\']}", "", "## Summary", ""]\n    s = assets["summary"]\n    md += [\n        f"- Total models: {s[\'total_models\']}",\n        f"- Local models: {s[\'local_models\']}",\n        f"- Referenced models: {s[\'referenced_models\']}",\n        f"- Total size: {s[\'total_size_gb\']} GB",\n        "",\n        "## Models",\n        ""\n    ]\n    for model in assets["models"][:500]:\n        md.append(f"- `{model[\'name\']}` — {model[\'extension\']} — {model[\'size_gb\']} GB — {model[\'source\']}")\n    (out / "AI_ASSET_INVENTORY.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")\n    return assets\n\nif __name__ == "__main__":\n    assets = write_inventory()\n    print(json.dumps(assets["summary"], indent=2))\n'

def info(msg):
    print(f"[KayocktheOS v0.6.0] {msg}")

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
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_scanner():
    write_text("AI/scan_ai_assets.py", SCANNER_CODE)
    spec = importlib.util.spec_from_file_location("kayock_ai_asset_scanner", ROOT / "AI/scan_ai_assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assets = mod.write_inventory()
    info(f"AI inventory written with {assets['summary']['total_models']} model(s).")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; scanner installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")
    if "def ai_assets(" not in old:
        insert = """
def ai_assets():
    try:
        scanner = ROOT / "AI" / "scan_ai_assets.py"
        if scanner.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_ai_asset_scanner", scanner)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_inventory()
    except Exception as exc:
        return {"error": str(exc), "summary": {"total_models": 0}}
    return {"summary": {"total_models": 0}, "models": []}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"ai_assets": ai_assets(),' not in old:
        old = old.replace('"system": system_scan(),', '"system": system_scan(),\n        "ai_assets": ai_assets(),')

    if 'elif path == "/api/ai-assets":' not in old:
        old = old.replace(
            'elif path == "/api/system":\n            self._json(system_scan())',
            'elif path == "/api/system":\n            self._json(system_scan())\n        elif path == "/api/ai-assets":\n            self._json(ai_assets())'
        )
        old = old.replace('["/api/ping", "/api/status", "/api/system"]', '["/api/ping", "/api/status", "/api/system", "/api/ai-assets"]')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/ai-assets support.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 0.6.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: AI Asset Scanner", text, count=1)
        if "ai_asset_scanner: enabled" not in text:
            text += "\n  ai_asset_scanner: enabled\n" if "features:" in text else "\nfeatures:\n  ai_asset_scanner: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/AI_ASSET_SCANNER.md", """# AI Asset Scanner

v0.6.0 adds read-only AI asset inventory.

## Scans

- `AI/Models`
- Paths referenced in `AI/Model_Links/FoxAI_Model_References.txt`

## API endpoint

```text
http://127.0.0.1:8844/api/ai-assets
```
""")
    write_text("Forge/Decisions/0006_ai_asset_scanner.md", """# Decision 0006 - AI Asset Scanner

KayocktheOS should discover available local and referenced AI assets.

The scanner is read-only and does not download, move, or delete models.
""")
    write_text("Foundry/Releases/v0.6.0_release_notes.md", "# v0.6.0 Release Notes - AI Asset Scanner\n\nAdds read-only model inventory and `/api/ai-assets`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.6.0 - AI Asset Scanner\n\n- Added read-only AI asset scanner.\n- Added `AI/scan_ai_assets.py`.\n- Added AI inventory output in `AI/Inventory`.\n- Added `/api/ai-assets`.\n- `/api/status` now includes `ai_assets`.\n"
    if "v0.6.0 - AI Asset Scanner" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_scanner()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v0.6.0 AI Asset Scanner patch complete.")
    info("Restart KayocktheOS and check /api/ai-assets.")

if __name__ == "__main__":
    main()
