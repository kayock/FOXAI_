from pathlib import Path
from core_v10.mission_planner import MissionPlanner
from core_v10.capability_gap_analyzer import CapabilityGapAnalyzer

root = Path(__file__).resolve().parent
planner = MissionPlanner(root)
analyzer = CapabilityGapAnalyzer(root)

tests = [
    "Tell me a joke about a toaster joining Starfleet.",
    "Write chapter three where Anthony learns the prophecy.",
    "Draw me a logo for the Engineering Fleet.",
    "Diagnose why the browser crashes.",
    "Professor Ada, find every place MissionBus is used.",
]

for request in tests:
    plan = planner.create_plan(request)
    report = analyzer.analyze_plan(plan)
    print(analyzer.render_text(report))
    print("-" * 72)
