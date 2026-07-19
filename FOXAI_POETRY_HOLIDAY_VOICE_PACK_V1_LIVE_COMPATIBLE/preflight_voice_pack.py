from pathlib import Path
import hashlib
import sys

path=Path(sys.argv[1])
actual=hashlib.sha256(path.read_bytes()).hexdigest()
source="e29aaee218dbcee486c76987308164660375ce360df04f4437692f0d168cb297"
updated="e939e9a43b1705f3b1fa28e294d77261429d7dbecc516cae469a203bcebac296"

if actual==updated:
    print("VOICE PACK ALREADY INSTALLED")
    raise SystemExit(20)
if actual!=source:
    print("PREFLIGHT STOPPED SAFELY")
    print("No files were changed.")
    print("Live SHA-256:",actual)
    print("Expected SHA-256:",source)
    raise SystemExit(3)

print("PREFLIGHT PASSED")
print("This package exactly matches the installed Rhyme Coach build.")
