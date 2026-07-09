from pathlib import Path
from core_v10.extension_manager import ExtensionManager
from core_v10.fleet_registry import FleetRegistry

root = Path(__file__).resolve().parent

print("FOXAI CM v2.3b Lifecycle Guard Test")
print("===================================")
print()

manager = ExtensionManager(root)

print("Passive health test:")
health = manager.passive_health()
print("mode:", health.get("mode"))
print("total:", health.get("total"))
for item in health.get("items", []):
    h = item.get("health", {})
    print(f"- {item.get('callsign')}: {h.get('status')} - {h.get('message')}")

print()
print("Fleet Registry refresh:")
fleet = FleetRegistry(root)
data = fleet.refresh()
summary = fleet.summary(data)
print("mode:", summary.get("mode"))
print("total:", summary.get("total"))
print("states:", summary.get("states"))

print()
print("If no GUI apps opened, lifecycle guard passed.")
