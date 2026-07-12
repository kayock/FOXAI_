from pathlib import Path
import json
import datetime
import os

ROOT = Path(__file__).resolve().parents[1]
FOXAI_ROOT = Path("Z:/FOXAI")

LLM_PATTERNS = ["*.gguf"]
IMAGE_PATTERNS = ["*.safetensors", "*.ckpt"]
WORKFLOW_PATTERNS = ["*.json"]

def file_item(path, category):
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "category": category,
        "extension": path.suffix.lower(),
        "size_gb": round(stat.st_size / (1024 ** 3), 3),
        "size_mb": round(stat.st_size / (1024 ** 2), 1),
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "capabilities": infer_capabilities(path.name, category)
    }

def infer_capabilities(name, category):
    n = name.lower()
    caps = []
    if category == "llm":
        caps.append("chat")
        if "coder" in n or "code" in n:
            caps.append("coding")
        if "deepseek" in n or "r1" in n:
            caps.append("reasoning")
        if "vl" in n or "vision" in n:
            caps.append("vision")
        if "qwen" in n:
            caps.append("general")
    if category == "image_checkpoint":
        caps += ["image_generation", "comfyui"]
        if "turbo" in n:
            caps.append("fast_generation")
        if "sdxl" in n or "xl" in n:
            caps.append("sdxl")
    if category == "workflow":
        caps += ["workflow", "comfyui"]
    return sorted(set(caps))

def scan_patterns(base, patterns, category):
    items = []
    if not base.exists():
        return items
    for pattern in patterns:
        for path in base.rglob(pattern):
            try:
                items.append(file_item(path, category))
            except Exception:
                pass
    return items

def scan_foxai():
    exists = FOXAI_ROOT.exists()
    llms = []
    image_models = []
    workflows = []
    comfy_root = FOXAI_ROOT / "ComfyUI"

    if exists:
        llms = scan_patterns(FOXAI_ROOT, LLM_PATTERNS, "llm")
        image_models = scan_patterns(comfy_root / "models", IMAGE_PATTERNS, "image_checkpoint")
        workflows = scan_patterns(comfy_root, WORKFLOW_PATTERNS, "workflow")

    all_assets = llms + image_models + workflows
    by_category = {}
    total_gb = 0
    for item in all_assets:
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1
        total_gb += item.get("size_gb", 0)

    payload = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "foxai_root": str(FOXAI_ROOT),
        "exists": exists,
        "summary": {
            "total_assets": len(all_assets),
            "llm_models": len(llms),
            "image_models": len(image_models),
            "workflows": len(workflows),
            "total_size_gb": round(total_gb, 3),
            "by_category": by_category
        },
        "assets": {
            "llms": sorted(llms, key=lambda x: x["name"].lower()),
            "image_models": sorted(image_models, key=lambda x: x["name"].lower()),
            "workflows": sorted(workflows, key=lambda x: x["name"].lower())
        }
    }
    return payload

def write_inventory():
    payload = scan_foxai()
    out = ROOT / "AI" / "Inventory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "foxai_inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md = [
        "# FOXAI Inventory",
        "",
        f"Generated: {payload['generated_at']}",
        f"FOXAI root: `{payload['foxai_root']}`",
        f"Exists: {payload['exists']}",
        "",
        "## Summary",
        "",
        f"- Total assets: {payload['summary']['total_assets']}",
        f"- LLM models: {payload['summary']['llm_models']}",
        f"- Image models: {payload['summary']['image_models']}",
        f"- Workflows: {payload['summary']['workflows']}",
        f"- Total size: {payload['summary']['total_size_gb']} GB",
        "",
        "## LLM Models",
        ""
    ]
    for item in payload["assets"]["llms"][:200]:
        md.append(f"- `{item['name']}` — {item['size_gb']} GB — {', '.join(item['capabilities'])}")

    md += ["", "## Image Models", ""]
    for item in payload["assets"]["image_models"][:200]:
        md.append(f"- `{item['name']}` — {item['size_gb']} GB — {', '.join(item['capabilities'])}")

    (out / "FOXAI_INVENTORY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload

if __name__ == "__main__":
    print(json.dumps(write_inventory()["summary"], indent=2))
