from pathlib import Path
from core_v10.fleet_command_bridge import FleetCommandBridge

root = Path(__file__).resolve().parent
bridge = FleetCommandBridge(root)

tests = [
    "Tell me a joke about a toaster joining Starfleet.",
    "Professor Ada, explain what MissionBus does.",
    "Write a mythic sentence about the Engineering Fleet.",
]

print("FOXAI CM v4.1 - Bridge Officer Framework Test")
print("=============================================")
print()

for request in tests:
    print("ORDER:", request)
    report = bridge.command(request)
    print(bridge.render_text(report))
    print("-" * 72)
