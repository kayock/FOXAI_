from pathlib import Path
from core_v10.extension_manager import ExtensionManager

root = Path(__file__).resolve().parent
manager = ExtensionManager(root)

print("FOXAI CM v2.1 Extension Manifest System")
print("=======================================")
print()

print("Extensions:")
for ext in manager.list_extensions():
    print(f"- {ext.get('callsign')} | {ext.get('name')} | {ext.get('department')} | installed={ext.get('installed')}")
    print(f"  capabilities: {', '.join(ext.get('capabilities', []))}")
    print(f"  path: {ext.get('path')}")

print()
print("Health:")
health = manager.health()
for item in health.get("items", []):
    h = item.get("health", {})
    print(f"- {item.get('callsign')}: {h.get('status')} - {h.get('message')}")

print()
print("Invoke Search Shuttle:")
result = manager.invoke("ripgrep", "search", {"pattern": "ExtensionManager", "target": str(root)})
print("ok:", result.get("ok"))
print("message:", result.get("message"))
print((result.get("output") or "")[:2500])
