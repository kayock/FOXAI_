from pathlib import Path
from core_v10.mission_bus import MissionBus

root = Path(__file__).resolve().parent
bus = MissionBus(root)

print("FOXAI Capability Manager v2 / Mission Bus Test")
print("==============================================")
print()

tests = [
    ("ping", {}),
    ("capabilities.list", {}),
    ("capabilities.health", {}),
    ("capabilities.find", {"capability": "creative_writing"}),
    ("capabilities.find", {"capability": "local_llm"}),
    ("capabilities.launch", {"key": "novel_forge"}),
]

for command, payload in tests:
    print("COMMAND:", command, payload)
    result = bus.dispatch(command, payload)
    if command == "capabilities.list" and result.get("ok"):
        for item in result["capabilities"]:
            print(f"- {item['name']} | {item['category']} | reserved={item['reserved']} | installed={item['installed']} | py_adapter={item.get('has_python_adapter')}")
    elif command == "capabilities.health" and result.get("ok"):
        print("total:", result["total"], "installed:", result["installed"], "reserved:", result["reserved"])
    elif command == "capabilities.find" and result.get("ok"):
        for item in result["matches"]:
            print(f"- {item['name']} ({item['key']}) reserved={item['reserved']}")
    else:
        print(result)
    print()

print("Expected:")
print("- Novel Forge should be reserved/not installed.")
print("- Aider should be reserved/not installed.")
print("- Iron Library should be installed if Library folder exists.")
print("- llama server may be online/offline depending whether model server is running.")
