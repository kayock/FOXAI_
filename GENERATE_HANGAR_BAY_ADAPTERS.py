from __future__ import annotations

import json
from pathlib import Path

FOXAI_ROOT = Path(__file__).resolve().parent
DRIVE_ROOT = Path(FOXAI_ROOT.anchor)
HANGAR_ROOT = DRIVE_ROOT / "Hanger Bay"
CAP_ROOT = FOXAI_ROOT / "Capabilities"

KNOWN_CATEGORIES = {
    "autoruns": ("Startup Diagnostics", ["startup", "repair", "diagnostics"]),
    "crystaldiskinfo": ("Storage Diagnostics", ["storage", "smart", "drive_health", "repair"]),
    "hwmonitor": ("Hardware Monitoring", ["hardware_monitoring", "temperatures", "repair"]),
    "systeminformer": ("System Diagnostics", ["processes", "system_monitoring", "repair"]),
    "tcpview": ("Network Diagnostics", ["network", "connections", "repair"]),
    "wiztree": ("Storage Tools", ["disk_usage", "storage", "cleanup"]),
    "qbtorrent": ("Downloads", ["downloads", "torrent"]),
    "stellarium": ("Science", ["astronomy", "education", "science"]),
    "oneloupe": ("Accessibility", ["magnifier", "accessibility"]),
    "passwordgorilla": ("Security", ["passwords", "security"]),
    "pdf_summarizer": ("Knowledge", ["pdfs", "summarizer", "documents"]),
    "renpy": ("Creative Studio", ["visual_novel", "game_dev", "creative"]),
    "subtitleedit": ("Multimedia", ["subtitles", "video", "multimedia"]),
    "virtualmagnifyingglass": ("Accessibility", ["magnifier", "accessibility"]),
    "flux": ("Creative Studio", ["image_generation", "creative_studio"]),
}

def slugify(value: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in value).strip("_")

def find_launchable(folder: Path) -> Path | None:
    # Prefer real app executables, avoid uninstallers/updaters when possible.
    candidates = []
    for p in folder.rglob("*.exe"):
        name = p.name.lower()
        if any(bad in name for bad in ["unins", "uninstall", "setup", "installer", "update", "crash"]):
            continue
        candidates.append(p)

    if not candidates:
        # Some folders may intentionally be document/tool folders.
        return None

    # Prefer portable app launcher names.
    preferred = []
    for p in candidates:
        lower = p.name.lower()
        if "portable" in lower or lower.startswith(folder.name.lower()[:8]):
            preferred.append(p)

    chosen = sorted(preferred or candidates, key=lambda p: (len(p.parts), len(p.name), p.name.lower()))[0]
    return chosen

def classify(folder_name: str):
    key = folder_name.lower()
    for marker, value in KNOWN_CATEGORIES.items():
        if marker in key:
            return value
    if "development" in key:
        return ("Development", ["development", "tools"])
    if "productivity" in key:
        return ("Productivity", ["productivity", "tools"])
    if "multimedia" in key:
        return ("Multimedia", ["multimedia", "creative"])
    if "system" in key:
        return ("System", ["system", "repair", "diagnostics"])
    return ("Hangar Bay", ["portable_tool", "hangar_bay"])

def make_adapter(folder: Path) -> dict:
    launchable = find_launchable(folder)
    category, capabilities = classify(folder.name)
    key = "hangar_" + slugify(folder.name)

    rel_path = str(folder).replace(str(FOXAI_ROOT), "%FOXAI_ROOT%")
    if str(folder).startswith(str(DRIVE_ROOT)):
        rel_path = str(folder).replace(str(DRIVE_ROOT), "%DRIVE_ROOT%")

    if launchable:
        path_value = str(launchable).replace(str(FOXAI_ROOT), "%FOXAI_ROOT%")
        if str(launchable).startswith(str(DRIVE_ROOT)):
            path_value = str(launchable).replace(str(DRIVE_ROOT), "%DRIVE_ROOT%")
    else:
        path_value = rel_path

    return {
        "key": key,
        "name": folder.name,
        "category": category,
        "reserved": False,
        "path": path_value,
        "cwd": rel_path,
        "capabilities": capabilities,
        "source": "Hanger Bay auto-discovery",
        "notes": "Auto-generated from Hanger Bay folder. Review path if launch fails.",
    }

def main() -> int:
    if not HANGAR_ROOT.exists():
        print(f"[ERROR] Hanger Bay folder not found: {HANGAR_ROOT}")
        print("Expected location: drive root \\Hanger Bay, for example Z:\\Hanger Bay")
        return 1

    CAP_ROOT.mkdir(parents=True, exist_ok=True)

    folders = [p for p in HANGAR_ROOT.iterdir() if p.is_dir()]
    if not folders:
        print("[WARN] No folders found inside Hanger Bay.")
        return 0

    created = 0
    for folder in sorted(folders, key=lambda p: p.name.lower()):
        adapter = make_adapter(folder)
        out_dir = CAP_ROOT / adapter["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "adapter.json"
        out_file.write_text(json.dumps(adapter, indent=2), encoding="utf-8")
        print(f"[OK] {adapter['name']} -> {out_file}")
        created += 1

    print()
    print(f"Created/updated {created} Hangar Bay capability adapters.")
    print()
    print("Next:")
    print("Run TEST_CAPABILITY_MANAGER.bat or TEST_CAPABILITY_BUS.bat again.")
    print("You should now see Hangar Bay tools listed as capabilities.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
