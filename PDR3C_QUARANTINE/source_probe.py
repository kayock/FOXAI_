from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import site
import sys

REQUESTED = ["customtkinter", "Pillow"]

def pnorm(value):
    try:
        return str(Path(value).resolve())
    except Exception:
        return str(value)

def inside(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False

def marker_applies(raw):
    if ";" not in raw:
        return True
    marker = raw.split(";", 1)[1].strip().lower()
    if "extra ==" in marker or "extra!=" in marker or "extra !=" in marker:
        return False
    if "darwin" in marker and sys.platform != "darwin":
        return False
    if "linux" in marker and not sys.platform.startswith("linux"):
        return False
    if ("win32" in marker or "windows" in marker) and sys.platform != "win32":
        return False
    try:
        from packaging.requirements import Requirement
        return bool(Requirement(raw).marker.evaluate())
    except Exception:
        return True

def requirement_name(raw):
    try:
        from packaging.requirements import Requirement
        return Requirement(raw).name
    except Exception:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", raw)
        return match.group(1) if match else None

site_roots = []
for value in list(site.getsitepackages()) + [site.getusersitepackages()]:
    if value and Path(value).is_dir():
        normalized = pnorm(value)
        if normalized.lower() not in {x.lower() for x in site_roots}:
            site_roots.append(normalized)

def distribution_record(name):
    dist = metadata.distribution(name)
    files = []
    skipped_outside = []
    for item in list(dist.files or []):
        absolute = Path(dist.locate_file(item)).resolve()
        matched_root = None
        relative = None
        for root in site_roots:
            if inside(absolute, root):
                matched_root = root
                relative = str(absolute.relative_to(Path(root))).replace("/", "\\")
                break
        if matched_root is None:
            skipped_outside.append(str(absolute))
            continue
        if absolute.is_file():
            files.append({
                "source": str(absolute),
                "site_root": matched_root,
                "relative": relative,
                "size_bytes": absolute.stat().st_size,
            })
    return {
        "requested_name": name,
        "name": dist.metadata.get("Name", name),
        "version": dist.version,
        "requires": list(dist.requires or []),
        "files": files,
        "skipped_outside_site_roots": skipped_outside,
    }

records = {}
missing = []
queue = list(REQUESTED)
seen = set()

while queue:
    name = queue.pop(0)
    key = name.lower().replace("_", "-")
    if key in seen:
        continue
    seen.add(key)
    try:
        rec = distribution_record(name)
    except metadata.PackageNotFoundError:
        missing.append(name)
        continue
    records[rec["name"]] = rec
    for raw in rec["requires"]:
        if not marker_applies(raw):
            continue
        dep = requirement_name(raw)
        if dep:
            queue.append(dep)

imports = {}
for module_name in ("customtkinter", "PIL"):
    try:
        module = importlib.import_module(module_name)
        imports[module_name] = {
            "available": True,
            "origin": pnorm(getattr(module, "__file__", "")),
            "error": None,
        }
    except Exception as exc:
        imports[module_name] = {
            "available": False,
            "origin": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

base = Path(sys.base_prefix)
full_checks = {
    "python_exe": Path(sys.executable).is_file(),
    "python_dll": any(base.glob("python3*.dll")),
    "dlls_dir": (base / "DLLs").is_dir(),
    "tkinter_package": (base / "Lib" / "tkinter" / "__init__.py").is_file(),
    "tkinter_extension": (base / "DLLs" / "_tkinter.pyd").is_file(),
    "tcl_dir": (base / "tcl").is_dir(),
}

tkinter_check = {"available": False, "origin": None, "tcl_patchlevel": None, "error": None}
try:
    import tkinter
    interpreter = tkinter.Tcl()
    tkinter_check = {
        "available": True,
        "origin": pnorm(tkinter.__file__),
        "tcl_patchlevel": interpreter.eval("info patchlevel"),
        "error": None,
    }
except Exception as exc:
    tkinter_check["error"] = f"{type(exc).__name__}: {exc}"

result = {
    "executable": pnorm(sys.executable),
    "version": sys.version,
    "version_info": list(sys.version_info[:3]),
    "prefix": pnorm(sys.prefix),
    "base_prefix": pnorm(sys.base_prefix),
    "enable_user_site": bool(getattr(site, "ENABLE_USER_SITE", False)),
    "user_site": pnorm(site.getusersitepackages()),
    "site_roots": site_roots,
    "imports": imports,
    "distributions": records,
    "missing_distributions": missing,
    "full_runtime_checks": full_checks,
    "tkinter": tkinter_check,
}
print(json.dumps(result, ensure_ascii=False))
