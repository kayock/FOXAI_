from pathlib import Path
import ast
import time


class ProjectIndex:
    """
    Read-only project index for Engineer.

    This scans source files and extracts simple structural facts:
    - files
    - Python classes
    - Python functions
    - imports
    - largest files
    """

    CODE_EXTENSIONS = {
        ".py", ".md", ".txt", ".json", ".ini", ".bat", ".ps1", ".yaml", ".yml"
    }

    IGNORE_DIRS = {
        "__pycache__", ".git", ".idea", ".vscode", "Models", "models",
        "output", "outputs", "temp", "tmp", "Backups", "Releases",
        "Mission Archive"
    }

    IGNORE_SUFFIXES = {
        ".pyc", ".pyo", ".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg", ".webp", ".ico"
    }

    def __init__(self, root):
        self.root = Path(root)
        self.created_at = time.time()
        self.files = []
        self.python_files = []
        self.classes = []
        self.functions = []
        self.imports = []
        self.errors = []

    def build(self):
        self.files = []
        self.python_files = []
        self.classes = []
        self.functions = []
        self.imports = []
        self.errors = []

        for path in self.iter_files():
            info = self.file_info(path)
            self.files.append(info)

            if path.suffix.lower() == ".py":
                self.python_files.append(info)
                self.scan_python(path)

        return self

    def iter_files(self):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue

            if path.suffix.lower() in self.IGNORE_SUFFIXES:
                continue

            if path.suffix.lower() not in self.CODE_EXTENSIONS:
                continue

            yield path

    def rel(self, path):
        try:
            return str(Path(path).relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path)

    def file_info(self, path):
        try:
            size = path.stat().st_size
        except Exception:
            size = 0

        return {
            "path": path,
            "relative": self.rel(path),
            "suffix": path.suffix.lower(),
            "size": size,
        }

    def scan_python(self, path):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as error:
            self.errors.append({
                "file": self.rel(path),
                "error": str(error),
            })
            return

        rel = self.rel(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.append({
                    "name": node.name,
                    "file": rel,
                    "line": getattr(node, "lineno", None),
                })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.append({
                    "name": node.name,
                    "file": rel,
                    "line": getattr(node, "lineno", None),
                    "async": isinstance(node, ast.AsyncFunctionDef),
                })

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append({
                        "module": alias.name,
                        "file": rel,
                        "line": getattr(node, "lineno", None),
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = f"{module}.{alias.name}" if module else alias.name
                    self.imports.append({
                        "module": name,
                        "file": rel,
                        "line": getattr(node, "lineno", None),
                    })

    def largest_files(self, limit=10):
        return sorted(self.files, key=lambda item: item["size"], reverse=True)[:limit]

    def find_symbol(self, symbol):
        lowered = symbol.lower()
        class_hits = [c for c in self.classes if lowered in c["name"].lower()]
        function_hits = [f for f in self.functions if lowered in f["name"].lower()]
        import_hits = [i for i in self.imports if lowered in i["module"].lower()]
        file_hits = [f for f in self.files if lowered in f["relative"].lower()]
        return {
            "classes": class_hits,
            "functions": function_hits,
            "imports": import_hits,
            "files": file_hits,
        }

    def summary(self):
        return {
            "root": str(self.root),
            "file_count": len(self.files),
            "python_file_count": len(self.python_files),
            "class_count": len(self.classes),
            "function_count": len(self.functions),
            "import_count": len(self.imports),
            "parse_error_count": len(self.errors),
            "largest_files": self.largest_files(),
        }

    def architecture_report(self):
        summary = self.summary()

        core_files = [f for f in self.files if f["relative"].startswith("core/")]
        ui_files = [f for f in self.files if f["relative"].startswith("ui/")]
        agent_files = [f for f in self.files if "agent" in f["relative"].lower()]

        lines = [
            "PROJECT INDEX REPORT",
            "",
            f"Root: {summary['root']}",
            "",
            f"Files indexed: {summary['file_count']}",
            f"Python files: {summary['python_file_count']}",
            f"Classes detected: {summary['class_count']}",
            f"Functions detected: {summary['function_count']}",
            f"Imports detected: {summary['import_count']}",
            f"Parse errors: {summary['parse_error_count']}",
            "",
            "Module groups:",
            f"• core/: {len(core_files)} files",
            f"• ui/: {len(ui_files)} files",
            f"• agent-related: {len(agent_files)} files",
            "",
            "Largest indexed files:",
        ]

        for item in summary["largest_files"][:8]:
            kb = item["size"] / 1024
            lines.append(f"• {item['relative']} ({kb:.1f} KB)")

        if summary["parse_error_count"]:
            lines.append("")
            lines.append("Parse warnings:")
            for error in self.errors[:5]:
                lines.append(f"• {error['file']}: {error['error']}")

        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)
