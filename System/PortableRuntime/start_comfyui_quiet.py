from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


def health_ready(timeout: float = 0.6) -> bool:
    try:
        with urlopen(
            "http://127.0.0.1:8188/system_stats",
            timeout=timeout,
        ) as response:
            response.read(64)
        return True
    except Exception:
        return False


def load_psutil(root: Path):
    candidates = [
        root / "Runtime" / "Desktop" / "site-packages",
        root / "Runtime" / "Core" / "site-packages",
        root / "Runtime" / "ComfyUI" / "site-packages",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            value = str(candidate)
            if value not in sys.path:
                sys.path.insert(0, value)
    try:
        import psutil
        return psutil
    except Exception:
        return None


def existing_process(root: Path) -> tuple[bool, int | None]:
    psutil = load_psutil(root)
    if psutil is None:
        return False, None

    root_text = str(root).replace("/", "\\").casefold()
    markers = (
        "launch_comfyui_isolated.py",
        str(root / "ComfyUI" / "main.py")
        .replace("/", "\\")
        .casefold(),
    )

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

            isolated = (
                markers[0] in normalized
                and (root_text in normalized or "8188" in normalized)
            )
            direct = markers[1] in normalized
            port_process = (
                "comfyui" in normalized
                and "--port" in normalized
                and "8188" in normalized
            )
            if isolated or direct or port_process:
                return True, int(process.info.get("pid") or process.pid)
        except Exception:
            continue

    return False, None


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start FOXAI ComfyUI quietly with a plain log file."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--source", default="foxai")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    python = root / "Runtime" / "Desktop" / "python" / "python.exe"
    launcher = (
        root
        / "System"
        / "PortableRuntime"
        / "launch_comfyui_isolated.py"
    )

    if not python.is_file():
        print(f"ERROR: Portable Python is missing: {python}")
        return 2
    if not launcher.is_file():
        print(f"ERROR: Isolated ComfyUI launcher is missing: {launcher}")
        return 3

    if health_ready():
        print("ComfyUI is already READY on 127.0.0.1:8188.")
        return 0

    running, pid = existing_process(root)
    if running:
        print(
            "ComfyUI is already STARTING"
            + (f" as PID {pid}." if pid else ".")
        )
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = (
        root
        / "Runtime"
        / "ComfyUI"
        / "logs"
        / "quiet"
        / stamp
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "console.log"

    command = [
        str(python),
        "-I",
        "-B",
        "-S",
        str(launcher),
        "--root",
        str(root),
        "--",
        "--cpu",
        "--disable-all-custom-nodes",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
    ]

    environment = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(key, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["HF_HUB_DISABLE_TELEMETRY"] = "1"
    environment["DO_NOT_TRACK"] = "1"

    flags = 0
    if os.name == "nt":
        flags = (
            subprocess.CREATE_NO_WINDOW
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )

    with log_path.open("wb", buffering=0) as output:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
        )

    time.sleep(0.8)
    return_code = process.poll()
    if return_code is not None:
        print(
            "ERROR: Quiet ComfyUI process exited immediately "
            f"with code {return_code}."
        )
        print(f"Log: {log_path}")
        return 4

    state = {
        "schema": 1,
        "state": "STARTING",
        "source": str(args.source),
        "pid": process.pid,
        "started": datetime.now(timezone.utc).isoformat(),
        "endpoint": "http://127.0.0.1:8188",
        "log_path": str(log_path),
        "command": command,
        "visible_console": False,
        "tee_wrapper_used": False,
    }
    state_path = (
        root
        / "Runtime"
        / "ComfyUI"
        / "logs"
        / "quiet"
        / "latest_start.json"
    )
    write_json(state_path, state)

    print(f"ComfyUI started quietly as PID {process.pid}.")
    print(f"Progress log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
