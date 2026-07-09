from pathlib import Path
from core_v10.mission_bus import MissionBus

root = Path(__file__).resolve().parent
bus = MissionBus(root)

print("FOXAI Mission Bus Phase 2")
print("=========================")

for command, payload in [
    ("ping", {}),
    ("professors.list", {}),
    ("projects.create", {"name": "FOXAI_Mission_Bus_Test"}),
    ("memory.add", {
        "project": "FOXAI_Mission_Bus_Test",
        "kind": "objective",
        "text": "Prove that Mission Bus can route commands through FOXAI Core."
    }),
    ("memory.add", {
        "project": "FOXAI_Mission_Bus_Test",
        "kind": "decision",
        "text": "All future departments should call MissionBus.dispatch()."
    }),
    ("memory.context", {
        "project": "FOXAI_Mission_Bus_Test",
        "professor": "fox",
        "model_name": "smoke-test"
    }),
]:
    print()
    print("COMMAND:", command)
    result = bus.dispatch(command, payload)
    if command == "memory.context" and result.get("ok"):
        print(result["context"][:2200])
    else:
        print(result)

print()
print("Smoke test complete.")
