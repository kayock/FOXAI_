from pathlib import Path
from core_v10.extension_commissioner import commission_known_extensions
from core_v10.extension_manager import ExtensionManager

root = Path(__file__).resolve().parent

print("FOXAI CM v2.2a Shuttle Pod Commissioning FIX")
print("============================================")
print()

result = commission_known_extensions(root, overwrite=False)

print("Inventory executables:", result["inventory_count"])
print()

print("Created:")
for item in result["created"]:
    print(f"- {item['callsign']} ({item['key']}) -> {item['path']}")
if not result["created"]:
    print("- None")

print()
print("Skipped:")
for item in result["skipped"]:
    print(f"- {item['name']} ({item['key']}): {item['reason']}")
if not result["skipped"]:
    print("- None")

print()
print("Missing signatures:")
for item in result["missing"]:
    print(f"- {item['name']} ({item['key']}): {item['reason']}")
if not result["missing"]:
    print("- None")

print()
print("Registered Extensions After Commissioning:")
manager = ExtensionManager(root)
for ext in manager.list_extensions():
    print(f"- {ext.get('callsign')} | {ext.get('department')} | installed={ext.get('installed')} | {', '.join(ext.get('capabilities', []))}")

print()
print("Health:")
health = manager.health()
for item in health.get("items", []):
    h = item.get("health", {})
    print(f"- {item.get('callsign')}: {h.get('status')} - {h.get('message')}")
