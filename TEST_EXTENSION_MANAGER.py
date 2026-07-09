from pathlib import Path
from core_v10.extension_manager import ExtensionManager

root = Path(__file__).resolve().parent
manager = ExtensionManager(root)

print("FOXAI Extension Manager v1")
print("==========================")
print()

print("Extensions:")
for ext in manager.list_extensions():
    print(f"- {ext.get('name')} [{ext.get('department')}] installed={ext.get('installed')} capabilities={', '.join(ext.get('capabilities', []))}")

print()
print("Health:")
health = manager.health()
for item in health.get("items", []):
    h = item.get("health", {})
    print(f"- {item.get('name')}: {h.get('status')} - {h.get('message')}")

print()
print("Find capability: code_search")
for ext in manager.find_capability("code_search"):
    print(f"- {ext.get('name')} ({ext.get('key')})")
