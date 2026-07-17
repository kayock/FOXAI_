
from __future__ import annotations

import argparse
import ast
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import traceback
import zipfile

KNOWN_HASHES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3', 'foxai.py': '423bb098170dbaad2b96c6b07e31beee171904d286b8364457ce6357551c33d0', 'ComfyUI/main.py': 'd2580be49e7abb3218b1e7056844b2c72a2e7d8711268849429ad3b418c38bc9', 'System/PortableRuntime/verify_desktop_runtime.py': '3743657d9249c00cf11f891b3e703743eca206301f9a48807b17d568a440939e', 'START_FOXAI_DESKTOP_PORTABLE.bat': '89e906d805f99392b4ecc2ea85aa688577517a26e577de3542159a1f5eaf046c', 'START_FOXAI_WORKSHOP_PORTABLE.bat': '1e6b4bb53b81ba53c88fb6d88bf91f35ac5f730744e3ebd7329c6ec79af6728f'}
SHORTCUT_HASHES = {'desktop': {'filename': 'Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02'}, 'web': {'filename': 'START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd'}}

CRITICAL_FREE_BYTES = 2 * 1024**3
RECOMMENDED_FREE_BYTES = 10 * 1024**3
MAX_WHEEL_FILES = 2000
MAX_TOOL_SCAN_FILES = 12000
MAX_REPAIR_PYTHON_FILES = 2500
MAX_MODEL_FILES = 10000

TOOL_SPECS = {
    "git": {
        "filenames": ["git.exe", "git.cmd", "git.bat"],
        "path_commands": ["git.exe", "git"],
        "version_args": ["--version"],
        "importance": "recommended",
        "purpose": "exact diffs, rollback history, and optional approved commits",
    },
    "ripgrep": {
        "filenames": ["rg.exe"],
        "path_commands": ["rg.exe", "rg"],
        "version_args": ["--version"],
        "importance": "recommended",
        "purpose": "fast bounded source search",
    },
    "gitleaks": {
        "filenames": ["gitleaks.exe"],
        "path_commands": ["gitleaks.exe", "gitleaks"],
        "version_args": ["version"],
        "importance": "recommended",
        "purpose": "secret scanning and redaction checks",
    },
    "semgrep": {
        "filenames": ["semgrep.exe", "semgrep-script.py"],
        "path_commands": ["semgrep.exe", "semgrep"],
        "version_args": ["--version"],
        "importance": "recommended",
        "purpose": "static security and code-pattern scanning",
    },
    "keepassxc": {
        "filenames": ["KeePassXC.exe", "keepassxc.exe"],
        "path_commands": ["KeePassXC.exe", "keepassxc"],
        "version_args": ["--version"],
        "importance": "optional",
        "purpose": "portable secrets vault",
    },
    "sandboxie": {
        "filenames": ["SandMan.exe", "SbieCtrl.exe"],
        "path_commands": ["SandMan.exe", "SbieCtrl.exe"],
        "version_args": [],
        "importance": "optional",
        "purpose": "Repair Chamber isolation",
    },
}

MODULE_SPECS = {
    "casbin": {"importance": "required", "purpose": "deterministic authorization"},
    "psutil": {"importance": "required", "purpose": "process and machine inspection"},
    "requests": {"importance": "required", "purpose": "existing service adapters"},
    "customtkinter": {"importance": "required", "purpose": "desktop interface"},
    "PIL": {"importance": "required", "purpose": "desktop images and UI assets"},
    "tkinter": {"importance": "required", "purpose": "desktop GUI runtime"},
    "keyring": {"importance": "recommended", "purpose": "Credential Manager adapter"},
    "tree_sitter": {"importance": "recommended", "purpose": "structured source parsing"},
    "pytest": {"importance": "recommended", "purpose": "controlled verification tests"},
    "llm_guard": {"importance": "optional", "purpose": "prompt/output defenses"},
    "garak": {"importance": "optional", "purpose": "automated model red-team evaluation"},
}

REQUIREMENT_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-ui.txt",
    "ComfyUI/requirements.txt",
]


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def sha256_file(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_under(path: Path, root: Path):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def source_label(path_value, root: Path):
    if not path_value:
        return "NOT_FOUND"
    try:
        path = Path(path_value).resolve()
    except (OSError, TypeError, ValueError):
        return "UNKNOWN"
    return "USB" if is_under(path, root) else "HOST_PC"


def verify_package(bundle: Path):
    manifest_path = bundle / "PACKAGE_MANIFEST.json"
    result = {
        "manifest_exists": manifest_path.is_file(),
        "checked": 0,
        "failed": [],
        "passed": False,
    }
    if not manifest_path.is_file():
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        path = bundle / Path(relative)
        actual_hash = sha256_file(path)
        actual_size = path.stat().st_size if path.is_file() else None
        result["checked"] += 1
        if not (
            path.is_file()
            and actual_hash == expected["sha256"]
            and actual_size == expected["size_bytes"]
        ):
            result["failed"].append({
                "path": relative,
                "expected_sha256": expected["sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": expected["size_bytes"],
                "actual_size_bytes": actual_size,
            })
    result["passed"] = not result["failed"]
    return result


def snapshot_known_integrity(root: Path):
    files = []
    for relative, expected in sorted(KNOWN_HASHES.items()):
        path = root / Path(relative)
        actual = sha256_file(path)
        files.append({
            "path": relative,
            "source": "USB",
            "exists": path.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })

    usb_root = Path(root.anchor)
    shortcuts = []
    for key, item in SHORTCUT_HASHES.items():
        path = usb_root / item["filename"]
        actual = sha256_file(path)
        shortcuts.append({
            "name": key,
            "path": str(path),
            "source": "USB",
            "exists": path.is_file(),
            "expected_sha256": item["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == item["sha256"],
        })

    return {
        "files": files,
        "shortcuts": shortcuts,
        "failed_files": [item for item in files if not item["matches_expected"]],
        "failed_shortcuts": [
            item for item in shortcuts if not item["matches_expected"]
        ],
        "passed": (
            all(item["matches_expected"] for item in files)
            and all(item["matches_expected"] for item in shortcuts)
        ),
    }


def get_volume_info(root: Path):
    result = {
        "root": root.anchor,
        "label": None,
        "filesystem": None,
        "serial_number": None,
        "drive_type_code": None,
        "drive_type": None,
    }
    if os.name != "nt":
        return result

    kernel32 = ctypes.windll.kernel32
    volume_name = ctypes.create_unicode_buffer(261)
    filesystem_name = ctypes.create_unicode_buffer(261)
    serial = ctypes.c_uint32()
    max_component = ctypes.c_uint32()
    flags = ctypes.c_uint32()

    ok = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root.anchor),
        volume_name,
        len(volume_name),
        ctypes.byref(serial),
        ctypes.byref(max_component),
        ctypes.byref(flags),
        filesystem_name,
        len(filesystem_name),
    )
    if ok:
        result.update({
            "label": volume_name.value,
            "filesystem": filesystem_name.value,
            "serial_number": int(serial.value),
        })

    code = int(kernel32.GetDriveTypeW(ctypes.c_wchar_p(root.anchor)))
    names = {
        0: "UNKNOWN",
        1: "NO_ROOT_DIR",
        2: "REMOVABLE",
        3: "FIXED",
        4: "REMOTE",
        5: "CDROM",
        6: "RAMDISK",
    }
    result["drive_type_code"] = code
    result["drive_type"] = names.get(code, "UNKNOWN")
    return result


def get_memory_info():
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_uint32),
            ("dwMemoryLoad", ctypes.c_uint32),
            ("ullTotalPhys", ctypes.c_uint64),
            ("ullAvailPhys", ctypes.c_uint64),
            ("ullTotalPageFile", ctypes.c_uint64),
            ("ullAvailPageFile", ctypes.c_uint64),
            ("ullTotalVirtual", ctypes.c_uint64),
            ("ullAvailVirtual", ctypes.c_uint64),
            ("ullAvailExtendedVirtual", ctypes.c_uint64),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {
            "total_bytes": int(status.ullTotalPhys),
            "available_bytes": int(status.ullAvailPhys),
            "memory_load_percent": int(status.dwMemoryLoad),
        }
    return None


def machine_profile(root: Path, controller: Path):
    usage = shutil.disk_usage(root)
    return {
        "classification": {
            "foxai_root": "USB",
            "controller": source_label(controller, root),
            "dependency_labels": ["USB", "HOST_PC", "NOT_FOUND"],
        },
        "foxai_root": str(root),
        "controller": str(controller),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "python_controller_version": sys.version,
        "memory": get_memory_info(),
        "volume": get_volume_info(root),
        "disk": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "critical_minimum_bytes": CRITICAL_FREE_BYTES,
            "recommended_minimum_bytes": RECOMMENDED_FREE_BYTES,
            "critical_space_passed": usage.free >= CRITICAL_FREE_BYTES,
            "recommended_space_passed": usage.free >= RECOMMENDED_FREE_BYTES,
        },
        "environment_summary": {
            name: os.environ.get(name)
            for name in (
                "COMPUTERNAME",
                "USERNAME",
                "PROCESSOR_IDENTIFIER",
                "PROCESSOR_ARCHITECTURE",
                "NUMBER_OF_PROCESSORS",
            )
        },
    }


def run_json_probe(executable: Path, code: str, env, cwd: Path, timeout=60, use_s=True):
    result = {
        "executable": str(executable),
        "source": None,
        "exists": executable.is_file(),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "data": None,
        "passed": False,
    }
    if not executable.is_file():
        return result

    command = [str(executable)]
    if use_s:
        command.append("-s")
    command.extend(["-c", code])

    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout[-12000:]
        result["stderr"] = completed.stderr[-12000:]
        if completed.returncode == 0 and completed.stdout.strip():
            result["data"] = json.loads(completed.stdout.strip().splitlines()[-1])
        result["passed"] = (
            completed.returncode == 0 and isinstance(result["data"], dict)
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def runtime_probe(root: Path):
    desktop_python = root / "Runtime" / "Desktop" / "python" / "python.exe"
    core_python = root / "env" / "python" / "python.exe"
    desktop_site = root / "Runtime" / "Desktop" / "site-packages"
    core_site = root / "Runtime" / "Core" / "site-packages"

    probe_code = r'''
import importlib
import importlib.util
import json
import site
import sys

required = ["tkinter", "customtkinter", "PIL", "casbin", "psutil", "requests"]
optional = ["keyring", "tree_sitter", "pytest", "llm_guard", "garak"]
modules = {}

for name in required:
    try:
        module = importlib.import_module(name)
        modules[name] = {
            "available": True,
            "origin": getattr(module, "__file__", None),
            "version": getattr(module, "__version__", None),
            "error": None,
        }
    except Exception as exc:
        modules[name] = {
            "available": False,
            "origin": None,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

for name in optional:
    try:
        spec = importlib.util.find_spec(name)
        modules[name] = {
            "available": spec is not None,
            "origin": getattr(spec, "origin", None) if spec else None,
            "version": None,
            "error": None,
        }
    except Exception as exc:
        modules[name] = {
            "available": False,
            "origin": None,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

print(json.dumps({
    "executable": sys.executable,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "enable_user_site": site.ENABLE_USER_SITE,
    "sys_path": sys.path,
    "modules": modules,
}))
'''

    desktop_env = os.environ.copy()
    desktop_env.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHOME": str(root / "Runtime" / "Desktop" / "python"),
        "PYTHONPATH": os.pathsep.join(
            [str(desktop_site), str(core_site), str(root)]
        ),
    })
    desktop = run_json_probe(
        desktop_python, probe_code, desktop_env, root, timeout=60, use_s=True
    )
    desktop["source"] = source_label(desktop_python, root)

    core_env = os.environ.copy()
    core_env.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHOME": "",
        "PYTHONPATH": os.pathsep.join([str(core_site), str(root)]),
    })
    core = run_json_probe(
        core_python, probe_code, core_env, root, timeout=60, use_s=True
    )
    core["source"] = source_label(core_python, root)

    data = desktop.get("data") or {}
    modules = data.get("modules") or {}
    required_names = [
        name for name, spec in MODULE_SPECS.items()
        if spec["importance"] == "required"
    ]
    desktop["required_modules_passed"] = all(
        modules.get(name, {}).get("available") for name in required_names
    )
    desktop["origins_usb_owned"] = all(
        (not item.get("available"))
        or source_label(item.get("origin"), root) == "USB"
        for item in modules.values()
    )
    desktop["portable_contract_passed"] = (
        desktop.get("passed") is True
        and source_label(data.get("executable"), root) == "USB"
        and source_label(data.get("prefix"), root) == "USB"
        and data.get("enable_user_site") is False
        and desktop["required_modules_passed"]
        and desktop["origins_usb_owned"]
    )

    return {
        "desktop": desktop,
        "core_controller": core,
        "passed": desktop["portable_contract_passed"],
    }


def verify_desktop_manifest(root: Path):
    manifest_path = (
        root / "Runtime" / "Desktop" / "DESKTOP_RUNTIME_MANIFEST.json"
    )
    result = {
        "manifest_path": str(manifest_path),
        "exists": manifest_path.is_file(),
        "format": None,
        "declared_file_count": 0,
        "checked": 0,
        "missing": [],
        "size_mismatches": [],
        "hash_mismatches": [],
        "unexpected_cache_files": [],
        "passed": False,
    }
    if not manifest_path.is_file():
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result["format"] = manifest.get("format")
    files = manifest.get("files") or []
    result["declared_file_count"] = len(files)

    for item in files:
        relative = Path(*item["relative"].split("/"))
        if item["kind"] == "runtime":
            path = root / "Runtime" / "Desktop" / "python" / relative
        elif item["kind"] == "desktop_package":
            path = (
                root / "Runtime" / "Desktop" / "site-packages" / relative
            )
        else:
            result["missing"].append({
                "relative": item.get("relative"),
                "reason": f"unknown kind {item.get('kind')}",
            })
            continue

        if not path.is_file():
            result["missing"].append(str(path))
            continue

        actual_size = path.stat().st_size
        if actual_size != item["size_bytes"]:
            result["size_mismatches"].append({
                "path": str(path),
                "expected": item["size_bytes"],
                "actual": actual_size,
            })
            continue

        actual_hash = sha256_file(path)
        if actual_hash != item["sha256"]:
            result["hash_mismatches"].append({
                "path": str(path),
                "expected": item["sha256"],
                "actual": actual_hash,
            })
        result["checked"] += 1

    for scan_root in (
        root / "Runtime" / "Desktop" / "python",
        root / "Runtime" / "Desktop" / "site-packages",
    ):
        if not scan_root.is_dir():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            lower_parts = [part.lower() for part in path.parts]
            if (
                "__pycache__" in lower_parts
                or path.suffix.lower() in {".pyc", ".pyo"}
            ):
                result["unexpected_cache_files"].append(str(path))
                if len(result["unexpected_cache_files"]) >= 200:
                    break

    result["passed"] = (
        result["format"] == "foxai_portable_desktop_runtime_manifest_v2"
        and result["checked"] == len(files)
        and not result["missing"]
        and not result["size_mismatches"]
        and not result["hash_mismatches"]
    )
    return result


def bounded_files(roots, max_depth, max_files):
    files = []
    stack = [(path, 0) for path in roots if path.exists()]
    while stack and len(files) < max_files:
        current, depth = stack.pop()
        try:
            if current.is_file():
                files.append(current)
                continue
            if not current.is_dir() or depth > max_depth:
                continue
            for child in current.iterdir():
                if child.is_dir():
                    stack.append((child, depth + 1))
                elif child.is_file():
                    files.append(child)
                    if len(files) >= max_files:
                        break
        except OSError:
            continue
    return files, bool(stack)


def local_tool_candidates(root: Path):
    roots = [
        root / "tools",
        root / "RepairBay",
        root / "System",
        root / "Runtime",
        root / "Hanger Bay",
    ]
    files, truncated = bounded_files(
        roots, max_depth=5, max_files=MAX_TOOL_SCAN_FILES
    )
    by_name = {}
    for path in files:
        by_name.setdefault(path.name.lower(), []).append(path)
    return by_name, truncated, len(files)


def safe_version(path: Path, args, timeout=10):
    if not args:
        return {
            "attempted": False,
            "returncode": None,
            "output": None,
            "error": None,
        }
    try:
        completed = subprocess.run(
            [str(path), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env={**os.environ, "PYTHONNOUSERSITE": "1"},
        )
        return {
            "attempted": True,
            "returncode": completed.returncode,
            "output": completed.stdout.strip()[-3000:],
            "error": None,
        }
    except Exception as exc:
        return {
            "attempted": True,
            "returncode": None,
            "output": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def tool_inventory(root: Path):
    local_by_name, truncated, scanned = local_tool_candidates(root)
    tools = {}

    for name, spec in TOOL_SPECS.items():
        local_matches = []
        for filename in spec["filenames"]:
            local_matches.extend(local_by_name.get(filename.lower(), []))
        local_matches = sorted(
            {str(path.resolve()) for path in local_matches},
            key=str.lower,
        )

        path_match = None
        for command in spec["path_commands"]:
            resolved = shutil.which(command)
            if resolved:
                path_match = str(Path(resolved).resolve())
                break

        selected = local_matches[0] if local_matches else path_match
        selected_path = Path(selected) if selected else None
        version = (
            safe_version(selected_path, spec["version_args"])
            if selected_path and selected_path.is_file()
            else {
                "attempted": False,
                "returncode": None,
                "output": None,
                "error": None,
            }
        )

        tools[name] = {
            "purpose": spec["purpose"],
            "importance": spec["importance"],
            "available": bool(selected_path and selected_path.is_file()),
            "selected_path": str(selected_path) if selected_path else None,
            "source": (
                source_label(selected_path, root)
                if selected_path else "NOT_FOUND"
            ),
            "usb_candidates": local_matches,
            "path_candidate": path_match,
            "version_probe": version,
        }

    return {
        "classification_rule": (
            "Path under FOXAI root = USB; other path = HOST_PC"
        ),
        "bounded_local_scan": {
            "roots": ["tools", "RepairBay", "System", "Runtime", "Hanger Bay"],
            "max_depth": 5,
            "max_files": MAX_TOOL_SCAN_FILES,
            "files_seen": scanned,
            "truncated": truncated,
        },
        "tools": tools,
    }


def parse_requirement_name(line):
    line = line.strip()
    if not line or line.startswith("#") or line.startswith(("-r", "--")):
        return None
    line = line.split(";", 1)[0].strip()
    line = re.split(r"===|==|~=|!=|<=|>=|<|>", line, maxsplit=1)[0]
    line = line.split("[", 1)[0].strip()
    if not line or "://" in line or line.startswith((".", "/")):
        return None
    return re.sub(r"[-_.]+", "-", line).lower()


def wheel_name(filename):
    if not filename.lower().endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) < 2:
        return None
    return re.sub(r"[-_.]+", "-", parts[0]).lower()


def wheelhouse_report(root: Path):
    wheelhouse = root / "Wheelhouse"
    result = {
        "path": str(wheelhouse),
        "source": "USB",
        "exists": wheelhouse.is_dir(),
        "wheel_count": 0,
        "total_bytes": 0,
        "packages": {},
        "invalid_wheels": [],
        "truncated": False,
        "requirements": {},
        "coverage": {},
    }

    if wheelhouse.is_dir():
        wheels = []
        for path in wheelhouse.rglob("*.whl"):
            wheels.append(path)
            if len(wheels) >= MAX_WHEEL_FILES:
                result["truncated"] = True
                break

        for path in wheels:
            result["wheel_count"] += 1
            result["total_bytes"] += path.stat().st_size
            name = wheel_name(path.name)
            if name:
                result["packages"].setdefault(name, []).append({
                    "filename": path.name,
                    "relative": str(path.relative_to(root)),
                    "size_bytes": path.stat().st_size,
                })
            try:
                if not zipfile.is_zipfile(path):
                    result["invalid_wheels"].append(str(path))
            except OSError as exc:
                result["invalid_wheels"].append(
                    f"{path}: {type(exc).__name__}: {exc}"
                )

    direct = set()
    for relative in REQUIREMENT_FILES:
        path = root / Path(relative)
        entry = {
            "path": relative,
            "exists": path.is_file(),
            "sha256": sha256_file(path),
            "direct_packages": [],
        }
        if path.is_file():
            text = path.read_text(
                encoding="utf-8-sig", errors="replace"
            )
            for line in text.splitlines():
                name = parse_requirement_name(line)
                if name:
                    direct.add(name)
                    entry["direct_packages"].append(name)
        result["requirements"][relative] = entry

    for name in sorted(direct):
        result["coverage"][name] = {
            "covered_by_wheelhouse": name in result["packages"],
            "wheel_files": result["packages"].get(name, []),
        }

    covered = sum(
        1 for item in result["coverage"].values()
        if item["covered_by_wheelhouse"]
    )
    result["coverage_summary"] = {
        "direct_requirements": len(direct),
        "covered": covered,
        "missing": len(direct) - covered,
    }
    result["passed_basic_integrity"] = (
        result["exists"]
        and result["wheel_count"] > 0
        and not result["invalid_wheels"]
    )
    return result


def repair_bay_report(root: Path):
    roots = [
        root / "RepairBay",
        root / "System" / "PortableRuntime",
        root / "tools",
    ]
    files, truncated = bounded_files(
        roots,
        max_depth=6,
        max_files=MAX_REPAIR_PYTHON_FILES * 3,
    )
    python_files = [
        path for path in files if path.suffix.lower() == ".py"
    ][:MAX_REPAIR_PYTHON_FILES]

    errors = []
    parsed = 0
    features = {
        "preview": [],
        "approval": [],
        "verify": [],
        "rollback": [],
        "diff": [],
        "scan": [],
        "receipt": [],
    }

    for path in python_files:
        try:
            text = path.read_text(
                encoding="utf-8-sig", errors="replace"
            )
            ast.parse(text, filename=str(path))
            parsed += 1
            lower = text.lower()
            for term in features:
                if term in lower and len(features[term]) < 50:
                    features[term].append(str(path.relative_to(root)))
        except SyntaxError as exc:
            errors.append({
                "path": str(path.relative_to(root)),
                "line": exc.lineno,
                "offset": exc.offset,
                "message": exc.msg,
            })
        except OSError as exc:
            errors.append({
                "path": str(path.relative_to(root)),
                "message": f"{type(exc).__name__}: {exc}",
            })

    test_files, tests_truncated = bounded_files(
        [root / "tests"], max_depth=6, max_files=5000
    )
    py_tests = [
        path for path in test_files
        if path.name.lower().startswith("test")
        and path.suffix.lower() == ".py"
    ]

    important = [
        "RepairBay",
        "tests",
        "baseline",
        "Backups",
        "Logs",
        "Reports",
        "COMMISSION_FOXAI_USB.bat",
        "COMMISSION_ENGINEERING.bat",
        "ENGINEERING_REPORT.bat",
        "ENGINEERING_STATUS.bat",
    ]

    return {
        "roots": [
            {"path": str(path), "source": "USB", "exists": path.exists()}
            for path in roots
        ],
        "important_paths": [
            {
                "path": relative,
                "exists": (root / Path(relative)).exists(),
                "type": (
                    "directory"
                    if (root / Path(relative)).is_dir()
                    else "file"
                    if (root / Path(relative)).is_file()
                    else None
                ),
            }
            for relative in important
        ],
        "bounded_scan": {
            "max_depth": 6,
            "files_seen": len(files),
            "truncated": truncated,
        },
        "python_syntax": {
            "python_files_considered": len(python_files),
            "parsed_successfully": parsed,
            "errors": errors,
            "passed": not errors,
        },
        "feature_evidence": features,
        "tests_inventory": {
            "test_python_file_count": len(py_tests),
            "examples": [
                str(path.relative_to(root)) for path in py_tests[:100]
            ],
            "truncated": tests_truncated,
            "tests_executed": False,
        },
    }


def model_inventory(root: Path):
    roots = [
        root / "Models",
        root / "ComfyUI" / "models" / "checkpoints",
        root / "ComfyUI" / "models" / "loras",
        root / "ComfyUI" / "models" / "vae",
    ]
    files, truncated = bounded_files(
        roots, max_depth=5, max_files=MAX_MODEL_FILES
    )
    allowed = {".gguf", ".safetensors", ".ckpt", ".pt", ".pth", ".bin"}
    items = []
    total = 0

    for path in files:
        if path.suffix.lower() not in allowed:
            continue
        size = path.stat().st_size
        total += size
        items.append({
            "path": str(path.relative_to(root)),
            "size_bytes": size,
            "source": "USB",
        })

    items.sort(key=lambda item: item["size_bytes"], reverse=True)
    return {
        "roots": [str(path) for path in roots],
        "model_file_count": len(items),
        "total_bytes": total,
        "largest_files": items[:100],
        "truncated": truncated,
        "hashing_skipped": True,
        "reason": (
            "Large model files are inventoried by path and size only."
        ),
    }


def host_python_comfy(root: Path):
    host_python = shutil.which("python.exe") or shutil.which("python")
    result = {
        "command": "python.exe",
        "resolved_path": (
            str(Path(host_python).resolve()) if host_python else None
        ),
        "source": source_label(host_python, root),
        "exists": bool(host_python and Path(host_python).is_file()),
        "version_probe": None,
        "torch_probe": None,
        "comfy_main_exists": (root / "ComfyUI" / "main.py").is_file(),
        "passed": False,
    }
    if not result["exists"]:
        return result

    path = Path(result["resolved_path"])
    result["version_probe"] = safe_version(path, ["--version"], timeout=10)

    code = (
        "import json,sys,torch;"
        "print(json.dumps({"
        "'executable':sys.executable,"
        "'torch_version':getattr(torch,'__version__',None),"
        "'cuda_available':bool(torch.cuda.is_available())"
        "}))"
    )
    env = os.environ.copy()
    env["PYTHONHOME"] = ""
    env["PYTHONPATH"] = ""
    result["torch_probe"] = run_json_probe(
        path,
        code,
        env,
        root / "ComfyUI",
        timeout=60,
        use_s=False,
    )
    result["torch_probe"]["source"] = source_label(path, root)
    result["passed"] = (
        result["comfy_main_exists"]
        and result["torch_probe"].get("passed") is True
    )
    return result


def classify(results):
    critical = []
    notes = []

    def add_critical(name, passed, detail):
        if not passed:
            critical.append({"check": name, "detail": detail})

    def add_note(name, condition, detail):
        if condition:
            notes.append({"check": name, "detail": detail})

    add_critical(
        "preflight_package_integrity",
        results["package_integrity"]["passed"],
        "The preflight package did not match its own manifest.",
    )
    add_critical(
        "known_good_integrity",
        results["known_integrity"]["passed"],
        "A protected or known-good FOXAI file/shortcut changed.",
    )
    add_critical(
        "desktop_runtime_manifest",
        results["desktop_runtime_manifest"]["passed"],
        "The live Desktop runtime did not match its exact manifest.",
    )
    add_critical(
        "desktop_runtime_functional",
        results["runtime_checks"]["passed"],
        "The USB-owned Desktop runtime contract or required imports failed.",
    )
    add_critical(
        "repair_bay_present",
        (Path(results["root"]) / "RepairBay").is_dir(),
        "The RepairBay directory is missing.",
    )
    add_critical(
        "critical_free_space",
        results["machine_profile"]["disk"]["critical_space_passed"],
        "The FOXAI volume has less than 2 GiB free.",
    )
    add_critical(
        "combined_startup_backend",
        results["host_python_comfy"]["passed"],
        "The current ComfyUI host-Python/torch backend failed its import probe.",
    )
    add_critical(
        "repair_python_syntax",
        results["repair_bay"]["python_syntax"]["passed"],
        "A bounded Repair Bay/portable-runtime Python file has a syntax error.",
    )

    add_note(
        "recommended_free_space",
        not results["machine_profile"]["disk"]["recommended_space_passed"],
        "Less than 10 GiB is free on the FOXAI volume.",
    )
    add_note(
        "wheelhouse_missing_or_empty",
        not results["wheelhouse"]["passed_basic_integrity"],
        "The offline wheelhouse is missing, empty, truncated, or has an invalid wheel.",
    )
    add_note(
        "wheelhouse_direct_requirement_gaps",
        results["wheelhouse"]["coverage_summary"]["missing"] > 0,
        (
            f"{results['wheelhouse']['coverage_summary']['missing']} direct "
            "requirement(s) lack an obvious matching wheel."
        ),
    )
    add_note(
        "desktop_bytecode_cache_present",
        bool(results["desktop_runtime_manifest"]["unexpected_cache_files"]),
        (
            "Disposable __pycache__/.pyc files exist in the Desktop runtime; "
            "they are not treated as integrity failures."
        ),
    )

    for name, item in results["tools"]["tools"].items():
        if item["importance"] == "recommended" and not item["available"]:
            notes.append({
                "check": f"recommended_tool_{name}",
                "detail": f"{name} is not available from USB or HOST PC.",
            })
        elif item["importance"] == "recommended" and item["source"] == "HOST_PC":
            notes.append({
                "check": f"host_only_tool_{name}",
                "detail": (
                    f"{name} is available only from HOST PC at "
                    f"{item['selected_path']}."
                ),
            })

    modules = (
        results["runtime_checks"].get("desktop", {}).get("data", {})
        .get("modules", {})
    )
    for name, spec in MODULE_SPECS.items():
        if (
            spec["importance"] == "recommended"
            and not modules.get(name, {}).get("available")
        ):
            notes.append({
                "check": f"recommended_module_{name}",
                "detail": (
                    f"Python module {name} is not available in the USB runtime."
                ),
            })

    if critical:
        state = "NEEDS_ATTENTION"
    elif notes:
        state = "READY_WITH_NOTES"
    else:
        state = "READY"

    return {
        "state": state,
        "critical_failures": critical,
        "notes": notes,
        "critical_failure_count": len(critical),
        "note_count": len(notes),
    }


def recommendations(classification):
    actions = []
    priority = 1

    for failure in classification["critical_failures"]:
        actions.append({
            "priority": priority,
            "severity": "BLOCKER",
            "title": failure["check"],
            "recommendation": failure["detail"],
            "automatic_action_taken": False,
        })
        priority += 1

    for note in classification["notes"]:
        actions.append({
            "priority": priority,
            "severity": "NOTE",
            "title": note["check"],
            "recommendation": note["detail"],
            "automatic_action_taken": False,
        })
        priority += 1

    if not actions:
        actions.append({
            "priority": 1,
            "severity": "INFO",
            "title": "preflight_clear",
            "recommendation": (
                "Proceed to the read-only Repair Bay source/dependency scan."
            ),
            "automatic_action_taken": False,
        })

    return {
        "repairs_performed": False,
        "installs_performed": False,
        "downloads_performed": False,
        "next_actions": actions,
    }


def make_report(results, receipt):
    classification = results.get("classification") or {
        "state": receipt.get("state", "NEEDS_ATTENTION"),
        "critical_failure_count": 1,
        "note_count": 0,
        "critical_failures": [],
        "notes": [],
    }
    machine = results.get("machine_profile") or {}
    disk = machine.get("disk") or {}
    volume = machine.get("volume") or {}
    runtime_manifest = results.get("desktop_runtime_manifest") or {}
    runtime = (results.get("runtime_checks") or {}).get("desktop") or {}
    wheel = results.get("wheelhouse") or {}
    coverage = wheel.get("coverage_summary") or {}
    tools = (results.get("tools") or {}).get("tools") or {}

    lines = [
        "# FOXAI Repair & Optimization Preflight",
        "",
        f"## Overall state: **{classification['state']}**",
        "",
        f"- Critical failures: **{classification.get('critical_failure_count', 0)}**",
        f"- Notes: **{classification.get('note_count', 0)}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        "- Repairs performed: **False**",
        "- Installs/downloads performed: **False**",
        "- FOXAI/ComfyUI launched: **False**",
        "",
        "## Portable runtime",
        "",
        f"- Exact Desktop manifest passed: **{runtime_manifest.get('passed')}**",
        f"- Files checked: **{runtime_manifest.get('checked', 0)}**",
        f"- Functional USB runtime contract passed: "
        f"**{runtime.get('portable_contract_passed')}**",
        "",
        "## Machine and storage",
        "",
        f"- FOXAI root: `{results.get('root')}` (**USB**)",
        f"- Controller: `{machine.get('controller')}` "
        f"(**{(machine.get('classification') or {}).get('controller')}**)",
        f"- Free space: **{disk.get('free_bytes')} bytes**",
        f"- Filesystem: **{volume.get('filesystem')}**",
        "",
        "## Offline wheelhouse",
        "",
        f"- Exists: **{wheel.get('exists')}**",
        f"- Wheels: **{wheel.get('wheel_count', 0)}**",
        f"- Direct requirements covered: **{coverage.get('covered', 0)} / "
        f"{coverage.get('direct_requirements', 0)}**",
        f"- Invalid wheels: **{len(wheel.get('invalid_wheels') or [])}**",
        "",
        "## Repair tooling",
        "",
    ]

    for name, item in tools.items():
        state = "AVAILABLE" if item.get("available") else "MISSING"
        lines.append(f"- {name}: **{state}** ({item.get('source')})")

    if classification.get("critical_failures"):
        lines += ["", "## Critical failures", ""]
        for item in classification["critical_failures"]:
            lines.append(f"- **{item['check']}** — {item['detail']}")

    if classification.get("notes"):
        lines += ["", "## Notes", ""]
        for item in classification["notes"]:
            lines.append(f"- **{item['check']}** — {item['detail']}")

    if receipt.get("failure"):
        lines += [
            "",
            "## Preflight execution failure",
            "",
            f"- `{receipt['failure'].get('message')}`",
        ]

    lines += [
        "",
        "## Safety receipt",
        "",
        "- No live source or configuration file was modified.",
        "- No file was deleted, overwritten, repaired, installed, or downloaded.",
        "- No entire-drive recursive scan was performed.",
        "- Child processes were limited to local import/version probes.",
        "- Dependencies are labeled USB, HOST_PC, or NOT_FOUND.",
        "",
        "Upload this complete `UPLOAD_THIS` folder before any repair plan is created.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    started = utc_now()
    root = Path(args.root).resolve()
    bundle = Path(args.bundle).resolve()
    output = (
        bundle / "PREFLIGHT_OUTPUT" / started.strftime("%Y%m%dT%H%M%SZ")
    )
    upload = output / "UPLOAD_THIS"
    upload.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_phase4a_repair_optimization_read_only_preflight",
        "created": started.isoformat(),
        "root": str(root),
        "state": "NEEDS_ATTENTION",
        "verified": False,
        "read_only_preflight": True,
        "repairs_performed": False,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "foxai_launched": False,
        "comfyui_launched": False,
        "browser_launched": False,
        "entire_drive_recursive_scan": False,
        "child_process_policy": (
            "Only local Python import probes and installed-tool version probes."
        ),
        "writes_limited_to": str(output),
    }
    results = {"root": str(root)}
    exit_code = 2

    try:
        print("1/9 Verifying preflight package...", flush=True)
        results["package_integrity"] = verify_package(bundle)

        print("2/9 Capturing machine profile...", flush=True)
        results["machine_profile"] = machine_profile(
            root, Path(sys.executable).resolve()
        )

        print("3/9 Verifying known-good FOXAI integrity...", flush=True)
        results["known_integrity"] = snapshot_known_integrity(root)

        print("4/9 Hash-verifying the portable Desktop runtime...", flush=True)
        results["desktop_runtime_manifest"] = verify_desktop_manifest(root)

        print("5/9 Probing portable Python runtimes and imports...", flush=True)
        results["runtime_checks"] = runtime_probe(root)

        print("6/9 Inventorying Repair Bay and tests...", flush=True)
        results["repair_bay"] = repair_bay_report(root)

        print("7/9 Inspecting offline wheelhouse...", flush=True)
        results["wheelhouse"] = wheelhouse_report(root)

        print("8/9 Inventorying USB and HOST PC tools...", flush=True)
        results["tools"] = tool_inventory(root)
        results["host_python_comfy"] = host_python_comfy(root)

        print("9/9 Inventorying models and classifying readiness...", flush=True)
        results["models"] = model_inventory(root)
        results["classification"] = classify(results)
        results["recommendations"] = recommendations(
            results["classification"]
        )

        receipt.update({
            "state": results["classification"]["state"],
            "verified": results["package_integrity"]["passed"],
            "critical_failure_count": (
                results["classification"]["critical_failure_count"]
            ),
            "note_count": results["classification"]["note_count"],
        })
        exit_code = (
            0
            if receipt["state"] in {"READY", "READY_WITH_NOTES"}
            else 2
        )

    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        results["classification"] = {
            "state": "NEEDS_ATTENTION",
            "critical_failures": [{
                "check": "preflight_execution",
                "detail": f"{type(exc).__name__}: {exc}",
            }],
            "notes": [],
            "critical_failure_count": 1,
            "note_count": 0,
        }
        results["recommendations"] = recommendations(
            results["classification"]
        )

    finally:
        completed = utc_now()
        elapsed = round((completed - started).total_seconds(), 2)
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = elapsed
        results["elapsed_seconds"] = elapsed

        outputs = {
            "receipt.json": receipt,
            "machine_profile.json": results.get("machine_profile", {}),
            "known_integrity.json": results.get("known_integrity", {}),
            "desktop_runtime_manifest_check.json": results.get(
                "desktop_runtime_manifest", {}
            ),
            "runtime_checks.json": results.get("runtime_checks", {}),
            "repair_bay_report.json": results.get("repair_bay", {}),
            "wheelhouse_report.json": results.get("wheelhouse", {}),
            "tool_inventory.json": results.get("tools", {}),
            "host_python_comfy.json": results.get("host_python_comfy", {}),
            "model_inventory.json": results.get("models", {}),
            "classification.json": results.get("classification", {}),
            "recommendations.json": results.get("recommendations", {}),
        }
        for filename, data in outputs.items():
            (upload / filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        (upload / "report.md").write_text(
            make_report(results, receipt), encoding="utf-8"
        )
        (upload / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this entire UPLOAD_THIS folder. "
            "No repair, install, download, deletion, overwrite, or service launch occurred.\n",
            encoding="utf-8",
        )

        print()
        print("Preflight state:", receipt["state"])
        print("Verified receipt:", receipt["verified"])
        print("Elapsed seconds:", elapsed)
        print("Upload only:", upload)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("No repairs were performed.")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
