from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
from pathlib import Path
import site
import sys

def inside(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    python_root = root / "Runtime" / "Desktop" / "python"
    desktop_site = root / "Runtime" / "Desktop" / "site-packages"
    core_site = root / "Runtime" / "Core" / "site-packages"

    result = {
        "action": "foxai_portable_desktop_runtime_diagnostic",
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "root": str(root),
        "executable": str(Path(sys.executable).resolve()),
        "prefix": str(Path(sys.prefix).resolve()),
        "base_prefix": str(Path(sys.base_prefix).resolve()),
        "enable_user_site": bool(getattr(site, "ENABLE_USER_SITE", False)),
        "sys_path": list(sys.path),
        "checks": {},
        "modules": {},
        "foxai_launched": False,
        "comfyui_launched": False,
    }

    result["checks"]["executable_usb_owned"] = inside(sys.executable, python_root)
    result["checks"]["prefix_usb_owned"] = inside(sys.prefix, python_root)
    result["checks"]["base_prefix_usb_owned"] = inside(sys.base_prefix, python_root)
    result["checks"]["user_site_disabled"] = not bool(getattr(site, "ENABLE_USER_SITE", False))
    result["checks"]["host_user_site_absent"] = all(
        "AppData\\Roaming\\Python" not in str(p) for p in sys.path
    )

    expected_roots = {
        "tkinter": python_root,
        "customtkinter": desktop_site,
        "PIL": desktop_site,
        "casbin": core_site,
        "psutil": core_site,
        "requests": core_site,
    }

    for module_name, expected_root in expected_roots.items():
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

    try:
        import tkinter
        interp = tkinter.Tcl()
        result["modules"]["tkinter"]["tcl_patchlevel"] = interp.eval("info patchlevel")
    except Exception as exc:
        result["modules"]["tkinter"]["tcl_error"] = f"{type(exc).__name__}: {exc}"

    result["checks"]["required_modules_available"] = all(
        item.get("available") for item in result["modules"].values()
    )
    result["checks"]["module_origins_correct"] = all(
        item.get("origin_ok") for item in result["modules"].values()
    )
    result["verified"] = all(result["checks"].values())

    log_dir = root / "Logs" / "PortableRuntime"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"desktop_runtime_diagnostic_{stamp}.json"
    log_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print()
    print("Diagnostic receipt:", log_path)
    return 0 if result["verified"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
