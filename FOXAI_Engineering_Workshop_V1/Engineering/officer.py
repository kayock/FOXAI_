from __future__ import annotations

OFFICER = {
    "name": "Chief Engineer Ada",
    "callsign": "Ada",
    "role": "Chief Engineer",
    "motto": "Clarity first. Then automation.",
    "responsibilities": [
        "Engineering Workshop coordination",
        "Repair Bay coordination",
        "Controlled implementation and rollback",
        "Code quality",
        "Architecture checks",
        "Build readiness",
        "Evidence-backed engineering reports",
    ],
}


def briefing() -> str:
    return (
        "Chief Engineer Ada: Engineering begins read-only, changes only an approved "
        "exact plan, validates the result, and restores the snapshot when validation fails."
    )
