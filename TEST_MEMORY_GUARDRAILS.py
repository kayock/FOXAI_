from pathlib import Path
from core_v10.foxai_core import FoxAICore

root = Path(__file__).resolve().parent
core = FoxAICore(root)

project = core.create_project("FOXAI_Memory_Test")
mission = core.mission("FOXAI_Memory_Test", professor="fox", model_name="guardrail-test")

mission.memory.add_item("fact", "FOXAI is a portable Star Trek Engineering Console for Makers, Builders, and Explorers.")
mission.memory.add_item("decision", "All future LLM calls should route through MissionBus.dispatch().")
mission.memory.add_item("objective", "Build grounded Mission Intelligence that does not invent unstored details.")
mission.memory.add_item("task", "Create a Mission Intelligence panel in the web UI.")
mission.memory.add_item("fact", "Novel Forge is reserved but not installed yet.")

print("FOXAI Memory Guardrail Test")
print("===========================")
print()
print("Project:", project["name"])
print("Memory folder:", mission.memory.memory_root)
print()
print(mission.memory.build_remembered_only_context("Agent Fox", "guardrail-test")[:5000])
print()
print("PASS if the report contains only stored memory and says unknown by default.")
