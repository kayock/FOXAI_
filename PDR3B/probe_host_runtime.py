from __future__ import annotations

import importlib
import importlib.metadata
import json
import pathlib
import sys

NAMES = [
    "tkinter",
    "customtkinter",
    "PIL",
    "psutil",
    "requests",
    "casbin",
    "watchdog",
    "pluggy",
]

result = {
    "executable": sys.executable,
    "version": sys.version,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "packages": {},
    "tk": {},
    "runtime_components": [],
}

for name in NAMES:
    item = {
        "available": False,
        "module_file": None,
        "version": None,
        "requires": [],
        "error": None,
    }
    try:
        module = importlib.import_module(name)
        item["available"] = True
        item["module_file"] = getattr(module, "__file__", None)
        distribution = {
            "PIL": "Pillow",
            "casbin": "pycasbin",
        }.get(name, name)
        try:
            item["version"] = importlib.metadata.version(distribution)
            item["requires"] = (
                importlib.metadata.requires(distribution) or []
            )
        except Exception:
            item["version"] = getattr(module, "__version__", None)
    except Exception as exc:
        item["error"] = f"{type(exc).__name__}: {exc}"
    result["packages"][name] = item

try:
    import tkinter
    tcl = tkinter.Tcl()
    result["tk"] = {
        "available": True,
        "TkVersion": tkinter.TkVersion,
        "TclVersion": tkinter.TclVersion,
        "patchlevel": tcl.eval("info patchlevel"),
    }
except Exception as exc:
    result["tk"] = {
        "available": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

base = pathlib.Path(sys.base_prefix)
components = [
    base / "python.exe",
    base / "pythonw.exe",
    base / "python314.dll",
    base / "python314.zip",
    base / "DLLs" / "_tkinter.pyd",
    base / "Lib" / "tkinter" / "__init__.py",
    base / "tcl",
]
for path in components:
    result["runtime_components"].append({
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
    })

print(json.dumps(result))
