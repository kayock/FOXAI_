from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    required = {
        "exact whitespace helper": "def _writer_exact_text",
        "exact poem validation": (
            "poem=_writer_exact_text(d.get('poem'),32000)"
        ),
        "verified positions": "'verified_selection_start':start",
        "browser position sync": "d.verified_selection_start",
        "workshop preserved": "Selected Lines / Stanza Workshop",
        "archive preserved": "My Poems",
        "Eric voice preserved": "Eric — Poet/Narrator",
    }
    missing = [
        name for name, marker in required.items()
        if marker not in text
    ]
    if missing:
        print("VERIFY FAILED: " + ", ".join(missing))
        return 4
    print("POEM SELECTION MATCH FIX VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
