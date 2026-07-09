from __future__ import annotations

OFFICER = {
    "name": "Chief Engineer Ada",
    "callsign": "Ada",
    "role": "Chief Engineer",
    "motto": "Clarity first. Then automation.",
    "responsibilities": [
        "Repair Bay coordination",
        "Code quality",
        "Architecture checks",
        "Build readiness",
        "Engineering reports",
    ],
}


def briefing() -> str:
    return (
        "Chief Engineer Ada: Engineering is responsible for keeping FOXAI "
        "stable, repairable, and ready for launch."
    )
