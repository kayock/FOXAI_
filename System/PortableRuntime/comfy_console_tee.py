from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run isolated ComfyUI while mirroring its console "
            "to current.log."
        )
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("comfy_args", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    portable = (
        root / "Runtime" / "Desktop" / "python" / "python.exe"
    )
    isolated = (
        root
        / "System"
        / "PortableRuntime"
        / "launch_comfyui_isolated.py"
    )

    if not portable.is_file():
        print(
            f"ERROR: Portable Python not found: {portable}",
            flush=True,
        )
        return 2
    if not isolated.is_file():
        print(
            f"ERROR: Isolated ComfyUI launcher not found: {isolated}",
            flush=True,
        )
        return 3

    comfy_args = list(args.comfy_args)
    if comfy_args and comfy_args[0] == "--":
        comfy_args = comfy_args[1:]

    log_dir = (
        root / "Runtime" / "ComfyUI" / "logs" / "live"
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    current_log = log_dir / "current.log"

    command = [
        str(portable),
        "-I",
        "-B",
        "-S",
        str(isolated),
        "--root",
        str(root),
        "--",
        *comfy_args,
    ]

    header = (
        "\n"
        "============================================================\n"
        "FOXAI COMFYUI OPERATIONS CAPTURE\n"
        f"Started: {datetime.now(timezone.utc).isoformat()}\n"
        f"Command: {' '.join(command)}\n"
        "============================================================\n"
    ).encode("utf-8", errors="replace")

    with current_log.open("wb") as log:
        log.write(header)
        log.flush()
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.flush()

        child = subprocess.Popen(
            command,
            cwd=str(root),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        try:
            assert child.stdout is not None
            while True:
                chunk = child.stdout.read(512)
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                log.write(chunk)
                log.flush()
            return int(child.wait())
        except KeyboardInterrupt:
            print(
                "\nFOXAI: Stop requested. Closing ComfyUI...",
                flush=True,
            )
            try:
                child.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                try:
                    child.terminate()
                except Exception:
                    pass
            try:
                return int(child.wait(timeout=10))
            except Exception:
                try:
                    child.kill()
                except Exception:
                    pass
                return 130


if __name__ == "__main__":
    raise SystemExit(main())
