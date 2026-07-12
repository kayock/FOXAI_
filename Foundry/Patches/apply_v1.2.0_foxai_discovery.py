from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v1.2.0_before_foxai_discovery_{STAMP}"

FOXAI_DISCOVERY = 'from pathlib import Path\nimport json\nimport datetime\nimport os\n\nROOT = Path(__file__).resolve().parents[1]\nFOXAI_ROOT = Path("Z:/FOXAI")\n\nLLM_PATTERNS = ["*.gguf"]\nIMAGE_PATTERNS = ["*.safetensors", "*.ckpt"]\nWORKFLOW_PATTERNS = ["*.json"]\n\ndef file_item(path, category):\n    stat = path.stat()\n    return {\n        "name": path.name,\n        "path": str(path),\n        "category": category,\n        "extension": path.suffix.lower(),\n        "size_gb": round(stat.st_size / (1024 ** 3), 3),\n        "size_mb": round(stat.st_size / (1024 ** 2), 1),\n        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),\n        "capabilities": infer_capabilities(path.name, category)\n    }\n\ndef infer_capabilities(name, category):\n    n = name.lower()\n    caps = []\n    if category == "llm":\n        caps.append("chat")\n        if "coder" in n or "code" in n:\n            caps.append("coding")\n        if "deepseek" in n or "r1" in n:\n            caps.append("reasoning")\n        if "vl" in n or "vision" in n:\n            caps.append("vision")\n        if "qwen" in n:\n            caps.append("general")\n    if category == "image_checkpoint":\n        caps += ["image_generation", "comfyui"]\n        if "turbo" in n:\n            caps.append("fast_generation")\n        if "sdxl" in n or "xl" in n:\n            caps.append("sdxl")\n    if category == "workflow":\n        caps += ["workflow", "comfyui"]\n    return sorted(set(caps))\n\ndef scan_patterns(base, patterns, category):\n    items = []\n    if not base.exists():\n        return items\n    for pattern in patterns:\n        for path in base.rglob(pattern):\n            try:\n                items.append(file_item(path, category))\n            except Exception:\n                pass\n    return items\n\ndef scan_foxai():\n    exists = FOXAI_ROOT.exists()\n    llms = []\n    image_models = []\n    workflows = []\n    comfy_root = FOXAI_ROOT / "ComfyUI"\n\n    if exists:\n        llms = scan_patterns(FOXAI_ROOT, LLM_PATTERNS, "llm")\n        image_models = scan_patterns(comfy_root / "models", IMAGE_PATTERNS, "image_checkpoint")\n        workflows = scan_patterns(comfy_root, WORKFLOW_PATTERNS, "workflow")\n\n    all_assets = llms + image_models + workflows\n    by_category = {}\n    total_gb = 0\n    for item in all_assets:\n        by_category[item["category"]] = by_category.get(item["category"], 0) + 1\n        total_gb += item.get("size_gb", 0)\n\n    payload = {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "foxai_root": str(FOXAI_ROOT),\n        "exists": exists,\n        "summary": {\n            "total_assets": len(all_assets),\n            "llm_models": len(llms),\n            "image_models": len(image_models),\n            "workflows": len(workflows),\n            "total_size_gb": round(total_gb, 3),\n            "by_category": by_category\n        },\n        "assets": {\n            "llms": sorted(llms, key=lambda x: x["name"].lower()),\n            "image_models": sorted(image_models, key=lambda x: x["name"].lower()),\n            "workflows": sorted(workflows, key=lambda x: x["name"].lower())\n        }\n    }\n    return payload\n\ndef write_inventory():\n    payload = scan_foxai()\n    out = ROOT / "AI" / "Inventory"\n    out.mkdir(parents=True, exist_ok=True)\n    (out / "foxai_inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")\n\n    md = [\n        "# FOXAI Inventory",\n        "",\n        f"Generated: {payload[\'generated_at\']}",\n        f"FOXAI root: `{payload[\'foxai_root\']}`",\n        f"Exists: {payload[\'exists\']}",\n        "",\n        "## Summary",\n        "",\n        f"- Total assets: {payload[\'summary\'][\'total_assets\']}",\n        f"- LLM models: {payload[\'summary\'][\'llm_models\']}",\n        f"- Image models: {payload[\'summary\'][\'image_models\']}",\n        f"- Workflows: {payload[\'summary\'][\'workflows\']}",\n        f"- Total size: {payload[\'summary\'][\'total_size_gb\']} GB",\n        "",\n        "## LLM Models",\n        ""\n    ]\n    for item in payload["assets"]["llms"][:200]:\n        md.append(f"- `{item[\'name\']}` — {item[\'size_gb\']} GB — {\', \'.join(item[\'capabilities\'])}")\n\n    md += ["", "## Image Models", ""]\n    for item in payload["assets"]["image_models"][:200]:\n        md.append(f"- `{item[\'name\']}` — {item[\'size_gb\']} GB — {\', \'.join(item[\'capabilities\'])}")\n\n    (out / "FOXAI_INVENTORY.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")\n    return payload\n\nif __name__ == "__main__":\n    print(json.dumps(write_inventory()["summary"], indent=2))\n'

def info(msg):
    print(f"[KayocktheOS v1.2.0] {msg}")

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

def install_discovery():
    write_text("AI/foxai_discovery.py", FOXAI_DISCOVERY)
    spec = importlib.util.spec_from_file_location("kayock_foxai_discovery", ROOT / "AI/foxai_discovery.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    payload = mod.write_inventory()
    info(f"FOXAI inventory written with {payload['summary']['total_assets']} asset(s).")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; FOXAI discovery installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def foxai_status(" not in old:
        insert = """
def foxai_status():
    try:
        scanner = ROOT / "AI" / "foxai_discovery.py"
        if scanner.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_foxai_discovery", scanner)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_inventory()
    except Exception as exc:
        return {"error": str(exc), "exists": False, "summary": {"total_assets": 0}}
    return {"exists": False, "summary": {"total_assets": 0}, "assets": {}}
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"foxai": foxai_status(),' not in old:
        # Insert near AI assets if present, otherwise near system
        if '"ai_assets": ai_assets(),' in old:
            old = old.replace('"ai_assets": ai_assets(),', '"ai_assets": ai_assets(),\n        "foxai": foxai_status(),')
        else:
            old = old.replace('"system": system_scan(),', '"system": system_scan(),\n        "foxai": foxai_status(),')

    if 'elif path == "/api/foxai":' not in old:
        if 'elif path == "/api/ai-assets":' in old:
            old = old.replace(
                'elif path == "/api/ai-assets":\n            self._json(ai_assets())',
                'elif path == "/api/ai-assets":\n            self._json(ai_assets())\n        elif path == "/api/foxai":\n            self._json(foxai_status())'
            )
        else:
            old = old.replace(
                'elif path == "/api/system":\n            self._json(system_scan())',
                'elif path == "/api/system":\n            self._json(system_scan())\n        elif path == "/api/foxai":\n            self._json(foxai_status())'
            )

    path.write_text(old, encoding="utf-8")
    info("Core API patched with /api/foxai support.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 1.2.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: FOXAI Discovery", text, count=1)
        if "foxai_discovery: enabled" not in text:
            text += "\n  foxai_discovery: enabled\n" if "features:" in text else "\nfeatures:\n  foxai_discovery: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FOXAI_DISCOVERY.md", """# FOXAI Discovery

v1.2.0 makes KayocktheOS aware of the FOXAI asset warehouse.

## Canonical path

```text
Z:\\FOXAI
```

## Scans

- GGUF language models
- ComfyUI checkpoints
- ComfyUI workflow JSON files

## API endpoint

```text
http://127.0.0.1:8844/api/foxai
```

## Principle

FOXAI owns AI assets.
KayocktheOS discovers, catalogs, and orchestrates them.
""")
    write_text("Forge/Decisions/0013_foxai_discovery.md", """# Decision 0013 - FOXAI Discovery

FOXAI is the AI asset warehouse.

KayocktheOS should not duplicate large models. It discovers and orchestrates assets from `Z:\FOXAI`.
""")
    write_text("Foundry/Releases/v1.2.0_release_notes.md", "# v1.2.0 Release Notes - FOXAI Discovery\n\nAdds `AI/foxai_discovery.py` and `/api/foxai`.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v1.2.0 - FOXAI Discovery\n\n- Added `AI/foxai_discovery.py`.\n- Added FOXAI inventory output in `AI/Inventory`.\n- Added `/api/foxai`.\n- Established `Z:\\FOXAI` as the canonical AI asset warehouse.\n"
    if "v1.2.0 - FOXAI Discovery" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_discovery()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v1.2.0 FOXAI Discovery patch complete.")
    info("Restart KayocktheOS and test /api/foxai.")

if __name__ == "__main__":
    main()
