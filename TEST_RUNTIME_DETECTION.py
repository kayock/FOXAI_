from pathlib import Path
from core_v10.bridge_officers import BridgeOfficerRegistry

root = Path(__file__).resolve().parent
registry = BridgeOfficerRegistry(root)

report = registry.assignment_report({
    "mission_type": "General Conversation",
    "department": "Academy",
    "professor": "Professor Kayock",
})

print(registry.render_text(report))
print()
print("Runtime detection:")
print(report.get("runtime_detection"))
