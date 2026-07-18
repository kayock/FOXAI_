#!/usr/bin/env python3
"""FOXAI USB C3F no-launch activation and launcher-integration preflight."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_NAME = "FOXAI_USBC3F_CONTROLLED_ACTIVATION_PREFLIGHT"
EXPECTED_C3E_RUN = "20260718T023211Z"
EXPECTED_C3E_HASHES = {
    "classification.json": "c7610778147ecea8541f27b54742e7430ca071bc18e4e1d36307db8e774169a4",
    "receipt.json": "1c347f28e33a1f26a6c06bd39eace0f54d56547bbc7748f9781c1a0c51a08c72",
    "commit_receipt.json": "106fc00e542996cc06c10a9b5a041f6af25b4404c65b86da7e87fafa222f127a",
    "installed_file_inventory_final.json": "d55a3d8c8c81c1ce0aaf3ebb98a5c8345c8d3be75915a450786c29cb3b66f16b",
    "portable_verification_postcommit.json": "751d3cbb98016800c7e744b7ad8b7c35e470aa89e99d5f75552b572f109485ec",
    "pe_binary_verification_final.json": "dce8cce7f90244311dd3cd73a59a992f40e235dfda825b8cbb20f94bde75c2b9",
    "boundary_final_protected_comparison.json": "7b3fb45d7d1c3c4e55cb7e9ab095a59dc076c9ee62e2d13a4c6f312ea586d57f",
    "evidence_integrity.json": "f6689560ff74dfcbc7c437f4c56032a17b54db04c405cbb4c6b186042db80f53",
    "package_verification.json": "7e11cbc6f77baaa48306f2dd6d3ed8b99038750609755f6bdb1920232adda815",
}
EXPECTED_TARGET_COUNT = 39046
EXPECTED_TARGET_BYTES = 1520221467
EXPECTED_TARGET_TREE = "e689af293a34f34f59da8f76f0bbb682d2de2df712467cde0134d8c510e99b62"
EXPECTED_PACKAGE_COUNT = 96
PORTABLE_REL = Path("Runtime/Desktop/python/python.exe")
TARGET_REL = Path("Runtime/ComfyUI/site-packages")
COMFY_REL = Path("ComfyUI")
EXCLUDED_SCAN_DIRS = {
    ".git", "__pycache__", "models", "output", "input", "temp", "user",
    "node_modules", "Runtime", "Logs", "INSTALL_OUTPUT", "PLAN_OUTPUT",
    "PREFLIGHT_OUTPUT", "ACQUISITION_OUTPUT", "STAGING_WHEELHOUSE",
}
TEXT_EXTENSIONS = {".py", ".bat", ".cmd", ".ps1", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
LAUNCH_PATTERNS = [
    ("comfy_main", re.compile(r"ComfyUI|COMFY_MAIN|main\.py", re.I)),
    ("cpu_flag", re.compile(r"--cpu", re.I)),
    ("port_8188", re.compile(r"8188")),
    ("bare_python", re.compile(r"(?<![\\/\w])python(?:\.exe)?\b", re.I)),
    ("pycmd", re.compile(r"\bpycmd\s*\(", re.I)),
    ("pip_requirements", re.compile(r"pip\s+install|requirements\.txt", re.I)),
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def verify_package(package: Path) -> dict[str, Any]:
    manifest_path = package / "PACKAGE_INTEGRITY.json"
    manifest = read_json(manifest_path)
    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    expected_paths = set()
    for item in manifest.get("files", []):
        rel = str(item["path"])
        expected_paths.add(rel.casefold())
        path = package / Path(rel)
        if not path.is_file():
            rows.append({"path": rel, "verified": False, "reason": "missing"})
            issues.append(f"Missing sealed package file: {rel}")
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == int(item["size_bytes"]) and digest == str(item["sha256"])
        rows.append({"path": rel, "size_bytes": size, "sha256": digest, "verified": ok})
        if not ok:
            issues.append(f"Sealed package mismatch: {rel}")
    allowed_unsealed = {"package_integrity.json"}
    for path in package.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(package).as_posix()
        if rel.casefold() in expected_paths or rel.casefold() in allowed_unsealed:
            continue
        if rel.startswith("PREFLIGHT_OUTPUT/"):
            continue
        if "__pycache__" in path.parts or path.suffix.lower() == ".pyc":
            continue
        issues.append(f"Unexpected unsealed package file: {rel}")
    return {"verified": not issues, "issues": issues, "files": rows, "revision": manifest.get("revision")}


def verify_c3e_evidence(root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    folder = root / "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL" / "INSTALL_OUTPUT" / EXPECTED_C3E_RUN
    if not folder.is_dir():
        raise RuntimeError(f"Exact reviewed C3E output is missing: {folder}")
    critical_rows = []
    for name, expected in EXPECTED_C3E_HASHES.items():
        path = folder / name
        if not path.is_file():
            raise RuntimeError(f"C3E evidence file missing: {name}")
        actual = sha256_file(path)
        critical_rows.append({"file": name, "expected_sha256": expected, "actual_sha256": actual, "verified": actual == expected})
        if actual != expected:
            raise RuntimeError(f"Exact reviewed C3E evidence changed: {name}")

    evidence = read_json(folder / "evidence_integrity.json")
    all_rows = []
    for item in evidence.get("files", []):
        path = folder / str(item["file"])
        if not path.is_file():
            raise RuntimeError(f"C3E evidence-integrity member missing: {item['file']}")
        size = path.stat().st_size
        digest = sha256_file(path)
        ok = size == int(item["size_bytes"]) and digest == str(item["sha256"])
        all_rows.append({"file": item["file"], "size_bytes": size, "sha256": digest, "verified": ok})
        if not ok:
            raise RuntimeError(f"C3E evidence-integrity verification failed: {item['file']}")

    classification = read_json(folder / "classification.json")
    receipt = read_json(folder / "receipt.json")
    commit = read_json(folder / "commit_receipt.json")
    post = read_json(folder / "portable_verification_postcommit.json")
    pe = read_json(folder / "pe_binary_verification_final.json")
    boundary = read_json(folder / "boundary_final_protected_comparison.json")
    if classification.get("mode") != "C3E_INSTALLED_VERIFIED_COMMITTED_READY_FOR_C3F_REVIEW" or classification.get("verified") is not True:
        raise RuntimeError("C3E classification is not the exact accepted state")
    if receipt.get("verified") is not True or receipt.get("final_target_committed") is not True:
        raise RuntimeError("C3E receipt does not prove a committed target")
    if commit.get("committed") is not True or commit.get("final_exists_after") is not True:
        raise RuntimeError("C3E commit receipt is not verified")
    if post.get("verified") is not True or pe.get("verified") is not True or boundary.get("verified") is not True:
        raise RuntimeError("C3E post-commit verification or protected boundary review failed")
    if int(receipt.get("exact_package_count", 0)) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("C3E exact package count changed")
    return folder, {
        "verified": True,
        "folder": str(folder),
        "critical_files": critical_rows,
        "evidence_file_count": len(all_rows),
        "all_evidence_files_verified": all(row["verified"] for row in all_rows),
        "classification": classification.get("mode"),
        "final_target": receipt.get("final_target"),
        "package_count": receipt.get("exact_package_count"),
        "installed_file_count": receipt.get("installed_file_count"),
        "installed_bytes": receipt.get("installed_bytes"),
        "installed_tree_sha256": receipt.get("installed_tree_sha256"),
        "launcher_change": receipt.get("launcher_change"),
        "comfyui_launched": receipt.get("comfyui_launched"),
    }, read_json(folder / "installed_file_inventory_final.json")


def verify_target_from_inventory(root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    target = root / TARGET_REL
    if not target.is_dir():
        raise RuntimeError(f"Committed isolated target is missing: {target}")
    expected_rows = inventory.get("files") or []
    expected = {str(item["path"]).casefold(): item for item in expected_rows}
    if len(expected) != len(expected_rows):
        raise RuntimeError("C3E installed inventory contains duplicate case-insensitive paths")
    actual_paths: dict[str, Path] = {}
    symlinks: list[str] = []
    for path in sorted(target.rglob("*"), key=lambda p: str(p).casefold()):
        if path.is_symlink():
            symlinks.append(path.relative_to(target).as_posix())
            continue
        if path.is_file():
            rel = path.relative_to(target).as_posix()
            actual_paths[rel.casefold()] = path
    missing = sorted(set(expected) - set(actual_paths))
    unexpected = sorted(set(actual_paths) - set(expected))
    mismatches: list[dict[str, Any]] = []
    total = 0
    aggregate = hashlib.sha256()
    verified_rows = []
    # Preserve the exact sealed C3E inventory sequence. C3E generated this
    # sequence using Windows full-path ordering, where backslash separators
    # sort differently from normalized forward slashes. Re-sorting here would
    # produce a different aggregate hash even when every file is unchanged.
    for item in expected_rows:
        key = str(item["path"]).casefold()
        path = actual_paths.get(key)
        if path is None:
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        rel = str(item["path"])
        ok = size == int(item["size_bytes"]) and digest == str(item["sha256"])
        if not ok and len(mismatches) < 100:
            mismatches.append({
                "path": rel,
                "expected_size": item["size_bytes"],
                "actual_size": size,
                "expected_sha256": item["sha256"],
                "actual_sha256": digest,
            })
        total += size
        aggregate.update(rel.casefold().encode("utf-8", errors="surrogatepass"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        verified_rows.append(ok)
    result = {
        "verified": not symlinks and not missing and not unexpected and not mismatches
                    and len(actual_paths) == EXPECTED_TARGET_COUNT
                    and total == EXPECTED_TARGET_BYTES
                    and aggregate.hexdigest() == EXPECTED_TARGET_TREE
                    and all(verified_rows),
        "target": str(target),
        "expected_file_count": EXPECTED_TARGET_COUNT,
        "actual_file_count": len(actual_paths),
        "expected_bytes": EXPECTED_TARGET_BYTES,
        "actual_bytes": total,
        "expected_tree_sha256": EXPECTED_TARGET_TREE,
        "actual_tree_sha256": aggregate.hexdigest(),
        "missing": missing[:100],
        "unexpected": unexpected[:100],
        "mismatches": mismatches,
        "symlinks": symlinks[:100],
    }
    if not result["verified"]:
        raise RuntimeError(f"Committed isolated target no longer matches C3E inventory: {result}")
    return result


def clean_probe_env(output: Path) -> dict[str, str]:
    cache = output / "OFFLINE_CACHE"
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in [
        "PYTHONHOME", "PYTHONPATH", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL",
    ]:
        env.pop(key, None)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "NO_PROXY": "*",
        "SETUPTOOLS_USE_DISTUTILS": "local",
        "HF_HOME": str(cache / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(cache / "huggingface" / "hub"),
        "TRANSFORMERS_CACHE": str(cache / "transformers"),
        "TORCH_HOME": str(cache / "torch"),
        "XDG_CACHE_HOME": str(cache / "xdg"),
        "MPLCONFIGDIR": str(cache / "matplotlib"),
    })
    return env


def run_activation_probe(root: Path, package: Path, output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    python = root / PORTABLE_REL
    probe = package / "System/Activation/usbc3f_portable_activation_probe.py"
    result_path = output / "portable_activation_probe.json"
    command = [
        str(python), "-I", "-B", "-S", str(probe),
        "--root", str(root),
        "--target", str(root / TARGET_REL),
        "--comfy", str(root / COMFY_REL),
        "--output", str(result_path),
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(root / COMFY_REL),
        env=clean_probe_env(output),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    execution = {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_file": "portable_activation_probe_stdout.txt",
        "stderr_file": "portable_activation_probe_stderr.txt",
        "result_file": result_path.name,
        "network_allowed": False,
        "launch_allowed": False,
    }
    (output / execution["stdout_file"]).write_text(completed.stdout, encoding="utf-8", newline="\n")
    (output / execution["stderr_file"]).write_text(completed.stderr, encoding="utf-8", newline="\n")
    result = read_json(result_path) if result_path.is_file() else {"verified": False, "issues": ["probe produced no result"]}
    if completed.returncode != 0 or result.get("verified") is not True:
        raise RuntimeError(f"Portable activation probe failed: returncode={completed.returncode}, issues={result.get('issues')}")
    return execution, result


def should_scan(path: Path, root: Path, package: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    if path.stat().st_size > 8 * 1024 * 1024:
        return False
    if is_within(path, root / "Runtime") or is_within(path, package):
        return False
    rel = path.relative_to(root)
    if any(part in EXCLUDED_SCAN_DIRS for part in rel.parts):
        return False
    return True


def scan_launch_surfaces(root: Path, package: Path, output: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    snapshots = output / "SOURCE_SNAPSHOTS"
    known_primary = {
        "start_foxai_workshop_portable.bat",
        "core/foxai_web.py",
    }
    known_legacy = {
        "launch foxai workshop.bat", "start_foxai_clean.bat",
        "start comfyui cpu.bat", "install comfyui requirements.bat",
    }
    candidate_paths: list[Path] = []
    package_resolved = package.resolve(strict=False)
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        kept_dirs = []
        for dirname in dirnames:
            child = current_path / dirname
            if child.resolve(strict=False) == package_resolved:
                continue
            if dirname.casefold() in {name.casefold() for name in EXCLUDED_SCAN_DIRS}:
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in filenames:
            candidate_paths.append(current_path / filename)
    for path in sorted(candidate_paths, key=lambda p: str(p).casefold()):
        try:
            if not should_scan(path, root, package):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not re.search(r"ComfyUI|COMFY_MAIN|main\.py|8188", text, re.I):
            continue
        rel = path.relative_to(root).as_posix()
        lines = text.splitlines()
        matches: list[dict[str, Any]] = []
        for number, line in enumerate(lines, 1):
            tags = [name for name, pattern in LAUNCH_PATTERNS if pattern.search(line)]
            if tags:
                matches.append({"line": number, "tags": tags, "text": line[:500]})
        if not matches:
            continue
        lower = rel.casefold()
        role = "primary" if lower in known_primary else "legacy" if lower in known_legacy else "discovered"
        direct_launch = any(
            ("comfy_main" in row["tags"] and ("cpu_flag" in row["tags"] or "bare_python" in row["tags"] or "pycmd" in row["tags"]))
            for row in matches
        )
        host_assisted = any("bare_python" in row["tags"] or "pycmd" in row["tags"] for row in matches)
        isolated_reference = "Runtime\\ComfyUI\\site-packages" in text or "Runtime/ComfyUI/site-packages" in text or "launch_comfyui_isolated" in text
        dependency_mutation = False
        if path.suffix.casefold() in {".bat", ".cmd", ".ps1"}:
            for row in matches:
                stripped = row["text"].strip().casefold()
                if "pip_requirements" in row["tags"] and not stripped.startswith(("echo ", "rem ", "::", "#")):
                    dependency_mutation = True
                    break
        elif path.suffix.casefold() == ".py":
            for row in matches:
                lower_line = row["text"].casefold()
                if "pip_requirements" in row["tags"] and "subprocess" in lower_line:
                    dependency_mutation = True
                    break
        finding = {
            "path": rel,
            "role": role,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "direct_launch_surface": direct_launch,
            "dependency_mutation_surface": dependency_mutation,
            "host_assisted_reference": host_assisted,
            "already_isolated_reference": isolated_reference,
            "matches": matches,
        }
        findings.append(finding)
        snapshot = snapshots / Path(rel)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, snapshot)
    direct = [row for row in findings if row["direct_launch_surface"]]
    host = [row for row in direct if row["host_assisted_reference"] and not row["already_isolated_reference"]]
    return {
        "verified": True,
        "scanned_finding_count": len(findings),
        "direct_launch_surface_count": len(direct),
        "host_assisted_direct_surface_count": len(host),
        "already_isolated_direct_surface_count": len([row for row in direct if row["already_isolated_reference"]]),
        "dependency_mutation_surface_count": len([row for row in findings if row["dependency_mutation_surface"]]),
        "findings": findings,
    }


def activation_launcher_template() -> str:
    return r'''#!/usr/bin/env python3
"""Proposed C3G ComfyUI isolated activation launcher.

This file is a proposal only until C3G operator approval. It must be run by the
USB-owned portable Python with -I -B -S. It activates only the committed
Runtime/ComfyUI/site-packages target and then executes ComfyUI/main.py.
"""
from __future__ import annotations
import argparse
import os
import runpy
import site
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", required=True)
    parser.add_argument("remainder", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()
    root = Path(parsed.root).resolve(strict=True)
    portable = (root / "Runtime/Desktop/python/python.exe").resolve(strict=True)
    target = (root / "Runtime/ComfyUI/site-packages").resolve(strict=True)
    main_py = (root / "ComfyUI/main.py").resolve(strict=True)
    if Path(sys.executable).resolve(strict=True) != portable:
        raise RuntimeError("ComfyUI isolated launcher requires the USB-owned portable Python")
    for key in ("PYTHONHOME", "PYTHONPATH"):
        os.environ.pop(key, None)
    os.environ.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "SETUPTOOLS_USE_DISTUTILS": "local",
    })
    site.addsitedir(str(target))
    sys.path.insert(0, str(main_py.parent))
    forwarded = list(parsed.remainder)
    if forwarded and forwarded[0] == "--":
        forwarded.pop(0)
    sys.argv = [str(main_py), *forwarded]
    os.chdir(main_py.parent)
    runpy.run_path(str(main_py), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def batch_launcher_template() -> str:
    return r'''@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "ACTIVATOR=%FOXAI_ROOT%\System\PortableRuntime\launch_comfyui_isolated.py"
set "TARGET=%FOXAI_ROOT%\Runtime\ComfyUI\site-packages"
set "MAIN=%FOXAI_ROOT%\ComfyUI\main.py"

if not exist "%PYTHON%" echo ERROR: Portable Python missing.& pause & exit /b 2
if not exist "%ACTIVATOR%" echo ERROR: Isolated activator missing.& pause & exit /b 3
if not exist "%TARGET%\torch\__init__.py" echo ERROR: Isolated target incomplete.& pause & exit /b 4
if not exist "%MAIN%" echo ERROR: ComfyUI main.py missing.& pause & exit /b 5

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%ACTIVATOR%" --root "%FOXAI_ROOT%" -- --cpu
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo ComfyUI exited normally.) else echo ComfyUI exited with code %RC%.
pause
exit /b %RC%
'''


def generate_proposed_changes(root: Path, launch_scan: dict[str, Any], output: Path) -> dict[str, Any]:
    proposed = output / "PROPOSED_C3G_CHANGESET"
    (proposed / "System/PortableRuntime").mkdir(parents=True, exist_ok=True)
    (proposed / "System/PortableRuntime/launch_comfyui_isolated.py.proposed").write_text(
        activation_launcher_template(), encoding="utf-8", newline="\n"
    )
    (proposed / "START_COMFYUI_ISOLATED.bat.proposed").write_text(
        batch_launcher_template(), encoding="utf-8", newline="\r\n"
    )

    changes: list[dict[str, Any]] = [
        {
            "action": "add",
            "path": "System/PortableRuntime/launch_comfyui_isolated.py",
            "purpose": "Single portable-Python activation boundary for the committed isolated target",
            "requires_operator_approval": True,
        },
        {
            "action": "add",
            "path": "START_COMFYUI_ISOLATED.bat",
            "purpose": "Direct operator-controlled isolated ComfyUI launcher",
            "requires_operator_approval": True,
        },
    ]

    for finding in launch_scan.get("findings", []):
        if not finding.get("direct_launch_surface") and not finding.get("dependency_mutation_surface"):
            continue
        purpose = (
            "Disable legacy direct pip mutation for the locked isolated runtime"
            if finding.get("dependency_mutation_surface") and not finding.get("direct_launch_surface")
            else "Route direct ComfyUI launch through the isolated activation launcher or explicitly retire the legacy surface"
        )
        changes.append({
            "action": "review_and_patch",
            "path": finding["path"],
            "role": finding["role"],
            "current_sha256": finding["sha256"],
            "purpose": purpose,
            "requires_operator_approval": True,
        })

    exact_notes = {
        "verified_c3e_target": str(root / TARGET_REL),
        "expected_target_tree_sha256": EXPECTED_TARGET_TREE,
        "portable_python": str(root / PORTABLE_REL),
        "comfyui_main": str(root / COMFY_REL / "main.py"),
        "c3g_write_scope": [
            "System/PortableRuntime/launch_comfyui_isolated.py",
            "START_COMFYUI_ISOLATED.bat",
            "exact reviewed direct launch surfaces only",
        ],
        "c3g_forbidden": [
            "No dependency installation or wheel download",
            "No edit to Runtime/ComfyUI/site-packages",
            "No edit to Runtime/Desktop or Runtime/Core",
            "No ComfyUI launch during integration apply",
            "No automatic deletion or rollback",
        ],
        "first_launch_deferred_to": "C3H controlled first-start gate after C3G integration is separately reviewed",
    }
    write_json(proposed / "ACTIVATION_CONTRACT.json", exact_notes)
    write_json(proposed / "REQUIRED_CHANGES.json", {"changes": changes})

    # Produce exact small diffs for known direct-call substitutions when patterns are unique.
    patches: list[dict[str, Any]] = []
    for finding in launch_scan.get("findings", []):
        rel = finding["path"]
        source = root / Path(rel)
        try:
            text = source.read_text(encoding="utf-8", errors="strict")
        except Exception:
            continue
        updated = text
        if rel.casefold() == "core/foxai_web.py":
            old = "proc=launch(pycmd()+[str(COMFY_MAIN),'--cpu'],COMFY,env=comfy_child_env())"
            replacement = "proc=launch(comfy_isolated_cmd(),COMFY,env=comfy_isolated_env())"
            count = updated.count(old)
            if count == 2:
                updated = updated.replace(old, replacement)
                anchor = "def pycmd():\n"
                helper = (
                    "def comfy_isolated_cmd():\n"
                    "    portable=ROOT/'Runtime'/'Desktop'/'python'/'python.exe'\n"
                    "    activator=ROOT/'System'/'PortableRuntime'/'launch_comfyui_isolated.py'\n"
                    "    return [str(portable),'-I','-B','-S',str(activator),'--root',str(ROOT),'--','--cpu']\n"
                    "def comfy_isolated_env():\n"
                    "    env=os.environ.copy()\n"
                    "    for key in ('PYTHONNOUSERSITE','PYTHONHOME','PYTHONPATH'):\n"
                    "        env.pop(key,None)\n"
                    "    env['PYTHONDONTWRITEBYTECODE']='1'\n"
                    "    env['PYTHONNOUSERSITE']='1'\n"
                    "    env['HF_HUB_DISABLE_TELEMETRY']='1'\n"
                    "    env['DO_NOT_TRACK']='1'\n"
                    "    return env\n"
                )
                if anchor in updated:
                    updated = updated.replace(anchor, helper + anchor, 1)
            else:
                patches.append({"path": rel, "generated": False, "reason": f"Expected 2 exact web launch calls, found {count}"})
        elif rel.casefold() == "start_foxai_workshop_portable.bat":
            old_check = """where python.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: The proven ComfyUI startup method requires python.exe on the host PATH.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 4
)
"""
            new_check = r"""if not exist "%ROOT%Runtime\ComfyUI\site-packages\torch\__init__.py" (
    echo ERROR: The verified isolated ComfyUI target is missing or incomplete.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 4
)
if not exist "%ROOT%System\PortableRuntime\launch_comfyui_isolated.py" (
    echo ERROR: The isolated ComfyUI activator is missing.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 4
)
"""
            old_launch = 'start "ComfyUI CPU" /D "%ROOT%ComfyUI" cmd.exe /d /k "set PYTHONHOME=& set PYTHONPATH=& python.exe main.py --cpu"'
            new_launch = r'start "ComfyUI CPU" /D "%ROOT%ComfyUI" cmd.exe /d /k ""%ROOT%Runtime\Desktop\python\python.exe" -I -B -S "%ROOT%System\PortableRuntime\launch_comfyui_isolated.py" --root "%ROOT%." -- --cpu"'
            if old_check in updated and old_launch in updated:
                updated = updated.replace(old_check, new_check, 1).replace(old_launch, new_launch, 1)
            else:
                patches.append({"path": rel, "generated": False, "reason": "Primary workshop launcher patterns were not uniquely recognized"})
        elif rel.casefold() == "launch foxai workshop.bat":
            old_launch = 'start "ComfyUI CPU" cmd /k "cd /d "%~dp0ComfyUI" && python main.py --cpu"'
            new_launch = r'start "ComfyUI CPU" cmd /k ""%~dp0Runtime\Desktop\python\python.exe" -I -B -S "%~dp0System\PortableRuntime\launch_comfyui_isolated.py" --root "%~dp0." -- --cpu"'
            if old_launch in updated:
                updated = updated.replace(old_launch, new_launch, 1)
            else:
                patches.append({"path": rel, "generated": False, "reason": "Legacy workshop launch pattern was not uniquely recognized"})
        elif rel.casefold() == "start_foxai_clean.bat":
            old_launch = 'start "FOXAI ComfyUI" cmd /k "cd /d "%COMFY_DIR%" && %PYTHON_CMD% main.py --cpu"'
            new_launch = r'start "FOXAI ComfyUI" cmd /k ""%FOXAI_ROOT%\Runtime\Desktop\python\python.exe" -I -B -S "%FOXAI_ROOT%\System\PortableRuntime\launch_comfyui_isolated.py" --root "%FOXAI_ROOT%" -- --cpu"'
            if old_launch in updated:
                updated = updated.replace(old_launch, new_launch, 1)
            else:
                patches.append({"path": rel, "generated": False, "reason": "Clean launcher ComfyUI pattern was not uniquely recognized"})
        elif rel.casefold() == "start comfyui cpu.bat":
            updated = batch_launcher_template()
        elif rel.casefold() == "install comfyui requirements.bat":
            updated = (
                "@echo off\r\n"
                "title FOXAI - Isolated ComfyUI Runtime Protected\r\n"
                "echo ComfyUI dependencies are managed by the verified isolated USB runtime.\r\n"
                "echo This legacy pip installer is intentionally disabled.\r\n"
                "echo No packages were changed.\r\n"
                "pause\r\n"
                "exit /b 0\r\n"
            )
        if updated != text:
            diff = "".join(difflib.unified_diff(
                text.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=rel,
                tofile=rel + ".proposed",
            ))
            patch_path = proposed / "PATCHES" / (rel.replace("/", "__").replace("\\", "__") + ".diff")
            patch_path.parent.mkdir(parents=True, exist_ok=True)
            patch_path.write_text(diff, encoding="utf-8", newline="\n")
            patches.append({"path": rel, "generated": True, "patch": patch_path.relative_to(proposed).as_posix(), "current_sha256": finding["sha256"]})
    write_json(proposed / "PATCH_INDEX.json", {"patches": patches})
    return {
        "verified": True,
        "folder": str(proposed),
        "proposed_change_count": len(changes),
        "generated_patch_count": len([row for row in patches if row.get("generated")]),
        "patches": patches,
    }


def snapshot_scanned_files(scan: dict[str, Any]) -> dict[str, str]:
    return {row["path"]: row["sha256"] for row in scan.get("findings", [])}


def reverify_scanned_files(root: Path, before: dict[str, str]) -> dict[str, Any]:
    changes = []
    for rel, expected in before.items():
        path = root / Path(rel)
        actual = sha256_file(path) if path.is_file() else None
        if actual != expected:
            changes.append({"path": rel, "before": expected, "after": actual})
    return {"verified": not changes, "changes": changes}


def build_evidence_integrity(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(output.rglob("*"), key=lambda p: str(p).casefold()):
        if not path.is_file() or path.name in {"evidence_integrity.json", "UPLOAD_THIS_C3F_REVIEW.zip"}:
            continue
        rows.append({
            "file": path.relative_to(output).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def make_review_zip(output: Path) -> Path:
    zip_path = output / "UPLOAD_THIS_C3F_REVIEW.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.rglob("*"), key=lambda p: str(p).casefold()):
            if path.is_file() and path != zip_path:
                archive.write(path, path.relative_to(output).as_posix())
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    package = Path(__file__).resolve(strict=True).parents[2]
    if package.name != PACKAGE_NAME or package.parent.resolve(strict=True) != root:
        print("[STOPPED] C3F package/root placement is invalid.")
        return 2

    output_root = package / "PREFLIGHT_OUTPUT"
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / utc_stamp()
    output.mkdir(parents=False, exist_ok=False)
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    blocking: list[str] = []
    classification = "C3F_BLOCKED_FAIL_CLOSED"
    verified = False

    receipt: dict[str, Any] = {
        "action": "foxai_usbc3f_controlled_activation_preflight",
        "state": "running",
        "started": started_utc,
        "root": str(root),
        "output": str(output),
        "no_launch": True,
        "no_launcher_change": True,
        "no_runtime_change": True,
        "no_network": True,
    }

    try:
        package_verification = verify_package(package)
        write_json(output / "package_verification.json", package_verification)
        if not package_verification["verified"]:
            raise RuntimeError(f"C3F package integrity failed: {package_verification['issues']}")

        c3e_folder, c3e_verification, installed_inventory = verify_c3e_evidence(root)
        write_json(output / "c3e_input_verification.json", c3e_verification)

        target_verification = verify_target_from_inventory(root, installed_inventory)
        write_json(output / "isolated_target_reverification.json", target_verification)

        launch_scan = scan_launch_surfaces(root, package, output)
        write_json(output / "launcher_surface_inventory.json", launch_scan)
        scanned_before = snapshot_scanned_files(launch_scan)

        execution, probe_result = run_activation_probe(root, package, output)
        write_json(output / "portable_activation_probe_execution.json", execution)
        # Probe writes portable_activation_probe.json itself.

        proposal = generate_proposed_changes(root, launch_scan, output)
        write_json(output / "proposed_c3g_summary.json", proposal)

        source_after = reverify_scanned_files(root, scanned_before)
        write_json(output / "source_boundary_comparison.json", source_after)
        if not source_after["verified"]:
            raise RuntimeError(f"Launch/source files changed during C3F: {source_after['changes']}")

        target_after = verify_target_from_inventory(root, installed_inventory)
        write_json(output / "isolated_target_reverification_after.json", target_after)

        if launch_scan.get("direct_launch_surface_count", 0) == 0:
            raise RuntimeError("No direct ComfyUI launch surfaces were discovered; integration scope cannot be reviewed")
        if probe_result.get("main_py", {}).get("executed") is not False:
            raise RuntimeError("No-launch probe execution state is invalid")
        if probe_result.get("blocked_audit_events"):
            raise RuntimeError("Probe observed a blocked network/process/server event")

        classification = "C3F_READY_FOR_C3G_CONTROLLED_INTEGRATION_APPROVAL"
        verified = True
    except Exception as exc:
        blocking.append(f"{type(exc).__name__}: {exc}")
        (output / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")

    completed = datetime.now(timezone.utc).isoformat()
    receipt.update({
        "state": "preflight_complete_ready_for_exact_review" if verified else "blocked_fail_closed",
        "completed": completed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "verified": verified,
        "classification": classification,
        "blocking_findings": blocking,
        "final_target": str(root / TARGET_REL),
        "final_target_exists": (root / TARGET_REL).is_dir(),
        "launcher_change": False,
        "source_change": False,
        "package_install": False,
        "package_uninstall": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "next_gate": "Upload UPLOAD_THIS_C3F_REVIEW.zip. C3G requires fresh explicit operator approval and remains no-launch.",
    })
    write_json(output / "receipt.json", receipt)
    write_json(output / "classification.json", {
        "mode": classification,
        "verified": verified,
        "blocking_findings": blocking,
        "launcher_change": False,
        "network_access": False,
        "comfyui_launched": False,
        "next_gate": receipt["next_gate"],
    })
    report = [
        "# FOXAI USB C3F — Controlled Activation / Launcher Integration Preflight",
        "",
        f"- Classification: `{classification}`",
        f"- Verified: `{verified}`",
        f"- Elapsed seconds: **{receipt['elapsed_seconds']}**",
        f"- Final isolated target exists: **{receipt['final_target_exists']}**",
        "- Launcher changes: **False**",
        "- ComfyUI launched: **False**",
        "- Network access: **False**",
        "",
        "C3F only proves the committed target can be activated under portable Python and inventories/proposes exact launcher integration. It performs no operational integration and no ComfyUI start.",
        "",
        "## Blocking findings",
        "",
    ]
    report.extend([f"- {item}" for item in blocking] or ["None."])
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    build_evidence_integrity(output)
    make_review_zip(output)

    print()
    if verified:
        print("[COMPLETE] C3F no-launch activation preflight completed.")
        print("[READY] Exact review is required before C3G integration approval.")
    else:
        print("[STOPPED] C3F failed closed. No launcher or runtime change was made.")
        for item in blocking:
            print(" -", item)
    print("Review bundle:", output / "UPLOAD_THIS_C3F_REVIEW.zip")
    return 0 if verified else 19


if __name__ == "__main__":
    raise SystemExit(main())
