from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    required = {
        "strict replacement prompt": (
            "OUTPUT ONLY THE REPLACEMENT LINES. "
            "NEVER RETURN THE WHOLE POEM."
        ),
        "compact Eric guide": (
            "def _poetry_compact_eric_voice_prompt"
        ),
        "line-count rejection": "len(lines)>max_line_count",
        "scope rejection response": "'scope_rejected':True",
        "open archive preserved": "My Poems",
        "selection workshop preserved": (
            "Selected Lines / Stanza Workshop"
        ),
    }
    missing = [
        name for name, marker in required.items()
        if marker not in text
    ]
    if missing:
        print("VERIFY FAILED: " + ", ".join(missing))
        return 4
    print("POEM SELECTION SCOPE FIX VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
