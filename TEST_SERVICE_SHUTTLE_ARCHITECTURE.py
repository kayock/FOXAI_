from pathlib import Path
from core_v10.fleet_registry import FleetRegistry
from core_v10.mission_planner import MissionPlanner
from core_v10.capability_gap_analyzer import CapabilityGapAnalyzer

root = Path(__file__).resolve().parent
fleet = FleetRegistry(root)
planner = MissionPlanner(root)
gap = CapabilityGapAnalyzer(root)

print("FOXAI CM v3.4b - Service Shuttle Architecture Test")
print("==================================================")
print()

data = fleet.refresh()
summary = fleet.summary(data)
print("Fleet total:", summary.get("total"))
print("Fleet states:", summary.get("states"))
print("Fleet kinds:", summary.get("kinds"))
print()

conversation = (data.get("shuttles") or {}).get("conversation")
print("Conversation Shuttle:")
print(conversation)
print()

plan = planner.create_plan("Tell me a joke about a toaster joining Starfleet.")
report = gap.analyze_plan(plan)
print(gap.render_text(report))

print()
if conversation and conversation.get("service_state") == "Operational":
    print("PASS: Conversation Shuttle is operational as a service.")
else:
    print("FAIL: Conversation Shuttle is not operational.")

if any(g.get("capability") == "general_reasoning" and g.get("available") for g in report.get("gaps", [])):
    print("PASS: general_reasoning is available from Fleet Registry.")
else:
    print("FAIL: general_reasoning still missing.")
