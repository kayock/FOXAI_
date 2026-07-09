from pathlib import Path
import shutil
import datetime
import re
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"v0.7.0_before_service_bus_{STAMP}"

SERVICE_BUS_CODE = 'from pathlib import Path\nimport json\nimport datetime\n\nROOT = Path(__file__).resolve().parents[2]\nSERVICES_DIR = ROOT / "System" / "Services"\nEVENTS_DIR = ROOT / "System" / "Events"\nSERVICE_REGISTRY = SERVICES_DIR / "services.json"\nEVENT_LOG = EVENTS_DIR / "event_log.jsonl"\n\nDEFAULT_SERVICES = [\n    {\n        "id": "system",\n        "name": "System Service",\n        "status": "enabled",\n        "owner": "System",\n        "description": "Machine, OS, CPU, RAM, GPU, disk, and tool awareness.",\n        "capabilities": ["system_scan", "tool_detection", "hardware_summary"],\n        "endpoints": ["/api/system"]\n    },\n    {\n        "id": "models",\n        "name": "Model Service",\n        "status": "enabled",\n        "owner": "AI",\n        "description": "Local and referenced AI asset inventory.",\n        "capabilities": ["model_inventory", "model_reference_scan"],\n        "endpoints": ["/api/ai-assets"]\n    },\n    {\n        "id": "modules",\n        "name": "Module Service",\n        "status": "enabled",\n        "owner": "System",\n        "description": "Dynamic department and module registry.",\n        "capabilities": ["module_discovery", "module_status"],\n        "endpoints": ["/api/status"]\n    },\n    {\n        "id": "bridge",\n        "name": "Bridge Service",\n        "status": "enabled",\n        "owner": "Shell",\n        "description": "Operator-facing status and desktop data.",\n        "capabilities": ["bridge_status", "dashboard_data"],\n        "endpoints": ["/api/bridge"]\n    },\n    {\n        "id": "academy",\n        "name": "Academy Service",\n        "status": "planned",\n        "owner": "Academy",\n        "description": "Professors, lessons, and learning workflows.",\n        "capabilities": ["professors", "lessons"],\n        "endpoints": []\n    },\n    {\n        "id": "repair_bay",\n        "name": "Repair Bay Service",\n        "status": "planned",\n        "owner": "RepairBay",\n        "description": "Read-only diagnostics and future repair recommendations.",\n        "capabilities": ["diagnostics", "reports"],\n        "endpoints": []\n    },\n    {\n        "id": "knowledge",\n        "name": "Knowledge Service",\n        "status": "planned",\n        "owner": "Knowledge",\n        "description": "Iron Library search, ingestion, and retrieval.",\n        "capabilities": ["document_index", "search"],\n        "endpoints": []\n    },\n    {\n        "id": "creative_studio",\n        "name": "Creative Studio Service",\n        "status": "planned",\n        "owner": "CreativeStudio",\n        "description": "Image, video, audio, and comic workflows.",\n        "capabilities": ["image_workflow", "media_tools"],\n        "endpoints": []\n    }\n]\n\ndef ensure_dirs():\n    SERVICES_DIR.mkdir(parents=True, exist_ok=True)\n    EVENTS_DIR.mkdir(parents=True, exist_ok=True)\n\ndef load_services():\n    ensure_dirs()\n    if SERVICE_REGISTRY.exists():\n        try:\n            data = json.loads(SERVICE_REGISTRY.read_text(encoding="utf-8"))\n            if isinstance(data, list):\n                return data\n        except Exception:\n            pass\n    save_services(DEFAULT_SERVICES)\n    return DEFAULT_SERVICES\n\ndef save_services(services):\n    ensure_dirs()\n    SERVICE_REGISTRY.write_text(json.dumps(services, indent=2), encoding="utf-8")\n\ndef service_summary():\n    services = load_services()\n    return {\n        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),\n        "total_services": len(services),\n        "enabled": sum(1 for s in services if s.get("status") == "enabled"),\n        "planned": sum(1 for s in services if s.get("status") == "planned"),\n        "services": services\n    }\n\ndef publish_event(event_type, source, message, payload=None):\n    ensure_dirs()\n    event = {\n        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),\n        "type": event_type,\n        "source": source,\n        "message": message,\n        "payload": payload or {}\n    }\n    with EVENT_LOG.open("a", encoding="utf-8") as f:\n        f.write(json.dumps(event) + "\\n")\n    return event\n\ndef recent_events(limit=25):\n    ensure_dirs()\n    if not EVENT_LOG.exists():\n        return []\n    lines = [line.strip() for line in EVENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]\n    events = []\n    for line in lines[-limit:]:\n        try:\n            events.append(json.loads(line))\n        except Exception:\n            pass\n    return events\n\ndef initialize_bus():\n    ensure_dirs()\n    services = load_services()\n    publish_event("service_bus_initialized", "service_bus", "KayocktheOS Service Bus initialized.", {"services": len(services)})\n    return service_summary()\n\nif __name__ == "__main__":\n    summary = initialize_bus()\n    print(json.dumps(summary, indent=2))\n'

def info(msg):
    print(f"[KayocktheOS v0.7.0] {msg}")

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
    for item in ["manifest.yaml","System","AI","Forge","Foundry","Docs","00_START_HERE","Shell"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_service_bus():
    write_text("System/Services/service_bus.py", SERVICE_BUS_CODE)
    spec = importlib.util.spec_from_file_location("kayock_service_bus", ROOT / "System/Services/service_bus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.initialize_bus()
    info(f"Service Bus initialized with {summary['total_services']} service(s).")

def patch_core_api():
    path = ROOT / "System/API/core_api.py"
    if not path.exists():
        info("Core API not found; Service Bus installed but API patch skipped.")
        return
    old = path.read_text(encoding="utf-8", errors="replace")

    if "def service_bus(" not in old:
        insert = """
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
        "events": service_events().get("events", [])[-10:],
        "health": health(),
        "modules": modules(),
    }
"""
        old = old.replace("\ndef status_payload():", insert + "\ndef status_payload():")

    if '"services": service_bus(),' not in old:
        old = old.replace('"ai_assets": ai_assets(),', '"ai_assets": ai_assets(),\n        "services": service_bus(),\n        "events": service_events().get("events", []),')

    if 'elif path == "/api/services":' not in old:
        old = old.replace(
            'elif path == "/api/ping":\n            self._json({"ok": True, "service": "KayocktheOS Core API"})',
            'elif path == "/api/services":\n            self._json(service_bus())\n        elif path == "/api/events":\n            self._json(service_events())\n        elif path == "/api/bridge":\n            self._json(bridge_payload())\n        elif path == "/api/ping":\n            self._json({"ok": True, "service": "KayocktheOS Core API"})'
        )

    old = old.replace('["/api/ping", "/api/status", "/api/system", "/api/ai-assets"]', '["/api/ping", "/api/status", "/api/system", "/api/ai-assets", "/api/services", "/api/events", "/api/bridge"]')
    old = old.replace('["/api/ping", "/api/status", "/api/system"]', '["/api/ping", "/api/status", "/api/system", "/api/services", "/api/events", "/api/bridge"]')

    path.write_text(old, encoding="utf-8")
    info("Core API patched with Service Bus endpoints.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        text = re.sub(r"version: .*", "version: 0.7.0", text, count=1)
        text = re.sub(r"codename: .*", "codename: Service Bus", text, count=1)
        if "service_bus: enabled" not in text:
            text += "\n  service_bus: enabled\n" if "features:" in text else "\nfeatures:\n  service_bus: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/SERVICE_BUS.md", """# Service Bus

v0.7.0 introduces the first internal Service Bus.

## Purpose

The Service Bus lets KayocktheOS departments advertise services and capabilities without every department directly depending on every other department.

## Current services

- System Service
- Model Service
- Module Service
- Bridge Service
- Academy Service
- Repair Bay Service
- Knowledge Service
- Creative Studio Service

## API endpoints

```text
/api/services
/api/events
/api/bridge
```

## Rule

Departments should communicate through services, not through random direct file coupling.
""")
    write_text("Forge/Decisions/0007_service_bus.md", """# Decision 0007 - Service Bus

KayocktheOS will use an internal service bus for department communication.

The Core remains Python.
The Shell remains Electron/JavaScript.
Services advertise capabilities through JSON.
""")
    write_text("Foundry/Releases/v0.7.0_release_notes.md", "# v0.7.0 Release Notes - Service Bus\n\nAdds internal service registry, event log, and service API endpoints.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## v0.7.0 - Service Bus\n\n- Added `System/Services/service_bus.py`.\n- Added service registry and event log.\n- Added `/api/services`, `/api/events`, and `/api/bridge`.\n- Established services as the future communication boundary between departments.\n"
    if "v0.7.0 - Service Bus" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_service_bus()
    patch_core_api()
    update_manifest()
    create_docs()
    update_changelog()
    info("v0.7.0 Service Bus patch complete.")
    info("Restart KayocktheOS and test /api/services and /api/bridge.")

if __name__ == "__main__":
    main()
