#!/usr/bin/env python3
"""FOXAI USB C3A — ComfyUI Dependency Closure and Binary Compatibility Preflight.

Read-only with respect to the verified FOXAI/ComfyUI/runtime trees. The only writes
are new evidence files under this package's PREFLIGHT_OUTPUT directory.

No pip install/download, no package copy, no target creation, no launcher edits,
and no FOXAI/ComfyUI launch are performed.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata as md
import importlib.util
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile
import time
import traceback
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path
from typing import Any, Iterable, Iterator

ACTION = "foxai_usbc3a_comfyui_dependency_closure_binary_compatibility_preflight"
EXPECTED_PORTABLE_VERSION = (3, 14, 6)
EXPECTED_RELATIVE_PYTHON = Path("Runtime/Desktop/python/python.exe")
PREFERRED_TARGET_REL = Path("Runtime/ComfyUI/site-packages")
COMFY_REL = Path("ComfyUI")
SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    "models", "output", "input", "temp", "user", "node_modules",
}
MANIFEST_NAMES = {
    "requirements.txt", "requirements-dev.txt", "requirements_dev.txt",
    "manager_requirements.txt", "pyproject.toml", "setup.cfg", "setup.py",
}
BINARY_SUFFIXES = {".pyd", ".dll", ".exe"}
WHEEL_NAME_RE = re.compile(
    r"^(?P<name>.+?)-(?P<version>[^-]+)(?:-(?P<build>[^-]+))?-(?P<py>[^-]+)-(?P<abi>[^-]+)-(?P<plat>[^-]+)\.whl$",
    re.IGNORECASE,
)
REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
URL_SECRET_RE = re.compile(r"(?P<scheme>https?://)(?P<userinfo>[^/@\s]+@)", re.IGNORECASE)

# Optional precision parser. The preflight remains operational without it.
try:
    from packaging.markers import default_environment as packaging_default_environment
    from packaging.requirements import Requirement as PackagingRequirement
    from packaging.tags import sys_tags as packaging_sys_tags
    from packaging.utils import canonicalize_name as packaging_canonicalize_name
    from packaging.version import Version as PackagingVersion
    PACKAGING_AVAILABLE = True
    PACKAGING_SOURCE = "packaging"
except Exception:
    try:
        from pip._vendor.packaging.markers import default_environment as packaging_default_environment
        from pip._vendor.packaging.requirements import Requirement as PackagingRequirement
        from pip._vendor.packaging.tags import sys_tags as packaging_sys_tags
        from pip._vendor.packaging.utils import canonicalize_name as packaging_canonicalize_name
        from pip._vendor.packaging.version import Version as PackagingVersion
        PACKAGING_AVAILABLE = True
        PACKAGING_SOURCE = "pip._vendor.packaging"
    except Exception:
        PACKAGING_AVAILABLE = False
        PACKAGING_SOURCE = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def canonical_name(name: str) -> str:
    if PACKAGING_AVAILABLE:
        return packaging_canonicalize_name(name)
    return re.sub(r"[-_.]+", "-", name).lower().strip()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


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


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def redact_requirement_line(line: str) -> str:
    line = URL_SECRET_RE.sub(lambda m: m.group("scheme") + "<redacted>@", line)
    # Redact obvious embedded query credentials while preserving package/URL identity.
    try:
        if "http://" in line or "https://" in line:
            parts = line.split()
            out = []
            for part in parts:
                if part.startswith(("http://", "https://")):
                    u = urllib.parse.urlsplit(part)
                    q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
                    safe_q = [(k, "<redacted>" if any(t in k.lower() for t in ("token", "key", "secret", "password")) else v) for k, v in q]
                    part = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(safe_q), u.fragment))
                out.append(part)
            line = " ".join(out)
    except Exception:
        pass
    return line


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except Exception:
        return path.absolute()


def find_root(start: Path) -> Path | None:
    candidates = [safe_resolve(start), *safe_resolve(start).parents]
    for candidate in candidates:
        if (candidate / COMFY_REL / "main.py").is_file() and (candidate / "Runtime/Desktop/python").is_dir():
            return candidate
    return None


def root_identity(root: Path) -> dict[str, Any]:
    markers = {
        "comfy_main": root / "ComfyUI/main.py",
        "portable_python": root / EXPECTED_RELATIVE_PYTHON,
        "desktop_site_packages": root / "Runtime/Desktop/site-packages",
        "core_site_packages": root / "Runtime/Core/site-packages",
    }
    return {
        "root": str(root),
        "verified": markers["comfy_main"].is_file() and markers["portable_python"].is_file(),
        "markers": {k: file_record(v, root, include_hash=v.is_file()) for k, v in markers.items()},
    }


def subprocess_env(allow_user_site: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
    })
    env.pop("PYTHONHOME", None)
    if allow_user_site:
        env.pop("PYTHONNOUSERSITE", None)
    return env


def run_json_probe(
    python_exe: Path,
    script: Path,
    args: list[str],
    timeout: int = 90,
    allow_user_site: bool = False,
) -> dict[str, Any]:
    cmd = [str(python_exe), "-B", str(script), *args]
    started = time.monotonic()
    try:
        cp = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=subprocess_env(allow_user_site=allow_user_site),
            errors="replace",
        )
        result: dict[str, Any] = {
            "command": [str(python_exe), "-B", str(script), *args[:1], "<arguments-redacted>" if len(args) > 1 else ""],
            "returncode": cp.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-20000:],
        }
        if cp.returncode == 0:
            try:
                result["data"] = json.loads(cp.stdout)
            except Exception as exc:
                result["parse_error"] = f"{type(exc).__name__}: {exc}"
        return result
    except Exception as exc:
        return {
            "command": [str(python_exe), "-B", str(script), args[0] if args else ""],
            "returncode": None,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def probe_current_runtime(extra_paths: list[str], import_modules: list[str], do_tensor_smoke: bool) -> dict[str, Any]:
    for p in reversed(extra_paths):
        if p and Path(p).exists():
            sys.path.insert(0, p)

    result: dict[str, Any] = {
        "executable": sys.executable,
        "version": sys.version,
        "version_info": list(sys.version_info[:5]),
        "implementation": platform.python_implementation(),
        "architecture": platform.architecture(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "abiflags": getattr(sys, "abiflags", ""),
        "soabi": sysconfig.get_config_var("SOABI"),
        "ext_suffix": sysconfig.get_config_var("EXT_SUFFIX"),
        "platform_tag": sysconfig.get_platform(),
        "enable_user_site": None,
        "sys_path": sys.path,
        "extra_paths": extra_paths,
        "packaging_available": PACKAGING_AVAILABLE,
        "packaging_source": PACKAGING_SOURCE,
        "supported_tags": [],
        "site_packages": [],
        "distributions": {},
        "imports": {},
    }
    try:
        import site
        result["enable_user_site"] = bool(site.ENABLE_USER_SITE)
        for candidate in [site.getusersitepackages(), *(site.getsitepackages() if hasattr(site, "getsitepackages") else [])]:
            if isinstance(candidate, str) and candidate not in result["site_packages"]:
                result["site_packages"].append(candidate)
    except Exception as exc:
        result["site_error"] = f"{type(exc).__name__}: {exc}"

    if PACKAGING_AVAILABLE:
        try:
            result["supported_tags"] = [str(t) for _, t in zip(range(500), packaging_sys_tags())]
        except Exception as exc:
            result["supported_tags_error"] = f"{type(exc).__name__}: {exc}"
    else:
        major, minor = sys.version_info[:2]
        plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
        result["supported_tags"] = [
            f"cp{major}{minor}-cp{major}{minor}-{plat}",
            f"cp{major}{minor}-abi3-{plat}",
            f"cp{major}{minor}-none-{plat}",
            f"py{major}-none-any",
            "py3-none-any",
        ]

    # Static metadata inventory; no pip invocation.
    try:
        for dist in md.distributions(path=[p for p in sys.path if p]):
            name = dist.metadata.get("Name") or ""
            if not name:
                continue
            key = canonical_name(name)
            if key in result["distributions"]:
                continue
            root = str(getattr(dist, "_path", ""))
            result["distributions"][key] = {
                "name": name,
                "version": dist.version,
                "metadata_path": root,
                "requires": dist.requires or [],
            }
    except Exception as exc:
        result["distribution_error"] = f"{type(exc).__name__}: {exc}"

    for module_name in import_modules:
        item: dict[str, Any] = {"requested": module_name}
        try:
            spec = importlib.util.find_spec(module_name)
            item["find_spec"] = {
                "found": spec is not None,
                "origin": getattr(spec, "origin", None) if spec else None,
                "search_locations": list(spec.submodule_search_locations or []) if spec else [],
            }
            module = __import__(module_name)
            item.update({
                "available": True,
                "version": getattr(module, "__version__", None),
                "file": getattr(module, "__file__", None),
            })
            if module_name == "torch":
                item["cuda_available"] = bool(module.cuda.is_available())
                item["cuda_version"] = getattr(getattr(module, "version", None), "cuda", None)
                item["mkldnn_available"] = bool(getattr(getattr(module, "backends", None), "mkldnn", None) and module.backends.mkldnn.is_available())
                if do_tensor_smoke:
                    tensor = module.tensor([1.0, 2.0], dtype=module.float32)
                    item["tensor_smoke"] = (tensor + 1).tolist() == [2.0, 3.0]
            elif module_name == "torchvision":
                try:
                    from torchvision import extension as tv_extension
                    item["compiled_ops_available"] = bool(tv_extension._has_ops())
                except Exception as exc:
                    item["compiled_ops_error"] = f"{type(exc).__name__}: {exc}"
            elif module_name == "torchaudio":
                # Import is the binary loader check. Record extension origins if available.
                try:
                    ext_spec = importlib.util.find_spec("torchaudio.lib._torchaudio")
                    item["extension_origin"] = getattr(ext_spec, "origin", None) if ext_spec else None
                except Exception as exc:
                    item["extension_probe_error"] = f"{type(exc).__name__}: {exc}"
        except BaseException as exc:  # includes DLL loader errors and SystemExit
            item.update({
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=12),
            })
        result["imports"][module_name] = item
    return result


def parse_req_name(raw: str) -> str | None:
    cleaned = raw.strip()
    if not cleaned or cleaned.startswith(("#", "-", "--")):
        return None
    if " @ " in cleaned:
        return canonical_name(cleaned.split(" @ ", 1)[0].strip())
    match = REQ_NAME_RE.match(cleaned)
    return canonical_name(match.group(1)) if match else None


def requirement_record(raw: str, source: str, line: int | None = None) -> dict[str, Any]:
    redacted = redact_requirement_line(raw.strip())
    rec: dict[str, Any] = {"raw": redacted, "source": source}
    if line is not None:
        rec["line"] = line
    rec["name"] = parse_req_name(redacted)
    if PACKAGING_AVAILABLE and rec["name"]:
        try:
            req = PackagingRequirement(redacted)
            rec.update({
                "name": canonical_name(req.name),
                "specifier": str(req.specifier),
                "marker": str(req.marker) if req.marker else None,
                "url": redact_requirement_line(req.url) if req.url else None,
                "extras": sorted(req.extras),
                "parser": "packaging",
            })
            if req.marker:
                try:
                    rec["marker_applies"] = bool(req.marker.evaluate(packaging_default_environment()))
                except Exception as exc:
                    rec["marker_error"] = f"{type(exc).__name__}: {exc}"
            else:
                rec["marker_applies"] = True
        except Exception as exc:
            rec["parse_error"] = f"{type(exc).__name__}: {exc}"
    else:
        rec["parser"] = "fallback"
    return rec


def read_text_limited(path: Path, limit: int = 2_000_000) -> str:
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError(f"file exceeds {limit} byte preflight limit")
    return data.decode("utf-8-sig", errors="replace")


def parse_requirements_file(path: Path, root: Path, seen: set[Path] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen = seen or set()
    resolved = safe_resolve(path)
    if resolved in seen:
        return [], [{"path": str(path), "error": "recursive include skipped"}]
    seen.add(resolved)
    requirements: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    try:
        text = read_text_limited(path)
        evidence.append({**file_record(path, root), "kind": "requirements"})
    except Exception as exc:
        return [], [{"path": str(path), "error": f"{type(exc).__name__}: {exc}"}]

    logical_lines: list[tuple[int, str]] = []
    pending = ""
    pending_line = 0
    for n, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not pending:
            pending_line = n
        if stripped.endswith("\\"):
            pending += stripped[:-1].rstrip() + " "
            continue
        logical_lines.append((pending_line, pending + stripped))
        pending = ""
    if pending:
        logical_lines.append((pending_line, pending))

    for n, line in logical_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        include_match = re.match(r"^(?:-r|--requirement)\s+(.+)$", stripped)
        constraint_match = re.match(r"^(?:-c|--constraint)\s+(.+)$", stripped)
        if include_match or constraint_match:
            rel = (include_match or constraint_match).group(1).strip().strip('"\'')
            child = safe_resolve(path.parent / rel)
            # Fail closed: never follow requirement includes outside the FOXAI root.
            if not child.is_relative_to(safe_resolve(root)):
                evidence.append({"path": str(child), "error": "include outside FOXAI root blocked"})
                continue
            child_reqs, child_ev = parse_requirements_file(child, root, seen)
            requirements.extend(child_reqs)
            evidence.extend(child_ev)
            continue
        if stripped.startswith(("--index-url", "--extra-index-url", "--find-links", "--trusted-host")):
            evidence.append({"path": str(path.relative_to(root)), "line": n, "option": redact_requirement_line(stripped)})
            continue
        requirements.append(requirement_record(stripped, str(path.relative_to(root)), n))
    return requirements, evidence


def parse_pyproject(path: Path, root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rec = {**file_record(path, root), "kind": "pyproject"}
    requirements: list[dict[str, Any]] = []
    try:
        import tomllib
        data = tomllib.loads(read_text_limited(path))
        project = data.get("project") or {}
        for raw in project.get("dependencies") or []:
            requirements.append(requirement_record(str(raw), str(path.relative_to(root))))
        for group, values in (project.get("optional-dependencies") or {}).items():
            for raw in values or []:
                item = requirement_record(str(raw), str(path.relative_to(root)))
                item["optional_group"] = str(group)
                requirements.append(item)
        poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
        for name, spec in poetry.items():
            if canonical_name(name) == "python":
                continue
            raw = name if spec == "*" else f"{name}{spec}" if isinstance(spec, str) else name
            item = requirement_record(raw, str(path.relative_to(root)))
            item["source_table"] = "tool.poetry.dependencies"
            requirements.append(item)
    except Exception as exc:
        rec["parse_error"] = f"{type(exc).__name__}: {exc}"
    return requirements, rec


def walk_files(base: Path, suffixes: set[str] | None = None, max_files: int = 20000) -> Iterator[Path]:
    count = 0
    if not base.exists():
        return
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIR_NAMES]
        for name in filenames:
            p = Path(dirpath) / name
            if suffixes is None or p.suffix.lower() in suffixes:
                yield p
                count += 1
                if count >= max_files:
                    return


def collect_manifests(root: Path, comfy_root: Path) -> dict[str, Any]:
    manifests: list[Path] = []
    core_candidates = [
        comfy_root / "requirements.txt",
        comfy_root / "manager_requirements.txt",
        comfy_root / "pyproject.toml",
    ]
    manifests.extend([p for p in core_candidates if p.is_file()])

    custom_root = comfy_root / "custom_nodes"
    if custom_root.is_dir():
        for dirpath, dirnames, filenames in os.walk(custom_root, followlinks=False):
            rel_depth = len(Path(dirpath).relative_to(custom_root).parts)
            if rel_depth >= 4:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIR_NAMES]
            for name in filenames:
                lower = name.lower()
                is_requirements = lower.endswith(".txt") and (
                    lower.startswith("requirements") or lower.endswith("requirements.txt")
                )
                if lower in MANIFEST_NAMES or is_requirements:
                    manifests.append(Path(dirpath) / name)

    requirements: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for path in sorted(set(manifests), key=lambda p: str(p).lower()):
        if path.name.lower().endswith("requirements.txt") or path.name.lower().startswith("requirements"):
            reqs, ev = parse_requirements_file(path, root)
            requirements.extend(reqs)
            evidence.extend(ev)
        elif path.name.lower() == "pyproject.toml":
            reqs, ev = parse_pyproject(path, root)
            requirements.extend(reqs)
            evidence.append(ev)
        else:
            evidence.append({**file_record(path, root), "kind": "manifest_not_parsed"})

    dedup: dict[tuple[str | None, str, str], dict[str, Any]] = {}
    for req in requirements:
        key = (req.get("name"), req.get("raw", ""), req.get("source", ""))
        dedup[key] = req
    requirements = list(dedup.values())
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for req in requirements:
        if req.get("name"):
            by_name[req["name"]].append(req)
    return {
        "manifest_count": len(evidence),
        "manifests": evidence,
        "requirements": requirements,
        "requirements_by_name": dict(sorted(by_name.items())),
        "unique_named_requirement_count": len(by_name),
        "parser_precision": PACKAGING_SOURCE or "fallback",
    }


def static_import_inventory(comfy_root: Path, root: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    syntax_errors: list[dict[str, Any]] = []
    scanned = 0
    for path in walk_files(comfy_root, {".py"}, max_files=12000):
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = read_text_limited(path)
            tree = ast.parse(text, filename=str(path))
            scanned += 1
            local_names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    local_names.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    local_names.add(node.module.split(".", 1)[0])
            for name in local_names:
                counts[name] += 1
                if len(samples[name]) < 5:
                    samples[name].append(str(path.relative_to(root)))
        except (SyntaxError, UnicodeError) as exc:
            if len(syntax_errors) < 100:
                syntax_errors.append({"path": str(path.relative_to(root)), "error": f"{type(exc).__name__}: {exc}"})
        except Exception:
            continue
    stdlib = set(getattr(sys, "stdlib_module_names", set()))
    local_top = {p.name for p in comfy_root.iterdir() if p.is_dir()} | {p.stem for p in comfy_root.glob("*.py")}
    third_party_candidates = [
        {"module": name, "file_count": count, "samples": samples[name]}
        for name, count in counts.most_common()
        if name not in stdlib and name not in local_top and not name.startswith("_")
    ]
    return {
        "python_files_scanned": scanned,
        "syntax_error_count": len(syntax_errors),
        "syntax_errors": syntax_errors,
        "all_top_level_imports": dict(counts.most_common()),
        "third_party_import_candidates": third_party_candidates,
        "limitations": [
            "Static AST scanning does not see every dynamic import.",
            "Import names are not always identical to distribution names.",
        ],
    }


def dist_inventory(paths: list[Path]) -> dict[str, Any]:
    existing = [str(p) for p in paths if p.is_dir()]
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    try:
        for dist in md.distributions(path=existing):
            name = dist.metadata.get("Name") or ""
            if not name:
                continue
            key = canonical_name(name)
            rec = {
                "name": name,
                "version": dist.version,
                "metadata_path": str(getattr(dist, "_path", "")),
                "requires": dist.requires or [],
            }
            found.setdefault(key, rec)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return {"paths": existing, "distribution_count": len(found), "distributions": dict(sorted(found.items())), "errors": errors}


def requirement_status(requirements: list[dict[str, Any]], distributions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for req in requirements:
        name = req.get("name")
        if not name:
            continue
        if req.get("marker_applies") is False:
            statuses.append({"name": name, "raw": req.get("raw"), "status": "NOT_APPLICABLE_MARKER", "source": req.get("source")})
            continue
        dist = distributions.get(name)
        item = {
            "name": name,
            "raw": req.get("raw"),
            "source": req.get("source"),
            "installed": bool(dist),
            "installed_version": dist.get("version") if dist else None,
            "specifier": req.get("specifier"),
        }
        if not dist:
            item["status"] = "MISSING"
        elif PACKAGING_AVAILABLE and req.get("specifier"):
            try:
                parsed = PackagingRequirement(req["raw"])
                ok = parsed.specifier.contains(PackagingVersion(dist["version"]), prereleases=True)
                item["specifier_satisfied"] = bool(ok)
                item["status"] = "SATISFIED" if ok else "VERSION_CONFLICT"
            except Exception as exc:
                item["status"] = "PRESENT_CONSTRAINT_UNVERIFIED"
                item["check_error"] = f"{type(exc).__name__}: {exc}"
        else:
            item["status"] = "PRESENT" if not req.get("specifier") else "PRESENT_CONSTRAINT_UNVERIFIED"
        statuses.append(item)
    return statuses


def parse_wheel_filename(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path), "filename": path.name, "size_bytes": path.stat().st_size}
    match = WHEEL_NAME_RE.match(path.name)
    if not match:
        rec["filename_parse_error"] = True
        return rec
    tags = []
    for py in match.group("py").split("."):
        for abi in match.group("abi").split("."):
            for plat in match.group("plat").split("."):
                tags.append(f"{py}-{abi}-{plat}")
    rec.update({
        "name": canonical_name(match.group("name")),
        "version": match.group("version"),
        "build": match.group("build"),
        "filename_tags": tags,
    })
    return rec


def inspect_wheel(path: Path, supported_tags: set[str]) -> dict[str, Any]:
    rec = parse_wheel_filename(path)
    try:
        rec["sha256"] = sha256_file(path)
        with zipfile.ZipFile(path) as z:
            metadata_names = [n for n in z.namelist() if n.endswith(".dist-info/METADATA")]
            wheel_names = [n for n in z.namelist() if n.endswith(".dist-info/WHEEL")]
            if metadata_names:
                raw = z.read(metadata_names[0]).decode("utf-8", errors="replace")
                msg = Parser().parsestr(raw)
                rec["metadata"] = {
                    "name": msg.get("Name"),
                    "version": msg.get("Version"),
                    "requires_python": msg.get("Requires-Python"),
                    "requires_dist": msg.get_all("Requires-Dist") or [],
                }
            if wheel_names:
                raw = z.read(wheel_names[0]).decode("utf-8", errors="replace")
                msg = Parser().parsestr(raw)
                rec["wheel_tags"] = msg.get_all("Tag") or []
                rec["root_is_purelib"] = msg.get("Root-Is-Purelib")
    except Exception as exc:
        rec["inspection_error"] = f"{type(exc).__name__}: {exc}"
    wheel_tags = set(rec.get("wheel_tags") or rec.get("filename_tags") or [])
    rec["compatible_with_portable_runtime"] = bool(wheel_tags & supported_tags) if supported_tags else None
    rec["matching_supported_tags"] = sorted(wheel_tags & supported_tags)[:50]
    return rec


def wheelhouse_inventory(root: Path, supported_tags: list[str]) -> dict[str, Any]:
    dirs = [root / "Wheelhouse", root / "wheelhouse", root / "Wheels", root / "wheels"]
    wheels: list[dict[str, Any]] = []
    for d in dirs:
        if d.is_dir():
            for p in d.rglob("*.whl"):
                if p.is_file():
                    rec = inspect_wheel(p, set(supported_tags))
                    rec["path"] = str(p.relative_to(root))
                    wheels.append(rec)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for wheel in wheels:
        if wheel.get("name"):
            by_name[wheel["name"]].append(wheel)
    return {
        "scanned_directories": [str(d) for d in dirs],
        "wheel_count": len(wheels),
        "compatible_wheel_count": sum(1 for w in wheels if w.get("compatible_with_portable_runtime") is True),
        "wheels": wheels,
        "by_name": dict(sorted(by_name.items())),
    }


def pe_info(path: Path, include_imports: bool = True) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path), "size_bytes": path.stat().st_size}
    machine_names = {0x014C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}
    try:
        with path.open("rb") as f:
            if f.read(2) != b"MZ":
                rec["pe"] = False
                return rec
            f.seek(0x3C)
            pe_offset = struct.unpack("<I", f.read(4))[0]
            f.seek(pe_offset)
            if f.read(4) != b"PE\0\0":
                rec["pe"] = False
                return rec
            file_header = f.read(20)
            machine, section_count, _, _, _, opt_size, characteristics = struct.unpack("<HHIIIHH", file_header)
            optional = f.read(opt_size)
            magic = struct.unpack_from("<H", optional, 0)[0]
            rec.update({
                "pe": True,
                "machine": machine_names.get(machine, hex(machine)),
                "machine_code": hex(machine),
                "section_count": section_count,
                "optional_magic": hex(magic),
                "characteristics": hex(characteristics),
            })
            if not include_imports or magic not in (0x10B, 0x20B):
                return rec
            data_dir_offset = 96 if magic == 0x10B else 112
            import_rva, import_size = struct.unpack_from("<II", optional, data_dir_offset + 8)
            sections = []
            for _ in range(section_count):
                raw = f.read(40)
                name = raw[:8].rstrip(b"\0").decode("ascii", errors="replace")
                virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", raw, 8)
                sections.append((name, virtual_address, max(virtual_size, raw_size), raw_ptr))

            def rva_to_offset(rva: int) -> int | None:
                for _, va, span, ptr in sections:
                    if va <= rva < va + span:
                        return ptr + (rva - va)
                return None

            imports: list[str] = []
            if import_rva:
                desc_offset = rva_to_offset(import_rva)
                if desc_offset is not None:
                    for idx in range(4096):
                        f.seek(desc_offset + idx * 20)
                        raw = f.read(20)
                        if len(raw) < 20:
                            break
                        values = struct.unpack("<IIIII", raw)
                        if values == (0, 0, 0, 0, 0):
                            break
                        name_offset = rva_to_offset(values[3])
                        if name_offset is None:
                            continue
                        f.seek(name_offset)
                        buf = bytearray()
                        while len(buf) < 1024:
                            b = f.read(1)
                            if not b or b == b"\0":
                                break
                            buf.extend(b)
                        imports.append(buf.decode("ascii", errors="replace"))
            rec["imports"] = sorted(set(imports), key=str.lower)
            rec["import_directory_size"] = import_size
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def binary_inventory(
    paths: list[Path],
    root: Path,
    resolver_dirs: list[Path] | None = None,
    max_files: int = 30000,
) -> dict[str, Any]:
    binaries: list[dict[str, Any]] = []
    available_dlls: set[str] = set()
    scanned_paths: list[str] = []
    resolver_paths: list[str] = []
    for resolver in resolver_dirs or []:
        if resolver.is_dir():
            resolver_paths.append(str(resolver))
            try:
                for p in resolver.iterdir():
                    if p.is_file() and p.suffix.lower() in {".dll", ".exe"}:
                        available_dlls.add(p.name.lower())
            except Exception:
                pass
    for base in paths:
        if not base.exists():
            continue
        scanned_paths.append(str(base))
        iterator = [base] if base.is_file() else walk_files(base, BINARY_SUFFIXES, max_files=max_files)
        for p in iterator:
            if p.suffix.lower() not in BINARY_SUFFIXES:
                continue
            available_dlls.add(p.name.lower())
            info = pe_info(p)
            try:
                info["path"] = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
            except Exception:
                info["path"] = str(p)
            binaries.append(info)
            if len(binaries) >= max_files:
                break
        if len(binaries) >= max_files:
            break

    # Windows API set names are resolved virtually by the loader.
    virtual_prefixes = ("api-ms-win-", "ext-ms-win-")
    always_system = {
        "kernel32.dll", "user32.dll", "advapi32.dll", "ole32.dll", "oleaut32.dll",
        "shell32.dll", "ntdll.dll", "ws2_32.dll", "bcrypt.dll", "crypt32.dll",
        "gdi32.dll", "comdlg32.dll", "shlwapi.dll", "secur32.dll", "rpcrt4.dll",
        "version.dll", "winmm.dll", "imm32.dll", "setupapi.dll", "cfgmgr32.dll",
        "normaliz.dll", "dbghelp.dll", "psapi.dll", "msvcrt.dll",
    }
    import_counts: Counter[str] = Counter()
    unresolved: Counter[str] = Counter()
    for item in binaries:
        for dep in item.get("imports") or []:
            low = dep.lower()
            import_counts[low] += 1
            if low in available_dlls or low in always_system or low.startswith(virtual_prefixes):
                continue
            unresolved[low] += 1
    machine_mismatches = [b for b in binaries if b.get("pe") and b.get("machine") not in ("x64", None)]
    return {
        "scanned_paths": scanned_paths,
        "resolver_paths": resolver_paths,
        "binary_count": len(binaries),
        "available_dll_name_count": len(available_dlls),
        "machine_mismatch_count": len(machine_mismatches),
        "machine_mismatches": machine_mismatches[:200],
        "imported_dll_counts": dict(import_counts.most_common()),
        "unresolved_loader_names": dict(unresolved.most_common()),
        "binaries": binaries,
        "limitations": [
            "Unresolved loader names are evidence for review, not proof of runtime failure; Windows search paths and side-by-side assemblies can resolve additional DLLs.",
            "Delay-load imports are not parsed by this preflight.",
        ],
    }


def collect_host_candidates() -> list[Path]:
    candidates = [Path(r"C:\Python314\python.exe"), Path(sys.executable)]
    for name in ("python.exe", "python3.exe", "py.exe", "python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    unique: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def collect_package_binary_roots(runtime_data: dict[str, Any], module_names: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    imports = runtime_data.get("imports") or {}
    for name in module_names:
        item = imports.get(name) or {}
        file = item.get("file")
        if file:
            p = Path(file)
            roots.append(p.parent if p.is_file() else p)
        ext = item.get("extension_origin")
        if ext:
            roots.append(Path(ext).parent)
    unique: list[Path] = []
    seen: set[str] = set()
    for p in roots:
        key = str(safe_resolve(p)).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def package_pair_compatibility(runtime_data: dict[str, Any]) -> list[dict[str, Any]]:
    distributions = runtime_data.get("distributions") or {}
    checks: list[dict[str, Any]] = []
    for dependent in ("torchvision", "torchaudio"):
        dist = distributions.get(dependent)
        if not dist:
            continue
        for raw in dist.get("requires") or []:
            req = requirement_record(raw, f"installed metadata: {dependent}")
            if req.get("name") != "torch":
                continue
            status = requirement_status([req], distributions)[0]
            status["dependent"] = dependent
            checks.append(status)
    return checks


def produce_report(output: Path, summary: dict[str, Any]) -> None:
    c = summary["classification"]
    lines = [
        "# FOXAI USB C3A",
        "## ComfyUI Dependency Closure and Binary Compatibility Preflight",
        "",
        f"- State: **{summary['state']}**",
        f"- Verified: **{summary['verified']}**",
        f"- Root: `{summary['root']}`",
        f"- Portable Python: `{summary['portable_python']}`",
        f"- Preferred isolated target: `{summary['preferred_target']}`",
        f"- Target existed before preflight: **{summary['target_existed']}**",
        f"- Classification: **{c['mode']}**",
        f"- Live runtime/ComfyUI files modified: **False**",
        f"- Install/download/copy/launcher change/launch/network: **False**",
        "",
        "## Blocking findings",
        "",
    ]
    if c["blocking_findings"]:
        lines.extend(f"- {x}" for x in c["blocking_findings"])
    else:
        lines.append("- None detected by this preflight.")
    lines += ["", "## Important findings", ""]
    lines.extend(f"- {x}" for x in c["notes"] or ["No additional notes."])
    lines += ["", "## Next gate", "", f"- {c['next_gate']}", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main_preflight(args: argparse.Namespace) -> int:
    start_dt = utc_now()
    started = time.monotonic()
    script = safe_resolve(Path(__file__))
    package_root = script.parents[2]
    root = safe_resolve(Path(args.root)) if args.root else find_root(package_root.parent)

    output_base = package_root / "PREFLIGHT_OUTPUT"
    stamp = start_dt.strftime("%Y%m%dT%H%M%SZ")
    output = output_base / stamp
    output.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": ACTION,
        "created": start_dt.isoformat(),
        "state": "preflight_started_fail_closed",
        "verified": False,
        "read_only_preflight": True,
        "live_files_modified": False,
        "files_deleted": False,
        "files_overwritten": False,
        "target_directory_created": False,
        "package_install": False,
        "package_download": False,
        "package_copy": False,
        "launcher_change": False,
        "network_access": False,
        "foxai_launched": False,
        "webui_launched": False,
        "desktop_launched": False,
        "comfyui_launched": False,
        "writes_limited_to": str(output),
    }
    write_json(output / "receipt.json", receipt)

    if root is None:
        receipt.update({
            "state": "failed_closed_root_not_verified",
            "completed": iso_now(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "classification": "FAIL_CLOSED_ROOT_NOT_VERIFIED",
        })
        write_json(output / "receipt.json", receipt)
        write_json(output / "classification.json", {
            "mode": "FAIL_CLOSED_ROOT_NOT_VERIFIED",
            "blocking_findings": ["The FOXAI root could not be verified from package location or --root."],
            "notes": [],
            "next_gate": "Place the package directly under the verified FOXAI root and rerun.",
        })
        return 2

    identity = root_identity(root)
    write_json(output / "root_identity.json", identity)
    portable_python = root / EXPECTED_RELATIVE_PYTHON
    target = root / PREFERRED_TARGET_REL
    target_existed = target.exists()
    target_before = {
        "path": str(target),
        "exists": target_existed,
        "is_directory": target.is_dir(),
        "entry_count": len(list(target.iterdir())) if target.is_dir() else None,
    }
    write_json(output / "target_state.json", target_before)

    if not identity["verified"]:
        receipt.update({
            "root": str(root),
            "state": "failed_closed_root_markers_missing",
            "completed": iso_now(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "classification": "FAIL_CLOSED_ROOT_MARKERS_MISSING",
        })
        write_json(output / "receipt.json", receipt)
        write_json(output / "classification.json", {
            "mode": "FAIL_CLOSED_ROOT_MARKERS_MISSING",
            "blocking_findings": ["ComfyUI main.py or the verified Desktop portable Python is missing."],
            "notes": [],
            "next_gate": "Stop and review the root markers; do not install anything.",
        })
        return 3

    # Runtime probes.
    portable_probe = run_json_probe(
        portable_python, script,
        ["--runtime-probe", "--modules", ""],
        timeout=60,
    )
    write_json(output / "portable_runtime.json", portable_probe)
    portable_data = portable_probe.get("data") or {}

    # Dependency manifests and static imports.
    manifests = collect_manifests(root, root / COMFY_REL)
    write_json(output / "dependency_manifests.json", manifests)
    imports = static_import_inventory(root / COMFY_REL, root)
    write_json(output / "static_import_inventory.json", imports)

    target_paths = [target]
    portable_paths = [
        root / "Runtime/Desktop/site-packages",
        root / "Runtime/Core/site-packages",
        target,
    ]
    portable_dists = dist_inventory(portable_paths)
    write_json(output / "portable_distribution_inventory.json", portable_dists)
    target_dists = dist_inventory(target_paths)
    write_json(output / "target_distribution_inventory.json", target_dists)

    target_status = requirement_status(manifests["requirements"], target_dists["distributions"])
    portable_status = requirement_status(manifests["requirements"], portable_dists["distributions"])
    write_json(output / "dependency_status_target.json", target_status)
    write_json(output / "dependency_status_portable_paths.json", portable_status)

    wheels = wheelhouse_inventory(root, portable_data.get("supported_tags") or [])
    write_json(output / "wheelhouse_compatibility.json", wheels)

    # Host runtime discovery and binary smoke.
    host_probes: list[dict[str, Any]] = []
    selected_host: dict[str, Any] | None = None
    selected_host_exe: Path | None = None
    for candidate in collect_host_candidates():
        if not candidate.exists():
            host_probes.append({"path": str(candidate), "exists": False})
            continue
        probe = run_json_probe(
            candidate,
            script,
            ["--runtime-probe", "--modules", "torch,torchvision,torchaudio", "--tensor-smoke"],
            timeout=120,
            allow_user_site=True,
        )
        probe["path"] = str(candidate)
        probe["exists"] = True
        host_probes.append(probe)
        data = probe.get("data") or {}
        if (data.get("imports") or {}).get("torch", {}).get("available") and selected_host is None:
            selected_host = data
            selected_host_exe = candidate
    write_json(output / "host_runtime_probes.json", host_probes)

    injected_probe: dict[str, Any] = {"status": "not_run", "reason": "No usable host torch runtime found."}
    pair_checks: list[dict[str, Any]] = []
    if selected_host:
        pair_checks = package_pair_compatibility(selected_host)
        host_paths = [p for p in selected_host.get("sys_path") or [] if p and "site-packages" in p.lower() and Path(p).is_dir()]
        probe_args = ["--runtime-probe", "--modules", "torch,torchvision,torchaudio", "--tensor-smoke"]
        for p in host_paths:
            probe_args += ["--extra-path", p]
        injected_probe = run_json_probe(portable_python, script, probe_args, timeout=120)
        injected_probe["source_host_python"] = str(selected_host_exe)
        injected_probe["injected_paths"] = host_paths
    write_json(output / "portable_with_host_stack_probe.json", injected_probe)
    write_json(output / "torch_family_metadata_compatibility.json", pair_checks)

    # Binary inventory is static and never loads ComfyUI. Include system DLL names on Windows.
    binary_roots = [portable_python.parent, target]
    if selected_host:
        binary_roots.extend(collect_package_binary_roots(selected_host, ("torch", "torchvision", "torchaudio")))
    resolver_dirs: list[Path] = []
    system_root = os.environ.get("SystemRoot")
    if system_root:
        resolver_dirs.append(Path(system_root) / "System32")
    binaries = binary_inventory(binary_roots, root, resolver_dirs=resolver_dirs)
    write_json(output / "binary_inventory.json", binaries)

    # Derive classification.
    blocking: list[str] = []
    notes: list[str] = []
    portable_ok = portable_probe.get("returncode") == 0 and bool(portable_data)
    if not portable_ok:
        blocking.append("The verified Desktop portable Python did not complete the environment probe.")
    else:
        actual_version = tuple((portable_data.get("version_info") or [])[:3])
        if actual_version != EXPECTED_PORTABLE_VERSION:
            blocking.append(
                "Verified Desktop runtime drift: expected Python "
                + ".".join(map(str, EXPECTED_PORTABLE_VERSION))
                + ", observed "
                + (".".join(map(str, actual_version)) if actual_version else "unknown")
                + "."
            )
        observed_exe = os.path.normcase(os.path.abspath(str(portable_data.get("executable") or "")))
        expected_exe = os.path.normcase(os.path.abspath(str(portable_python)))
        if observed_exe and observed_exe != expected_exe:
            blocking.append(
                f"Portable interpreter identity drift: expected {portable_python}, observed {portable_data.get('executable')}."
            )

    manifest_names = set(manifests["requirements_by_name"])
    if not manifest_names:
        blocking.append("No named ComfyUI dependency requirements were parsed.")
    else:
        notes.append(f"Parsed {len(manifest_names)} unique named dependencies from {manifests['manifest_count']} manifests.")

    injected_data = injected_probe.get("data") or {}
    injected_imports = injected_data.get("imports") or {}
    torch_ok = bool(injected_imports.get("torch", {}).get("available"))
    tv_ok = bool(injected_imports.get("torchvision", {}).get("available"))
    ta_ok = bool(injected_imports.get("torchaudio", {}).get("available"))
    tensor_ok = bool(injected_imports.get("torch", {}).get("tensor_smoke"))
    if selected_host is None:
        blocking.append("No host Python runtime with an importable torch stack was found.")
    elif not (torch_ok and tv_ok and ta_ok and tensor_ok):
        blocking.append("The host torch family did not fully load through the portable Python with a tensor smoke test.")
    else:
        notes.append("Portable Python loaded the host torch, torchvision, and torchaudio stack and passed a minimal CPU tensor smoke test.")

    conflicts = [x for x in pair_checks if x.get("status") == "VERSION_CONFLICT"]
    unverified_pairs = [x for x in pair_checks if x.get("status") == "PRESENT_CONSTRAINT_UNVERIFIED"]
    if conflicts:
        for item in conflicts:
            blocking.append(
                f"Installed {item.get('dependent')} metadata requires {item.get('raw')}, but torch {item.get('installed_version')} is present."
            )
    elif unverified_pairs:
        blocking.append("Torch-family metadata pins could not be evaluated exactly because the packaging parser was unavailable.")

    if binaries["machine_mismatch_count"]:
        blocking.append(f"Found {binaries['machine_mismatch_count']} non-x64 PE binaries in the candidate runtime paths.")
    unresolved = binaries.get("unresolved_loader_names") or {}
    if unresolved:
        notes.append(f"Static PE review found {len(unresolved)} unresolved loader names requiring exact review; these are not automatically classified as failures.")

    target_nonempty = target_existed and bool(target_before.get("entry_count"))
    if target_nonempty:
        blocking.append("The preferred isolated target already exists and is non-empty; no closure plan may overwrite it without exact review.")
    elif target_existed:
        notes.append("The preferred isolated target exists and is empty; the preflight did not modify it.")
    else:
        notes.append("The preferred isolated target does not exist; the preflight did not create it.")

    compatible_torch_wheels = []
    for name in ("torch", "torchvision", "torchaudio"):
        compatible_torch_wheels.extend([w for w in (wheels.get("by_name") or {}).get(name, []) if w.get("compatible_with_portable_runtime")])
    if not compatible_torch_wheels:
        notes.append("No compatible USB wheelhouse wheels were found for torch, torchvision, or torchaudio.")

    target_missing = [x for x in target_status if x.get("status") == "MISSING"]
    notes.append(f"Preferred target currently lacks {len({x['name'] for x in target_missing})} unique parsed dependency distributions.")

    if blocking:
        if conflicts:
            mode = "BLOCKED_TORCH_FAMILY_VERSION_CONFLICT"
            next_gate = "Review the exact torch/torchvision/torchaudio version set and acquire a mutually compatible offline set before any install preview."
        elif target_nonempty:
            mode = "FAIL_CLOSED_TARGET_NOT_EMPTY"
            next_gate = "Inventory and approve the existing target contents before any dependency action."
        elif selected_host and not (torch_ok and tv_ok and ta_ok and tensor_ok):
            mode = "BLOCKED_BINARY_COMPATIBILITY"
            next_gate = "Review the portable-with-host-stack traceback and PE/DLL evidence; do not copy or install packages."
        else:
            mode = "C3A_REVIEW_REQUIRED"
            next_gate = "Review the captured dependency and binary evidence; do not install or copy packages."
    else:
        mode = "C3A_READY_FOR_EXACT_CLOSURE_PLAN"
        next_gate = "Prepare a no-action exact dependency closure plan for the isolated target, including hashes, sizes, sources, and rollback boundaries."

    classification = {
        "mode": mode,
        "blocking_findings": blocking,
        "notes": notes,
        "next_gate": next_gate,
    }
    write_json(output / "classification.json", classification)

    summary = {
        "state": "preflight_complete_ready_for_exact_review",
        "verified": portable_ok and identity["verified"],
        "root": str(root),
        "portable_python": str(portable_python),
        "preferred_target": str(target),
        "target_existed": target_existed,
        "classification": classification,
    }
    produce_report(output, summary)

    receipt.update({
        "root": str(root),
        "state": summary["state"],
        "verified": summary["verified"],
        "completed": iso_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "classification": mode,
    })
    write_json(output / "receipt.json", receipt)

    # Integrity manifest of evidence only; no live files are copied.
    evidence_files = []
    for p in sorted(output.iterdir(), key=lambda p: p.name.lower()):
        if p.is_file() and p.name != "evidence_integrity.json":
            evidence_files.append({"name": p.name, "size_bytes": p.stat().st_size, "sha256": sha256_file(p)})
    write_json(output / "evidence_integrity.json", {"files": evidence_files, "count": len(evidence_files)})
    print(json.dumps({"output": str(output), "classification": mode, "verified": summary["verified"]}))
    return 0 if summary["verified"] else 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Verified FOXAI root. Normally auto-detected from package location.")
    parser.add_argument("--runtime-probe", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--extra-path", action="append", default=[], help=argparse.SUPPRESS)
    parser.add_argument("--modules", default="", help=argparse.SUPPRESS)
    parser.add_argument("--tensor-smoke", action="store_true", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.runtime_probe:
        modules = [x.strip() for x in args.modules.split(",") if x.strip()]
        print(json.dumps(probe_current_runtime(args.extra_path, modules, args.tensor_smoke), ensure_ascii=False))
        return 0
    return main_preflight(args)


if __name__ == "__main__":
    raise SystemExit(main())
