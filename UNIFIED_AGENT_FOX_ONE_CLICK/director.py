from core.security_containment import (
    authorize_department_route,
    is_explicit_engineer_command,
    new_airlock_correlation_id,
    record_authorization_decision,
)

IMAGE_EXPLICIT_TRIGGERS = [
    "/image ",
    "draw",
    "paint",
    "render",
    "illustrate",
    "visualize",
    "generate an image",
    "generate a picture",
    "create an image",
    "create a picture",
    "make an image",
    "make a picture",
    "show me a picture",
    "picture of",
    "image of",
]

IMAGE_STYLE_TERMS = [
    "macro photograph",
    "photograph",
    "photo",
    "portrait",
    "cinematic",
    "depth of field",
    "bokeh",
    "8k",
    "4k",
    "ultra detailed",
    "highly detailed",
    "award-winning",
    "masterpiece",
    "concept art",
    "digital painting",
    "steampunk",
    "cyberpunk",
    "fantasy art",
    "rendered",
    "volumetric lighting",
    "dramatic lighting",
    "sharp focus",
    "wide angle",
    "close-up",
    "close up",
]

LIBRARY_TRIGGERS = [
    "search my library",
    "search library",
    "find documents",
    "find docs",
    "look in iron library",
    "check iron library",
    "iron library",
]

ENGINEER_TRIGGERS = [
    # Investigation / kernel reasoning
    "investigate",
    "investigation",
    "investigation engine",
    "ranked evidence",
    "recommendation",
    "engineering assessment",
    "heuristic",
    "mission router",
    "kernel",
    "boot report",
    "service registry",
    "timeout",

    # Scanning / indexing
    "scan for new files",
    "scan new files",
    "reindex project",
    "scan project files",
    "project index",

    # Architecture / review
    "review your code",
    "scan your code",
    "scan your own code",
    "review your own code",
    "architecture review",
    "technical debt",
    "dependency graph",
    "runtime graph",
    "code review",
    "refactor",

    # Build / forge
    "forge",
    "forge sprint",
    "build component",
    "generate implementation",

    # Errors / debugging
    "debug",
    "fix this code",
    "python error",
    "traceback",
    "syntaxerror",
    "indentationerror",
    "module not found",
]


def _score_terms(lowered, terms, points):
    score = 0
    hits = []
    for term in terms:
        if term in lowered:
            score += points
            hits.append(term)
    return score, hits


def classify(
    text,
    actor="operator",
    operator_approved=False,
    *,
    correlation_id=None,
    mission_id=None,
    audit=True,
):
    lowered = text.lower().strip()
    correlation_id = correlation_id or new_airlock_correlation_id()
    mission_id = (mission_id or "").strip()

    scores = {
        "chat": 1,
        "red_canvas": 0,
        "iron_library": 0,
        "engineer": 0,
    }

    reasons = {
        "chat": ["default conversational fallback"],
        "red_canvas": [],
        "iron_library": [],
        "engineer": [],
    }

    # Unified Agent Fox chat:
    # Ordinary language remains in the main Agent Fox conversation.
    # A department is selected only by an explicit slash command.
    if lowered.startswith("/image "):
        scores["red_canvas"] = 100
        reasons["red_canvas"].append("explicit /image command")
    elif is_explicit_engineer_command(text):
        scores["engineer"] = 100
        reasons["engineer"].append("explicit operator Engineer command")
    else:
        reasons["chat"].append("normal message remains in unified Agent Fox chat")

    selected = max(scores, key=scores.get)

    authorization = authorize_department_route(
        actor,
        "engineering_airlock" if selected == "engineer" else selected,
        "route",
        operator_approved=operator_approved,
    )
    authorization_data = authorization.to_dict()
    audit_receipt = None

    sensitive_attempt = (
        selected == "engineer"
        or is_explicit_engineer_command(text)
    )
    if sensitive_attempt and audit:
        audit_receipt = record_authorization_decision(
            authorization,
            correlation_id=correlation_id,
            mission_id=mission_id,
        )
        if not audit_receipt.get("verified"):
            authorization_data = {
                **authorization_data,
                "allowed": False,
                "reason": (
                    "The security audit receipt could not be verified."
                ),
                "policy_source": "audit_fail_closed",
            }

    if selected == "engineer" and not authorization_data["allowed"]:
        scores["engineer"] = -1000
        selected = "chat"
        reasons["chat"].append(
            f"Engineering Airlock denied: "
            f"{authorization_data['reason']}"
        )

    return {
        "agent": selected,
        "payload": text[7:].strip() if lowered.startswith("/image ") and selected == "red_canvas" else text,
        "scores": scores,
        "reasons": reasons[selected],
        "authorization": authorization_data,
        "correlation_id": correlation_id,
        "mission_id": mission_id,
        "audit_receipt": audit_receipt,
    }


def direct(
    text,
    actor="operator",
    operator_approved=False,
    *,
    correlation_id=None,
    mission_id=None,
    audit=True,
):
    result = classify(
        text,
        actor=actor,
        operator_approved=operator_approved,
        correlation_id=correlation_id,
        mission_id=mission_id,
        audit=audit,
    )
    return {
        "agent": result["agent"],
        "payload": result["payload"],
        "scores": result["scores"],
        "reasons": result["reasons"],
        "authorization": result["authorization"],
        "correlation_id": result["correlation_id"],
        "mission_id": result["mission_id"],
        "audit_receipt": result["audit_receipt"],
    }
