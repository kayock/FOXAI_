from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import site
import sys

def inside(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
parser.add_argument("--python-root", required=True)
parser.add_argument("--desktop-site", required=True)
parser.add_argument("--core-site", required=True)
parser.add_argument("--closure", required=True)
args = parser.parse_args()

root = Path(args.root).resolve()
python_root = Path(args.python_root).resolve()
desktop_site = Path(args.desktop_site).resolve()
core_site = Path(args.core_site).resolve()
closure = json.loads(Path(args.closure).read_text(encoding="utf-8"))

result = {
    "executable": str(Path(sys.executable).resolve()),
    "prefix": str(Path(sys.prefix).resolve()),
    "base_prefix": str(Path(sys.base_prefix).resolve()),
    "enable_user_site": bool(getattr(site, "ENABLE_USER_SITE", False)),
    "user_site": site.getusersitepackages(),
    "sys_path": list(sys.path),
    "checks": {},
    "modules": {},
    "compile_errors": [],
}

result["checks"]["executable_inside_quarantine"] = inside(sys.executable, python_root)
result["checks"]["prefix_inside_quarantine"] = inside(sys.prefix, python_root)
result["checks"]["base_prefix_inside_quarantine"] = inside(sys.base_prefix, python_root)
result["checks"]["user_site_disabled"] = not bool(getattr(site, "ENABLE_USER_SITE", False))
result["checks"]["user_site_absent_from_sys_path"] = all(
    str(Path(p)).lower() != str(Path(site.getusersitepackages())).lower()
    for p in sys.path if p
)

try:
    import tkinter
    tcl = tkinter.Tcl()
    patchlevel = tcl.eval("info patchlevel")
    result["modules"]["tkinter"] = {
        "available": True,
        "origin": str(Path(tkinter.__file__).resolve()),
        "tcl_patchlevel": patchlevel,
        "origin_ok": inside(tkinter.__file__, python_root),
    }
except Exception as exc:
    result["modules"]["tkinter"] = {
        "available": False,
        "error": f"{type(exc).__name__}: {exc}",
        "origin_ok": False,
    }

for module_name, expected_root in (
    ("customtkinter", desktop_site),
    ("PIL", desktop_site),
    ("casbin", core_site),
    ("psutil", core_site),
    ("requests", core_site),
):
    try:
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
        result["modules"][module_name] = {
            "available": True,
            "origin": str(Path(origin).resolve()) if origin else None,
            "origin_ok": bool(origin and inside(origin, expected_root)),
        }
    except Exception as exc:
        result["modules"][module_name] = {
            "available": False,
            "origin": None,
            "origin_ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

for item in closure["local_files"]:
    path = root / Path(item["path"])
    try:
        source = path.read_text(encoding="utf-8-sig", errors="strict")
        compile(source, str(path), "exec", dont_inherit=True)
    except Exception as exc:
        result["compile_errors"].append({
            "path": item["path"],
            "error": f"{type(exc).__name__}: {exc}",
        })

result["checks"]["all_required_modules_available"] = all(
    item.get("available") for item in result["modules"].values()
)
result["checks"]["all_module_origins_correct"] = all(
    item.get("origin_ok") for item in result["modules"].values()
)
result["checks"]["dependency_closure_compiles"] = not result["compile_errors"]
result["verified"] = all(result["checks"].values())
print(json.dumps(result, ensure_ascii=False))
