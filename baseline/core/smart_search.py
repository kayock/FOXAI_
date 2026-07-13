from pathlib import Path


class SmartSearch:
    """
    SmartSearch RC2 - Evidence Intelligence

    Searches like an engineer, not a grep tool.

    Evidence priority:
    1. Executable first-party source
    2. UI source
    3. Configuration
    4. Project memory / Forge Journal
    5. Mission Archive / history
    6. Vendor / third-party fallback
    """

    VENDOR_DIRS = {
        "ComfyUI",
        "venv",
        ".venv",
        "env",
        "site-packages",
        "node_modules",
        "__pycache__",
        ".git",
        "Models",
        "models",
    }

    SEARCH_EXTENSIONS = {
        ".py", ".json", ".md", ".txt", ".ini", ".bat", ".ps1", ".yaml", ".yml"
    }

    SOURCE_DIRS = {"core", "ui", "departments"}
    CONFIG_DIRS = {"config"}
    MEMORY_DIRS = {"Projects", "Library"}
    HISTORY_DIRS = {"Mission Archive", "MissionArchive", "Archive"}

    def __init__(self, root):
        self.root = Path(root)

    def rel(self, path):
        try:
            return str(Path(path).relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path).replace("\\", "/")

    def top_dir(self, path):
        try:
            rel = Path(path).relative_to(self.root)
        except Exception:
            rel = Path(path)

        return rel.parts[0] if rel.parts else ""

    def is_vendor(self, path):
        return bool(set(Path(path).parts) & self.VENDOR_DIRS)

    def evidence_class(self, path):
        top = self.top_dir(path)
        suffix = Path(path).suffix.lower()

        if self.is_vendor(path):
            return {
                "class": "vendor",
                "label": "Vendor / third-party",
                "priority": 10,
            }

        if top == "ui":
            return {
                "class": "ui_source",
                "label": "UI source",
                "priority": 95,
            }

        if top == "core" or top == "departments":
            return {
                "class": "source",
                "label": "Executable source",
                "priority": 100,
            }

        if top in self.CONFIG_DIRS or suffix in {".ini", ".yaml", ".yml"}:
            return {
                "class": "config",
                "label": "Configuration",
                "priority": 80,
            }

        if top in self.MEMORY_DIRS:
            return {
                "class": "project_memory",
                "label": "Project memory / knowledge",
                "priority": 55,
            }

        if top in self.HISTORY_DIRS:
            return {
                "class": "history",
                "label": "Mission history",
                "priority": 25,
            }

        if suffix == ".py":
            return {
                "class": "source_other",
                "label": "Other source",
                "priority": 65,
            }

        return {
            "class": "document",
            "label": "Document",
            "priority": 45,
        }

    def iter_files(self, include_vendor=False, include_history=True):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in self.SEARCH_EXTENSIONS:
                continue

            if self.is_vendor(path) and not include_vendor:
                continue

            evidence = self.evidence_class(path)
            if evidence["class"] == "history" and not include_history:
                continue

            yield path

    def search(self, query, limit=12, include_vendor=False, include_history=True):
        query = query or ""
        lowered = query.lower()
        results = []

        for path in self.iter_files(include_vendor=include_vendor, include_history=include_history):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            text_lower = text.lower()
            idx = text_lower.find(lowered)

            if idx < 0:
                continue

            evidence = self.evidence_class(path)
            rel = self.rel(path)

            score = evidence["priority"]

            # Path/name matches matter, but not enough to make history beat source.
            if lowered in rel.lower():
                score += 15

            # Python source is usually stronger implementation evidence.
            if path.suffix.lower() == ".py":
                score += 10

            # Mission archives are intentionally weak implementation evidence.
            if evidence["class"] == "history":
                score -= 10

            start = max(0, idx - 260)
            end = min(len(text), idx + len(query) + 520)
            snippet = text[start:end].strip()

            results.append({
                "file": rel,
                "score": score,
                "evidence_class": evidence["class"],
                "evidence_label": evidence["label"],
                "vendor": evidence["class"] == "vendor",
                "snippet": snippet,
            })

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def layered_search(self, query, limit=12, include_history=False):
        # Layer 1: executable source and config, no history, no vendor.
        primary = self.search(
            query,
            limit=limit,
            include_vendor=False,
            include_history=False,
        )

        strong = [
            item for item in primary
            if item["evidence_class"] in {"source", "ui_source", "source_other", "config"}
        ]

        if strong:
            return {
                "query": query,
                "scope": "Executable/source evidence",
                "primary": strong,
                "history": [],
                "vendor": [],
                "history_searched": False,
                "vendor_searched": False,
            }

        # Layer 2: project memory / documents, still no vendor.
        with_history = self.search(
            query,
            limit=limit,
            include_vendor=False,
            include_history=True,
        )

        history = [
            item for item in with_history
            if item["evidence_class"] in {"project_memory", "history", "document"}
        ]

        if history:
            return {
                "query": query,
                "scope": "Project knowledge / history fallback",
                "primary": [],
                "history": history,
                "vendor": [],
                "history_searched": True,
                "vendor_searched": False,
            }

        # Layer 3: vendor fallback.
        vendor = self.search(
            query,
            limit=limit,
            include_vendor=True,
            include_history=True,
        )

        vendor = [item for item in vendor if item["vendor"]]

        return {
            "query": query,
            "scope": "Vendor fallback",
            "primary": [],
            "history": [],
            "vendor": vendor,
            "history_searched": True,
            "vendor_searched": True,
        }

    def confidence_hint(self, layered_result):
        if layered_result["primary"]:
            best = layered_result["primary"][0]
            if best["evidence_class"] in {"source", "ui_source"}:
                return 88, "Strong source-code evidence."
            return 78, "First-party evidence found, but not direct UI/core source."

        if layered_result["history"]:
            return 58, "Only project memory or mission history evidence found."

        if layered_result["vendor"]:
            return 35, "Only vendor fallback evidence found."

        return 20, "No direct evidence found."

    def format_report(self, query, limit=8):
        data = self.layered_search(query, limit=limit)

        confidence, reason = self.confidence_hint(data)

        lines = [
            "SMART SEARCH REPORT",
            "",
            f"Query: {query}",
            f"Scope: {data['scope']}",
            f"Evidence Confidence Hint: {confidence}%",
            f"Reason: {reason}",
            "",
        ]

        if data["primary"]:
            lines.append("Primary evidence:")
            lines.append("")

            for item in data["primary"]:
                lines.append(f"--- {item['file']} ---")
                lines.append(f"Class: {item['evidence_label']}")
                lines.append(f"Score: {item['score']}")
                lines.append(item["snippet"])
                lines.append("")

            lines.append("History Search:")
            lines.append("Skipped because source/config evidence was found.")
            lines.append("")
            lines.append("Vendor Search:")
            lines.append("Skipped because first-party source evidence was found.")

        elif data["history"]:
            lines.append("No executable source evidence found.")
            lines.append("")
            lines.append("Historical / project knowledge evidence:")
            lines.append("")

            for item in data["history"]:
                lines.append(f"--- {item['file']} ---")
                lines.append(f"Class: {item['evidence_label']}")
                lines.append(f"Score: {item['score']}")
                lines.append(item["snippet"])
                lines.append("")

            lines.append("Vendor Search:")
            lines.append("Skipped because historical evidence was found. Use vendor search explicitly if needed.")

        elif data["vendor"]:
            lines.append("No first-party or history evidence found.")
            lines.append("")
            lines.append("Vendor fallback evidence:")
            lines.append("")

            for item in data["vendor"]:
                lines.append(f"--- {item['file']} ---")
                lines.append(f"Class: {item['evidence_label']}")
                lines.append(f"Score: {item['score']}")
                lines.append(item["snippet"])
                lines.append("")

        else:
            lines.append("No matches found.")

        lines.extend([
            "",
            "Search Policy:",
            "Executable FOXAI source outranks project memory, mission history, and vendor dependencies.",
        ])

        return "\n".join(lines)
