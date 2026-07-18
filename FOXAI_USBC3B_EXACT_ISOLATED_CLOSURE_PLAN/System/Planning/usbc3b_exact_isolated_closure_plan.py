#!/usr/bin/env python3
"""FOXAI USB C3B — Exact Isolated Dependency Closure Plan.

This is a no-install planning tool. It verifies the reviewed C3A evidence,
resolves an exact Windows CPython 3.14 dependency closure using PyPI JSON
metadata only, selects one compatible wheel per package, and writes a plan.

Safety boundary:
- no pip/uv install, download, uninstall, or package copy
- no wheel payload retrieval
- no creation or modification of Runtime/ComfyUI/site-packages
- no launcher/source/runtime edits
- no FOXAI/WebUI/Desktop/ComfyUI launch
- network is restricted to HTTPS JSON metadata from pypi.org
- all writes are new files under this package's PLAN_OUTPUT directory
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import ssl
import sys
import sysconfig
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ACTION = "foxai_usbc3b_exact_isolated_dependency_closure_plan"
EXPECTED_PORTABLE_VERSION = (3, 14, 6)
EXPECTED_RELATIVE_PYTHON = Path("Runtime/Desktop/python/python.exe")
PREFERRED_TARGET_REL = Path("Runtime/ComfyUI/site-packages")
C3A_PACKAGE_DIR = "FOXAI_USBC3A_COMFYUI_DEPENDENCY_PREFLIGHT"
EXPECTED_C3A_CLASSIFICATION = "C3A_READY_FOR_EXACT_CLOSURE_PLAN"
EXPECTED_C3A_HASHES = {
    "receipt.json": "aea93fbd4ef15e374ad44ea9d4024ec8a8eb83160a59aec5ac0269897cd757e6",
    "classification.json": "101ad317b7d571712304a33ff700f021bef08d01a06d0ab59c9e44cc7604ce11",
    "evidence_integrity.json": "2b16c42cd00b13a7ba81a3d2990cfada48b33d96ba910875f5c73d1a94f95743",
    "dependency_manifests.json": "791086fa5215caa9a22f7a7cbaa77f613534f71d6959b40965995956645da2b2",
    "host_runtime_probes.json": "3fdc0a52410445d7c5b0c3346d80797b2229aa4c2797bbfc12988aba565ab0b2",
    "portable_runtime.json": "426a1c0e5f2c4f4363ecf281f149090fe6bb4d1e58429875df386ed9b3092523",
    "target_state.json": "d3f0e1db580b6d177050c9101f4fb8606bb491188daa00ff396e096a95c7c0c9",
}
PYPI_JSON_HOST = "pypi.org"
PYPI_FILE_HOST = "files.pythonhosted.org"
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_RESOLUTION_ROUNDS = 30
USER_AGENT = "FOXAI-USBC3B/1.0 metadata-only dependency planner"
REQ_CONTINUATION_RE = re.compile(r"\\\s*$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


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


def file_record(path: Path, base: Path | None = None, include_hash: bool = True) -> dict[str, Any]:
    try:
        stat = path.stat()
        shown = str(path.relative_to(base)) if base and path.is_relative_to(base) else str(path)
        rec: dict[str, Any] = {
            "path": shown,
            "exists": True,
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
        if include_hash and path.is_file():
            rec["sha256"] = sha256_file(path)
        return rec
    except Exception as exc:
        return {"path": str(path), "exists": path.exists(), "error": f"{type(exc).__name__}: {exc}"}


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except Exception:
        return path.absolute()


def find_root(start: Path) -> Path | None:
    resolved = safe_resolve(start)
    for candidate in [resolved, *resolved.parents]:
        if (candidate / "ComfyUI/main.py").is_file() and (candidate / EXPECTED_RELATIVE_PYTHON).is_file():
            return candidate
    return None


def target_state(target: Path) -> dict[str, Any]:
    state = {
        "path": str(target),
        "exists": target.exists(),
        "is_directory": target.is_dir(),
        "entry_count": None,
    }
    if target.is_dir():
        try:
            state["entry_count"] = len(list(target.iterdir()))
        except Exception as exc:
            state["entry_error"] = f"{type(exc).__name__}: {exc}"
    return state


class PackagingAPI:
    def __init__(self, root: Path):
        desktop_site = root / "Runtime/Desktop/site-packages"
        if not desktop_site.is_dir():
            raise RuntimeError(f"Verified Desktop site-packages is missing: {desktop_site}")
        sys.path.insert(0, str(desktop_site))
        try:
            from packaging.markers import default_environment
            from packaging.requirements import Requirement
            from packaging.specifiers import SpecifierSet
            from packaging.tags import sys_tags
            from packaging.utils import canonicalize_name, parse_wheel_filename
            from packaging.version import InvalidVersion, Version
        except Exception as exc:
            raise RuntimeError(f"Could not load verified read-only packaging library: {type(exc).__name__}: {exc}") from exc
        self.default_environment = default_environment
        self.Requirement = Requirement
        self.SpecifierSet = SpecifierSet
        self.sys_tags = sys_tags
        self.canonicalize_name = canonicalize_name
        self.parse_wheel_filename = parse_wheel_filename
        self.InvalidVersion = InvalidVersion
        self.Version = Version
        self.source = str(desktop_site)

    def env(self) -> dict[str, str]:
        env = self.default_environment()
        env.update({
            "implementation_name": "cpython",
            "implementation_version": "3.14.6",
            "os_name": "nt",
            "platform_machine": "AMD64",
            "platform_python_implementation": "CPython",
            "platform_release": platform.release(),
            "platform_system": "Windows",
            "platform_version": platform.version(),
            "python_full_version": "3.14.6",
            "python_version": "3.14",
            "sys_platform": "win32",
            "extra": "",
        })
        return env


@dataclass(frozen=True)
class ConstraintRecord:
    raw: str
    source: str
    parent: str | None


class MetadataClient:
    def __init__(self, output: Path):
        self.output = output
        self.context = ssl.create_default_context()
        self.exact_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.project_cache: dict[str, dict[str, Any]] = {}
        self.log: list[dict[str, Any]] = []
        self.total_bytes = 0

    def _fetch_json(self, url: str, purpose: str) -> dict[str, Any]:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != PYPI_JSON_HOST:
            raise RuntimeError(f"Metadata source rejected by allowlist: {url}")
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(1, 4):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=45, context=self.context) as response:
                    final = urllib.parse.urlsplit(response.geturl())
                    if final.scheme != "https" or final.hostname != PYPI_JSON_HOST:
                        raise RuntimeError(f"Metadata redirect rejected by allowlist: {response.geturl()}")
                    length_header = response.headers.get("Content-Length")
                    if length_header and int(length_header) > MAX_JSON_BYTES:
                        raise RuntimeError(f"Metadata response exceeds limit: {length_header} bytes")
                    payload = response.read(MAX_JSON_BYTES + 1)
                    if len(payload) > MAX_JSON_BYTES:
                        raise RuntimeError("Metadata response exceeded maximum allowed size")
                    data = json.loads(payload.decode("utf-8"))
                    elapsed = round(time.monotonic() - started, 3)
                    self.total_bytes += len(payload)
                    self.log.append({
                        "url": url,
                        "purpose": purpose,
                        "attempt": attempt,
                        "status": getattr(response, "status", 200),
                        "bytes": len(payload),
                        "elapsed_seconds": elapsed,
                    })
                    return data
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(0.75 * attempt)
        self.log.append({
            "url": url,
            "purpose": purpose,
            "status": "failed",
            "error": f"{type(last_error).__name__}: {last_error}",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        })
        raise RuntimeError(f"PyPI metadata request failed for {url}: {type(last_error).__name__}: {last_error}")

    def exact(self, name: str, version: str) -> dict[str, Any]:
        key = (name, version)
        if key not in self.exact_cache:
            qname = urllib.parse.quote(name, safe="")
            qver = urllib.parse.quote(version, safe="")
            self.exact_cache[key] = self._fetch_json(
                f"https://{PYPI_JSON_HOST}/pypi/{qname}/{qver}/json",
                f"exact release metadata for {name}=={version}",
            )
        return self.exact_cache[key]

    def project(self, name: str) -> dict[str, Any]:
        if name not in self.project_cache:
            qname = urllib.parse.quote(name, safe="")
            self.project_cache[name] = self._fetch_json(
                f"https://{PYPI_JSON_HOST}/pypi/{qname}/json",
                f"release index metadata for {name}",
            )
        return self.project_cache[name]


class Resolver:
    def __init__(
        self,
        pkg: PackagingAPI,
        client: MetadataClient,
        host_distributions: dict[str, dict[str, Any]],
        direct_requirements: list[dict[str, Any]],
    ):
        self.pkg = pkg
        self.client = client
        self.env = pkg.env()
        self.supported_tags = list(pkg.sys_tags())
        self.tag_rank = {tag: i for i, tag in enumerate(self.supported_tags)}
        self.host = {pkg.canonicalize_name(k): v for k, v in host_distributions.items()}
        self.direct_input = direct_requirements
        self.fixed_versions: dict[str, str] = {}
        self.direct_records: list[dict[str, Any]] = []
        self.selection_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.project_candidate_cache: dict[tuple[str, tuple[str, ...]], tuple[str, dict[str, Any], str]] = {}
        self.warnings: list[str] = []

    def marker_applies(self, req: Any, extras: set[str] | None = None) -> bool:
        if req.marker is None:
            return True
        values = extras or {""}
        for extra in values:
            env = dict(self.env)
            env["extra"] = extra
            try:
                if req.marker.evaluate(env):
                    return True
            except Exception as exc:
                raise RuntimeError(f"Could not evaluate marker {req.marker!s}: {type(exc).__name__}: {exc}") from exc
        return False

    def build_direct_pins(self) -> None:
        seen: set[str] = set()
        for item in self.direct_input:
            raw = str(item.get("raw") or "").strip()
            if not raw:
                continue
            req = self.pkg.Requirement(raw)
            if not self.marker_applies(req):
                self.direct_records.append({"raw": raw, "status": "MARKER_NOT_APPLICABLE"})
                continue
            name = self.pkg.canonicalize_name(req.name)
            if name in seen:
                continue
            seen.add(name)
            host = self.host.get(name)
            if not host or not host.get("version"):
                raise RuntimeError(f"Direct dependency {name} has no verified host version in C3A evidence")
            version = str(host["version"])
            if req.specifier and not req.specifier.contains(version, prereleases=True):
                raise RuntimeError(f"Verified host {name}=={version} does not satisfy direct requirement {raw}")
            self.fixed_versions[name] = version
            self.direct_records.append({
                "name": name,
                "raw": raw,
                "source": item.get("source"),
                "line": item.get("line"),
                "host_version": version,
                "exact_pin": f"{name}=={version}",
                "status": "PINNED_TO_VERIFIED_HOST_VERSION",
            })
        if not self.fixed_versions:
            raise RuntimeError("No applicable direct dependencies were available to pin")

    def _requires_python_ok(self, spec: str | None) -> bool:
        if not spec:
            return True
        try:
            return self.pkg.SpecifierSet(spec).contains("3.14.6", prereleases=True)
        except Exception:
            return False

    def _select_wheel_from_files(self, name: str, version: str, files: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
        candidates: list[tuple[int, str, dict[str, Any], str]] = []
        for file in files:
            if file.get("packagetype") != "bdist_wheel":
                continue
            if file.get("yanked"):
                continue
            filename = str(file.get("filename") or "")
            url = str(file.get("url") or "")
            if not filename.lower().endswith(".whl"):
                continue
            parsed_url = urllib.parse.urlsplit(url)
            if parsed_url.scheme != "https" or parsed_url.hostname != PYPI_FILE_HOST:
                continue
            if not self._requires_python_ok(file.get("requires_python")):
                continue
            try:
                parsed_name, parsed_version, _build, tags = self.pkg.parse_wheel_filename(filename)
            except Exception:
                continue
            if self.pkg.canonicalize_name(str(parsed_name)) != name:
                continue
            if str(parsed_version) != version:
                continue
            ranks = [self.tag_rank[tag] for tag in tags if tag in self.tag_rank]
            if not ranks:
                continue
            best_tag = min((tag for tag in tags if tag in self.tag_rank), key=lambda t: self.tag_rank[t])
            candidates.append((min(ranks), filename.lower(), file, str(best_tag)))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]))
        rank, _lower, file, tag = candidates[0]
        digest = ((file.get("digests") or {}).get("sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"Selected wheel lacks a valid SHA-256 digest: {file.get('filename')}")
        return {
            "name": name,
            "version": version,
            "filename": file.get("filename"),
            "url": file.get("url"),
            "size_bytes": int(file.get("size") or 0),
            "sha256": digest,
            "requires_python": file.get("requires_python"),
            "upload_time_iso_8601": file.get("upload_time_iso_8601") or file.get("upload_time"),
            "selected_tag": tag,
            "tag_preference_rank": rank,
            "yanked": bool(file.get("yanked")),
            "source_index": "https://pypi.org/simple",
            "metadata_api": f"https://pypi.org/pypi/{urllib.parse.quote(name, safe='')}/{urllib.parse.quote(version, safe='')}/json",
        }

    def exact_release(self, name: str, version: str) -> dict[str, Any]:
        key = (name, version)
        if key in self.selection_cache:
            return self.selection_cache[key]
        data = self.client.exact(name, version)
        info = data.get("info") or {}
        observed_name = self.pkg.canonicalize_name(str(info.get("name") or name))
        observed_version = str(info.get("version") or version)
        if observed_name != name or observed_version != version:
            raise RuntimeError(
                f"PyPI identity mismatch for {name}=={version}: observed {observed_name}=={observed_version}"
            )
        if not self._requires_python_ok(info.get("requires_python")):
            raise RuntimeError(f"{name}=={version} does not support Python 3.14.6")
        wheel = self._select_wheel_from_files(name, version, data.get("urls") or [])
        result = {
            "name": name,
            "version": version,
            "requires_python": info.get("requires_python"),
            "requires_dist": list(info.get("requires_dist") or []),
            "wheel": wheel,
            "project_url": info.get("project_url") or info.get("package_url"),
        }
        self.selection_cache[key] = result
        return result

    def _satisfies(self, version: str, records: list[ConstraintRecord]) -> bool:
        for record in records:
            req = self.pkg.Requirement(record.raw)
            if req.specifier and not req.specifier.contains(version, prereleases=True):
                return False
        return True

    def select_version(self, name: str, records: list[ConstraintRecord]) -> tuple[str, dict[str, Any], str]:
        normalized_constraints = tuple(sorted(record.raw for record in records))
        cache_key = (name, normalized_constraints)
        if cache_key in self.project_candidate_cache:
            return self.project_candidate_cache[cache_key]

        host = self.host.get(name)
        if host and host.get("version"):
            host_version = str(host["version"])
            if self._satisfies(host_version, records):
                try:
                    exact = self.exact_release(name, host_version)
                    if exact.get("wheel"):
                        result = (host_version, exact, "VERIFIED_HOST_VERSION")
                        self.project_candidate_cache[cache_key] = result
                        return result
                except Exception as exc:
                    self.warnings.append(f"Host preference rejected for {name}=={host_version}: {type(exc).__name__}: {exc}")

        project = self.client.project(name)
        releases = project.get("releases") or {}
        candidates: list[tuple[Any, str, dict[str, Any]]] = []
        prerelease_candidates: list[tuple[Any, str, dict[str, Any]]] = []
        for version, files in releases.items():
            try:
                parsed = self.pkg.Version(version)
            except self.pkg.InvalidVersion:
                continue
            if not self._satisfies(version, records):
                continue
            wheel = self._select_wheel_from_files(name, version, files or [])
            if not wheel:
                continue
            row = (parsed, version, wheel)
            if parsed.is_prerelease or parsed.is_devrelease:
                prerelease_candidates.append(row)
            else:
                candidates.append(row)
        chosen_pool = candidates or prerelease_candidates
        if not chosen_pool:
            rendered = "; ".join(record.raw for record in records)
            raise RuntimeError(f"No compatible cp314 Windows wheel found for {name} satisfying: {rendered}")
        chosen_pool.sort(key=lambda x: x[0], reverse=True)
        _parsed, version, project_wheel = chosen_pool[0]
        exact = self.exact_release(name, version)
        exact_wheel = exact.get("wheel")
        if not exact_wheel:
            raise RuntimeError(f"Selected project release {name}=={version} lost its compatible wheel in exact metadata")
        if project_wheel["sha256"] != exact_wheel["sha256"]:
            raise RuntimeError(f"PyPI project/exact metadata digest mismatch for {name}=={version}")
        result = (version, exact, "LATEST_COMPATIBLE_FALLBACK")
        self.project_candidate_cache[cache_key] = result
        return result

    def resolve(self) -> dict[str, Any]:
        self.build_direct_pins()
        selected = dict(self.fixed_versions)
        requested_extras: dict[str, set[str]] = defaultdict(set)
        selection_reason: dict[str, str] = {name: "DIRECT_PIN_VERIFIED_HOST" for name in selected}
        history: list[dict[str, Any]] = []

        for round_no in range(1, MAX_RESOLUTION_ROUNDS + 1):
            constraints: dict[str, list[ConstraintRecord]] = defaultdict(list)
            next_extras: dict[str, set[str]] = defaultdict(set)
            graph: dict[str, set[str]] = defaultdict(set)

            for item in self.direct_records:
                if item.get("status") != "PINNED_TO_VERIFIED_HOST_VERSION":
                    continue
                req = self.pkg.Requirement(item["raw"])
                name = self.pkg.canonicalize_name(req.name)
                constraints[name].append(ConstraintRecord(item["raw"], f"direct:{item.get('source')}:{item.get('line')}", None))
                next_extras[name].update(req.extras)

            for parent, version in sorted(selected.items()):
                exact = self.exact_release(parent, version)
                if not exact.get("wheel"):
                    raise RuntimeError(f"No compatible wheel exists for selected {parent}=={version}")
                parent_extras = requested_extras.get(parent) or {""}
                for raw in exact.get("requires_dist") or []:
                    req = self.pkg.Requirement(raw)
                    if not self.marker_applies(req, parent_extras):
                        continue
                    child = self.pkg.canonicalize_name(req.name)
                    constraints[child].append(ConstraintRecord(raw, f"metadata:{parent}=={version}", parent))
                    next_extras[child].update(req.extras)
                    graph[parent].add(child)

            new_selected: dict[str, str] = {}
            new_reason: dict[str, str] = {}
            selection_details: dict[str, dict[str, Any]] = {}
            for name in sorted(constraints):
                records = constraints[name]
                if name in self.fixed_versions:
                    version = self.fixed_versions[name]
                    if not self._satisfies(version, records):
                        rendered = "; ".join(record.raw for record in records)
                        raise RuntimeError(f"Fixed direct pin conflict: {name}=={version} does not satisfy {rendered}")
                    exact = self.exact_release(name, version)
                    if not exact.get("wheel"):
                        raise RuntimeError(f"Fixed direct pin has no compatible wheel: {name}=={version}")
                    reason = "DIRECT_PIN_VERIFIED_HOST"
                else:
                    version, exact, reason = self.select_version(name, records)
                new_selected[name] = version
                new_reason[name] = reason
                selection_details[name] = {
                    "version": version,
                    "reason": reason,
                    "constraint_count": len(records),
                    "constraints": [record.__dict__ for record in records],
                    "requested_extras": sorted(next_extras.get(name) or []),
                }

            history.append({
                "round": round_no,
                "selected_count": len(new_selected),
                "changed": new_selected != selected or {k: sorted(v) for k, v in next_extras.items()} != {k: sorted(v) for k, v in requested_extras.items()},
                "selections": selection_details,
            })
            if new_selected == selected and {k: sorted(v) for k, v in next_extras.items()} == {k: sorted(v) for k, v in requested_extras.items()}:
                return {
                    "selected": selected,
                    "selection_reason": selection_reason,
                    "constraints": constraints,
                    "requested_extras": requested_extras,
                    "graph": graph,
                    "history": history,
                }
            selected = new_selected
            selection_reason = new_reason
            requested_extras = next_extras

        raise RuntimeError(f"Dependency resolution did not converge after {MAX_RESOLUTION_ROUNDS} rounds")


def locate_and_verify_c3a(root: Path) -> tuple[Path, dict[str, Any]]:
    output_root = root / C3A_PACKAGE_DIR / "PREFLIGHT_OUTPUT"
    if not output_root.is_dir():
        raise RuntimeError(f"C3A output root is missing: {output_root}")
    candidates = sorted([p for p in output_root.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    diagnostics: list[dict[str, Any]] = []
    for candidate in candidates:
        row: dict[str, Any] = {"path": str(candidate), "matches_expected_hashes": False}
        try:
            missing = [name for name in EXPECTED_C3A_HASHES if not (candidate / name).is_file()]
            if missing:
                row["missing"] = missing
                diagnostics.append(row)
                continue
            observed = {name: sha256_file(candidate / name) for name in EXPECTED_C3A_HASHES}
            row["observed_hashes"] = observed
            if observed != EXPECTED_C3A_HASHES:
                row["hash_mismatches"] = {
                    name: {"expected": EXPECTED_C3A_HASHES[name], "observed": observed[name]}
                    for name in EXPECTED_C3A_HASHES if observed[name] != EXPECTED_C3A_HASHES[name]
                }
                diagnostics.append(row)
                continue
            receipt = read_json(candidate / "receipt.json")
            classification = read_json(candidate / "classification.json")
            if receipt.get("verified") is not True or receipt.get("classification") != EXPECTED_C3A_CLASSIFICATION:
                row["receipt_rejected"] = receipt
                diagnostics.append(row)
                continue
            if classification.get("mode") != EXPECTED_C3A_CLASSIFICATION:
                row["classification_rejected"] = classification
                diagnostics.append(row)
                continue
            integrity = read_json(candidate / "evidence_integrity.json")
            integrity_errors = []
            for item in integrity.get("files") or []:
                path = candidate / str(item.get("name") or "")
                if not path.is_file():
                    integrity_errors.append(f"missing:{path.name}")
                    continue
                if path.stat().st_size != int(item.get("size_bytes") or -1):
                    integrity_errors.append(f"size:{path.name}")
                if sha256_file(path) != item.get("sha256"):
                    integrity_errors.append(f"sha256:{path.name}")
            if integrity_errors:
                row["integrity_errors"] = integrity_errors
                diagnostics.append(row)
                continue
            row["matches_expected_hashes"] = True
            row["receipt"] = receipt
            row["classification"] = classification
            row["evidence_count"] = integrity.get("count")
            return candidate, {"selected": row, "candidates_reviewed": diagnostics + [row]}
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            diagnostics.append(row)
    raise RuntimeError("No C3A evidence folder matched the reviewed integrity hashes and verified classification")


def select_host_inventory(c3a_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    probes = read_json(c3a_dir / "host_runtime_probes.json")
    for probe in probes:
        data = probe.get("data") or {}
        imports = data.get("imports") or {}
        version = tuple((data.get("version_info") or [])[:3])
        if version != EXPECTED_PORTABLE_VERSION:
            continue
        if not (imports.get("torch", {}).get("available") and imports.get("torchvision", {}).get("available") and imports.get("torchaudio", {}).get("available")):
            continue
        distributions = data.get("distributions") or {}
        if not distributions:
            continue
        return probe, distributions
    raise RuntimeError("C3A evidence contains no verified Python 3.14.6 host inventory with the torch family importable")


def verify_closure(pkg: PackagingAPI, resolver: Resolver, result: dict[str, Any]) -> dict[str, Any]:
    selected: dict[str, str] = result["selected"]
    extras: dict[str, set[str]] = result["requested_extras"]
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for parent, version in sorted(selected.items()):
        exact = resolver.exact_release(parent, version)
        for raw in exact.get("requires_dist") or []:
            req = pkg.Requirement(raw)
            if not resolver.marker_applies(req, extras.get(parent) or {""}):
                continue
            child = pkg.canonicalize_name(req.name)
            observed = selected.get(child)
            ok = observed is not None and (not req.specifier or req.specifier.contains(observed, prereleases=True))
            checks.append({
                "parent": f"{parent}=={version}",
                "requirement": raw,
                "child": child,
                "selected_version": observed,
                "satisfied": ok,
            })
            if not ok:
                errors.append(f"{parent}=={version} requires {raw}; selected {child}=={observed}")
    return {
        "verified": not errors,
        "selected_package_count": len(selected),
        "evaluated_dependency_edge_count": len(checks),
        "errors": errors,
        "checks": checks,
    }


def topological_order(graph: dict[str, set[str]], selected: dict[str, str]) -> dict[str, Any]:
    # graph maps package -> dependencies. Reverse it so dependencies are emitted first.
    indegree = {name: 0 for name in selected}
    dependents: dict[str, set[str]] = defaultdict(set)
    for parent, deps in graph.items():
        if parent not in selected:
            continue
        for dep in deps:
            if dep not in selected or dep == parent:
                continue
            dependents[dep].add(parent)
            indegree[parent] += 1
    queue = deque(sorted(name for name, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while queue:
        name = queue.popleft()
        ordered.append(name)
        for child in sorted(dependents.get(name) or []):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    cycles = sorted(name for name, degree in indegree.items() if degree > 0)
    if cycles:
        ordered.extend(name for name in sorted(selected) if name not in ordered)
    return {
        "order": [{"position": i + 1, "name": name, "version": selected[name]} for i, name in enumerate(ordered)],
        "cycle_or_mutual_dependency_nodes": cycles,
        "note": "Order is advisory. A future installer should use a locked resolver with hashes rather than manually installing one wheel at a time.",
    }


def write_lock_files(output: Path, resolver: Resolver, result: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    selected = result["selected"]
    reasons = result["selection_reason"]
    rows: list[dict[str, Any]] = []
    total_size = 0
    for name in sorted(selected):
        version = selected[name]
        exact = resolver.exact_release(name, version)
        wheel = dict(exact["wheel"])
        wheel["selection_reason"] = reasons.get(name)
        wheel["direct"] = name in resolver.fixed_versions
        rows.append(wheel)
        total_size += int(wheel.get("size_bytes") or 0)

    lock_lines = [
        "# FOXAI USB C3B exact Windows CPython 3.14 wheel lock",
        "# PLAN ONLY — not authorization to install or download",
        "# One approved wheel hash is listed per exact package version.",
        "--only-binary=:all:",
        "--index-url https://pypi.org/simple",
        "",
    ]
    for row in rows:
        lock_lines.append(f"# {row['filename']} | {row['size_bytes']} bytes | {row['url']}")
        lock_lines.append(f"{row['name']}=={row['version']} --hash=sha256:{row['sha256']}")
    (output / "requirements-exact-windows-cp314.txt").write_text("\n".join(lock_lines) + "\n", encoding="utf-8", newline="\n")

    with (output / "wheel-download-manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order", "name", "version", "direct", "selection_reason", "filename", "selected_tag",
            "size_bytes", "sha256", "url", "source_index", "requires_python", "upload_time_iso_8601",
        ])
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            writer.writerow({"order": i, **{k: row.get(k) for k in writer.fieldnames if k != "order"}})
    write_json(output / "exact_wheel_plan.json", {"package_count": len(rows), "compressed_wheel_bytes": total_size, "wheels": rows})
    return rows, total_size


def produce_report(output: Path, summary: dict[str, Any]) -> None:
    c = summary["classification"]
    f = summary["footprint"]
    lines = [
        "# FOXAI USB C3B",
        "## Exact Isolated Dependency Closure Plan",
        "",
        f"- State: **{summary['state']}**",
        f"- Verified: **{summary['verified']}**",
        f"- Root: `{summary['root']}`",
        f"- Portable Python: `{summary['portable_python']}`",
        f"- Preferred isolated target: `{summary['preferred_target']}`",
        f"- Target existed before/after: **{summary['target_before']['exists']} / {summary['target_after']['exists']}**",
        f"- Classification: **{c['mode']}**",
        f"- Exact package count: **{summary['package_count']}**",
        f"- Exact compressed wheel bytes: **{f['exact_compressed_wheel_bytes']}**",
        f"- Metadata requests: **{summary['metadata_request_count']}**",
        f"- Metadata bytes retrieved: **{summary['metadata_bytes']}**",
        "- Wheel payloads retrieved: **False**",
        "- Live runtime/ComfyUI files modified: **False**",
        "- Install/download/copy/launcher change/launch: **False**",
        "",
        "## Blocking findings",
        "",
    ]
    if c["blocking_findings"]:
        lines.extend(f"- {x}" for x in c["blocking_findings"])
    else:
        lines.append("- None detected by this planning run.")
    lines += ["", "## Important findings", ""]
    lines.extend(f"- {x}" for x in c["notes"])
    lines += ["", "## Next gate", "", f"- {c['next_gate']}", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main_plan(args: argparse.Namespace) -> int:
    started = time.monotonic()
    script = Path(__file__).resolve()
    package_dir = script.parents[2]
    output_root = package_dir / "PLAN_OUTPUT"
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / utc_now().strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(exist_ok=False)

    receipt: dict[str, Any] = {
        "action": ACTION,
        "state": "started_fail_closed",
        "started": iso_now(),
        "completed": None,
        "verified": False,
        "root": None,
        "portable_python": None,
        "preferred_target": None,
        "classification": "FAIL_CLOSED_IN_PROGRESS",
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "target_directory_created": False,
        "package_install": False,
        "package_uninstall": False,
        "wheel_payload_download": False,
        "package_copy": False,
        "launcher_change": False,
        "metadata_network_access": True,
        "metadata_hosts_allowed": [PYPI_JSON_HOST],
        "wheel_file_hosts_recorded_but_not_fetched": [PYPI_FILE_HOST],
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "writes_limited_to": str(output),
    }
    write_json(output / "receipt.json", receipt)

    root = Path(args.root) if args.root else find_root(package_dir)
    if root is None:
        raise RuntimeError("The verified FOXAI root could not be found from package placement or --root")
    root = safe_resolve(root)
    portable_python = root / EXPECTED_RELATIVE_PYTHON
    target = root / PREFERRED_TARGET_REL
    before = target_state(target)
    critical_before = {
        "comfy_main": file_record(root / "ComfyUI/main.py", root),
        "portable_python": file_record(portable_python, root),
        "target": before,
    }
    write_json(output / "boundary_before.json", critical_before)

    if before["exists"] and (not before["is_directory"] or before.get("entry_count")):
        raise RuntimeError("Preferred isolated target exists and is not an empty directory; planning stopped fail-closed")
    if not portable_python.is_file():
        raise RuntimeError(f"Verified portable Python is missing: {portable_python}")
    if sys.executable.lower() != str(portable_python).lower():
        raise RuntimeError(f"C3B must run under the verified portable Python. Expected {portable_python}, observed {sys.executable}")
    if tuple(sys.version_info[:3]) != EXPECTED_PORTABLE_VERSION:
        raise RuntimeError(f"Portable Python drift: expected 3.14.6, observed {sys.version.split()[0]}")
    if platform.machine().upper() not in {"AMD64", "X86_64"} or sysconfig.get_platform().lower() != "win-amd64":
        raise RuntimeError(f"Binary target drift: expected win-amd64, observed machine={platform.machine()} platform={sysconfig.get_platform()}")

    pkg = PackagingAPI(root)
    c3a_dir, c3a_verification = locate_and_verify_c3a(root)
    write_json(output / "c3a_input_verification.json", c3a_verification)
    host_probe, host_distributions = select_host_inventory(c3a_dir)
    write_json(output / "selected_host_inventory_summary.json", {
        "source_path": host_probe.get("path"),
        "executable": (host_probe.get("data") or {}).get("executable"),
        "python_version": (host_probe.get("data") or {}).get("version"),
        "distribution_count": len(host_distributions),
        "torch_family": {
            name: (host_distributions.get(name) or {}).get("version")
            for name in ("torch", "torchvision", "torchaudio")
        },
    })
    manifests = read_json(c3a_dir / "dependency_manifests.json")

    client = MetadataClient(output)
    resolver = Resolver(pkg, client, host_distributions, manifests.get("requirements") or [])
    result = resolver.resolve()

    direct_pins_text = [
        "# C3B direct pins: verified C3A host versions only",
        "# Input to dependency closure planning; not an install command.",
    ]
    for item in sorted((x for x in resolver.direct_records if x.get("exact_pin")), key=lambda x: x["name"]):
        direct_pins_text.append(f"{item['exact_pin']}  # from {item.get('raw')}")
    (output / "direct_pins.in").write_text("\n".join(direct_pins_text) + "\n", encoding="utf-8", newline="\n")
    write_json(output / "direct_requirements_exact.json", {
        "count": len(resolver.fixed_versions),
        "requirements": resolver.direct_records,
    })

    closure = verify_closure(pkg, resolver, result)
    write_json(output / "closure_verification.json", closure)
    if not closure["verified"]:
        raise RuntimeError("Independent closure verification found unsatisfied dependency edges")

    rows, compressed_bytes = write_lock_files(output, resolver, result)
    order = topological_order(result["graph"], result["selected"])
    write_json(output / "install_order.json", order)
    write_json(output / "dependency_graph.json", {
        "nodes": [{
            "name": name,
            "version": result["selected"][name],
            "direct": name in resolver.fixed_versions,
            "selection_reason": result["selection_reason"].get(name),
            "requested_extras": sorted(result["requested_extras"].get(name) or []),
        } for name in sorted(result["selected"])],
        "edges": [
            {"from": parent, "to": dep}
            for parent in sorted(result["graph"])
            for dep in sorted(result["graph"][parent])
            if parent in result["selected"] and dep in result["selected"]
        ],
    })
    write_json(output / "resolution_history.json", {
        "rounds": len(result["history"]),
        "history": result["history"],
        "warnings": resolver.warnings,
    })

    # Exact compressed size comes from signed PyPI metadata. Installed size remains an estimate until staged wheels are inspected.
    conservative_reservation = max(compressed_bytes * 4, compressed_bytes + 2 * 1024**3)
    footprint = {
        "exact_compressed_wheel_bytes": compressed_bytes,
        "exact_compressed_wheel_gib": round(compressed_bytes / 1024**3, 4),
        "conservative_future_staging_and_install_reservation_bytes": conservative_reservation,
        "conservative_future_staging_and_install_reservation_gib": round(conservative_reservation / 1024**3, 4),
        "known_host_torch_unpacked_bytes_from_C3": 522277671,
        "limitations": [
            "Installed footprint is not exact until approved wheels are staged and inspected.",
            "The reservation is deliberately conservative and is not an authorization to allocate or create directories.",
        ],
    }
    write_json(output / "footprint_estimate.json", footprint)
    write_json(output / "source_policy.json", {
        "metadata_network_allowed": True,
        "allowed_metadata_scheme": "https",
        "allowed_metadata_hosts": [PYPI_JSON_HOST],
        "approved_wheel_file_host": PYPI_FILE_HOST,
        "wheel_payloads_fetched": False,
        "selected_wheels": len(rows),
        "requirements": [
            "A future acquisition step must fetch only the exact URLs and SHA-256 hashes in wheel-download-manifest.csv.",
            "No source distributions or local builds are approved by this plan.",
            "No alternate mirrors are approved without a new exact review.",
        ],
    })
    write_json(output / "rollback_boundaries.json", {
        "current_target": str(target),
        "target_exists_now": before["exists"],
        "c3b_actions": "planning evidence only",
        "future_allowed_write_boundary_requires_new_operator_approval": [
            str(target),
            str(root / "Runtime/ComfyUI/wheelhouse"),
        ],
        "protected_unchanged_boundaries": [
            str(root / "Runtime/Desktop"),
            str(root / "Runtime/Core"),
            str(root / "ComfyUI"),
            str(root / "System"),
            str(root / "START_FOXAI_CLEAN.bat"),
        ],
        "future_rollback_concept_only": [
            "Stop ComfyUI if a later approved test launched it.",
            "Preserve the later install receipt and failure evidence.",
            "Remove only the newly created isolated target and staging wheelhouse after explicit operator approval.",
            "Never delete or modify Desktop/Core runtimes or ComfyUI source as rollback.",
        ],
        "rollback_executed_by_c3b": False,
    })

    write_json(output / "network_metadata_log.json", {
        "request_count": len(client.log),
        "bytes_retrieved": client.total_bytes,
        "allowed_host": PYPI_JSON_HOST,
        "wheel_payload_requests": 0,
        "requests": client.log,
    })

    after = target_state(target)
    critical_after = {
        "comfy_main": file_record(root / "ComfyUI/main.py", root),
        "portable_python": file_record(portable_python, root),
        "target": after,
    }
    boundary_ok = (
        critical_before["comfy_main"].get("sha256") == critical_after["comfy_main"].get("sha256")
        and critical_before["portable_python"].get("sha256") == critical_after["portable_python"].get("sha256")
        and before == after
    )
    write_json(output / "boundary_after.json", {"verified_unchanged": boundary_ok, "before": critical_before, "after": critical_after})
    if not boundary_ok:
        raise RuntimeError("Protected boundary verification changed during C3B; stop and inspect")

    notes = [
        f"Pinned {len(resolver.fixed_versions)} direct ComfyUI dependencies to the exact C3A-verified host versions.",
        f"Resolved and independently verified {len(result['selected'])} exact packages and {closure['evaluated_dependency_edge_count']} active dependency edges.",
        "Every selected artifact is a compatible Windows CPython 3.14 wheel from files.pythonhosted.org with an exact SHA-256 and size.",
        "Only PyPI JSON metadata was retrieved; no wheel payload was fetched and the isolated target was not created.",
    ]
    fallback = [name for name, reason in result["selection_reason"].items() if reason == "LATEST_COMPATIBLE_FALLBACK"]
    if fallback:
        notes.append("Transitive packages that could not reuse the host version were resolved to the latest compatible wheel: " + ", ".join(sorted(fallback)) + ".")
    if order["cycle_or_mutual_dependency_nodes"]:
        notes.append("The advisory install order contains dependency cycles/mutual edges; a locked resolver must perform the future installation.")

    classification = {
        "mode": "C3B_READY_FOR_EXACT_WHEEL_ACQUISITION_REVIEW",
        "blocking_findings": [],
        "notes": notes,
        "next_gate": "Upload the newest C3B PLAN_OUTPUT folder for exact review before any wheel acquisition, target creation, install, launcher change, or ComfyUI launch.",
    }
    write_json(output / "classification.json", classification)

    summary = {
        "state": "plan_complete_ready_for_exact_review",
        "verified": True,
        "root": str(root),
        "portable_python": str(portable_python),
        "preferred_target": str(target),
        "target_before": before,
        "target_after": after,
        "classification": classification,
        "package_count": len(result["selected"]),
        "metadata_request_count": len(client.log),
        "metadata_bytes": client.total_bytes,
        "footprint": footprint,
    }
    produce_report(output, summary)

    receipt.update({
        "state": summary["state"],
        "completed": iso_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "verified": True,
        "root": str(root),
        "portable_python": str(portable_python),
        "preferred_target": str(target),
        "classification": classification["mode"],
        "metadata_request_count": len(client.log),
        "metadata_bytes_retrieved": client.total_bytes,
        "exact_package_count": len(result["selected"]),
    })
    write_json(output / "receipt.json", receipt)

    evidence_files = []
    for path in sorted(output.iterdir(), key=lambda p: p.name.lower()):
        if path.is_file() and path.name != "evidence_integrity.json":
            evidence_files.append({"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(output / "evidence_integrity.json", {"count": len(evidence_files), "files": evidence_files})
    print(json.dumps({"output": str(output), "classification": classification["mode"], "verified": True}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Verified FOXAI root. Normally auto-detected from package placement.")
    args = parser.parse_args()
    try:
        return main_plan(args)
    except Exception as exc:
        # Always create a fail-closed evidence folder if possible.
        try:
            script = Path(__file__).resolve()
            package_dir = script.parents[2]
            output_root = package_dir / "PLAN_OUTPUT"
            output_root.mkdir(parents=True, exist_ok=True)
            candidates = sorted([p for p in output_root.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
            output = candidates[0] if candidates else output_root / utc_now().strftime("%Y%m%dT%H%M%SZ")
            output.mkdir(exist_ok=True)
            failure = {
                "mode": "C3B_FAIL_CLOSED_REVIEW_REQUIRED",
                "blocking_findings": [f"{type(exc).__name__}: {exc}"],
                "notes": ["No install, wheel payload download, package copy, target creation, launcher change, or launch was authorized."],
                "next_gate": "Upload the newest C3B PLAN_OUTPUT folder for failure review. Do not proceed to acquisition or installation.",
            }
            write_json(output / "classification.json", failure)
            receipt_path = output / "receipt.json"
            receipt = read_json(receipt_path) if receipt_path.is_file() else {"action": ACTION}
            receipt.update({
                "state": "failed_closed",
                "completed": iso_now(),
                "verified": False,
                "classification": failure["mode"],
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "live_files_modified": False,
                "target_directory_created": False,
                "package_install": False,
                "wheel_payload_download": False,
                "package_copy": False,
                "launcher_change": False,
                "foxai_launched": False,
                "webui_launched": False,
                "desktop_launched": False,
                "comfyui_launched": False,
            })
            write_json(receipt_path, receipt)
            evidence_files = []
            for path in sorted(output.iterdir(), key=lambda p: p.name.lower()):
                if path.is_file() and path.name != "evidence_integrity.json":
                    evidence_files.append({"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
            write_json(output / "evidence_integrity.json", {"count": len(evidence_files), "files": evidence_files})
        except Exception:
            pass
        print(f"[FAIL CLOSED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
