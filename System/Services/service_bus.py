from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = ROOT / "System" / "Services"
EVENTS_DIR = ROOT / "System" / "Events"
SERVICE_REGISTRY = SERVICES_DIR / "services.json"
EVENT_LOG = EVENTS_DIR / "event_log.jsonl"

DEFAULT_SERVICES = [
    {
        "id": "system",
        "name": "System Service",
        "status": "enabled",
        "owner": "System",
        "description": "Machine, OS, CPU, RAM, GPU, disk, and tool awareness.",
        "capabilities": ["system_scan", "tool_detection", "hardware_summary"],
        "endpoints": ["/api/system"]
    },
    {
        "id": "models",
        "name": "Model Service",
        "status": "enabled",
        "owner": "AI",
        "description": "Local and referenced AI asset inventory.",
        "capabilities": ["model_inventory", "model_reference_scan"],
        "endpoints": ["/api/ai-assets"]
    },
    {
        "id": "modules",
        "name": "Module Service",
        "status": "enabled",
        "owner": "System",
        "description": "Dynamic department and module registry.",
        "capabilities": ["module_discovery", "module_status"],
        "endpoints": ["/api/status"]
    },
    {
        "id": "bridge",
        "name": "Bridge Service",
        "status": "enabled",
        "owner": "Shell",
        "description": "Operator-facing status and desktop data.",
        "capabilities": ["bridge_status", "dashboard_data"],
        "endpoints": ["/api/bridge"]
    },
    {
        "id": "academy",
        "name": "Academy Service",
        "status": "planned",
        "owner": "Academy",
        "description": "Professors, lessons, and learning workflows.",
        "capabilities": ["professors", "lessons"],
        "endpoints": []
    },
    {
        "id": "repair_bay",
        "name": "Repair Bay Service",
        "status": "planned",
        "owner": "RepairBay",
        "description": "Read-only diagnostics and future repair recommendations.",
        "capabilities": ["diagnostics", "reports"],
        "endpoints": []
    },
    {
        "id": "knowledge",
        "name": "Knowledge Service",
        "status": "planned",
        "owner": "Knowledge",
        "description": "Iron Library search, ingestion, and retrieval.",
        "capabilities": ["document_index", "search"],
        "endpoints": []
    },
    {
        "id": "creative_studio",
        "name": "Creative Studio Service",
        "status": "planned",
        "owner": "CreativeStudio",
        "description": "Image, video, audio, and comic workflows.",
        "capabilities": ["image_workflow", "media_tools"],
        "endpoints": []
    }
]

def ensure_dirs():
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

def load_services():
    ensure_dirs()
    if SERVICE_REGISTRY.exists():
        try:
            data = json.loads(SERVICE_REGISTRY.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    save_services(DEFAULT_SERVICES)
    return DEFAULT_SERVICES

def save_services(services):
    ensure_dirs()
    SERVICE_REGISTRY.write_text(json.dumps(services, indent=2), encoding="utf-8")

def service_summary():
    services = load_services()
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_services": len(services),
        "enabled": sum(1 for s in services if s.get("status") == "enabled"),
        "planned": sum(1 for s in services if s.get("status") == "planned"),
        "services": services
    }

def publish_event(event_type, source, message, payload=None):
    ensure_dirs()
    event = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "type": event_type,
        "source": source,
        "message": message,
        "payload": payload or {}
    }
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return event

def recent_events(limit=25):
    ensure_dirs()
    if not EVENT_LOG.exists():
        return []
    lines = [line.strip() for line in EVENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events

def initialize_bus():
    ensure_dirs()
    services = load_services()
    publish_event("service_bus_initialized", "service_bus", "KayocktheOS Service Bus initialized.", {"services": len(services)})
    return service_summary()

if __name__ == "__main__":
    summary = initialize_bus()
    print(json.dumps(summary, indent=2))
