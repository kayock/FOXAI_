from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads(
    (PACKAGE / "DESIGN_TARGETS.json").read_text(encoding="utf-8")
)
REPORT_ROOT = ROOT / "Reports" / "DesktopRuntimeDesign"

STANDARD_LIBRARY = {
    "ast", "configparser", "datetime", "hashlib", "json", "os",
    "pathlib", "platform", "re", "shutil", "subprocess", "sys",
    "threading", "time", "tkinter", "uuid", "zipfile",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_shortcut(path: Path) -> dict:
    record = {
        "path": str(path),
        "exists": path.is_file(),
        "resolved": False,
    }
    if not path.is_file():
        return record

    shell = (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
        or shutil.which("pwsh.exe")
        or shutil.which("pwsh")
    )
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
        "IconLocation=$s.IconLocation"
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
            process.stderr or process.stdout or "Shortcut resolution failed."
        )[-3000:]
        return record

    record.update(json.loads(process.stdout.strip()))
    record["resolved"] = True
    return record



def normalized_windows_path(value: str) -> str:
    text = str(value or "").strip().strip('"')
    return str(Path(text)).rstrip("\\/").casefold()


def shortcut_icon_path(value: str) -> Path:
    text = str(value or "").strip().strip('"')
    text = re.sub(r",\s*-?\d+\s*$", "", text)
    return Path(text)


def find_shortcut_by_target(target: str) -> dict:
    matches = []
    inspected = []

    for path in sorted(ROOT.glob("*.lnk")):
        resolved = resolve_shortcut(path)
        inspected.append({
            "path": str(path),
            "resolved": resolved.get("resolved", False),
            "target": resolved.get("TargetPath"),
        })
        if (
            resolved.get("resolved")
            and normalized_windows_path(resolved.get("TargetPath", ""))
            == normalized_windows_path(target)
        ):
            resolved["sha256"] = sha256(path)
            matches.append(resolved)

    if len(matches) != 1:
        return {
            "resolved": False,
            "expected_target": target,
            "match_count": len(matches),
            "matches": matches,
            "inspected": inspected,
            "error": (
                "Expected exactly one FOXAI-root shortcut targeting "
                f"{target}; found {len(matches)}."
            ),
        }

    result = matches[0]
    result["match_count"] = 1
    result["inspected_shortcut_count"] = len(inspected)
    result["discovery_scope"] = str(ROOT / "*.lnk")
    return result

def analyze_python(path: Path) -> dict:
    record = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "imports": [],
        "local_imports": [],
        "external_imports": [],
        "string_paths": [],
        "parse_error": None,
    }
    if not path.is_file():
        return record

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text, filename=str(path))
    except Exception as exc:
        record["parse_error"] = f"{type(exc).__name__}: {exc}"
        return record

    imports = set()
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        ):
            value = node.value.strip()
            if (
                value
                and len(value) < 1000
                and (
                    "\\" in value
                    or "/" in value
                    or Path(value).suffix.lower()
                    in {
                        ".ico", ".png", ".json", ".ini",
                        ".db", ".sqlite", ".bat", ".exe", ".gguf",
                    }
                )
            ):
                strings.append({
                    "line": getattr(node, "lineno", None),
                    "value": value,
                })

    local = []
    external = []
    for module in sorted(imports):
        root_name = module.split(".", 1)[0]
        candidates = [
            ROOT.joinpath(*module.split(".")).with_suffix(".py"),
            ROOT.joinpath(*module.split(".")) / "__init__.py",
            ROOT / f"{root_name}.py",
        ]
        if (
            root_name in {"core", "ui"}
            or any(item.is_file() for item in candidates)
        ):
            local.append(module)
        elif root_name not in STANDARD_LIBRARY:
            external.append(module)

    record.update({
        "imports": sorted(imports),
        "local_imports": local,
        "external_imports": external,
        "string_paths": strings[:300],
        "line_count": len(text.splitlines()),
    })
    return record


def resolve_local_module(module: str) -> Path | None:
    root_name = module.split(".", 1)[0]
    candidates = [
        ROOT.joinpath(*module.split(".")).with_suffix(".py"),
        ROOT.joinpath(*module.split(".")) / "__init__.py",
        ROOT / f"{root_name}.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def dependency_closure(entrypoints: list[Path]) -> dict:
    queue = list(entrypoints)
    seen = set()
    records = []

    while queue:
        path = queue.pop(0)
        if not path.is_file():
            records.append({
                "path": str(path),
                "exists": False,
            })
            continue

        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)

        record = analyze_python(path)
        records.append(record)

        for module in record.get("local_imports", []):
            candidate = resolve_local_module(module)
            if candidate is not None:
                queue.append(candidate)

    return {
        "records": records,
        "file_count": sum(
            1 for item in records if item.get("exists", True)
        ),
        "files": [
            item["path"]
            for item in records
            if item.get("exists", True)
        ],
        "external_modules": sorted({
            module.split(".", 1)[0]
            for item in records
            for module in item.get("external_imports", [])
        }),
    }


def launcher_contract(path: Path) -> dict:
    record = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
        "launches_foxai": False,
        "launches_comfyui": False,
        "uses_system_python": False,
        "interesting_lines": [],
    }
    if not path.is_file():
        return record

    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), start=1):
        lower = line.casefold()
        if any(
            token in lower
            for token in (
                "python", "foxai.py", "comfyui",
                "main.py --cpu", "cd /d", "start ",
            )
        ):
            record["interesting_lines"].append({
                "line": number,
                "text": line,
            })

    record["launches_foxai"] = "foxai.py" in text.casefold()
    record["launches_comfyui"] = (
        "comfyui" in text.casefold()
        and "main.py --cpu" in text.casefold()
    )
    record["uses_system_python"] = bool(
        re.search(r"(?i)(^|\s)python(\.exe)?(\s|$)", text)
    )
    return record


def probe_stable_python() -> dict:
    cmd = shutil.which("cmd.exe") or shutil.which("cmd")
    if not cmd:
        return {
            "passed": False,
            "error": "cmd.exe was not found.",
        }

    probe_path = PACKAGE / "probe_host_runtime.py"
    command = (
        f'cd /d "{ROOT}" && '
        f'python -s "{probe_path}"'
    )
    env = os.environ.copy()
    env.pop("PYTHONNOUSERSITE", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    process = subprocess.run(
        [cmd, "/d", "/s", "/c", command],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )

    result = {
        "passed": False,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    if process.returncode != 0:
        return result

    lines = [
        line.strip()
        for line in process.stdout.splitlines()
        if line.strip().startswith("{")
    ]
    if not lines:
        result["error"] = "The host Python probe returned no JSON."
        return result

    result["data"] = json.loads(lines[-1])
    result["passed"] = True
    return result


def launcher_templates() -> dict:
    diagnostic_lines = [
        "@echo off",
        "setlocal",
        "title FOXAI Desktop Portable - Diagnostic",
        'cd /d "%~dp0"',
        "",
        'set "PYTHONNOUSERSITE=1"',
        'set "PYTHONDONTWRITEBYTECODE=1"',
        'set "PYTHONHOME=%~dp0Runtime\\Desktop\\python"',
        'set "TCL_LIBRARY=%~dp0Runtime\\Desktop\\python\\tcl\\tcl8.6"',
        'set "TK_LIBRARY=%~dp0Runtime\\Desktop\\python\\tcl\\tk8.6"',
        "",
        'set "PYTHON=%~dp0Runtime\\Desktop\\python\\python.exe"',
        'if not exist "%PYTHON%" (',
        "  echo [STOPPED] Portable Desktop Python was not found:",
        "  echo %PYTHON%",
        "  pause",
        "  exit /b 2",
        ")",
        "",
        '"%PYTHON%" -s "%~dp0foxai.py"',
        'set "RESULT=%ERRORLEVEL%"',
        "echo.",
        "echo FOXAI Desktop exited with code %RESULT%.",
        "pause",
        "exit /b %RESULT%",
        "",
    ]

    normal_lines = [
        "@echo off",
        "setlocal",
        'cd /d "%~dp0"',
        "",
        'set "PYTHONNOUSERSITE=1"',
        'set "PYTHONDONTWRITEBYTECODE=1"',
        'set "PYTHONHOME=%~dp0Runtime\\Desktop\\python"',
        'set "TCL_LIBRARY=%~dp0Runtime\\Desktop\\python\\tcl\\tcl8.6"',
        'set "TK_LIBRARY=%~dp0Runtime\\Desktop\\python\\tcl\\tk8.6"',
        "",
        'set "PYTHON=%~dp0Runtime\\Desktop\\python\\pythonw.exe"',
        'if not exist "%PYTHON%" (',
        "  echo Portable Desktop Python is missing.",
        "  pause",
        "  exit /b 2",
        ")",
        "",
        'start "" "%PYTHON%" -s "%~dp0foxai.py"',
        "",
    ]

    return {
        "diagnostic": "\r\n".join(diagnostic_lines),
        "normal": "\r\n".join(normal_lines),
    }


def build_design(
    launcher: dict,
    shortcuts: dict,
    icons: dict,
    closure: dict,
    host_probe: dict,
) -> dict:
    data = host_probe.get("data") or {}
    packages = data.get("packages") or {}

    blockers = []
    if not host_probe.get("passed"):
        blockers.append(
            "The exact `python` command used by the stable launcher "
            "could not be probed."
        )
    if not data.get("tk", {}).get("available"):
        blockers.append(
            "The stable launcher's Python does not expose Tcl/Tk."
        )
    for name in ("customtkinter", "PIL"):
        if not packages.get(name, {}).get("available"):
            blockers.append(
                f"The stable launcher's Python does not expose {name}."
            )
    if not launcher.get("launches_foxai"):
        blockers.append(
            "The protected launcher no longer clearly launches foxai.py."
        )

    desktop_packages = {
        "customtkinter": packages.get("customtkinter"),
        "Pillow": packages.get("PIL"),
    }
    shared_candidates = {
        name: packages.get(name)
        for name in (
            "psutil",
            "requests",
            "casbin",
            "watchdog",
            "pluggy",
        )
    }

    proposed = TARGETS["proposed_layout"]

    return {
        "state": (
            "exact_design_ready"
            if not blockers
            else "exact_design_ready_with_blockers"
        ),
        "blockers": blockers,
        "stable_chain": {
            "launcher": launcher,
            "shortcuts": shortcuts,
            "icons": icons,
        },
        "dependency_closure": closure,
        "external_modules": closure["external_modules"],
        "desktop_packages": desktop_packages,
        "shared_core_candidates": shared_candidates,
        "host_runtime": {
            "executable": data.get("executable"),
            "version": data.get("version"),
            "prefix": data.get("prefix"),
            "base_prefix": data.get("base_prefix"),
            "tk": data.get("tk"),
            "components": data.get("runtime_components", []),
        },
        "portable_layout": proposed,
        "launcher_templates": launcher_templates(),
        "later_apply_scope": {
            "added": [
                r"Runtime\Desktop\python\**",
                r"Runtime\Desktop\site-packages\**",
                proposed["manifest"],
                proposed["diagnostic_launcher"],
                proposed["normal_launcher"],
            ],
            "modified": [],
            "deleted": [],
        },
        "verification_gates": [
            "Every protected Desktop and WebUI baseline matches.",
            "Portable Python is CPython 3.14.6 AMD64.",
            "Portable Python imports tkinter and creates a Tcl interpreter.",
            "Portable Python imports CustomTkinter and Pillow from USB.",
            "Shared packages resolve only from approved USB runtime paths.",
            "All dependency-closure Python files compile.",
            "The diagnostic launcher opens FOXAI without system Python.",
            "The stable launcher and both existing shortcuts remain unchanged.",
            "No model or ComfyUI process starts without operator action.",
            "Boundary Watch remains 5/5.",
        ],
        "next_phase": {
            "name": "Portable Desktop Runtime Phase 3C",
            "purpose": (
                "Quarantined acquisition of the complete CPython/Tcl-Tk "
                "runtime and exact Desktop wheels."
            ),
            "network_required": True,
            "live_install": False,
        },
    }


def write_report(receipt: dict, path: Path) -> None:
    design = receipt.get("design", {})
    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3B",
        "## Exact Portable-Runtime Design",
        "",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        "- Live files modified: **False**",
        "- Desktop launched: **False**",
        "- Packages installed: **False**",
        "- Network access: **False**",
        "",
        "## Protected stable chain",
        "",
        "- `Launch FOXAI Workshop.bat - Shortcut.lnk`",
        "- `Launch FOXAI Workshop.bat`",
        "- `foxai.py`",
        "- `Icons\\foxai_fixed.ico`",
        "",
        "The stable shortcut and launcher remain unchanged.",
        "",
        "## Proposed portable layout",
        "",
        "```text",
        "Runtime\\Desktop\\python\\",
        "Runtime\\Desktop\\site-packages\\",
        "Runtime\\Desktop\\DESKTOP_RUNTIME_MANIFEST.json",
        "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat",
        "START_FOXAI_DESKTOP_PORTABLE.bat",
        "```",
        "",
        "## Desktop-only packages",
        "",
    ]

    for name, item in design.get("desktop_packages", {}).items():
        version = item.get("version") if item else "unresolved"
        lines.append(f"- {name}: `{version}`")

    lines += ["", "## Reusable portable core", ""]
    for name, item in design.get(
        "shared_core_candidates",
        {},
    ).items():
        version = item.get("version") if item else "unresolved"
        lines.append(f"- {name}: `{version}`")

    closure = design.get("dependency_closure", {})
    lines += [
        "",
        "## Dependency closure",
        "",
        f"- Local Python files: **{closure.get('file_count', 0)}**",
        "- External module roots:",
    ]
    for module in design.get("external_modules", []):
        lines.append(f"  - `{module}`")

    scope = design.get("later_apply_scope", {})
    lines += [
        "",
        "## Later apply scope",
        "",
        "Modified existing files: **None**",
        "",
        "Added:",
    ]
    for item in scope.get("added", []):
        lines.append(f"- `{item}`")

    lines += [
        "",
        "Deleted: **None**",
        "",
        "## Verification gates",
        "",
    ]
    for item in design.get("verification_gates", []):
        lines.append(f"- {item}")

    blockers = design.get("blockers", [])
    if blockers:
        lines += ["", "## Blockers", ""]
        for item in blockers:
            lines.append(f"- {item}")

    lines += [
        "",
        "## Next",
        "",
        "**Phase 3C — Quarantined Desktop Runtime Acquisition**",
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
    stamp = datetime.now(timezone.utc).strftime("PDR3B_%Y%m%dT%H%M%SZ")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    receipt = {
        "action": "foxai_portable_desktop_runtime_phase3b_design",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "read_only": True,
        "apply_capability_present": False,
        "live_files_modified": False,
        "desktop_gui_launched": False,
        "package_install": False,
        "network_access": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "runtime_changes": False,
        "checks": {},
        "shortcut_contract": {},
        "launcher_contract": {},
        "dependency_closure": {},
        "host_runtime_probe": {},
        "design": {},
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
                "One or more protected Desktop/WebUI baselines changed."
            )
        receipt["checks"]["live_baselines"] = {
            "passed": True,
            "files": baseline_files,
        }

        desktop_expected = TARGETS["stable_desktop"]["shortcut"]
        web_expected = TARGETS["protected_web"]["shortcut"]
        discovery = TARGETS["shortcut_discovery"]

        desktop_shortcut = find_shortcut_by_target(
            discovery["desktop_target"]
        )
        web_shortcut = find_shortcut_by_target(
            discovery["web_target"]
        )
        receipt["shortcut_contract"] = {
            "desktop": desktop_shortcut,
            "web": web_shortcut,
        }

        expected_root = normalized_windows_path(
            discovery["require_working_directory"]
        )
        expected_icon_parent = normalized_windows_path(
            discovery["required_icon_parent"]
        )

        desktop_icon = shortcut_icon_path(
            desktop_shortcut.get("IconLocation", "")
        )
        web_icon = shortcut_icon_path(
            web_shortcut.get("IconLocation", "")
        )

        checks = {
            "desktop_resolved": desktop_shortcut.get("resolved") is True,
            "desktop_unique_target_match": (
                desktop_shortcut.get("match_count") == 1
            ),
            "desktop_target": (
                normalized_windows_path(
                    desktop_shortcut.get("TargetPath", "")
                )
                == normalized_windows_path(discovery["desktop_target"])
            ),
            "desktop_working_directory": (
                normalized_windows_path(
                    desktop_shortcut.get("WorkingDirectory", "")
                )
                == expected_root
            ),
            "desktop_icon_is_usb_owned": (
                normalized_windows_path(desktop_icon.parent)
                == expected_icon_parent
            ),
            "desktop_icon_exists": desktop_icon.is_file(),
            "web_resolved": web_shortcut.get("resolved") is True,
            "web_unique_target_match": (
                web_shortcut.get("match_count") == 1
            ),
            "web_target": (
                normalized_windows_path(
                    web_shortcut.get("TargetPath", "")
                )
                == normalized_windows_path(discovery["web_target"])
            ),
            "web_working_directory": (
                normalized_windows_path(
                    web_shortcut.get("WorkingDirectory", "")
                )
                == expected_root
            ),
            "web_icon_is_usb_owned": (
                normalized_windows_path(web_icon.parent)
                == expected_icon_parent
            ),
            "web_icon_exists": web_icon.is_file(),
        }

        if not all(checks.values()):
            failed = [
                name for name, passed in checks.items() if not passed
            ]
            raise RuntimeError(
                "Protected shortcut discovery or validation failed: "
                + ", ".join(failed)
            )

        icons = {
            "desktop": {
                "path": str(desktop_icon),
                "exists": True,
                "sha256": sha256(desktop_icon),
            },
            "web": {
                "path": str(web_icon),
                "exists": True,
                "sha256": sha256(web_icon),
            },
        }

        receipt["checks"]["shortcut_contract"] = {
            "passed": True,
            "checks": checks,
            "icons": icons,
            "desktop_shortcut_filename": Path(
                desktop_shortcut["path"]
            ).name,
            "web_shortcut_filename": Path(
                web_shortcut["path"]
            ).name,
            "note": (
                "Shortcuts were identified by exact BAT target rather than "
                "by display filename."
            ),
        }

        launcher = launcher_contract(
            ROOT / "Launch FOXAI Workshop.bat"
        )
        receipt["launcher_contract"] = launcher

        entrypoints = [
            ROOT / "foxai.py",
            ROOT / "ui/main_window.py",
        ]
        missing = [str(item) for item in entrypoints if not item.is_file()]
        if missing:
            raise RuntimeError(
                "Desktop entrypoints are missing: " + ", ".join(missing)
            )

        closure = dependency_closure(entrypoints)
        receipt["dependency_closure"] = closure

        parse_errors = [
            item for item in closure["records"]
            if item.get("parse_error")
        ]
        if parse_errors:
            raise RuntimeError(
                "One or more Desktop dependency files failed parsing."
            )

        host_probe = probe_stable_python()
        receipt["host_runtime_probe"] = host_probe

        design = build_design(
            launcher,
            receipt["shortcut_contract"],
            icons,
            closure,
            host_probe,
        )
        receipt["design"] = design
        receipt["state"] = (
            "exact_design_verified"
            if not design["blockers"]
            else "exact_design_verified_with_blockers"
        )
        receipt["verified"] = True

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
                "A protected baseline changed during Phase 3B."
            )
        receipt["checks"]["live_baselines_after"] = {
            "passed": True,
            "files": after_files,
        }
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

    results_zip = report_dir / "PDR3B_RESULTS.zip"
    with zipfile.ZipFile(
        results_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(receipt_path, arcname="receipt.json")
        archive.write(report_path, arcname="report.md")

    print("=" * 72)
    print("FOXAI PORTABLE DESKTOP RUNTIME PHASE 3B")
    print("EXACT DESIGN")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(f"Report: {report_dir}")
    print(f"Upload: {results_zip}")
    print("Stable launcher modified: False")
    print("Stable shortcut modified: False")
    print("Desktop GUI launched: False")
    print("Packages installed: False")
    print("Network access: False")

    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")

    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
