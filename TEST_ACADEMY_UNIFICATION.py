from pathlib import Path
import json

from core_v10.academy import list_professors, get_professor, academy_status

root = Path(__file__).resolve().parent
outbox = root / "OpsBridge" / "outbox"
outbox.mkdir(parents=True, exist_ok=True)

report = {
    "ok": True,
    "test": "Academy Unification",
    "list_professors_count": len(list_professors()),
    "fox": get_professor("fox").name,
    "ada": get_professor("ada").name,
    "sagan": get_professor("Professor Sagan").name,
    "academy_status": academy_status(),
}

(outbox / "academy_unification_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

print("FOXAI Academy Unification Test")
print("==============================")
print()
print(f"OK: {report['ok']}")
print(f"Professors: {report['list_professors_count']}")
print(f"Fox: {report['fox']}")
print(f"Ada: {report['ada']}")
print(f"Sagan: {report['sagan']}")
print()
print("Report:")
print(outbox / "academy_unification_report.json")
