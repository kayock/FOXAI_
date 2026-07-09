from pathlib import Path
import json

root = Path(__file__).resolve().parent
manifest = root / "Extensions" / "Academy" / "Conversation" / "extension.json"

if not manifest.exists():
    print("Conversation manifest not found.")
    print("Run INSTALL_CONVERSATION_SHUTTLE.bat first.")
    raise SystemExit(1)

data = json.loads(manifest.read_text(encoding="utf-8"))
data["kind"] = "service"
data["executables"] = []
data["status"] = "ready"
manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

print("Conversation manifest patched as kind=service.")
print(manifest)
