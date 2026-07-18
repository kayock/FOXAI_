#!/usr/bin/env python3
"""Proposed C3G ComfyUI isolated activation launcher.

This file is a proposal only until C3G operator approval. It must be run by the
USB-owned portable Python with -I -B -S. It activates only the committed
Runtime/ComfyUI/site-packages target and then executes ComfyUI/main.py.
"""
from __future__ import annotations
import argparse
import os
import runpy
import site
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", required=True)
    parser.add_argument("remainder", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()
    root = Path(parsed.root).resolve(strict=True)
    portable = (root / "Runtime/Desktop/python/python.exe").resolve(strict=True)
    target = (root / "Runtime/ComfyUI/site-packages").resolve(strict=True)
    main_py = (root / "ComfyUI/main.py").resolve(strict=True)
    if Path(sys.executable).resolve(strict=True) != portable:
        raise RuntimeError("ComfyUI isolated launcher requires the USB-owned portable Python")
    for key in ("PYTHONHOME", "PYTHONPATH"):
        os.environ.pop(key, None)
    os.environ.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "SETUPTOOLS_USE_DISTUTILS": "local",
    })
    site.addsitedir(str(target))
    sys.path.insert(0, str(main_py.parent))
    forwarded = list(parsed.remainder)
    if forwarded and forwarded[0] == "--":
        forwarded.pop(0)
    sys.argv = [str(main_py), *forwarded]
    os.chdir(main_py.parent)
    runpy.run_path(str(main_py), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
