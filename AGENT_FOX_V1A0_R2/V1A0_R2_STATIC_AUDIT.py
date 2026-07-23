from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "foxai.agent_fox.technical_core.v1a0.r2.static_baseline.v1"
MISSION_ID = "ENG-20260721-042128-CF3008"
DEFAULT_ROOT = Path(r"Z:\FOXAI")
DEFAULT_OUTPUT_RELATIVE = Path(r"System\EngineeringWorkshop\missions\ENG-20260721-042128-CF3008_V1A0_R2_STATIC_AUDIT")
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_HASH_BYTES = 16 * 1024 * 1024
MAX_ITEMS = 5000
EXCLUDED_DIR_NAMES = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "cache", "caches", "temp", "tmp"
}
LAUNCHER_SUFFIXES = {".bat", ".cmd", ".ps1", ".vbs", ".lnk"}
MODEL_SUFFIXES = {".gguf", ".safetensors", ".ckpt", ".pt", ".pth", ".onnx"}
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".index", ".faiss"}
TEXT_CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".txt"}
PROTECTED_CANDIDATES = (
    r"core\foxai_web.py",
    r"Config\model_sources.json",
    r"Launch FOXAI Workshop.bat",
    r"START_FOXAI_WEB_PORTABLE.bat",
    r"START_FOXAI_WEB_WITH_COMFYUI.bat",
    r"START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat",
)
REUSABLE_NAMES = {
    "source_locator.py", "health.py", "manifest.json", "core_api.py",
    "capability_graph.py", "dependency_graph.py", "evidence_ranker.py",
    "confidence_engine.py", "recommendation_engine.py", "investigation_engine.py",
    "snapshot.py", "rollback.py", "receipt.py", "validator.py", "patch_engine.py",
}
PATH_TOKEN_RE = re.compile(
    r'''(?ix)
    (?P<quoted>"[^"\r\n]+\.(?:exe|py|bat|cmd|ps1|vbs)")
    |
    (?P<bare>(?:[A-Za-z]:\\|%[A-Za-z0-9_]+%\\|\.\\|\.\.\\)[^\r\n&|<>]+?\.(?:exe|py|bat|cmd|ps1|vbs))
    '''
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(value: Path) -> str:
    return str(value).replace("/", "\\")


def within(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def read_text_bounded(path: Path, limit: int = MAX_TEXT_BYTES) -> tuple[str | None, str | None]:
    try:
        size = path.stat().st_size
        if size > limit:
            return None, f"skipped_text_over_limit:{size}"
        data = path.read_bytes()
    except (OSError, PermissionError) as exc:
        return None, f"read_error:{type(exc).__name__}:{exc}"
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            return data.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, "unsupported_encoding"


def hash_small(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        result: dict[str, Any] = {
            "path": norm(path), "exists": True, "size_bytes": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
        }
        if stat.st_size <= MAX_HASH_BYTES:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            result["sha256"] = digest.hexdigest()
        else:
            result["sha256"] = None
            result["hash_status"] = "skipped_over_limit"
        return result
    except (OSError, PermissionError) as exc:
        return {"path": norm(path), "exists": path.exists(), "error": f"{type(exc).__name__}:{exc}"}


def safe_mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except (OSError, PermissionError):
        return 0


def entry_meta(path: Path, root: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {
            "path": norm(path),
            "relative_path": norm(path.relative_to(root)) if within(path, root) else None,
            "kind": "directory" if path.is_dir() else "file",
            "size_bytes": stat.st_size if path.is_file() else None,
            "modified_ns": stat.st_mtime_ns,
            "suffix": path.suffix.lower() if path.is_file() else "",
        }
    except (OSError, PermissionError) as exc:
        return {"path": norm(path), "error": f"{type(exc).__name__}:{exc}"}


def walk_bounded(
    starts: Iterable[Path], root: Path, *, max_depth: int, max_items: int,
    file_filter=None, dir_filter=None, max_scanned: int = 50000
) -> tuple[list[Path], list[str]]:
    found: list[Path] = []
    warnings: list[str] = []
    scanned_entries = 0
    stack: list[tuple[Path, int]] = []
    for start in starts:
        if start.exists() and within(start, root):
            stack.append((start, 0))
    seen: set[str] = set()
    while stack and len(found) < max_items and scanned_entries < max_scanned:
        current, depth = stack.pop()
        key = os.path.normcase(str(current.resolve(strict=False)))
        if key in seen:
            continue
        seen.add(key)
        try:
            if current.is_symlink():
                warnings.append(f"skipped_symlink:{norm(current)}")
                continue
            with os.scandir(current) as iterator:
                entries = list(iterator)
        except (OSError, PermissionError) as exc:
            warnings.append(f"scan_error:{norm(current)}:{type(exc).__name__}:{exc}")
            continue
        entries.sort(key=lambda item: item.name.casefold())
        for entry in entries:
            scanned_entries += 1
            if scanned_entries > max_scanned:
                break
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    warnings.append(f"skipped_symlink:{norm(path)}")
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.casefold() in EXCLUDED_DIR_NAMES:
                        continue
                    if dir_filter is not None and dir_filter(path):
                        found.append(path)
                        if len(found) >= max_items:
                            break
                    if depth < max_depth:
                        stack.append((path, depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    if file_filter is None or file_filter(path):
                        found.append(path)
                        if len(found) >= max_items:
                            break
            except (OSError, PermissionError) as exc:
                warnings.append(f"entry_error:{norm(path)}:{type(exc).__name__}:{exc}")
    if scanned_entries >= max_scanned:
        warnings.append(f"scan_entry_limit_reached:{max_scanned}")
    elif stack:
        warnings.append(f"item_limit_reached:{max_items}")
    return found, warnings


def top_level_inventory(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    items: list[dict[str, Any]] = []
    try:
        paths = sorted(root.iterdir(), key=lambda p: p.name.casefold())
    except (OSError, PermissionError) as exc:
        return [], [f"root_list_error:{type(exc).__name__}:{exc}"]
    for path in paths[:1000]:
        if path.is_symlink():
            warnings.append(f"skipped_symlink:{norm(path)}")
            continue
        items.append(entry_meta(path, root))
    return items, warnings


def collect_launchers(root: Path) -> dict[str, Any]:
    starts = [root, root / "System", root / "Departments"]
    files, warnings = walk_bounded(
        starts, root, max_depth=4, max_items=800,
        file_filter=lambda p: p.suffix.lower() in LAUNCHER_SUFFIXES, max_scanned=25000,
    )
    records: list[dict[str, Any]] = []
    for path in sorted(set(files), key=lambda p: str(p).casefold()):
        record = entry_meta(path, root)
        record.update({"execution_performed": False, "interesting_lines": [], "path_tokens": []})
        if path.suffix.lower() == ".lnk":
            record["parse_status"] = "shortcut_target_not_resolved_in_static_r2"
            records.append(record)
            continue
        text, error = read_text_bounded(path)
        if error:
            record["parse_status"] = error
            records.append(record)
            continue
        assert text is not None
        interesting: list[dict[str, Any]] = []
        tokens: set[str] = set()
        for line_no, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.casefold().startswith(("rem ", "::", "#")):
                continue
            lowered = stripped.casefold()
            if any(term in lowered for term in ("python", ".py", "llama", "comfy", "call ", "start ", "set ", "cd ", "pushd", "http://", "https://")):
                if len(interesting) < 250:
                    interesting.append({"line": line_no, "text": stripped[:2000]})
            for match in PATH_TOKEN_RE.finditer(stripped):
                token = (match.group("quoted") or match.group("bare") or "").strip('" ')
                if token:
                    tokens.add(token[:2000])
        record["parse_status"] = "static_text_parsed"
        record["interesting_lines"] = interesting
        record["path_tokens"] = sorted(tokens, key=str.casefold)[:500]
        records.append(record)
    return {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "execution_performed": False,
        "launcher_count": len(records),
        "launchers": records,
        "warnings": warnings,
    }


def collect_static_python_runtimes(root: Path, launchers: dict[str, Any]) -> dict[str, Any]:
    runtime_root = root / "Runtime"
    files, warnings = walk_bounded(
        [runtime_root], root, max_depth=7, max_items=250,
        file_filter=lambda p: p.name.casefold() in {"python.exe", "pythonw.exe"}, max_scanned=30000,
    )
    candidates: dict[str, Path] = {os.path.normcase(str(p)): p for p in files}
    for launcher in launchers.get("launchers", []):
        for token in launcher.get("path_tokens", []):
            expanded = os.path.expandvars(token)
            p = Path(expanded)
            if not p.is_absolute():
                p = root / p
            if p.name.casefold() in {"python.exe", "pythonw.exe"}:
                candidates.setdefault(os.path.normcase(str(p)), p)
    records = []
    for path in sorted(candidates.values(), key=lambda p: str(p).casefold()):
        record = entry_meta(path, root)
        record.update({
            "interpreter_executed": False,
            "version": None,
            "sys_path": None,
            "prefixes": None,
            "user_site_state": None,
            "missing_evidence": "Runtime execution intentionally deferred; static file evidence only.",
        })
        records.append(record)

    site_packages, site_warnings = walk_bounded(
        [runtime_root], root, max_depth=8, max_items=100,
        dir_filter=lambda p: p.name.casefold() == "site-packages",
        file_filter=lambda p: False, max_scanned=25000,
    )
    warnings.extend(site_warnings)
    packages: list[dict[str, Any]] = []
    for site in sorted(set(site_packages), key=lambda p: str(p).casefold()):
        try:
            metadata_files = sorted(site.glob("*.dist-info/METADATA"), key=lambda p: p.name.casefold())[:1500]
        except OSError as exc:
            warnings.append(f"site_packages_error:{norm(site)}:{type(exc).__name__}:{exc}")
            continue
        for metadata in metadata_files:
            text, error = read_text_bounded(metadata, 512 * 1024)
            if error or text is None:
                packages.append({"metadata_path": norm(metadata), "error": error})
                continue
            name = None
            version = None
            for line in text.splitlines():
                if line.startswith("Name:") and name is None:
                    name = line.partition(":")[2].strip()
                elif line.startswith("Version:") and version is None:
                    version = line.partition(":")[2].strip()
                if name is not None and version is not None:
                    break
            packages.append({
                "name": name,
                "version": version,
                "metadata_path": norm(metadata),
                "site_packages": norm(site),
                "evidence_class": "static_package_metadata",
            })
            if len(packages) >= 3000:
                warnings.append("package_limit_reached:3000")
                break
        if len(packages) >= 3000:
            break
    return {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "probe_mode": "static_only_no_interpreter_execution",
        "runtime_count": len(records),
        "runtimes": records,
        "package_metadata_count": len(packages),
        "packages": packages,
        "host_vs_portable_conflicts_verified": False,
        "missing_evidence": [
            "Exact interpreter versions, sys.path, prefixes, environment differences, and active runtime ownership require a later explicitly bounded runtime-probe mission.",
            "No Python interpreter other than the Workshop validation interpreter was launched by this collector.",
        ],
        "warnings": warnings,
    }


def collect_reusable_components(root: Path) -> dict[str, Any]:
    starts = [root / "core", root / "Departments", root / "System", root / "Repair Bay", root / "RepairBay"]
    files, warnings = walk_bounded(
        starts, root, max_depth=7, max_items=1500,
        file_filter=lambda p: p.name.casefold() in REUSABLE_NAMES or p.name.casefold().endswith("manifest.json"), max_scanned=30000,
    )
    records: list[dict[str, Any]] = []
    import_edges: list[dict[str, str]] = []
    for path in sorted(set(files), key=lambda p: str(p).casefold()):
        record = entry_meta(path, root)
        if path.suffix.lower() == ".py":
            text, error = read_text_bounded(path)
            if error or text is None:
                record["parse_status"] = error
            else:
                try:
                    tree = ast.parse(text, filename=str(path))
                    definitions: list[dict[str, Any]] = []
                    imports: list[str] = []
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and len(definitions) < 500:
                            definitions.append({"name": node.name, "kind": type(node).__name__, "line": node.lineno})
                        elif isinstance(node, ast.Import):
                            imports.extend(alias.name for alias in node.names)
                        elif isinstance(node, ast.ImportFrom):
                            imports.append("." * node.level + (node.module or ""))
                    record.update({
                        "parse_status": "ast_parsed_without_import",
                        "definitions": definitions,
                        "imports": sorted(set(imports), key=str.casefold)[:1000],
                    })
                    for target in record["imports"]:
                        if len(import_edges) < 10000:
                            import_edges.append({"source": record.get("relative_path") or norm(path), "import": target})
                except SyntaxError as exc:
                    record["parse_status"] = f"syntax_error:{exc.lineno}:{exc.msg}"
        elif path.suffix.lower() == ".json":
            text, error = read_text_bounded(path)
            if error or text is None:
                record["parse_status"] = error
            else:
                try:
                    data = json.loads(text)
                    record["parse_status"] = "json_parsed"
                    record["top_level_keys"] = sorted(data.keys(), key=str.casefold)[:250] if isinstance(data, dict) else []
                except json.JSONDecodeError as exc:
                    record["parse_status"] = f"json_error:{exc.lineno}:{exc.msg}"
        records.append(record)
    return {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "source_imported_or_executed": False,
        "component_count": len(records),
        "components": records,
        "import_edges": import_edges,
        "warnings": warnings,
    }


def collect_manifests_and_configs(root: Path) -> dict[str, Any]:
    starts = [root / "Config", root / "core", root / "Departments", root / "System"]
    files, warnings = walk_bounded(
        starts, root, max_depth=6, max_items=1000,
        file_filter=lambda p: p.name.casefold() in {"manifest.json", "pyproject.toml", "requirements.txt", "model_sources.json"}
        or p.name.casefold().startswith("requirements"), max_scanned=20000,
    )
    records: list[dict[str, Any]] = []
    for path in sorted(set(files), key=lambda p: str(p).casefold()):
        record = entry_meta(path, root)
        text, error = read_text_bounded(path)
        if error or text is None:
            record["parse_status"] = error
        elif path.suffix.lower() == ".json":
            try:
                data = json.loads(text)
                record["parse_status"] = "json_parsed"
                record["top_level_keys"] = sorted(data.keys(), key=str.casefold)[:250] if isinstance(data, dict) else []
            except json.JSONDecodeError as exc:
                record["parse_status"] = f"json_error:{exc.lineno}:{exc.msg}"
        else:
            record["parse_status"] = "text_read"
            record["line_count"] = len(text.splitlines())
        if isinstance(record.get("size_bytes"), int) and record["size_bytes"] <= MAX_HASH_BYTES:
            record["sha256"] = hash_small(path).get("sha256")
        records.append(record)
    return {"schema": SCHEMA, "mission_id": MISSION_ID, "files": records, "warnings": warnings}


def collect_models_databases_and_storage(root: Path) -> dict[str, Any]:
    candidate_roots: list[Path] = []
    top, warnings = walk_bounded(
        [root], root, max_depth=4, max_items=400,
        dir_filter=lambda p: any(term in p.name.casefold() for term in ("model", "checkpoint", "database", "index", "output", "save", "archive", "backup", "snapshot", "receipt", "writing", "poem")),
        file_filter=lambda p: False, max_scanned=30000,
    )
    candidate_roots.extend(top)
    files: list[Path] = []
    for candidate in sorted(set(candidate_roots), key=lambda p: str(p).casefold())[:80]:
        found, more = walk_bounded(
            [candidate], root, max_depth=4, max_items=1000,
            file_filter=lambda p: p.suffix.lower() in MODEL_SUFFIXES | DATABASE_SUFFIXES, max_scanned=5000,
        )
        files.extend(found)
        warnings.extend(more)
        if len(files) >= 2000:
            warnings.append("model_database_limit_reached:2000")
            files = files[:2000]
            break
    model_records = [entry_meta(p, root) for p in sorted({str(p): p for p in files if p.suffix.lower() in MODEL_SUFFIXES}.values(), key=lambda p: str(p).casefold())]
    database_records = [entry_meta(p, root) for p in sorted({str(p): p for p in files if p.suffix.lower() in DATABASE_SUFFIXES}.values(), key=lambda p: str(p).casefold())]
    storage_roots = [entry_meta(p, root) for p in sorted(set(candidate_roots), key=lambda p: str(p).casefold())[:400]]
    return {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "models_loaded": False,
        "large_files_hashed": False,
        "model_files": model_records,
        "database_and_index_files": database_records,
        "classified_storage_roots": storage_roots,
        "warnings": warnings,
    }


def collect_mission_evidence(root: Path) -> dict[str, Any]:
    engineering = root / "System" / "EngineeringWorkshop"
    starts = [engineering / "receipts", engineering / "missions", root / "Reports"]
    files, warnings = walk_bounded(
        starts, root, max_depth=4, max_items=600,
        file_filter=lambda p: p.suffix.lower() in {".json", ".md", ".txt"}
        and any(term in p.name.casefold() for term in ("receipt", "mission", "report", "result", "summary")), max_scanned=20000,
    )
    files = sorted(set(files), key=safe_mtime_ns, reverse=True)[:300]
    records: list[dict[str, Any]] = []
    for path in files:
        record = entry_meta(path, root)
        if path.suffix.lower() == ".json":
            text, error = read_text_bounded(path, 1024 * 1024)
            if error or text is None:
                record["parse_status"] = error
            else:
                try:
                    data = json.loads(text)
                    record["parse_status"] = "json_parsed"
                    if isinstance(data, dict):
                        for key in ("mission_id", "title", "result", "state", "route", "network_used", "rollback", "rollback_used", "live_system_modified"):
                            if key in data:
                                record[key] = data[key]
                except json.JSONDecodeError as exc:
                    record["parse_status"] = f"json_error:{exc.lineno}:{exc.msg}"
        else:
            record["parse_status"] = "metadata_only"
        records.append(record)
    return {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "original_receipts_modified": False,
        "similarity_is_not_proof": True,
        "record_count": len(records),
        "records": records,
        "warnings": warnings,
    }


def protected_snapshot(root: Path) -> list[dict[str, Any]]:
    return [hash_small(root / Path(rel)) for rel in PROTECTED_CANDIDATES]


def compare_snapshots(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    b = {item["path"]: item for item in before}
    a = {item["path"]: item for item in after}
    changes = []
    for path in sorted(set(b) | set(a), key=str.casefold):
        left = b.get(path)
        right = a.get(path)
        keys = ("exists", "size_bytes", "modified_ns", "sha256", "error")
        if any((left or {}).get(k) != (right or {}).get(k) for k in keys):
            changes.append({"path": path, "before": left, "after": right})
    return {"unchanged": not changes, "changes": changes}


def output_size(output_root: Path) -> int:
    total = 0
    if output_root.exists():
        for current, dirs, files in os.walk(output_root):
            dirs[:] = [d for d in dirs if d.casefold() not in EXCLUDED_DIR_NAMES]
            for name in files:
                try:
                    total += (Path(current) / name).stat().st_size
                except OSError:
                    pass
    return total


def write_json(output_root: Path, name: str, data: Any) -> dict[str, Any]:
    path = output_root / name
    if not within(path, output_root):
        raise RuntimeError(f"write_outside_output_root:{path}")
    encoded = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if output_size(output_root) + len(encoded) > MAX_OUTPUT_BYTES:
        raise RuntimeError("output_ceiling_exceeded")
    path.write_bytes(encoded)
    return {"path": norm(path), "size_bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def write_text(output_root: Path, name: str, text: str) -> dict[str, Any]:
    path = output_root / name
    if not within(path, output_root):
        raise RuntimeError(f"write_outside_output_root:{path}")
    encoded = text.encode("utf-8")
    if output_size(output_root) + len(encoded) > MAX_OUTPUT_BYTES:
        raise RuntimeError("output_ceiling_exceeded")
    path.write_bytes(encoded)
    return {"path": norm(path), "size_bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def load_repository_reference(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "not_supplied"}
    text, error = read_text_bounded(path, 1024 * 1024)
    if error or text is None:
        return {"status": "unreadable", "path": norm(path), "error": error}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"status": "invalid_json", "path": norm(path), "error": f"{exc.lineno}:{exc.msg}"}
    return {"status": "loaded", "path": norm(path), "sha256": hash_small(path).get("sha256"), "data": data}


def build_summary(
    root: Path, top: list[dict[str, Any]], launchers: dict[str, Any], runtimes: dict[str, Any],
    reusable: dict[str, Any], configs: dict[str, Any], storage: dict[str, Any], missions: dict[str, Any],
    protected: dict[str, Any], warnings: list[str]
) -> str:
    return "\n".join([
        "# Agent Fox Technical Core V1A-0 R2 Static Baseline",
        "",
        f"- Mission: `{MISSION_ID}`",
        f"- Project root: `{norm(root)}`",
        "- Mode: bounded static inspection only",
        "- Network used: No",
        "- Packages installed: No",
        "- FOXAI launchers executed: No",
        "- FOXAI source imported or executed: No",
        "- Additional Python interpreters launched by collector: No",
        f"- Top-level entries: {len(top)}",
        f"- Launchers statically inventoried: {launchers.get('launcher_count', 0)}",
        f"- Python executable files statically found: {runtimes.get('runtime_count', 0)}",
        f"- Package metadata records: {runtimes.get('package_metadata_count', 0)}",
        f"- Reusable components indexed: {reusable.get('component_count', 0)}",
        f"- Manifest/config files indexed: {len(configs.get('files', []))}",
        f"- Model files inventoried without loading: {len(storage.get('model_files', []))}",
        f"- Database/index files inventoried: {len(storage.get('database_and_index_files', []))}",
        f"- Historical mission evidence records: {missions.get('record_count', 0)}",
        f"- Protected candidates unchanged: {protected.get('unchanged')}",
        f"- Collector warnings: {len(warnings)}",
        "",
        "## Deliberately deferred",
        "",
        "Exact interpreter versions, sys.path, environment differences, active process ownership, Windows processes/services/tasks/ports/event logs, and digital signatures are not probed in R2. They require later bounded missions after this static baseline is reviewed.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded static FOXAI baseline collector")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--mission-id", default=MISSION_ID)
    parser.add_argument("--output-relative", default=str(DEFAULT_OUTPUT_RELATIVE))
    parser.add_argument("--repository-reference")
    args = parser.parse_args()

    if args.mission_id != MISSION_ID:
        raise SystemExit("mission_id_mismatch")
    root = Path(args.root).resolve(strict=False)
    if not root.is_dir():
        raise SystemExit(f"project_root_not_found:{root}")
    output_root = (root / Path(args.output_relative)).resolve(strict=False)
    engineering_missions = (root / "System" / "EngineeringWorkshop" / "missions").resolve(strict=False)
    if not within(output_root, engineering_missions):
        raise SystemExit(f"output_not_in_engineering_missions:{output_root}")
    if output_root.exists():
        raise SystemExit(f"output_root_must_not_exist:{output_root}")
    output_root.mkdir(parents=True, exist_ok=False)

    started = utc_now()
    protected_before = protected_snapshot(root)
    top, top_warnings = top_level_inventory(root)
    launchers = collect_launchers(root)
    runtimes = collect_static_python_runtimes(root, launchers)
    reusable = collect_reusable_components(root)
    configs = collect_manifests_and_configs(root)
    storage = collect_models_databases_and_storage(root)
    missions = collect_mission_evidence(root)
    repository = load_repository_reference(Path(args.repository_reference).resolve(strict=False) if args.repository_reference else None)
    protected_after = protected_snapshot(root)
    protected = compare_snapshots(protected_before, protected_after)

    warnings = []
    warnings.extend(top_warnings)
    for section in (launchers, runtimes, reusable, configs, storage, missions):
        warnings.extend(section.get("warnings", []))

    manifest = {
        "schema": SCHEMA,
        "mission_id": MISSION_ID,
        "generated_at": utc_now(),
        "project_root": norm(root),
        "evidence_class": "observed_live_metadata_and_static_live_source",
        "top_level_inventory": top,
        "repository_reference": repository,
        "protected_candidates": protected_after,
        "protected_candidates_unchanged": protected,
        "capabilities": {
            "can_inventory_paths_and_metadata": True,
            "can_statically_trace_launcher_text": True,
            "can_parse_selected_python_source_without_importing": True,
            "can_read_static_dist_info_metadata": True,
            "can_execute_foxai_source": False,
            "can_apply_repairs": False,
        },
        "safety": {
            "network_used": False,
            "packages_installed": False,
            "elevation_requested": False,
            "foxai_source_imported_or_executed": False,
            "foxai_launchers_executed": False,
            "additional_python_interpreters_launched_by_collector": False,
            "models_loaded": False,
            "services_or_processes_changed": False,
            "existing_files_deleted_or_renamed": False,
            "existing_foxai_source_files_modified": False,
            "mission_workspace_written": True,
            "output_root": norm(output_root),
            "output_ceiling_bytes": MAX_OUTPUT_BYTES,
        },
        "missing_evidence": [
            "Exact runtime versions, sys.path, prefixes and host-versus-portable behavior were deliberately not executed in R2.",
            "Windows live processes, services, startup, tasks, ports, event failures and signatures were deliberately deferred.",
            "A static launcher reference is not proof that the referenced component is currently active.",
            "Repository evidence is reference evidence and is not treated as proof of the live installation.",
        ],
    }

    outputs = []
    outputs.append(write_json(output_root, "LIVE_STATIC_MANIFEST.json", manifest))
    outputs.append(write_json(output_root, "LAUNCHER_TRACE_CANDIDATES.json", launchers))
    outputs.append(write_json(output_root, "PYTHON_RUNTIME_STATIC_MAP.json", runtimes))
    outputs.append(write_json(output_root, "REUSABLE_COMPONENTS_MAP.json", reusable))
    outputs.append(write_json(output_root, "MANIFEST_AND_CONFIG_MAP.json", configs))
    outputs.append(write_json(output_root, "MODEL_DATABASE_AND_STORAGE_MAP.json", storage))
    outputs.append(write_json(output_root, "MISSION_EVIDENCE_INDEX.json", missions))
    outputs.append(write_json(output_root, "GAPS_AND_WARNINGS.json", {
        "schema": SCHEMA, "mission_id": MISSION_ID,
        "warnings": warnings, "missing_evidence": manifest["missing_evidence"]
    }))
    outputs.append(write_text(output_root, "SUMMARY.md", build_summary(
        root, top, launchers, runtimes, reusable, configs, storage, missions, protected, warnings
    )))

    if not protected.get("unchanged"):
        raise SystemExit("protected_candidate_changed_during_static_audit")

    required_names = {
        "LIVE_STATIC_MANIFEST.json", "LAUNCHER_TRACE_CANDIDATES.json",
        "PYTHON_RUNTIME_STATIC_MAP.json", "REUSABLE_COMPONENTS_MAP.json",
        "MANIFEST_AND_CONFIG_MAP.json", "MODEL_DATABASE_AND_STORAGE_MAP.json",
        "MISSION_EVIDENCE_INDEX.json", "GAPS_AND_WARNINGS.json", "SUMMARY.md",
    }
    actual_names = {p.name for p in output_root.iterdir() if p.is_file()}
    if not required_names.issubset(actual_names):
        raise SystemExit(f"missing_outputs:{sorted(required_names - actual_names)}")

    receipt = {
        "schema": "foxai.agent_fox.technical_core.v1a0.r2.audit_receipt.v1",
        "mission_id": MISSION_ID,
        "result": "static_baseline_complete",
        "started_at": started,
        "finished_at": utc_now(),
        "project_root": norm(root),
        "output_root": norm(output_root),
        "outputs": outputs,
        "output_total_bytes_before_receipt": output_size(output_root),
        "network_used": False,
        "packages_installed": False,
        "live_foxai_source_modified": False,
        "mission_workspace_written": True,
        "foxai_source_or_launchers_executed": False,
        "additional_python_interpreters_launched_by_collector": False,
        "models_loaded": False,
        "protected_candidates_unchanged": True,
        "warnings_count": len(warnings),
        "authoritative_status": "Implementation receipt remains authoritative after Workshop completion.",
    }
    receipt_meta = write_json(output_root, "AUDIT_RECEIPT.json", receipt)
    final_size = output_size(output_root)
    if final_size > MAX_OUTPUT_BYTES:
        raise SystemExit(f"output_ceiling_exceeded:{final_size}")

    # Self-verify the receipt and central safety flags before successful exit.
    loaded = json.loads((output_root / "AUDIT_RECEIPT.json").read_text(encoding="utf-8"))
    if loaded.get("result") != "static_baseline_complete":
        raise SystemExit("receipt_result_invalid")
    if loaded.get("network_used") is not False or loaded.get("live_foxai_source_modified") is not False:
        raise SystemExit("receipt_safety_invalid")
    print(json.dumps({
        "result": "static_baseline_complete",
        "mission_id": MISSION_ID,
        "output_root": norm(output_root),
        "output_total_bytes": final_size,
        "audit_receipt": receipt_meta,
        "network_used": False,
        "live_foxai_source_modified": False,
        "additional_python_interpreters_launched_by_collector": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
