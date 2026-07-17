from pathlib import Path
import ast
from collections import defaultdict


class RuntimeGraph:
    """
    Read-only runtime relationship scanner for FOXAI.

    Unlike DependencyGraph, this looks for object relationships and call sites:
    - self.app.brainstem
    - app.brainstem
    - self.specialists["red_canvas"]
    - diagnostics.run_full_inspection(...)
    - generate_image(...)
    - build_prompt(...)
    """

    IGNORE_DIRS = {
        "__pycache__", ".git", ".idea", ".vscode", "Models", "models",
        "output", "outputs", "temp", "tmp", "Backups", "Releases",
        "Mission Archive"
    }

    KNOWN_TARGETS = {
        "brainstem": ["brainstem"],
        "director": ["direct"],
        "diagnostics": ["diagnostics", "run_full_inspection", "hardware_status", "neural_status", "creative_status"],
        "red canvas": ["red_canvas", "RedCanvasAgent", "generate_red_canvas", "route_image_request", "generate_image"],
        "iron library": ["iron_library", "LibraryAgent", "search_documents", "list_documents", "ensure_library"],
        "promptsmith": ["promptsmith", "build_prompt", "run_promptsmith"],
        "comfy": ["comfy", "ComfyUI", "generate_image", "is_comfy_running"],
        "engineer": ["engineer", "EngineerAgent", "ProjectIndex", "DependencyGraph", "RuntimeGraph"],
        "mission control": ["mission_status", "add_chat", "start_mission_animation", "stop_mission_animation"],
        "workshop state": ["begin_workshop_mission", "complete_workshop_mission", "fail_workshop_mission", "apply_workshop_state"],
    }

    def __init__(self, root):
        self.root = Path(root)
        self.references = defaultdict(list)
        self.calls = defaultdict(list)
        self.attributes = defaultdict(list)
        self.errors = []

    def build(self):
        self.references = defaultdict(list)
        self.calls = defaultdict(list)
        self.attributes = defaultdict(list)
        self.errors = []

        for path in self.iter_python_files():
            self.scan_file(path)

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

    def scan_file(self, path):
        rel = self.rel(path)

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception as error:
            self.errors.append({"file": rel, "error": str(error)})
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = self.attribute_name(node)
                if name:
                    self.record_reference(name, rel, getattr(node, "lineno", None), "attribute")
                    self.attributes[name].append({
                        "file": rel,
                        "line": getattr(node, "lineno", None),
                    })

            elif isinstance(node, ast.Call):
                call_name = self.call_name(node.func)
                if call_name:
                    self.record_reference(call_name, rel, getattr(node, "lineno", None), "call")
                    self.calls[call_name].append({
                        "file": rel,
                        "line": getattr(node, "lineno", None),
                    })

            elif isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    value = node.value
                    self.record_reference(value, rel, getattr(node, "lineno", None), "string")

    def attribute_name(self, node):
        parts = []

        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        if not parts:
            return None

        return ".".join(reversed(parts))

    def call_name(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            return self.attribute_name(node)

        return None

    def record_reference(self, value, rel, line, kind):
        lowered = str(value).lower()

        for target, patterns in self.KNOWN_TARGETS.items():
            for pattern in patterns:
                if pattern.lower() in lowered:
                    self.references[target].append({
                        "value": value,
                        "file": rel,
                        "line": line,
                        "kind": kind,
                        "pattern": pattern,
                    })
                    break

    def summary(self):
        total_refs = sum(len(items) for items in self.references.values())
        return {
            "targets": len(self.references),
            "references": total_refs,
            "calls": sum(len(items) for items in self.calls.values()),
            "attributes": sum(len(items) for items in self.attributes.values()),
            "parse_errors": len(self.errors),
        }

    def report(self):
        summary = self.summary()

        lines = [
            "RUNTIME RELATIONSHIP GRAPH",
            "",
            f"Targets detected: {summary['targets']}",
            f"Runtime references: {summary['references']}",
            f"Call sites detected: {summary['calls']}",
            f"Attribute references detected: {summary['attributes']}",
            f"Parse errors: {summary['parse_errors']}",
            "",
            "Known Workshop relationships:",
        ]

        for target in sorted(self.KNOWN_TARGETS):
            refs = self.references.get(target, [])
            files = sorted({item["file"] for item in refs})
            lines.append(f"• {target}: {len(refs)} reference(s) across {len(files)} file(s)")

        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def relationship_answer(self, query):
        target = self.extract_target(query)
        refs = self.references.get(target, [])

        lines = [
            "RUNTIME RELATIONSHIP ANALYSIS",
            "",
            f"Target: {target}",
            "",
        ]

        if not refs:
            lines.append("No runtime references were detected for this target.")
        else:
            grouped = defaultdict(list)
            for item in refs:
                grouped[item["file"]].append(item)

            lines.append(f"References found: {len(refs)}")
            lines.append(f"Files involved: {len(grouped)}")
            lines.append("")

            for file, items in sorted(grouped.items())[:20]:
                lines.append(f"--- {file} ---")
                for item in items[:12]:
                    lines.append(
                        f"• line {item.get('line')}: {item.get('kind')} → {item.get('value')}"
                    )
                if len(items) > 12:
                    lines.append(f"• ... {len(items) - 12} more")
                lines.append("")

        lines.append("Interpretation:")
        lines.append(self.interpret_target(target))

        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def extract_target(self, query):
        lowered = query.lower()

        for target in self.KNOWN_TARGETS:
            if target in lowered:
                return target

        aliases = {
            "brainstem": "brainstem",
            "state": "workshop state",
            "busy": "workshop state",
            "red": "red canvas",
            "canvas": "red canvas",
            "library": "iron library",
            "diagnostic": "diagnostics",
            "diag": "diagnostics",
            "comfyui": "comfy",
            "comfy": "comfy",
            "prompt": "promptsmith",
            "engineer": "engineer",
            "mission": "mission control",
        }

        for key, value in aliases.items():
            if key in lowered:
                return value

        return "brainstem"

    def interpret_target(self, target):
        explanations = {
            "brainstem": "Brainstem is the Workshop state manager. Runtime references usually indicate state checks, mission locks, readiness checks, or active mission tracking.",
            "director": "Director is responsible for classifying operator requests and choosing the correct department.",
            "diagnostics": "Diagnostics gathers Workshop health information for the Diagnostics department, Advisor, and future Engineer troubleshooting.",
            "red canvas": "Red Canvas handles image-generation missions, including prompt preparation, ComfyUI submission, and output display.",
            "iron library": "Iron Library handles local document and code search.",
            "promptsmith": "PromptSmith enhances visual prompts before Red Canvas sends them to ComfyUI.",
            "comfy": "ComfyUI is the image-generation backend used by Red Canvas.",
            "engineer": "Engineer analyzes the project in read-only mode and uses ProjectIndex, DependencyGraph, and RuntimeGraph.",
            "mission control": "Mission Control is the narration layer that reports what FOXAI is doing.",
            "workshop state": "Workshop state methods lock/unlock controls, track active missions, and prevent overlapping operations.",
        }

        return explanations.get(target, "No interpretation is available for this target yet.")
