#!/usr/bin/env python3
"""FOXAI USB C3C — Exact Wheel Acquisition and Cryptographic Staging.

C3C consumes the exact, reviewed C3B closure evidence and acquires only those
approved wheel payloads into this package's isolated STAGING_WHEELHOUSE.

Authorized effects:
- HTTPS JSON metadata requests to pypi.org for exact release revalidation
- HTTPS wheel payload requests to the exact reviewed files.pythonhosted.org URLs
- new files only under FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION

Forbidden effects:
- no pip/uv/package installation or uninstallation
- no source distributions or local builds
- no creation or modification of Runtime/ComfyUI/site-packages
- no creation or modification of Runtime/ComfyUI/wheelhouse
- no Desktop/Core/ComfyUI/System/launcher changes
- no FOXAI/WebUI/Desktop/ComfyUI launch

The implementation is deliberately fail-closed. A payload enters the accepted
staging wheelhouse only after exact URL, response, size, SHA-256, filename tag,
ZIP structure, and wheel RECORD verification.
"""
from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import io
import json
import os
import platform
import re
import shutil
import ssl
import struct
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

ACTION = "foxai_usbc3c_exact_wheel_acquisition_and_cryptographic_staging"
EXPECTED_PORTABLE_VERSION = (3, 14, 6)
EXPECTED_RELATIVE_PYTHON = Path("Runtime/Desktop/python/python.exe")
PREFERRED_TARGET_REL = Path("Runtime/ComfyUI/site-packages")
RUNTIME_WHEELHOUSE_REL = Path("Runtime/ComfyUI/wheelhouse")
C3B_PACKAGE_DIR = "FOXAI_USBC3B_EXACT_ISOLATED_CLOSURE_PLAN"
EXPECTED_C3B_CLASSIFICATION = "C3B_READY_FOR_EXACT_WHEEL_ACQUISITION_REVIEW"
SUCCESS_CLASSIFICATION = "C3C_READY_FOR_EXACT_ISOLATED_INSTALL_REVIEW"
PYPI_JSON_HOST = "pypi.org"
PYPI_FILE_HOST = "files.pythonhosted.org"
MAX_JSON_BYTES = 32 * 1024 * 1024
USER_AGENT = "FOXAI-USBC3C/1.0.3 exact-wheel-acquisition-r3"

# These values bind C3C to the exact C3B output that was independently reviewed.
EXPECTED_C3B_HASHES = {
    "boundary_after.json": "8987c27dc641443eb2f2152255689d27f2871c23dd2d1cfac6f40ec4a12bdae2",
    "boundary_before.json": "c92b9b93da00324456a38976d19c13fa9ab767c7e0a5a4c89f1082842d2eb64c",
    "c3a_input_verification.json": "6f27db48291f3dfa8cc66aaae5218313290cad1bfbae9c4f523b786ff4852f40",
    "classification.json": "c6031ffa6f7ee6af3b45bd66a3a538be20dce010ed0e34ddd7438b67c81d4bc4",
    "closure_verification.json": "bcc371f2c6c9561b7452bc50261561515346bdf562380e767028eb09ea0539c0",
    "dependency_graph.json": "0d4034ad6e32ab32df71a5589cbb73877206cca07f937ba85279ea3ed1b4bef7",
    "direct_pins.in": "30978ff4a6e2f251038a6726c7c1b4a064c99112584ab02fc147fcc6112cbb83",
    "direct_requirements_exact.json": "b865c87a7a2e865def0ef4a8bf1ece6623566b2ddf73045b83eab0a0e6e6d120",
    "evidence_integrity.json": "73f39e348e92a78612bd44d00ad03def9a7048e8250e6b9a68ecfb8789e814d9",
    "exact_wheel_plan.json": "17fe4d11767605bebf6d4eb1dfa03d9b8baac2127f2e23b7e27a012c62e7155d",
    "footprint_estimate.json": "3346518aa30415362f5bf2a6105adef68eaa367acf4c2cc099e3c59e67f3fe53",
    "install_order.json": "0a629dc4976edc270665eaf703f8c40fbfc2519562241227b75ea289df39b406",
    "network_metadata_log.json": "f3e5dd2b2745b279ef178f3c95bf94b4cfab58b078bf9540b36af68059c7a788",
    "receipt.json": "07f35f15a3bb41aba53f18774fb08eeca1440044dd131b3696c16ba6929d79df",
    "report.md": "acb034eb59e1ac85ab74a492225c82f3d741015f2096675b4322405ae4fbdca8",
    "requirements-exact-windows-cp314.txt": "3c18ffc1e0e55508f8c4d174abef3c88f901aa05875f12bd4c7e8b3436ac143b",
    "resolution_history.json": "64576a4f356eec2247030b86cc3cab563f78d030b89a035bd240372386077666",
    "rollback_boundaries.json": "671c467c9e09af9af52c0268a9f7874fcd30a7600ef192ee00553639c98f9e44",
    "selected_host_inventory_summary.json": "2185ede44aa2744a1e4dc8da71530d57e0c85db68852b9fdeae5c1ba52929ad8",
    "source_policy.json": "bdb11a9f8099ce0dfac029beaaf396b139f6cea9017fa2f5d9fe4cecf215f1c7",
    "wheel-download-manifest.csv": "b35814df5d406db3ed5583dda80c8123c1ff888e2ec8e2aedcff5aeb420f07d4",
}
EXPECTED_C3B_PACKAGE_COUNT = 96
EXPECTED_C3B_COMPRESSED_BYTES = 718_175_632
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.+!-]+\.whl$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def timestamp_slug() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except Exception:
        return path.absolute()


def is_under(path: Path, parent: Path) -> bool:
    try:
        safe_resolve(path).relative_to(safe_resolve(parent))
        return True
    except ValueError:
        return False


def file_record(path: Path, base: Path | None = None, include_hash: bool = True) -> dict[str, Any]:
    shown = str(path)
    try:
        if base and path.is_relative_to(base):
            shown = str(path.relative_to(base))
        stat = path.stat()
        rec: dict[str, Any] = {
            "path": shown,
            "exists": True,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
        if include_hash and path.is_file():
            rec["sha256"] = sha256_file(path)
        return rec
    except Exception as exc:
        return {"path": shown, "exists": path.exists(), "error": f"{type(exc).__name__}: {exc}"}


def directory_state(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path), "exists": path.exists(), "is_directory": path.is_dir()}
    if path.is_dir():
        try:
            entries = sorted(p.name for p in path.iterdir())
            rec["entry_count"] = len(entries)
            rec["entries_preview"] = entries[:100]
        except Exception as exc:
            rec["entry_error"] = f"{type(exc).__name__}: {exc}"
    return rec


def find_root(start: Path) -> Path | None:
    resolved = safe_resolve(start)
    for candidate in [resolved, *resolved.parents]:
        if (candidate / "ComfyUI/main.py").is_file() and (candidate / EXPECTED_RELATIVE_PYTHON).is_file():
            return candidate
    return None


def normalize_windows_path(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(safe_resolve(path))))


def verify_runtime_identity(root: Path) -> dict[str, Any]:
    expected_python = root / EXPECTED_RELATIVE_PYTHON
    actual = Path(sys.executable)
    result = {
        "expected_python": str(expected_python),
        "actual_python": str(actual),
        "version": list(sys.version_info[:3]),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pointer_bits": struct.calcsize("P") * 8,
        "checks": {},
    }
    result["checks"] = {
        "exact_executable": normalize_windows_path(expected_python) == normalize_windows_path(actual),
        "exact_version": tuple(sys.version_info[:3]) == EXPECTED_PORTABLE_VERSION,
        "cpython": platform.python_implementation() == "CPython",
        "64_bit": struct.calcsize("P") * 8 == 64,
    }
    if not all(result["checks"].values()):
        raise RuntimeError(f"Portable runtime identity check failed: {result}")
    return result


class PackagingAPI:
    def __init__(self, root: Path):
        desktop_site = root / "Runtime/Desktop/site-packages"
        if not desktop_site.is_dir():
            raise RuntimeError(f"Verified Desktop site-packages is missing: {desktop_site}")
        sys.path.insert(0, str(desktop_site))
        try:
            from packaging.tags import sys_tags
            from packaging.utils import canonicalize_name, parse_wheel_filename
            from packaging.version import Version
        except Exception as exc:
            raise RuntimeError(f"Could not load verified read-only packaging library: {type(exc).__name__}: {exc}") from exc
        self.canonicalize_name = canonicalize_name
        self.parse_wheel_filename = parse_wheel_filename
        self.Version = Version
        self.supported_tags = frozenset(sys_tags())
        self.source = str(desktop_site)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect rejected: {newurl}", headers, fp)


class ExactNetworkClient:
    def __init__(self):
        context = ssl.create_default_context()
        https_handler = urllib.request.HTTPSHandler(context=context)
        self.opener = urllib.request.build_opener(NoRedirectHandler(), https_handler)
        self.log: list[dict[str, Any]] = []
        self.metadata_bytes = 0
        self.payload_bytes = 0

    def fetch_json(self, url: str, purpose: str) -> dict[str, Any]:
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != PYPI_JSON_HOST
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise RuntimeError(f"Metadata URL rejected by strict allowlist: {url}")
        started = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with self.opener.open(req, timeout=60) as response:
                status = getattr(response, "status", 200)
                final_url = response.geturl()
                if status != 200 or final_url != url:
                    raise RuntimeError(f"Unexpected metadata response status/final URL: {status} {final_url}")
                length_header = response.headers.get("Content-Length")
                if length_header and int(length_header) > MAX_JSON_BYTES:
                    raise RuntimeError(f"Metadata response exceeds {MAX_JSON_BYTES} bytes")
                payload = response.read(MAX_JSON_BYTES + 1)
                if len(payload) > MAX_JSON_BYTES:
                    raise RuntimeError("Metadata response exceeded maximum allowed size")
                data = json.loads(payload.decode("utf-8"))
                self.metadata_bytes += len(payload)
                self.log.append({
                    "kind": "metadata",
                    "purpose": purpose,
                    "url": url,
                    "final_url": final_url,
                    "status": status,
                    "bytes": len(payload),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "content_type": response.headers.get("Content-Type"),
                })
                return data
        except Exception as exc:
            self.log.append({
                "kind": "metadata",
                "purpose": purpose,
                "url": url,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            raise

    def download_exact(self, item: dict[str, Any], destination: Path) -> dict[str, Any]:
        url = item["url"]
        expected_size = int(item["size_bytes"])
        expected_hash = item["sha256"]
        expected_filename = item["filename"]
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != PYPI_FILE_HOST
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or Path(urllib.parse.unquote(parsed.path)).name != expected_filename
        ):
            raise RuntimeError(f"Wheel URL rejected by strict allowlist: {url}")
        if destination.exists():
            raise RuntimeError(f"Partial destination already exists; refusing overwrite: {destination}")
        started = time.monotonic()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/octet-stream, application/zip;q=0.9, */*;q=0.1",
                "Accept-Encoding": "identity",
            },
        )
        h = hashlib.sha256()
        total = 0
        try:
            with self.opener.open(req, timeout=180) as response:
                status = getattr(response, "status", 200)
                final_url = response.geturl()
                if status != 200:
                    raise RuntimeError(f"Unexpected wheel HTTP status: {status}")
                if final_url != url:
                    raise RuntimeError(f"Wheel redirect/final URL change rejected: {final_url}")
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) != expected_size:
                    raise RuntimeError(
                        f"Wheel Content-Length changed: expected {expected_size}, got {content_length}"
                    )
                content_type = (response.headers.get("Content-Type") or "").lower()
                if "text/html" in content_type or "application/json" in content_type:
                    raise RuntimeError(f"Wheel response has unsafe content type: {content_type}")
                with destination.open("xb") as out:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > expected_size:
                            raise RuntimeError("Wheel response exceeded exact expected byte size")
                        h.update(block)
                        out.write(block)
                    out.flush()
                    os.fsync(out.fileno())
            actual_hash = h.hexdigest()
            if total != expected_size:
                raise RuntimeError(f"Wheel size mismatch: expected {expected_size}, got {total}")
            if actual_hash != expected_hash:
                raise RuntimeError(f"Wheel SHA-256 mismatch: expected {expected_hash}, got {actual_hash}")
            self.payload_bytes += total
            record = {
                "kind": "wheel",
                "name": item["name"],
                "version": item["version"],
                "filename": expected_filename,
                "url": url,
                "final_url": final_url,
                "status": 200,
                "bytes": total,
                "sha256": actual_hash,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "content_type": content_type,
                "content_length": int(content_length) if content_length is not None else None,
                "content_length_present": content_length is not None,
            }
            self.log.append(record)
            return record
        except Exception as exc:
            self.log.append({
                "kind": "wheel",
                "name": item.get("name"),
                "version": item.get("version"),
                "filename": expected_filename,
                "url": url,
                "status": "failed",
                "bytes_written": total,
                "partial_path": str(destination),
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            raise


def verify_c3b_evidence(root: Path) -> tuple[Path, dict[str, Any]]:
    outputs = root / C3B_PACKAGE_DIR / "PLAN_OUTPUT"
    if not outputs.is_dir():
        raise RuntimeError(f"Reviewed C3B PLAN_OUTPUT folder is missing: {outputs}")
    candidates = sorted((p for p in outputs.iterdir() if p.is_dir()), reverse=True)
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        result: dict[str, Any] = {"candidate": str(candidate), "checks": {}, "mismatches": []}
        try:
            for name, expected_hash in EXPECTED_C3B_HASHES.items():
                path = candidate / name
                if not path.is_file():
                    result["mismatches"].append(f"missing:{name}")
                    continue
                actual = sha256_file(path)
                if actual != expected_hash:
                    result["mismatches"].append(f"sha256:{name}:{actual}")
            if result["mismatches"]:
                attempts.append(result)
                continue
            integrity = read_json(candidate / "evidence_integrity.json")
            listed = {entry["name"]: entry for entry in integrity.get("files", [])}
            if integrity.get("count") != 20 or set(listed) != (set(EXPECTED_C3B_HASHES) - {"evidence_integrity.json"}):
                raise RuntimeError("C3B internal evidence manifest file set/count is not exact")
            for name, entry in listed.items():
                path = candidate / name
                if int(entry.get("size_bytes", -1)) != path.stat().st_size:
                    raise RuntimeError(f"C3B internal size mismatch: {name}")
                if entry.get("sha256") != sha256_file(path):
                    raise RuntimeError(f"C3B internal hash mismatch: {name}")
            classification = read_json(candidate / "classification.json")
            receipt = read_json(candidate / "receipt.json")
            wheel_plan = read_json(candidate / "exact_wheel_plan.json")
            checks = {
                "classification": classification.get("mode") == EXPECTED_C3B_CLASSIFICATION,
                "no_blockers": classification.get("blocking_findings") == [],
                "receipt_verified": receipt.get("verified") is True,
                "receipt_state": receipt.get("state") == "plan_complete_ready_for_exact_review",
                "receipt_classification": receipt.get("classification") == EXPECTED_C3B_CLASSIFICATION,
                "no_wheel_payload_download": receipt.get("wheel_payload_download") is False,
                "no_target_creation": receipt.get("target_directory_created") is False,
                "package_count": wheel_plan.get("package_count") == EXPECTED_C3B_PACKAGE_COUNT,
                "compressed_bytes": wheel_plan.get("compressed_wheel_bytes") == EXPECTED_C3B_COMPRESSED_BYTES,
            }
            result["checks"] = checks
            if not all(checks.values()):
                result["mismatches"].append("semantic_continuity_gate_failed")
                attempts.append(result)
                continue
            result["verified"] = True
            result["expected_hashes"] = EXPECTED_C3B_HASHES
            return candidate, {"selected": str(candidate), "verified": True, "attempts": attempts + [result]}
        except Exception as exc:
            result["mismatches"].append(f"{type(exc).__name__}: {exc}")
            attempts.append(result)
    raise RuntimeError(f"No exact reviewed C3B output matched continuity gate. Attempts: {attempts}")


def load_and_validate_manifest(c3b_dir: Path, packaging_api: PackagingAPI) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = c3b_dir / "wheel-download-manifest.csv"
    plan = read_json(c3b_dir / "exact_wheel_plan.json")
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    expected_fields = [
        "order", "name", "version", "direct", "selection_reason", "filename", "selected_tag",
        "size_bytes", "sha256", "url", "source_index", "requires_python", "upload_time_iso_8601",
    ]
    if not rows or list(rows[0].keys()) != expected_fields:
        raise RuntimeError("C3B wheel manifest schema does not match reviewed schema")
    if len(rows) != EXPECTED_C3B_PACKAGE_COUNT:
        raise RuntimeError(f"Manifest package count changed: {len(rows)}")
    plan_wheels = plan.get("wheels", [])
    if len(plan_wheels) != len(rows):
        raise RuntimeError("Manifest and exact wheel plan counts differ")
    items: list[dict[str, Any]] = []
    names: set[str] = set()
    filenames: set[str] = set()
    urls: set[str] = set()
    total = 0
    for index, (row, planned) in enumerate(zip(rows, plan_wheels, strict=True), start=1):
        if int(row["order"]) != index:
            raise RuntimeError(f"Manifest order is not exact at row {index}")
        canonical = packaging_api.canonicalize_name(row["name"])
        if canonical in names:
            raise RuntimeError(f"Duplicate canonical package name: {canonical}")
        filename = row["filename"]
        if filename in filenames or not SAFE_FILENAME_RE.fullmatch(filename):
            raise RuntimeError(f"Duplicate or unsafe wheel filename: {filename}")
        if row["url"] in urls:
            raise RuntimeError(f"Duplicate wheel URL: {row['url']}")
        if not HEX64_RE.fullmatch(row["sha256"]):
            raise RuntimeError(f"Malformed SHA-256 for {filename}")
        size = int(row["size_bytes"])
        if size <= 0:
            raise RuntimeError(f"Invalid wheel size for {filename}")
        parsed = urllib.parse.urlsplit(row["url"])
        if (
            parsed.scheme != "https" or parsed.hostname != PYPI_FILE_HOST or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or Path(urllib.parse.unquote(parsed.path)).name != filename
        ):
            raise RuntimeError(f"Unsafe manifest URL: {row['url']}")
        parsed_name, parsed_version, _build, wheel_tags = packaging_api.parse_wheel_filename(filename)
        if packaging_api.canonicalize_name(parsed_name) != canonical:
            raise RuntimeError(f"Filename project mismatch for {filename}")
        if packaging_api.Version(row["version"]) != parsed_version:
            raise RuntimeError(f"Filename version mismatch for {filename}")
        if not (set(wheel_tags) & packaging_api.supported_tags):
            raise RuntimeError(f"Wheel no longer matches this portable interpreter: {filename}")
        item = {
            "order": index,
            "name": canonical,
            "display_name": row["name"],
            "version": row["version"],
            "direct": row["direct"].strip().lower() == "true",
            "selection_reason": row["selection_reason"],
            "filename": filename,
            "selected_tag": row["selected_tag"],
            "size_bytes": size,
            "sha256": row["sha256"],
            "url": row["url"],
            "source_index": row["source_index"],
            "requires_python": row["requires_python"],
            "upload_time_iso_8601": row["upload_time_iso_8601"],
            "metadata_api": planned.get("metadata_api"),
        }
        for key in ["name", "version", "filename", "url", "size_bytes", "sha256", "selected_tag"]:
            plan_value = planned.get(key)
            compare_value = item[key]
            if key == "name":
                plan_value = packaging_api.canonicalize_name(str(plan_value))
            if plan_value != compare_value:
                raise RuntimeError(f"C3B CSV/JSON mismatch for {filename}: {key}")
        names.add(canonical)
        filenames.add(filename)
        urls.add(row["url"])
        total += size
        items.append(item)
    if total != EXPECTED_C3B_COMPRESSED_BYTES:
        raise RuntimeError(f"Manifest byte total changed: expected {EXPECTED_C3B_COMPRESSED_BYTES}, got {total}")
    summary = {
        "verified": True,
        "package_count": len(items),
        "compressed_wheel_bytes": total,
        "unique_names": len(names),
        "unique_filenames": len(filenames),
        "unique_urls": len(urls),
        "all_urls_https": True,
        "only_approved_file_host": True,
        "source_distributions": 0,
        "packaging_source": packaging_api.source,
        "supported_tag_count": len(packaging_api.supported_tags),
    }
    return items, summary


def metadata_revalidate(items: list[dict[str, Any]], client: ExactNetworkClient, packaging_api: PackagingAPI) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    total_items = len(items)
    for position, item in enumerate(items, start=1):
        print(f"[META {position:03d}/{total_items:03d}] {item['name']}=={item['version']}", flush=True)
        url = item.get("metadata_api") or (
            f"https://{PYPI_JSON_HOST}/pypi/{urllib.parse.quote(item['display_name'], safe='')}/"
            f"{urllib.parse.quote(item['version'], safe='')}/json"
        )
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != PYPI_JSON_HOST or not parsed.path.endswith("/json"):
            raise RuntimeError(f"Unsafe C3B metadata API URL: {url}")
        data = client.fetch_json(url, f"revalidate:{item['name']}=={item['version']}")
        info = data.get("info", {})
        files = data.get("urls", [])
        matches = [f for f in files if f.get("filename") == item["filename"]]
        if len(matches) != 1:
            raise RuntimeError(f"Exact wheel disappeared or became ambiguous: {item['filename']}")
        selected = matches[0]
        digest = (selected.get("digests") or {}).get("sha256")
        checks = {
            "project": packaging_api.canonicalize_name(str(info.get("name", ""))) == item["name"],
            "version": str(info.get("version")) == item["version"],
            "packagetype": selected.get("packagetype") == "bdist_wheel",
            "url": selected.get("url") == item["url"],
            "size": int(selected.get("size", -1)) == item["size_bytes"],
            "sha256": digest == item["sha256"],
            "not_yanked": selected.get("yanked") is False,
            "upload_time": selected.get("upload_time_iso_8601") == item["upload_time_iso_8601"],
            "requires_python": (selected.get("requires_python") or "") == (item["requires_python"] or ""),
        }
        result = {
            "name": item["name"],
            "version": item["version"],
            "filename": item["filename"],
            "checks": checks,
            "current_upload_time_iso_8601": selected.get("upload_time_iso_8601"),
            "current_requires_python": selected.get("requires_python"),
            "yanked_reason": selected.get("yanked_reason"),
        }
        results.append(result)
        if not all(checks.values()):
            raise RuntimeError(f"PyPI metadata changed for {item['filename']}: {checks}")
    return {
        "verified": True,
        "package_count": len(results),
        "all_exact_files_available": True,
        "all_not_yanked": True,
        "all_hashes_sizes_urls_unchanged": True,
        "results": results,
    }


def decode_record_digest(value: str) -> tuple[str, bytes]:
    if "=" not in value:
        raise RuntimeError(f"Malformed RECORD digest: {value}")
    algorithm, encoded = value.split("=", 1)
    if algorithm not in hashlib.algorithms_available:
        raise RuntimeError(f"Unsupported RECORD digest algorithm: {algorithm}")
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    try:
        digest = base64.urlsafe_b64decode(encoded + padding)
    except Exception as exc:
        raise RuntimeError(f"Malformed RECORD base64 digest: {value}") from exc
    return algorithm, digest


def safe_member_name(name: str) -> bool:
    if "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and bool(path.parts)


def validate_wheel_structure(path: Path, item: dict[str, Any], packaging_api: PackagingAPI) -> dict[str, Any]:
    if path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
        raise RuntimeError(f"Outer cryptographic verification failed before wheel inspection: {path.name}")

    # Newly downloaded wheels are deliberately held under a non-installable
    # ``.partial`` filename until every acceptance test passes. Parse the exact
    # reviewed wheel filename from the immutable C3B manifest, while separately
    # binding the on-disk temporary/final name to that manifest entry.
    expected_disk_names = {
        item["filename"],
        f"{item['order']:03d}__{item['filename']}.partial",
    }
    if path.name not in expected_disk_names:
        raise RuntimeError(
            f"Wheel staging filename is not bound to the exact manifest entry: "
            f"actual={path.name!r}, expected={sorted(expected_disk_names)!r}"
        )
    parsed_name, parsed_version, _build, filename_tags = packaging_api.parse_wheel_filename(item["filename"])
    if packaging_api.canonicalize_name(parsed_name) != item["name"] or str(parsed_version) != item["version"]:
        raise RuntimeError(f"Wheel filename identity mismatch: {path.name}")
    if not (set(filename_tags) & packaging_api.supported_tags):
        raise RuntimeError(f"Wheel tags are incompatible with portable Python: {path.name}")
    try:
        zf = zipfile.ZipFile(path, "r")
    except Exception as exc:
        raise RuntimeError(f"Wheel is not a readable ZIP archive: {path.name}: {exc}") from exc
    with zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise RuntimeError(f"Wheel has duplicate archive member names: {path.name}")
        if not names:
            raise RuntimeError(f"Wheel is empty: {path.name}")
        # ZIP archives may contain explicit directory placeholder entries ending
        # in "/". Wheel RECORD files describe installed file payloads and normally
        # do not list those directory placeholders. Keep validating every archive
        # entry for path safety, encryption, and symlinks, but compare and verify
        # RECORD against non-directory file members only.
        file_infos = [i for i in infos if not i.is_dir()]
        file_names = [i.filename for i in file_infos]
        if not file_infos:
            raise RuntimeError(f"Wheel contains no file members: {path.name}")
        total_uncompressed = 0
        for info in infos:
            if not safe_member_name(info.filename):
                raise RuntimeError(f"Unsafe wheel member path in {path.name}: {info.filename}")
            if info.flag_bits & 0x1:
                raise RuntimeError(f"Encrypted wheel member rejected: {path.name}:{info.filename}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if (mode & 0o170000) == 0o120000:
                raise RuntimeError(f"Symbolic link wheel member rejected: {path.name}:{info.filename}")
            total_uncompressed += info.file_size
        # The wheel's primary distribution metadata directory is required to be a
        # top-level ``*.dist-info`` directory. Some legitimate wheels (notably
        # setuptools) vendor other distributions whose own ``*.dist-info`` files
        # live deeper inside package directories. Those vendored metadata files are
        # ordinary payload members and remain fully covered by the primary RECORD;
        # they must not be mistaken for additional primary wheel metadata.
        def is_top_level_dist_info_member(member: str, leaf: str) -> bool:
            parts = PurePosixPath(member).parts
            return len(parts) == 2 and parts[0].endswith(".dist-info") and parts[1] == leaf

        record_names = [n for n in file_names if is_top_level_dist_info_member(n, "RECORD")]
        wheel_names = [n for n in file_names if is_top_level_dist_info_member(n, "WHEEL")]
        metadata_names = [n for n in file_names if is_top_level_dist_info_member(n, "METADATA")]
        if len(record_names) != 1 or len(wheel_names) != 1 or len(metadata_names) != 1:
            raise RuntimeError(
                f"Wheel must contain exactly one top-level RECORD, WHEEL, and METADATA: {path.name}"
            )
        record_name = record_names[0]
        dist_info_prefix = record_name[: -len("RECORD")]
        if wheel_names[0] != dist_info_prefix + "WHEEL" or metadata_names[0] != dist_info_prefix + "METADATA":
            raise RuntimeError(f"Wheel top-level dist-info metadata directories disagree: {path.name}")
        wheel_text = zf.read(wheel_names[0]).decode("utf-8")
        metadata_bytes = zf.read(metadata_names[0])
        metadata_message = email.parser.BytesParser().parsebytes(metadata_bytes)
        metadata_project = packaging_api.canonicalize_name(str(metadata_message.get("Name", "")))
        metadata_version = str(metadata_message.get("Version", ""))
        if metadata_project != item["name"] or metadata_version != item["version"]:
            raise RuntimeError(
                f"Wheel METADATA identity mismatch: {path.name}: {metadata_project}=={metadata_version}"
            )
        declared_tags = {
            line.split(":", 1)[1].strip() for line in wheel_text.splitlines() if line.lower().startswith("tag:")
        }
        filename_tag_strings = {str(tag) for tag in filename_tags}
        if not (declared_tags & filename_tag_strings):
            raise RuntimeError(f"WHEEL Tag fields do not support filename tags: {path.name}")
        record_text = zf.read(record_name).decode("utf-8")
        reader = csv.reader(io.StringIO(record_text))
        record_rows: dict[str, tuple[str, str]] = {}
        for row in reader:
            if len(row) != 3:
                raise RuntimeError(f"Malformed RECORD row in {path.name}: {row}")
            member, digest, size = row
            if member in record_rows:
                raise RuntimeError(f"Duplicate RECORD member in {path.name}: {member}")
            record_rows[member] = (digest, size)
        if set(record_rows) != set(file_names):
            missing = sorted(set(file_names) - set(record_rows))[:10]
            extra = sorted(set(record_rows) - set(file_names))[:10]
            raise RuntimeError(
                f"RECORD/archive file-member mismatch in {path.name}; "
                f"missing={missing}, extra={extra}"
            )
        verified_members = 0
        verified_bytes = 0
        for info in file_infos:
            digest_text, size_text = record_rows[info.filename]
            if info.filename == record_name:
                if digest_text or size_text:
                    raise RuntimeError(f"RECORD self-entry must have empty digest and size: {path.name}")
                continue
            if not digest_text or not size_text:
                raise RuntimeError(f"Unsigned or unsized wheel member rejected: {path.name}:{info.filename}")
            expected_member_size = int(size_text)
            if expected_member_size != info.file_size:
                raise RuntimeError(f"RECORD size mismatch: {path.name}:{info.filename}")
            algorithm, expected_digest = decode_record_digest(digest_text)
            h = hashlib.new(algorithm)
            actual_size = 0
            with zf.open(info, "r") as member_file:
                while True:
                    block = member_file.read(1024 * 1024)
                    if not block:
                        break
                    actual_size += len(block)
                    h.update(block)
            if actual_size != expected_member_size or h.digest() != expected_digest:
                raise RuntimeError(f"RECORD digest mismatch: {path.name}:{info.filename}")
            verified_members += 1
            verified_bytes += actual_size
        return {
            "name": item["name"],
            "version": item["version"],
            "filename": path.name,
            "outer_size_bytes": path.stat().st_size,
            "outer_sha256": item["sha256"],
            "archive_member_count": len(infos),
            "archive_file_member_count": len(file_infos),
            "archive_directory_member_count": len(infos) - len(file_infos),
            "total_uncompressed_bytes": total_uncompressed,
            "record_verified_members": verified_members,
            "record_verified_bytes": verified_bytes,
            "dist_info_prefix": dist_info_prefix,
            "metadata_name": metadata_project,
            "metadata_version": metadata_version,
            "declared_tags": sorted(declared_tags),
            "filename_tags": sorted(filename_tag_strings),
            "verified": True,
        }


def validate_staging_wheelhouse(staging: Path, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected = {item["filename"]: item for item in items}
    reused: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    if staging.exists() and not staging.is_dir():
        raise RuntimeError(f"Staging wheelhouse path exists but is not a directory: {staging}")
    if staging.is_dir():
        entries = list(staging.iterdir())
        unexpected = [p.name for p in entries if not p.is_file() or p.name not in expected]
        if unexpected:
            raise RuntimeError(f"Unexpected staging wheelhouse entries rejected: {sorted(unexpected)}")
        for path in entries:
            item = expected[path.name]
            actual_size = path.stat().st_size
            actual_hash = sha256_file(path)
            if actual_size != item["size_bytes"] or actual_hash != item["sha256"]:
                raise RuntimeError(
                    f"Existing staging wheel differs from exact manifest; refusing overwrite: {path.name}"
                )
            reused.append({
                "filename": path.name,
                "size_bytes": actual_size,
                "sha256": actual_hash,
                "status": "reused_exact_existing",
            })
    present = {r["filename"] for r in reused}
    missing = [item for item in items if item["filename"] not in present]
    return reused, missing


def inventory_staging(staging: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {item["filename"]: item for item in items}
    entries = sorted(staging.iterdir(), key=lambda p: p.name) if staging.is_dir() else []
    if any(not p.is_file() for p in entries):
        raise RuntimeError("Staging wheelhouse contains non-file entries")
    if {p.name for p in entries} != set(expected):
        missing = sorted(set(expected) - {p.name for p in entries})
        extra = sorted({p.name for p in entries} - set(expected))
        raise RuntimeError(f"Final staging set is not exact; missing={missing}, extra={extra}")
    files: list[dict[str, Any]] = []
    total = 0
    for path in entries:
        item = expected[path.name]
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != item["size_bytes"] or digest != item["sha256"]:
            raise RuntimeError(f"Final staging inventory verification failed: {path.name}")
        files.append({
            "name": item["name"],
            "version": item["version"],
            "filename": path.name,
            "size_bytes": size,
            "sha256": digest,
            "path": str(path),
        })
        total += size
    if len(files) != EXPECTED_C3B_PACKAGE_COUNT or total != EXPECTED_C3B_COMPRESSED_BYTES:
        raise RuntimeError("Final staging inventory count or byte total changed")
    return {
        "verified": True,
        "wheel_count": len(files),
        "total_bytes": total,
        "unexpected_entries": [],
        "missing_entries": [],
        "files": files,
    }


def boundary_snapshot(root: Path, package_dir: Path, staging: Path) -> dict[str, Any]:
    protected_files = [
        root / EXPECTED_RELATIVE_PYTHON,
        root / "ComfyUI/main.py",
        root / "START_FOXAI_CLEAN.bat",
    ]
    return {
        "captured": iso_now(),
        "root": str(root),
        "preferred_target": directory_state(root / PREFERRED_TARGET_REL),
        "runtime_wheelhouse": directory_state(root / RUNTIME_WHEELHOUSE_REL),
        "desktop_runtime": directory_state(root / "Runtime/Desktop"),
        "core_runtime": directory_state(root / "Runtime/Core"),
        "comfyui_source": directory_state(root / "ComfyUI"),
        "package_directory": str(package_dir),
        "staging_wheelhouse": directory_state(staging),
        "protected_files": [file_record(p, root, include_hash=True) for p in protected_files],
    }


def compare_protected_boundaries(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_files = {r["path"]: r for r in before.get("protected_files", [])}
    after_files = {r["path"]: r for r in after.get("protected_files", [])}
    file_checks: list[dict[str, Any]] = []
    for name in sorted(set(before_files) | set(after_files)):
        b = before_files.get(name, {})
        a = after_files.get(name, {})
        same = (
            b.get("exists") == a.get("exists")
            and b.get("size_bytes") == a.get("size_bytes")
            and b.get("sha256") == a.get("sha256")
        )
        file_checks.append({"path": name, "unchanged": same, "before": b, "after": a})
    target_before = before["preferred_target"]
    target_after = after["preferred_target"]
    runtime_wh_before = before["runtime_wheelhouse"]
    runtime_wh_after = after["runtime_wheelhouse"]
    checks = {
        "protected_files_unchanged": all(x["unchanged"] for x in file_checks),
        "preferred_target_unchanged": target_before == target_after,
        "preferred_target_not_created": not target_after.get("exists", False),
        "runtime_wheelhouse_unchanged": runtime_wh_before == runtime_wh_after,
    }
    return {"verified": all(checks.values()), "checks": checks, "file_checks": file_checks}


def create_evidence_integrity(output: Path) -> dict[str, Any]:
    excluded = {"evidence_integrity.json", "UPLOAD_THIS_C3C_REVIEW.zip", "review_bundle_info.json"}
    files: list[dict[str, Any]] = []
    for path in sorted(output.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name in excluded:
            continue
        files.append({"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    obj = {"count": len(files), "files": files}
    write_json(output / "evidence_integrity.json", obj)
    return obj


def create_review_bundle(output: Path) -> dict[str, Any]:
    bundle = output / "UPLOAD_THIS_C3C_REVIEW.zip"
    included: list[dict[str, Any]] = []
    with zipfile.ZipFile(bundle, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(output.iterdir(), key=lambda p: p.name):
            if not path.is_file() or path.name in {bundle.name, "review_bundle_info.json"}:
                continue
            zf.write(path, arcname=path.name)
            included.append({"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    info = {
        "bundle": bundle.name,
        "size_bytes": bundle.stat().st_size,
        "sha256": sha256_file(bundle),
        "wheel_payloads_included": False,
        "included_file_count": len(included),
        "included_files": included,
    }
    write_json(output / "review_bundle_info.json", info)
    return info


def write_report(output: Path, data: dict[str, Any]) -> None:
    lines = [
        "# FOXAI USB C3C — Exact Wheel Acquisition and Cryptographic Staging",
        "",
        f"- State: `{data['state']}`",
        f"- Classification: `{data['classification']}`",
        f"- Verified: `{str(data['verified']).lower()}`",
        f"- Exact wheels accepted: `{data.get('accepted_wheels', 0)}`",
        f"- Exact staged bytes: `{data.get('accepted_bytes', 0)}`",
        f"- Newly downloaded wheels: `{data.get('downloaded_wheels', 0)}`",
        f"- Reused exact wheels: `{data.get('reused_wheels', 0)}`",
        f"- Metadata requests: `{data.get('metadata_requests', 0)}`",
        f"- Wheel requests: `{data.get('wheel_requests', 0)}`",
        "",
        "## Safety boundary",
        "",
        "- No package installation or uninstallation occurred.",
        "- No source archive or local build was used.",
        "- Runtime/ComfyUI/site-packages was not created or modified.",
        "- Runtime/ComfyUI/wheelhouse was not created or modified.",
        "- Desktop, Core, ComfyUI source, System, and launchers were not modified.",
        "- FOXAI, WebUI, Desktop, and ComfyUI were not launched.",
        "",
    ]
    blockers = data.get("blocking_findings", [])
    if blockers:
        lines += ["## Blocking findings", ""] + [f"- {x}" for x in blockers] + [""]
    lines += [
        "## Review upload",
        "",
        "Upload `UPLOAD_THIS_C3C_REVIEW.zip`. It contains evidence only and excludes wheel payloads.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    started_dt = utc_now()
    started_monotonic = time.monotonic()
    package_dir = Path(__file__).resolve().parents[2]
    root = safe_resolve(args.root)
    output_root = package_dir / "ACQUISITION_OUTPUT"
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / timestamp_slug()
    suffix = 0
    while output.exists():
        suffix += 1
        output = output_root / f"{timestamp_slug()}_{suffix:02d}"
    output.mkdir(parents=False, exist_ok=False)
    partials = output / "PARTIAL_DOWNLOADS"
    staging = package_dir / "STAGING_WHEELHOUSE"

    client = ExactNetworkClient()
    state = "stopped_fail_closed"
    classification = "C3C_BLOCKED_FAIL_CLOSED"
    blocking_findings: list[str] = []
    c3b_verification: dict[str, Any] = {}
    manifest_summary: dict[str, Any] = {}
    metadata_result: dict[str, Any] = {}
    acquisition_results: list[dict[str, Any]] = []
    structure_results: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {}
    runtime_identity: dict[str, Any] = {}
    boundary_before: dict[str, Any] = {}
    boundary_after: dict[str, Any] = {}
    boundary_comparison: dict[str, Any] = {}
    reused: list[dict[str, Any]] = []
    downloaded_count = 0
    package_api_source = None

    try:
        discovered = find_root(root)
        if discovered is None or safe_resolve(discovered) != root:
            raise RuntimeError(f"FOXAI root verification failed: {root}")
        if not is_under(package_dir, root):
            raise RuntimeError("C3C package is not located inside the verified FOXAI root")
        if package_dir.name != "FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION":
            raise RuntimeError(f"C3C package directory name changed: {package_dir.name}")
        runtime_identity = verify_runtime_identity(root)
        target = root / PREFERRED_TARGET_REL
        if target.exists():
            raise RuntimeError(f"Preferred isolated target already exists; C3C refuses ambiguous state: {target}")
        if not is_under(output, package_dir) or not is_under(staging, package_dir):
            raise RuntimeError("C3C write paths escaped the package directory")
        boundary_before = boundary_snapshot(root, package_dir, staging)
        write_json(output / "boundary_before.json", boundary_before)

        c3b_dir, c3b_verification = verify_c3b_evidence(root)
        write_json(output / "c3b_input_verification.json", c3b_verification)

        packaging_api = PackagingAPI(root)
        package_api_source = packaging_api.source
        items, manifest_summary = load_and_validate_manifest(c3b_dir, packaging_api)
        write_json(output / "manifest_validation.json", manifest_summary)

        free_before = shutil.disk_usage(root).free
        reused, missing = validate_staging_wheelhouse(staging, items)
        missing_bytes = sum(item["size_bytes"] for item in missing)
        reserve = missing_bytes + 512 * 1024 * 1024
        space_report = {
            "free_bytes_before": free_before,
            "exact_total_wheel_bytes": EXPECTED_C3B_COMPRESSED_BYTES,
            "already_staged_exact_bytes": sum(r["size_bytes"] for r in reused),
            "missing_download_bytes": missing_bytes,
            "required_free_reserve_bytes": reserve,
            "sufficient": free_before >= reserve,
        }
        write_json(output / "space_report.json", space_report)
        if not space_report["sufficient"]:
            raise RuntimeError(f"Insufficient free space for fail-closed staging reserve: {space_report}")

        # Revalidate every exact release before requesting any wheel payload.
        print(f"[C3C] Revalidating {len(items)} exact PyPI release records before payload acquisition.", flush=True)
        metadata_result = metadata_revalidate(items, client, packaging_api)
        write_json(output / "metadata_revalidation.json", metadata_result)

        if not staging.exists():
            staging.mkdir(parents=False, exist_ok=False)
        if missing:
            partials.mkdir(parents=False, exist_ok=False)

        reused_names = {r["filename"] for r in reused}
        total_items = len(items)
        for position, item in enumerate(items, start=1):
            final_path = staging / item["filename"]
            mib = item["size_bytes"] / (1024 * 1024)
            if item["filename"] in reused_names:
                print(f"[WHEEL {position:03d}/{total_items:03d}] REVERIFY {item['filename']} ({mib:.2f} MiB)", flush=True)
                structure = validate_wheel_structure(final_path, item, packaging_api)
                structure["acquisition_status"] = "reused_exact_existing"
                structure_results.append(structure)
                acquisition_results.append({
                    "name": item["name"],
                    "version": item["version"],
                    "filename": item["filename"],
                    "status": "reused_exact_existing",
                    "size_bytes": item["size_bytes"],
                    "sha256": item["sha256"],
                })
                continue
            partial_path = partials / f"{item['order']:03d}__{item['filename']}.partial"
            print(f"[WHEEL {position:03d}/{total_items:03d}] DOWNLOAD {item['filename']} ({mib:.2f} MiB)", flush=True)
            network_record = client.download_exact(item, partial_path)
            structure = validate_wheel_structure(partial_path, item, packaging_api)
            structure["acquisition_status"] = "newly_downloaded_exact"
            if final_path.exists():
                raise RuntimeError(f"Destination appeared during acquisition; refusing overwrite: {final_path}")
            partial_path.rename(final_path)
            print(f"[WHEEL {position:03d}/{total_items:03d}] ACCEPTED {item['filename']}", flush=True)
            downloaded_count += 1
            acquisition_results.append({
                "name": item["name"],
                "version": item["version"],
                "filename": item["filename"],
                "status": "newly_downloaded_exact",
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
                "network": network_record,
            })
            structure_results.append(structure)

        inventory = inventory_staging(staging, items)
        boundary_after = boundary_snapshot(root, package_dir, staging)
        boundary_comparison = compare_protected_boundaries(boundary_before, boundary_after)
        if not boundary_comparison["verified"]:
            raise RuntimeError(f"Protected boundary verification failed: {boundary_comparison['checks']}")
        if len(structure_results) != EXPECTED_C3B_PACKAGE_COUNT or not all(r.get("verified") for r in structure_results):
            raise RuntimeError("Not every exact wheel passed structural and RECORD verification")

        state = "acquisition_complete_ready_for_exact_review"
        classification = SUCCESS_CLASSIFICATION
    except Exception as exc:
        blocking_findings.append(f"{type(exc).__name__}: {exc}")
        blocking_findings.append(traceback.format_exc())
        try:
            if not boundary_after and root.exists():
                boundary_after = boundary_snapshot(root, package_dir, staging)
            if boundary_before and boundary_after:
                boundary_comparison = compare_protected_boundaries(boundary_before, boundary_after)
        except Exception as boundary_exc:
            blocking_findings.append(f"Boundary capture failure: {type(boundary_exc).__name__}: {boundary_exc}")
    finally:
        completed_dt = utc_now()
        elapsed = round(time.monotonic() - started_monotonic, 3)
        try:
            write_json(output / "runtime_identity.json", runtime_identity)
            write_json(output / "c3b_input_verification.json", c3b_verification)
            write_json(output / "manifest_validation.json", manifest_summary)
            write_json(output / "metadata_revalidation.json", metadata_result)
            write_json(output / "network_log.json", {
                "allowed_metadata_host": PYPI_JSON_HOST,
                "allowed_wheel_host": PYPI_FILE_HOST,
                "redirects_allowed": False,
                "metadata_bytes": client.metadata_bytes,
                "payload_bytes": client.payload_bytes,
                "requests": client.log,
            })
            write_json(output / "acquisition_results.json", {
                "count": len(acquisition_results),
                "downloaded_count": downloaded_count,
                "reused_count": len(reused),
                "results": acquisition_results,
            })
            write_json(output / "wheel_structure_verification.json", {
                "count": len(structure_results),
                "all_verified": bool(structure_results) and all(r.get("verified") for r in structure_results),
                "results": structure_results,
            })
            write_json(output / "wheelhouse_inventory.json", inventory)
            write_json(output / "boundary_after.json", boundary_after)
            write_json(output / "boundary_comparison.json", boundary_comparison)
            source_policy = {
                "metadata_network_allowed": True,
                "metadata_host": PYPI_JSON_HOST,
                "wheel_payload_network_allowed": True,
                "wheel_host": PYPI_FILE_HOST,
                "exact_manifest_urls_only": True,
                "redirects_rejected": True,
                "source_distributions_allowed": False,
                "alternate_mirrors_allowed": False,
                "package_install_allowed": False,
                "staging_wheelhouse": str(staging),
                "runtime_target": str(root / PREFERRED_TARGET_REL),
                "runtime_wheelhouse": str(root / RUNTIME_WHEELHOUSE_REL),
            }
            write_json(output / "source_policy.json", source_policy)
            write_json(output / "rollback_boundaries.json", {
                "c3c_allowed_write_boundary": str(package_dir),
                "accepted_staging_wheelhouse": str(staging),
                "preferred_target_untouched": str(root / PREFERRED_TARGET_REL),
                "runtime_wheelhouse_untouched": str(root / RUNTIME_WHEELHOUSE_REL),
                "protected_unchanged_boundaries": [
                    str(root / "Runtime/Desktop"), str(root / "Runtime/Core"), str(root / "ComfyUI"),
                    str(root / "System"), str(root / "START_FOXAI_CLEAN.bat"),
                ],
                "failure_behavior": "Preserve already accepted exact wheels and partial failure evidence; never overwrite mismatched files.",
                "rollback_executed": False,
                "future_removal_requires_operator_approval": True,
            })
            file_checks = boundary_comparison.get("file_checks", []) if isinstance(boundary_comparison, dict) else []
            protected_deleted = any(
                check.get("before", {}).get("exists") is True
                and check.get("after", {}).get("exists") is False
                for check in file_checks
            )
            protected_changed = any(
                check.get("before", {}).get("exists") is True
                and check.get("after", {}).get("exists") is True
                and not check.get("unchanged", False)
                for check in file_checks
            )
            target_created = (
                boundary_before.get("preferred_target", {}).get("exists") is False
                and boundary_after.get("preferred_target", {}).get("exists") is True
            ) if boundary_before and boundary_after else False
            runtime_wheelhouse_created = (
                boundary_before.get("runtime_wheelhouse", {}).get("exists") is False
                and boundary_after.get("runtime_wheelhouse", {}).get("exists") is True
            ) if boundary_before and boundary_after else False
            receipt = {
                "action": ACTION,
                "state": state,
                "started": started_dt.isoformat(),
                "completed": completed_dt.isoformat(),
                "elapsed_seconds": elapsed,
                "verified": state == "acquisition_complete_ready_for_exact_review",
                "root": str(root),
                "portable_python": str(root / EXPECTED_RELATIVE_PYTHON),
                "preferred_target": str(root / PREFERRED_TARGET_REL),
                "staging_wheelhouse": str(staging),
                "classification": classification,
                "blocking_findings": blocking_findings,
                "exact_package_count": inventory.get("wheel_count", 0),
                "exact_staged_bytes": inventory.get("total_bytes", 0),
                "newly_downloaded_wheels": downloaded_count,
                "reused_exact_wheels": len(reused),
                "metadata_request_count": sum(1 for r in client.log if r.get("kind") == "metadata"),
                "wheel_request_count": sum(1 for r in client.log if r.get("kind") == "wheel"),
                "metadata_bytes_retrieved": client.metadata_bytes,
                "wheel_payload_bytes_retrieved": client.payload_bytes,
                "c3c_writes_outside_package": False,
                "protected_key_files_unchanged": bool(boundary_comparison.get("checks", {}).get("protected_files_unchanged", False)),
                "protected_files_deleted": protected_deleted,
                "protected_files_changed": protected_changed,
                "target_directory_created": target_created,
                "runtime_wheelhouse_created": runtime_wheelhouse_created,
                "package_install": False,
                "package_uninstall": False,
                "source_archive_download": False,
                "local_build": False,
                "package_copy": False,
                "launcher_change": False,
                "foxai_launched": False,
                "webui_launched": False,
                "desktop_launched": False,
                "comfyui_launched": False,
                "writes_limited_to": str(package_dir),
                "packaging_source": package_api_source,
            }
            write_json(output / "receipt.json", receipt)
            classification_obj = {
                "mode": classification,
                "blocking_findings": blocking_findings,
                "notes": [
                    "C3C accepts only the exact externally reviewed C3B manifest.",
                    "Every accepted wheel must match exact PyPI metadata, URL, size, SHA-256, compatible tags, ZIP structure, and wheel RECORD hashes.",
                    "Accepted payloads are staged only under the C3C package and are not installed.",
                ],
                "next_gate": (
                    "Upload UPLOAD_THIS_C3C_REVIEW.zip for exact review before any isolated target creation, package installation, launcher change, or ComfyUI launch."
                    if state == "acquisition_complete_ready_for_exact_review"
                    else "Upload UPLOAD_THIS_C3C_REVIEW.zip for failure review. Do not install or create the isolated target."
                ),
            }
            write_json(output / "classification.json", classification_obj)
            report_data = {
                "state": state,
                "classification": classification,
                "verified": receipt["verified"],
                "accepted_wheels": inventory.get("wheel_count", 0),
                "accepted_bytes": inventory.get("total_bytes", 0),
                "downloaded_wheels": downloaded_count,
                "reused_wheels": len(reused),
                "metadata_requests": receipt["metadata_request_count"],
                "wheel_requests": receipt["wheel_request_count"],
                "blocking_findings": blocking_findings,
            }
            write_report(output, report_data)
            create_evidence_integrity(output)
            create_review_bundle(output)
        except Exception as evidence_exc:
            print(f"[EVIDENCE ERROR] {type(evidence_exc).__name__}: {evidence_exc}", file=sys.stderr)
            traceback.print_exc()

    print("=" * 72)
    print("FOXAI USB C3C — Exact Wheel Acquisition and Cryptographic Staging")
    print("=" * 72)
    print(f"State:          {state}")
    print(f"Classification: {classification}")
    print(f"Evidence:       {output}")
    print(f"Staging:        {staging}")
    if blocking_findings:
        print(f"Blocking:       {blocking_findings[0]}")
    print("Upload:         UPLOAD_THIS_C3C_REVIEW.zip from the newest output folder")
    return 0 if state == "acquisition_complete_ready_for_exact_review" else 20


if __name__ == "__main__":
    raise SystemExit(main())
