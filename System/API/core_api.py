from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json, datetime, urllib.parse, os, platform, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
PORT = 8844

def read_text(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return default

def simple_yaml_value(text, key, default=""):
    for line in text.splitlines():
        if line.strip().startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return default

def operator_name():
    return simple_yaml_value(read_text(ROOT / "System/Config/operator.yaml"), "display_name", "Operator") or "Operator"

def operator_quote():
    return simple_yaml_value(read_text(ROOT / "System/Config/operator.yaml"), "quote", "Wonder is a tool. Build with it.")

def project_info():
    text = read_text(ROOT / "manifest.yaml")
    return {
        "name": "KayocktheOS",
        "version": simple_yaml_value(text, "version", "0.4.0"),
        "codename": simple_yaml_value(text, "codename", "Living System Scanner"),
        "usb_mode": "usb_mode: true" in text,
        "build": simple_yaml_value(text, "build", "development"),
    }

def run_cmd(args, timeout=3):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)
        return (result.stdout or result.stderr or "").strip()
    except Exception:
        return ""

def command_version(command, args=None):
    exe = shutil.which(command)
    if not exe:
        return {"installed": False, "path": None, "version": None}
    out = run_cmd([exe] + (args or ["--version"]))
    first = out.splitlines()[0] if out else "installed"
    return {"installed": True, "path": exe, "version": first}

def count_files(folder, patterns):
    base = ROOT / folder
    if not base.exists():
        return 0
    total = 0
    for pattern in patterns:
        total += sum(1 for _ in base.rglob(pattern))
    return total

def disk_info():
    try:
        usage = shutil.disk_usage(ROOT.anchor or str(ROOT.drive) + "\\")
        return {
            "root": str(ROOT),
            "drive": ROOT.drive or ROOT.anchor,
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
        }
    except Exception as e:
        return {"error": str(e), "root": str(ROOT)}

def memory_info():
    if platform.system().lower() == "windows":
        out = run_cmd(["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"])
        for line in out.splitlines():
            if line.startswith("TotalPhysicalMemory="):
                try:
                    b = int(line.split("=",1)[1].strip())
                    return {"total_gb": round(b/(1024**3), 2)}
                except Exception:
                    pass
    return {"total_gb": None}

def cpu_info():
    name = platform.processor() or platform.machine()
    if platform.system().lower() == "windows":
        out = run_cmd(["wmic", "cpu", "get", "Name", "/value"])
        for line in out.splitlines():
            if line.startswith("Name="):
                name = line.split("=",1)[1].strip() or name
    return {"name": name, "machine": platform.machine(), "cores_logical": os.cpu_count()}

def gpu_info():
    if platform.system().lower() == "windows":
        out = run_cmd(["wmic", "path", "win32_VideoController", "get", "Name", "/value"])
        gpus = [line.split("=",1)[1].strip() for line in out.splitlines() if line.startswith("Name=") and line.split("=",1)[1].strip()]
        return {"gpus": gpus}
    return {"gpus": []}

def system_scan():
    return {
        "os": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "platform": platform.platform()},
        "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        "cpu": cpu_info(),
        "memory": memory_info(),
        "gpu": gpu_info(),
        "disk": disk_info(),
        "tools": {
            "git": command_version("git"),
            "node": command_version("node", ["--version"]),
            "npm": command_version("npm", ["--version"]),
            "python": {"installed": True, "path": sys.executable, "version": sys.version.split()[0]},
        },
        "assets": {
            "gguf_models": count_files("AI/Models", ["*.gguf"]),
            "safetensors_models": count_files("AI/Models", ["*.safetensors"]),
            "knowledge_files": count_files("Knowledge", ["*.pdf","*.txt","*.md","*.docx","*.html"]),
        }
    }

def browser_exe():
    search_dirs = [ROOT/"Shell/Kayock_Browser", ROOT/"Interface/Kayock_Browser"]
    patterns = ["Kayock-Browser*.exe", "KayockBrowser*.exe", "*Browser*.exe", "*.exe"]
    for folder in search_dirs:
        if not folder.exists():
            continue
        for pattern in patterns:
            matches = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if matches:
                return str(matches[0].relative_to(ROOT))
    return None

def modules():
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


def health():
    checks = [
        ("Manifest", "manifest.yaml"),
        ("Operator Profile", "System/Config/operator.yaml"),
        ("Module Registry", "System/Registry/modules"),
        ("Logs", "System/Logs"),
        ("Core API", "System/API/core_api.py"),
        ("Shell Source", "Shell/KayockBrowser"),
    ]
    results = []
    for label, rel in checks:
        exists = (ROOT / rel).exists()
        results.append({"label": label, "path": rel, "status": "OK" if exists else "MISSING"})
    exe = browser_exe()
    results.append({"label": "Kayock Browser EXE", "path": exe or "Shell/Kayock_Browser", "status": "OK" if exe else "MISSING"})
    return results

def recent_logs():
    text = read_text(ROOT / "System/Logs/boot.log")
    return [line for line in text.splitlines() if line.strip()][-8:]

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

def service_bus():
    try:
        bus = ROOT / "System" / "Services" / "service_bus.py"
        if bus.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_service_bus", bus)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.service_summary()
    except Exception as exc:
        return {"error": str(exc), "total_services": 0, "services": []}
    return {"total_services": 0, "services": []}

def service_events():
    try:
        bus = ROOT / "System" / "Services" / "service_bus.py"
        if bus.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_service_bus", bus)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return {"events": mod.recent_events()}
    except Exception as exc:
        return {"error": str(exc), "events": []}
    return {"events": []}

def bridge_payload():
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "project": project_info(),
        "operator": {"documentation_term": "Operator", "display_name": operator_name(), "quote": operator_quote()},
        "services": service_bus(),
        "academy": academy_status(),
        "release_check": release_check(),
        "events": service_events().get("events", [])[-10:],
        "health": health(),
        "modules": modules(),
    }

def release_check():
    try:
        checker = ROOT / "Foundry" / "release_check.py"
        if checker.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_release_check", checker)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_report()
    except Exception as exc:
        return {"error": str(exc), "ship_ready": False}
    return {"ship_ready": False, "error": "release checker missing"}

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

def ai_gateway_status():
    try:
        gateway = ROOT / "AI" / "ai_gateway.py"
        if gateway.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_ai_gateway", gateway)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.gateway_status()
    except Exception as exc:
        return {"error": str(exc), "status": "error"}
    return {"status": "missing"}

def ai_chat_placeholder(prompt="", context=None):
    try:
        gateway = ROOT / "AI" / "ai_gateway.py"
        if gateway.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_ai_gateway", gateway)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat_placeholder(prompt, context)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "AI Gateway missing."}

def local_runtime_health():
    try:
        runtime = ROOT / "AI" / "local_runtime.py"
        if runtime.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_runtime", runtime)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.runtime_health()
    except Exception as exc:
        return {"online": False, "error": str(exc)}
    return {"online": False, "message": "local runtime connector missing"}

def ai_chat(prompt="", context=None):
    try:
        runtime = ROOT / "AI" / "local_runtime.py"
        if runtime.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_runtime", runtime)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt, context)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return ai_chat_placeholder(prompt, context)

def local_chat_status():
    try:
        feature = ROOT / "AI" / "local_chat.py"
        if feature.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_local_chat", feature)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat_status()
    except Exception as exc:
        return {"error": str(exc), "configured": False}
    return {"configured": False, "message": "Local Chat feature missing"}

def runtime_launcher_status():
    try:
        feature = ROOT / "AI" / "runtime_launcher.py"
        if feature.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_runtime_launcher", feature)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"error": str(exc), "configured": False}
    return {"configured": False, "message": "Runtime launcher missing"}

def first_contact_status():
    try:
        fc = ROOT / "AI" / "first_contact.py"
        if fc.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_first_contact", fc)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ready_for_contact": False, "error": str(exc)}
    return {"ready_for_contact": False, "message": "First Contact missing"}

def first_contact_chat(prompt=""):
    try:
        fc = ROOT / "AI" / "first_contact.py"
        if fc.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kayock_first_contact", fc)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "First Contact missing"}

def kobold_adapter_status():
    try:
        adapter = ROOT / "AI" / "kobold_engine_adapter.py"
        if adapter.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kobold_adapter", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.write_config_and_launcher()
    except Exception as exc:
        return {"online": False, "error": str(exc)}
    return {"online": False, "message": "Kobold adapter missing"}

def kobold_adapter_chat(prompt=""):
    try:
        adapter = ROOT / "AI" / "kobold_engine_adapter.py"
        if adapter.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("kobold_adapter", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.chat(prompt)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "Kobold adapter missing"}

def model_profiles_status():
    try:
        profiles = ROOT / "AI" / "model_profiles.py"
        if profiles.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("model_profiles", profiles)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "Model profiles missing"}

def core_working_status():
    try:
        core = ROOT / "AI" / "core_working.py"
        if core.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("core_working", core)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "message": "Core Working missing"}

def status_payload():
    mods = modules()
    health_items = health()
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "project": project_info(),
        "operator": {"documentation_term": "Operator", "display_name": operator_name(), "quote": operator_quote()},
        "shell": {"browser_exe": browser_exe(), "dashboard": "Shell/Bridge_Dashboard/index.html", "status": "ready" if browser_exe() else "missing_browser"},
        "system": system_scan(),
        "ai_assets": ai_assets(),
        "foxai": foxai_status(),
        "ai_gateway": ai_gateway_status(),
        "local_runtime": local_runtime_health(),
        "local_chat": local_chat_status(),
        "first_contact": first_contact_status(),
        "kobold_adapter": kobold_adapter_status(),
        "model_profiles": model_profiles_status(),
        "core_working": core_working_status(),
        "runtime_launcher": runtime_launcher_status(),
        "health": health_items,
        "modules": mods,
        "summary": {
            "enabled_modules": sum(1 for m in mods if m.get("status") == "enabled"),
            "planned_modules": sum(1 for m in mods if m.get("status") == "planned"),
            "health_ok": sum(1 for h in health_items if h.get("status") == "OK"),
            "health_total": len(health_items)
        },
        "recent_logs": recent_logs(),
    }

class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, code=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            self._json(status_payload())
        elif path == "/api/system":
            self._json(system_scan())
        elif path == "/api/ai-assets":
            self._json(ai_assets())
        elif path == "/api/foxai":
            self._json(foxai_status())
        elif path == "/api/ai-gateway":
            self._json(ai_gateway_status())
        elif path == "/api/runtime":
            self._json(local_runtime_health())
        elif path == "/api/local-chat":
            self._json(local_chat_status())
        elif path == "/api/first-contact":
            self._json(first_contact_status())
        elif path == "/api/kobold":
            self._json(kobold_adapter_status())
        elif path == "/api/model-profiles":
            self._json(model_profiles_status())
        elif path == "/api/core-working":
            self._json(core_working_status())
        elif path == "/api/runtime-launcher":
            self._json(runtime_launcher_status())
        elif path == "/api/services":
            self._json(service_bus())
        elif path == "/api/events":
            self._json(service_events())
        elif path == "/api/bridge":
            self._json(bridge_payload())
        elif path == "/api/academy":
            self._json(academy_status())
        elif path == "/api/release-check":
            self._json(release_check())
        elif path == "/api/ping":
            self._json({"ok": True, "service": "KayocktheOS Core API"})
        else:
            self._json({"error": "not found", "available": ["/api/ping", "/api/status", "/api/system", "/api/ai-assets", "/api/services", "/api/events", "/api/bridge", "/api/academy", "/api/release-check"]}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"prompt": raw}
        if path == "/api/chat":
            self._json(kobold_adapter_chat(payload.get("prompt", "")))
        else:
            self._json({"error": "not found", "available": ["/api/chat"]}, 404)

    def log_message(self, format, *args):
        return

def run():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"KayocktheOS Core API running at http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
