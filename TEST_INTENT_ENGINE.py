from pathlib import Path
from core_v10.intent_engine import IntentEngine
from core_v10.mission_planner import MissionPlanner

root = Path(__file__).resolve().parent
engine = IntentEngine()
planner = MissionPlanner(root)

tests = [
    "Professor Ada, find every place MissionBus is used.",
    "Compare today's FOXAI folder with yesterday's backup.",
    "Find where I put my GGUF models.",
    "Parse the code structure and find classes.",
    "Tell me a joke about a toaster joining Starfleet.",
    "Write chapter three where Anthony learns the prophecy.",
    "Draw me a logo for the Engineering Fleet.",
    "Research the Python sqlite3 docs.",
    "Diagnose why the browser crashes.",
]

print("FOXAI Mission Planner v3.1 — Intent Engine")
print("==========================================")
print()

for request in tests:
    intent = engine.classify(request)
    print("REQUEST:", request)
    print("INTENT:", intent["mission_type"], "|", intent["department"], "|", intent["lead_professor"], "| confidence", intent["confidence"])
    print("CAPABILITIES:", ", ".join(intent["required_capabilities"]))
    print()

print("\n" + "=" * 72 + "\n")

for request in tests[:5]:
    plan = planner.create_plan(request)
    print(planner.render_plan_text(plan))
    print("\n" + "-" * 72 + "\n")
