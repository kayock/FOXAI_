from pathlib import Path
import ast


class TechnicalDebtEngine:
    """
    Read-only technical debt scanner for FOXAI.

    This engine does not modify files. It looks for structural signals:
    - large files
    - large classes
    - large functions
    - parse errors
    - possible refactor candidates
    """

    IGNORE_DIRS = {
        "__pycache__", ".git", ".idea", ".vscode", "Models", "models",
        "output", "outputs", "temp", "tmp", "Backups", "Releases",
        "Mission Archive", "ComfyUI", "Memory"
    }

    def __init__(self, root):
        self.root = Path(root)
        self.files = []
        self.functions = []
        self.classes = []
        self.errors = []

    def build(self):
        self.files = []
        self.functions = []
        self.classes = []
        self.errors = []

        for path in self.iter_python_files():
            self.scan_python_file(path)

        return self

    def iter_python_files(self):
        for path in self.root.rglob("*.py"):
            if not path.is_file():
                continue

            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue

            yield path

    def rel(self, path):
        try:
            return str(Path(path).relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path)

    def scan_python_file(self, path):
        rel = self.rel(path)

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
            tree = ast.parse(source)
        except Exception as error:
            self.errors.append({
                "file": rel,
                "error": str(error),
            })
            return

        self.files.append({
            "file": rel,
            "line_count": len(lines),
            "size": path.stat().st_size if path.exists() else 0,
        })

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.append({
                    "name": node.name,
                    "file": rel,
                    "line": getattr(node, "lineno", None),
                    "end_line": getattr(node, "end_lineno", None),
                    "line_count": self.node_line_count(node),
                    "method_count": len([child for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))]),
                })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.append({
                    "name": node.name,
                    "file": rel,
                    "line": getattr(node, "lineno", None),
                    "end_line": getattr(node, "end_lineno", None),
                    "line_count": self.node_line_count(node),
                    "async": isinstance(node, ast.AsyncFunctionDef),
                })

    def node_line_count(self, node):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)

        if start is None or end is None:
            return 0

        return max(0, end - start + 1)

    def largest_files(self, limit=10):
        return sorted(self.files, key=lambda item: item["line_count"], reverse=True)[:limit]

    def largest_functions(self, limit=10):
        return sorted(self.functions, key=lambda item: item["line_count"], reverse=True)[:limit]

    def largest_classes(self, limit=10):
        return sorted(self.classes, key=lambda item: item["line_count"], reverse=True)[:limit]

    def score(self):
        score = 100
        suggestions = []

        large_files = [f for f in self.files if f["line_count"] > 600]
        very_large_files = [f for f in self.files if f["line_count"] > 1000]
        large_functions = [f for f in self.functions if f["line_count"] > 80]
        large_classes = [c for c in self.classes if c["line_count"] > 500]

        if very_large_files:
            score -= min(25, len(very_large_files) * 8)
            suggestions.append("Very large modules detected. Consider splitting them by department or responsibility.")
        elif large_files:
            score -= min(15, len(large_files) * 5)
            suggestions.append("Large modules detected. Monitor these as refactor candidates.")

        if large_functions:
            score -= min(20, len(large_functions) * 3)
            suggestions.append("Large functions detected. Consider extracting helper functions.")

        if large_classes:
            score -= min(15, len(large_classes) * 5)
            suggestions.append("Large classes detected. Consider splitting responsibilities.")

        if self.errors:
            score -= min(20, len(self.errors) * 5)
            suggestions.append("Parse errors detected. These should be reviewed first.")

        score = max(0, min(100, score))

        if score >= 90:
            label = "EXCELLENT"
        elif score >= 75:
            label = "GOOD"
        elif score >= 50:
            label = "NEEDS ATTENTION"
        else:
            label = "REFACTOR RECOMMENDED"

        if not suggestions:
            suggestions.append("No major structural concerns detected.")

        return {
            "score": score,
            "label": label,
            "suggestions": suggestions,
            "large_file_count": len(large_files),
            "very_large_file_count": len(very_large_files),
            "large_function_count": len(large_functions),
            "large_class_count": len(large_classes),
            "parse_error_count": len(self.errors),
        }

    def review(self):
        debt = self.score()

        lines = [
            "TECHNICAL DEBT REPORT",
            "",
            f"Architecture Health: {debt['score']}% - {debt['label']}",
            "",
            "Project Scope:",
            f"• Python files reviewed: {len(self.files)}",
            f"• Classes detected: {len(self.classes)}",
            f"• Functions detected: {len(self.functions)}",
            f"• Parse errors: {len(self.errors)}",
            "",
            "Signals:",
            f"• Very large files: {debt['very_large_file_count']}",
            f"• Large files: {debt['large_file_count']}",
            f"• Large functions: {debt['large_function_count']}",
            f"• Large classes: {debt['large_class_count']}",
            "",
            "Largest FOXAI files:",
        ]

        for item in self.largest_files(8):
            lines.append(f"• {item['file']} ({item['line_count']} lines)")

        lines.extend([
            "",
            "Largest functions:",
        ])

        for item in self.largest_functions(8):
            lines.append(f"• {item['name']} in {item['file']}:{item['line']} ({item['line_count']} lines)")

        lines.extend([
            "",
            "Largest classes:",
        ])

        for item in self.largest_classes(8):
            lines.append(f"• {item['name']} in {item['file']}:{item['line']} ({item['line_count']} lines, {item['method_count']} methods)")

        lines.extend([
            "",
            "Recommendations:",
        ])

        for suggestion in debt["suggestions"]:
            lines.append(f"• {suggestion}")

        if self.errors:
            lines.extend([
                "",
                "Parse warnings:",
            ])

            for error in self.errors[:8]:
                lines.append(f"• {error['file']}: {error['error']}")

        lines.extend([
            "",
            "Engineer Assessment:",
            self.assessment_text(debt),
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)

    def assessment_text(self, debt):
        if debt["score"] >= 90:
            return (
                "The Workshop architecture is currently healthy. "
                "The main risk is continued growth of UI modules. "
                "Future refactors should focus on extracting department panels from main_window.py."
            )

        if debt["score"] >= 75:
            return (
                "The Workshop is healthy but beginning to show natural growth pressure. "
                "The next safe refactor is to split large UI departments into their own modules."
            )

        if debt["score"] >= 50:
            return (
                "The Workshop is functional but accumulating structural debt. "
                "Refactoring should be prioritized before adding many more large departments."
            )

        return (
            "The Workshop would benefit from immediate refactoring before major new features are added."
        )

    def refactor_plan(self):
        debt = self.score()
        largest = self.largest_files(5)

        lines = [
            "ENGINEER REFACTOR PLAN",
            "",
            f"Architecture Health: {debt['score']}% - {debt['label']}",
            "",
            "Priority 1: Split high-growth UI code",
            "Reason: main_window.py is the central orchestrator and should not absorb every department forever.",
            "",
            "Candidate extraction targets:",
            "• Diagnostics panel → ui/diagnostics_panel.py",
            "• Engineer panel → ui/engineer_panel.py",
            "• Red Canvas panel → ui/red_canvas_panel.py",
            "• Dashboard panel → ui/dashboard_panel.py",
            "• Settings/Profile panel → ui/settings_panel.py",
            "",
            "Priority 2: Preserve source of truth boundaries",
            "• Brainstem owns Workshop state.",
            "• Director owns mission routing.",
            "• Diagnostics owns health checks.",
            "• Engineer owns code analysis.",
            "• Identity Engine should own branding and themes.",
            "",
            "Priority 3: Add Identity Engine before hardcoding new profiles",
            "Reason: Kayock's Forge should be a profile, not a fork.",
            "",
            "Largest current files reviewed:",
        ]

        for item in largest:
            lines.append(f"• {item['file']} ({item['line_count']} lines)")

        lines.extend([
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)
