from core.paths import BASE

SEARCH_ROOTS = [
    BASE,
    BASE / "Library",
    BASE / "core",
    BASE / "ui",
    BASE / "agents",
    BASE / "Prompts",
]

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".ini",
    ".bat",
    ".ps1",
    ".yml",
    ".yaml",
    ".html",
    ".css",
    ".js",
}

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "ComfyUI",
    "Models",
    "Engine",
    "Backups",
    "Red Canvas",
    "Mission Archive",
    "Memory",
    "Outputs",
}


def ensure_library():
    folders = [
        BASE / "Library",
        BASE / "Library" / "Physics",
        BASE / "Library" / "DnD",
        BASE / "Library" / "Programming",
        BASE / "Library" / "Manuals",
        BASE / "Library" / "Research",
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def should_ignore(path):
    return any(part in IGNORE_DIRS for part in path.parts)


def list_documents():
    ensure_library()
    docs = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if should_ignore(path):
                continue

            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                docs.append(path)

    return sorted(set(docs))


def search_documents(query, max_results=50):
    query = query.lower().strip()
    if not query:
        return []

    results = []

    for path in list_documents():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lowered = text.lower()

        if query in lowered or path.name.lower().find(query) >= 0:
            index = lowered.find(query)
            if index == -1:
                index = 0

            start = max(0, index - 250)
            end = min(len(text), index + 500)
            snippet = text[start:end].strip()

            results.append((path, snippet))

    return results[:max_results]