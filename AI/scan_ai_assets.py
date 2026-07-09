from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATTERNS = ["*.gguf","*.safetensors","*.ckpt","*.bin","*.onnx","*.pt","*.pth"]

def parse_model_refs():
    refs = []
    ref_file = ROOT / "AI" / "Model_Links" / "FoxAI_Model_References.txt"
    if not ref_file.exists():
        return refs
    for line in ref_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        refs.append({"name": key.strip(), "path": value.strip().strip('"')})
    return refs

def resolve_ref_path(value):
    p = Path(value)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p

def scan_folder(folder):
    folder = Path(folder)
    models = []
    if not folder.exists():
        return models
    for pattern in MODEL_PATTERNS:
        for file in folder.rglob(pattern):
            try:
                stat = file.stat()
                try:
                    rel = str(file.relative_to(ROOT))
                except Exception:
                    rel = str(file)
                models.append({
                    "name": file.name,
                    "path": str(file),
                    "relative_path": rel,
                    "extension": file.suffix.lower(),
                    "size_gb": round(stat.st_size / (1024 ** 3), 3),
                    "size_mb": round(stat.st_size / (1024 ** 2), 1),
                    "source": "local" if str(file).startswith(str(ROOT)) else "reference"
                })
            except Exception:
                pass
    return models

def build_ai_assets():
    local_models = scan_folder(ROOT / "AI" / "Models")
    refs = parse_model_refs()
    referenced_models = []
    for ref in refs:
        referenced_models.extend(scan_folder(resolve_ref_path(ref["path"])))

    all_models = local_models + referenced_models
    by_ext = {}
    total_gb = 0
    for model in all_models:
        by_ext[model["extension"]] = by_ext.get(model["extension"], 0) + 1
        total_gb += model.get("size_gb", 0)

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "local_model_root": str(ROOT / "AI" / "Models"),
        "references": refs,
        "summary": {
            "total_models": len(all_models),
            "local_models": len(local_models),
            "referenced_models": len(referenced_models),
            "total_size_gb": round(total_gb, 3),
            "by_extension": by_ext
        },
        "models": sorted(all_models, key=lambda x: (x["extension"], x["name"].lower()))
    }

def write_inventory():
    assets = build_ai_assets()
    out = ROOT / "AI" / "Inventory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ai_assets.json").write_text(json.dumps(assets, indent=2), encoding="utf-8")
    md = ["# AI Asset Inventory", "", f"Generated: {assets['generated_at']}", "", "## Summary", ""]
    s = assets["summary"]
    md += [
        f"- Total models: {s['total_models']}",
        f"- Local models: {s['local_models']}",
        f"- Referenced models: {s['referenced_models']}",
        f"- Total size: {s['total_size_gb']} GB",
        "",
        "## Models",
        ""
    ]
    for model in assets["models"][:500]:
        md.append(f"- `{model['name']}` — {model['extension']} — {model['size_gb']} GB — {model['source']}")
    (out / "AI_ASSET_INVENTORY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return assets

if __name__ == "__main__":
    assets = write_inventory()
    print(json.dumps(assets["summary"], indent=2))
