from pathlib import Path
import sys

path=Path(sys.argv[1])
text=path.read_text(encoding="utf-8")
markers=[
    "Analysis and revision are separate.",
    "Revision target for the Workshop",
    "Recheck Poem",
    "function updateRhymeTargetPreview()",
    "The poem has not changed, so the analysis is unchanged.",
]
missing=[m for m in markers if m not in text]
if missing:
    print("VERIFY FAILED:", ", ".join(missing))
    raise SystemExit(4)
print("RHYME COACH CLARITY FIX VERIFIED")
