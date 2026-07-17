from pathlib import Path
import ast
from collections import defaultdict


class DependencyGraph:
    """
    Read-only dependency graph for FOXAI.

    This scans Python imports and builds relationships between modules.
    It is intentionally conservative and does not execute project code.
    """

    IGNORE_DIRS = {
        "__pycache__", ".git", ".idea", ".vscode", "Models", "models",
        "output", "outputs", "temp", "tmp", "Backups", "Releases",
        "Mission Archive"
    }

    def __init__(self, root):
        self.root = Path(root)
        self.modules = {}
        self.imports_by_file = defaultdict(list)
        self.imported_by = defaultdict(list)
        self.errors = []

    def build(self):
        self.modules = {}
        self.imports_by_file = defaultdict(list)
        self.imported_by = defaultdict(list)
        self.errors = []

        for path in self.iter_python_files():
            module_name = self.module_name(path)
            rel = self.rel(path)
            self.modules[module_name] = rel
            self.scan_file(path, module_name, rel)

        self.build_reverse_edges()
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

    def module_name(self, path):
        rel = Path(path).relative_to(self.root)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def scan_file(self, path, module_name, rel):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as error:
            self.errors.append({
                "file": rel,
                "error": str(error),
            })
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports_by_file[module_name].append({
                        "module": alias.name,
                        "line": getattr(node, "lineno", None),
                        "type": "import",
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    module = self.resolve_relative_import(module_name, module, node.level)

                self.imports_by_file[module_name].append({
                    "module": module,
                    "line": getattr(node, "lineno", None),
                    "type": "from",
                })

    def resolve_relative_import(self, current_module, imported_module, level):
        parts = current_module.split(".")
        base = parts[:-level] if level <= len(parts) else []

        if imported_module:
            base.append(imported_module)

        return ".".join(base)

    def build_reverse_edges(self):
        for source_module, imports in self.imports_by_file.items():
            source_file = self.modules.get(source_module, source_module)

            for item in imports:
                imported = item["module"]

                if not imported:
                    continue

                # Store both exact and package-level reverse links.
                self.imported_by[imported].append({
                    "module": source_module,
                    "file": source_file,
                    "line": item.get("line"),
                })

    def find_imports_matching(self, query):
        lowered = query.lower()
        matches = []

        for module, imports in self.imports_by_file.items():
            rel = self.modules.get(module, module)

            for item in imports:
                imported = item["module"]
                if lowered in imported.lower():
                    matches.append({
                        "source_module": module,
                        "source_file": rel,
                        "imported_module": imported,
                        "line": item.get("line"),
                    })

        return matches

    def find_files_importing(self, query):
        query_lower = query.lower()
        results = []

        for module, imports in self.imports_by_file.items():
            rel = self.modules.get(module, module)

            for item in imports:
                imported = item["module"]
                if query_lower in imported.lower():
                    results.append({
                        "file": rel,
                        "module": module,
                        "imports": imported,
                        "line": item.get("line"),
                    })

        return results

    def direct_imports_for_file(self, query):
        query_lower = query.lower()
        matches = []

        for module, rel in self.modules.items():
            if query_lower in module.lower() or query_lower in rel.lower():
                matches.append({
                    "module": module,
                    "file": rel,
                    "imports": self.imports_by_file.get(module, []),
                })

        return matches

    def summary(self):
        edge_count = sum(len(items) for items in self.imports_by_file.values())
        return {
            "module_count": len(self.modules),
            "import_edge_count": edge_count,
            "parse_error_count": len(self.errors),
        }

    def report(self, limit=20):
        summary = self.summary()

        lines = [
            "DEPENDENCY GRAPH REPORT",
            "",
            f"Modules scanned: {summary['module_count']}",
            f"Import edges: {summary['import_edge_count']}",
            f"Parse errors: {summary['parse_error_count']}",
            "",
            "Key FOXAI dependencies:",
        ]

        for key in [
            "core.brainstem",
            "core.director",
            "core.diagnostics",
            "core.project_index",
            "core.dependency_graph",
            "core.comfy_bridge",
            "core.promptsmith",
            "core.engineer_agent",
        ]:
            hits = self.find_files_importing(key)
            lines.append(f"• {key}: used by {len(hits)} file(s)")

        lines.append("")
        lines.append("Top import-heavy modules:")

        ranked = sorted(
            self.imports_by_file.items(),
            key=lambda item: len(item[1]),
            reverse=True
        )

        for module, imports in ranked[:limit]:
            rel = self.modules.get(module, module)
            lines.append(f"• {rel}: {len(imports)} imports")

        if self.errors:
            lines.append("")
            lines.append("Parse warnings:")
            for error in self.errors[:5]:
                lines.append(f"• {error['file']}: {error['error']}")

        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def dependency_answer(self, query):
        graph_query = self.extract_dependency_target(query)
        graph_query = graph_query or query

        imports = self.direct_imports_for_file(graph_query)
        used_by = self.find_files_importing(graph_query)

        lines = [
            "DEPENDENCY ANALYSIS",
            "",
            f"Target: {graph_query}",
            "",
        ]

        if imports:
            lines.append("Direct imports:")
            for match in imports[:8]:
                lines.append(f"--- {match['file']} ---")
                for item in match["imports"][:20]:
                    lines.append(f"• {item['module']} (line {item.get('line')})")
                if len(match["imports"]) > 20:
                    lines.append(f"• ... {len(match['imports']) - 20} more")
                lines.append("")
        else:
            lines.append("Direct imports:")
            lines.append("No matching source file/module found.")
            lines.append("")

        lines.append("Used by:")
        if used_by:
            for item in used_by[:20]:
                lines.append(f"• {item['file']} imports {item['imports']} at line {item.get('line')}")
            if len(used_by) > 20:
                lines.append(f"• ... {len(used_by) - 20} more")
        else:
            lines.append("No imports found matching this target.")

        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def extract_dependency_target(self, query):
        lowered = query.lower()

        known = {
            "brainstem": "core.brainstem",
            "director": "core.director",
            "diagnostics": "core.diagnostics",
            "project index": "core.project_index",
            "dependency graph": "core.dependency_graph",
            "promptsmith": "core.promptsmith",
            "red canvas": "red_canvas",
            "comfy bridge": "core.comfy_bridge",
            "comfyui": "comfy",
            "engineer": "core.engineer_agent",
            "main window": "ui.main_window",
        }

        for key, value in known.items():
            if key in lowered:
                return value

        return None
