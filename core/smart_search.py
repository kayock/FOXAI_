import ast
import re
from pathlib import Path

from core.security_containment import is_protected_path, redact_secrets


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

    GENERATED_ARTIFACT_TOP_DIRS = {
        "Backup",
        "Backups",
        "baseline",
        "candidate",
        "payload",
    }

    GENERATED_BUNDLE_MARKERS = (
        "_apply_",
        "_preview_",
        "_patch_bundle_",
        "_checkpoint_",
    )

    SEARCH_EXTENSIONS = {
        ".py", ".json", ".md", ".txt", ".ini", ".bat", ".ps1", ".yaml", ".yml"
    }

    SOURCE_DIRS = {"core", "ui", "departments"}
    CONFIG_DIRS = {"config"}
    MEMORY_DIRS = {"Projects", "Library", "Memory"}
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

    def is_generated_artifact(self, path):
        top = self.top_dir(path)
        normalized = top.casefold()

        if normalized in {
            name.casefold() for name in self.GENERATED_ARTIFACT_TOP_DIRS
        }:
            return True

        return (
            normalized.startswith("kayocktheos_")
            and any(marker in normalized for marker in self.GENERATED_BUNDLE_MARKERS)
        )

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

    @staticmethod
    def is_identifier_query(query):
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", query or ""))

    @staticmethod
    def assignment_names(target):
        if isinstance(target, ast.Name):
            return [target.id]

        if isinstance(target, (ast.Tuple, ast.List)):
            names = []
            for item in target.elts:
                names.extend(SmartSearch.assignment_names(item))
            return names

        return []

    @staticmethod
    def line_index(text, lineno):
        if not lineno or lineno < 1:
            return 0

        lines = text.splitlines(keepends=True)
        if lineno > len(lines):
            return len(text)

        return sum(len(line) for line in lines[:lineno - 1])

    def python_symbol_evidence(self, text, query):
        if not self.is_identifier_query(query):
            return None

        query_key = query.casefold()

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return {
                "kind": "text",
                "label": "Text match",
                "bonus": 0,
                "lineno": None,
                "index": text.casefold().find(query_key),
            }

        best = None

        def consider(kind, label, bonus, name, node):
            nonlocal best

            if not name or str(name).casefold() != query_key:
                return

            candidate = {
                "kind": kind,
                "label": label,
                "bonus": bonus,
                "lineno": getattr(node, "lineno", None),
            }

            if best is None or candidate["bonus"] > best["bonus"]:
                best = candidate

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                consider(
                    "class_definition",
                    "Class definition",
                    40,
                    node.name,
                    node,
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                consider(
                    "function_definition",
                    "Function definition",
                    38,
                    node.name,
                    node,
                )

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    for name in self.assignment_names(target):
                        consider(
                            "assignment",
                            "Assignment / symbol definition",
                            35,
                            name,
                            node,
                        )

            elif isinstance(node, ast.AnnAssign):
                for name in self.assignment_names(node.target):
                    consider(
                        "assignment",
                        "Assignment / symbol definition",
                        35,
                        name,
                        node,
                    )

            elif isinstance(node, ast.NamedExpr):
                for name in self.assignment_names(node.target):
                    consider(
                        "assignment",
                        "Assignment / symbol definition",
                        33,
                        name,
                        node,
                    )

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imported_name = alias.asname or alias.name.rsplit(".", 1)[-1]
                    consider(
                        "import",
                        "Imported symbol",
                        18,
                        imported_name,
                        node,
                    )

            elif isinstance(node, ast.Name):
                consider(
                    "reference",
                    "Code reference",
                    8,
                    node.id,
                    node,
                )

            elif isinstance(node, ast.Attribute):
                consider(
                    "reference",
                    "Attribute reference",
                    6,
                    node.attr,
                    node,
                )

        if best is not None:
            best["index"] = self.line_index(text, best["lineno"])
            return best

        return {
            "kind": "text_only",
            "label": "Text/example only",
            "bonus": -20,
            "lineno": None,
            "index": text.casefold().find(query_key),
        }

    def iter_files(self, include_vendor=False, include_history=True):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in self.SEARCH_EXTENSIONS:
                continue

            if is_protected_path(path, self.root):
                continue

            if self.is_generated_artifact(path):
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
            match = None

            # Path/name matches matter, but not enough to make history beat source.
            if lowered in rel.lower():
                score += 15

            # Python source is usually stronger implementation evidence.
            if path.suffix.lower() == ".py":
                score += 10
                match = self.python_symbol_evidence(text, query)
                if match:
                    score += match["bonus"]
                    if match.get("index", -1) >= 0:
                        idx = match["index"]

            # Mission archives are intentionally weak implementation evidence.
            if evidence["class"] == "history":
                score -= 10

            start = max(0, idx - 260)
            end = min(len(text), idx + len(query) + 520)
            snippet, redaction_count = redact_secrets(text[start:end].strip())

            results.append({
                "file": rel,
                "score": score,
                "evidence_class": evidence["class"],
                "evidence_label": evidence["label"],
                "match_kind": match["kind"] if match else "text",
                "match_label": match["label"] if match else "Text match",
                "vendor": evidence["class"] == "vendor",
                "snippet": snippet,
                "redactions": redaction_count,
            })

        results.sort(
            key=lambda item: (-item["score"], item["file"].casefold())
        )
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
                lines.append(f"Match: {item['match_label']}")
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
                lines.append(f"Match: {item['match_label']}")
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
                lines.append(f"Match: {item['match_label']}")
                lines.append(item["snippet"])
                lines.append("")

        else:
            lines.append("No matches found.")

        lines.extend([
            "",
            "Search Policy:",
            "Executable FOXAI source outranks project memory, mission history, and vendor dependencies.",
            "Generated apply/preview/checkpoint bundles and backup trees are excluded.",
            "Protected credential/key/vault paths are excluded and displayed snippets are secret-redacted.",
        ])

        return "\n".join(lines)
