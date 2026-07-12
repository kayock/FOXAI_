from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = ROOT / "System" / "Registry" / "modules"
DISCOVERY_PATHS = [
    "Academy",
    "Knowledge",
    "RepairBay",
    "CreativeStudio",
    "AI",
    "Shell/KayockBrowser",
    "System",
    "Forge",
    "Foundry",
]

def parse_simple_yaml(path):
    data = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data

def discover_modules():
    modules = []
    seen = set()
    for rel in DISCOVERY_PATHS:
        base = ROOT / rel
        if not base.exists():
            continue
        candidates = []
        direct = base / "module.yaml"
        if direct.exists():
            candidates.append(direct)
        candidates.extend(base.rglob("*.module.yaml"))
        for manifest in candidates:
            try:
                item = parse_simple_yaml(manifest)
                module_id = item.get("id") or manifest.parent.name.lower().replace(" ", "_")
                if module_id in seen:
                    continue
                seen.add(module_id)
                item.setdefault("id", module_id)
                item.setdefault("name", module_id.replace("_", " ").title())
                item.setdefault("status", "planned")
                item.setdefault("owner", rel.split("/")[0])
                item.setdefault("path", str(manifest.parent.relative_to(ROOT)).replace("\\", "/"))
                item.setdefault("description", "")
                item.setdefault("icon", "□")
                modules.append(item)
            except Exception as exc:
                modules.append({
                    "id": f"error_{manifest.parent.name}",
                    "name": f"Manifest Error: {manifest.parent.name}",
                    "status": "error",
                    "owner": rel,
                    "path": str(manifest.relative_to(ROOT)).replace("\\", "/"),
                    "description": str(exc),
                    "icon": "!"
                })
    return modules

def write_registry():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    modules = discover_modules()
    for old in REGISTRY_DIR.glob("*.module.yaml"):
        old.unlink()
    for item in modules:
        module_id = item.get("id", "unknown")
        lines = [
            f"id: {module_id}",
            f"name: {item.get('name','')}",
            f"status: {item.get('status','planned')}",
            f"owner: {item.get('owner','')}",
            f"path: {item.get('path','')}",
            f"icon: {item.get('icon','□')}",
            f"description: {item.get('description','')}",
            f"version: {item.get('version','')}",
            f"entry: {item.get('entry','none')}",
        ]
        (REGISTRY_DIR / f"{module_id}.module.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REGISTRY_DIR / "modules.json").write_text(json.dumps(modules, indent=2), encoding="utf-8")
    return modules

if __name__ == "__main__":
    mods = write_registry()
    print(f"Discovered {len(mods)} modules.")
    for mod in mods:
        print(f"- {mod.get('icon','□')} {mod.get('name')} [{mod.get('status')}]")
