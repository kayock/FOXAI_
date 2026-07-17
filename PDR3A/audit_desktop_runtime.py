from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads(
    (PACKAGE / "AUDIT_TARGETS.json").read_text(encoding="utf-8")
)
REPORT_ROOT = ROOT / "Reports" / "DesktopRuntimeAudit"

DRIVE_PATH_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])([A-Z]:\\[^\"'\r\n<>|]*)"
)
PATH_STRING_SUFFIXES = {
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".json", ".ini", ".yaml", ".yml", ".toml", ".db",
    ".sqlite", ".sqlite3", ".bat", ".cmd", ".exe", ".py",
    ".gguf", ".wav", ".mp3",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, include_hash: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
    }
    if not path.is_file():
        return result
    stat = path.stat()
    result.update({
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
    })
    if include_hash:
        result["sha256"] = sha256(path)
    return result


def desktop_locations() -> list[Path]:
    candidates: list[Path] = []
    userprofile = os.environ.get("USERPROFILE")
    public = os.environ.get("PUBLIC")
    onedrives = [
        os.environ.get("OneDrive"),
        os.environ.get("OneDriveConsumer"),
        os.environ.get("OneDriveCommercial"),
    ]
    if userprofile:
        candidates.append(Path(userprofile) / "Desktop")
    if public:
        candidates.append(Path(public) / "Desktop")
    for raw in onedrives:
        if raw:
            candidates.append(Path(raw) / "Desktop")

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        if path.is_dir():
            unique.append(path)
    return unique


def powershell_executable() -> str | None:
    return (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
        or shutil.which("pwsh.exe")
        or shutil.which("pwsh")
    )


def resolve_shortcut(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "resolved": False,
        "resolution_method": None,
    }
    if not path.is_file():
        return record

    shell = powershell_executable()
    if not shell:
        record["error"] = "PowerShell was not found."
        return record

    escaped = str(path).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop';"
        "$w=New-Object -ComObject WScript.Shell;"
        f"$s=$w.CreateShortcut('{escaped}');"
        "[pscustomobject]@{"
        "TargetPath=$s.TargetPath;"
        "Arguments=$s.Arguments;"
        "WorkingDirectory=$s.WorkingDirectory;"
        "IconLocation=$s.IconLocation;"
        "Description=$s.Description;"
        "WindowStyle=$s.WindowStyle;"
        "Hotkey=$s.Hotkey"
        "}|ConvertTo-Json -Compress"
    )
    process = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if process.returncode != 0:
        record["error"] = (
            (process.stderr or process.stdout or "Shortcut resolution failed.")
            .strip()[-2000:]
        )
        return record

    try:
        data = json.loads(process.stdout.strip())
    except Exception as exc:
        record["error"] = f"Shortcut JSON parse failed: {exc}"
        record["stdout"] = process.stdout
        return record

    record.update(data)
    record["resolved"] = True
    record["resolution_method"] = "WScript.Shell.CreateShortcut"

    target_raw = data.get("TargetPath") or ""
    working_raw = data.get("WorkingDirectory") or ""
    record["target_exists"] = (
        Path(target_raw).exists() if target_raw else False
    )
    record["working_directory_exists"] = (
        Path(working_raw).is_dir() if working_raw else False
    )
    return record


def find_matching_shortcuts() -> dict[str, Any]:
    terms = [
        item.casefold()
        for item in TARGETS["desktop_shortcut_name_terms"]
    ]
    locations = desktop_locations()
    matches: list[dict[str, Any]] = []
    total = 0

    for location in locations:
        try:
            for path in sorted(location.glob("*.lnk")):
                total += 1
                name = path.stem.casefold()
                if any(term in name for term in terms):
                    matches.append(resolve_shortcut(path))
        except Exception as exc:
            matches.append({
                "path": str(location),
                "resolved": False,
                "error": f"{type(exc).__name__}: {exc}",
            })

    return {
        "searched_locations": [str(item) for item in locations],
        "matching_shortcuts": matches,
        "matching_count": len(matches),
        "all_desktop_shortcut_count": total,
        "scope": "Desktop .lnk files only; matching names only are resolved.",
    }


def analyze_batch_text(text: str, path: Path) -> dict[str, Any]:
    lines = text.splitlines()
    commands = []
    absolute_paths = []
    system_python_tokens = []

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        lower = stripped.casefold()
        if not stripped or lower.startswith(("rem ", "::")):
            continue
        if any(
            token in lower
            for token in (
                "python", "py ", "main_window", "customtkinter",
                "activate", ".venv", "env\\python", "start ",
                "cd ", "pushd", "set ",
            )
        ):
            commands.append({
                "line": number,
                "text": line[:1000],
            })
        for match in DRIVE_PATH_RE.finditer(line):
            absolute_paths.append({
                "line": number,
                "path": match.group(1).strip(),
            })
        if re.search(
            r"(?i)(^|\s)(python|pythonw|py)(\.exe)?(\s|$)",
            line,
        ):
            system_python_tokens.append({
                "line": number,
                "text": line[:1000],
            })

    return {
        "line_count": len(lines),
        "commands_of_interest": commands,
        "absolute_drive_paths": absolute_paths,
        "uses_system_python_token": bool(system_python_tokens),
        "system_python_evidence": system_python_tokens,
        "mentions_venv": ".venv" in text.casefold(),
        "mentions_embedded_python": (
            "env\\python" in text.casefold()
            or "env/python" in text.casefold()
        ),
        "mentions_ui_main_window": (
            "ui\\main_window.py" in text.casefold()
            or "ui/main_window.py" in text.casefold()
            or "main_window.py" in text.casefold()
        ),
        "source_path": str(path),
    }


def root_launcher_inventory() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(ROOT.glob("*.bat")):
        lower = path.name.casefold()
        if "fox" not in lower and "kayock" not in lower:
            continue
        record = file_record(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        record.update(analyze_batch_text(text, path))
        records.append(record)
    return records


def analyze_python_source(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "imports": [],
        "from_imports": [],
        "string_path_candidates": [],
        "absolute_drive_paths": [],
        "local_module_candidates": [],
        "parse_error": None,
    }
    if not path.is_file():
        return result

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text, filename=str(path))
    except Exception as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"
        return result

    imports: set[str] = set()
    from_imports: set[str] = set()
    path_candidates = []
    absolute_paths = []
    local_candidates: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
                local_candidates.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                from_imports.add(node.module)
                local_candidates.add(node.module.split(".", 1)[0])
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        ):
            value = node.value.strip()
            if not value or len(value) > 1000:
                continue
            suffix = Path(value).suffix.casefold()
            if (
                suffix in PATH_STRING_SUFFIXES
                or "\\" in value
                or "/" in value
            ):
                path_candidates.append({
                    "line": getattr(node, "lineno", None),
                    "value": value,
                })
            for match in DRIVE_PATH_RE.finditer(value):
                absolute_paths.append({
                    "line": getattr(node, "lineno", None),
                    "path": match.group(1).strip(),
                })

    result.update({
        "imports": sorted(imports),
        "from_imports": sorted(from_imports),
        "string_path_candidates": path_candidates[:300],
        "absolute_drive_paths": absolute_paths[:100],
        "local_module_candidates": sorted(local_candidates),
        "line_count": len(text.splitlines()),
        "sha256": sha256(path),
    })
    return result


def run_python_probe(executable: Path, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "executable": str(executable),
        "exists": executable.is_file(),
        "passed": False,
        "returncode": None,
        "data": None,
        "stderr": None,
    }
    if not executable.is_file():
        return result

    probe = r'''
import importlib
import importlib.metadata
import json
import os
import pathlib
import site
import sys

names = json.loads(sys.argv[1])
data = {
    "executable": sys.executable,
    "version": sys.version,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "user_site_enabled": bool(getattr(site, "ENABLE_USER_SITE", None)),
    "user_site": site.getusersitepackages(),
    "sys_path": list(sys.path),
    "platform": sys.platform,
    "packages": {},
    "tk": {},
    "candidate_tcl_directories": [],
}

for name in names:
    item = {
        "available": False,
        "module_file": None,
        "version": None,
        "error": None,
    }
    try:
        module = importlib.import_module(name)
        item["available"] = True
        item["module_file"] = getattr(module, "__file__", None)
        package_name = {
            "PIL": "Pillow",
            "casbin": "pycasbin",
        }.get(name, name)
        try:
            item["version"] = importlib.metadata.version(package_name)
        except Exception:
            item["version"] = getattr(module, "__version__", None)
    except Exception as exc:
        item["error"] = f"{type(exc).__name__}: {exc}"
    data["packages"][name] = item

try:
    import tkinter
    tcl = tkinter.Tcl()
    data["tk"] = {
        "available": True,
        "TkVersion": tkinter.TkVersion,
        "TclVersion": tkinter.TclVersion,
        "tcl_patchlevel": tcl.eval("info patchlevel"),
        "tk_library_env": os.environ.get("TK_LIBRARY"),
        "tcl_library_env": os.environ.get("TCL_LIBRARY"),
    }
except Exception as exc:
    data["tk"] = {
        "available": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

bases = {
    pathlib.Path(sys.executable).resolve().parent,
    pathlib.Path(sys.prefix).resolve(),
    pathlib.Path(sys.base_prefix).resolve(),
}
for base in sorted(bases, key=lambda p: str(p).casefold()):
    for candidate in (
        base / "tcl",
        base / "Lib" / "tkinter",
        base / "DLLs",
    ):
        data["candidate_tcl_directories"].append({
            "path": str(candidate),
            "exists": candidate.exists(),
        })

print(json.dumps(data))
'''
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [
            str(executable),
            "-s",
            "-c",
            probe,
            json.dumps(TARGETS["runtime_probe_imports"]),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result["returncode"] = process.returncode
    result["stderr"] = process.stderr
    if process.returncode != 0:
        result["stdout"] = process.stdout[-5000:]
        return result

    try:
        result["data"] = json.loads(process.stdout.strip())
        result["passed"] = True
    except Exception as exc:
        result["stderr"] = (
            (process.stderr or "")
            + f"\nJSON parse failure: {type(exc).__name__}: {exc}"
        )
        result["stdout"] = process.stdout[-5000:]
    return result


def discover_system_pythons() -> dict[str, Any]:
    commands = [
        ["where.exe", "python.exe"],
        ["where.exe", "pythonw.exe"],
        ["py.exe", "-0p"],
    ]
    results = []
    candidates: list[Path] = []

    for command in commands:
        executable = shutil.which(command[0])
        if not executable:
            results.append({
                "command": command,
                "available": False,
            })
            continue

        process = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=45,
        )
        results.append({
            "command": [executable, *command[1:]],
            "available": True,
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        })

        for line in (process.stdout or "").splitlines():
            cleaned = line.strip().strip("*").strip()
            direct = Path(cleaned)
            if direct.suffix.casefold() == ".exe" and direct.is_file():
                candidates.append(direct)
                continue
            match = re.search(
                r"(?i)([A-Z]:\\.*?python(?:w)?\.exe)\s*$",
                cleaned,
            )
            if match:
                possible = Path(match.group(1))
                if possible.is_file():
                    candidates.append(possible)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)

    return {
        "discovery_commands": results,
        "candidates": [str(path) for path in unique],
        "probes": [
            run_python_probe(path, f"system_python_{index + 1}")
            for index, path in enumerate(unique[:8])
        ],
    }


def pyvenv_record(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
    }
    if not path.is_file():
        return result

    text = path.read_text(encoding="utf-8", errors="replace")
    values = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    home = values.get("home")
    result.update({
        "values": values,
        "host_bound_home": home,
        "host_bound": bool(
            home
            and Path(home).drive
            and Path(home).drive.casefold()
            != ROOT.drive.casefold()
        ),
    })
    return result


def package_metadata_from_runtime(runtime_root: Path) -> dict[str, Any]:
    site_packages = runtime_root / "site-packages"
    result: dict[str, Any] = {
        "runtime_root": str(runtime_root),
        "site_packages": str(site_packages),
        "exists": site_packages.is_dir(),
        "packages": {},
    }
    if not site_packages.is_dir():
        return result

    names = {
        "psutil": "psutil",
        "requests": "requests",
        "pycasbin": "pycasbin",
        "watchdog": "watchdog",
        "pluggy": "pluggy",
        "Pillow": "pillow",
        "customtkinter": "customtkinter",
    }
    for display, prefix in names.items():
        matches = sorted(
            site_packages.glob(f"{prefix.replace('-', '_')}*.dist-info")
        )
        result["packages"][display] = {
            "dist_info_matches": [str(item) for item in matches],
            "available": bool(matches),
        }
    return result


def shortcut_launch_chain(
    shortcuts: list[dict[str, Any]],
    launchers: list[dict[str, Any]],
) -> dict[str, Any]:
    chains = []
    launcher_by_path = {
        str(Path(item["path"]).resolve()).casefold(): item
        for item in launchers
        if item.get("exists")
    }

    for shortcut in shortcuts:
        target_raw = shortcut.get("TargetPath") or ""
        target = Path(target_raw) if target_raw else None
        chain: dict[str, Any] = {
            "shortcut": shortcut.get("path"),
            "target": target_raw or None,
            "arguments": shortcut.get("Arguments"),
            "working_directory": shortcut.get("WorkingDirectory"),
            "target_exists": shortcut.get("target_exists"),
            "launcher_analysis": None,
        }
        if target and target.exists():
            key = str(target.resolve()).casefold()
            chain["launcher_analysis"] = launcher_by_path.get(key)
        chains.append(chain)

    return {"chains": chains}


def classify(
    shortcut_data: dict[str, Any],
    launchers: list[dict[str, Any]],
    runtime_probes: list[dict[str, Any]],
    system_pythons: dict[str, Any],
    venv: dict[str, Any],
    shared_core: dict[str, Any],
) -> dict[str, Any]:
    stable_shortcuts = [
        item for item in shortcut_data["matching_shortcuts"]
        if item.get("resolved") and item.get("target_exists")
    ]

    bundled = next(
        (
            probe for probe in runtime_probes
            if probe["label"] == "bundled_embedded_python"
        ),
        None,
    )
    venv_probe = next(
        (
            probe for probe in runtime_probes
            if probe["label"] == "current_dot_venv"
        ),
        None,
    )

    def package_available(
        probe: dict[str, Any] | None,
        name: str,
    ) -> bool:
        try:
            return bool(
                probe
                and probe["passed"]
                and probe["data"]["packages"][name]["available"]
            )
        except Exception:
            return False

    bundled_tk = bool(
        bundled
        and bundled.get("passed")
        and bundled.get("data", {}).get("tk", {}).get("available")
    )
    venv_tk = bool(
        venv_probe
        and venv_probe.get("passed")
        and venv_probe.get("data", {}).get("tk", {}).get("available")
    )
    system_tk_count = sum(
        bool(
            item.get("passed")
            and item.get("data", {}).get("tk", {}).get("available")
        )
        for item in system_pythons.get("probes", [])
    )

    must_fix = []
    reusable = []
    preserve = []
    notes = []

    if not bundled_tk:
        must_fix.append(
            "The current USB embedded Python has no usable Tcl/Tk runtime; "
            "it cannot become the Desktop GUI runtime by wheels alone."
        )
    if not package_available(bundled, "customtkinter"):
        must_fix.append(
            "The USB embedded runtime does not own CustomTkinter."
        )
    if not package_available(bundled, "PIL"):
        must_fix.append(
            "The USB embedded runtime does not own Pillow/PIL."
        )
    if venv.get("host_bound"):
        must_fix.append(
            "The existing .venv is tied to a Python home outside the USB."
        )
    if any(item.get("uses_system_python_token") for item in launchers):
        must_fix.append(
            "At least one Desktop launcher invokes system Python by name."
        )

    for name in ("psutil", "requests", "pycasbin", "watchdog", "pluggy"):
        if shared_core.get("packages", {}).get(name, {}).get("available"):
            reusable.append(
                f"Runtime/Core already owns {name}; the Desktop runtime can "
                "reuse it if import isolation remains explicit."
            )

    preserve.extend([
        "Keep the currently working Desktop shortcut and launcher unchanged "
        "until the USB-owned Desktop runtime passes guarded launch testing.",
        "Keep the working portable WebUI runtime and launcher unchanged.",
        "Keep ComfyUI/PyTorch outside this Desktop-runtime milestone.",
        "Keep all model files and model-source registry behavior unchanged.",
    ])

    if stable_shortcuts:
        notes.append(
            "A matching resolved Desktop shortcut was found and its stable "
            "launch chain can ground Phase 3B."
        )
    else:
        notes.append(
            "No matching resolved Desktop shortcut was found automatically. "
            "The launcher audit still proceeds; a shortcut Target and Start-in "
            "value may be requested before Phase 3B."
        )

    return {
        "stable_shortcut_found": bool(stable_shortcuts),
        "stable_shortcut_count": len(stable_shortcuts),
        "bundled_tk_available": bundled_tk,
        "dot_venv_tk_available": venv_tk,
        "system_python_with_tk_count": system_tk_count,
        "must_fix": must_fix,
        "reusable": reusable,
        "preserve": preserve,
        "notes": notes,
        "recommended_phase3b_design": [
            "Acquire or assemble a complete USB-owned CPython runtime that "
            "includes Tcl/Tk rather than modifying the embedded WebUI runtime.",
            "Give the Desktop runtime its own isolated site-packages layer.",
            "Reuse approved Runtime/Core packages through an explicit path "
            "contract where versions are compatible.",
            "Add Desktop-only packages such as CustomTkinter and Pillow to a "
            "separate verified wheelhouse/runtime manifest.",
            "Create a new portable Desktop launcher beside the existing stable "
            "launcher; do not overwrite the stable launcher initially.",
            "Validate icon/assets, working directory, context menus, and model "
            "launch integration before changing shortcuts.",
        ],
    }


def write_report(receipt: dict[str, Any], path: Path) -> None:
    findings = receipt.get("findings", {})
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3A",
        "## Read-Only Audit",
        "",
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Machine: `{receipt['machine']['name']}`",
        "- Desktop GUI launched: **False**",
        "- Model or ComfyUI action: **None**",
        "- Pip/package installation: **None**",
        "- Live files modified: **False**",
        "- Network access: **False**",
        "",
        "## Stable shortcut",
        "",
        f"- Matching resolved shortcut found: "
        f"**{findings.get('stable_shortcut_found')}**",
        f"- Matching resolved shortcut count: "
        f"**{findings.get('stable_shortcut_count', 0)}**",
        "",
        "## Runtime findings",
        "",
        f"- Bundled embedded Python has Tk: "
        f"**{findings.get('bundled_tk_available')}**",
        f"- Existing `.venv` has Tk: "
        f"**{findings.get('dot_venv_tk_available')}**",
        f"- Discovered system Pythons with Tk: "
        f"**{findings.get('system_python_with_tk_count', 0)}**",
        "",
        "## Must fix",
        "",
    ]

    for item in findings.get("must_fix", []):
        lines.append(f"- {item}")

    lines += [
        "",
        "## Reusable portable-core components",
        "",
    ]
    for item in findings.get("reusable", []):
        lines.append(f"- {item}")

    lines += [
        "",
        "## Preserve",
        "",
    ]
    for item in findings.get("preserve", []):
        lines.append(f"- {item}")

    lines += [
        "",
        "## Phase 3B design direction",
        "",
    ]
    for item in findings.get("recommended_phase3b_design", []):
        lines.append(f"- {item}")

    lines += [
        "",
        "## Safety",
        "",
        "This audit only reads explicitly scoped FOXAI files, known runtime",
        "locations, and Desktop shortcut metadata. It does not open the GUI,",
        "run pip, install packages, change shortcuts, start models, contact",
        "network services, or modify FOXAI.",
    ]

    if receipt.get("failure"):
        lines += [
            "",
            "## Failure",
            "",
            f"- `{receipt['failure']['type']}: "
            f"{receipt['failure']['message']}`",
        ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("PDR3A_%Y%m%dT%H%M%SZ")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "foxai_portable_desktop_runtime_phase3a_audit",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "machine": {
            "name": (
                os.environ.get("COMPUTERNAME")
                or platform.node()
                or "UNKNOWN"
            ).upper(),
            "platform": platform.platform(),
            "python": sys.version,
            "python_executable": sys.executable,
        },
        "read_only": True,
        "apply_capability_present": False,
        "desktop_gui_launched": False,
        "automatic_launch": False,
        "model_server_action": False,
        "comfyui_action": False,
        "pip_install": False,
        "package_install": False,
        "network_access": False,
        "shortcut_changes": False,
        "source_changes": False,
        "config_changes": False,
        "runtime_changes": False,
        "delete_operations": [],
        "checks": {},
        "shortcuts": {},
        "launchers": [],
        "launch_chain": {},
        "desktop_source": {},
        "runtime_probes": [],
        "system_pythons": {},
        "venv": {},
        "shared_core": {},
        "findings": {},
        "failure": None,
    }

    try:
        baseline_files = []
        for relative, expected in TARGETS["known_live_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            baseline_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })

        if not all(item["ok"] for item in baseline_files):
            raise RuntimeError(
                "One or more protected FOXAI baselines changed."
            )

        receipt["checks"]["live_baselines"] = {
            "passed": True,
            "files": baseline_files,
        }

        receipt["shortcuts"] = find_matching_shortcuts()
        receipt["launchers"] = root_launcher_inventory()
        receipt["launch_chain"] = shortcut_launch_chain(
            receipt["shortcuts"]["matching_shortcuts"],
            receipt["launchers"],
        )

        desktop_source_path = ROOT / "ui/main_window.py"
        receipt["desktop_source"] = analyze_python_source(
            desktop_source_path
        )
        if receipt["desktop_source"].get("parse_error"):
            raise RuntimeError(
                "Desktop source parse failed: "
                + receipt["desktop_source"]["parse_error"]
            )

        bundled = ROOT / "env/python/python.exe"
        dot_venv = ROOT / ".venv/Scripts/python.exe"
        receipt["runtime_probes"] = [
            run_python_probe(bundled, "bundled_embedded_python"),
            run_python_probe(dot_venv, "current_dot_venv"),
        ]
        receipt["system_pythons"] = discover_system_pythons()
        receipt["venv"] = pyvenv_record(
            ROOT / ".venv/pyvenv.cfg"
        )
        receipt["shared_core"] = package_metadata_from_runtime(
            ROOT / "Runtime/Core"
        )

        receipt["findings"] = classify(
            receipt["shortcuts"],
            receipt["launchers"],
            receipt["runtime_probes"],
            receipt["system_pythons"],
            receipt["venv"],
            receipt["shared_core"],
        )

        after_files = []
        for relative, expected in TARGETS["known_live_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            after_files.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })

        if not all(item["ok"] for item in after_files):
            raise RuntimeError(
                "A protected FOXAI baseline changed during the audit."
            )

        receipt["checks"]["live_baselines_after"] = {
            "passed": True,
            "files": after_files,
        }

        receipt["state"] = "desktop_runtime_audit_verified"
        receipt["verified"] = True
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    receipt_path = report_dir / "receipt.json"
    report_path = report_dir / "report.md"

    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    write_report(receipt, report_path)

    results_zip = report_dir / "PDR3A_RESULTS.zip"
    with zipfile.ZipFile(
        results_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(receipt_path, arcname="receipt.json")
        archive.write(report_path, arcname="report.md")

    print("=" * 72)
    print("FOXAI PORTABLE DESKTOP RUNTIME PHASE 3A")
    print("READ-ONLY AUDIT")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(
        "Stable shortcut found: "
        f"{receipt.get('findings', {}).get('stable_shortcut_found', False)}"
    )
    print(f"Report: {report_dir}")
    print(f"Upload: {results_zip}")
    print("Desktop GUI launched: False")
    print("Pip/package install: False")
    print("Live files modified: False")
    print("Network access: False")

    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")

    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
