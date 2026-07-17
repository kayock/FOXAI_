from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import site
import sys

MODULES = ["tkinter", "customtkinter", "PIL", "psutil", "requests", "casbin", "watchdog", "pluggy"]
DIST_HINTS = {
    "tkinter": None,
    "customtkinter": "customtkinter",
    "PIL": "Pillow",
    "psutil": "psutil",
    "requests": "requests",
    "casbin": "pycasbin",
    "watchdog": "watchdog",
    "pluggy": "pluggy",
}

def path_of(module):
    value = getattr(module, "__file__", None)
    if value:
        return str(Path(value).resolve())
    package_paths = getattr(module, "__path__", None)
    if package_paths:
        return [str(Path(p).resolve()) for p in package_paths]
    return None

def inspect_module(name):
    item = {
        "module": name,
        "available": False,
        "origin": None,
        "distribution": DIST_HINTS.get(name),
        "version": None,
        "requires_dist": [],
        "active_requirements": [],
        "error": None,
    }
    try:
        module = importlib.import_module(name)
        item["available"] = True
        item["origin"] = path_of(module)
    except Exception as exc:
        item["error"] = f"{type(exc).__name__}: {exc}"
        return item

    dist_name = DIST_HINTS.get(name)
    if not dist_name:
        return item

    try:
        dist = metadata.distribution(dist_name)
        item["distribution"] = dist.metadata.get("Name", dist_name)
        item["version"] = dist.version
        requirements = list(dist.requires or [])
        item["requires_dist"] = requirements

        try:
            from packaging.requirements import Requirement
            active = []
            environment = {
                "implementation_name": sys.implementation.name,
                "implementation_version": ".".join(map(str, sys.implementation.version[:3])),
                "os_name": os.name,
                "platform_machine": os.environ.get("PROCESSOR_ARCHITECTURE", ""),
                "platform_python_implementation": sys.implementation.name.capitalize(),
                "platform_release": "",
                "platform_system": "Windows" if os.name == "nt" else os.name,
                "platform_version": "",
                "python_full_version": ".".join(map(str, sys.version_info[:3])),
                "python_version": ".".join(map(str, sys.version_info[:2])),
                "sys_platform": sys.platform,
                "extra": "",
            }
            for raw in requirements:
                req = Requirement(raw)
                if req.marker is None or req.marker.evaluate(environment):
                    active.append({
                        "name": req.name,
                        "specifier": str(req.specifier),
                        "marker": str(req.marker) if req.marker else "",
                        "raw": raw,
                    })
            item["active_requirements"] = active
        except Exception:
            item["active_requirements"] = []
    except Exception as exc:
        item["metadata_error"] = f"{type(exc).__name__}: {exc}"

    return item

base = Path(sys.base_prefix)
checks = {
    "python_exe": Path(sys.executable).exists(),
    "python_dll": any(base.glob("python3*.dll")),
    "dlls_dir": (base / "DLLs").is_dir(),
    "tkinter_package": (base / "Lib" / "tkinter" / "__init__.py").is_file(),
    "tkinter_extension": (base / "DLLs" / "_tkinter.pyd").is_file(),
    "tcl_dir": (base / "tcl").is_dir(),
}
result = {
    "executable": str(Path(sys.executable).resolve()),
    "version": sys.version,
    "version_info": list(sys.version_info[:3]),
    "prefix": str(Path(sys.prefix).resolve()),
    "base_prefix": str(base.resolve()),
    "sys_path": list(sys.path),
    "enable_user_site": bool(getattr(site, "ENABLE_USER_SITE", False)),
    "user_site": site.getusersitepackages(),
    "modules": {name: inspect_module(name) for name in MODULES},
    "full_runtime_checks": checks,
}
print(json.dumps(result, ensure_ascii=False))
