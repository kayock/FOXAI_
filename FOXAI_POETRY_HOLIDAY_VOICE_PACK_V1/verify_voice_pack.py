from pathlib import Path
import hashlib
import sys

path=Path(sys.argv[1])
text=path.read_text(encoding="utf-8")
actual=hashlib.sha256(path.read_bytes()).hexdigest()
expected="768dc10c2f4b2186f4b5fad0109d35f091c8585f0b2a6eeafc4081cb438a5601"

required={
    "pack marker":"# POETRY_VOICE_PACK_V1_START",
    "Poe profile":"Edgar Allan Poe — Gothic Lyric",
    "West Coast profile":"Beneath the Beats — West Coast Voice",
    "Gunslinger profile":"Dust and Duty — Last Gunslinger Voice",
    "Frankenstein profile":"The Forsaken Flame — Exile’s Voice",
    "dynamic controls":"POETRY_VOICE_PROFILE_UI",
    "guarded stanza workflow":"maximum_attempts=6",
    "safe alternatives":"Create Up to 3 Safe Alternatives",
}
missing=[
    name
    for name, marker in required.items()
    if marker not in text
]
if actual!=expected:
    print("VERIFY FAILED: updated file hash did not match.")
    print("Actual:",actual)
    print("Expected:",expected)
    raise SystemExit(4)
if missing:
    print("VERIFY FAILED:",", ".join(missing))
    raise SystemExit(5)

print("HOLIDAY VOICE PACK VERIFIED")
for name in required:
    print("  PASS",name)
print("SHA-256:",actual)
