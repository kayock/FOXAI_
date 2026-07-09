from pathlib import Path
from core_v10.foxai_core import FoxAICore

root = Path(__file__).resolve().parent
core = FoxAICore(root)

print("FOXAI root:", root)
print("\nProfessors:")
for p in core.list_professors():
    status = "INSTALLED" if p["installed"] else "RESERVED / NOT INSTALLED"
    print(f"- {p['name']} ({p['college']}) [{status}]")

project = core.create_project("FOXAI_v10_Test")
print("\nProject created:", project)

mission = core.mission("FOXAI_v10_Test", professor="fox", model_name="test-model")
mission.memory.add_item("objective", "Prove FOXAI Core v10 can create disk-backed memory.")
mission.memory.add_item("decision", "Novel Forge is reserved but not installed yet.")
mission.memory.event("Core v10 smoke test completed.")

print("\nMemory folder:", mission.memory.memory_root)
print("Created files:")
for p in sorted(mission.memory.memory_root.iterdir()):
    print("-", p.name)

print("\nMission Intelligence Preview:\n")
print(mission.memory.build_context("Agent Fox", "test-model")[:2000])
