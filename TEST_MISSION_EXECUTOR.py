from pathlib import Path
from core_v10.mission_executor import MissionExecutor

root = Path(__file__).resolve().parent
executor = MissionExecutor(root)

tests = [
    "Tell me a joke about a toaster joining Starfleet.",
    "Professor Ada, explain what MissionBus does.",
    "Write a mythic sentence about the Engineering Fleet.",
]

print("FOXAI CM v3.7 - Mission Execution Engine Test")
print("=============================================")
print()

for request in tests:
    print("REQUEST:", request)
    report = executor.execute(request)
    print(executor.render_text(report))
    print("-" * 72)
