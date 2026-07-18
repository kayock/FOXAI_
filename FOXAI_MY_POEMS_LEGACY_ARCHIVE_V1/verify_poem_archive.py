from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("VERIFY FAILED: expected foxai_web.py path")
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"VERIFY FAILED: file missing: {path}")
        return 3

    text = path.read_text(encoding="utf-8", errors="strict")
    required = {
        "My Poems page": "<section id=poemarchive class=page>",
        "archive loader": "function loadPoemArchive(",
        "archive backend": "def kayock_writer_poetry_archive():",
        "recording preparation": "def kayock_writer_poetry_recordings_prepare",
        "legacy settings": "def kayock_writer_poetry_legacy_update",
        "first Eric Voice milestone": "FIRST ERIC VOICE POEM",
        "recording slots": "Voice Legacy Recordings",
    }

    missing = [name for name, marker in required.items() if marker not in text]
    if missing:
        print("VERIFY FAILED: " + ", ".join(missing))
        return 4

    print("MY POEMS / LEGACY ARCHIVE VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
