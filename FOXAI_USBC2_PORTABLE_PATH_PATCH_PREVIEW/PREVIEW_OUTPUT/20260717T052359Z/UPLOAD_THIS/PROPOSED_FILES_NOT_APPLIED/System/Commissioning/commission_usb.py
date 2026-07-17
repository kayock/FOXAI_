from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import urllib.request
from datetime import datetime, timezone
from typing import Any

VERSION = "1.1-preview"
REPORT_RELATIVE = Path("Reports/Commissioning")
SAFE_COMFY_DIRS = [
    "ComfyUI/custom_nodes",
    "ComfyUI/models",
    "ComfyUI/models/checkpoints",
    "ComfyUI/models/loras",
    "ComfyUI/models/vae",
    "ComfyUI/input",
    "ComfyUI/output",
    "ComfyUI/temp",
]
PORTS = {
    8765: "FOXAI WebUI",
    8080: "Local Chat Engine",
    8188: "ComfyUI",
    8844: "KayocktheOS Core API",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def under_root(value: str | None, root: Path) -> bool:
    if not value or value in {"built-in", "frozen"}:
        return True
    try:
        Path(value).resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def runtime_environment(
    root: Path,
    *,
    portable_paths: bool,
    allow_user_site: bool,
) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONHOME", None)
    if portable_paths:
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(root / "Runtime/Desktop/site-packages"),
                str(root / "Runtime/Core/site-packages"),
            ]
        )
    else:
        env.pop("PYTHONPATH", None)
        if allow_user_site:
            env.pop("PYTHONNOUSERSITE", None)
        else:
            env["PYTHONNOUSERSITE"] = "1"
    return env


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
            and (candidate / "Config/FoxAI.ini").is_file()
        ):
            return candidate
    raise RuntimeError(
        "FOXAI root was not found. Install this under the FOXAI USB root."
    )


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def http_probe(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=0.7) as response:
            return {"reachable": True, "status": int(response.status)}
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


def runtime_probe(
    executable: Path,
    root: Path,
    *,
    structure_only: bool,
    environment: dict[str, str] | None = None,
    use_s: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(executable),
        "exists": executable.is_file(),
        "runs": False,
        "portable_origins": {},
        "modules": {},
    }
    if not executable.is_file():
        return result
    if structure_only:
        result.update({"runs": None, "structure_only": True})
        return result

    probe = """
import importlib.util
import json
import site
import sys
names = ['psutil', 'PIL', 'customtkinter', 'requests', 'casbin', 'torch']
modules = {}
for name in names:
    try:
        spec = importlib.util.find_spec(name)
        modules[name] = {
            'available': bool(spec),
            'origin': getattr(spec, 'origin', None) if spec else None,
        }
    except Exception as exc:
        modules[name] = {'available': False, 'error': type(exc).__name__}
print(json.dumps({
    'version': sys.version,
    'executable': sys.executable,
    'prefix': sys.prefix,
    'base_prefix': sys.base_prefix,
    'sys_path': sys.path,
    'user_site': site.getusersitepackages(),
    'enable_user_site': site.ENABLE_USER_SITE,
    'modules': modules,
}))
"""
    try:
        command = [str(executable)]
        if use_s:
            command.append("-s")
        command.extend(["-c", probe])
        process = subprocess.run(
            command,
            cwd=str(root),
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
        result["returncode"] = process.returncode
        result["stderr"] = process.stderr.strip()[-1200:]
        if process.returncode != 0:
            return result
        data = json.loads(process.stdout.strip().splitlines()[-1])
        result.update(
            {
                "runs": True,
                "version": data.get("version"),
                "executable_reported": data.get("executable"),
                "prefix": data.get("prefix"),
                "base_prefix": data.get("base_prefix"),
                "user_site": data.get("user_site"),
                "enable_user_site": data.get("enable_user_site"),
                "modules": data.get("modules") or {},
            }
        )
        for name, item in result["modules"].items():
            origin = item.get("origin") if isinstance(item, dict) else None
            result["portable_origins"][name] = under_root(origin, root)
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def parse_pth(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "portable_base_ready": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return {
        "exists": True,
        "sha256": sha256(path),
        "entries": lines,
        "has_current_directory": "." in lines,
        "imports_site": "import site" in lines,
        "portable_base_ready": "." in lines and "import site" in lines,
    }


def parse_venv(path: Path, root: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    values = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().casefold()] = value.strip()
    home = values.get("home")
    home_inside = under_root(home, root) if home else None
    return {
        "exists": True,
        "sha256": sha256(path),
        "values": values,
        "home_inside_usb": home_inside,
        "portability_warning": bool(home and home_inside is False),
    }


def compile_check(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "compiles": False}
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        return {"exists": True, "compiles": True, "sha256": sha256(path)}
    except Exception as exc:
        return {
            "exists": True,
            "compiles": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def file_check(path: Path, *, min_bytes: int = 1) -> dict[str, Any]:
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    return {
        "exists": exists,
        "size_bytes": size,
        "size_ok": exists and size >= min_bytes,
        "sha256": (
            sha256(path)
            if exists and size < 64 * 1024 * 1024
            else None
        ),
    }


def dir_check(path: Path) -> dict[str, Any]:
    return {"exists": path.is_dir()}


def status_from(required_ok: bool, notes: list[str]) -> str:
    if not required_ok:
        return "NEEDS_ATTENTION"
    return "READY_WITH_NOTES" if notes else "READY"


def inventory_models(root: Path) -> dict[str, Any]:
    candidates: list[Path] = []
    for base in (root / "Models/Chat", root / "Models/Vision"):
        if base.is_dir():
            candidates.extend(base.rglob("*.gguf"))
    projectors: list[dict[str, Any]] = []
    language: list[dict[str, Any]] = []
    for path in sorted(set(candidates)):
        record = {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
        }
        if path.name.casefold().startswith("mmproj"):
            projectors.append(record)
        else:
            language.append(record)

    checkpoints: list[dict[str, Any]] = []
    checkpoint_dir = root / "ComfyUI/models/checkpoints"
    if checkpoint_dir.is_dir():
        for path in sorted(checkpoint_dir.glob("*.safetensors")):
            checkpoints.append(
                {
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                }
            )
    return {
        "language_models": language,
        "vision_projectors": projectors,
        "creative_checkpoints": checkpoints,
        "language_model_count": len(language),
        "vision_projector_count": len(projectors),
        "creative_checkpoint_count": len(checkpoints),
    }


def runtime_has(
    probe: dict[str, Any],
    module: str,
    *,
    portable_only: bool = False,
) -> bool:
    item = (probe.get("modules") or {}).get(module) or {}
    available = item.get("available") is True
    if portable_only:
        return (
            available
            and (probe.get("portable_origins") or {}).get(module) is True
        )
    return available


def build_report(
    root: Path,
    *,
    structure_only: bool = False,
) -> dict[str, Any]:
    portable_desktop = root / "Runtime/Desktop/python/python.exe"
    embedded = root / "env/python/python.exe"
    venv = root / ".venv/Scripts/python.exe"

    portable_probe = runtime_probe(
        portable_desktop,
        root,
        structure_only=structure_only,
        environment=runtime_environment(
            root,
            portable_paths=True,
            allow_user_site=False,
        ),
        use_s=True,
    )
    embedded_probe = runtime_probe(
        embedded,
        root,
        structure_only=structure_only,
        environment=runtime_environment(
            root,
            portable_paths=False,
            allow_user_site=False,
        ),
        use_s=True,
    )
    venv_probe = runtime_probe(
        venv,
        root,
        structure_only=structure_only,
        environment=runtime_environment(
            root,
            portable_paths=False,
            allow_user_site=False,
        ),
        use_s=True,
    )

    system_python = shutil.which("python")
    system_probe = (
        runtime_probe(
            Path(system_python),
            root,
            structure_only=structure_only,
            environment=runtime_environment(
                root,
                portable_paths=False,
                allow_user_site=True,
            ),
            use_s=False,
        )
        if system_python
        else {"exists": False}
    )

    pth = parse_pth(root / "env/python/python314._pth")
    venv_config = parse_venv(root / ".venv/pyvenv.cfg", root)
    models = inventory_models(root)
    comfy_dirs = {
        relative: dir_check(root / relative)
        for relative in SAFE_COMFY_DIRS
    }
    missing_safe_dirs = [
        relative
        for relative, value in comfy_dirs.items()
        if not value["exists"]
    ]

    core_files = {
        "webui": compile_check(root / "core/foxai_web.py"),
        "server": compile_check(root / "core/server.py"),
        "security": compile_check(root / "core/security_containment.py"),
        "engine": file_check(
            root / "Engine/llama-server.exe",
            min_bytes=1024,
        ),
        "config": file_check(root / "Config/FoxAI.ini"),
    }

    web_runtime = (
        portable_probe if portable_probe.get("runs") else embedded_probe
    )
    web_runtime_ready = bool(
        portable_probe.get("runs")
        or (
            embedded_probe.get("exists")
            and embedded_probe.get("runs") is not False
            and pth.get("portable_base_ready")
        )
    )
    web_notes: list[str] = []
    web_required = all(
        [
            web_runtime_ready,
            core_files["webui"].get("compiles"),
            core_files["server"].get("compiles"),
            core_files["engine"].get("size_ok"),
            core_files["config"].get("exists"),
            models["language_model_count"] > 0,
        ]
    )
    if not structure_only:
        if not runtime_has(web_runtime, "psutil"):
            web_notes.append(
                "psutil is unavailable to bundled Python; metrics and "
                "some process controls will be reduced."
            )
        elif not runtime_has(
            web_runtime,
            "psutil",
            portable_only=True,
        ):
            web_notes.append(
                "psutil resolves outside the USB; another computer may "
                "not provide it."
            )
    if models["vision_projector_count"] == 0:
        web_notes.append(
            "No vision projector was found; image profiles will not be "
            "complete."
        )

    desktop_runtime = (
        portable_probe
        if portable_probe.get("runs")
        else (venv_probe if venv_probe.get("runs") else embedded_probe)
    )
    desktop_required_modules = [
        "customtkinter",
        "PIL",
        "requests",
        "psutil",
    ]
    desktop_missing: list[str] = []
    desktop_external: list[str] = []
    if not structure_only:
        for name in desktop_required_modules:
            if not runtime_has(desktop_runtime, name):
                desktop_missing.append(name)
            elif not runtime_has(
                desktop_runtime,
                name,
                portable_only=True,
            ):
                desktop_external.append(name)
    desktop_required = bool(
        (root / "ui/main_window.py").is_file()
        and desktop_runtime.get("exists")
        and desktop_runtime.get("runs") is not False
        and not desktop_missing
    )
    desktop_notes: list[str] = []
    if desktop_missing:
        desktop_notes.append(
            "Missing desktop modules: " + ", ".join(desktop_missing)
        )
    if desktop_external:
        desktop_notes.append(
            "Desktop modules resolve outside the USB: "
            + ", ".join(desktop_external)
        )
    if (
        desktop_runtime is venv_probe
        and venv_config.get("portability_warning")
    ):
        desktop_notes.append(
            ".venv pyvenv.cfg points outside the USB and may not transfer "
            "to another computer."
        )

    comfy_main = compile_check(root / "ComfyUI/main.py")
    runtime_candidates = [portable_probe, embedded_probe, venv_probe, system_probe]
    torch_local = any(
        runtime_has(item, "torch", portable_only=True)
        for item in runtime_candidates
    )
    torch_any = any(
        runtime_has(item, "torch")
        for item in runtime_candidates
    )
    comfy_required = bool(
        comfy_main.get("compiles")
        and not missing_safe_dirs
        and models["creative_checkpoint_count"] > 0
        and (torch_any or structure_only)
    )
    comfy_notes: list[str] = []
    if missing_safe_dirs:
        comfy_notes.append(
            "Missing safe ComfyUI folders: "
            + ", ".join(missing_safe_dirs)
        )
    if not structure_only and not torch_any:
        comfy_notes.append("No checked Python runtime can import torch.")
    elif not structure_only and torch_any and not torch_local:
        comfy_notes.append(
            "torch is supplied outside the USB; Creative Studio is not "
            "yet proven portable."
        )

    shell_files = {
        "launcher": file_check(root / "System/Launchers/launch.py"),
        "core_api": file_check(root / "System/API/core_api.py"),
        "dashboard": file_check(
            root / "Shell/Bridge_Dashboard/index.html"
        ),
        "operator": file_check(root / "System/Config/operator.yaml"),
        "browser_interface": file_check(
            root
            / "Interface/Kayock_Browser/"
            "Kayock-Browser-2.5.3-rc.1-Portable.exe",
            min_bytes=1024,
        ),
        "browser_shell": dir_check(root / "Shell/Kayock_Browser"),
    }
    shell_required = all(
        [
            shell_files["launcher"]["exists"],
            shell_files["core_api"]["exists"],
            shell_files["dashboard"]["exists"],
            shell_files["operator"]["exists"],
            shell_files["browser_interface"]["size_ok"],
        ]
    )
    shell_notes = [
        "This is a separate alternate shell, not the primary FOXAI "
        "WebUI launcher.",
        "Starting it writes System/Logs/boot.log and first boot may update "
        "System/Config/operator.yaml.",
    ]

    node = shutil.which("node")
    npm = shutil.which("npm")
    bridge_package = root / "Bridge/package.json"
    shell_package = root / "Shell/KayockBrowser/package.json"
    bridge_required = bool(
        node
        and npm
        and (bridge_package.is_file() or shell_package.is_file())
    )
    bridge_notes: list[str] = []
    if not node:
        bridge_notes.append("Node.js was not found on this computer.")
    if not npm:
        bridge_notes.append("npm was not found on this computer.")
    bridge_notes.append(
        "Existing Bridge launchers may run npm install; commissioning "
        "never runs them automatically."
    )

    ports = {}
    for port, label in PORTS.items():
        opened = port_open(port)
        probe = None
        if opened:
            if port == 8765:
                probe = http_probe("http://127.0.0.1:8765/")
            elif port == 8080:
                probe = http_probe("http://127.0.0.1:8080/health")
            elif port == 8188:
                probe = http_probe(
                    "http://127.0.0.1:8188/system_stats"
                )
            elif port == 8844:
                probe = http_probe("http://127.0.0.1:8844/api/ping")
        ports[str(port)] = {
            "label": label,
            "open": opened,
            "probe": probe,
        }

    browser_actual = (
        root
        / "Interface/Kayock_Browser/"
        "Kayock-Browser-2.5.3-rc.1-Portable.exe"
    )
    fleet_path = root / "Config/fleet_registry.json"
    fleet_text = (
        fleet_path.read_text(encoding="utf-8", errors="ignore")
        if fleet_path.is_file()
        else ""
    )
    disk = shutil.disk_usage(root)
    portable_required_modules = [
        "customtkinter",
        "PIL",
        "requests",
        "psutil",
    ]
    portable_ready = bool(
        portable_probe.get("runs")
        and all(
            runtime_has(
                portable_probe,
                name,
                portable_only=True,
            )
            for name in portable_required_modules
        )
    )
    host_assisted_ready = bool(
        system_probe.get("runs")
        and all(
            runtime_has(system_probe, name)
            for name in portable_required_modules
        )
    )
    runtime_mode = (
        "PORTABLE_READY"
        if portable_ready
        else (
            "HOST_ASSISTED_READY"
            if host_assisted_ready
            else "NEEDS_ATTENTION"
        )
    )

    web_status = status_from(web_required, web_notes)
    if web_status == "NEEDS_ATTENTION":
        overall_status = "NEEDS_ATTENTION"
    elif any(
        [
            desktop_notes,
            comfy_notes,
            venv_config.get("portability_warning"),
        ]
    ):
        overall_status = "READY_WITH_NOTES"
    else:
        overall_status = "READY"

    return {
        "action": "foxai_usb_commissioning_check",
        "created": utc_now(),
        "version": VERSION,
        "root": str(root),
        "read_only_check": True,
        "reports_written": False,
        "automatic_install": False,
        "automatic_repair": False,
        "automatic_launch": False,
        "overall_status": overall_status,
        "runtime_mode": runtime_mode,
        "primary_launcher": "START_FOXAI_WEB_PORTABLE.bat",
        "desktop_launcher": "Start FoxAI.bat",
        "alternate_shell_launcher": "Start_KayocktheOS.bat",
        "profiles": {
            "FOXAI WebUI": {
                "status": web_status,
                "required_ok": web_required,
                "notes": web_notes,
                "launcher": "START_FOXAI_WEB_PORTABLE.bat",
            },
            "FOXAI Desktop": {
                "status": status_from(
                    desktop_required,
                    desktop_notes,
                ),
                "required_ok": desktop_required,
                "notes": desktop_notes,
                "launcher": "Start FoxAI.bat",
            },
            "Creative Studio / ComfyUI": {
                "status": status_from(comfy_required, comfy_notes),
                "required_ok": comfy_required,
                "notes": comfy_notes,
                "launcher": "operator-controlled through FOXAI",
            },
            "KayocktheOS Alternate Shell": {
                "status": status_from(shell_required, shell_notes),
                "required_ok": shell_required,
                "notes": shell_notes,
                "launcher": "Start_KayocktheOS.bat",
                "default": False,
            },
            "Bridge / Node Shell": {
                "status": status_from(bridge_required, bridge_notes),
                "required_ok": bridge_required,
                "notes": bridge_notes,
                "default": False,
            },
        },
        "runtime": {
            "portable_desktop_python": portable_probe,
            "embedded_python": embedded_probe,
            "embedded_pth": pth,
            "venv_python": venv_probe,
            "venv_config": venv_config,
            "system_python": system_probe,
        },
        "core_files": core_files,
        "models": models,
        "comfyui": {
            "main": comfy_main,
            "safe_directories": comfy_dirs,
            "missing_safe_directories": missing_safe_dirs,
            "safe_folder_repair_available_in_this_phase": False,
        },
        "alternate_shell": shell_files,
        "ports": ports,
        "portability": {
            "root_drive": root.drive,
            "root_bat_files": len(list(root.glob("*.bat"))),
            "fleet_registry_contains_hardcoded_z": "Z:\\" in fleet_text,
            "secondary_browser_launcher_path_stale": (
                browser_actual.is_file()
                and not (root.parent / browser_actual.name).is_file()
            ),
            "portable_desktop_site_packages_directory": (
                root / "Runtime/Desktop/site-packages"
            ).is_dir(),
            "portable_core_site_packages_directory": (
                root / "Runtime/Core/site-packages"
            ).is_dir(),
        },
        "storage": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "next_safe_action": (
            "Start FOXAI WebUI"
            if web_required
            else "Open the report and correct required WebUI checks"
        ),
    }


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# FOXAI USB Commissioning Report",
        "",
        f"- Created: `{report['created']}`",
        f"- Root: `{report['root']}`",
        f"- Overall: **{report['overall_status']}**",
        f"- Runtime mode: **{report['runtime_mode']}**",
        f"- Automatic install: **{report['automatic_install']}**",
        f"- Automatic repair: **{report['automatic_repair']}**",
        f"- Automatic launch: **{report['automatic_launch']}**",
        "",
        "## Profiles",
    ]
    for name, profile in report["profiles"].items():
        lines.extend(
            [
                "",
                f"### {name}",
                f"Status: **{profile['status']}**",
            ]
        )
        for note in profile.get("notes") or []:
            lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "This check does not install packages, create missing ComfyUI ",
            "folders, rewrite drive-letter paths, alter configuration, or ",
            "start a service. Existing launchers remain unchanged.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    folder = root / REPORT_RELATIVE / f"USBC1_{stamp}"
    folder.mkdir(parents=True, exist_ok=False)
    written = dict(report)
    written["reports_written"] = True
    (folder / "receipt.json").write_text(
        json.dumps(written, indent=2),
        encoding="utf-8",
    )
    (folder / "report.md").write_text(
        report_markdown(written),
        encoding="utf-8",
    )
    return folder


def print_summary(report: dict[str, Any]) -> None:
    print("=" * 72)
    print("FOXAI USB COMMISSIONING")
    print("=" * 72)
    print("Overall:", report["overall_status"])
    print("Runtime mode:", report["runtime_mode"])
    print("Root:", report["root"])
    print()
    for name, profile in report["profiles"].items():
        print(f"[{profile['status']:<16}] {name}")
        for note in profile.get("notes") or []:
            print("  -", note)
    print()
    print("Next safe action:", report["next_safe_action"])


def launch_batch(root: Path, relative: str) -> None:
    target = root / relative
    if not target.is_file():
        print("Launcher is missing:", target)
        return
    if os.name != "nt":
        print("Launch is supported on Windows only.")
        return
    subprocess.Popen(
        ["cmd.exe", "/c", "start", "", str(target)],
        cwd=str(root),
    )


def interactive(
    root: Path,
    report: dict[str, Any],
    report_folder: Path | None,
) -> None:
    while True:
        print_summary(report)
        print("1. Start FOXAI WebUI")
        print("2. Start FOXAI Desktop")
        print("3. Show alternate KayocktheOS Shell warning")
        print("4. Open commissioning report folder")
        print("5. Run checks again")
        print("6. Exit")
        choice = input("\nSelect option: ").strip()
        if choice == "1":
            if report["profiles"]["FOXAI WebUI"]["required_ok"]:
                launch_batch(root, "START_FOXAI_WEB_PORTABLE.bat")
            else:
                print("FOXAI WebUI is not ready. Review required checks.")
            input("Press Enter...")
        elif choice == "2":
            if report["profiles"]["FOXAI Desktop"]["required_ok"]:
                launch_batch(root, "Start FoxAI.bat")
            else:
                print("FOXAI Desktop is not ready on this computer.")
            input("Press Enter...")
        elif choice == "3":
            print("\nThe alternate shell is not the primary FOXAI interface.")
            print(
                "It starts a local API, writes System/Logs/boot.log, and "
                "may update"
            )
            print("System/Config/operator.yaml during first boot.")
            print(
                "Use Start_KayocktheOS.bat directly only when you intend "
                "that workflow."
            )
            input("Press Enter...")
        elif choice == "4":
            if report_folder and os.name == "nt":
                os.startfile(report_folder)  # type: ignore[attr-defined]
            else:
                print(report_folder or "No report folder was written.")
            input("Press Enter...")
        elif choice == "5":
            report = build_report(root)
            print("Checks refreshed.")
        elif choice == "6":
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--noninteractive", action="store_true")
    parser.add_argument("--structure-only", action="store_true")
    args = parser.parse_args()

    root = (
        Path(args.root).resolve()
        if args.root
        else find_root(Path(__file__).resolve())
    )
    report = build_report(root, structure_only=args.structure_only)
    report_folder = None
    if not args.no_write:
        report_folder = write_report(root, report)
        report["report_folder"] = str(report_folder)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)
        if report_folder:
            print("Report:", report_folder)
    if not args.noninteractive and not args.json:
        interactive(root, report, report_folder)
    return 0 if report["profiles"]["FOXAI WebUI"]["required_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
