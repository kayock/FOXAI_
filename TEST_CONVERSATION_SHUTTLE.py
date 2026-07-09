from pathlib import Path
from core_v10.conversation_shuttle import ConversationShuttle
from core_v10.mission_planner import MissionPlanner
from core_v10.capability_gap_analyzer import CapabilityGapAnalyzer

root = Path(__file__).resolve().parent
shuttle = ConversationShuttle(root)
planner = MissionPlanner(root)
gap = CapabilityGapAnalyzer(root)

print("FOXAI CM v3.4 - USS Conversation Shuttle")
print("========================================")
print()

print("Health:")
print(shuttle.health())
print()

tests = [
    ("Tell me a joke about a toaster joining Starfleet.", "Professor Kayock"),
    ("Professor Ada, explain what MissionBus does.", "Professor Ada"),
    ("Write a mythic sentence about the Engineering Fleet.", "Professor Tolkien"),
]

for prompt, professor in tests:
    print("PROMPT:", prompt)
    result = shuttle.chat(prompt=prompt, professor=professor)
    print("MISSION:", result["mission_id"])
    print("PROVIDER:", result["provider"], "| MODEL:", result["model"])
    print("ANSWER:", result["answer"])
    print()

print("Planner gap check after Conversation Shuttle:")
plan = planner.create_plan("Tell me a joke about a toaster joining Starfleet.")
report = gap.analyze_plan(plan)
print(gap.render_text(report))
