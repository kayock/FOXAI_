from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

BRIDGE_SCHEMA = "foxai.agent_fox.technical_core.v1a2.static_bridge.v1"
CONTRACT_SCHEMA = "foxai.agent_fox.technical_core.v1a2.static_bridge_contract.v1"
DEFAULT_PROJECT_ROOT = Path(r"Z:\FOXAI")
DEFAULT_NORMALIZED_DIR = Path(
    r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-051832-1CAA3F_V1A1_NORMALIZED"
)
DEFAULT_OUTPUT_DIR = Path(
    r"Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-053749-E3BE2A_V1A2_STATIC_BRIDGE"
)
DEFAULT_MISSION_ID = "ENG-20260721-053749-E3BE2A"

MAX_SOURCE_FILES = 8000
MAX_LAUNCHER_FILES = 1200
MAX_SOURCE_FILE_BYTES = 4 * 1024 * 1024
MAX_LAUNCHER_FILE_BYTES = 1024 * 1024
MAX_TOTAL_SOURCE_READ_BYTES = 128 * 1024 * 1024
MAX_LINE_RECORDS = 60000
MAX_LINE_LENGTH = 480
MAX_OCCURRENCES_PER_KEY = 300
MAX_QUERY_RESULTS = 100
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_TRACE_DEPTH = 12

SOURCE_SUFFIXES = {
    ".py", ".pyw", ".bat", ".cmd", ".ps1", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".html", ".htm", ".js", ".mjs", ".cjs",
    ".ts", ".tsx", ".css",
}
PYTHON_SUFFIXES = {".py", ".pyw"}
LAUNCHER_SUFFIXES = {".bat", ".cmd", ".ps1"}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}

FIRST_PARTY_ROOTS = (
    "Academy", "agents", "AI", "Architecture", "assets", "Bridge", "BridgeUI",
    "Capabilities", "Config", "core", "CreativeStudio", "Data", "Departments",
    "Engine", "Extensions", "Forge", "Foundry", "Interface", "Knowledge", "Memory",
    "Modules", "NovelForge", "OpsBridge", "Plugins", "RepairBay", "Shell", "System",
    "The_Forge", "tools", "ui", "Vault",
)

EXCLUDED_DIR_NAMES = {
    ".git", ".venv", "venv", "env", "__pycache__", "site-packages", "node_modules",
    "models", "wheelhouse", "downloads", "_downloads", "logs", "reports", "outputs",
    "output", "archive", "archives", "backups", "backup", "snapshots", "receipts",
    "previews", "missions", "baseline", "baselines", "dist", "build", "packages",
    "package", "library", "writing", "my writing", "my poems", "legacy work",
}

SECRET_NAME_RE = re.compile(
    r"(?:api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)
SECRET_LINE_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|client[_-]?secret)"
    r"\s*[:=]\s*([^\s,;\]\}\)]+|[\"'][^\"']*[\"'])"
)
ENV_REF_RE = re.compile(r"%(?:~[A-Za-z0-9]+|[^%]+)%")
PORT_RE = re.compile(r"(?i)(?:--port(?:=|\s+)|\bport\s*[:=]\s*|127\.0\.0\.1:|localhost:)(\d{2,5})")
WINDOWS_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:\\[^\r\n\"<>|?*]+|(?:\.\.?\\|[^\s\"']+\\)[^\r\n\"<>|?*]+)"
)
QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
BATCH_SET_RE = re.compile(r"(?i)^\s*set\s+(?:\"([^=\"]+)=([^\"]*)\"|([^=\s]+)=(.*))\s*$")
BATCH_CALL_RE = re.compile(r"(?i)^\s*call\s+(.+?)\s*$")
BATCH_START_RE = re.compile(r"(?i)^\s*start(?:\s+\"[^\"]*\")?\s+(.+?)\s*$")
BATCH_CD_RE = re.compile(r"(?i)^\s*(?:cd|chdir|pushd)\s+(?:/d\s+)?(.+?)\s*$")
BATCH_GOTO_RE = re.compile(r"(?i)^\s*goto\s+([^\s&|]+)")
BATCH_LABEL_RE = re.compile(r"^\s*:([^:\s]+)\s*$")
PYTHON_COMMAND_RE = re.compile(r"(?i)(%[A-Za-z0-9_]*(?:python|py)[A-Za-z0-9_]*%|[^\s\"']*pythonw?\.exe|\bpy(?:\.exe)?\b|\bpythonw?\b)")
SCRIPT_REF_RE = re.compile(r"(?i)([^\s\"']+\.(?:py|pyw|bat|cmd|ps1))\b")
PACKAGE_DIR_RE = re.compile(
    r"(?i)(?:^|_)(?:apply|preflight|integration|hotfix|patch|install|package|build|preview|seal|"
    r"closure|enablement|activation|migration|repair|fix)(?:_|$)"
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, max_bytes: int | None = None) -> str:
    size = path.stat().st_size
    if max_bytes is not None and size > max_bytes:
        raise ValueError(f"hash_input_over_limit:{path}:{size}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_bounded(path: Path, max_bytes: int) -> tuple[str, str, int]:
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"file_over_limit:{path}:{size}")
    raw = path.read_bytes()
    attempts = ("utf-8-sig", "utf-8", "cp1252")
    for encoding in attempts:
        try:
            return raw.decode(encoding), encoding, len(raw)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replacement", len(raw)


def norm_win(value: str | Path | None) -> str:
    if value is None:
        return ""
    return str(value).replace("/", "\\").strip()


def rel_win(path: Path, root: Path) -> str:
    try:
        return norm_win(path.resolve(strict=False).relative_to(root.resolve(strict=False)))
    except (ValueError, OSError):
        return norm_win(path)


def redacted_text(text: str) -> str:
    return SECRET_LINE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)


def safe_literal(value: Any, name: str = "") -> Any:
    if SECRET_NAME_RE.search(name):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redacted_text(value[:300])
    if isinstance(value, (list, tuple)) and len(value) <= 20:
        return [safe_literal(item, name) for item in value]
    if isinstance(value, dict) and len(value) <= 20:
        return {str(key): safe_literal(item, str(key)) for key, item in value.items()}
    return "[COMPLEX_OR_TRUNCATED]"


def classify_path(relative_path: str) -> dict[str, Any]:
    normalized = norm_win(relative_path).lstrip("\\")
    parts = [part for part in PureWindowsPath(normalized).parts if part not in {"\\", "/"}]
    lower = [part.casefold() for part in parts]
    suffix = PureWindowsPath(normalized).suffix.casefold()
    categories: list[str] = []
    historical = False
    if any(part in {"archive", "archives"} for part in lower):
        categories.append("archive")
        historical = True
    if any(part in {"backup", "backups"} for part in lower):
        categories.append("backup")
        historical = True
    if any(part in {"snapshot", "snapshots", "baseline", "baselines"} for part in lower):
        categories.append("snapshot")
        historical = True
    if any(part in {"receipt", "receipts"} for part in lower):
        categories.append("receipt")
        historical = True
    if any(part in {"missions", "previews"} for part in lower):
        categories.append("mission_workspace")
        historical = True
    if lower and (PACKAGE_DIR_RE.search(lower[0]) or lower[0].startswith("agent_fox_v1a")):
        categories.append("package")
        historical = True
    if suffix in LAUNCHER_SUFFIXES:
        categories.append("launcher")
    if any(part in {"runtime", ".venv", "venv", "env", "site-packages"} for part in lower):
        categories.append("runtime")
    if any("output" in part or part in {"reports", "logs", "generated"} for part in lower):
        categories.append("generated_output")
    if any(part in {"writing", "my writing", "my poems", "legacy work", "personal"} for part in lower):
        categories.append("personal_content")
    if not historical:
        categories.append("live_candidate")
    unique: list[str] = []
    for category in categories:
        if category not in unique:
            unique.append(category)
    return {
        "categories": unique,
        "historical_or_derived_location": historical,
        "primary_category": unique[0] if unique else "live_candidate",
    }


def language_for_suffix(suffix: str) -> str:
    return {
        ".py": "python", ".pyw": "python", ".bat": "batch", ".cmd": "batch",
        ".ps1": "powershell", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml", ".ini": "ini", ".cfg": "config", ".html": "html",
        ".htm": "html", ".js": "javascript", ".mjs": "javascript",
        ".cjs": "javascript", ".ts": "typescript", ".tsx": "typescript",
        ".css": "css",
    }.get(suffix.casefold(), "text")


def is_excluded_dir(path: Path, project_root: Path) -> bool:
    relative = rel_win(path, project_root)
    parts = [part.casefold() for part in PureWindowsPath(relative).parts]
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    if parts and PACKAGE_DIR_RE.search(parts[0]):
        return True
    if parts and parts[0].startswith("agent_fox_v1a"):
        return True
    if len(parts) >= 2 and parts[0] == "system" and parts[1] == "engineeringworkshop":
        return True
    return False


def discover_source_files(project_root: Path) -> tuple[list[Path], dict[str, Any]]:
    candidates: dict[str, Path] = {}
    skipped = Counter()
    examined_entries = 0

    for child in sorted(project_root.iterdir(), key=lambda item: item.name.casefold()):
        examined_entries += 1
        if child.is_symlink():
            skipped["symlink"] += 1
            continue
        if child.is_file() and child.suffix.casefold() in SOURCE_SUFFIXES:
            candidates[rel_win(child, project_root).casefold()] = child

    for root_name in FIRST_PARTY_ROOTS:
        source_root = project_root / root_name
        if not source_root.is_dir() or source_root.is_symlink():
            continue
        stack = [source_root]
        while stack and len(candidates) < MAX_SOURCE_FILES:
            current = stack.pop()
            try:
                children = sorted(current.iterdir(), key=lambda item: item.name.casefold(), reverse=True)
            except (PermissionError, OSError):
                skipped["directory_read_error"] += 1
                continue
            for child in children:
                examined_entries += 1
                if child.is_symlink():
                    skipped["symlink"] += 1
                    continue
                if child.is_dir():
                    if is_excluded_dir(child, project_root):
                        skipped["excluded_directory"] += 1
                    else:
                        stack.append(child)
                elif child.is_file() and child.suffix.casefold() in SOURCE_SUFFIXES:
                    key = rel_win(child, project_root).casefold()
                    candidates.setdefault(key, child)
                    if len(candidates) >= MAX_SOURCE_FILES:
                        break

    ordered = [candidates[key] for key in sorted(candidates)]
    return ordered, {
        "candidate_count": len(ordered),
        "examined_entries": examined_entries,
        "source_file_cap_reached": len(ordered) >= MAX_SOURCE_FILES,
        "skipped": dict(sorted(skipped.items())),
        "allowlisted_roots": list(FIRST_PARTY_ROOTS),
    }


class PythonCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[str] = []
        self.symbols: list[dict[str, Any]] = []
        self.imports: list[dict[str, Any]] = []
        self.settings: list[dict[str, Any]] = []
        self.references: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    def _qualname(self, name: str) -> str:
        return ".".join([*self.scope, name]) if self.scope else name

    def _record_symbol(self, node: ast.AST, name: str, kind: str) -> None:
        record = {
            "name": name,
            "qualname": self._qualname(name),
            "kind": kind,
            "line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", getattr(node, "lineno", None)),
        }
        self.symbols.append(record)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_symbol(node, node.name, "function" if not self.scope else "method_or_nested_function")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_symbol(node, node.name, "async_function" if not self.scope else "async_method_or_nested_function")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._record_symbol(node, node.name, "class")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.imports.append({
                "kind": "import",
                "module": alias.name,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            self.imports.append({
                "kind": "from_import",
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def _record_assignment(self, target: ast.AST, value: ast.AST, line: int) -> None:
        names: list[str] = []
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Attribute):
            names.append(target.attr)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                if isinstance(item, ast.Name):
                    names.append(item.id)
        literal: Any = "[NON_LITERAL]"
        try:
            literal = safe_literal(ast.literal_eval(value), names[0] if names else "")
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            pass
        for name in names:
            self.settings.append({
                "name": name,
                "qualname": self._qualname(name),
                "line": line,
                "value": "[REDACTED]" if SECRET_NAME_RE.search(name) else literal,
            })

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._record_assignment(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if node.value is not None:
            self._record_assignment(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if len(self.references[node.id.casefold()]) < MAX_OCCURRENCES_PER_KEY:
            self.references[node.id.casefold()].append({"name": node.id, "line": node.lineno, "kind": "name"})
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if len(self.references[node.attr.casefold()]) < MAX_OCCURRENCES_PER_KEY:
            self.references[node.attr.casefold()].append({"name": node.attr, "line": node.lineno, "kind": "attribute"})
        self.generic_visit(node)


def flatten_json_keys(value: Any, prefix: str = "", depth: int = 0) -> list[dict[str, Any]]:
    if depth > 10:
        return []
    records: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key in sorted(value, key=lambda item: str(item).casefold()):
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            item = value[key]
            records.append({
                "name": name,
                "qualname": path,
                "line": None,
                "value": safe_literal(item, name) if not isinstance(item, (dict, list)) else "[CONTAINER]",
            })
            records.extend(flatten_json_keys(item, path, depth + 1))
    elif isinstance(value, list):
        for index, item in enumerate(value[:100]):
            path = f"{prefix}[{index}]"
            records.extend(flatten_json_keys(item, path, depth + 1))
    return records


def interesting_line_records(text: str, relative_path: str, language: str, global_state: dict[str, int]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if global_state["line_records"] >= MAX_LINE_RECORDS:
            break
        stripped = raw_line.strip()
        if not stripped:
            continue
        if language == "python" and stripped.startswith("#"):
            continue
        if language in {"batch", "powershell"} and stripped.lower().startswith(("rem ", "::")):
            continue
        if language in {"json", "yaml", "toml", "ini", "config"}:
            include = any(marker in stripped for marker in (":", "=", "-"))
        else:
            include = bool(IDENTIFIER_RE.search(stripped))
        if not include:
            continue
        records.append({
            "path": relative_path,
            "line": line_no,
            "language": language,
            "text": redacted_text(stripped[:MAX_LINE_LENGTH]),
        })
        global_state["line_records"] += 1
    return records


def parse_source_file(path: Path, project_root: Path, global_state: dict[str, int]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    relative = rel_win(path, project_root)
    suffix = path.suffix.casefold()
    language = language_for_suffix(suffix)
    stat = path.stat()
    base = {
        "path": norm_win(path),
        "relative_path": relative,
        "suffix": suffix,
        "language": language,
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "path_classification": classify_path(relative),
        "source_imported_or_executed": False,
    }
    if stat.st_size > MAX_SOURCE_FILE_BYTES:
        base.update({"parse_status": "skipped_file_over_limit", "sha256": None, "line_count": None, "symbols": [], "imports": [], "settings": []})
        return base, [], {}
    text, encoding, byte_count = read_text_bounded(path, MAX_SOURCE_FILE_BYTES)
    global_state["bytes_read"] += byte_count
    base.update({
        "sha256": sha256_bytes(text.encode("utf-8")),
        "source_bytes_sha256": sha256_file(path, MAX_SOURCE_FILE_BYTES),
        "encoding": encoding,
        "line_count": len(text.splitlines()),
    })
    line_records = interesting_line_records(text, relative, language, global_state)
    references: dict[str, list[dict[str, Any]]] = {}

    if suffix in PYTHON_SUFFIXES:
        try:
            tree = ast.parse(text, filename=relative)
            collector = PythonCollector()
            collector.visit(tree)
            base.update({
                "parse_status": "python_ast_parsed",
                "symbols": sorted(collector.symbols, key=lambda item: ((item.get("line") or 0), item["qualname"].casefold())),
                "imports": sorted(collector.imports, key=lambda item: ((item.get("line") or 0), item["module"].casefold(), item["name"].casefold())),
                "settings": sorted(collector.settings, key=lambda item: ((item.get("line") or 0), item["qualname"].casefold())),
                "syntax_error": None,
            })
            references = dict(collector.references)
        except SyntaxError as exc:
            base.update({
                "parse_status": "python_syntax_error",
                "symbols": [],
                "imports": [],
                "settings": [],
                "syntax_error": {"line": exc.lineno, "offset": exc.offset, "message": exc.msg},
            })
    elif suffix == ".json":
        try:
            value = json.loads(text)
            settings = flatten_json_keys(value)
            base.update({"parse_status": "json_parsed", "symbols": [], "imports": [], "settings": settings, "syntax_error": None})
        except json.JSONDecodeError as exc:
            base.update({
                "parse_status": "json_syntax_error", "symbols": [], "imports": [], "settings": [],
                "syntax_error": {"line": exc.lineno, "column": exc.colno, "message": exc.msg},
            })
    else:
        imports: list[dict[str, Any]] = []
        settings: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if language in {"javascript", "typescript"}:
                match = re.search(r"(?i)\b(?:import\s+.*?\s+from\s+|require\s*\()\s*[\"']([^\"']+)", stripped)
                if match:
                    imports.append({"kind": "static_text_import", "module": match.group(1), "name": match.group(1), "alias": None, "line": line_no})
            if language in {"yaml", "toml", "ini", "config"}:
                match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*[:=]\s*(.*)$", line)
                if match:
                    name, raw_value = match.groups()
                    settings.append({
                        "name": name,
                        "qualname": name,
                        "line": line_no,
                        "value": "[REDACTED]" if SECRET_NAME_RE.search(name) else redacted_text(raw_value[:300]),
                    })
        base.update({"parse_status": "static_text_parsed", "symbols": [], "imports": imports, "settings": settings, "syntax_error": None})
    return base, line_records, references


def expand_batch_value(value: str, variables: dict[str, str], launcher_dir: str) -> tuple[str, list[str]]:
    expanded = value.strip().strip('"')
    expanded = re.sub(r"(?i)%~dp0", lambda _match: launcher_dir.rstrip("\\") + "\\", expanded)
    unresolved: list[str] = []
    for _ in range(8):
        changed = False
        for match in list(ENV_REF_RE.finditer(expanded)):
            token = match.group(0)
            key = token[1:-1].casefold()
            if key in variables:
                expanded = expanded.replace(token, variables[key])
                changed = True
            elif token not in unresolved:
                unresolved.append(token)
        if not changed:
            break
    return norm_win(expanded), sorted(unresolved, key=str.casefold)


def target_from_command(command: str) -> str | None:
    value = command.strip()
    if not value:
        return None
    quoted = QUOTED_RE.match(value)
    if quoted:
        return quoted.group(1) or quoted.group(2)
    token = value.split()[0]
    return token.strip('"\'') if token else None


def resolve_launcher_target(raw_target: str, launcher_path: Path, project_root: Path, variables: dict[str, str]) -> dict[str, Any]:
    launcher_dir = norm_win(launcher_path.parent)
    expanded, unresolved = expand_batch_value(raw_target, variables, launcher_dir)
    candidate_text = expanded.strip().strip('"\'')
    if not candidate_text:
        return {"raw_target": raw_target, "expanded_target": expanded, "resolved_path": None, "exists": False, "unresolved_variables": unresolved, "confirmation": "unresolved"}
    pure = PureWindowsPath(candidate_text)
    if pure.is_absolute():
        candidate = Path(candidate_text)
    else:
        candidate = launcher_path.parent / candidate_text
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(project_root.resolve(strict=False))
        within_root = True
    except (ValueError, OSError):
        within_root = False
    exists = resolved.is_file() and not resolved.is_symlink()
    confirmation = "static_existing_target" if exists and not unresolved else "unresolved_or_unverified_target"
    return {
        "raw_target": raw_target,
        "expanded_target": expanded,
        "resolved_path": norm_win(resolved),
        "relative_path": rel_win(resolved, project_root) if within_root else None,
        "within_project_root": within_root,
        "exists": exists,
        "unresolved_variables": unresolved,
        "confirmation": confirmation,
    }


def parse_launcher(path: Path, project_root: Path, source_classification: dict[str, Any]) -> dict[str, Any]:
    relative = rel_win(path, project_root)
    stat = path.stat()
    base = {
        "path": norm_win(path),
        "relative_path": relative,
        "suffix": path.suffix.casefold(),
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "path_classification": source_classification,
        "launcher_executed": False,
    }
    if stat.st_size > MAX_LAUNCHER_FILE_BYTES:
        base.update({"parse_status": "skipped_file_over_limit", "sha256": None, "edges": [], "settings": [], "labels": [], "gotos": [], "ports": [], "environment_references": []})
        return base
    text, encoding, _ = read_text_bounded(path, MAX_LAUNCHER_FILE_BYTES)
    variables: dict[str, str] = {}
    settings: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    gotos: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    working_directories: list[dict[str, Any]] = []
    ports: set[int] = set()
    environment_references: set[str] = set()
    python_references: list[dict[str, Any]] = []

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.lower().startswith(("rem ", "::", "@rem ")):
            continue
        for token in ENV_REF_RE.findall(stripped):
            environment_references.add(token)
        for port_text in PORT_RE.findall(stripped):
            port = int(port_text)
            if 1 <= port <= 65535:
                ports.add(port)
        label_match = BATCH_LABEL_RE.match(stripped)
        if label_match:
            labels.append({"name": label_match.group(1), "line": line_no})
            continue
        set_match = BATCH_SET_RE.match(stripped)
        if set_match:
            name = (set_match.group(1) or set_match.group(3) or "").strip()
            value = (set_match.group(2) if set_match.group(1) is not None else set_match.group(4) or "").strip()
            expanded, unresolved = expand_batch_value(value, variables, norm_win(path.parent))
            variables[name.casefold()] = expanded
            settings.append({
                "name": name,
                "line": line_no,
                "value": "[REDACTED]" if SECRET_NAME_RE.search(name) else redacted_text(expanded[:500]),
                "unresolved_variables": unresolved,
            })
            continue
        goto_match = BATCH_GOTO_RE.match(stripped)
        if goto_match:
            gotos.append({"target_label": goto_match.group(1), "line": line_no})
        cd_match = BATCH_CD_RE.match(stripped)
        if cd_match:
            expanded, unresolved = expand_batch_value(cd_match.group(1), variables, norm_win(path.parent))
            working_directories.append({"raw": cd_match.group(1), "expanded": expanded, "line": line_no, "unresolved_variables": unresolved})
        command_kind = None
        command_text = None
        call_match = BATCH_CALL_RE.match(stripped)
        start_match = BATCH_START_RE.match(stripped)
        if call_match:
            command_kind, command_text = "call", call_match.group(1)
        elif start_match:
            command_kind, command_text = "start", start_match.group(1)
        elif SCRIPT_REF_RE.search(stripped) or PYTHON_COMMAND_RE.search(stripped):
            command_kind, command_text = "command_reference", stripped.lstrip("@").strip()
        if command_text:
            target = target_from_command(command_text)
            if target:
                resolution = resolve_launcher_target(target, path, project_root, variables)
                resolution.update({"kind": command_kind, "line": line_no, "command": redacted_text(command_text[:1000])})
                if resolution["confirmation"] != "static_existing_target":
                    resolution["confirmed_active_or_executed"] = False
                else:
                    resolution["confirmed_active_or_executed"] = False
                edges.append(resolution)
        python_match = PYTHON_COMMAND_RE.search(stripped)
        if python_match:
            raw_python = python_match.group(1)
            resolution = resolve_launcher_target(raw_python, path, project_root, variables)
            python_references.append({"line": line_no, "raw": raw_python, **resolution, "interpreter_executed": False})

    return {
        **base,
        "parse_status": "static_text_parsed",
        "encoding": encoding,
        "sha256": sha256_file(path, MAX_LAUNCHER_FILE_BYTES),
        "line_count": len(text.splitlines()),
        "settings": sorted(settings, key=lambda item: (item["line"], item["name"].casefold())),
        "labels": sorted(labels, key=lambda item: (item["line"], item["name"].casefold())),
        "gotos": sorted(gotos, key=lambda item: (item["line"], item["target_label"].casefold())),
        "working_directories": sorted(working_directories, key=lambda item: item["line"]),
        "edges": sorted(edges, key=lambda item: (item["line"], item.get("kind", ""), item.get("raw_target", "").casefold())),
        "ports": sorted(ports),
        "environment_references": sorted(environment_references, key=str.casefold),
        "python_references": sorted(python_references, key=lambda item: (item["line"], item["raw"].casefold())),
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_v1a1(normalized_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = {
        "NORMALIZED_WHOLE_FOXAI_STATIC_MANIFEST.json",
        "LAUNCHER_CLASSIFICATION_REPORT.json",
        "NORMALIZATION_RECEIPT.json",
    }
    missing = [name for name in sorted(required) if not (normalized_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing_v1a1_inputs:{missing}")
    manifest = load_json(normalized_dir / "NORMALIZED_WHOLE_FOXAI_STATIC_MANIFEST.json")
    launchers = load_json(normalized_dir / "LAUNCHER_CLASSIFICATION_REPORT.json")
    receipt = load_json(normalized_dir / "NORMALIZATION_RECEIPT.json")
    if receipt.get("result") != "normalized_static_manifest_complete":
        raise ValueError("v1a1_not_complete")
    if receipt.get("source_evidence_unchanged") is not True:
        raise ValueError("v1a1_source_evidence_not_verified")
    return manifest, launchers, receipt


def build_known_good_report(manifest: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for item in manifest.get("protected_candidate_verification", {}).get("records", []):
        path = Path(item.get("path", ""))
        expected = item.get("expected_sha256")
        if not path.is_file() or path.is_symlink():
            records.append({
                "path": norm_win(path), "expected_sha256": expected, "actual_sha256": None,
                "status": "missing_or_unreadable", "comparison_is_current_live_metadata": True,
            })
            continue
        actual = sha256_file(path)
        records.append({
            "path": norm_win(path),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "size_bytes": path.stat().st_size,
            "status": "match" if actual == expected else "mismatch",
            "comparison_is_current_live_metadata": True,
        })
    return {
        "schema": BRIDGE_SCHEMA,
        "comparison_rule": "A hash match proves file identity with the recorded known-good candidate, not complete runtime health.",
        "records": sorted(records, key=lambda item: item["path"].casefold()),
        "all_match": bool(records) and all(item["status"] == "match" for item in records),
        "record_count": len(records),
    }


def build_bridge(project_root: Path, normalized_dir: Path, mission_id: str) -> dict[str, Any]:
    manifest, launcher_report, v1a1_receipt = load_v1a1(normalized_dir)
    source_paths, discovery = discover_source_files(project_root)
    global_state = {"bytes_read": 0, "line_records": 0}
    source_records: list[dict[str, Any]] = []
    line_records: list[dict[str, Any]] = []
    symbol_index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    import_index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    setting_index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    reference_index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped = Counter()

    for source_path in source_paths:
        if global_state["bytes_read"] >= MAX_TOTAL_SOURCE_READ_BYTES:
            skipped["total_read_ceiling_reached"] += 1
            break
        try:
            record, file_lines, references = parse_source_file(source_path, project_root, global_state)
        except (PermissionError, OSError, ValueError) as exc:
            relative = rel_win(source_path, project_root)
            source_records.append({
                "path": norm_win(source_path), "relative_path": relative,
                "suffix": source_path.suffix.casefold(), "language": language_for_suffix(source_path.suffix),
                "parse_status": "read_error", "error": f"{type(exc).__name__}:{exc}",
                "source_imported_or_executed": False, "path_classification": classify_path(relative),
                "symbols": [], "imports": [], "settings": [],
            })
            skipped["read_error"] += 1
            continue
        source_records.append(record)
        line_records.extend(file_lines)
        for symbol in record.get("symbols", []):
            key = symbol["name"].casefold()
            if len(symbol_index[key]) < MAX_OCCURRENCES_PER_KEY:
                symbol_index[key].append({"path": record["relative_path"], **symbol})
        for imported in record.get("imports", []):
            key = imported["module"].casefold()
            if len(import_index[key]) < MAX_OCCURRENCES_PER_KEY:
                import_index[key].append({"path": record["relative_path"], **imported})
        for setting in record.get("settings", []):
            key = setting["name"].casefold()
            if len(setting_index[key]) < MAX_OCCURRENCES_PER_KEY:
                setting_index[key].append({"path": record["relative_path"], **setting})
        for key, occurrences in references.items():
            target = reference_index[key]
            for occurrence in occurrences:
                if len(target) >= MAX_OCCURRENCES_PER_KEY:
                    break
                target.append({"path": record["relative_path"], **occurrence})

    v1a1_launcher_by_path = {
        norm_win(item.get("path", "")).casefold(): item
        for item in launcher_report.get("launchers", [])
        if item.get("path")
    }
    launcher_records: list[dict[str, Any]] = []
    launcher_skipped = Counter()
    for item in sorted(launcher_report.get("launchers", []), key=lambda row: norm_win(row.get("path", "")).casefold()):
        if len(launcher_records) >= MAX_LAUNCHER_FILES:
            launcher_skipped["launcher_file_cap_reached"] += 1
            break
        path = Path(item.get("path", ""))
        classification = item.get("path_classification") or classify_path(item.get("relative_path", rel_win(path, project_root)))
        if not path.is_file() or path.is_symlink():
            launcher_records.append({
                "path": norm_win(path), "relative_path": item.get("relative_path") or rel_win(path, project_root),
                "path_classification": classification, "parse_status": "missing_or_unreadable",
                "launcher_executed": False, "edges": [], "settings": [], "labels": [], "gotos": [],
                "ports": [], "environment_references": [], "python_references": [],
            })
            launcher_skipped["missing_or_unreadable"] += 1
            continue
        try:
            launcher_records.append(parse_launcher(path, project_root, classification))
        except (PermissionError, OSError, ValueError) as exc:
            launcher_records.append({
                "path": norm_win(path), "relative_path": item.get("relative_path") or rel_win(path, project_root),
                "path_classification": classification, "parse_status": "read_error",
                "error": f"{type(exc).__name__}:{exc}", "launcher_executed": False,
                "edges": [], "settings": [], "labels": [], "gotos": [], "ports": [],
                "environment_references": [], "python_references": [],
            })
            launcher_skipped["read_error"] += 1

    known_good = build_known_good_report(manifest)

    code_index = {
        "schema": BRIDGE_SCHEMA,
        "mission_id": mission_id,
        "project_root": norm_win(project_root),
        "static_only": True,
        "source_imported_or_executed": False,
        "files": sorted(source_records, key=lambda item: item["relative_path"].casefold()),
        "file_count": len(source_records),
        "symbol_count": sum(len(item.get("symbols", [])) for item in source_records),
        "import_count": sum(len(item.get("imports", [])) for item in source_records),
        "setting_count": sum(len(item.get("settings", [])) for item in source_records),
    }
    launcher_index = {
        "schema": BRIDGE_SCHEMA,
        "mission_id": mission_id,
        "project_root": norm_win(project_root),
        "static_only": True,
        "launchers_executed": False,
        "source_launcher_record_count": launcher_report.get("source_launcher_count"),
        "records": sorted(launcher_records, key=lambda item: item["relative_path"].casefold()),
        "record_count": len(launcher_records),
        "edge_count": sum(len(item.get("edges", [])) for item in launcher_records),
        "confirmed_active_or_executed_targets": 0,
    }
    references = {
        "schema": BRIDGE_SCHEMA,
        "mission_id": mission_id,
        "line_records": line_records,
        "line_record_count": len(line_records),
        "line_record_cap_reached": global_state["line_records"] >= MAX_LINE_RECORDS,
        "symbol_index": {key: value for key, value in sorted(symbol_index.items())},
        "import_index": {key: value for key, value in sorted(import_index.items())},
        "setting_index": {key: value for key, value in sorted(setting_index.items())},
        "reference_index": {key: value for key, value in sorted(reference_index.items())},
    }
    coverage = {
        "schema": BRIDGE_SCHEMA,
        "mission_id": mission_id,
        "source_discovery": discovery,
        "source_files_indexed": len(source_records),
        "source_bytes_read": global_state["bytes_read"],
        "source_read_ceiling_bytes": MAX_TOTAL_SOURCE_READ_BYTES,
        "line_records": len(line_records),
        "line_record_ceiling": MAX_LINE_RECORDS,
        "launcher_records_from_v1a1": launcher_report.get("source_launcher_count"),
        "launcher_records_processed": len(launcher_records),
        "launcher_skipped": dict(sorted(launcher_skipped.items())),
        "source_skipped": dict(sorted(skipped.items())),
        "complete_areas": [
            "Static Python AST definition, import, assignment, and syntax evidence for indexed files",
            "Static BAT/CMD/PowerShell launcher text evidence for readable V1A-1 launcher records",
            "Current hash comparison for V1A-1 protected known-good candidates",
        ],
        "partial_areas": [
            "Whole-FOXAI source coverage is bounded to allowlisted first-party roots and root-level source/config files",
            "Batch variable and branch resolution is static and may remain unresolved",
            "Text-search evidence is capped and may omit later lines after the global line-record ceiling",
        ],
        "not_collected_areas": [
            "Runtime execution behavior, sys.path, import activation, processes, services, ports, scheduled tasks, event logs, and signatures",
            "Shortcut target resolution and dynamic shell expansion",
            "Third-party runtime, ComfyUI, model, library, personal-writing, archive, backup, snapshot, and package source trees",
        ],
        "network_used": False,
        "packages_installed": False,
        "foxai_source_imported_or_executed": False,
        "launchers_executed": False,
        "models_loaded": False,
    }
    receipt_seed = {
        "schema": BRIDGE_SCHEMA,
        "mission_id": mission_id,
        "result": "static_code_and_launcher_bridge_complete",
        "source_v1a1_mission_id": v1a1_receipt.get("mission_id"),
        "source_v1a1_result": v1a1_receipt.get("result"),
        "network_used": False,
        "packages_installed": False,
        "foxai_source_imported_or_executed": False,
        "launchers_executed": False,
        "python_interpreters_discovered_or_probed_by_bridge": False,
        "models_loaded": False,
        "existing_foxai_source_modified": False,
        "known_good_candidates_all_match": known_good.get("all_match"),
        "unresolved_launcher_targets_reported_as_confirmed_active": 0,
    }
    return {
        "STATIC_CODE_INDEX.json": code_index,
        "STATIC_LAUNCHER_INDEX.json": launcher_index,
        "STATIC_REFERENCE_INDEX.json": references,
        "KNOWN_GOOD_COMPARISON.json": known_good,
        "STATIC_INDEX_COVERAGE.json": coverage,
        "STATIC_BRIDGE_RECEIPT.json": receipt_seed,
    }


def query_examples_text() -> str:
    return """# Agent Fox Technical Core V1A-2 Query Examples\n\nAll queries are read-only and search the generated static indexes. A static reference does not prove that a component is running.\n\n```text\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode search --term source_locator\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode explain --path core\\foxai_web.py\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode trace-launcher --path START_FOXAI_WEB_WITH_COMFYUI.bat\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-symbol --term run_app\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-setting --term model\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-references --term source_locator\npython static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode compare-known-good\n```\n"""


def finalize_outputs(outputs: dict[str, Any]) -> dict[str, bytes]:
    serialized: dict[str, bytes] = {}
    for name, value in outputs.items():
        serialized[name] = pretty_bytes(value)
    query_bytes = query_examples_text().encode("utf-8")
    serialized["QUERY_EXAMPLES.md"] = query_bytes
    receipt = dict(outputs["STATIC_BRIDGE_RECEIPT.json"])
    receipt["core_outputs_before_receipt"] = [
        {"name": name, "size_bytes": len(data), "sha256": sha256_bytes(data)}
        for name, data in sorted(serialized.items())
        if name != "STATIC_BRIDGE_RECEIPT.json"
    ]
    serialized["STATIC_BRIDGE_RECEIPT.json"] = pretty_bytes(receipt)
    total = sum(len(data) for data in serialized.values())
    if total > MAX_OUTPUT_BYTES:
        raise ValueError(f"output_ceiling_exceeded:{total}")
    return serialized


def write_outputs(output_dir: Path, serialized: dict[str, bytes], verify_existing: bool = False) -> None:
    if verify_existing:
        missing: list[str] = []
        mismatches: list[str] = []
        for name, data in serialized.items():
            path = output_dir / name
            if not path.is_file():
                missing.append(name)
            elif path.read_bytes() != data:
                mismatches.append(name)
        if missing or mismatches:
            raise ValueError(f"determinism_check_failed:missing={missing}:mismatches={mismatches}")
        print("AGENT_FOX_V1A2_DETERMINISM_VERIFIED")
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in output_dir.iterdir() if path.is_file()}
    allowed = set(serialized)
    unexpected = sorted(existing - allowed)
    if unexpected:
        raise ValueError(f"unexpected_existing_output_files:{unexpected}")
    for name, data in serialized.items():
        (output_dir / name).write_bytes(data)


def load_indexes(index_dir: Path) -> dict[str, Any]:
    required = [
        "STATIC_CODE_INDEX.json", "STATIC_LAUNCHER_INDEX.json", "STATIC_REFERENCE_INDEX.json",
        "KNOWN_GOOD_COMPARISON.json", "STATIC_INDEX_COVERAGE.json", "STATIC_BRIDGE_RECEIPT.json",
    ]
    return {name: load_json(index_dir / name) for name in required}


def find_path_record(records: Iterable[dict[str, Any]], path_text: str) -> list[dict[str, Any]]:
    wanted = norm_win(path_text).casefold().lstrip("\\")
    exact: list[dict[str, Any]] = []
    suffix: list[dict[str, Any]] = []
    for record in records:
        relative = norm_win(record.get("relative_path", "")).casefold().lstrip("\\")
        full = norm_win(record.get("path", "")).casefold()
        if wanted in {relative, full}:
            exact.append(record)
        elif relative.endswith(wanted) or full.endswith(wanted):
            suffix.append(record)
    return exact or suffix


def trace_launcher(records: list[dict[str, Any]], start_path: str, max_depth: int = MAX_TRACE_DEPTH) -> dict[str, Any]:
    by_relative = {norm_win(item.get("relative_path", "")).casefold(): item for item in records}
    matches = find_path_record(records, start_path)
    if not matches:
        return {"finding": "launcher_not_found", "path": start_path, "trace": []}
    start = matches[0]
    queue: deque[tuple[dict[str, Any], int]] = deque([(start, 0)])
    visited: set[str] = set()
    trace: list[dict[str, Any]] = []
    while queue:
        current, depth = queue.popleft()
        key = norm_win(current.get("relative_path", "")).casefold()
        if key in visited or depth > max_depth:
            continue
        visited.add(key)
        trace.append({
            "depth": depth,
            "path": current.get("relative_path"),
            "parse_status": current.get("parse_status"),
            "ports": current.get("ports", []),
            "python_references": current.get("python_references", []),
            "edges": current.get("edges", []),
        })
        for edge in current.get("edges", []):
            relative = norm_win(edge.get("relative_path", "")).casefold()
            if relative in by_relative and relative not in visited:
                queue.append((by_relative[relative], depth + 1))
    return {
        "finding": "static_launcher_trace",
        "starting_path": start.get("relative_path"),
        "execution_performed": False,
        "similarity_or_reference_is_not_runtime_proof": True,
        "trace": trace,
    }


def run_query(index_dir: Path, mode: str, term: str | None, path_text: str | None, limit: int) -> dict[str, Any]:
    indexes = load_indexes(index_dir)
    code = indexes["STATIC_CODE_INDEX.json"]
    launchers = indexes["STATIC_LAUNCHER_INDEX.json"]
    references = indexes["STATIC_REFERENCE_INDEX.json"]
    limit = max(1, min(limit, MAX_QUERY_RESULTS))
    if mode == "search":
        if not term:
            raise ValueError("search_requires_term")
        needle = term.casefold()
        matches = [item for item in references.get("line_records", []) if needle in item.get("text", "").casefold()]
        return {"finding": "static_text_matches", "term": term, "match_count": len(matches), "results": matches[:limit], "truncated": len(matches) > limit}
    if mode == "explain":
        if not path_text:
            raise ValueError("explain_requires_path")
        code_matches = find_path_record(code.get("files", []), path_text)
        launcher_matches = find_path_record(launchers.get("records", []), path_text)
        return {"finding": "file_static_explanation", "path": path_text, "code_records": code_matches[:limit], "launcher_records": launcher_matches[:limit], "execution_performed": False}
    if mode == "trace-launcher":
        if not path_text:
            raise ValueError("trace_launcher_requires_path")
        return trace_launcher(launchers.get("records", []), path_text)
    if mode in {"find-symbol", "find-setting", "find-references"}:
        if not term:
            raise ValueError(f"{mode}_requires_term")
        table_name = {"find-symbol": "symbol_index", "find-setting": "setting_index", "find-references": "reference_index"}[mode]
        table = references.get(table_name, {})
        needle = term.casefold()
        exact = list(table.get(needle, []))
        if not exact:
            for key in sorted(table):
                if needle in key:
                    exact.extend(table[key])
                    if len(exact) >= limit:
                        break
        return {"finding": mode.replace("find-", "") + "_matches", "term": term, "results": exact[:limit], "truncated": len(exact) > limit}
    if mode == "compare-known-good":
        return indexes["KNOWN_GOOD_COMPARISON.json"]
    raise ValueError(f"unsupported_query_mode:{mode}")


def self_test() -> None:
    sample_python = """import json as js\nfrom pathlib import Path\nAPI_KEY = 'do-not-show'\nPORT = 8080\nclass Fox:\n    def trace(self, item):\n        return Path(item)\n"""
    tree = ast.parse(sample_python)
    collector = PythonCollector()
    collector.visit(tree)
    assert any(item["name"] == "Fox" and item["kind"] == "class" for item in collector.symbols)
    assert any(item["name"] == "trace" for item in collector.symbols)
    assert any(item["module"] == "json" for item in collector.imports)
    secret = next(item for item in collector.settings if item["name"] == "API_KEY")
    assert secret["value"] == "[REDACTED]"
    port = next(item for item in collector.settings if item["name"] == "PORT")
    assert port["value"] == 8080
    variables = {"root": r"Z:\FOXAI"}
    expanded, unresolved = expand_batch_value(r"%ROOT%\core\foxai_web.py", variables, r"Z:\FOXAI")
    assert expanded == r"Z:\FOXAI\core\foxai_web.py"
    assert unresolved == []
    expanded2, unresolved2 = expand_batch_value(r"%UNKNOWN%\x.py", variables, r"Z:\FOXAI")
    assert "%UNKNOWN%" in expanded2 and unresolved2 == ["%UNKNOWN%"]
    assert redacted_text("token=abc123") == "token=[REDACTED]"
    classification = classify_path(r"Backups\old\START.bat")
    assert classification["historical_or_derived_location"] is True
    assert "backup" in classification["categories"]
    print("AGENT_FOX_V1A2_SELF_TEST_OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Fox V1A-2 static code and launcher evidence bridge")
    subparsers = parser.add_subparsers(dest="command")
    build = subparsers.add_parser("build")
    build.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    build.add_argument("--normalized-dir", type=Path, default=DEFAULT_NORMALIZED_DIR)
    build.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    build.add_argument("--mission-id", default=DEFAULT_MISSION_ID)
    build.add_argument("--verify-existing", action="store_true")
    query = subparsers.add_parser("query")
    query.add_argument("--index-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    query.add_argument("--mode", required=True, choices=["search", "explain", "trace-launcher", "find-symbol", "find-setting", "find-references", "compare-known-good"])
    query.add_argument("--term")
    query.add_argument("--path")
    query.add_argument("--limit", type=int, default=25)
    query.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--self-test", action="store_true")
    return parser


def print_human(value: Any, indent: int = 0) -> None:
    prefix = "  " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                print(f"{prefix}{key}:")
                print_human(item, indent + 1)
            else:
                print(f"{prefix}{key}: {item}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                print(f"{prefix}-")
                print_human(item, indent + 1)
            else:
                print(f"{prefix}- {item}")
    else:
        print(f"{prefix}{value}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.command == "build":
        outputs = build_bridge(args.project_root, args.normalized_dir, args.mission_id)
        serialized = finalize_outputs(outputs)
        write_outputs(args.output_dir, serialized, verify_existing=args.verify_existing)
        if not args.verify_existing:
            print(json.dumps({
                "result": "static_code_and_launcher_bridge_complete",
                "output_dir": norm_win(args.output_dir),
                "files": sorted(serialized),
                "total_output_bytes": sum(len(data) for data in serialized.values()),
                "network_used": False,
                "foxai_source_or_launchers_executed": False,
            }, indent=2))
        return 0
    if args.command == "query":
        result = run_query(args.index_dir, args.mode, args.term, args.path, args.limit)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            print_human(result)
        return 0
    parser.error("choose build, query, or --self-test")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
