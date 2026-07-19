from pathlib import Path
import hashlib
import sys

path=Path(sys.argv[1])
text=path.read_text(encoding="utf-8")
actual=hashlib.sha256(path.read_bytes()).hexdigest()
expected="e939e9a43b1705f3b1fa28e294d77261429d7dbecc516cae469a203bcebac296"

required=[
    "# POETRY_VOICE_PACK_V1_START",
    "Edgar Allan Poe — Gothic Lyric",
    "Beneath the Beats — West Coast Voice",
    "Dust and Duty — Last Gunslinger Voice",
    "The Forsaken Flame — Exile’s Voice",
    "POETRY_VOICE_PROFILE_UI",
    "Analysis and revision are separate.",
]
if actual!=expected:
    print("VERIFY FAILED: updated hash mismatch.")
    raise SystemExit(4)
missing=[item for item in required if item not in text]
if missing:
    print("VERIFY FAILED:",", ".join(missing))
    raise SystemExit(5)

print("HOLIDAY VOICE PACK VERIFIED")
print("Current Rhyme Coach workflow preserved.")
