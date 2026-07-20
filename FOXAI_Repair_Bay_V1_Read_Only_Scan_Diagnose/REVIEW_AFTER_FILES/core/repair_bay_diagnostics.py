from __future__ import annotations

import ast
import ctypes
import json
import os
import platform
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCAN_VERSION = "1.0"
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
    return {
        "id": str(finding_id),
        "title": str(title),
        "severity": value,
        "summary": str(summary),
        "evidence": [str(item) for item in (evidence or [])],
        "suggested_action": str(suggested_action or "No action required."),
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
                result["signals"].append(label)
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
                result["signals"].append("Pending file rename operations")
        except (FileNotFoundError, OSError):
            pass

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


def _zero_byte_live_files(root: Path, *, limit: int = 100) -> list[str]:
    results: list[str] = []
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
                if path.is_file() and path.suffix.casefold() in allowed and path.stat().st_size == 0:
                    results.append(str(path.relative_to(root)).replace("\\", "/"))
                    if len(results) >= limit:
                        return results
            except Exception:
                continue
    return results


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
            "Review each proposed action separately. Repair Bay V1 does not apply repairs."
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
            "title": "Repair Bay V1 — Read-Only Scan and Diagnose",
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
        findings.append(
            _finding(
                "pending_reboot",
                "Pending Windows restart",
                "recommended" if reboot.get("pending") else "healthy",
                "Windows reports a pending restart." if reboot.get("pending") else "No standard pending-restart signal was found.",
                evidence=list(reboot.get("signals") or []),
                suggested_action="Save work and schedule a normal restart; do not force one during a scan.",
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
        findings.append(
            _finding(
                "zero_byte_live_files",
                "Empty live source or launcher files",
                "recommended" if zero_byte else "healthy",
                f"Found {len(zero_byte)} zero-byte live file(s) in core configuration and Study locations." if zero_byte else "No zero-byte live source, configuration, or Study launcher files were found.",
                evidence=zero_byte,
                suggested_action="Restore each empty live file from its exact known-good source after confirming the path and hash.",
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

        root_launchers = []
        try:
            root_launchers = [path for path in project_root.glob("*.bat") if path.is_file()]
        except Exception:
            pass
        launcher_count = len(root_launchers)
        findings.append(
            _finding(
                "root_launcher_clutter",
                "FOXAI root launcher count",
                "recommended" if launcher_count > 40 else "informational",
                f"The FOXAI root contains {launcher_count} BAT launcher or utility file(s).",
                evidence=[path.name for path in sorted(root_launchers)[:60]],
                suggested_action="Preserve known-good launchers, then design a separate approved launcher index or archive plan instead of deleting scripts directly.",
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
        "title": "Repair Bay V1 — Read-Only Scan and Diagnose",
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
