from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    required = {
        "coach panel": "Rhyme &amp; Rhythm Coach",
        "analysis action": "function analyzePoemRhymeRhythm()",
        "syllable estimate": "function poetryEstimateWordSyllables(",
        "rhyme-key estimate": "function poetryRhymeKey(",
        "stanza workshop bridge": (
            "function sendRhymeStanzaToWorkshop("
        ),
        "AABB target": "Couplets — AABB",
        "ABAB target": "Alternating — ABAB",
        "honest approximation note": (
            "Syllable and rhyme results are approximate"
        ),
        "open-project workflow preserved": (
            "function openSavedPoemInStudio("
        ),
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
    print("RHYME & RHYTHM COACH v1 VERIFIED")
    for name in required:
        print(f"  PASS  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
