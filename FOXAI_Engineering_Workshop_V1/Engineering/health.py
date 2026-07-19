from __future__ import annotations

from pathlib import Path
import importlib.util
import os
import shutil
import sys


def _ensure_hanger_bay(root: Path) -> Path:
    hb = root.parent / "Hanger Bay"
    if hb.exists() and str(hb) not in sys.path:
        sys.path.insert(0, str(hb))
    return hb


def health(root: str | Path = ".") -> dict:
    root = Path(root).resolve()
    hanger_bay = _ensure_hanger_bay(root)

    checks = {
        "ruff": "ruff",
        "black": "black",
        "mypy": "mypy",
        "pydeps": "pydeps",
        "import-linter": "importlinter",
        "grimp": "grimp",
        "pip-audit": "pip_audit",
        "cyclonedx-bom": "cyclonedx_py",
    }

    tools = {}
    for label, import_name in checks.items():
        found = importlib.util.find_spec(import_name) is not None
        tools[label] = {
            "ok": found,
            "import_name": import_name,
            "status": "ready" if found else "missing",
        }

    department_root = Path(__file__).resolve().parent
    foxai_root = department_root.parents[1] if len(department_root.parents) >= 2 else root
    workshop_data = foxai_root / "System" / "EngineeringWorkshop"
    workshop_data.mkdir(parents=True, exist_ok=True)

    workshop = {
        "module_ready": all(
            (department_root / name).exists()
            for name in (
                "workshop.py",
                "patch_engine.py",
                "snapshot.py",
                "validator.py",
                "mission_router.py",
                "mission_state.py",
            )
        ),
        "state_writable": os.access(workshop_data, os.W_OK),
        "python_available": bool(sys.executable and Path(sys.executable).exists()),
        "subprocess_available": shutil.which(Path(sys.executable).name) is not None
        or Path(sys.executable).exists(),
        "data_root": str(workshop_data),
    }
    workshop["implementation_available"] = all(
        workshop[key]
        for key in ("module_ready", "state_writable", "python_available", "subprocess_available")
    )

    optional_tools_ok = all(item["ok"] for item in tools.values())
    ok = bool(workshop["implementation_available"])

    return {
        "ok": ok,
        "department": "engineering",
        "name": "Engineering Department",
        "officer": "Chief Engineer Ada",
        "hanger_bay": str(hanger_bay),
        "tools": tools,
        "optional_tools_complete": optional_tools_ok,
        "workshop": workshop,
        "services": [
            "Engineering Workshop",
            "Repair Bay",
            "Diagnostics",
            "Build Verification",
            "Code Review",
            "Architecture Inspection",
            "Security Inspection",
        ],
        "status": "workshop_ready" if ok else "needs_attention",
    }
