from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    required = {
        "open workflow": "function openSavedPoemInStudio(",
        "open original": "Open Original",
        "open polished": "Open Polished",
        "duplicate workflow": "Duplicate as New Poem",
        "prompt display": "Saved Prompt &amp; Creation Fields",
        "imagery save": "f'imagery:",
        "length save": "f'length:",
        "opening-line save": "f'opening_line:",
        "full prompt snapshot": "f'prompt_fields:",
        "source lineage": "'opened_from':_writer_text",
        "selection workshop preserved": (
            "Selected Lines / Stanza Workshop"
        ),
        "My Poems preserved": "First Eric Voice Milestone",
    }
    missing = [
        name for name, marker in required.items()
        if marker not in text
    ]
    if missing:
        print("VERIFY FAILED: " + ", ".join(missing))
        return 4
    print("OPEN POEM PROJECT v1 VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
