from core.paths import LIBRARY

SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".json", ".ini", ".bat", ".ps1"}

def ensure_library():
    for folder in ["Physics", "DnD", "Programming", "Manuals", "Research"]:
        (LIBRARY / folder).mkdir(parents=True, exist_ok=True)

def list_documents():
    ensure_library()
    return sorted([p for p in LIBRARY.rglob("*") if p.is_file()])

def search_documents(query):
    query = query.lower().strip()
    results = []
    if not query:
        return results
    for path in list_documents():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        if query in low:
            idx = low.find(query)
            results.append((path, text[max(0, idx-160):min(len(text), idx+260)].strip()))
    return results
