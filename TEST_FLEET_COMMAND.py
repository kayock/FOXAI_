from pathlib import Path
from core_v10.fleet_command import FleetCommand

root = Path(__file__).resolve().parent
command = FleetCommand(root)

tests = [
    "Tell me a joke about a toaster joining Starfleet.",
    "Professor Ada, explain what MissionBus does.",
    "Write a mythic sentence about the Engineering Fleet.",
]

print("FOXAI CM v4.0 - Fleet Command Foundation Test")
print("=============================================")
print()

for request in tests:
    print("ORDER:", request)
    report = command.command(request)
    print(command.render_text(report))
    print("-" * 72)
