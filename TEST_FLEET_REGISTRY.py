from pathlib import Path
from core_v10.fleet_registry import FleetRegistry

root = Path(__file__).resolve().parent
fleet = FleetRegistry(root)

print("FOXAI CM v2.3 Fleet Registry")
print("============================")
print()

result = fleet.scan_and_commission()
commission = result["commission"]
summary = result["summary"]

print("Commissioning:")
print("  Inventory executables:", commission.get("inventory_count"))
print("  Created:", len(commission.get("created", [])))
for item in commission.get("created", []):
    print(f"    + {item['callsign']} ({item['key']})")
print("  Skipped:", len(commission.get("skipped", [])))
for item in commission.get("skipped", []):
    print(f"    = {item['name']} ({item['key']}): {item['reason']}")
print("  Missing:", len(commission.get("missing", [])))
for item in commission.get("missing", []):
    print(f"    - {item['name']} ({item['key']}): {item['reason']}")

print()
print("Fleet Summary:")
print("  Total:", summary["total"])
print("  States:", summary["states"])
print("  Updated:", summary["updated"])

print()
print("Departments:")
for dept, shuttles in summary["departments"].items():
    print(f"\n{dept}:")
    for s in shuttles:
        print(f"  - {s['callsign']} [{s['service_state']}]")
        print(f"    capabilities: {', '.join(s.get('capabilities', []))}")
        print(f"    health: {s.get('health_message')}")
        if s.get("path"):
            print(f"    path: {s.get('path')}")

print()
print("Fleet registry saved to:")
print(fleet.registry_path)
