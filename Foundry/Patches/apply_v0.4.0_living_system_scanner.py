from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.4.0_before_living_system_{STAMP}"

CORE_API = 'from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler\nfrom pathlib import Path\nimport json, datetime, urllib.parse, os, platform, shutil, subprocess, sys\n\nROOT = Path(__file__).resolve().parents[2]\nPORT = 8844\n\ndef read_text(path, default=""):\n    try:\n        return Path(path).read_text(encoding="utf-8")\n    except Exception:\n        return default\n\ndef simple_yaml_value(text, key, default=""):\n    for line in text.splitlines():\n        if line.strip().startswith(key + ":"):\n            return line.split(":", 1)[1].strip()\n    return default\n\ndef operator_name():\n    return simple_yaml_value(read_text(ROOT / "System/Config/operator.yaml"), "display_name", "Operator") or "Operator"\n\ndef operator_quote():\n    return simple_yaml_value(read_text(ROOT / "System/Config/operator.yaml"), "quote", "Wonder is a tool. Build with it.")\n\ndef project_info():\n    text = read_text(ROOT / "manifest.yaml")\n    return {\n        "name": "KayocktheOS",\n        "version": simple_yaml_value(text, "version", "0.4.0"),\n        "codename": simple_yaml_value(text, "codename", "Living System Scanner"),\n        "usb_mode": "usb_mode: true" in text,\n        "build": simple_yaml_value(text, "build", "development"),\n    }\n\ndef run_cmd(args, timeout=3):\n    try:\n        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)\n        return (result.stdout or result.stderr or "").strip()\n    except Exception:\n        return ""\n\ndef command_version(command, args=None):\n    exe = shutil.which(command)\n    if not exe:\n        return {"installed": False, "path": None, "version": None}\n    out = run_cmd([exe] + (args or ["--version"]))\n    first = out.splitlines()[0] if out else "installed"\n    return {"installed": True, "path": exe, "version": first}\n\ndef count_files(folder, patterns):\n    base = ROOT / folder\n    if not base.exists():\n        return 0\n    total = 0\n    for pattern in patterns:\n        total += sum(1 for _ in base.rglob(pattern))\n    return total\n\ndef disk_info():\n    try:\n        usage = shutil.disk_usage(ROOT.anchor or str(ROOT.drive) + "\\\\")\n        return {\n            "root": str(ROOT),\n            "drive": ROOT.drive or ROOT.anchor,\n            "total_gb": round(usage.total / (1024**3), 2),\n            "free_gb": round(usage.free / (1024**3), 2),\n            "used_gb": round(usage.used / (1024**3), 2),\n        }\n    except Exception as e:\n        return {"error": str(e), "root": str(ROOT)}\n\ndef memory_info():\n    if platform.system().lower() == "windows":\n        out = run_cmd(["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"])\n        for line in out.splitlines():\n            if line.startswith("TotalPhysicalMemory="):\n                try:\n                    b = int(line.split("=",1)[1].strip())\n                    return {"total_gb": round(b/(1024**3), 2)}\n                except Exception:\n                    pass\n    return {"total_gb": None}\n\ndef cpu_info():\n    name = platform.processor() or platform.machine()\n    if platform.system().lower() == "windows":\n        out = run_cmd(["wmic", "cpu", "get", "Name", "/value"])\n        for line in out.splitlines():\n            if line.startswith("Name="):\n                name = line.split("=",1)[1].strip() or name\n    return {"name": name, "machine": platform.machine(), "cores_logical": os.cpu_count()}\n\ndef gpu_info():\n    if platform.system().lower() == "windows":\n        out = run_cmd(["wmic", "path", "win32_VideoController", "get", "Name", "/value"])\n        gpus = [line.split("=",1)[1].strip() for line in out.splitlines() if line.startswith("Name=") and line.split("=",1)[1].strip()]\n        return {"gpus": gpus}\n    return {"gpus": []}\n\ndef system_scan():\n    return {\n        "os": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "platform": platform.platform()},\n        "python": {"executable": sys.executable, "version": sys.version.split()[0]},\n        "cpu": cpu_info(),\n        "memory": memory_info(),\n        "gpu": gpu_info(),\n        "disk": disk_info(),\n        "tools": {\n            "git": command_version("git"),\n            "node": command_version("node", ["--version"]),\n            "npm": command_version("npm", ["--version"]),\n            "python": {"installed": True, "path": sys.executable, "version": sys.version.split()[0]},\n        },\n        "assets": {\n            "gguf_models": count_files("AI/Models", ["*.gguf"]),\n            "safetensors_models": count_files("AI/Models", ["*.safetensors"]),\n            "knowledge_files": count_files("Knowledge", ["*.pdf","*.txt","*.md","*.docx","*.html"]),\n        }\n    }\n\ndef browser_exe():\n    search_dirs = [ROOT/"Shell/Kayock_Browser", ROOT/"Interface/Kayock_Browser"]\n    patterns = ["Kayock-Browser*.exe", "KayockBrowser*.exe", "*Browser*.exe", "*.exe"]\n    for folder in search_dirs:\n        if not folder.exists():\n            continue\n        for pattern in patterns:\n            matches = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)\n            if matches:\n                return str(matches[0].relative_to(ROOT))\n    return None\n\ndef modules():\n    out = []\n    reg = ROOT / "System/Registry/modules"\n    for file in sorted(reg.glob("*.module.yaml")):\n        text = read_text(file)\n        item = {}\n        for key in ["id", "name", "status", "owner", "path", "description"]:\n            item[key] = simple_yaml_value(text, key, "")\n        out.append(item)\n    return out\n\ndef health():\n    checks = [\n        ("Manifest", "manifest.yaml"),\n        ("Operator Profile", "System/Config/operator.yaml"),\n        ("Module Registry", "System/Registry/modules"),\n        ("Logs", "System/Logs"),\n        ("Core API", "System/API/core_api.py"),\n        ("Shell Source", "Shell/KayockBrowser"),\n    ]\n    results = []\n    for label, rel in checks:\n        exists = (ROOT / rel).exists()\n        results.append({"label": label, "path": rel, "status": "OK" if exists else "MISSING"})\n    exe = browser_exe()\n    results.append({"label": "Kayock Browser EXE", "path": exe or "Shell/Kayock_Browser", "status": "OK" if exe else "MISSING"})\n    return results\n\ndef recent_logs():\n    text = read_text(ROOT / "System/Logs/boot.log")\n    return [line for line in text.splitlines() if line.strip()][-8:]\n\ndef status_payload():\n    mods = modules()\n    health_items = health()\n    return {\n        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),\n        "project": project_info(),\n        "operator": {"documentation_term": "Operator", "display_name": operator_name(), "quote": operator_quote()},\n        "shell": {"browser_exe": browser_exe(), "dashboard": "Shell/Bridge_Dashboard/index.html", "status": "ready" if browser_exe() else "missing_browser"},\n        "system": system_scan(),\n        "health": health_items,\n        "modules": mods,\n        "summary": {\n            "enabled_modules": sum(1 for m in mods if m.get("status") == "enabled"),\n            "planned_modules": sum(1 for m in mods if m.get("status") == "planned"),\n            "health_ok": sum(1 for h in health_items if h.get("status") == "OK"),\n            "health_total": len(health_items)\n        },\n        "recent_logs": recent_logs(),\n    }\n\nclass Handler(BaseHTTPRequestHandler):\n    def _json(self, payload, code=200):\n        body = json.dumps(payload, indent=2).encode("utf-8")\n        self.send_response(code)\n        self.send_header("Content-Type", "application/json; charset=utf-8")\n        self.send_header("Access-Control-Allow-Origin", "*")\n        self.send_header("Cache-Control", "no-store")\n        self.end_headers()\n        self.wfile.write(body)\n\n    def do_GET(self):\n        path = urllib.parse.urlparse(self.path).path\n        if path == "/api/status":\n            self._json(status_payload())\n        elif path == "/api/system":\n            self._json(system_scan())\n        elif path == "/api/ping":\n            self._json({"ok": True, "service": "KayocktheOS Core API"})\n        else:\n            self._json({"error": "not found", "available": ["/api/ping", "/api/status", "/api/system"]}, 404)\n\n    def log_message(self, format, *args):\n        return\n\ndef run():\n    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)\n    print(f"KayocktheOS Core API running at http://127.0.0.1:{PORT}")\n    server.serve_forever()\n\nif __name__ == "__main__":\n    run()\n'

def info(msg):
    print(f"[KayocktheOS v0.4.0] {msg}")

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
    for item in ["manifest.yaml","Start_KayocktheOS.bat","System","Shell","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, BACKUP_DIR / "core_api.py.bak")
    path.write_text(CORE_API, encoding="utf-8")
    info("Updated System/API/core_api.py with Living System Scanner.")

def patch_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        import re
        text = re.sub(r"version: .*", "version: 0.4.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Living System Scanner", text, count=1)
        if "living_system_scanner: enabled" not in text:
            text += "\n  living_system_scanner: enabled\n" if "features:" in text else "\nfeatures:\n  living_system_scanner: enabled\n"
        path.write_text(text, encoding="utf-8")
    else:
        write_text("manifest.yaml", "project:\n  name: KayocktheOS\n  version: 0.4.0\n  codename: Living System Scanner\nfeatures:\n  living_system_scanner: enabled\n")

def create_docs():
    write_text("Docs/LIVING_SYSTEM_SCANNER.md", """# Living System Scanner

v0.4.0 adds a read-only machine awareness layer.

## API endpoints

```text
http://127.0.0.1:8844/api/system
http://127.0.0.1:8844/api/status
```

## Scanner collects

- Operating system
- Python version
- CPU name and logical cores
- RAM estimate
- GPU names where available
- Disk usage for the KayocktheOS drive
- Git, Node, and npm detection
- Counts for local model and Knowledge files

## Safety

This scanner is read-only.
It does not modify the host machine.
""")
    write_text("Forge/Decisions/0004_living_system_scanner.md", """# Decision 0004 - Living System Scanner

KayocktheOS should understand the machine it is running on.

v0.4.0 scanner is read-only.
""")
    write_text("Foundry/Releases/v0.4.0_release_notes.md", """# v0.4.0 Release Notes - Living System Scanner

Adds read-only system scanning to the Core API.

New endpoint:

```text
/api/system
```

The existing `/api/status` endpoint now includes a `system` section.
""")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.4.0 - Living System Scanner\n\n- Added read-only machine scanner.\n- Added `/api/system` endpoint.\n- Added CPU, RAM, GPU, disk, OS, Python, Git, Node, npm detection.\n- Added model and Knowledge file counts.\n"
    if "v0.4.0 - Living System Scanner" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    patch_core_api()
    patch_manifest()
    create_docs()
    update_changelog()
    info("v0.4.0 Living System Scanner patch complete.")
    info("Restart Start_KayocktheOS.bat, then open http://127.0.0.1:8844/api/system")

if __name__ == "__main__":
    main()
