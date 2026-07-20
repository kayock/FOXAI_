from __future__ import annotations

import ast
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCAN_VERSION = "1.4"
SEVERITIES = ("urgent", "recommended", "informational", "healthy")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finding(
    finding_id: str,
    title: str,
    severity: str,
    summary: str,
    *,
    evidence: list[str] | None = None,
    suggested_action: str = "",
    category: str = "general",
) -> dict[str, Any]:
    value = str(severity or "informational").strip().lower()
    if value not in SEVERITIES:
        value = "informational"
    next_action = (
        "No action required."
        if value == "healthy"
        else str(suggested_action or "No action required.")
    )
    return {
        "id": str(finding_id),
        "title": str(title),
        "severity": value,
        "summary": str(summary),
        "evidence": [str(item) for item in (evidence or [])],
        "suggested_action": next_action,
        "category": str(category or "general"),
    }


def _memory_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "total_bytes": None,
        "available_bytes": None,
        "percent_used": None,
        "source": "unavailable",
    }
    if os.name != "nt":
        return result

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ok = bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)))
        if ok:
            result.update(
                {
                    "available": True,
                    "total_bytes": int(status.ullTotalPhys),
                    "available_bytes": int(status.ullAvailPhys),
                    "percent_used": int(status.dwMemoryLoad),
                    "source": "GlobalMemoryStatusEx",
                }
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _uptime_seconds() -> int | None:
    if os.name != "nt":
        return None
    try:
        return int(ctypes.windll.kernel32.GetTickCount64() // 1000)
    except Exception:
        return None


def _windows_pending_reboot() -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "pending": False,
        "confirmed_pending": False,
        "rename_pending": False,
        "confirmed_signals": [],
        "advisory_signals": [],
        "signals": [],
        "source": "unavailable",
    }
    if os.name != "nt":
        return result
    try:
        import winreg

        result["available"] = True
        result["source"] = "Windows registry read-only"
        keys = [
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
                "Component Based Servicing",
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
                "Windows Update",
            ),
        ]
        for hive, key, label in keys:
            try:
                handle = winreg.OpenKey(hive, key, 0, winreg.KEY_READ)
                winreg.CloseKey(handle)
                result["confirmed_signals"].append(label)
            except FileNotFoundError:
                pass
            except OSError:
                pass

        try:
            handle = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager",
                0,
                winreg.KEY_READ,
            )
            value, _ = winreg.QueryValueEx(handle, "PendingFileRenameOperations")
            winreg.CloseKey(handle)
            if value:
                result["advisory_signals"].append("Pending file rename operations")
        except (FileNotFoundError, OSError):
            pass

        result["confirmed_pending"] = bool(result["confirmed_signals"])
        result["rename_pending"] = bool(result["advisory_signals"])
        result["signals"] = list(result["confirmed_signals"]) + list(result["advisory_signals"])
        result["pending"] = bool(result["signals"])
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _syntax_result(path: Path) -> tuple[bool, str]:
    try:
        source = path.read_text(encoding="utf-8", errors="strict")
        ast.parse(source, filename=str(path))
        return True, "Syntax parsed successfully."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _database_quick_check(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "Database file was not found."
    connection = None
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=10)
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute("PRAGMA quick_check").fetchall()
        messages = [str(row[0]) for row in rows]
        ok = bool(messages) and all(message.casefold() == "ok" for message in messages)
        return ok, "; ".join(messages[:10]) or "No quick-check response."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        if connection is not None:
            connection.close()


def _json_result(path: Path, *, max_bytes: int = 5 * 1024 * 1024) -> tuple[bool, str]:
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return True, f"Skipped content parse because file is {size} bytes."
        json.loads(path.read_text(encoding="utf-8", errors="strict"))
        return True, "JSON parsed successfully."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _count_models(root: Path, *, limit: int = 5000) -> dict[str, Any]:
    model_root = root / "Models"
    count = 0
    total_bytes = 0
    errors: list[str] = []
    if not model_root.is_dir():
        return {"count": 0, "total_bytes": 0, "errors": [], "limited": False}
    limited = False
    try:
        for path in model_root.rglob("*.gguf"):
            if count >= limit:
                limited = True
                break
            try:
                stat = path.stat()
                count += 1
                total_bytes += int(stat.st_size)
            except Exception as exc:
                if len(errors) < 10:
                    errors.append(f"{path}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return {
        "count": count,
        "total_bytes": total_bytes,
        "errors": errors,
        "limited": limited,
    }


def _live_python_files(root: Path, *, limit: int = 600) -> list[Path]:
    results: list[Path] = []
    bases = [root / "core", root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"]
    for base in bases:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            lowered = {part.casefold() for part in path.parts}
            if "vendor" in lowered or "__pycache__" in lowered:
                continue
            results.append(path)
            if len(results) >= limit:
                return results
    return results


def _live_json_files(root: Path, *, limit: int = 250) -> list[Path]:
    config = root / "Config"
    if not config.is_dir():
        return []
    return [path for path in sorted(config.rglob("*.json")) if path.is_file()][:limit]


def _zero_byte_live_files(root: Path, *, limit: int = 100) -> dict[str, list[str]]:
    suspicious: list[str] = []
    valid_package_markers: list[str] = []
    bases = [root / "core", root / "Config", root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"]
    allowed = {".py", ".json", ".bat", ".ps1", ".toml", ".ini", ".cfg", ".md"}
    for base in bases:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            lowered = {part.casefold() for part in path.parts}
            if "vendor" in lowered or "data" in lowered or "__pycache__" in lowered:
                continue
            try:
                if not (path.is_file() and path.suffix.casefold() in allowed and path.stat().st_size == 0):
                    continue
                relative = str(path.relative_to(root)).replace("\\", "/")
                if path.suffix.casefold() == ".py" and path.name.casefold() == "__init__.py":
                    valid_package_markers.append(relative)
                else:
                    suspicious.append(relative)
                if len(suspicious) + len(valid_package_markers) >= limit:
                    return {
                        "suspicious": suspicious,
                        "valid_package_markers": valid_package_markers,
                    }
            except Exception:
                continue
    return {
        "suspicious": suspicious,
        "valid_package_markers": valid_package_markers,
    }


def _launcher_family(name: str) -> str:
    tokens = re.findall(r"[A-Z0-9]+", Path(name).stem.upper())
    noise = {
        "START", "LAUNCH", "RUN", "OPEN", "APPLY", "BUILD", "VERIFY",
        "TEST", "CHECK", "FIX", "PATCH", "HOTFIX", "UPDATE", "INSTALL",
        "COMMISSION", "CREATE", "GENERATE", "PREVIEW", "FINAL", "OLD",
        "NEW", "COPY", "BACKUP", "ROLLBACK", "RESTORE", "TOOL", "UTILITY",
        "SCRIPT", "PACKAGE", "CANDIDATE", "CONTROLLED",
    }
    cleaned: list[str] = []
    for token in tokens:
        if token in noise:
            continue
        if re.fullmatch(r"(?:V|R|C)\d+[A-Z0-9]*", token):
            continue
        if re.fullmatch(r"PHASE\d+[A-Z0-9]*", token):
            continue
        if re.fullmatch(r"20\d{6,12}", token):
            continue
        if re.fullmatch(r"[A-F0-9]{8,}", token):
            continue
        cleaned.append(token)
    return " ".join(cleaned)


def _normalized_reference(raw: str) -> str:
    value = str(raw or "").strip().strip('"').replace("\\", "/")
    value = re.sub(r"(?i)^%~dp0", "", value)
    value = re.sub(r"(?i)^%cd%/", "", value)
    return value.rsplit("/", 1)[-1].strip()


def _read_batch_text(path: Path, *, max_bytes: int = 512 * 1024) -> tuple[str, bool, str]:
    try:
        data = path.read_bytes()
        truncated = len(data) > max_bytes
        if truncated:
            data = data[:max_bytes]
        try:
            text = data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
        return text, truncated, ""
    except Exception as exc:
        return "", False, f"{type(exc).__name__}: {exc}"


def _logical_batch_lines(text: str) -> list[str]:
    logical: list[str] = []
    pending = ""
    for raw in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip()
        if pending:
            line = pending + line.lstrip()
            pending = ""
        if line.endswith("^"):
            pending = line[:-1] + " "
            continue
        logical.append(line)
    if pending:
        logical.append(pending.rstrip())
    return logical


def _batch_content_map(text: str) -> dict[str, Any]:
    command_words: set[str] = set()
    batch_refs: set[str] = set()
    python_refs: set[str] = set()
    powershell_refs: set[str] = set()
    executable_refs: set[str] = set()
    meaningful_lines = 0
    change_capable_commands = {
        "COPY", "XCOPY", "ROBOCOPY", "MOVE", "DEL", "ERASE", "RMDIR", "RD",
        "MKDIR", "MD", "REG", "SC", "NET", "TASKKILL", "SHUTDOWN", "PIP",
        "INSTALL", "GIT", "CURL", "WGET", "POWERSHELL", "PWSH",
    }
    observed_change_capable: set[str] = set()
    known_commands = {
        "CALL", "START", "CMD", "PYTHON", "PY", "POWERSHELL", "PWSH", "GIT",
        "NODE", "NPM", "NPX", "CURL", "WGET", "TASKKILL", "TIMEOUT", "PAUSE",
        "COPY", "XCOPY", "ROBOCOPY", "MOVE", "DEL", "ERASE", "RMDIR", "RD",
        "MKDIR", "MD", "REG", "SC", "NET", "SHUTDOWN", "EXPLORER", "SET",
    }
    quoted_pattern = re.compile(r'"([^"\r\n]+\.(?:bat|cmd|py|ps1|exe))"', re.I)
    bare_pattern = re.compile(
        r"(?<![A-Za-z0-9_.])([%~!A-Za-z0-9_./\\:\-]+\.(?:bat|cmd|py|ps1|exe))(?![A-Za-z0-9_.])",
        re.I,
    )

    for raw in _logical_batch_lines(text):
        stripped = raw.strip()
        if not stripped:
            continue
        without_at = stripped.lstrip("@").lstrip()
        lowered = without_at.casefold()
        if lowered.startswith("rem ") or lowered == "rem" or without_at.startswith("::"):
            continue
        if lowered.startswith("echo ") or lowered in {"echo", "echo."}:
            continue
        meaningful_lines += 1
        upper_line = without_at.upper()
        for command in known_commands:
            if re.search(rf"(?<![A-Z0-9_]){re.escape(command)}(?![A-Z0-9_])", upper_line):
                command_words.add(command)
        for command in change_capable_commands:
            if re.search(rf"(?<![A-Z0-9_]){re.escape(command.upper())}(?![A-Z0-9_])", upper_line):
                observed_change_capable.add(command.upper())
        refs = list(quoted_pattern.findall(without_at)) + list(bare_pattern.findall(without_at))
        for raw_ref in refs:
            ref = _normalized_reference(raw_ref)
            lower_ref = ref.casefold()
            if lower_ref.endswith((".bat", ".cmd")):
                batch_refs.add(ref)
            elif lower_ref.endswith(".py"):
                python_refs.add(ref)
            elif lower_ref.endswith(".ps1"):
                powershell_refs.add(ref)
            elif lower_ref.endswith(".exe"):
                executable_refs.add(ref)

    return {
        "commands": sorted(command_words),
        "child_launchers": sorted(batch_refs, key=str.casefold),
        "python_scripts": sorted(python_refs, key=str.casefold),
        "powershell_scripts": sorted(powershell_refs, key=str.casefold),
        "executables": sorted(executable_refs, key=str.casefold),
        "change_capable_commands_present": sorted(observed_change_capable),
        "meaningful_lines": meaningful_lines,
    }


def _protected_launcher_roles(name: str) -> list[str]:
    upper = str(name or "").upper()
    roles: list[str] = []
    exact = {
        "START_FOXAI_WEB_WITH_COMFYUI.BAT": "known_good_webui",
        "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.BAT": "desktop_recovery",
        "PUSH_TO_GITHUB.BAT": "github_source_backup",
        "SETUP_GITHUB_REMOTE.BAT": "github_setup",
    }
    if upper in exact:
        roles.append(exact[upper])
    if "WORKSHOP" in upper:
        roles.append("engineering_workshop")
    if upper.startswith(("START_COMFYUI", "STATUS_COMFYUI", "STOP_COMFYUI")) or upper.startswith("START COMFYUI"):
        roles.append("comfyui_lifecycle")
    if upper.startswith("STOP_") or upper.startswith("STOP "):
        roles.append("stop_control")
    if upper.startswith("COMMISSION_") or upper.startswith("COMMISSION "):
        roles.append("commissioning")
    if any(token in upper for token in ("RECOVERY", "RESTORE", "ROLLBACK")):
        roles.append("recovery")
    if "GITHUB" in upper:
        roles.append("github_workflow")
    return sorted(set(roles))


def _infer_launcher_purpose(name: str, content: dict[str, Any], protected_roles: list[str]) -> str:
    upper = str(name or "").upper()
    if "known_good_webui" in protected_roles:
        return "Starts the known-good FOXAI WebUI with the approved ComfyUI workflow."
    if "desktop_recovery" in protected_roles:
        return "Starts the known-good two-window FOXAI Desktop recovery workflow."
    if "engineering_workshop" in protected_roles:
        return "Opens or starts the Engineering Workshop workflow."
    if "comfyui_lifecycle" in protected_roles:
        if upper.startswith("STOP"):
            return "Stops a ComfyUI runtime through a dedicated lifecycle control."
        if upper.startswith("STATUS"):
            return "Reports ComfyUI lifecycle status."
        return "Starts a ComfyUI runtime or approved node profile."
    if "github_source_backup" in protected_roles or "github_workflow" in protected_roles:
        return "Supports the protected GitHub source-control workflow."
    if "stop_control" in protected_roles:
        return "Stops a named FOXAI or model-engine process through a dedicated control."
    if "commissioning" in protected_roles:
        return "Runs a commissioning or readiness workflow."
    if "recovery" in protected_roles:
        return "Supports recovery, restore, or rollback operations."
    tokens = set(re.findall(r"[A-Z0-9]+", Path(name).stem.upper()))
    if tokens & {"VERIFY", "TEST", "CHECK", "STATUS", "REPORT", "DIAGNOSTIC", "INSPECT", "SCAN", "AUDIT"}:
        return "Runs a verification, status, inspection, or diagnostic workflow."
    if tokens & {"APPLY", "PATCH", "FIX", "HOTFIX", "INSTALL", "BUILD", "COMMISSION", "GENERATE", "CREATE"}:
        return "Runs a build, installation, patch, or setup utility that requires review before reuse."
    if tokens & {"START", "LAUNCH", "RUN", "OPEN"}:
        children = content.get("child_launchers") or []
        return (
            f"Starts an entry workflow and references {len(children)} child launcher(s)."
            if children
            else "Starts or opens a FOXAI workflow."
        )
    return "Purpose is not confidently resolved from the filename and static content alone."


def _receipt_launcher_mentions(
    root: Path,
    names: list[str],
    *,
    max_receipts: int = 500,
    max_bytes: int = 2 * 1024 * 1024,
) -> tuple[dict[str, list[str]], list[str]]:
    mentions = {name: [] for name in names}
    errors: list[str] = []
    receipt_root = root / "System" / "EngineeringWorkshop" / "receipts"
    if not receipt_root.is_dir():
        return mentions, errors
    name_lookup = {name.casefold(): name for name in names}
    try:
        receipts = sorted(path for path in receipt_root.rglob("*.json") if path.is_file())[:max_receipts]
    except Exception as exc:
        return mentions, [f"{type(exc).__name__}: {exc}"]
    for path in receipts:
        try:
            size = path.stat().st_size
            if size > max_bytes:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            relative = str(path.relative_to(root)).replace("\\", "/")
            for lowered, original in name_lookup.items():
                if lowered in text:
                    mentions[original].append(relative)
        except Exception as exc:
            if len(errors) < 10:
                errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    return mentions, errors


def _external_protected_baseline(root: Path) -> list[dict[str, Any]]:
    entries = [
        ("KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat", "kayocks_study_start"),
        ("KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY.bat", "kayocks_study_verify"),
    ]
    result: list[dict[str, Any]] = []
    for relative, role in entries:
        path = root / relative
        item: dict[str, Any] = {
            "path": relative,
            "role": role,
            "present": path.is_file(),
            "size_bytes": 0,
            "sha256": "",
        }
        try:
            if path.is_file():
                data = path.read_bytes()
                item["size_bytes"] = len(data)
                item["sha256"] = hashlib.sha256(data).hexdigest()
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        result.append(item)
    return result


def _launcher_inventory(root: Path, *, hash_limit_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    try:
        launchers = sorted(path for path in root.glob("*.bat") if path.is_file())
    except Exception as exc:
        return {
            "total": 0,
            "items": [],
            "protected_baseline": {"root": [], "external": [], "missing": []},
            "relationship_edges": [],
            "receipt_backed": [],
            "exact_duplicate_groups": [],
            "similar_name_groups": [],
            "obsolete_looking_candidates": [],
            "unresolved_items": [],
            "archive_plan": {"status": "proposal_only", "changes_applied": 0, "candidates": []},
            "unreadable": [f"{type(exc).__name__}: {exc}"],
        }

    known_good_names = {
        "START_FOXAI_WEB_WITH_COMFYUI.BAT",
        "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.BAT",
    }
    active_prefixes = {"START", "LAUNCH", "RUN", "OPEN"}
    historical_tokens = {
        "APPLY", "BUILD", "PATCH", "HOTFIX", "INSTALL", "COMMISSION",
        "MIGRATE", "UPGRADE", "ROLLBACK", "RESTORE", "BOOTSTRAP",
        "PHASE", "CANDIDATE", "PREVIEW", "PACKAGE", "CREATE", "GENERATE",
    }
    verification_tokens = {
        "VERIFY", "CHECK", "STATUS", "REPORT", "DIAGNOSTIC", "TEST",
        "INSPECT", "SCAN", "AUDIT",
    }
    legacy_tokens = {"OLD", "LEGACY", "DEPRECATED", "OBSOLETE", "ARCHIVE", "COPY", "ALPHA", "BETA"}

    unreadable: list[str] = []
    hash_groups: dict[str, list[str]] = {}
    family_groups: dict[str, list[str]] = {}
    raw_items: list[dict[str, Any]] = []
    names = [path.name for path in launchers]
    receipt_mentions, receipt_errors = _receipt_launcher_mentions(root, names)
    unreadable.extend(receipt_errors)

    for path in launchers:
        name = path.name
        upper = name.upper()
        tokens = set(re.findall(r"[A-Z0-9]+", Path(name).stem.upper()))
        first_match = re.findall(r"[A-Z0-9]+", Path(name).stem.upper())
        first = first_match[0] if first_match else ""
        if upper in known_good_names:
            category = "known_good_active"
        elif first in active_prefixes and not (tokens & historical_tokens):
            category = "likely_active"
        elif tokens & historical_tokens:
            category = "historical_build_patch"
        elif tokens & verification_tokens:
            category = "verification_status"
        else:
            category = "unknown"

        text, truncated, error = _read_batch_text(path)
        if error:
            unreadable.append(f"{name}: {error}")
        content = _batch_content_map(text) if not error else {
            "commands": [], "child_launchers": [], "python_scripts": [],
            "powershell_scripts": [], "executables": [],
            "change_capable_commands_present": [], "meaningful_lines": 0,
        }
        roles = _protected_launcher_roles(name)
        size = 0
        digest = ""
        try:
            data = path.read_bytes()
            size = len(data)
            if size <= hash_limit_bytes:
                digest = hashlib.sha256(data).hexdigest()
                hash_groups.setdefault(digest, []).append(name)
            else:
                unreadable.append(f"Skipped duplicate hash for oversized BAT: {name} ({size} bytes)")
        except Exception as exc:
            unreadable.append(f"{name}: {type(exc).__name__}: {exc}")
        family = _launcher_family(name)
        if len(family) >= 5:
            family_groups.setdefault(family, []).append(name)
        raw_items.append(
            {
                "name": name,
                "relative_path": name,
                "size_bytes": size,
                "sha256": digest,
                "category": category,
                "protected": bool(roles),
                "protected_roles": roles,
                "purpose": _infer_launcher_purpose(name, content, roles),
                "commands": content["commands"],
                "change_capable_commands_present": content["change_capable_commands_present"],
                "child_launchers": content["child_launchers"],
                "python_scripts": content["python_scripts"],
                "powershell_scripts": content["powershell_scripts"],
                "executables": content["executables"],
                "meaningful_lines": content["meaningful_lines"],
                "content_truncated": truncated,
                "receipt_evidence": list(receipt_mentions.get(name) or []),
                "called_by": [],
                "entry_point_status": "unresolved",
                "archive_review": {"status": "protected" if roles else "not_proposed", "reasons": []},
            }
        )

    by_upper = {item["name"].upper(): item for item in raw_items}
    edges: list[dict[str, str]] = []
    for item in raw_items:
        for child in item["child_launchers"]:
            child_name = _normalized_reference(child)
            target = by_upper.get(child_name.upper())
            if target is None:
                continue
            target["called_by"].append(item["name"])
            edges.append({"parent": item["name"], "child": target["name"]})

    exact_duplicates = [
        {"sha256": digest, "files": sorted(group)}
        for digest, group in sorted(hash_groups.items())
        if digest and len(group) > 1
    ]
    duplicate_members = {name for group in exact_duplicates for name in group["files"]}
    duplicate_group_markers: dict[str, list[str]] = {}
    for group in exact_duplicates:
        group_markers = sorted(
            {
                token
                for member in group.get("files") or []
                for token in re.findall(r"[A-Z0-9]+", Path(member).stem.upper())
                if token in legacy_tokens
            }
        )
        for member in group.get("files") or []:
            duplicate_group_markers[str(member)] = group_markers
    similar_names = [
        {"family": family, "files": sorted(set(group))}
        for family, group in sorted(family_groups.items())
        if len(set(group)) > 1
    ]

    obsolete_candidates: list[dict[str, Any]] = []
    unresolved_items: list[str] = []
    for item in raw_items:
        item["called_by"] = sorted(set(item["called_by"]), key=str.casefold)
        if item["protected"]:
            item["entry_point_status"] = "protected_entry_point" if not item["called_by"] else "protected_support_or_entry"
            continue
        if item["called_by"]:
            item["entry_point_status"] = "support_launcher"
        elif item["category"] in {"known_good_active", "likely_active"}:
            item["entry_point_status"] = "likely_entry_point"
        elif item["category"] == "verification_status":
            item["entry_point_status"] = "diagnostic_utility"
        elif item["category"] == "historical_build_patch":
            item["entry_point_status"] = "historical_utility"
        else:
            item["entry_point_status"] = "unresolved"

        upper_tokens = set(re.findall(r"[A-Z0-9]+", Path(item["name"]).stem.upper()))
        name_markers = sorted(upper_tokens & legacy_tokens)
        group_name_markers = list(duplicate_group_markers.get(item["name"]) or [])
        duplicate_evidence = item["name"] in duplicate_members
        reasons: list[str] = []
        if duplicate_evidence:
            reasons.append("Exact duplicate content exists elsewhere in the root.")
        if name_markers:
            reasons.append(
                "Filename marker(s) " + ", ".join(name_markers)
                + " are context only and are not cleanup evidence by themselves."
            )
        elif group_name_markers:
            reasons.append(
                "Another member of the exact duplicate group contains contextual marker(s): "
                + ", ".join(group_name_markers) + "."
            )
        candidate_basis = []
        if duplicate_evidence:
            candidate_basis.append("exact_duplicate_content")
        if group_name_markers:
            candidate_basis.append("context_marker_in_duplicate_group")
        item["name_markers"] = name_markers
        item["archive_review"] = {
            "status": "not_proposed",
            "reasons": [],
            "name_markers": name_markers,
            "duplicate_group_name_markers": group_name_markers,
            "candidate_basis": candidate_basis,
            "filename_only_cleanup_allowed": False,
        }
        if (
            duplicate_evidence
            and group_name_markers
            and not item["receipt_evidence"]
            and not item["called_by"]
            and item["category"] in {"historical_build_patch", "likely_active", "unknown"}
        ):
            item["archive_review"] = {
                "status": "review_candidate_only",
                "reasons": reasons,
                "name_markers": name_markers,
                "duplicate_group_name_markers": group_name_markers,
                "candidate_basis": candidate_basis,
                "filename_only_cleanup_allowed": False,
            }
            obsolete_candidates.append(
                {
                    "name": item["name"],
                    "confidence": "low",
                    "reasons": reasons,
                    "name_markers": name_markers,
                    "candidate_basis": candidate_basis,
                    "protected": False,
                    "action": "manual_review_only",
                    "filename_only_cleanup_allowed": False,
                }
            )
        if item["entry_point_status"] == "unresolved":
            unresolved_items.append(item["name"])

    root_protected = [
        {
            "name": item["name"],
            "roles": item["protected_roles"],
            "sha256": item["sha256"],
            "receipt_evidence": item["receipt_evidence"],
        }
        for item in raw_items
        if item["protected"]
    ]
    external = _external_protected_baseline(root)
    missing = [entry["path"] for entry in external if not entry.get("present")]
    receipt_backed = [item["name"] for item in raw_items if item["receipt_evidence"]]
    archive_plan = {
        "status": "proposal_only",
        "changes_applied": 0,
        "automatic_cleanup": False,
        "delete_allowed": False,
        "move_allowed": False,
        "rename_allowed": False,
        "candidate_count": len(obsolete_candidates),
        "candidates": obsolete_candidates,
        "phases": [
            {
                "phase": 1,
                "name": "Freeze protected baseline",
                "action": "Record protected paths, hashes, roles, receipt evidence, and incoming references before considering cleanup.",
            },
            {
                "phase": 2,
                "name": "Resolve raw unknown classifications",
                "action": "Use static content and relationships to distinguish raw unknown classification from unresolved-after-resolution status.",
            },
            {
                "phase": 3,
                "name": "Compare exact duplicate evidence",
                "action": "Compare exact content, callers, receipts, and known workflows. Filename wording is context only; candidate does not mean obsolete.",
            },
            {
                "phase": 4,
                "name": "Prepare a separate proposal only if evidence justifies it",
                "action": "Require a new snapshot, exact destination list, reversible location, and explicit operator approval. Never infer cleanup from a filename and never delete directly.",
            },
        ],
    }
    return {
        "total": len(launchers),
        "items": sorted(raw_items, key=lambda item: item["name"].casefold()),
        "protected_baseline": {"root": root_protected, "external": external, "missing": missing},
        "relationship_edges": sorted(edges, key=lambda edge: (edge["parent"].casefold(), edge["child"].casefold())),
        "receipt_backed": sorted(receipt_backed, key=str.casefold),
        "exact_duplicate_groups": exact_duplicates,
        "similar_name_groups": similar_names,
        "obsolete_looking_candidates": obsolete_candidates,
        "unresolved_items": sorted(unresolved_items, key=str.casefold),
        "archive_plan": archive_plan,
        "unreadable": unreadable,
        "category_counts": {
            key: sum(1 for item in raw_items if item["category"] == key)
            for key in (
                "known_good_active", "likely_active", "historical_build_patch",
                "verification_status", "unknown",
            )
        },
    }


def _launcher_inventory_evidence(inventory: dict[str, Any]) -> list[str]:
    counts = dict(inventory.get("category_counts") or {})
    protected = list((inventory.get("protected_baseline") or {}).get("root") or [])
    external = list((inventory.get("protected_baseline") or {}).get("external") or [])
    lines = [
        (
            "Raw categories before static resolution: "
            f"{counts.get('known_good_active', 0)} known-good active, "
            f"{counts.get('likely_active', 0)} likely active, "
            f"{counts.get('historical_build_patch', 0)} historical/build/patch, "
            f"{counts.get('verification_status', 0)} verification/status, "
            f"{counts.get('unknown', 0)} unknown."
        ),
        "Protected root baseline ({}): {}".format(
            len(protected),
            ", ".join(item.get("name", "") for item in protected[:20]) or "none",
        ),
        "Protected Study baseline: " + ", ".join(
            f"{item.get('path')} ({'present' if item.get('present') else 'missing'})"
            for item in external
        ),
    ]
    consistency = dict(inventory.get("evidence_consistency") or {})
    lines.append(
        "Final static resolution: "
        f"{consistency.get('raw_unknown_count', len(inventory.get('raw_unknown_items') or []))} raw unknown classification(s), "
        f"{consistency.get('unresolved_after_resolution_count', len(inventory.get('unresolved_items') or []))} unresolved-after-resolution item(s)."
    )
    lines.append("Filename-only cleanup allowed: NO.")
    receipt_backed = list(inventory.get("receipt_backed") or [])
    lines.append(
        f"Receipt-backed launchers ({len(receipt_backed)}): "
        + (", ".join(receipt_backed[:20]) or "none")
    )
    for edge in list(inventory.get("relationship_edges") or [])[:15]:
        lines.append(f"Launcher relationship: {edge.get('parent')} -> {edge.get('child')}")
    for group in list(inventory.get("exact_duplicate_groups") or [])[:10]:
        lines.append("Exact duplicate content: " + " | ".join(group.get("files") or []))
    for candidate in list(inventory.get("obsolete_looking_candidates") or [])[:12]:
        lines.append(
            f"Duplicate-review candidate only [{candidate.get('confidence')} confidence]: "
            f"{candidate.get('name')} — " + " ".join(candidate.get("reasons") or [])
        )
    unresolved = list(inventory.get("unresolved_items") or [])
    lines.append(
        f"Unresolved after static resolution ({len(unresolved)}): " + (", ".join(unresolved[:20]) or "none")
    )
    lines.extend(list(inventory.get("unreadable") or [])[:10])
    return lines


def _launcher_index_resolution(item: dict[str, Any]) -> dict[str, Any]:
    """Resolve only what static content supports; uncertain launchers remain unresolved."""
    name = str(item.get("name") or "")
    purpose = str(item.get("purpose") or "")
    entry_status = str(item.get("entry_point_status") or "unresolved")
    commands = [str(value) for value in (item.get("commands") or [])]
    children = [str(value) for value in (item.get("child_launchers") or [])]
    python_scripts = [str(value) for value in (item.get("python_scripts") or [])]
    powershell_scripts = [str(value) for value in (item.get("powershell_scripts") or [])]
    executables = [str(value) for value in (item.get("executables") or [])]
    called_by = [str(value) for value in (item.get("called_by") or [])]
    meaningful_lines = int(item.get("meaningful_lines") or 0)
    signals: list[str] = []
    confidence = "high" if item.get("protected") or item.get("receipt_evidence") else "medium"
    unresolved_reason = ""

    if children:
        signals.append("References child launcher(s): " + ", ".join(children))
    if python_scripts:
        signals.append("References Python script(s): " + ", ".join(python_scripts))
    if powershell_scripts:
        signals.append("References PowerShell script(s): " + ", ".join(powershell_scripts))
    if executables:
        signals.append("References executable(s): " + ", ".join(executables))
    if commands:
        signals.append("Recognized command(s): " + ", ".join(commands))
    if called_by:
        signals.append("Called by: " + ", ".join(called_by))
    if item.get("receipt_evidence"):
        signals.append(
            f"Named by {len(item.get('receipt_evidence') or [])} Engineering Workshop receipt(s)."
        )

    if entry_status != "unresolved":
        return {
            "purpose": purpose,
            "purpose_confidence": confidence,
            "entry_point_status": entry_status,
            "resolution_state": "resolved",
            "unresolved_reason": "",
            "resolution_signals": signals,
        }

    confidence = "low"
    resolved_status = "unresolved"
    resolved_purpose = purpose

    if called_by and children:
        resolved_purpose = (
            "Routes one launcher workflow into another and is statically referenced by a parent launcher."
        )
        resolved_status = "support_launcher"
        confidence = "medium"
    elif called_by:
        resolved_purpose = "Serves as a support launcher that is statically referenced by another root BAT file."
        resolved_status = "support_launcher"
        confidence = "medium"
    elif children:
        resolved_purpose = "Acts as a launcher router for one or more child BAT workflows."
        resolved_status = "likely_entry_point"
        confidence = "medium"
    elif python_scripts:
        resolved_purpose = (
            "Starts a Python-backed FOXAI utility: " + ", ".join(python_scripts[:4]) + "."
        )
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif powershell_scripts:
        resolved_purpose = (
            "Starts a PowerShell-backed FOXAI utility: " + ", ".join(powershell_scripts[:4]) + "."
        )
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif executables:
        resolved_purpose = (
            "Starts or controls executable component(s): " + ", ".join(executables[:4]) + "."
        )
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif "GIT" in commands:
        resolved_purpose = "Runs a Git source-control utility."
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif "TASKKILL" in commands:
        resolved_purpose = "Runs a dedicated process-stop control."
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif "EXPLORER" in commands:
        resolved_purpose = "Opens a local FOXAI folder or resource in Windows Explorer."
        resolved_status = "utility_entry_point"
        confidence = "medium"
    elif meaningful_lines == 0:
        unresolved_reason = "The BAT file is empty, comment-only, or contains no statically meaningful command."
    elif not signals:
        unresolved_reason = "The filename and static text do not expose a reliable target, child launcher, or command."
    else:
        unresolved_reason = (
            "Static signals exist, but they are too generic to assign a trustworthy purpose without execution."
        )

    return {
        "purpose": resolved_purpose,
        "purpose_confidence": confidence,
        "entry_point_status": resolved_status,
        "resolution_state": "resolved" if resolved_status != "unresolved" else "unresolved",
        "unresolved_reason": unresolved_reason,
        "resolution_signals": signals,
    }


def _approved_launcher_front_doors(
    inventory: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    by_name = {
        str(item.get("name") or "").casefold(): item
        for item in (inventory.get("items") or [])
    }
    root_definitions = [
        {
            "name": "START_FOXAI_WEB_WITH_COMFYUI.bat",
            "tier": "primary",
            "label": "FOXAI WebUI + Creative Studio",
            "reason": "Receipt-backed known-good combined launcher.",
        },
        {
            "name": "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat",
            "tier": "primary",
            "label": "FOXAI Desktop Recovery",
            "reason": "Receipt-backed known-good two-window Desktop recovery launcher.",
        },
        {
            "name": "Launch FOXAI Workshop.bat",
            "tier": "specialized",
            "label": "Engineering Workshop",
            "reason": "Protected Workshop entry point for guarded implementation work.",
        },
    ]
    root_entries: list[dict[str, Any]] = []
    for definition in root_definitions:
        item = by_name.get(definition["name"].casefold())
        root_entries.append(
            {
                **definition,
                "present": item is not None,
                "protected": bool((item or {}).get("protected")),
                "sha256": str((item or {}).get("sha256") or ""),
                "receipt_evidence": list((item or {}).get("receipt_evidence") or []),
            }
        )

    external_by_role = {
        str(item.get("role") or ""): item
        for item in ((inventory.get("protected_baseline") or {}).get("external") or [])
    }
    study = external_by_role.get("kayocks_study_start") or {}
    external_entries = [
        {
            "path": "KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat",
            "tier": "specialized",
            "label": "Kayock's Study Standalone",
            "reason": "Known-good standalone fallback for the Bibliotheca and Research Desk.",
            "present": bool(study.get("present")),
            "protected": True,
            "sha256": str(study.get("sha256") or ""),
        }
    ]
    return {"root": root_entries, "external": external_entries}


def _finalize_launcher_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    """Create one finalized launcher dataset shared by scans, the index, and handoffs."""
    finalized = dict(inventory or {})
    duplicate_lookup: dict[str, list[dict[str, Any]]] = {}
    for group_index, group in enumerate(finalized.get("exact_duplicate_groups") or [], start=1):
        group_id = f"exact-{group_index}"
        files = list(group.get("files") or [])
        for name in files:
            duplicate_lookup.setdefault(str(name).casefold(), []).append(
                {
                    "group_id": group_id,
                    "sha256": str(group.get("sha256") or ""),
                    "files": files,
                }
            )

    similar_lookup: dict[str, list[dict[str, Any]]] = {}
    for group_index, group in enumerate(finalized.get("similar_name_groups") or [], start=1):
        group_id = f"similar-{group_index}"
        files = list(group.get("files") or [])
        for name in files:
            similar_lookup.setdefault(str(name).casefold(), []).append(
                {
                    "group_id": group_id,
                    "family": str(group.get("family") or ""),
                    "files": files,
                }
            )

    raw_unknown: list[str] = []
    refined_unresolved: list[str] = []
    enriched_items: list[dict[str, Any]] = []
    for original in finalized.get("items") or []:
        item = dict(original)
        item["raw_category"] = str(item.get("category") or "unknown")
        item["raw_entry_point_status"] = str(item.get("entry_point_status") or "unresolved")
        if item["raw_category"] == "unknown" or item["raw_entry_point_status"] == "unresolved":
            raw_unknown.append(str(item.get("name") or ""))
        resolution = _launcher_index_resolution(item)
        item.update(resolution)
        item["exact_duplicate_membership"] = duplicate_lookup.get(
            str(item.get("name") or "").casefold(), []
        )
        item["similar_name_membership"] = similar_lookup.get(
            str(item.get("name") or "").casefold(), []
        )
        item["review_flags"] = {
            "exact_duplicate": bool(item["exact_duplicate_membership"]),
            "archive_candidate": item.get("archive_review", {}).get("status") == "review_candidate_only",
        }
        if item.get("resolution_state") == "unresolved":
            refined_unresolved.append(str(item.get("name") or ""))
        duplicate_terms = []
        for group in item["exact_duplicate_membership"]:
            duplicate_terms.extend(
                [str(group.get("group_id") or ""), str(group.get("sha256") or ""), *(group.get("files") or [])]
            )
        similar_terms = []
        for group in item["similar_name_membership"]:
            similar_terms.extend(
                [str(group.get("group_id") or ""), str(group.get("family") or ""), *(group.get("files") or [])]
            )
        archive_review = item.get("archive_review") or {}
        item["search_text"] = " ".join(
            [
                str(item.get("name") or ""),
                str(item.get("relative_path") or ""),
                str(item.get("purpose") or ""),
                str(item.get("raw_category") or ""),
                str(item.get("category") or ""),
                str(item.get("raw_entry_point_status") or ""),
                str(item.get("entry_point_status") or ""),
                str(item.get("resolution_state") or ""),
                str(item.get("unresolved_reason") or ""),
                " ".join(item.get("resolution_signals") or []),
                " ".join(item.get("protected_roles") or []),
                " ".join(item.get("commands") or []),
                " ".join(item.get("change_capable_commands_present") or []),
                " ".join(item.get("child_launchers") or []),
                " ".join(item.get("called_by") or []),
                " ".join(item.get("python_scripts") or []),
                " ".join(item.get("powershell_scripts") or []),
                " ".join(item.get("executables") or []),
                " ".join(item.get("receipt_evidence") or []),
                " ".join(duplicate_terms),
                " ".join(similar_terms),
                str(archive_review.get("status") or ""),
                " ".join(archive_review.get("reasons") or []),
                " ".join(archive_review.get("name_markers") or []),
                " ".join(archive_review.get("duplicate_group_name_markers") or []),
                " ".join(archive_review.get("candidate_basis") or []),
                "exact duplicate" if item["review_flags"]["exact_duplicate"] else "",
                "archive review candidate" if item["review_flags"]["archive_candidate"] else "",
                "protected" if item.get("protected") else "unprotected",
            ]
        ).casefold()
        enriched_items.append(item)

    finalized["items"] = sorted(
        enriched_items, key=lambda item: str(item.get("name") or "").casefold()
    )
    finalized["raw_unknown_items"] = sorted(set(raw_unknown), key=str.casefold)
    finalized["unresolved_items"] = sorted(set(refined_unresolved), key=str.casefold)
    finalized["approved_front_doors"] = _approved_launcher_front_doors(finalized)
    finalized["index_filters"] = {
        "categories": sorted(
            {str(item.get("category") or "") for item in enriched_items if item.get("category")}
        ),
        "entry_point_statuses": sorted(
            {
                str(item.get("entry_point_status") or "")
                for item in enriched_items
                if item.get("entry_point_status")
            }
        ),
        "protection": ["all", "protected", "unprotected"],
        "resolution": ["all", "resolved", "unresolved"],
        "review": ["all", "exact_duplicates", "archive_candidates"],
    }
    finalized["evidence_consistency"] = {
        "finalized": True,
        "dataset": "finalized_launcher_index_dataset",
        "raw_unknown_count": len(finalized["raw_unknown_items"]),
        "unresolved_after_resolution_count": len(finalized["unresolved_items"]),
        "filename_only_cleanup_allowed": False,
    }
    return finalized


def run_launcher_index(
    root: str | Path,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only searchable launcher index without executing or changing BAT files."""
    started = time.perf_counter()
    project_root = Path(root).expanduser().resolve()
    inventory = _finalize_launcher_inventory(_launcher_inventory(project_root))
    enriched_items = list(inventory.get("items") or [])
    refined_unresolved = list(inventory.get("unresolved_items") or [])

    protected_count = sum(1 for item in enriched_items if item.get("protected"))
    front_doors = inventory["approved_front_doors"]
    front_door_count = sum(
        1
        for item in list(front_doors.get("root") or []) + list(front_doors.get("external") or [])
        if item.get("present")
    )
    elapsed = round(time.perf_counter() - started, 3)
    return {
        "ok": project_root.is_dir(),
        "version": SCAN_VERSION,
        "title": "Repair Bay V1.4 — Consistent Launcher Evidence",
        "created_at": _iso_now(),
        "root": str(project_root),
        "read_only": True,
        "elapsed_seconds": elapsed,
        "summary": {
            "total": int(inventory.get("total") or 0),
            "protected": protected_count,
            "approved_front_doors": front_door_count,
            "resolved": len(enriched_items) - len(refined_unresolved),
            "unresolved": len(refined_unresolved),
            "exact_duplicate_groups": len(inventory.get("exact_duplicate_groups") or []),
            "archive_review_candidates": len(inventory.get("obsolete_looking_candidates") or []),
            "relationships": len(inventory.get("relationship_edges") or []),
            "receipt_backed": len(inventory.get("receipt_backed") or []),
        },
        "inventory": inventory,
        "context": dict(context or {}),
        "safety": {
            "batch_files_executed": False,
            "network_used": False,
            "commands_run": False,
            "files_written": 0,
            "moves": 0,
            "renames": 0,
            "deletions": 0,
            "archives_created": 0,
            "repairs_applied": 0,
        },
        "scope": {
            "root_batch_files_only": True,
            "static_text_analysis": True,
            "receipt_text_search": True,
            "protected_study_launchers_metadata_only": True,
            "proposal_only": True,
        },
    }

def _log_snapshot(root: Path) -> dict[str, Any]:
    logs = root / "Logs"
    total = 0
    largest: list[tuple[int, str]] = []
    errors: list[str] = []
    if not logs.is_dir():
        return {"files": 0, "total_bytes": 0, "largest": [], "errors": []}
    files = 0
    for path in logs.rglob("*"):
        try:
            if not path.is_file():
                continue
            size = int(path.stat().st_size)
            files += 1
            total += size
            largest.append((size, str(path.relative_to(root)).replace("\\", "/")))
        except Exception as exc:
            if len(errors) < 10:
                errors.append(f"{path}: {type(exc).__name__}: {exc}")
    largest.sort(reverse=True)
    return {
        "files": files,
        "total_bytes": total,
        "largest": [
            {"path": path, "size_bytes": size} for size, path in largest[:10]
        ],
        "errors": errors,
    }


def _workshop_snapshot(root: Path) -> dict[str, Any]:
    base = root / "System" / "EngineeringWorkshop"
    snapshots = base / "snapshots"
    receipts = base / "receipts"
    snapshot_count = 0
    receipt_count = 0
    latest_snapshot = ""
    latest_receipt = ""
    try:
        snapshot_files = [path for path in snapshots.rglob("*.zip") if path.is_file()] if snapshots.is_dir() else []
        receipt_files = [path for path in receipts.rglob("*.json") if path.is_file()] if receipts.is_dir() else []
        snapshot_count = len(snapshot_files)
        receipt_count = len(receipt_files)
        if snapshot_files:
            latest_snapshot = str(max(snapshot_files, key=lambda path: path.stat().st_mtime))
        if receipt_files:
            latest_receipt = str(max(receipt_files, key=lambda path: path.stat().st_mtime))
    except Exception:
        pass
    return {
        "snapshot_count": snapshot_count,
        "receipt_count": receipt_count,
        "latest_snapshot": latest_snapshot,
        "latest_receipt": latest_receipt,
    }


def _headline(counts: dict[str, int]) -> str:
    if counts.get("urgent", 0):
        return f"{counts['urgent']} urgent finding(s) need attention before repair work proceeds."
    if counts.get("recommended", 0):
        return f"No urgent problems found. {counts['recommended']} recommended item(s) deserve review."
    if counts.get("informational", 0):
        return "No urgent or recommended problems found. Informational notes are available."
    return "All completed checks reported healthy."


def _repair_plan(findings: list[dict[str, Any]]) -> dict[str, Any]:
    steps = []
    for finding in findings:
        if finding["severity"] not in {"urgent", "recommended"}:
            continue
        steps.append(
            {
                "finding_id": finding["id"],
                "priority": finding["severity"],
                "title": finding["title"],
                "proposed_action": finding["suggested_action"],
                "approval_required": True,
                "backup_required": finding["category"] in {"source", "runtime", "configuration", "database"},
                "status": "proposal_only",
            }
        )
    return {
        "status": "proposal_only",
        "approval_required": True,
        "automatic_repairs": False,
        "changes_applied": 0,
        "steps": steps,
        "message": (
            "Review each proposed action separately. Repair Bay V1.4 does not apply repairs."
            if steps
            else "No repair steps are proposed from this scan."
        ),
    }


def run_repair_bay_scan(
    root: str | Path,
    *,
    mode: str = "quick",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    scan_mode = str(mode or "quick").strip().lower()
    if scan_mode not in {"quick", "full"}:
        raise ValueError("Scan mode must be 'quick' or 'full'.")

    project_root = Path(root).expanduser().resolve()
    findings: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}

    findings.append(
        _finding(
            "safety_contract",
            "Read-only safety contract",
            "healthy",
            "This diagnostic uses file metadata, text parsing, read-only SQLite checks, and read-only Windows queries only.",
            evidence=[
                "No sockets or internet requests are used.",
                "No subprocesses or repair commands are run.",
                "No files, registry values, services, or settings are changed.",
            ],
            category="safety",
        )
    )

    host = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": str(Path(os.sys.executable).resolve()),
    }
    evidence["host"] = host
    findings.append(
        _finding(
            "host_profile",
            "Host profile",
            "informational",
            f"{host['system']} {host['release']} on {host['machine']} with Python {host['python']}.",
            evidence=[f"Python executable: {host['python_executable']}"],
            category="host",
        )
    )

    root_exists = project_root.is_dir()
    findings.append(
        _finding(
            "foxai_root",
            "FOXAI project root",
            "healthy" if root_exists else "urgent",
            "The FOXAI project root is readable." if root_exists else "The FOXAI project root was not found.",
            evidence=[str(project_root)],
            suggested_action="Restore or reconnect the approved FOXAI root before continuing.",
            category="runtime",
        )
    )
    if not root_exists:
        counts = {severity: sum(1 for item in findings if item["severity"] == severity) for severity in SEVERITIES}
        return {
            "ok": False,
            "version": SCAN_VERSION,
            "title": "Repair Bay V1.4 — Consistent Launcher Evidence",
            "created_at": _iso_now(),
            "mode": scan_mode,
            "root": str(project_root),
            "read_only": True,
            "findings": findings,
            "summary": {"counts": counts, "headline": _headline(counts)},
            "proposed_repair_plan": _repair_plan(findings),
            "evidence": evidence,
            "safety": {
                "network_used": False,
                "commands_run": False,
                "files_written": 0,
                "registry_written": False,
                "services_changed": False,
                "settings_changed": False,
            },
        }

    try:
        usage = shutil.disk_usage(project_root)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        evidence["disk"] = {
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": int(usage.free),
        }
        if free_gb < 5:
            severity = "urgent"
            summary = f"Only {free_gb:.1f} GB is free on the FOXAI drive."
        elif free_gb < 20:
            severity = "recommended"
            summary = f"FOXAI has {free_gb:.1f} GB free; large models and backups may need more room."
        elif free_gb < 50:
            severity = "informational"
            summary = f"FOXAI has {free_gb:.1f} GB free."
        else:
            severity = "healthy"
            summary = f"FOXAI has {free_gb:.1f} GB free out of {total_gb:.1f} GB."
        findings.append(
            _finding(
                "disk_space",
                "FOXAI drive free space",
                severity,
                summary,
                evidence=[f"Root: {project_root}", f"Free bytes: {usage.free}"],
                suggested_action="Review large models, outputs, and old packages through an approved cleanup plan; do not delete automatically.",
                category="storage",
            )
        )
    except Exception as exc:
        findings.append(
            _finding(
                "disk_space",
                "FOXAI drive free space",
                "recommended",
                "Free-space information could not be read.",
                evidence=[f"{type(exc).__name__}: {exc}"],
                suggested_action="Inspect drive availability manually before large builds.",
                category="storage",
            )
        )

    memory = _memory_snapshot()
    evidence["memory"] = memory
    if memory.get("available"):
        available_gb = int(memory["available_bytes"]) / (1024 ** 3)
        if available_gb < 1:
            severity = "urgent"
        elif available_gb < 2:
            severity = "recommended"
        elif int(memory.get("percent_used") or 0) >= 85:
            severity = "recommended"
        else:
            severity = "healthy"
        findings.append(
            _finding(
                "memory_pressure",
                "Current memory availability",
                severity,
                f"{available_gb:.1f} GB physical memory is currently available; {memory.get('percent_used')}% is in use.",
                suggested_action="Close unnecessary applications or reduce model/runtime load before heavy operations.",
                category="host",
            )
        )
    else:
        findings.append(
            _finding(
                "memory_pressure",
                "Current memory availability",
                "informational",
                "Physical-memory information is available only when this scanner runs on Windows.",
                evidence=[str(memory.get("error") or "Non-Windows verification environment")],
                category="host",
            )
        )

    uptime = _uptime_seconds()
    if uptime is not None:
        days = uptime / 86400
        findings.append(
            _finding(
                "system_uptime",
                "Windows uptime",
                "recommended" if days >= 14 else "healthy",
                f"Windows has been running for approximately {days:.1f} day(s).",
                suggested_action="Schedule a normal restart after saving work if uptime is contributing to stale services or updates.",
                category="host",
            )
        )

    reboot = _windows_pending_reboot()
    evidence["pending_reboot"] = reboot
    if reboot.get("available"):
        confirmed = list(reboot.get("confirmed_signals") or [])
        advisory = list(reboot.get("advisory_signals") or [])
        if confirmed:
            restart_severity = "recommended"
            restart_title = "Confirmed Windows restart requirement"
            restart_summary = "Windows Update or Component Based Servicing reports that a restart is required."
            restart_action = "Save work and schedule a normal restart; do not force one during a scan."
        elif advisory:
            restart_severity = "informational"
            restart_title = "Pending file rename marker"
            restart_summary = (
                "A pending file-rename marker exists, but no Windows Update or servicing restart signal was found. "
                "The marker may belong to another application or may be stale."
            )
            restart_action = (
                "No immediate action required. Recheck after a normal restart or after the related application finishes; "
                "do not clear the marker manually."
            )
        else:
            restart_severity = "healthy"
            restart_title = "Windows restart status"
            restart_summary = "No confirmed Windows Update, servicing, or file-rename restart signal was found."
            restart_action = "No action required."
        findings.append(
            _finding(
                "pending_reboot",
                restart_title,
                restart_severity,
                restart_summary,
                evidence=confirmed + advisory,
                suggested_action=restart_action,
                category="host",
            )
        )

    essentials = [
        ("core/foxai_web.py", "FOXAI WebUI source", "urgent"),
        ("core/engineer_agent.py", "Engineer source", "recommended"),
        ("Engine/llama-server.exe", "Local model engine", "urgent"),
        ("Runtime/Desktop/python/python.exe", "Portable Desktop Python", "urgent"),
        ("Config", "Configuration folder", "recommended"),
        ("Models", "Model folder", "recommended"),
        ("Library", "Library folder", "informational"),
        ("ComfyUI/main.py", "Creative Studio engine", "recommended"),
        ("KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py", "Kayock's Study server", "recommended"),
    ]
    missing_urgent: list[str] = []
    missing_recommended: list[str] = []
    present: list[str] = []
    for relative, label, missing_severity in essentials:
        path = project_root / relative
        if path.exists():
            present.append(f"{label}: {relative}")
        elif missing_severity == "urgent":
            missing_urgent.append(f"{label}: {relative}")
        else:
            missing_recommended.append(f"{label}: {relative}")
    if missing_urgent:
        essential_severity = "urgent"
        essential_summary = f"{len(missing_urgent)} essential runtime component(s) are missing."
    elif missing_recommended:
        essential_severity = "recommended"
        essential_summary = f"Core runtime exists, but {len(missing_recommended)} expected component(s) are missing."
    else:
        essential_severity = "healthy"
        essential_summary = "All expected core FOXAI components were found."
    findings.append(
        _finding(
            "essential_components",
            "Essential FOXAI components",
            essential_severity,
            essential_summary,
            evidence=missing_urgent + missing_recommended + present,
            suggested_action="Restore only the missing component from a verified package or known-good snapshot after reviewing an exact plan.",
            category="runtime",
        )
    )

    launchers = [
        "START_FOXAI_WEB_WITH_COMFYUI.bat",
        "START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat",
        "KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat",
        "KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY.bat",
    ]
    launcher_evidence: list[str] = []
    launcher_failures: list[str] = []
    for relative in launchers:
        path = project_root / relative
        try:
            if not path.is_file():
                launcher_failures.append(f"Missing: {relative}")
            elif path.stat().st_size == 0:
                launcher_failures.append(f"Zero bytes: {relative}")
            else:
                launcher_evidence.append(f"Present ({path.stat().st_size} bytes): {relative}")
        except Exception as exc:
            launcher_failures.append(f"Unreadable: {relative}: {type(exc).__name__}: {exc}")
    findings.append(
        _finding(
            "known_good_launchers",
            "Known-good launchers",
            "recommended" if launcher_failures else "healthy",
            f"{len(launcher_failures)} launcher issue(s) need review." if launcher_failures else "Known-good WebUI, Desktop recovery, and Study launchers are present and non-empty.",
            evidence=launcher_failures + launcher_evidence,
            suggested_action="Restore a missing or empty launcher from its known-good archived baseline; do not replace working launchers broadly.",
            category="runtime",
        )
    )

    key_sources = [
        project_root / "core" / "foxai_web.py",
        project_root / "core" / "engineer_agent.py",
        project_root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "study_server.py",
    ]
    syntax_failures: list[str] = []
    syntax_ok: list[str] = []
    for path in key_sources:
        if not path.is_file():
            continue
        ok, message = _syntax_result(path)
        relative = str(path.relative_to(project_root)).replace("\\", "/")
        (syntax_ok if ok else syntax_failures).append(f"{relative}: {message}")
    findings.append(
        _finding(
            "key_source_syntax",
            "Key Python source syntax",
            "urgent" if syntax_failures else "healthy",
            f"{len(syntax_failures)} key source file(s) failed syntax parsing." if syntax_failures else f"{len(syntax_ok)} key source file(s) parsed successfully without creating bytecode.",
            evidence=syntax_failures + syntax_ok,
            suggested_action="Compare the failing source with the latest verified snapshot and prepare an exact targeted restore or correction.",
            category="source",
        )
    )

    models = _count_models(project_root)
    evidence["models"] = models
    if models["count"] == 0:
        model_severity = "recommended"
        model_summary = "No local GGUF models were found under FOXAI/Models."
    elif models["errors"]:
        model_severity = "recommended"
        model_summary = f"Found {models['count']} local model(s), with {len(models['errors'])} metadata read error(s)."
    else:
        model_severity = "healthy"
        model_summary = f"Found {models['count']} local GGUF model(s) totaling {models['total_bytes'] / (1024 ** 3):.1f} GB."
    findings.append(
        _finding(
            "local_models",
            "Local model library",
            model_severity,
            model_summary,
            evidence=list(models["errors"]),
            suggested_action="Confirm an approved model folder or restore the preferred model reference; never move or delete model files automatically.",
            category="models",
        )
    )

    study_db = project_root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "Data" / "bibliotheca.sqlite3"
    if study_db.is_file():
        db_ok, db_message = _database_quick_check(study_db)
        findings.append(
            _finding(
                "bibliotheca_database",
                "Bibliotheca database integrity",
                "healthy" if db_ok else "urgent",
                "SQLite quick-check returned OK in read-only mode." if db_ok else "The Bibliotheca database did not pass its read-only quick-check.",
                evidence=[db_message, str(study_db)],
                suggested_action="Stop Study, preserve the database and WAL files, then review recovery from the latest verified backup before any repair.",
                category="database",
            )
        )
    else:
        findings.append(
            _finding(
                "bibliotheca_database",
                "Bibliotheca database integrity",
                "informational",
                "No Bibliotheca database was found, so no database integrity check was run.",
                evidence=[str(study_db)],
                category="database",
            )
        )

    workshop = _workshop_snapshot(project_root)
    evidence["engineering_workshop"] = workshop
    workshop_ok = workshop["snapshot_count"] > 0 and workshop["receipt_count"] > 0
    findings.append(
        _finding(
            "engineering_workshop_recovery",
            "Engineering Workshop recovery evidence",
            "healthy" if workshop_ok else "informational",
            (
                f"Found {workshop['snapshot_count']} snapshot archive(s) and {workshop['receipt_count']} receipt(s)."
                if workshop_ok
                else "No complete Engineering Workshop snapshot-and-receipt history was found yet."
            ),
            evidence=[item for item in [workshop.get("latest_snapshot", ""), workshop.get("latest_receipt", "")] if item],
            suggested_action="Keep verified snapshots and receipts with each implementation mission.",
            category="recovery",
        )
    )

    if scan_mode == "full":
        python_files = _live_python_files(project_root)
        full_syntax_failures: list[str] = []
        for path in python_files:
            ok, message = _syntax_result(path)
            if not ok:
                full_syntax_failures.append(
                    f"{path.relative_to(project_root).as_posix()}: {message}"
                )
                if len(full_syntax_failures) >= 30:
                    break
        findings.append(
            _finding(
                "full_python_syntax",
                "Full live Python syntax scan",
                "urgent" if full_syntax_failures else "healthy",
                f"Scanned {len(python_files)} live Python file(s); {len(full_syntax_failures)} failed." if full_syntax_failures else f"All {len(python_files)} scanned live Python file(s) parsed successfully.",
                evidence=full_syntax_failures,
                suggested_action="Restore or correct each failing source individually from a verified snapshot; avoid broad rewrites.",
                category="source",
            )
        )

        json_files = _live_json_files(project_root)
        json_failures: list[str] = []
        for path in json_files:
            ok, message = _json_result(path)
            if not ok:
                json_failures.append(
                    f"{path.relative_to(project_root).as_posix()}: {message}"
                )
                if len(json_failures) >= 30:
                    break
        findings.append(
            _finding(
                "configuration_json",
                "Configuration JSON validity",
                "recommended" if json_failures else "healthy",
                f"Scanned {len(json_files)} configuration JSON file(s); {len(json_failures)} failed to parse." if json_failures else f"All {len(json_files)} scanned configuration JSON file(s) parsed successfully.",
                evidence=json_failures,
                suggested_action="Restore or correct only the invalid configuration after reviewing an exact diff and preserving the original.",
                category="configuration",
            )
        )

        zero_byte = _zero_byte_live_files(project_root)
        suspicious_zero = list(zero_byte.get("suspicious") or [])
        valid_markers = list(zero_byte.get("valid_package_markers") or [])
        zero_summary = (
            f"Found {len(suspicious_zero)} suspicious zero-byte live file(s)."
            if suspicious_zero
            else (
                f"No suspicious zero-byte live files were found; {len(valid_markers)} empty __init__.py package marker(s) were recognized as valid."
                if valid_markers
                else "No zero-byte live source, configuration, or Study launcher files were found."
            )
        )
        findings.append(
            _finding(
                "zero_byte_live_files",
                "Empty live source or launcher files",
                "recommended" if suspicious_zero else "healthy",
                zero_summary,
                evidence=(
                    [f"Suspicious: {item}" for item in suspicious_zero]
                    + [f"Valid Python package marker: {item}" for item in valid_markers]
                ),
                suggested_action="Restore each suspicious empty live file from its exact known-good source after confirming the path and hash.",
                category="source",
            )
        )

        logs = _log_snapshot(project_root)
        evidence["logs"] = logs
        largest_size = max((item["size_bytes"] for item in logs["largest"]), default=0)
        logs_need_review = logs["total_bytes"] > 2 * 1024 ** 3 or largest_size > 250 * 1024 ** 2 or bool(logs["errors"])
        findings.append(
            _finding(
                "log_growth",
                "Log folder growth",
                "recommended" if logs_need_review else "healthy",
                f"Logs contain {logs['files']} file(s) totaling {logs['total_bytes'] / (1024 ** 2):.1f} MB.",
                evidence=[f"{item['path']}: {item['size_bytes']} bytes" for item in logs["largest"]] + list(logs["errors"]),
                suggested_action="Review oversized logs and archive or trim them only through an approved cleanup action.",
                category="storage",
            )
        )

        launcher_inventory = _finalize_launcher_inventory(_launcher_inventory(project_root))
        evidence["launcher_inventory"] = launcher_inventory
        launcher_count = int(launcher_inventory.get("total") or 0)
        duplicate_count = len(launcher_inventory.get("exact_duplicate_groups") or [])
        edge_count = len(launcher_inventory.get("relationship_edges") or [])
        receipt_count = len(launcher_inventory.get("receipt_backed") or [])
        protected_count = len((launcher_inventory.get("protected_baseline") or {}).get("root") or [])
        candidate_count = len(launcher_inventory.get("obsolete_looking_candidates") or [])
        unresolved_count = len(launcher_inventory.get("unresolved_items") or [])
        launcher_review = launcher_count > 40 or duplicate_count > 0 or unresolved_count > 0
        raw_unknown_count = len(launcher_inventory.get("raw_unknown_items") or [])
        launcher_summary = (
            f"Mapped {launcher_count} root BAT file(s) from one finalized read-only dataset. "
            f"Protected {protected_count} root launcher(s), found {edge_count} child-launcher relationship(s), "
            f"{receipt_count} receipt-backed launcher(s), {duplicate_count} exact duplicate group(s), "
            f"{candidate_count} low-confidence duplicate-review candidate(s), "
            f"{raw_unknown_count} raw unknown classification(s), and {unresolved_count} unresolved-after-resolution item(s)."
        )
        findings.append(
            _finding(
                "root_launcher_inventory",
                "FOXAI launcher map and protected baseline",
                "recommended" if launcher_review else "informational",
                launcher_summary,
                evidence=_launcher_inventory_evidence(launcher_inventory),
                suggested_action="Preserve the protected baseline. Review exact duplicate members and their static evidence only; a filename marker alone never justifies cleanup. Do not move, rename, delete, archive, or execute scripts from this scan.",
                category="organization",
            )
        )

    counts = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in SEVERITIES
    }
    elapsed = round(time.perf_counter() - started, 3)
    report = {
        "ok": counts["urgent"] == 0,
        "version": SCAN_VERSION,
        "title": "Repair Bay V1.4 — Consistent Launcher Evidence",
        "created_at": _iso_now(),
        "mode": scan_mode,
        "root": str(project_root),
        "read_only": True,
        "elapsed_seconds": elapsed,
        "summary": {
            "counts": counts,
            "headline": _headline(counts),
            "overall": (
                "urgent"
                if counts["urgent"]
                else "recommended"
                if counts["recommended"]
                else "healthy"
            ),
            "checks": len(findings),
        },
        "findings": findings,
        "proposed_repair_plan": _repair_plan(findings),
        "evidence": evidence,
        "context": dict(context or {}),
        "safety": {
            "network_used": False,
            "commands_run": False,
            "files_written": 0,
            "registry_written": False,
            "services_changed": False,
            "settings_changed": False,
            "repairs_applied": 0,
            "protected_content_scanned": False,
        },
        "scope": {
            "whole_drive_scan": False,
            "foxai_root_only": True,
            "protected_locations_excluded": True,
            "database_open_mode": "read_only",
            "source_validation": "AST parse only; no bytecode written",
        },
    }
    return report
