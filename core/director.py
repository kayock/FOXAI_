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
    # Explicit department call
    "engineer",

    # Investigation / kernel reasoning
    "investigate",
    "investigation",
    "investigation engine",
    "evidence",
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


def classify(text):
    lowered = text.lower().strip()

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

    if lowered.startswith("/image "):
        scores["red_canvas"] += 100
        reasons["red_canvas"].append("explicit /image command")

    library_score, library_hits = _score_terms(lowered, LIBRARY_TRIGGERS, 40)
    scores["iron_library"] += library_score
    reasons["iron_library"].extend([f"library trigger: {hit}" for hit in library_hits])

    engineer_score, engineer_hits = _score_terms(lowered, ENGINEER_TRIGGERS, 35)
    scores["engineer"] += engineer_score
    reasons["engineer"].extend([f"engineering trigger: {hit}" for hit in engineer_hits])

    explicit_image_score, explicit_image_hits = _score_terms(lowered, IMAGE_EXPLICIT_TRIGGERS, 45)
    scores["red_canvas"] += explicit_image_score
    reasons["red_canvas"].extend([f"image trigger: {hit}" for hit in explicit_image_hits])

    style_score, style_hits = _score_terms(lowered, IMAGE_STYLE_TERMS, 12)
    scores["red_canvas"] += style_score
    reasons["red_canvas"].extend([f"visual style term: {hit}" for hit in style_hits])

    # Quoted art prompts often arrive without "draw" or "image"; boost if they look like a pure visual prompt.
    visual_prompt_markers = len(style_hits)
    if visual_prompt_markers >= 3 and len(lowered) > 80:
        scores["red_canvas"] += 35
        reasons["red_canvas"].append("long visual prompt with multiple art/photo descriptors")

    # Prevent broad phrases like "make me laugh" from becoming image requests.
    if "make me laugh" in lowered or "make me a plan" in lowered:
        scores["red_canvas"] -= 50
        reasons["chat"].append("common non-image phrase detected")

    selected = max(scores, key=scores.get)

    return {
        "agent": selected,
        "payload": text[7:].strip() if lowered.startswith("/image ") and selected == "red_canvas" else text,
        "scores": scores,
        "reasons": reasons[selected],
    }


def direct(text):
    result = classify(text)
    return {
        "agent": result["agent"],
        "payload": result["payload"],
        "scores": result["scores"],
        "reasons": result["reasons"],
    }
