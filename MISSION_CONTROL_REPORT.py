from pathlib import Path
from core_v10.mission_control_report import MissionControlReport

root = Path(__file__).resolve().parent
report = MissionControlReport(root)

request = " ".join(__import__("sys").argv[1:]).strip()
if not request:
    request = "Professor Ada, find every place MissionBus is used."

report.render(request)
