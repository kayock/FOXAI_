from pathlib import Path
from core_v10.extension_manager import ExtensionManager

root = Path(__file__).resolve().parent
manager = ExtensionManager(root)

print("FOXAI Extension Manager v2")
print("==========================")
print()

print("Executable Inventory Sample:")
inventory = manager.executable_inventory()
print("Total executables found:", len(inventory))
for item in inventory[:20]:
    print(f"- {item['name']} :: {item['path']}")

print()
print("Extensions:")
for ext in manager.list_extensions():
    print(f"- {ext.get('name')} [{ext.get('department')}] installed={ext.get('installed')} path={ext.get('path')}")

print()
print("Health:")
health = manager.health()
for item in health.get("items", []):
    h = item.get("health", {})
    print(f"- {item.get('name')}: {h.get('status')} - {h.get('message')}")
    if h.get("path"):
        print(f"  path: {h.get('path')}")

print()
print("Find capability: code_search")
for ext in manager.find_capability("code_search"):
    print(f"- {ext.get('name')} ({ext.get('key')})")

print()
print("Invoke ripgrep search for MissionBus in FOXAI root:")
result = manager.invoke("ripgrep", "search", {"pattern": "MissionBus", "target": str(root)})
print("ok:", result.get("ok"))
print("message:", result.get("message"))
print((result.get("output") or "")[:2000])
