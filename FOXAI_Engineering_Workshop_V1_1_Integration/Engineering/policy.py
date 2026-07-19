from __future__ import annotations

import os
from pathlib import Path

DEFAULT_EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "wheelhouse",
    "wheelhouses",
    "cache",
    "caches",
    "temp",
    "tmp",
    "logs",
    "receipts",
    "snapshots",
    "snapshot",
    "backups",
    "backup",
    "archive",
    "archives",
    "quarantine",
    "pdr3c_quarantine",
    "preflight_output",
    "source_snapshots",
    "doc",
    "docs",
}

DEFAULT_PROTECTED_RELATIVE_PREFIXES = {
    ".git",
    ".env",
    "credentials",
    "secrets",
    "private",
}

ALLOWED_ACTIONS = {"replace_text", "write_file"}
MAX_TEXT_FILE_BYTES = 8 * 1024 * 1024
MAX_COMMAND_OUTPUT_CHARS = 200_000
DEFAULT_COMMAND_TIMEOUT_SECONDS = 180


class PolicyError(RuntimeError):
    """Raised when an engineering plan violates a Workshop safety rule."""


def canonical(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def is_within(path: Path, root: Path) -> bool:
    path_c = canonical(path)
    root_c = canonical(root)
    try:
        path_c.relative_to(root_c)
        return True
    except ValueError:
        return False


def validate_relative_path(relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise PolicyError(f"Path must be relative to the approved project root: {relative_path}")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise PolicyError(f"Unsafe relative path: {relative_path}")
    lowered = {part.lower() for part in candidate.parts}
    if lowered & DEFAULT_PROTECTED_RELATIVE_PREFIXES:
        raise PolicyError(f"Protected path is not eligible for Workshop V1 changes: {relative_path}")
    return candidate


def resolve_project_path(project_root: Path, relative_path: str) -> Path:
    rel = validate_relative_path(relative_path)
    target = canonical(project_root / rel)
    if not is_within(target, project_root):
        raise PolicyError(f"Resolved path escapes the project root: {relative_path}")
    if target.exists() and target.is_symlink():
        raise PolicyError(f"Symlink targets are not modified by Workshop V1: {relative_path}")
    parent = target.parent
    while is_within(parent, project_root) and parent != canonical(project_root):
        if parent.exists() and parent.is_symlink():
            raise PolicyError(f"Path crosses a symlinked directory: {relative_path}")
        parent = parent.parent
    return target


def ensure_project_root(project_root: Path) -> Path:
    root = canonical(project_root)
    if not root.exists() or not root.is_dir():
        raise PolicyError(f"Project root is not an existing directory: {root}")
    if root.is_symlink():
        raise PolicyError(f"Project root cannot be a symlink: {root}")
    return root


def writable_parent(path: Path) -> bool:
    existing = path
    while not existing.exists() and existing.parent != existing:
        existing = existing.parent
    return existing.exists() and os.access(existing, os.W_OK)
