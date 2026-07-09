from pathlib import Path
from core_v10.capability_manager import CapabilityManager

root = Path(__file__).resolve().parent
manager = CapabilityManager(root)

print("FOXAI Capability Manager v1")
print("===========================")
print()

health = manager.health()
print("Total:", health["total"])
print("Installed:", health["installed"])
print("Reserved:", health["reserved"])
print()

for item in health["items"]:
    h = item["health"]
    print(f"{item['name']} [{item['category']}]")
    print(f"  key: {item['key']}")
    print(f"  reserved: {item['reserved']}")
    print(f"  installed: {item['installed']}")
    print(f"  health: {h.get('status')} - {h.get('message')}")
    print(f"  capabilities: {', '.join(item['capabilities'])}")
    print()

print("Find creative_writing:")
for item in manager.by_capability("creative_writing"):
    print("-", item["name"], "(reserved)" if item["reserved"] else "")
