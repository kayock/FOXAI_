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
        "workshop panel": "Selected Lines / Stanza Workshop",
        "selection capture": "function capturePoemSelection()",
        "three-choice request": "function revisePoemSelection()",
        "selection-only apply": (
            "function applyPoemSelectionAlternative(index)"
        ),
        "revision backend": (
            "def kayock_writer_poetry_revise_selection"
        ),
        "revision endpoint": (
            "/api/writer/poetry/revise-selection"
        ),
        "compact ComfyUI dock": ".comfyopsdock[open]",
    }

    missing = [
        name for name, marker in required.items()
        if marker not in text
    ]
    if missing:
        print("VERIFY FAILED: " + ", ".join(missing))
        return 4

    print("POEM SELECTION WORKSHOP VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
