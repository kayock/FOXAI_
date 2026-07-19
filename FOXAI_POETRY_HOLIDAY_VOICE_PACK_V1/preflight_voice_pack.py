from pathlib import Path
import hashlib
import sys

path=Path(sys.argv[1])
if not path.is_file():
    print("PREFLIGHT FAILED: live WebUI file is missing.")
    raise SystemExit(2)

actual=hashlib.sha256(path.read_bytes()).hexdigest()
expected_source="469154f20f33dafa53ed7b17409cb0dcac755174b43eeae4ce25b3b263b30c24"
expected_updated="768dc10c2f4b2186f4b5fad0109d35f091c8585f0b2a6eeafc4081cb438a5601"

if actual==expected_updated:
    print("VOICE PACK ALREADY INSTALLED")
    raise SystemExit(20)

if actual!=expected_source:
    print("PREFLIGHT STOPPED SAFELY")
    print("The live foxai_web.py differs from the verified source used")
    print("to build this pack. No files were changed.")
    print("Live SHA-256:",actual)
    print("Expected SHA-256:",expected_source)
    raise SystemExit(3)

print("PREFLIGHT PASSED")
print("Live SHA-256:",actual)
