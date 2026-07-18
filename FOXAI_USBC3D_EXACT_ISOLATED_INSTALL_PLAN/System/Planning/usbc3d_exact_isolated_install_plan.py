#!/usr/bin/env python3
"""FOXAI USB C3D — Exact Isolated Installation Plan and Approval Preflight.

C3D is deliberately no-install. It consumes the exact reviewed C3C evidence and
staged wheelhouse, re-verifies every wheel, analyzes the future install payload,
proves that an exact approved installer engine can resolve the local lock in
--dry-run mode, and emits an operator-reviewable C3E transaction plan. Portable
pip is preferred; when it is intentionally absent, C3D may use the already
verified same-version host Python only as the installer engine.

Authorized effects:
- read the reviewed C3B/C3C evidence and C3C STAGING_WHEELHOUSE
- hash and inspect exact wheel payloads
- run the selected exact pip engine only with --dry-run, --no-index, --no-deps, local exact wheels
- write evidence and temporary dry-run files only inside this C3D package

Forbidden effects:
- no target or staging-target creation under Runtime/ComfyUI
- no package installation, uninstallation, build, extraction, or package copy
- no network access
- no launcher, Desktop, Core, ComfyUI source, or System changes
- no FOXAI, WebUI, Desktop, or ComfyUI launch
"""
from __future__ import annotations

import argparse
import csv
import email.parser
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import traceback
import urllib.parse
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

ACTION = "foxai_usbc3d_exact_isolated_install_plan_and_approval_preflight"
EXPECTED_PORTABLE_VERSION = (3, 14, 6)
EXPECTED_RELATIVE_PYTHON = Path("Runtime/Desktop/python/python.exe")
EXPECTED_HOST_PYTHON = Path(r"C:\Python314\python.exe")
EXPECTED_HOST_VERSION = (3, 14, 6)
EXPECTED_HOST_PIP_VERSION = "26.1.2"
PREFERRED_TARGET_REL = Path("Runtime/ComfyUI/site-packages")
RUNTIME_WHEELHOUSE_REL = Path("Runtime/ComfyUI/wheelhouse")
C3B_PACKAGE_DIR = "FOXAI_USBC3B_EXACT_ISOLATED_CLOSURE_PLAN"
C3C_PACKAGE_DIR = "FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION"
C3C_WHEELHOUSE_REL = Path(C3C_PACKAGE_DIR) / "STAGING_WHEELHOUSE"
EXPECTED_C3C_CLASSIFICATION = "C3C_READY_FOR_EXACT_ISOLATED_INSTALL_REVIEW"
SUCCESS_CLASSIFICATION = "C3D_READY_FOR_OPERATOR_APPROVAL"
EXPECTED_PACKAGE_COUNT = 96
EXPECTED_COMPRESSED_BYTES = 718_175_632
EXPECTED_C3B_INSTALL_ORDER_HASH = "0a629dc4976edc270665eaf703f8c40fbfc2519562241227b75ea289df39b406"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
IMPORT_LINE_RE = re.compile(r"^import(?:\s|\t)")

# Binds C3D to the exact C3C result that was independently reviewed.
EXPECTED_C3C_HASHES = {
    "acquisition_results.json": "57132daeaaff264de4e5854552ec65efeb7aee8c332e51c615edbcb6765964fa",
    "boundary_after.json": "0ce2ddefbcc00ded35966f945a549ba4adaa15598e1d4752eed50295c6e908bf",
    "boundary_before.json": "74882b373c31799c51f90f2e01d905800cfbb37e20931392bf4042cea16f5ecd",
    "boundary_comparison.json": "c3c37d5cb99037c5a621d1e6971f3dbd0cadd4728e80c93c5f1dd68f1a292316",
    "c3b_input_verification.json": "74662d7255515110fc97abdc8b53b1a4712d3a66b9f5305ce278dcb8789025fe",
    "classification.json": "51735da23959242deb901808aae80d093f30e9b5336a67e1b40d9c2e966cef4e",
    "evidence_integrity.json": "d59715dac1f7b61db42d0919940f438652a598c1de0c1e3150875dec11e2785e",
    "manifest_validation.json": "e0f39bb33acb697bf6c09b063c397ce1738bc903d7bcb2b39bd54598c81938bf",
    "metadata_revalidation.json": "639cbe2669c59b86b689cd878049e647088bf59bc328a20cc7144778bad6d4e7",
    "network_log.json": "f5cc037e035095f1e870291e4e3fbc8fb8cf6f293a35877637d1c8c0e1027037",
    "receipt.json": "65c6356e415df109a89284a840079426eec3efa6bad43e08195f46a87b478c71",
    "report.md": "e86d6431b138446b66300c6599f01140bc559116258d09a210893ef633706f79",
    "rollback_boundaries.json": "d3fdab8456b6cef12380376d31e761cd695749997d11a9303f1dc93d2a571688",
    "runtime_identity.json": "9a91eea2bcd2ecd776acf43a1f931fa86e29096c0d4aeea992ebf54cd1d0eec2",
    "source_policy.json": "7708c6b510636de7e18efb83d32d98d4654b549d263ed8f10830c179f8a2ac8b",
    "space_report.json": "be7eae1e5dc1a69792452a647bc02dca6504b5cbddf05d356ebccf5c46abdcc1",
    "wheel_structure_verification.json": "13bbc4257cea253d5c82ed65d2f12b71439bd451d0864a658eadd45a3b4518ed",
    "wheelhouse_inventory.json": "dcf4f9b9e224dc6d9188e085fba710e3d44f1f4ab924854282cb821b832da11e",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def timestamp_slug() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except Exception:
        return path.absolute()


def normalize_windows_path(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(safe_resolve(path))))


def file_record(path: Path, base: Path | None = None, include_hash: bool = True) -> dict[str, Any]:
    shown = str(path)
    try:
        if base is not None and path.is_relative_to(base):
            shown = str(path.relative_to(base))
        stat = path.stat()
        result: dict[str, Any] = {
            "path": shown,
            "exists": True,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
        if include_hash and path.is_file():
            result["sha256"] = sha256_file(path)
        return result
    except Exception as exc:
        return {"path": shown, "exists": path.exists(), "error": f"{type(exc).__name__}: {exc}"}


def directory_state(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "exists": path.exists(), "is_directory": path.is_dir()}
    if path.is_dir():
        entries = sorted(item.name for item in path.iterdir())
        result["entry_count"] = len(entries)
        result["entries_preview"] = entries[:100]
    return result


def verify_runtime_identity(root: Path) -> dict[str, Any]:
    expected = root / EXPECTED_RELATIVE_PYTHON
    actual = Path(sys.executable)
    checks = {
        "exact_executable": normalize_windows_path(expected) == normalize_windows_path(actual),
        "exact_version": tuple(sys.version_info[:3]) == EXPECTED_PORTABLE_VERSION,
        "cpython": platform.python_implementation() == "CPython",
        "64_bit": struct.calcsize("P") * 8 == 64,
        "windows": os.name == "nt",
        "amd64": platform.machine().upper() in {"AMD64", "X86_64"},
    }
    result = {
        "expected_python": str(expected),
        "actual_python": str(actual),
        "version": list(sys.version_info[:3]),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pointer_bits": struct.calcsize("P") * 8,
        "checks": checks,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Portable runtime identity check failed: {result}")
    return result


def snapshot_boundaries(root: Path) -> dict[str, Any]:
    key_files = [
        Path("ComfyUI/main.py"),
        EXPECTED_RELATIVE_PYTHON,
        Path("START_FOXAI_CLEAN.bat"),
    ]
    return {
        "captured": iso_now(),
        "key_files": [file_record(root / rel, base=root) for rel in key_files],
        "preferred_target": directory_state(root / PREFERRED_TARGET_REL),
        "runtime_wheelhouse": directory_state(root / RUNTIME_WHEELHOUSE_REL),
    }


def compare_boundaries(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_files = {row["path"]: row for row in before["key_files"]}
    after_files = {row["path"]: row for row in after["key_files"]}
    file_checks = []
    for name in sorted(before_files):
        left = before_files[name]
        right = after_files.get(name)
        unchanged = right is not None and left.get("exists") == right.get("exists") and left.get("size_bytes") == right.get("size_bytes") and left.get("sha256") == right.get("sha256")
        file_checks.append({"path": name, "unchanged": unchanged, "before": left, "after": right})
    target_unchanged = before["preferred_target"] == after["preferred_target"]
    runtime_wheelhouse_unchanged = before["runtime_wheelhouse"] == after["runtime_wheelhouse"]
    return {
        "verified": all(row["unchanged"] for row in file_checks) and target_unchanged and runtime_wheelhouse_unchanged,
        "checks": {
            "protected_files_unchanged": all(row["unchanged"] for row in file_checks),
            "preferred_target_unchanged": target_unchanged,
            "preferred_target_not_created": not after["preferred_target"].get("exists", False),
            "runtime_wheelhouse_unchanged": runtime_wheelhouse_unchanged,
            "runtime_wheelhouse_not_created": not after["runtime_wheelhouse"].get("exists", False),
        },
        "file_checks": file_checks,
    }


def find_exact_evidence(base: Path, expected_hashes: dict[str, str]) -> tuple[Path, dict[str, Any]]:
    candidates: list[Path] = []
    if base.is_dir():
        for receipt in base.rglob("receipt.json"):
            candidates.append(receipt.parent)
    matches: list[tuple[Path, dict[str, Any]]] = []
    attempts: list[dict[str, Any]] = []
    for folder in sorted(set(candidates), key=lambda p: str(p)):
        mismatches = []
        for filename, expected in expected_hashes.items():
            path = folder / filename
            if not path.is_file():
                mismatches.append({"file": filename, "status": "missing"})
                continue
            actual = sha256_file(path)
            if actual != expected:
                mismatches.append({"file": filename, "status": "hash_mismatch", "expected": expected, "actual": actual})
        attempts.append({"folder": str(folder), "mismatches": mismatches})
        if not mismatches:
            matches.append((folder, {"verified": True, "folder": str(folder), "file_count": len(expected_hashes), "hashes": expected_hashes}))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one exact reviewed C3C evidence folder; found {len(matches)}. Attempts: {attempts}")
    return matches[0]


def find_c3b_install_order(root: Path) -> tuple[Path, dict[str, Any]]:
    base = root / C3B_PACKAGE_DIR / "PLAN_OUTPUT"
    matches = []
    if base.is_dir():
        for path in base.rglob("install_order.json"):
            if sha256_file(path) == EXPECTED_C3B_INSTALL_ORDER_HASH:
                matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one reviewed C3B install_order.json; found {len(matches)}")
    data = read_json(matches[0])
    order = data.get("order")
    if not isinstance(order, list) or len(order) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("Reviewed C3B install order does not contain 96 entries")
    return matches[0], data


def canonicalize_name_fallback(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_inventory(c3c_folder: Path, wheelhouse: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classification = read_json(c3c_folder / "classification.json")
    receipt = read_json(c3c_folder / "receipt.json")
    manifest = read_json(c3c_folder / "manifest_validation.json")
    inventory_doc = read_json(c3c_folder / "wheelhouse_inventory.json")
    if classification.get("mode") != EXPECTED_C3C_CLASSIFICATION:
        raise RuntimeError(f"C3C classification mismatch: {classification}")
    if receipt.get("classification") != EXPECTED_C3C_CLASSIFICATION or receipt.get("verified") is not True:
        raise RuntimeError(f"C3C receipt mismatch: {receipt}")
    if receipt.get("exact_package_count") != EXPECTED_PACKAGE_COUNT or receipt.get("exact_staged_bytes") != EXPECTED_COMPRESSED_BYTES:
        raise RuntimeError("C3C receipt package count or byte total changed")
    if manifest.get("verified") is not True or manifest.get("package_count") != EXPECTED_PACKAGE_COUNT or manifest.get("compressed_wheel_bytes") != EXPECTED_COMPRESSED_BYTES:
        raise RuntimeError("C3C manifest validation changed")
    rows = inventory_doc.get("wheels") or inventory_doc.get("inventory") or inventory_doc.get("files")
    if not isinstance(rows, list):
        # R3 uses a top-level list under an implementation-specific key; find the unique list of dicts with filenames.
        candidate_lists = [v for v in inventory_doc.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "filename" in v[0]]
        if len(candidate_lists) != 1:
            raise RuntimeError(f"Could not identify exact wheel inventory list: keys={list(inventory_doc)}")
        rows = candidate_lists[0]
    if len(rows) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError(f"Wheelhouse inventory count changed: {len(rows)}")
    normalized = []
    for row in rows:
        name = canonicalize_name_fallback(str(row["name"]))
        version = str(row["version"])
        filename = str(row["filename"])
        size = int(row["size_bytes"])
        digest = str(row["sha256"]).lower()
        if not HEX64_RE.fullmatch(digest):
            raise RuntimeError(f"Malformed wheel hash for {filename}")
        normalized.append({"name": name, "version": version, "filename": filename, "size_bytes": size, "sha256": digest})
    if len({r["name"] for r in normalized}) != EXPECTED_PACKAGE_COUNT or len({r["filename"].casefold() for r in normalized}) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("Duplicate package name or wheel filename in C3C inventory")
    if sum(r["size_bytes"] for r in normalized) != EXPECTED_COMPRESSED_BYTES:
        raise RuntimeError("C3C wheel byte total changed")
    if not wheelhouse.is_dir():
        raise RuntimeError(f"C3C staging wheelhouse is missing: {wheelhouse}")
    return normalized, {"classification": classification, "receipt": receipt, "manifest_validation": manifest}


def reverify_wheelhouse(rows: list[dict[str, Any]], wheelhouse: Path) -> dict[str, Any]:
    expected = {row["filename"].casefold(): row for row in rows}
    actual_files = sorted(path for path in wheelhouse.iterdir() if path.is_file())
    actual_names = {path.name.casefold() for path in actual_files}
    missing = sorted(row["filename"] for key, row in expected.items() if key not in actual_names)
    unexpected = sorted(path.name for path in actual_files if path.name.casefold() not in expected)
    results = []
    for row in rows:
        path = wheelhouse / row["filename"]
        if not path.is_file():
            results.append({**row, "verified": False, "reason": "missing"})
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        verified = size == row["size_bytes"] and digest == row["sha256"]
        results.append({**row, "path": str(path), "actual_size_bytes": size, "actual_sha256": digest, "verified": verified})
    verified = not missing and not unexpected and all(row["verified"] for row in results)
    if not verified:
        raise RuntimeError(f"C3C wheelhouse exact re-verification failed: missing={missing}, unexpected={unexpected}")
    return {
        "verified": True,
        "wheel_count": len(results),
        "compressed_bytes": sum(row["actual_size_bytes"] for row in results),
        "missing": missing,
        "unexpected": unexpected,
        "wheels": results,
    }


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def destination_for_member(member: str, top_dist_info: str) -> tuple[str, str]:
    path = PurePosixPath(member)
    parts = path.parts
    data_prefix = top_dist_info[:-10] + ".data"  # remove '.dist-info'
    if parts and parts[0] == data_prefix and len(parts) >= 3:
        scheme = parts[1]
        relative = PurePosixPath(*parts[2:]).as_posix()
        mapping = {
            "purelib": "SITE",
            "platlib": "SITE",
            "scripts": "SCRIPTS",
            "headers": "HEADERS",
            "data": "DATA",
        }
        return mapping.get(scheme, f"UNKNOWN_DATA_SCHEME:{scheme}"), relative
    return "SITE", path.as_posix()


def analyze_wheels(rows: list[dict[str, Any]], wheelhouse: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    destinations: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    wheel_results = []
    pth_files = []
    entry_points = []
    unknown_schemes = set()
    total_uncompressed = 0
    total_file_members = 0
    total_native = 0

    for row in rows:
        wheel_path = wheelhouse / row["filename"]
        with zipfile.ZipFile(wheel_path, "r") as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            top_dist_infos = sorted({PurePosixPath(info.filename).parts[0] for info in infos if len(PurePosixPath(info.filename).parts) == 2 and PurePosixPath(info.filename).parts[0].endswith(".dist-info") and PurePosixPath(info.filename).parts[1] == "RECORD"})
            if len(top_dist_infos) != 1:
                raise RuntimeError(f"Wheel no longer has exactly one top-level primary dist-info: {row['filename']} -> {top_dist_infos}")
            top_dist_info = top_dist_infos[0]
            wheel_uncompressed = 0
            wheel_native = 0
            wheel_pth = []
            wheel_entry_points = []
            wheel_unknown_schemes = set()
            for info in infos:
                member = PurePosixPath(info.filename).as_posix()
                root_kind, dest = destination_for_member(member, top_dist_info)
                if root_kind.startswith("UNKNOWN_DATA_SCHEME:"):
                    unknown_schemes.add(root_kind)
                    wheel_unknown_schemes.add(root_kind)
                key = (root_kind, dest.casefold())
                destinations[key].append({"package": row["name"], "version": row["version"], "wheel": row["filename"], "member": member, "destination": dest, "root": root_kind, "size_bytes": info.file_size, "crc32": f"{info.CRC:08x}"})
                wheel_uncompressed += info.file_size
                total_uncompressed += info.file_size
                total_file_members += 1
                suffix = PurePosixPath(dest).suffix.lower()
                if suffix in {".pyd", ".dll"}:
                    wheel_native += 1
                    total_native += 1
                if root_kind == "SITE" and suffix == ".pth":
                    if info.file_size > 1024 * 1024:
                        raise RuntimeError(f"Unexpectedly large .pth file: {row['filename']}:{member}")
                    text = decode_text(archive.read(info))
                    active_lines = []
                    executable_lines = []
                    path_lines = []
                    for line_number, raw in enumerate(text.splitlines(), 1):
                        stripped = raw.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        record = {"line_number": line_number, "text": raw}
                        active_lines.append(record)
                        if IMPORT_LINE_RE.match(stripped):
                            executable_lines.append(record)
                        else:
                            path_lines.append(record)
                    item = {"package": row["name"], "version": row["version"], "wheel": row["filename"], "member": member, "destination": dest, "active_lines": active_lines, "executable_import_lines": executable_lines, "path_lines": path_lines}
                    pth_files.append(item)
                    wheel_pth.append(item)
            entry_name = f"{top_dist_info}/entry_points.txt"
            if entry_name in archive.namelist():
                text = decode_text(archive.read(entry_name))
                item = {"package": row["name"], "version": row["version"], "wheel": row["filename"], "member": entry_name, "text": text}
                entry_points.append(item)
                wheel_entry_points.append(item)
            wheel_results.append({
                "name": row["name"],
                "version": row["version"],
                "filename": row["filename"],
                "top_dist_info": top_dist_info,
                "file_members": len(infos),
                "uncompressed_bytes": wheel_uncompressed,
                "native_binary_files": wheel_native,
                "pth_file_count": len(wheel_pth),
                "entry_points_file_count": len(wheel_entry_points),
                "unknown_data_schemes": sorted(wheel_unknown_schemes),
            })

    collisions = []
    for (root_kind, _), owners in sorted(destinations.items(), key=lambda item: item[0]):
        packages = {owner["package"] for owner in owners}
        if len(owners) > 1 and len(packages) > 1:
            collisions.append({"root": root_kind, "destination_casefold": owners[0]["destination"].casefold(), "owners": owners})

    analysis = {
        "verified": not unknown_schemes,
        "wheel_count": len(wheel_results),
        "total_file_members": total_file_members,
        "total_uncompressed_bytes": total_uncompressed,
        "native_binary_file_count": total_native,
        "unknown_data_schemes": sorted(unknown_schemes),
        "wheels": wheel_results,
    }
    collision_report = {
        "verified": not collisions,
        "case_insensitive_cross_wheel_collision_count": len(collisions),
        "collisions": collisions,
        "note": "Directory sharing is normal; this report blocks only two different wheels targeting the same case-insensitive file path.",
    }
    pth_report = {
        "pth_file_count": len(pth_files),
        "pth_files_with_executable_import_lines": sum(1 for item in pth_files if item["executable_import_lines"]),
        "pth_files": pth_files,
        "review_required": any(item["executable_import_lines"] for item in pth_files),
        "note": "Executable .pth lines are recorded for operator review. They are not executed by C3D.",
    }
    entry_report = {
        "entry_points_metadata_file_count": len(entry_points),
        "entry_points": entry_points,
        "note": "C3D does not generate or execute console/gui scripts.",
    }
    return analysis, collision_report, pth_report, entry_report


def order_rows(rows: list[dict[str, Any]], install_order: dict[str, Any]) -> list[dict[str, Any]]:
    by_name = {row["name"]: row for row in rows}
    ordered = []
    seen = set()
    for item in install_order["order"]:
        name = canonicalize_name_fallback(str(item["name"]))
        version = str(item["version"])
        if name not in by_name:
            raise RuntimeError(f"C3B install order references missing package: {name}")
        row = by_name[name]
        if row["version"] != version:
            raise RuntimeError(f"C3B install order version mismatch for {name}: {version} != {row['version']}")
        if name in seen:
            raise RuntimeError(f"Duplicate package in C3B install order: {name}")
        seen.add(name)
        ordered.append(row)
    if len(ordered) != EXPECTED_PACKAGE_COUNT or seen != set(by_name):
        raise RuntimeError("C3B install order does not exactly cover C3C wheelhouse")
    return ordered


def generate_requirements(path: Path, ordered_rows: list[dict[str, Any]], wheelhouse: Path) -> dict[str, Any]:
    lines = [
        "# FOXAI USB C3D exact local wheel lock — generated from reviewed C3B/C3C evidence",
        "# This file is for pip consumption only. It performs no network resolution.",
        "--no-index",
        "--only-binary=:all:",
        "--require-hashes",
        "",
    ]
    entries = []
    for position, row in enumerate(ordered_rows, 1):
        wheel = safe_resolve(wheelhouse / row["filename"])
        uri = wheel.as_uri()
        line = f"{uri} --hash=sha256:{row['sha256']}"
        lines.append(line)
        entries.append({"position": position, **row, "path": str(wheel), "file_uri": uri, "requirement_line": line})
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {"verified": True, "path": str(path), "sha256": sha256_file(path), "entry_count": len(entries), "entries": entries}


def run_command(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 300) -> dict[str, Any]:
    started = iso_now()
    completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout, errors="replace")
    return {
        "command": command,
        "started": started,
        "completed": iso_now(),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _pip_probe_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PIP_NO_INDEX": "1",
        "PIP_NO_CACHE_DIR": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
    })
    return env


def _probe_pip_candidate(label: str, executable: Path, output: Path, require_exact_host: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "python": str(executable),
        "exists": executable.is_file(),
        "require_exact_host": require_exact_host,
        "verified": False,
    }
    if not executable.is_file():
        result["issues"] = ["python executable missing"]
        return result

    result["python_size_bytes"] = executable.stat().st_size
    result["python_sha256"] = sha256_file(executable)
    identity_code = (
        "import json,platform,struct,sys;"
        "print(json.dumps({'version':list(sys.version_info[:3]),"
        "'implementation':platform.python_implementation(),"
        "'machine':platform.machine(),"
        "'pointer_bits':struct.calcsize('P')*8,"
        "'platform':sys.platform,'executable':sys.executable}))"
    )
    env = _pip_probe_environment()
    prefix = [str(executable), "-I", "-B"]
    identity_result = run_command(prefix + ["-c", identity_code], cwd=output, env=env, timeout=60)
    result["identity_probe"] = identity_result
    identity: dict[str, Any] = {}
    if identity_result["returncode"] == 0:
        try:
            identity = json.loads(identity_result["stdout"].strip())
        except Exception as exc:
            result.setdefault("issues", []).append(f"identity JSON parse failed: {type(exc).__name__}: {exc}")
    result["identity"] = identity

    version_result = run_command(
        prefix + ["-m", "pip", "--isolated", "--disable-pip-version-check", "--version"],
        cwd=output,
        env=env,
        timeout=60,
    )
    help_result = run_command(
        prefix + ["-m", "pip", "--isolated", "--disable-pip-version-check", "install", "--help"],
        cwd=output,
        env=env,
        timeout=60,
    )
    help_text = help_result["stdout"] + "\n" + help_result["stderr"]
    required_options = [
        "--dry-run", "--report", "--target", "--require-hashes", "--no-deps",
        "--no-index", "--only-binary", "--no-compile", "--no-cache-dir",
    ]
    support = {option: option in help_text for option in required_options}
    pip_version_match = re.search(r"\bpip\s+([^\s]+)", version_result.get("stdout", ""))
    pip_version = pip_version_match.group(1) if pip_version_match else None

    expected_identity = (
        identity.get("version") == list(EXPECTED_HOST_VERSION if require_exact_host else EXPECTED_PORTABLE_VERSION)
        and identity.get("implementation") == "CPython"
        and identity.get("pointer_bits") == 64
        and str(identity.get("machine", "")).upper() in {"AMD64", "X86_64"}
        and identity.get("platform") == "win32"
    )
    exact_pip_ok = (pip_version == EXPECTED_HOST_PIP_VERSION) if require_exact_host else bool(pip_version)
    verified = (
        identity_result["returncode"] == 0
        and expected_identity
        and version_result["returncode"] == 0
        and help_result["returncode"] == 0
        and all(support.values())
        and exact_pip_ok
    )
    issues = list(result.get("issues", []))
    if not expected_identity:
        issues.append("Python identity does not match the approved CPython 3.14.6 x64 Windows installer identity")
    if version_result["returncode"] != 0:
        issues.append("pip version probe failed")
    if help_result["returncode"] != 0:
        issues.append("pip install help probe failed")
    if not all(support.values()):
        issues.append("one or more required pip safety/control options are unavailable")
    if require_exact_host and pip_version != EXPECTED_HOST_PIP_VERSION:
        issues.append(f"host pip version is {pip_version!r}; expected exact {EXPECTED_HOST_PIP_VERSION}")

    result.update({
        "verified": verified,
        "pip_version": pip_version,
        "version_probe": version_result,
        "install_help_returncode": help_result["returncode"],
        "required_option_support": support,
        "pip_install_help_sha256": hashlib.sha256(help_text.encode("utf-8", errors="replace")).hexdigest(),
        "pip_install_help_length": len(help_text),
        "command_prefix": prefix + ["-m", "pip", "--isolated", "--disable-pip-version-check"],
        "issues": issues,
    })
    return result


def probe_pip(output: Path) -> dict[str, Any]:
    portable = _probe_pip_candidate("portable_pip", Path(sys.executable), output, require_exact_host=False)
    host = _probe_pip_candidate("host_pip", EXPECTED_HOST_PYTHON, output, require_exact_host=True)
    selected = portable if portable["verified"] else host if host["verified"] else None
    return {
        "verified": selected is not None,
        "preferred_engine": "portable_pip",
        "fallback_policy": (
            "Use exact C:\\Python314\\python.exe CPython 3.14.6 x64 with pip 26.1.2 "
            "only when the protected portable Python intentionally has no pip. "
            "The engine performs a dry run only in C3D and writes no runtime files."
        ),
        "candidates": [portable, host],
        "selected_engine": selected,
        "host_assisted_installer_only": bool(selected and selected["label"] == "host_pip"),
    }

def run_pip_dry_run(output: Path, requirements: Path, expected_rows: list[dict[str, Any]], engine: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pip_temp = output / "PIP_DRY_RUN_TEMP"
    pip_cache = output / "PIP_DRY_RUN_CACHE"
    pip_temp.mkdir(exist_ok=False)
    pip_cache.mkdir(exist_ok=False)
    report_path = output / "pip_dry_run_report.json"
    env = os.environ.copy()
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PIP_NO_INDEX": "1",
        "PIP_CACHE_DIR": str(pip_cache),
        "TMP": str(pip_temp),
        "TEMP": str(pip_temp),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
    })
    command = list(engine["command_prefix"]) + [
        "install", "--dry-run", "--ignore-installed", "--no-deps", "--no-index",
        "--only-binary=:all:", "--require-hashes", "--no-cache-dir", "--progress-bar", "off",
        "--report", str(report_path), "-r", str(requirements),
    ]
    result = run_command(command, cwd=output, env=env, timeout=900)
    (output / "pip_dry_run_stdout.txt").write_text(result["stdout"], encoding="utf-8", newline="\n")
    (output / "pip_dry_run_stderr.txt").write_text(result["stderr"], encoding="utf-8", newline="\n")
    # Temporary extraction/cache data are never accepted as evidence or installation output.
    shutil.rmtree(pip_temp, ignore_errors=True)
    shutil.rmtree(pip_cache, ignore_errors=True)
    result_summary = {key: value for key, value in result.items() if key not in {"stdout", "stderr"}}
    result_summary["stdout_file"] = "pip_dry_run_stdout.txt"
    result_summary["stderr_file"] = "pip_dry_run_stderr.txt"
    result_summary["report_exists"] = report_path.is_file()
    result_summary["selected_engine"] = engine

    validation: dict[str, Any] = {"verified": False, "issues": []}
    if result["returncode"] != 0:
        validation["issues"].append(f"pip dry-run returned {result['returncode']}")
        return result_summary, validation
    if not report_path.is_file():
        validation["issues"].append("pip dry-run did not produce report")
        return result_summary, validation
    report = read_json(report_path)
    installs = report.get("install")
    if not isinstance(installs, list):
        validation["issues"].append("pip report install field missing")
        return result_summary, validation
    expected = {(row["name"], row["version"]): row for row in expected_rows}
    observed = {}
    observations = []
    for item in installs:
        metadata = item.get("metadata") or {}
        name = canonicalize_name_fallback(str(metadata.get("name", "")))
        version = str(metadata.get("version", ""))
        download = item.get("download_info") or {}
        archive = download.get("archive_info") or {}
        hashes = archive.get("hashes") or {}
        digest = str(hashes.get("sha256", "")).lower()
        url = str(download.get("url", ""))
        key = (name, version)
        observations.append({"name": name, "version": version, "sha256": digest, "url": url, "requested": item.get("requested"), "is_yanked": item.get("is_yanked")})
        if key in observed:
            validation["issues"].append(f"duplicate pip report package {name}=={version}")
        observed[key] = {"sha256": digest, "url": url}
    for key, row in expected.items():
        if key not in observed:
            validation["issues"].append(f"missing from pip report: {key[0]}=={key[1]}")
            continue
        if observed[key]["sha256"] != row["sha256"]:
            validation["issues"].append(f"pip report hash mismatch: {key[0]}=={key[1]}")
        parsed = urllib.parse.urlsplit(observed[key]["url"])
        if parsed.scheme != "file":
            validation["issues"].append(f"pip report used non-file source: {key[0]} -> {observed[key]['url']}")
    for key in observed:
        if key not in expected:
            validation["issues"].append(f"unexpected pip report package: {key[0]}=={key[1]}")
    validation.update({
        "verified": not validation["issues"] and len(installs) == EXPECTED_PACKAGE_COUNT,
        "pip_version": report.get("pip_version"),
        "report_version": report.get("version"),
        "install_count": len(installs),
        "environment": report.get("environment"),
        "observations": observations,
    })
    return result_summary, validation


def make_transaction_plan(root: Path, output: Path, requirements: Path, pth_report: dict[str, Any], pip_capability: dict[str, Any]) -> dict[str, Any]:
    runtime_comfy = root / "Runtime/ComfyUI"
    final_target = root / PREFERRED_TARGET_REL
    staging_template = runtime_comfy / ".C3E_site-packages_staging_<UTC_RUN_ID>"
    portable_python = root / EXPECTED_RELATIVE_PYTHON
    selected_engine = pip_capability.get("selected_engine") or {}
    if not selected_engine.get("verified"):
        command = []
    else:
        command = list(selected_engine["command_prefix"]) + [
            "install", "--ignore-installed", "--no-index", "--no-deps", "--only-binary=:all:", "--require-hashes",
            "--no-cache-dir", "--no-compile", "--progress-bar", "off",
            "--target", str(staging_template), "-r", str(requirements),
        ]
    return {
        "status": "PLAN_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
        "portable_python": str(portable_python),
        "installer_engine": selected_engine,
        "installer_mode": "HOST_ASSISTED_INSTALLER_ONLY" if selected_engine.get("label") == "host_pip" else "PORTABLE_PIP",
        "result_portability": (
            "The selected pip process is only the offline installer. The installed target is consumed by "
            "the protected portable CPython 3.14.6 runtime and must not import from the host after commit."
        ),
        "read_only_wheel_source": str(root / C3C_WHEELHOUSE_REL),
        "requirements_lock": str(requirements),
        "future_staging_target_template": str(staging_template),
        "future_final_target": str(final_target),
        "future_install_command_argv": command,
        "future_install_command_display": subprocess.list2cmdline(command),
        "required_preconditions": [
            "Fresh C3E operator approval",
            "C3D evidence remains exact and verified",
            "C3C wheelhouse re-hashes exactly",
            "Selected installer Python SHA-256, exact version, architecture, and pip version match the reviewed C3D evidence",
            "Final target and C3E staging target do not exist",
            "No FOXAI, Desktop, WebUI, or ComfyUI process is using the runtime",
        ],
        "transaction_sequence": [
            "Create one new timestamped staging directory adjacent to the final target",
            "Re-hash all 96 source wheels and the selected installer Python immediately before pip",
            "Run one offline hash-locked pip install with --ignore-installed into the empty staging directory",
            "Perform inventory, dependency, import, CPU tensor, torchvision-op, torchaudio, and DLL tests against staging",
            "Write a complete installation receipt and exact file inventory",
            "Commit only by same-volume rename from staging to the still-absent final target",
            "Do not edit or enable any launcher during C3E",
        ],
        "pth_activation_review": {
            "pth_file_count": pth_report["pth_file_count"],
            "executable_pth_file_count": pth_report["pth_files_with_executable_import_lines"],
            "future_test_activation": "Use site.addsitedir(staging_or_final_target) in a dedicated verification process so exact .pth behavior is visible and logged.",
        },
        "not_performed_by_c3d": True,
    }


def make_activation_plan(root: Path, pth_report: dict[str, Any]) -> dict[str, Any]:
    target = root / PREFERRED_TARGET_REL
    return {
        "status": "DEFERRED_UNTIL_AFTER_C3E_VERIFICATION",
        "target": str(target),
        "preferred_verification_activation": f"import site; site.addsitedir(r'{target}')",
        "reason": "site.addsitedir adds the isolated directory and processes its reviewed .pth files; C3D records but does not execute those files.",
        "pth_file_count": pth_report["pth_file_count"],
        "executable_pth_file_count": pth_report["pth_files_with_executable_import_lines"],
        "launcher_change_in_c3d": False,
        "launcher_change_in_c3e": False,
        "future_launcher_integration_gate": "C3F or later, only after isolated imports and a controlled ComfyUI launch pass.",
    }


def make_post_install_plan(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    versions = {row["name"]: row["version"] for row in rows}
    return {
        "status": "PLAN_ONLY",
        "target": str(root / PREFERRED_TARGET_REL),
        "required_checks_before_commit": [
            "Final target remains absent and transaction staging target is the only new Runtime/ComfyUI directory",
            "Installed importlib.metadata inventory contains exactly the 96 locked name/version pairs",
            "Every installed distribution RECORD path remains inside the transaction staging target",
            "Custom dependency-edge verifier reports all active requirements satisfied from the isolated target",
            "No package is imported from host user-site, host Python, Desktop site-packages, or Core site-packages when an isolated copy is expected",
            f"torch imports as {versions.get('torch')} and completes a CPU tensor calculation",
            f"torchvision imports as {versions.get('torchvision')} and its compiled operations report available",
            f"torchaudio imports as {versions.get('torchaudio')}",
            "numpy, scipy, Pillow, aiohttp, safetensors, tokenizers, transformers, and ComfyUI support packages import from the transaction target",
            "All staged .pyd and bundled DLL files are x64 and load without unresolved runtime errors during critical imports",
            "ComfyUI is not launched during C3E",
            "Protected Desktop, Core, ComfyUI source, System, and launcher hashes remain unchanged",
        ],
        "commit_condition": "All checks pass, receipt is verified, and final target is still absent.",
        "commit_action": "Same-volume rename of the verified transaction staging directory to Runtime\\ComfyUI\\site-packages.",
        "launch_test_deferred_to": "C3F controlled isolated ComfyUI launch review",
    }


def make_rollback_plan(root: Path) -> dict[str, Any]:
    return {
        "status": "PLAN_ONLY",
        "protected_existing_content": "No existing target is present, so no existing package tree may be overwritten or merged.",
        "before_commit": "On any failure, preserve evidence and remove only the newly created C3E transaction staging directory after operator approval.",
        "after_commit_before_launcher_integration": "The new final target is self-contained and can be disabled by renaming it or removed after operator approval; no launcher rollback is required because C3E changes no launcher.",
        "forbidden_rollback_actions": [
            "Do not run pip uninstall against Desktop, Core, host Python, or the isolated target",
            "Do not delete or alter the C3C staging wheelhouse",
            "Do not delete ComfyUI models, inputs, outputs, custom nodes, source, or launchers",
            "Do not overwrite a pre-existing final target",
        ],
        "future_authorized_write_boundary": [
            str(root / "Runtime/ComfyUI/.C3E_site-packages_staging_<UTC_RUN_ID>"),
            str(root / PREFERRED_TARGET_REL),
            str(root / "FOXAI_USBC3E_EXACT_ISOLATED_INSTALL"),
        ],
    }


def build_report(data: dict[str, Any]) -> str:
    classification = data["classification"]
    lines = [
        "# FOXAI USB C3D — Exact Isolated Installation Plan",
        "",
        f"- Classification: `{classification['mode']}`",
        f"- Verified: `{classification['verified']}`",
        f"- Exact wheel count: **{data['wheelhouse']['wheel_count']}**",
        f"- Exact compressed bytes: **{data['wheelhouse']['compressed_bytes']:,}**",
        f"- Exact uncompressed wheel payload bytes: **{data['payload']['total_uncompressed_bytes']:,}**",
        f"- Pip dry-run exact install count: **{data['pip_dry_run_validation'].get('install_count', 0)}**",
        f"- Selected installer engine: **{(data.get('pip_capability', {}).get('selected_engine') or {}).get('label', 'none')}**",
        f"- Cross-wheel destination collisions: **{data['collisions']['case_insensitive_cross_wheel_collision_count']}**",
        f"- `.pth` files recorded for review: **{data['pth']['pth_file_count']}**",
        f"- Executable `.pth` files recorded: **{data['pth']['pth_files_with_executable_import_lines']}**",
        "",
        "## Boundary result",
        "",
        "C3D performed no package installation, target creation, wheel extraction, package copy, launcher edit, network request, or ComfyUI launch. Its selected pip engine invocation used `--dry-run`, `--no-index`, `--no-deps`, exact local wheel paths, and SHA-256 hash checking.",
        "",
        "## Proposed C3E transaction",
        "",
        "C3E should install into a new adjacent transaction staging directory, verify it completely, and commit only by renaming the verified staging directory to the still-absent final target. C3E should not modify launchers or launch ComfyUI.",
        "",
        "## Operator decision",
        "",
        "A successful C3D result authorizes review only. It does not authorize C3E installation until the operator explicitly approves the exact C3D plan.",
    ]
    if classification.get("blocking_findings"):
        lines.extend(["", "## Blocking findings", ""] + [f"- {item}" for item in classification["blocking_findings"]])
    if classification.get("review_findings"):
        lines.extend(["", "## Review findings", ""] + [f"- {item}" for item in classification["review_findings"]])
    return "\n".join(lines) + "\n"


def create_evidence_integrity(output: Path, excluded: Iterable[str] = ()) -> dict[str, Any]:
    excluded_set = set(excluded)
    rows = []
    for path in sorted(output.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_file() or path.name in excluded_set or path.name == "evidence_integrity.json":
            continue
        rows.append({"filename": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    result = {"verified": True, "file_count": len(rows), "files": rows}
    write_json(output / "evidence_integrity.json", result)
    return result


def create_review_zip(output: Path) -> Path:
    destination = output / "UPLOAD_THIS_C3D_REVIEW.zip"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.iterdir(), key=lambda p: p.name.casefold()):
            if path.is_file() and path.name != destination.name:
                archive.write(path, path.name)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = safe_resolve(Path(args.root))
    package_dir = safe_resolve(Path(__file__).parents[2])
    output_base = package_dir / "PLAN_OUTPUT"
    output_base.mkdir(exist_ok=True)
    output = output_base / timestamp_slug()
    output.mkdir(exist_ok=False)
    started = utc_now()
    blocking: list[str] = []
    review_findings: list[str] = []
    state = "plan_blocked_fail_closed"
    classification_mode = "C3D_BLOCKED_FAIL_CLOSED"
    all_data: dict[str, Any] = {}
    boundary_before: dict[str, Any] | None = None

    try:
        if not (root / "ComfyUI/main.py").is_file():
            raise RuntimeError(f"FOXAI root verification failed: {root}")
        if not (root / EXPECTED_RELATIVE_PYTHON).is_file():
            raise RuntimeError(f"Portable Python missing: {root / EXPECTED_RELATIVE_PYTHON}")
        if normalize_windows_path(package_dir.parent) != normalize_windows_path(root):
            raise RuntimeError(f"C3D package must be directly inside FOXAI root. package={package_dir}, root={root}")
        if (root / PREFERRED_TARGET_REL).exists():
            raise RuntimeError(f"Preferred isolated target already exists; C3D refuses ambiguous state: {root / PREFERRED_TARGET_REL}")
        if (root / RUNTIME_WHEELHOUSE_REL).exists():
            raise RuntimeError(f"Runtime ComfyUI wheelhouse unexpectedly exists; C3D refuses ambiguous state: {root / RUNTIME_WHEELHOUSE_REL}")

        boundary_before = snapshot_boundaries(root)
        write_json(output / "boundary_before.json", boundary_before)

        runtime_identity = verify_runtime_identity(root)
        write_json(output / "runtime_identity.json", runtime_identity)
        all_data["runtime_identity"] = runtime_identity

        c3c_folder, c3c_verification = find_exact_evidence(root / C3C_PACKAGE_DIR / "ACQUISITION_OUTPUT", EXPECTED_C3C_HASHES)
        write_json(output / "c3c_input_verification.json", c3c_verification)
        all_data["c3c"] = c3c_verification

        order_path, install_order = find_c3b_install_order(root)
        order_verification = {"verified": True, "path": str(order_path), "sha256": sha256_file(order_path), "entry_count": len(install_order["order"]), "cycle_or_mutual_dependency_nodes": install_order.get("cycle_or_mutual_dependency_nodes", [])}
        write_json(output / "c3b_install_order_verification.json", order_verification)

        wheelhouse = root / C3C_WHEELHOUSE_REL
        rows, c3c_documents = load_inventory(c3c_folder, wheelhouse)
        write_json(output / "c3c_documents_summary.json", c3c_documents)

        wheelhouse_result = reverify_wheelhouse(rows, wheelhouse)
        write_json(output / "wheelhouse_reverification.json", wheelhouse_result)
        all_data["wheelhouse"] = wheelhouse_result

        payload, collisions, pth, entry_points = analyze_wheels(rows, wheelhouse)
        write_json(output / "wheel_payload_analysis.json", payload)
        write_json(output / "destination_collision_report.json", collisions)
        write_json(output / "pth_review.json", pth)
        write_json(output / "entry_points_review.json", entry_points)
        all_data.update({"payload": payload, "collisions": collisions, "pth": pth, "entry_points": entry_points})
        if payload["unknown_data_schemes"]:
            blocking.append(f"Unknown wheel .data installation schemes: {payload['unknown_data_schemes']}")
        if collisions["case_insensitive_cross_wheel_collision_count"]:
            blocking.append(f"Detected {collisions['case_insensitive_cross_wheel_collision_count']} cross-wheel destination file collisions")
        if pth["pth_files_with_executable_import_lines"]:
            review_findings.append(f"{pth['pth_files_with_executable_import_lines']} .pth file(s) contain executable import lines; exact contents are recorded in pth_review.json and must remain visible in C3E testing")

        ordered_rows = order_rows(rows, install_order)
        requirements_path = output / "exact-offline-install-requirements.txt"
        requirements_manifest = generate_requirements(requirements_path, ordered_rows, wheelhouse)
        write_json(output / "exact_install_lock.json", requirements_manifest)

        pip_capability = probe_pip(output)
        write_json(output / "pip_capability.json", pip_capability)
        all_data["pip_capability"] = pip_capability
        if not pip_capability["verified"]:
            blocking.append("No approved pip installer engine is available with all required no-action/install-control options")
            pip_dry_result = {"skipped": True, "reason": "pip capability failed"}
            pip_dry_validation = {"verified": False, "skipped": True, "issues": ["pip capability failed"]}
        else:
            pip_dry_result, pip_dry_validation = run_pip_dry_run(output, requirements_path, ordered_rows, pip_capability["selected_engine"])
            if not pip_dry_validation.get("verified"):
                blocking.append("Exact local pip dry-run did not reproduce all 96 locked wheel name/version/hash selections")
        write_json(output / "pip_dry_run_execution.json", pip_dry_result)
        write_json(output / "pip_dry_run_validation.json", pip_dry_validation)
        all_data["pip_dry_run_validation"] = pip_dry_validation

        usage = shutil.disk_usage(root)
        install_reserve = max(payload["total_uncompressed_bytes"] * 2, payload["total_uncompressed_bytes"] + 1024 * 1024 * 1024)
        space_plan = {
            "free_bytes": usage.free,
            "compressed_wheel_bytes": EXPECTED_COMPRESSED_BYTES,
            "exact_uncompressed_payload_bytes": payload["total_uncompressed_bytes"],
            "required_future_c3e_free_reserve_bytes": install_reserve,
            "sufficient": usage.free >= install_reserve,
            "note": "Reserve covers an adjacent transaction target, verification artifacts, and conservative overhead; C3D allocates none of it.",
        }
        if not space_plan["sufficient"]:
            blocking.append("Insufficient free space for the conservative C3E transaction reserve")
        write_json(output / "space_plan.json", space_plan)

        transaction = make_transaction_plan(root, output, requirements_path, pth, pip_capability)
        activation = make_activation_plan(root, pth)
        post_install = make_post_install_plan(root, rows)
        rollback = make_rollback_plan(root)
        write_json(output / "c3e_transaction_plan.json", transaction)
        write_json(output / "activation_plan.json", activation)
        write_json(output / "post_install_verification_plan.json", post_install)
        write_json(output / "rollback_plan.json", rollback)

        selected_engine = pip_capability.get("selected_engine") or {}
        operator_text = (
            "FOXAI USB C3D OPERATOR APPROVAL REQUEST\n\n"
            "C3D has prepared a plan only. No installation has occurred.\n\n"
            f"Reviewed installer engine: {selected_engine.get('label')} via {selected_engine.get('python')} with pip {selected_engine.get('pip_version')}.\n"
            "A future C3E may proceed only after exact review and a fresh explicit operator approval.\n"
            "C3E must install offline from the verified C3C wheelhouse into a new adjacent transaction staging directory, verify it, and commit by rename to Runtime\\ComfyUI\\site-packages.\n"
            "C3E must re-verify the installer engine, use --ignore-installed, must not modify either Python installation, and must not modify launchers or launch ComfyUI.\n\n"
            "Suggested approval wording after review:\n"
            "Proceed to USB C3E exact isolated installation under the reviewed C3D transaction and rollback boundaries.\n"
        )
        (output / "OPERATOR_APPROVAL_REQUEST.txt").write_text(operator_text, encoding="utf-8", newline="\n")

        if not blocking:
            classification_mode = SUCCESS_CLASSIFICATION
            state = "plan_complete_ready_for_exact_review"
        classification = {
            "mode": classification_mode,
            "verified": not blocking,
            "blocking_findings": blocking,
            "review_findings": review_findings,
            "notes": [
                "C3D is no-install and no-network.",
                "The exact C3C wheelhouse was re-hashed before planning.",
                "The selected approved pip engine was used only in dry-run mode with local hash-locked wheels, --no-index, and --no-deps.",
                "A successful C3D result authorizes operator review only, not target creation or package installation.",
            ],
            "next_gate": "Upload UPLOAD_THIS_C3D_REVIEW.zip for exact review. Do not create the target or run an installation until C3E is explicitly approved.",
        }
        write_json(output / "classification.json", classification)
        all_data["classification"] = classification

    except Exception as exc:
        blocking.append(f"{type(exc).__name__}: {exc}")
        (output / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        classification = {
            "mode": "C3D_BLOCKED_FAIL_CLOSED",
            "verified": False,
            "blocking_findings": blocking,
            "review_findings": review_findings,
            "notes": ["C3D stopped before any target creation or installation."],
            "next_gate": "Upload the C3D review bundle. Do not create or install the isolated target.",
        }
        write_json(output / "classification.json", classification)
        all_data["classification"] = classification

    finally:
        if boundary_before is None:
            try:
                boundary_before = snapshot_boundaries(root)
                write_json(output / "boundary_before.json", boundary_before)
            except Exception:
                boundary_before = {"error": "boundary snapshot unavailable"}
        try:
            boundary_after = snapshot_boundaries(root)
            write_json(output / "boundary_after.json", boundary_after)
            if isinstance(boundary_before, dict) and "key_files" in boundary_before:
                boundary_comparison = compare_boundaries(boundary_before, boundary_after)
            else:
                boundary_comparison = {"verified": False, "error": "before snapshot unavailable"}
            write_json(output / "boundary_comparison.json", boundary_comparison)
            if not boundary_comparison.get("verified"):
                blocking.append("Protected boundary comparison failed")
        except Exception as exc:
            boundary_comparison = {"verified": False, "error": f"{type(exc).__name__}: {exc}"}
            write_json(output / "boundary_comparison.json", boundary_comparison)
            blocking.append("Protected boundary comparison could not be completed")

        # Reconcile classification after final boundary checks.
        classification_path = output / "classification.json"
        classification = read_json(classification_path) if classification_path.is_file() else {}
        if blocking:
            classification.update({"mode": "C3D_BLOCKED_FAIL_CLOSED", "verified": False, "blocking_findings": list(dict.fromkeys(blocking))})
            state = "plan_blocked_fail_closed"
        else:
            classification.update({"mode": SUCCESS_CLASSIFICATION, "verified": True, "blocking_findings": []})
            state = "plan_complete_ready_for_exact_review"
        write_json(classification_path, classification)
        all_data["classification"] = classification

        completed = utc_now()
        receipt = {
            "action": ACTION,
            "state": state,
            "started": started.isoformat(),
            "completed": completed.isoformat(),
            "elapsed_seconds": round((completed - started).total_seconds(), 3),
            "verified": classification.get("verified", False),
            "root": str(root),
            "portable_python": str(root / EXPECTED_RELATIVE_PYTHON),
            "preferred_target": str(root / PREFERRED_TARGET_REL),
            "c3c_staging_wheelhouse": str(root / C3C_WHEELHOUSE_REL),
            "classification": classification.get("mode"),
            "blocking_findings": classification.get("blocking_findings", []),
            "exact_package_count": all_data.get("wheelhouse", {}).get("wheel_count"),
            "exact_compressed_bytes": all_data.get("wheelhouse", {}).get("compressed_bytes"),
            "exact_uncompressed_payload_bytes": all_data.get("payload", {}).get("total_uncompressed_bytes"),
            "pip_dry_run_install_count": all_data.get("pip_dry_run_validation", {}).get("install_count"),
            "network_access": False,
            "target_directory_created": (root / PREFERRED_TARGET_REL).exists(),
            "runtime_wheelhouse_created": (root / RUNTIME_WHEELHOUSE_REL).exists(),
            "package_install": False,
            "package_uninstall": False,
            "wheel_extraction": False,
            "package_copy": False,
            "local_build": False,
            "launcher_change": False,
            "foxai_launched": False,
            "webui_launched": False,
            "desktop_launched": False,
            "comfyui_launched": False,
            "writes_limited_to": str(package_dir),
            "protected_boundaries_unchanged": boundary_comparison.get("verified", False),
        }
        write_json(output / "receipt.json", receipt)
        all_data["receipt"] = receipt
        all_data.setdefault("wheelhouse", {})
        all_data.setdefault("payload", {})
        all_data.setdefault("collisions", {"case_insensitive_cross_wheel_collision_count": 0})
        all_data.setdefault("pth", {"pth_file_count": 0, "pth_files_with_executable_import_lines": 0})
        all_data.setdefault("pip_dry_run_validation", {})
        (output / "report.md").write_text(build_report(all_data), encoding="utf-8", newline="\n")
        create_evidence_integrity(output, excluded={"UPLOAD_THIS_C3D_REVIEW.zip"})
        review_zip = create_review_zip(output)
        print(f"C3D output: {output}")
        print(f"Review upload: {review_zip}")
        print(f"Classification: {classification.get('mode')}")
        print(f"Verified: {classification.get('verified')}")

    return 0 if classification.get("verified") else 20


if __name__ == "__main__":
    raise SystemExit(main())
