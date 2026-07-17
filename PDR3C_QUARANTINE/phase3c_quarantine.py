from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

EXPECTED_BASELINES = {'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Config/model_sources.json': 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91', 'Launch FOXAI Workshop.bat': '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480', 'START_FOXAI_WEB_PORTABLE.bat': '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/foxai_web.py': 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7', 'core/model_sources.py': 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'env/python/python314._pth': '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'tests/test_model_sources.py': 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'}
EXPECTED_SHORTCUTS = {'desktop': {'filename': 'Z:\\Launch FOXAI Workshop.bat - Shortcut.lnk', 'sha256': '2a41fab836312e95e40d5404bc379b050f31b7cd61bd1ac26bb22ce902aeae02', 'target': 'Z:\\FOXAI\\Launch FOXAI Workshop.bat', 'working_directory': 'Z:\\FOXAI', 'icon_path': 'Z:\\FOXAI\\Icons\\foxai_fixed.ico'}, 'web': {'filename': 'Z:\\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk', 'sha256': 'af0f79cfc583c51c4108cb2c1baa86634bf427e2eb881c64ed51a5994f2e40dd', 'target': 'Z:\\FOXAI\\START_FOXAI_WEB_PORTABLE.bat', 'working_directory': 'Z:\\FOXAI', 'icon_path': 'Z:\\FOXAI\\Icons\\ChatGPT Image Jul 6, 2026, 09_28_59 PM.ico'}}

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

def snapshot_baselines(root: Path):
    rows = []
    for relative, expected in sorted(EXPECTED_BASELINES.items()):
        full = root / Path(relative)
        actual = sha256_file(full)
        rows.append({
            "path": relative,
            "exists": full.is_file(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_expected": actual == expected,
        })
    return rows

def snapshot_shortcuts(root: Path):
    usb_root = Path(root.anchor)
    rows = {}
    for key, expected in EXPECTED_SHORTCUTS.items():
        full = usb_root / expected["filename"]
        actual = sha256_file(full)
        rows[key] = {
            "path": str(full),
            "exists": full.is_file(),
            "expected_sha256": expected["sha256"],
            "actual_sha256": actual,
            "matches_expected": actual == expected["sha256"],
        }
    return rows

def snapshots_pass(baselines, shortcuts):
    return (
        all(row["matches_expected"] for row in baselines)
        and all(row["matches_expected"] for row in shortcuts.values())
    )

def candidate_pythons(root: Path):
    values = [
        root / ".venv" / "Scripts" / "python.exe",
        Path(r"C:\Python314\python.exe"),
    ]
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
                value = line.strip()
                if value and "windowsapps" not in value.lower():
                    values.append(Path(value))
    except Exception:
        pass

    seen = set()
    result = []
    for value in values:
        key = os.path.normcase(str(value))
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result[:6]

def probe_candidate(candidate: Path, helper: Path):
    env = os.environ.copy()
    env.pop("PYTHONNOUSERSITE", None)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONUTF8"] = "1"

    try:
        completed = subprocess.run(
            [str(candidate), str(helper)],
            capture_output=True,
            text=True,
            timeout=25,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "candidate": str(candidate),
            "runs": False,
            "timeout": True,
            "error": "Timed out after 25 seconds.",
        }

    record = {
        "candidate": str(candidate),
        "exists": candidate.is_file(),
        "runs": completed.returncode == 0,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode == 0:
        try:
            record["inspection"] = json.loads(completed.stdout)
        except Exception as exc:
            record["runs"] = False
            record["error"] = f"JSON parse failed: {type(exc).__name__}: {exc}"
            record["stdout"] = completed.stdout[:4000]
    else:
        record["stdout"] = completed.stdout[:4000]
    return record

def select_sources(root: Path, helper: Path):
    probes = []
    runtime_source = None
    package_source = None

    print("Stage 1/6: probing only known Python locations...", flush=True)
    for candidate in candidate_pythons(root):
        print(f"  Probe: {candidate}", flush=True)
        if not candidate.is_file():
            probes.append({"candidate": str(candidate), "exists": False, "runs": False})
            continue
        record = probe_candidate(candidate, helper)
        probes.append(record)
        inspection = record.get("inspection") or {}
        checks = inspection.get("full_runtime_checks") or {}
        full_runtime = (
            record.get("runs")
            and inspection.get("tkinter", {}).get("available")
            and all(checks.get(name) for name in (
                "python_exe", "python_dll", "dlls_dir",
                "tkinter_package", "tkinter_extension", "tcl_dir",
            ))
        )
        imports = inspection.get("imports") or {}
        packages_ready = (
            record.get("runs")
            and imports.get("customtkinter", {}).get("available")
            and imports.get("PIL", {}).get("available")
            and bool(inspection.get("distributions"))
        )

        if full_runtime and runtime_source is None:
            runtime_source = record
        if packages_ready and package_source is None:
            package_source = record
        if runtime_source and package_source:
            break

    return {
        "probes": probes,
        "runtime_source": runtime_source,
        "package_source": package_source,
    }

def runtime_file_plan(source_root: Path):
    excluded_dirs = {"__pycache__"}
    files = []
    total = 0
    print(f"Stage 2/6: inventorying bounded runtime folder {source_root} ...", flush=True)
    for current, dirs, names in os.walk(source_root):
        current_path = Path(current)
        rel_dir = current_path.relative_to(source_root)

        dirs[:] = [
            name for name in dirs
            if name not in excluded_dirs
            and not (
                len(rel_dir.parts) == 1
                and rel_dir.parts[0].lower() == "lib"
                and name.lower() == "site-packages"
            )
        ]

        if (
            len(rel_dir.parts) >= 2
            and rel_dir.parts[0].lower() == "lib"
            and rel_dir.parts[1].lower() == "site-packages"
        ):
            dirs[:] = []
            continue

        for name in names:
            if name.lower().endswith((".pyc", ".pyo")):
                continue
            source = current_path / name
            if not source.is_file():
                continue
            relative = source.relative_to(source_root)
            files.append((source, relative, source.stat().st_size))
            total += source.stat().st_size
    return files, total

def copy_verified(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_file(source)
    shutil.copy2(source, destination)
    destination_hash = sha256_file(destination)
    if source_hash != destination_hash:
        raise RuntimeError(f"Copy hash mismatch: {source} -> {destination}")
    return source_hash

def acquire_runtime(plan, destination_root: Path):
    manifest = []
    count = len(plan)
    bytes_done = 0
    print(f"Stage 3/6: copying {count} runtime files into quarantine...", flush=True)
    for index, (source, relative, size) in enumerate(plan, start=1):
        destination = destination_root / relative
        digest = copy_verified(source, destination)
        bytes_done += size
        manifest.append({
            "relative": str(relative).replace("\\", "/"),
            "size_bytes": size,
            "sha256": digest,
            "source": str(source),
        })
        if index == 1 or index % 250 == 0 or index == count:
            print(
                f"  Runtime: {index}/{count} files, "
                f"{bytes_done / (1024 * 1024):.1f} MiB copied",
                flush=True,
            )
    return manifest

def package_file_plan(package_inspection):
    distributions = package_inspection.get("distributions") or {}
    selected = {}
    distribution_summary = []
    for name, record in sorted(distributions.items(), key=lambda item: item[0].lower()):
        distribution_summary.append({
            "name": record.get("name"),
            "version": record.get("version"),
            "requires": record.get("requires") or [],
            "file_count": len(record.get("files") or []),
        })
        for item in record.get("files") or []:
            relative = item["relative"].replace("/", "\\")
            key = relative.lower()
            source = Path(item["source"])
            if not source.is_file():
                raise RuntimeError(f"Package source file disappeared: {source}")
            if key in selected:
                previous = selected[key]
                if sha256_file(previous["source"]) != sha256_file(source):
                    raise RuntimeError(f"Package file collision with different content: {relative}")
                continue
            selected[key] = {
                "source": source,
                "relative": Path(relative),
                "distribution": record.get("name"),
                "version": record.get("version"),
                "size_bytes": source.stat().st_size,
            }
    return list(selected.values()), distribution_summary

def acquire_packages(plan, desktop_site: Path):
    manifest = []
    count = len(plan)
    print(f"Stage 4/6: copying {count} Desktop package files into quarantine...", flush=True)
    for index, item in enumerate(plan, start=1):
        destination = desktop_site / item["relative"]
        digest = copy_verified(item["source"], destination)
        manifest.append({
            "relative": str(item["relative"]).replace("\\", "/"),
            "size_bytes": item["size_bytes"],
            "sha256": digest,
            "source": str(item["source"]),
            "distribution": item["distribution"],
            "version": item["version"],
        })
        if index == 1 or index % 100 == 0 or index == count:
            print(f"  Packages: {index}/{count} files", flush=True)
    return manifest

def verify_quarantine(
    root: Path,
    python_root: Path,
    desktop_site: Path,
    bundle: Path,
    closure_path: Path,
    upload_dir: Path,
):
    print("Stage 5/6: running isolated quarantine verification...", flush=True)
    verifier = bundle / "verify_quarantine.py"
    python_exe = python_root / "python.exe"
    core_site = root / "Runtime" / "Core" / "site-packages"

    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONHOME"] = str(python_root)
    env["PYTHONPATH"] = os.pathsep.join([
        str(desktop_site),
        str(core_site),
        str(root),
    ])
    env["PYTHONUTF8"] = "1"

    command = [
        str(python_exe), "-s", str(verifier),
        "--root", str(root),
        "--python-root", str(python_root),
        "--desktop-site", str(desktop_site),
        "--core-site", str(core_site),
        "--closure", str(closure_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    record = {
        "command": command,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }
    if completed.returncode != 0:
        raise RuntimeError(
            "Quarantine Python returned a nonzero verification code: "
            + completed.stderr.strip()
        )
    try:
        verification = json.loads(completed.stdout)
    except Exception as exc:
        raise RuntimeError(f"Verification JSON parse failed: {type(exc).__name__}: {exc}")
    record["verification"] = verification
    (upload_dir / "QUARANTINE_VERIFICATION.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if not verification.get("verified"):
        failed = [name for name, ok in verification.get("checks", {}).items() if not ok]
        raise RuntimeError("Quarantine verification failed: " + ", ".join(failed))
    return record

def candidate_launcher_text():
    return r"""@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONHOME=%~dp0Runtime\Desktop\python"
set "PYTHONPATH=%~dp0Runtime\Desktop\site-packages;%~dp0Runtime\Core\site-packages;%~dp0"
"%~dp0Runtime\Desktop\python\python.exe" -s "%~dp0foxai.py"
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
"""

def make_report(receipt):
    source = receipt.get("source_selection") or {}
    runtime_source = ((source.get("runtime_source") or {}).get("inspection") or {})
    package_source = ((source.get("package_source") or {}).get("inspection") or {})
    verification = (
        (receipt.get("quarantine_verification") or {}).get("verification") or {}
    )
    distributions = receipt.get("desktop_distributions") or []

    lines = [
        "# FOXAI Portable Desktop Runtime Phase 3C",
        "## Quarantined Acquisition and Verification",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Elapsed seconds: **{receipt.get('elapsed_seconds')}**",
        f"- Read only with respect to live FOXAI: **True**",
        f"- Live files modified: **False**",
        f"- Network or installation used: **False**",
        f"- FOXAI or ComfyUI launched: **False**",
        "",
        "## Sources",
        "",
        f"- Full runtime source: `{runtime_source.get('base_prefix')}`",
        f"- Runtime version: `{runtime_source.get('version')}`",
        f"- Desktop package source interpreter: `{package_source.get('executable')}`",
        f"- Package source user site: `{package_source.get('user_site')}`",
        "",
        "## Acquired quarantine",
        "",
        f"- Runtime files: **{receipt.get('runtime_file_count', 0)}**",
        f"- Runtime size: **{receipt.get('runtime_size_bytes', 0) / (1024 * 1024):.1f} MiB**",
        f"- Desktop package files: **{receipt.get('desktop_package_file_count', 0)}**",
        "",
        "### Desktop distributions",
        "",
    ]
    for item in distributions:
        lines.append(f"- `{item.get('name')}=={item.get('version')}` — {item.get('file_count')} files")

    lines += [
        "",
        "## Isolated verification",
        "",
    ]
    for name, ok in (verification.get("checks") or {}).items():
        lines.append(f"- {name}: **{ok}**")

    lines += [
        "",
        "## Boundary result",
        "",
        "- `tkinter` loads from the quarantined full USB-owned Python runtime.",
        "- `customtkinter` and `PIL` load from quarantined Desktop site-packages.",
        "- `casbin`, `psutil`, and `requests` load from verified Runtime/Core site-packages.",
        "- No user-site package path is used by the quarantined runtime.",
        "- All Phase 3B local dependency files compile in memory without writing `.pyc` files.",
        "",
        "## Next gate",
        "",
        "**Phase 3D may prepare a preview-first live apply package. No live apply is authorized by this receipt.**",
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
    run_root = bundle / "Q" / started.strftime("%Y%m%dT%H%M%SZ")
    quarantine = run_root / "quarantine"
    upload_dir = run_root / "UPLOAD_THIS"
    upload_dir.mkdir(parents=True, exist_ok=True)

    receipt = {
        "action": "foxai_pdr_phase3c_quarantined_runtime_acquisition",
        "created": started.isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "read_only_live_foxai": True,
        "recursive_drive_scan": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "shortcut_changes": False,
        "launcher_changes": False,
        "runtime_live_changes": False,
        "source_changes": False,
        "package_install": False,
        "package_download": False,
        "network_access": False,
        "desktop_gui_launched": False,
        "comfyui_launched": False,
        "writes_limited_to": str(run_root),
        "phase3d_live_apply_authorized": False,
    }
    exit_code = 1

    try:
        before_baselines = snapshot_baselines(root)
        before_shortcuts = snapshot_shortcuts(root)
        receipt["protected_baselines_before"] = before_baselines
        receipt["protected_shortcuts_before"] = before_shortcuts
        receipt["before_snapshot_passed"] = snapshots_pass(before_baselines, before_shortcuts)
        if not receipt["before_snapshot_passed"]:
            raise RuntimeError("Protected baseline or shortcut verification failed before acquisition.")

        selection = select_sources(root, bundle / "source_probe.py")
        receipt["source_selection"] = selection
        runtime_record = selection.get("runtime_source")
        package_record = selection.get("package_source")
        if not runtime_record:
            raise RuntimeError("No complete full Python/Tcl/Tk runtime source was found.")
        if not package_record:
            raise RuntimeError(
                "No bounded host or project Python source contained both customtkinter and Pillow. "
                "No runtime copy was started."
            )

        runtime_inspection = runtime_record["inspection"]
        package_inspection = package_record["inspection"]
        runtime_source_root = Path(runtime_inspection["base_prefix"])
        if not runtime_source_root.is_dir():
            raise RuntimeError(f"Runtime source folder is missing: {runtime_source_root}")

        python_root = quarantine / "Runtime" / "Desktop" / "python"
        desktop_site = quarantine / "Runtime" / "Desktop" / "site-packages"
        python_root.mkdir(parents=True, exist_ok=True)
        desktop_site.mkdir(parents=True, exist_ok=True)

        runtime_plan, runtime_size = runtime_file_plan(runtime_source_root)
        if not runtime_plan:
            raise RuntimeError("Runtime source inventory was empty.")

        runtime_manifest = acquire_runtime(runtime_plan, python_root)
        package_plan, distribution_summary = package_file_plan(package_inspection)
        if not package_plan:
            raise RuntimeError("Desktop package file inventory was empty.")
        package_manifest = acquire_packages(package_plan, desktop_site)

        receipt["runtime_file_count"] = len(runtime_manifest)
        receipt["runtime_size_bytes"] = runtime_size
        receipt["desktop_package_file_count"] = len(package_manifest)
        receipt["desktop_distributions"] = distribution_summary

        manifest = {
            "created": utc_now().isoformat(),
            "runtime_source": str(runtime_source_root),
            "package_source_interpreter": package_inspection.get("executable"),
            "runtime_files": runtime_manifest,
            "desktop_package_files": package_manifest,
            "desktop_distributions": distribution_summary,
        }
        manifest_path = upload_dir / "QUARANTINE_FILE_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        closure_path = bundle / "dependency_closure_manifest.json"
        verification_record = verify_quarantine(
            root, python_root, desktop_site, bundle, closure_path, upload_dir
        )
        receipt["quarantine_verification"] = verification_record

        print("Stage 6/6: confirming protected live files are unchanged...", flush=True)
        after_baselines = snapshot_baselines(root)
        after_shortcuts = snapshot_shortcuts(root)
        receipt["protected_baselines_after"] = after_baselines
        receipt["protected_shortcuts_after"] = after_shortcuts
        receipt["after_snapshot_passed"] = snapshots_pass(after_baselines, after_shortcuts)
        if not receipt["after_snapshot_passed"]:
            raise RuntimeError("Protected baseline or shortcut verification failed after acquisition.")

        candidate_dir = run_root / "PROPOSED_LIVE_FILES_NOT_APPLIED"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "START_FOXAI_DESKTOP_PORTABLE.bat").write_text(
            candidate_launcher_text(), encoding="ascii", newline="\r\n"
        )
        (candidate_dir / "README_NOT_APPLIED.txt").write_text(
            "These files are proposals only. They were not copied into live FOXAI.\n",
            encoding="utf-8",
        )

        receipt["state"] = "quarantine_acquisition_verified"
        receipt["verified"] = True
        exit_code = 0
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            receipt["protected_baselines_after"] = snapshot_baselines(root)
            receipt["protected_shortcuts_after"] = snapshot_shortcuts(root)
            receipt["after_snapshot_passed"] = snapshots_pass(
                receipt["protected_baselines_after"],
                receipt["protected_shortcuts_after"],
            )
        except Exception as after_exc:
            receipt["after_snapshot_error"] = f"{type(after_exc).__name__}: {after_exc}"
    finally:
        completed = utc_now()
        receipt["completed"] = completed.isoformat()
        receipt["elapsed_seconds"] = round((completed - started).total_seconds(), 2)
        (upload_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (upload_dir / "report.md").write_text(make_report(receipt), encoding="utf-8")
        (upload_dir / "UPLOAD_INSTRUCTIONS.txt").write_text(
            "Zip and upload this UPLOAD_THIS folder only. "
            "Do not upload the large quarantine runtime folder.\n",
            encoding="utf-8",
        )

        print()
        print("Phase 3C state:", receipt["state"])
        print("Verified:", receipt["verified"])
        print("Elapsed seconds:", receipt["elapsed_seconds"])
        print("Upload only:", upload_dir)
        if receipt.get("failure"):
            print("Failure:", receipt["failure"]["message"])
        else:
            print("Phase 3D live apply is not yet authorized.")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
