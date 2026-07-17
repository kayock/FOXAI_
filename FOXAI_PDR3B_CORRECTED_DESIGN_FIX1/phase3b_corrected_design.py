from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}

EXCLUDED_TOP_LEVEL = {
    ".git", ".venv", "Backups", "ComfyUI", "Models", "Runtime", "Wheelhouse",
    "Reports", "design_output", "probe_output", "__pycache__",
}
MODULE_TO_DIST = {
    "PIL": "Pillow",
    "customtkinter": "customtkinter",
    "psutil": "psutil",
    "requests": "requests",
    "casbin": "pycasbin",
    "watchdog": "watchdog",
    "pluggy": "pluggy",
}
CORE_MODULES = {
    "psutil", "requests", "casbin", "watchdog", "pluggy",
    "charset_normalizer", "idna", "urllib3", "certifi",
    "simpleeval", "wcmatch", "bracex",
}
DESKTOP_DIRECT_MODULES = {"customtkinter", "PIL"}
SPECIAL_STDLIB_RUNTIME = {"tkinter"}

def utc_now():
    return dt.datetime.now(dt.timezone.utc)

def sha256_file(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalize(path: str | Path):
    try:
        return str(Path(path).resolve())
    except Exception:
        return os.path.normpath(str(path))

def path_inside(path: str | Path | None, parent: str | Path):
    if not path:
        return False
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False

def snapshot_baselines(root: Path):
    rows = []
    for relative, expected in sorted(EXPECTED_BASELINES.items()):
        full = root / Path(relative)
        actual = sha256_file(full)
        rows.append({
            "path": relative,
            "full_path": str(full),
            "exists": full.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    return rows

def baseline_passed(rows):
    return len(rows) == len(EXPECTED_BASELINES) and all(row["matches_expected"] for row in rows)

def resolve_shortcuts(bundle: Path, root: Path, output: Path):
    usb_root = Path(root.anchor)
    desktop_shortcut = usb_root / "Launch FOXAI Workshop.bat - Shortcut.lnk"
    web_shortcut = usb_root / "START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk"
    helper = bundle / "resolve_exact_shortcuts.ps1"
    command = [
        "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(helper),
        "-DesktopShortcut", str(desktop_shortcut),
        "-WebShortcut", str(web_shortcut),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    record = {
        "command": command,
        "returncode": result.returncode,
        "stderr": result.stderr.strip(),
        "stdout": result.stdout.strip(),
        "desktop_shortcut_expected_path": str(desktop_shortcut),
        "web_shortcut_expected_path": str(web_shortcut),
    }
    if result.returncode != 0:
        record["error"] = "PowerShell shortcut resolver returned a nonzero exit code."
        return record
    try:
        record["resolved"] = json.loads(result.stdout)
    except Exception as exc:
        record["error"] = f"Shortcut JSON parse failed: {type(exc).__name__}: {exc}"
    (output / "SHORTCUT_CONTRACT_RAW.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return record

def validate_shortcut_contract(shortcut_data, root: Path):
    usb_root = Path(root.anchor)
    expected = {
        "desktop": root / "Launch FOXAI Workshop.bat",
        "web": root / "START_FOXAI_WEB_PORTABLE.bat",
    }
    checks = []
    details = {}

    resolved_group = shortcut_data.get("resolved") or {}
    for key in ("desktop", "web"):
        rec = resolved_group.get(key) or {}
        target = rec.get("target") or ""
        working = rec.get("working_directory") or ""
        icon = rec.get("icon_path") or ""
        expected_target = expected[key]

        target_ok = bool(rec.get("resolved")) and os.path.normcase(normalize(target)) == os.path.normcase(normalize(expected_target))
        working_ok = (
            not working
            or os.path.normcase(normalize(working)) == os.path.normcase(normalize(root))
        )
        icon_ok = (
            not icon
            or (Path(icon).is_file() and path_inside(icon, usb_root))
        )
        unchanged = bool(rec.get("hash_unchanged"))

        details[key] = {
            **rec,
            "expected_target": str(expected_target),
            "target_ok": target_ok,
            "working_directory_ok": working_ok,
            "icon_contract": (
                "default_target_icon" if not icon
                else "explicit_usb_owned_icon" if icon_ok
                else "explicit_icon_not_verified"
            ),
            "icon_ok": icon_ok,
        }
        checks.extend([
            {"id": f"{key}_shortcut_resolved", "ok": bool(rec.get("resolved")), "detail": rec.get("error")},
            {"id": f"{key}_target_exact", "ok": target_ok, "detail": target},
            {"id": f"{key}_working_directory_safe", "ok": working_ok, "detail": working or "(blank; target directory applies)"},
            {"id": f"{key}_icon_safe", "ok": icon_ok, "detail": icon or "(blank; target icon applies)"},
            {"id": f"{key}_shortcut_hash_unchanged", "ok": unchanged, "detail": rec.get("hash_after")},
        ])
    return {"passed": all(c["ok"] for c in checks), "checks": checks, "details": details}

def read_text_evidence(path: Path):
    before = sha256_file(path)
    item = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256_before": before,
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "content": None,
        "read_error": None,
    }
    if path.is_file():
        try:
            item["content"] = path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            item["read_error"] = f"{type(exc).__name__}: {exc}"
    item["sha256_after"] = sha256_file(path)
    item["hash_unchanged"] = item["sha256_before"] == item["sha256_after"]
    return item

def launcher_contract(root: Path):
    files = [
        root / "Launch FOXAI Workshop.bat",
        root / "START_FOXAI_WEB_PORTABLE.bat",
        root / "foxai.py",
        root / "Create Desktop Shortcut.ps1",
    ]
    evidence = {p.name: read_text_evidence(p) for p in files}
    desktop_text = evidence["Launch FOXAI Workshop.bat"].get("content") or ""
    lower = desktop_text.lower()
    python_lines = [
        line.strip()
        for line in desktop_text.splitlines()
        if re.search(r"(?i)\bpython(?:\.exe)?\b|\bpy\s+-\d", line)
    ]
    foxai_lines = [
        line.strip()
        for line in desktop_text.splitlines()
        if "foxai.py" in line.lower() or "foxai_desktop.py" in line.lower()
    ]
    comfy_lines = [
        line.strip()
        for line in desktop_text.splitlines()
        if "comfyui" in line.lower() or "main.py --cpu" in line.lower()
    ]
    result = {
        "evidence": evidence,
        "desktop_python_lines": python_lines,
        "desktop_entrypoint_lines": foxai_lines,
        "comfyui_coupling_lines": comfy_lines,
        "uses_bare_system_python": any(
            re.search(r"(?i)(^|[&\s])python(?:\.exe)?\s+", line)
            and "env\\python" not in line.lower()
            and "runtime\\desktop" not in line.lower()
            for line in python_lines
        ),
        "starts_comfyui": bool(comfy_lines),
        "entrypoint": "foxai.py" if "foxai.py" in lower else ("FoxAI_Desktop.py" if "foxai_desktop.py" in lower else None),
        "hashes_unchanged": all(item["hash_unchanged"] for item in evidence.values()),
    }
    result["passed"] = (
        evidence["Launch FOXAI Workshop.bat"]["exists"]
        and evidence["foxai.py"]["exists"]
        and result["entrypoint"] is not None
        and result["hashes_unchanged"]
    )
    return result

def module_candidates(root: Path, current_file: Path, module: str, level: int):
    parts = module.split(".") if module else []
    if level:
        base = current_file.parent
        for _ in range(max(level - 1, 0)):
            base = base.parent
    else:
        base = root

    if parts:
        path_base = base.joinpath(*parts)
        yield path_base.with_suffix(".py")
        yield path_base / "__init__.py"
    elif level:
        yield base / "__init__.py"

def is_excluded(path: Path, root: Path):
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        return True
    return bool(rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL)

def parse_imports(path: Path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    tree = ast.parse(text, filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "level": 0, "kind": "import"})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append({
                "module": module,
                "level": int(node.level or 0),
                "kind": "from",
                "names": [alias.name for alias in node.names],
            })
    return imports

def resolve_local_import(root: Path, current_file: Path, item):
    module = item.get("module") or ""
    level = int(item.get("level") or 0)
    candidates = list(module_candidates(root, current_file, module, level))
    for candidate in candidates:
        if candidate.is_file() and not is_excluded(candidate, root):
            return candidate.resolve()

    # "from package import child" may point to package/child.py.
    if item.get("kind") == "from":
        if level:
            base = current_file.parent
            for _ in range(max(level - 1, 0)):
                base = base.parent
        else:
            base = root
        if module:
            base = base.joinpath(*module.split("."))
        for name in item.get("names") or []:
            if name == "*":
                continue
            for candidate in (base / f"{name}.py", base / name / "__init__.py"):
                if candidate.is_file() and not is_excluded(candidate, root):
                    return candidate.resolve()
    return None

def dependency_closure(root: Path, entrypoint: Path):
    queue = [entrypoint.resolve()]
    visited = set()
    files = []
    external_roots = set()
    parse_errors = []
    edges = []

    stdlib = set(getattr(sys, "stdlib_module_names", ()))

    while queue:
        path = queue.pop(0)
        key = os.path.normcase(str(path))
        if key in visited:
            continue
        visited.add(key)

        if is_excluded(path, root):
            continue
        try:
            imports = parse_imports(path)
        except Exception as exc:
            parse_errors.append({
                "path": str(path),
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        rel = str(path.relative_to(root)).replace("\\", "/")
        record = {
            "path": rel,
            "sha256": sha256_file(path),
            "imports": imports,
        }
        files.append(record)

        for item in imports:
            local = resolve_local_import(root, path, item)
            module = item.get("module") or ""
            top = module.split(".")[0] if module else ""
            if local:
                edges.append({"from": rel, "module": module, "to": str(local.relative_to(root)).replace("\\", "/")})
                queue.append(local)
            elif top and top not in stdlib and top not in {"core", "ui"}:
                external_roots.add(top)

    external_roots = sorted(external_roots)
    return {
        "entrypoint": str(entrypoint.relative_to(root)).replace("\\", "/"),
        "local_file_count": len(files),
        "local_files": sorted(files, key=lambda x: x["path"].lower()),
        "edges": edges,
        "external_module_roots": external_roots,
        "special_stdlib_runtime_requirements": sorted(SPECIAL_STDLIB_RUNTIME & {
            (item.get("module") or "").split(".")[0]
            for file in files
            for item in file["imports"]
        }),
        "parse_errors": parse_errors,
        "passed": bool(files) and not parse_errors,
    }

def write_host_inspector(output: Path, bundle: Path):
    source = (bundle / "host_runtime_inspector.py").read_text(encoding="utf-8")
    target = output / "host_runtime_inspector.py"
    target.write_text(source, encoding="utf-8")
    return target

def run_python_inspector(candidate: Path, inspector: Path, isolated: bool, timeout: int = 15):
    command = [str(candidate)]
    if isolated:
        command.append("-s")
    command.append(str(inspector))
    env = os.environ.copy()
    if isolated:
        env["PYTHONNOUSERSITE"] = "1"
        env.pop("PYTHONPATH", None)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "candidate": str(candidate),
            "command": command,
            "runs": False,
            "timeout": True,
            "error": f"Timed out after {timeout} seconds.",
        }
    record = {
        "candidate": str(candidate),
        "command": command,
        "runs": result.returncode == 0,
        "returncode": result.returncode,
        "stderr": result.stderr.strip(),
    }
    if result.returncode == 0:
        try:
            record["inspection"] = json.loads(result.stdout)
        except Exception as exc:
            record["runs"] = False
            record["error"] = f"Inspector JSON parse failed: {type(exc).__name__}: {exc}"
            record["stdout"] = result.stdout[:4000]
    else:
        record["stdout"] = result.stdout[:4000]
    return record

def host_python_candidates(root: Path):
    candidates = []
    seen = set()

    def add(value):
        if not value:
            return
        p = Path(value)
        key = os.path.normcase(str(p))
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    try:
        result = subprocess.run(
            ["where.exe", "python"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                add(line.strip())
    except Exception:
        pass

    cfg = root / ".venv" / "pyvenv.cfg"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8-sig", errors="replace")
        for line in text.splitlines():
            if line.lower().startswith("home"):
                home = line.split("=", 1)[-1].strip()
                add(Path(home) / "python.exe")

    localapp = os.environ.get("LOCALAPPDATA")
    if localapp:
        base = Path(localapp)
        add(base / "Python" / "pythoncore-3.14-64" / "python.exe")
        add(base / "Programs" / "Python" / "Python314" / "python.exe")
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        add(Path(program_files) / "Python314" / "python.exe")
    add(root / ".venv" / "Scripts" / "python.exe")

    return candidates[:6]

def probe_runtimes(root: Path, bundle: Path, output: Path):
    inspector = write_host_inspector(output, bundle)

    embedded = root / "env" / "python" / "python.exe"
    embedded_record = run_python_inspector(embedded, inspector, isolated=True)

    candidates = host_python_candidates(root)
    host_results = []
    selected = None
    for candidate in candidates:
        if not candidate.is_file():
            host_results.append({"candidate": str(candidate), "exists": False, "runs": False})
            continue
        record = run_python_inspector(candidate, inspector, isolated=False)
        record["exists"] = True
        host_results.append(record)
        if record.get("runs") and selected is None:
            selected = record
            # The launcher uses the first working bare `python` candidate.
            break

    return {
        "embedded_usb_runtime": embedded_record,
        "host_candidates_considered": [str(x) for x in candidates],
        "host_results": host_results,
        "selected_host_runtime": selected,
    }

def module_available(runtime_record, module):
    inspection = runtime_record.get("inspection") or {}
    return bool(((inspection.get("modules") or {}).get(module) or {}).get("available"))

def module_origin(runtime_record, module):
    inspection = runtime_record.get("inspection") or {}
    return ((inspection.get("modules") or {}).get(module) or {}).get("origin")

def build_design(root: Path, launcher, closure, runtime_probe):
    embedded = runtime_probe.get("embedded_usb_runtime") or {}
    selected = runtime_probe.get("selected_host_runtime") or {}
    selected_inspection = selected.get("inspection") or {}
    selected_modules = selected_inspection.get("modules") or {}

    external = set(closure.get("external_module_roots") or [])
    core_reusable = sorted(external & CORE_MODULES)
    desktop_direct_modules = sorted(external & DESKTOP_DIRECT_MODULES)
    desktop_distributions = []

    for module in desktop_direct_modules:
        info = selected_modules.get(module) or {}
        dist_name = info.get("distribution") or MODULE_TO_DIST.get(module) or module
        version = info.get("version")
        active_reqs = info.get("active_requirements") or []
        desktop_distributions.append({
            "module": module,
            "distribution": dist_name,
            "version": version,
            "pin": f"{dist_name}=={version}" if version else dist_name,
            "active_requirements": active_reqs,
            "origin": info.get("origin"),
        })

    transitive = {}
    for item in desktop_distributions:
        for req in item.get("active_requirements") or []:
            name = req.get("name")
            if name:
                transitive[name.lower()] = req

    host_tk = module_available(selected, "tkinter")
    embedded_tk = module_available(embedded, "tkinter")
    full_checks = selected_inspection.get("full_runtime_checks") or {}
    full_runtime_ready = bool(host_tk and all(full_checks.get(k) for k in (
        "python_exe", "python_dll", "dlls_dir", "tkinter_package", "tkinter_extension", "tcl_dir"
    )))

    architecture = {
        "principle": "Portable First, Host Enhanced",
        "desktop_runtime_strategy": (
            "Create a dedicated USB-owned full Windows Python runtime under Runtime/Desktop/python. "
            "The current embedded core Python cannot be the Desktop interpreter because it lacks tkinter/Tcl/Tk."
        ),
        "core_reuse_strategy": (
            "Reuse Runtime/Core/site-packages for shared packages. Do not duplicate psutil, requests, "
            "pycasbin/casbin, watchdog, pluggy, or their verified dependencies in the Desktop-only layer."
        ),
        "desktop_layer_strategy": (
            "Place only Desktop-specific Python packages and their active Windows dependencies under "
            "Runtime/Desktop/site-packages."
        ),
        "creative_runtime_boundary": (
            "Do not include ComfyUI, torch, torchvision, torchaudio, numpy, or other Creative Studio "
            "dependencies in the Desktop runtime. The new portable Desktop launcher must not start ComfyUI."
        ),
        "stable_chain_policy": (
            "Do not modify the existing USB-root shortcuts or Launch FOXAI Workshop.bat during Phase 3C. "
            "Build and verify new launchers beside the stable chain first."
        ),
        "host_runtime_role": (
            "The host may serve as a quarantined acquisition source and diagnostic reference. "
            "The finished Desktop boot chain must not borrow host Python or user-site packages."
        ),
    }

    proposed_layout = [
        "Runtime/Desktop/python/**",
        "Runtime/Desktop/site-packages/**",
        "Runtime/Desktop/DESKTOP_RUNTIME_MANIFEST.json",
        "START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat",
        "START_FOXAI_DESKTOP_PORTABLE.bat",
    ]
    later_scope = {
        "new_paths": proposed_layout,
        "modified_existing_files": [],
        "deleted_files": [],
        "explicit_non_changes": [
            "Z:\\Launch FOXAI Workshop.bat - Shortcut.lnk",
            "Z:\\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk",
            "Launch FOXAI Workshop.bat",
            "START_FOXAI_WEB_PORTABLE.bat",
            "foxai.py",
            "ui/main_window.py",
            "Runtime/Core/**",
            "ComfyUI/**",
            "Models/**",
            "Config/fleet_registry.json",
            "Config/model_sources.json",
        ],
    }

    acquisition = {
        "phase": "Phase 3C - Quarantined Desktop Runtime Acquisition",
        "network_or_install_in_phase3b": False,
        "host_runtime_candidate": {
            "executable": selected_inspection.get("executable"),
            "base_prefix": selected_inspection.get("base_prefix"),
            "version": selected_inspection.get("version"),
            "full_runtime_checks": full_checks,
            "suitable_as_quarantine_source_candidate": full_runtime_ready,
        },
        "desktop_direct_distributions": desktop_distributions,
        "active_transitive_requirements": sorted(transitive.values(), key=lambda x: x.get("name", "").lower()),
        "shared_core_modules": core_reusable,
        "rule": (
            "Phase 3C may copy or acquire only into a quarantine directory. It must hash every file, "
            "build manifests, run isolated imports, and make no live launcher or shortcut changes."
        ),
    }

    verification_gates = [
        {
            "id": "desktop_python_usb_owned",
            "requirement": "The Desktop interpreter and base_prefix resolve under Runtime/Desktop/python.",
        },
        {
            "id": "user_site_disabled",
            "requirement": "PYTHONNOUSERSITE=1 and `-s` are effective; no user-site directory appears in sys.path.",
        },
        {
            "id": "tkinter_complete",
            "requirement": "tkinter imports from the USB runtime and the Tcl/Tk directories plus _tkinter.pyd are present.",
        },
        {
            "id": "desktop_import_origins",
            "requirement": "customtkinter and PIL import from Runtime/Desktop/site-packages.",
        },
        {
            "id": "shared_core_import_origins",
            "requirement": "Shared packages import only from Runtime/Core/site-packages.",
        },
        {
            "id": "local_dependency_compile",
            "requirement": "Every Python file in the foxai.py dependency closure compiles with the candidate runtime.",
        },
        {
            "id": "diagnostic_launcher_no_fallback",
            "requirement": "The candidate launcher uses only Runtime/Desktop/python/python.exe and has no system-Python fallback.",
        },
        {
            "id": "no_comfyui_coupling",
            "requirement": "The candidate Desktop launcher contains no ComfyUI or torch launch command.",
        },
        {
            "id": "no_pip_or_network",
            "requirement": "The live launcher performs no pip install, package download, or network acquisition.",
        },
        {
            "id": "stable_chain_unchanged",
            "requirement": "The existing shortcuts, Launch FOXAI Workshop.bat, web launcher, and protected baseline hashes remain unchanged.",
        },
    ]

    blockers = []
    if not host_tk:
        blockers.append("No working host Python with tkinter was identified as a possible quarantined full-runtime source.")
    if not full_runtime_ready:
        blockers.append("The selected host Python did not prove all required Tcl/Tk/full-runtime files.")
    if not desktop_direct_modules:
        blockers.append("The dependency closure did not identify customtkinter/PIL; source closure may be incomplete.")
    if launcher.get("entrypoint") != "foxai.py":
        blockers.append("The stable desktop launcher entrypoint was not resolved to foxai.py.")

    return {
        "architecture": architecture,
        "observed_runtime_facts": {
            "embedded_tkinter_available": embedded_tk,
            "host_tkinter_available": host_tk,
            "current_launcher_uses_bare_system_python": launcher.get("uses_bare_system_python"),
            "current_launcher_starts_comfyui": launcher.get("starts_comfyui"),
        },
        "dependency_classification": {
            "external_module_roots": sorted(external),
            "shared_core_modules": core_reusable,
            "desktop_direct_modules": desktop_direct_modules,
            "special_stdlib_runtime_requirements": closure.get("special_stdlib_runtime_requirements") or [],
        },
        "proposed_layout": proposed_layout,
        "later_apply_scope": later_scope,
        "acquisition_plan": acquisition,
        "verification_gates": verification_gates,
        "blockers": blockers,
        "design_ready_for_phase3c": not blockers,
    }

def markdown_report(receipt):
    shortcut = receipt.get("shortcut_contract") or {}
    launcher = receipt.get("launcher_contract") or {}
    closure = receipt.get("dependency_closure") or {}
    runtimes = receipt.get("runtime_probe") or {}
    design = receipt.get("design") or {}

    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3B",
        "## Corrected Exact Portable-Runtime Design",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Read only: **True**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Live files modified: **False**",
        f"- Desktop or ComfyUI launched: **False**",
        f"- Packages installed or downloaded: **False**",
        f"- Drive recursion: **False**",
        "",
        "## Corrected shortcut contract",
        "",
    ]
    for key in ("desktop", "web"):
        item = ((shortcut.get("details") or {}).get(key) or {})
        lines += [
            f"### {key.title()}",
            f"- Shortcut: `{item.get('shortcut_path', '')}`",
            f"- Target: `{item.get('target', '')}`",
            f"- Working directory: `{item.get('working_directory') or '(blank; target directory applies)'}`",
            f"- Icon: `{item.get('icon_path') or '(blank; target icon applies)'}`",
            f"- Contract valid: **{bool(item.get('target_ok') and item.get('working_directory_ok') and item.get('icon_ok'))}**",
            "",
        ]

    lines += [
        "## Existing launcher facts",
        "",
        f"- Entry point: `{launcher.get('entrypoint')}`",
        f"- Uses bare host `python`: **{launcher.get('uses_bare_system_python')}**",
        f"- Starts ComfyUI: **{launcher.get('starts_comfyui')}**",
        "- The existing stable launcher remains unchanged.",
        "",
        "## Dependency closure",
        "",
        f"- Local Python files: **{closure.get('local_file_count', 0)}**",
        f"- External module roots: `{', '.join(closure.get('external_module_roots') or [])}`",
        f"- Special runtime requirement: `{', '.join(closure.get('special_stdlib_runtime_requirements') or [])}`",
        "",
        "## Runtime conclusion",
        "",
        f"- Embedded USB tkinter available: **{((design.get('observed_runtime_facts') or {}).get('embedded_tkinter_available'))}**",
        f"- Host tkinter available: **{((design.get('observed_runtime_facts') or {}).get('host_tkinter_available'))}**",
        "",
        "**The Desktop requires its own USB-owned full Windows Python runtime with Tcl/Tk.**",
        "The small embedded Core runtime remains the WebUI/security runtime and its verified shared packages are reused.",
        "",
        "## Proposed portable layout",
        "",
        "```text",
    ]
    lines.extend(design.get("proposed_layout") or [])
    lines += [
        "```",
        "",
        "## Package split",
        "",
        f"- Shared Core: `{', '.join(((design.get('dependency_classification') or {}).get('shared_core_modules') or []))}`",
        f"- Desktop direct: `{', '.join(((design.get('dependency_classification') or {}).get('desktop_direct_modules') or []))}`",
        "",
        "## Phase 3C gate",
        "",
        f"- Design ready for Phase 3C: **{design.get('design_ready_for_phase3c')}**",
    ]
    blockers = design.get("blockers") or []
    if blockers:
        lines.append("- Blockers:")
        lines.extend(f"  - {item}" for item in blockers)
    else:
        lines.append("- No design blockers found.")
        lines.append("- Phase 3C may acquire into quarantine only; no live apply is authorized.")
    lines += [
        "",
        "## Safety",
        "",
        "- No shortcut, launcher, runtime, source, configuration, model, or package was modified.",
        "- No FOXAI, Desktop UI, ComfyUI process, browser, or network operation was started.",
        "- The only writes are this timestamped report and receipt inside the extracted probe bundle.",
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
    output = bundle / "design_output" / started.strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_portable_desktop_runtime_phase3b_corrected_design",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(root),
        "read_only": True,
        "recursive_drive_scan": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "runtime_changes": False,
        "delete_operations": [],
        "writes": [
            str(output / "receipt.json"),
            str(output / "report.md"),
            str(output / "SHORTCUT_CONTRACT_RAW.json"),
            str(output / "host_runtime_inspector.py"),
        ],
    }

    exit_code = 1
    try:
        before = snapshot_baselines(root)
        receipt["protected_baselines_before"] = before
        receipt["baseline_before_passed"] = baseline_passed(before)
        if not receipt["baseline_before_passed"]:
            raise RuntimeError("Protected live baseline verification failed before the design probe.")

        shortcuts_raw = resolve_shortcuts(bundle, root, output)
        shortcut_contract = validate_shortcut_contract(shortcuts_raw, root)
        receipt["shortcut_contract"] = shortcut_contract
        if not shortcut_contract["passed"]:
            failed = [c["id"] for c in shortcut_contract["checks"] if not c["ok"]]
            raise RuntimeError("Corrected exact shortcut contract failed: " + ", ".join(failed))

        launcher = launcher_contract(root)
        receipt["launcher_contract"] = launcher
        if not launcher["passed"]:
            raise RuntimeError("Existing desktop launcher chain could not be read and verified.")

        entrypoint = root / (launcher["entrypoint"] or "foxai.py")
        closure = dependency_closure(root, entrypoint)
        receipt["dependency_closure"] = closure
        if not closure["passed"]:
            raise RuntimeError("Local Python dependency closure did not complete cleanly.")

        runtimes = probe_runtimes(root, bundle, output)
        receipt["runtime_probe"] = runtimes
        if not (runtimes.get("embedded_usb_runtime") or {}).get("runs"):
            raise RuntimeError("The USB embedded Python runtime did not complete its isolated inspection.")
        if not runtimes.get("selected_host_runtime"):
            raise RuntimeError("No working host Python candidate was identified for Desktop runtime design evidence.")

        design = build_design(root, launcher, closure, runtimes)
        receipt["design"] = design
        if not design["design_ready_for_phase3c"]:
            raise RuntimeError("Exact design still has blockers: " + " | ".join(design["blockers"]))

        after = snapshot_baselines(root)
        receipt["protected_baselines_after"] = after
        receipt["baseline_after_passed"] = baseline_passed(after)
        if not receipt["baseline_after_passed"]:
            raise RuntimeError("Protected live baseline verification failed after the design probe.")

        receipt["state"] = "exact_design_verified"
        receipt["verified"] = True
        exit_code = 0
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            after = snapshot_baselines(root)
            receipt["protected_baselines_after"] = after
            receipt["baseline_after_passed"] = baseline_passed(after)
        except Exception as after_exc:
            receipt["after_snapshot_error"] = f"{type(after_exc).__name__}: {after_exc}"
    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output / "report.md").write_text(markdown_report(receipt), encoding="utf-8")
        print()
        print("Phase 3B corrected design state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Output:", output)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("Phase 3C remains quarantine-only; no live apply is authorized.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
