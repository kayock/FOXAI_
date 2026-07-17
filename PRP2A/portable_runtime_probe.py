from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROBE_DIR = Path(__file__).resolve().parent
ROOT = PROBE_DIR.parent
REPORT_ROOT = ROOT / "Reports" / "PortableRuntimeProbe"

PACKAGE_MODULES = {
    "psutil": "psutil",
    "requests": "requests",
    "Pillow": "PIL",
    "customtkinter": "customtkinter",
    "pycasbin/casbin": "casbin",
    "torch": "torch",
    "watchdog": "watchdog",
    "pluggy": "pluggy",
    "numpy": "numpy",
    "tkinter": "tkinter",
}

SELECTED_SOURCE_FILES = [
    "core/foxai_web.py",
    "core/server.py",
    "core/security_containment.py",
    "core/engineer_agent.py",
    "ui/main_window.py",
    "foxai.py",
    "FoxAI_Desktop.py",
    "ComfyUI/main.py",
]

SELECTED_LAUNCHERS = [
    "START_FOXAI_WEB_PORTABLE.bat",
    "START_FOXAI_WEB.bat",
    "Start FoxAI.bat",
    "START_FOXAI_CLEAN.bat",
    "Start ComfyUI CPU.bat",
    "Start_KayocktheOS.bat",
    "Launch_KayocktheOS_Workshop.bat",
    "Start_Bridge.bat",
]

RUNTIME_CANDIDATES = {
    "embedded_python": "env/python/python.exe",
    "root_venv": ".venv/Scripts/python.exe",
    "comfyui_embedded": "ComfyUI/python_embeded/python.exe",
    "comfyui_embedded_alt": "ComfyUI/python_embedded/python.exe",
    "comfyui_venv": "ComfyUI/.venv/Scripts/python.exe",
}

STDLIB = set(getattr(sys, "stdlib_module_names", set())) | {
    "__future__", "typing", "pathlib", "datetime", "dataclasses",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inside_root(path_text: str | None) -> bool:
    if not path_text:
        return False
    try:
        candidate = Path(path_text).resolve()
        candidate.relative_to(ROOT.resolve())
        return True
    except Exception:
        return False


def run_json_probe(python: Path, isolated: bool) -> dict[str, Any]:
    code = r"""
import importlib.metadata as md
import importlib.util
import json
import site
import sys

modules = {
    "psutil": "psutil",
    "requests": "requests",
    "Pillow": "PIL",
    "customtkinter": "customtkinter",
    "pycasbin/casbin": "casbin",
    "torch": "torch",
    "watchdog": "watchdog",
    "pluggy": "pluggy",
    "numpy": "numpy",
    "tkinter": "tkinter",
}

distribution_candidates = {
    "psutil": ["psutil"],
    "requests": ["requests"],
    "Pillow": ["Pillow"],
    "customtkinter": ["customtkinter"],
    "pycasbin/casbin": ["pycasbin", "casbin"],
    "torch": ["torch"],
    "watchdog": ["watchdog"],
    "pluggy": ["pluggy"],
    "numpy": ["numpy"],
    "tkinter": [],
}

result = {
    "executable": sys.executable,
    "version": sys.version,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "sys_path": list(sys.path),
    "enable_user_site": bool(getattr(site, "ENABLE_USER_SITE", False)),
    "user_site": site.getusersitepackages(),
    "modules": {},
    "pip": {},
    "ensurepip": {},
}

for label, module_name in modules.items():
    try:
        spec = importlib.util.find_spec(module_name)
        origin = None if spec is None else spec.origin
        locations = [] if spec is None or spec.submodule_search_locations is None else list(spec.submodule_search_locations)
        available = spec is not None
        error = None
    except Exception as exc:
        origin = None
        locations = []
        available = False
        error = f"{type(exc).__name__}: {exc}"
    version = None
    distribution = None
    for candidate in distribution_candidates[label]:
        try:
            version = md.version(candidate)
            distribution = candidate
            break
        except Exception:
            pass
    result["modules"][label] = {
        "module": module_name,
        "available": available,
        "origin": origin,
        "locations": locations,
        "distribution": distribution,
        "version": version,
        "error": error,
    }

for module_name, key in [("pip", "pip"), ("ensurepip", "ensurepip")]:
    try:
        spec = importlib.util.find_spec(module_name)
        result[key] = {
            "available": spec is not None,
            "origin": None if spec is None else spec.origin,
        }
    except Exception as exc:
        result[key] = {"available": False, "origin": None, "error": str(exc)}

print(json.dumps(result))
"""
    args = [str(python)]
    if isolated:
        args.append("-s")
    args += ["-c", code]
    try:
        process = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=90,
        )
    except Exception as exc:
        return {
            "exists": python.exists(),
            "runs": False,
            "isolated": isolated,
            "error": f"{type(exc).__name__}: {exc}",
        }

    result: dict[str, Any] = {
        "exists": python.exists(),
        "runs": process.returncode == 0,
        "isolated": isolated,
        "returncode": process.returncode,
        "stderr": process.stderr[-4000:],
    }
    if process.returncode == 0:
        try:
            payload = json.loads(process.stdout)
            result.update(payload)
        except Exception as exc:
            result["runs"] = False
            result["error"] = f"JSON parse failed: {exc}"
            result["stdout_tail"] = process.stdout[-4000:]
    else:
        result["stdout_tail"] = process.stdout[-4000:]
    return result


def annotate_origins(runtime: dict[str, Any]) -> None:
    for module in runtime.get("modules", {}).values():
        origin = module.get("origin")
        locations = module.get("locations") or []
        paths = [origin] if origin else []
        paths.extend(locations)
        module["usb_owned"] = any(inside_root(p) for p in paths if p)
        module["host_borrowed"] = bool(module.get("available")) and not module["usb_owned"]


def source_imports(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    result: dict[str, Any] = {
        "exists": True,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"
        return result

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    result["imports"] = sorted(imports)
    result["non_stdlib_candidates"] = sorted(
        module for module in imports
        if module not in STDLIB
        and module not in {"core", "ui", "security_containment"}
    )
    return result


def requirement_files() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    patterns = [
        "requirements*.txt",
        "ComfyUI/requirements*.txt",
        "ComfyUI/**/requirements*.txt",
    ]
    seen: set[Path] = set()
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                content = f"<read failed: {exc}>"
            results.append({
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
                "content": content,
            })
    return sorted(results, key=lambda item: item["path"].lower())


def launcher_inventory() -> list[dict[str, Any]]:
    results = []
    for relative in SELECTED_LAUNCHERS:
        path = ROOT / relative
        if not path.is_file():
            results.append({"path": relative, "exists": False})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        results.append({
            "path": relative,
            "exists": True,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "content": text,
            "signals": {
                "uses_embedded_python": "env\\python\\python.exe" in lower or "env/python/python.exe" in lower,
                "uses_root_venv": ".venv" in lower,
                "uses_system_python": bool(re.search(r"(^|[ \"])(python|py)([ \".-]|$)", lower, re.MULTILINE)),
                "runs_pip_install": "pip install" in lower or "npm install" in lower,
                "starts_service": "start " in lower or "subprocess" in lower,
            },
        })
    return results


def fleet_paths() -> dict[str, Any]:
    path = ROOT / "Config/fleet_registry.json"
    if not path.is_file():
        legacy = ROOT / "fleet_registry.json"
        path = legacy if legacy.is_file() else path
    if not path.is_file():
        return {"exists": False}
    result: dict[str, Any] = {
        "exists": True,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "entries": [],
    }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    shuttles = payload.get("shuttles", {}) if isinstance(payload, dict) else {}
    for key, item in shuttles.items():
        if not isinstance(item, dict):
            continue
        for field in ("path", "manifest_path"):
            value = item.get(field)
            if not isinstance(value, str):
                continue
            drive_bound = bool(re.match(r"^[A-Za-z]:\\", value))
            root_bound = value.lower().startswith(str(ROOT).lower())
            same_drive = value[:2].lower() == str(ROOT)[:2].lower() if drive_bound else False
            result["entries"].append({
                "key": key,
                "field": field,
                "value": value,
                "drive_bound": drive_bound,
                "root_bound": root_bound,
                "same_drive_as_root": same_drive,
                "category": (
                    "internal_uri" if "://" in value
                    else "foxai_root_path" if root_bound
                    else "same_drive_external_path" if drive_bound and same_drive
                    else "foreign_drive_path" if drive_bound
                    else "relative_or_other"
                ),
            })
    return result


def detect_system_pythons() -> list[str]:
    candidates: list[str] = []
    commands = [
        ["where", "python"],
        ["where", "py"],
    ]
    for command in commands:
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            continue
        if process.returncode == 0:
            for line in process.stdout.splitlines():
                line = line.strip()
                if line and line not in candidates:
                    candidates.append(line)
    return candidates


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    required_labels = [
        "psutil",
        "requests",
        "Pillow",
        "customtkinter",
        "pycasbin/casbin",
    ]
    embedded_isolated = payload["runtimes"].get("embedded_python", {}).get("isolated", {})
    missing_isolated = []
    borrowed_normal = []
    normal = payload["runtimes"].get("embedded_python", {}).get("normal", {})
    for label in required_labels:
        iso_module = embedded_isolated.get("modules", {}).get(label, {})
        if not iso_module.get("available") or not iso_module.get("usb_owned"):
            missing_isolated.append(label)
        normal_module = normal.get("modules", {}).get(label, {})
        if normal_module.get("host_borrowed"):
            borrowed_normal.append(label)

    torch_iso = embedded_isolated.get("modules", {}).get("torch", {})
    launchers = {item["path"]: item for item in payload["launchers"]}
    desktop_launcher = launchers.get("Start FoxAI.bat", {})
    registry = payload["fleet_registry"]
    drive_bound_count = sum(
        1 for item in registry.get("entries", [])
        if item.get("drive_bound")
    )

    must_fix = []
    if borrowed_normal:
        must_fix.append(
            "Bundled Python borrows packages from the Windows user-site folder: "
            + ", ".join(borrowed_normal)
        )
    if missing_isolated:
        must_fix.append(
            "USB-only (-s) embedded Python lacks required packages: "
            + ", ".join(missing_isolated)
        )
    if desktop_launcher.get("signals", {}).get("uses_system_python"):
        must_fix.append(
            "Desktop launcher selects system Python instead of an explicitly USB-owned runtime."
        )
    root_venv = payload["runtimes"].get("root_venv", {})
    if root_venv.get("normal", {}).get("base_prefix"):
        base = root_venv["normal"].get("base_prefix")
        if base and not inside_root(base):
            must_fix.append(
                "Root .venv base interpreter points outside the USB: " + base
            )
    if drive_bound_count:
        must_fix.append(
            f"Fleet registry contains {drive_bound_count} drive-bound path fields."
        )

    separate = []
    if not torch_iso.get("available") or not torch_iso.get("usb_owned"):
        separate.append(
            "ComfyUI/PyTorch needs a separately verified USB-owned runtime strategy; "
            "do not fold a large Torch install into the small core runtime blindly."
        )

    safe_notes = [
        "Alternate KayocktheOS Shell remains separate and non-default.",
        "Bridge/npm launchers remain separate because they may install dependencies.",
        "Historic root launchers are not deleted or reorganized in this phase.",
    ]

    return {
        "must_fix_before_other_pc": must_fix,
        "separate_runtime_decisions": separate,
        "safe_to_leave_as_notes": safe_notes,
        "candidate_core_packages": required_labels + ["watchdog", "pluggy"],
        "candidate_creative_packages": ["torch", "numpy"],
        "recommended_architecture": {
            "core_runtime": "USB-owned embedded Python package directory; launch with user-site disabled.",
            "desktop": "Use the same USB-owned core runtime where tkinter is available.",
            "creative_runtime": "Keep ComfyUI/Torch isolated from the small core runtime and verify separately.",
            "registry": "Resolve FOXAI and same-drive Hanger Bay paths from the detected USB root instead of Z:.",
        },
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# FOXAI Portable Runtime Phase 2A — Read-Only Probe",
        "",
        f"- Created: `{payload['created']}`",
        f"- Root: `{payload['root']}`",
        "- State: **read_only_probe_complete**",
        "- Automatic install: **False**",
        "- Automatic repair: **False**",
        "- Automatic launch: **False**",
        "",
        "## Must fix before another-computer testing",
        "",
    ]
    for item in summary["must_fix_before_other_pc"]:
        lines.append(f"- {item}")
    if not summary["must_fix_before_other_pc"]:
        lines.append("- No blocking core-runtime issue detected.")

    lines += ["", "## Separate runtime decisions", ""]
    for item in summary["separate_runtime_decisions"]:
        lines.append(f"- {item}")
    if not summary["separate_runtime_decisions"]:
        lines.append("- No separate runtime decision detected.")

    lines += ["", "## Candidate core packages", ""]
    for item in summary["candidate_core_packages"]:
        lines.append(f"- `{item}`")

    lines += ["", "## Candidate creative packages", ""]
    for item in summary["candidate_creative_packages"]:
        lines.append(f"- `{item}`")

    lines += [
        "",
        "## Proposed architecture",
        "",
    ]
    for key, value in summary["recommended_architecture"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    lines += [
        "",
        "## Safety",
        "",
        "This probe only reads files and executes import checks. It does not install",
        "packages, modify Python paths, rewrite launchers or registries, start",
        "services, create ComfyUI folders, or delete anything. Its only writes are",
        "this timestamped report and receipt.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now().strftime("PRP2A_%Y%m%dT%H%M%S")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    runtimes: dict[str, Any] = {}
    for label, relative in RUNTIME_CANDIDATES.items():
        python = ROOT / relative
        entry: dict[str, Any] = {
            "path": str(python),
            "exists": python.is_file(),
        }
        if python.is_file():
            entry["normal"] = run_json_probe(python, isolated=False)
            entry["isolated"] = run_json_probe(python, isolated=True)
            annotate_origins(entry["normal"])
            annotate_origins(entry["isolated"])
        runtimes[label] = entry

    sources = {
        relative: source_imports(ROOT / relative)
        for relative in SELECTED_SOURCE_FILES
    }

    payload: dict[str, Any] = {
        "action": "foxai_portable_runtime_phase2a_read_only_probe",
        "created": created,
        "state": "read_only_probe_complete",
        "verified": True,
        "root": str(ROOT),
        "read_only_probe": True,
        "automatic_install": False,
        "automatic_repair": False,
        "automatic_launch": False,
        "source_or_config_modified": False,
        "delete_operations": [],
        "writes": [
            str((report_dir / "receipt.json").relative_to(ROOT)),
            str((report_dir / "report.md").relative_to(ROOT)),
        ],
        "runtimes": runtimes,
        "system_python_candidates": detect_system_pythons(),
        "source_imports": sources,
        "requirements": requirement_files(),
        "launchers": launcher_inventory(),
        "fleet_registry": fleet_paths(),
    }
    payload["summary"] = summarize(payload)

    receipt = report_dir / "receipt.json"
    report = report_dir / "report.md"
    receipt.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(payload, report)

    print("=" * 72)
    print("FOXAI PORTABLE RUNTIME PHASE 2A — READ-ONLY PROBE")
    print("=" * 72)
    print(f"State: {payload['state']}")
    print(f"Root: {ROOT}")
    print(f"Report: {report_dir}")
    print("")
    print("Must fix before another-computer testing:")
    for item in payload["summary"]["must_fix_before_other_pc"]:
        print(f"  - {item}")
    print("")
    print("Separate runtime decisions:")
    for item in payload["summary"]["separate_runtime_decisions"]:
        print(f"  - {item}")
    print("")
    print("No packages were installed. No launchers or configuration were changed.")
    print("Upload report.md and receipt.json from the folder printed above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
