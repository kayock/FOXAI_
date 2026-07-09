from pathlib import Path
from core_v10.fleet_registry import FleetRegistry
from core_v10.mission_planner import MissionPlanner
from core_v10.capability_gap_analyzer import CapabilityGapAnalyzer

root = Path(__file__).resolve().parent

fleet = FleetRegistry(root)
planner = MissionPlanner(root)
gap = CapabilityGapAnalyzer(root)

print("FOXAI CM v3.4a - Fleet Synchronization Test")
print("===========================================")
print()

data = fleet.refresh()
summary = fleet.summary(data)
print("Fleet total:", summary.get("total"))
print("Fleet states:", summary.get("states"))
print()

conversation = None
for s in (data.get("shuttles") or {}).values():
    if s.get("key") == "conversation":
        conversation = s
        break

print("Conversation Shuttle in Fleet Registry:")
print(conversation if conversation else "NOT FOUND")
print()

plan = planner.create_plan("Tell me a joke about a toaster joining Starfleet.")
report = gap.analyze_plan(plan)
print(gap.render_text(report))

print()
if any(g.get("capability") == "general_reasoning" and g.get("available") for g in report.get("gaps", [])):
    print("PASS: general_reasoning is now provided by the Fleet Registry.")
else:
    print("FAIL: general_reasoning still missing. Re-run INSTALL_CONVERSATION_SHUTTLE.bat, then this test.")
