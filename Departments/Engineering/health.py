from __future__ import annotations

from pathlib import Path
import importlib.util
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

    ok = all(item["ok"] for item in tools.values())

    return {
        "ok": ok,
        "department": "engineering",
        "name": "Engineering Department",
        "officer": "Chief Engineer Ada",
        "hanger_bay": str(hanger_bay),
        "tools": tools,
        "services": [
            "Repair Bay",
            "Diagnostics",
            "Build Verification",
            "Code Review",
            "Architecture Inspection",
            "Security Inspection",
        ],
        "status": "commissioned" if ok else "needs_attention",
    }
