from pathlib import Path
from core_v10.mission_planner import MissionPlanner

root = Path(__file__).resolve().parent
planner = MissionPlanner(root)

tests = [
    "Professor Ada, find every place MissionBus is used.",
    "Compare today's FOXAI folder with yesterday's backup.",
    "Find where I put my GGUF models.",
    "Parse the code structure and find classes.",
    "Tell me a joke about a toaster joining Starfleet.",
]

for request in tests:
    plan = planner.create_plan(request, professor="Professor Ada")
    print(planner.render_plan_text(plan))
    print("\n" + "-" * 72 + "\n")
