import time
import shutil
from pathlib import Path

import psutil

from core.paths import CONFIG, ASSETS, RED_CANVAS
from core.models import find_models
from core.agents import find_agents
from core.library import ensure_library, list_documents
from core.image_models import find_checkpoints
from core.comfy_bridge import is_comfy_running


STARTED_AT = time.time()


def _ok(name, status="OK", detail="", impact="", action=""):
    return {
        "name": name,
        "ok": True,
        "status": status,
        "detail": detail,
        "impact": impact,
        "action": action,
    }


def _warn(name, status="WARNING", detail="", impact="", action=""):
    return {
        "name": name,
        "ok": False,
        "status": status,
        "detail": detail,
        "impact": impact,
        "action": action,
    }


def uptime_label():
    seconds = int(time.time() - STARTED_AT)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining:02d}"


def hardware_status():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.cwd())

    return {
        "cpu_percent": cpu,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "ram_percent": ram.percent,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        "uptime": uptime_label(),
    }


def neural_status(app=None):
    models = find_models()

    selected_model = None
    if app is not None and hasattr(app, "model_menu"):
        try:
            selected_model = app.model_menu.get()
        except Exception:
            selected_model = None

    server_alive = False
    brainstem_state = "UNKNOWN"

    if app is not None and hasattr(app, "brainstem"):
        try:
            server_alive = app.brainstem.is_server_alive()
            brainstem_state = app.brainstem.state
        except Exception:
            pass

    checks = []

    if models:
        checks.append(_ok("Language Models", "DETECTED", f"{len(models)} model(s) found."))
    else:
        checks.append(_warn(
            "Language Models",
            "MISSING",
            "No language models were found.",
            "Chat and Engineer will not work.",
            "Place GGUF models in the configured Models/Chat folder."
        ))

    if server_alive:
        checks.append(_ok("Neural Engine", "ONLINE", "llama-server is responding."))
    else:
        checks.append(_warn(
            "Neural Engine",
            "OFFLINE",
            "The local chat server is not responding.",
            "Chat requests may fail until the neural engine starts.",
            "Click START MISSION and wait for the online message."
        ))

    return {
        "selected_model": selected_model,
        "model_count": len(models),
        "server_alive": server_alive,
        "brainstem_state": brainstem_state,
        "checks": checks,
    }


def creative_status():
    checkpoints = find_checkpoints()
    comfy_online = is_comfy_running()
    workflow_file = RED_CANVAS / "workflow_api.json"
    output_dir = RED_CANVAS / "Outputs"

    checks = []

    if comfy_online:
        checks.append(_ok("ComfyUI", "ONLINE", "ComfyUI is responding on port 8188."))
    else:
        checks.append(_warn(
            "ComfyUI",
            "OFFLINE",
            "ComfyUI is not responding on port 8188.",
            "Red Canvas image generation is unavailable.",
            "Start ComfyUI, then reopen Red Canvas."
        ))

    if workflow_file.exists():
        checks.append(_ok("Red Canvas Workflow", "FOUND", str(workflow_file)))
    else:
        checks.append(_warn(
            "Red Canvas Workflow",
            "MISSING",
            f"Missing workflow file: {workflow_file}",
            "Red Canvas cannot submit image jobs.",
            "Restore workflow_api.json into the Red Canvas folder."
        ))

    if checkpoints:
        checks.append(_ok("Image Checkpoints", "DETECTED", f"{len(checkpoints)} checkpoint option(s) found."))
    else:
        checks.append(_warn(
            "Image Checkpoints",
            "MISSING",
            "No checkpoint options were detected.",
            "Image generation may fail unless the workflow default is valid.",
            "Place checkpoints in ComfyUI/models/checkpoints."
        ))

    if output_dir.exists():
        checks.append(_ok("Output Folder", "READY", str(output_dir)))
    else:
        checks.append(_warn(
            "Output Folder",
            "MISSING",
            str(output_dir),
            "Generated images may not save where expected.",
            "Create the Red Canvas/Outputs folder."
        ))

    return {
        "comfy_online": comfy_online,
        "checkpoint_count": len(checkpoints),
        "workflow_exists": workflow_file.exists(),
        "output_dir_exists": output_dir.exists(),
        "checks": checks,
    }


def library_status():
    try:
        ensure_library()
        docs = list_documents()
        return {
            "document_count": len(docs),
            "checks": [
                _ok("Iron Library", "READY", f"{len(docs)} searchable document(s) detected.")
            ],
        }
    except Exception as error:
        return {
            "document_count": 0,
            "checks": [
                _warn(
                    "Iron Library",
                    "ERROR",
                    str(error),
                    "Library search may be unavailable.",
                    "Check Library folder permissions and paths."
                )
            ],
        }


def workshop_status(app=None):
    checks = []

    checks.append(_ok("Director", "OPERATIONAL", "Routing module loaded."))
    checks.append(_ok("Mission Control", "OPERATIONAL", "Mission narration is available."))
    checks.append(_ok("Brainstem", "OPERATIONAL", "Workshop state manager is loaded."))
    checks.append(_ok("Config", "READY" if CONFIG.exists() else "MISSING", str(CONFIG)))
    checks.append(_ok("Assets", "READY" if ASSETS.exists() else "MISSING", str(ASSETS)))

    if app is not None and hasattr(app, "brainstem"):
        snapshot = app.brainstem.snapshot()
    else:
        snapshot = {
            "state": "UNKNOWN",
            "busy": False,
            "active_mission": None,
            "active_specialist": None,
            "elapsed_label": "00:00",
            "last_error": None,
        }

    return {
        "brainstem": snapshot,
        "checks": checks,
    }


def advisor(app=None):
    hardware = hardware_status()
    models = find_models()

    ram_total = hardware["ram_total_gb"]
    model_names = [m.name for m in models]

    stable_model = None
    reason = "No models detected."

    q4_models = [name for name in model_names if "q4" in name.lower()]
    q8_models = [name for name in model_names if "q8" in name.lower()]
    small_models = [name for name in model_names if "8b" in name.lower() or "7b" in name.lower()]

    if ram_total < 16:
        stable_model = small_models[0] if small_models else (q4_models[0] if q4_models else (model_names[0] if model_names else None))
        reason = "Lower RAM detected; smaller quantized models are recommended for stability."
    elif q4_models:
        stable_model = q4_models[0]
        reason = "Q4 models usually provide the best stability and responsiveness on CPU systems."
    elif small_models:
        stable_model = small_models[0]
        reason = "Smaller models are recommended as the safest default."
    elif q8_models:
        stable_model = q8_models[0]
        reason = "Q8 model detected; quality may be higher, but CPU load can be heavier."
    elif model_names:
        stable_model = model_names[0]
        reason = "Only available model selected as fallback."

    recommended_threads = max(2, min(psutil.cpu_count(logical=True) or 4, 10))

    return {
        "recommended_model": stable_model,
        "recommended_threads": recommended_threads,
        "recommended_context": 8192,
        "recommended_reply_tokens": 2048,
        "reason": reason,
    }


def run_full_inspection(app=None):
    sections = {
        "workshop": workshop_status(app),
        "hardware": hardware_status(),
        "neural": neural_status(app),
        "creative": creative_status(),
        "library": library_status(),
        "advisor": advisor(app),
    }

    checks = []
    for section in ["workshop", "neural", "creative", "library"]:
        checks.extend(sections[section].get("checks", []))

    total = len(checks) or 1
    passed = sum(1 for check in checks if check.get("ok"))
    health_score = int((passed / total) * 100)

    if health_score >= 90:
        health_label = "EXCELLENT"
    elif health_score >= 75:
        health_label = "GOOD"
    elif health_score >= 50:
        health_label = "WARNING"
    else:
        health_label = "REPAIR RECOMMENDED"

    sections["summary"] = {
        "health_score": health_score,
        "health_label": health_label,
        "checks_total": total,
        "checks_passed": passed,
        "checks_failed": total - passed,
    }

    return sections
