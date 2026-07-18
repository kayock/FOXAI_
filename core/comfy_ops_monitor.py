from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

try:
    import psutil
except Exception:
    psutil = None


_PROGRESS_RE = re.compile(r"(?<!\d)(100|[1-9]?\d)\s*%")
_LOG_SUFFIXES = {".log", ".txt", ".out", ".err"}


def _health(timeout: float = 0.35) -> tuple[bool, str]:
    try:
        with urlopen(
            "http://127.0.0.1:8188/system_stats",
            timeout=timeout,
        ) as response:
            payload = response.read(1024 * 1024)
        if payload:
            try:
                json.loads(payload.decode("utf-8", errors="replace"))
            except Exception:
                pass
        return True, "ComfyUI health endpoint responded."
    except Exception:
        return False, "ComfyUI health endpoint is not ready yet."


def _running_process(root: Path) -> tuple[bool, int | None]:
    """Detect a live ComfyUI process without trusting stale controller state."""
    if psutil is None:
        return False, None

    root_text = str(root).replace("/", "\\").casefold()
    launcher_marker = "launch_comfyui_isolated.py"
    main_marker = str(root / "ComfyUI" / "main.py").replace("/", "\\").casefold()

    try:
        processes = psutil.process_iter(["pid", "cmdline"])
    except Exception:
        return False, None

    for process in processes:
        try:
            command = process.info.get("cmdline") or []
            normalized = (
                " ".join(str(part) for part in command)
                .replace("/", "\\")
                .casefold()
            )
            if not normalized:
                continue

            launcher_match = (
                launcher_marker in normalized
                and (root_text in normalized or "8188" in normalized)
            )
            main_match = main_marker in normalized
            comfy_port_match = (
                "comfyui" in normalized
                and "--port" in normalized
                and "8188" in normalized
            )
            if launcher_match or main_match or comfy_port_match:
                return True, int(process.info.get("pid") or process.pid)
        except Exception:
            continue

    return False, None


def _candidate_logs(root: Path) -> list[Path]:
    log_root = root / "Runtime" / "ComfyUI" / "logs"
    preferred = [
        log_root / "live" / "current.log",
        log_root / "current.log",
        log_root / "normal" / "current.log",
    ]
    found = [path for path in preferred if path.is_file()]
    if log_root.is_dir():
        try:
            for path in log_root.rglob("*"):
                if (
                    path.is_file()
                    and path.suffix.lower() in _LOG_SUFFIXES
                    and path not in found
                ):
                    found.append(path)
        except OSError:
            pass
    return found


def _latest_log(root: Path) -> Path | None:
    candidates = _candidate_logs(root)
    if not candidates:
        return None

    def modified(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    return max(candidates, key=modified)


def _tail(
    path: Path,
    max_bytes: int = 96 * 1024,
    line_limit: int = 140,
) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(-max_bytes, 2)
            raw = handle.read()
    except OSError as exc:
        return f"Unable to read log: {type(exc).__name__}: {exc}"

    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines[-max(10, int(line_limit)):]).strip()


def _progress(text: str) -> int | None:
    values = [
        int(match.group(1))
        for match in _PROGRESS_RE.finditer(text or "")
    ]
    return values[-1] if values else None


def comfy_operations_snapshot(
    root: str | Path,
    line_limit: int = 140,
) -> dict:
    root_path = Path(root).resolve()
    online, health_message = _health()
    process_running, process_pid = _running_process(root_path)
    log_path = _latest_log(root_path)
    tail = _tail(log_path, line_limit=line_limit) if log_path else ""
    progress = _progress(tail)

    if online and progress is not None and 0 < progress < 100:
        state = "GENERATING"
    elif online and progress == 100:
        state = "COMPLETE"
    elif online:
        state = "READY"
    elif process_running:
        state = "STARTING"
        health_message = (
            "ComfyUI is running and still loading. "
            "FOXAI will mark it online when port 8188 responds."
        )
    else:
        state = "OFFLINE"
        health_message = (
            "ComfyUI is stopped. Start it when you need Red Canvas."
        )

    modified = None
    if log_path is not None:
        try:
            modified = datetime.fromtimestamp(
                log_path.stat().st_mtime
            ).isoformat(timespec="seconds")
        except OSError:
            modified = None

    if online and not tail:
        health_message = (
            "ComfyUI is online. No captured console log is available yet."
        )

    return {
        "ok": True,
        "online": online,
        "process_running": process_running,
        "process_pid": process_pid,
        "state": state,
        "progress_percent": progress,
        "endpoint": "http://127.0.0.1:8188",
        "log_path": str(log_path) if log_path else None,
        "log_modified": modified,
        "tail": tail,
        "message": health_message,
        "read_only": True,
    }
