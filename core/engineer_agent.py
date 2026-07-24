print("=" * 60)
print("ENGINEER_AGENT RC26 GROUNDED REASONING LOADED")
print(__file__)
print("=" * 60)
from pathlib import Path
import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize

from core.project_index import ProjectIndex
from core.dependency_graph import DependencyGraph
from core.runtime_graph import RuntimeGraph
from core.mission_flow import MissionFlow
from core.technical_debt import TechnicalDebtEngine
from core.confidence_engine import ConfidenceEngine
from core.decision_layer import DecisionLayer
from core.forge_master import ForgeMaster
from core.forge_journal import ForgeJournal
from core.engineer_intent import EngineerIntent
# FOXAI_ENGINEERING_WORKSHOP_V1_1_INTEGRATION
try:
    from core.engineering_workshop_bridge import EngineeringWorkshopBridge
except Exception:
    EngineeringWorkshopBridge = None

from core.smart_search import SmartSearch
from core.kernel import get_kernel
from core.boot_manager import BootManager
from core.investigation_engine import InvestigationEngine, Mission, Evidence, EvidenceDriver
from core.evidence_ranker import EvidenceRanker
from core.recommendation_engine import RecommendationEngine
from core.evidence_drivers import TimeoutDriver, ContextMenuDriver, SpellcheckDriver


class SourceCodeDriver(EvidenceDriver):
    """
    SourceCodeDriver RC1

    Wraps SmartSearch so the Investigation Engine can collect structured
    source-code evidence without depending directly on Engineer presentation logic.
    """

    name = "SourceCodeDriver"

    def __init__(self, smart_search):
        self.smart_search = smart_search

    def collect(self, mission: Mission) -> list[Evidence]:
        evidence: list[Evidence] = []

        search_terms = self._terms_for(mission)

        for term in search_terms:
            result = self.smart_search.layered_search(term, limit=5)

            for item in result.get("primary", []):
                evidence.append(self._from_item(term, item, "source"))

            # For RC1, include history only if no source evidence exists.
            if not evidence:
                for item in result.get("history", []):
                    evidence.append(self._from_item(term, item, "history"))

            # Vendor evidence is intentionally last and low weight.
            if not evidence:
                for item in result.get("vendor", []):
                    evidence.append(self._from_item(term, item, "vendor"))

            if evidence:
                break

        return evidence

    def _terms_for(self, mission: Mission) -> list[str]:
        lowered = mission.query.lower()

        if "timeout" in lowered:
            return ["timeout=300", "timeout", "read timeout", "ChatTimeoutError"]

        if "investigation engine" in lowered or "investigation_engine" in lowered:
            return ["investigation_engine.py", "InvestigationEngine", "EvidenceDriver", "Mission"]

        if "right click" in lowered or "right-click" in lowered or "context menu" in lowered:
            return [
                "bind(\"<Button-3>\"",
                "bind('<Button-3>'",
                "context menu",
                "tk.Menu",
                "input_box",
                "chat_box",
            ]

        return [mission.query]

    def _from_item(self, term: str, item: dict, category: str) -> Evidence:
        base_confidence = {
            "source": 85,
            "history": 55,
            "vendor": 30,
        }.get(category, 40)

        base_weight = {
            "source": 90,
            "history": 45,
            "vendor": 20,
        }.get(category, 40)

        return Evidence(
            source=self.name,
            category=category,
            path=item.get("file", ""),
            snippet=item.get("snippet", ""),
            confidence=base_confidence,
            weight=base_weight,
            metadata={
                "search_term": term,
                "evidence_class": item.get("evidence_class", ""),
                "evidence_label": item.get("evidence_label", ""),
                "score": item.get("score", 0),
            },
        )



class EngineerAgent:
    """
    Engineer is FOXAI's read-only-first code specialist with a controlled implementation Workshop.

    Current goals:
    - Search the FOXAI project.
    - Build a project index.
    - Locate relevant code files.
    - Explain likely architecture areas.
    - Modify project files only through exact-plan preview, explicit approval, snapshot, validation, and rollback.
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

    EXACT_INSPECTION_MAX_BYTES = 262144
    EXACT_INSPECTION_MAX_CHARS = 120000
    REFERENCE_MANIFEST_RELATIVE_PATH = (
        Path("System") / "AgentFoxTechnicalCore" / "Reference"
        / "TECHNICAL_CORE_REFERENCE_MANIFEST.json"
    )
    CONTEXT_TRACE_MAX_FILES = 8
    CONTEXT_TRACE_MAX_FILE_BYTES = 3 * 1024 * 1024
    CONTEXT_TRACE_MAX_SNIPPETS_PER_FILE = 3
    GROUNDED_REASONING_MAX_FILES = 6
    GROUNDED_REASONING_MAX_WINDOWS_PER_FILE = 2
    GROUNDED_REASONING_WINDOW_RADIUS = 8
    GROUNDED_REASONING_MAX_PROMPT_CHARS = 48000

    def __init__(self, app):
        self.app = app
        self.project_root = Path(__file__).resolve().parents[1]
        self.index = None
        self.dependency_graph = None
        self.runtime_graph = None
        self.mission_flow = MissionFlow()
        self.technical_debt = None
        self.confidence = ConfidenceEngine()
        self.decision_layer = DecisionLayer()
        self.forge_master = ForgeMaster()
        self.forge_journal = ForgeJournal()
        self.intent = EngineerIntent()
        # FOXAI_ENGINEERING_WORKSHOP_V1_1_INTEGRATION
        self.engineering_workshop = (
            EngineeringWorkshopBridge(self)
            if EngineeringWorkshopBridge is not None
            else None
        )

        self.smart_search = SmartSearch(self.project_root)
        self.kernel = get_kernel(root=self.project_root)
        self.boot_manager = BootManager(app=self.app, kernel=self.kernel)
        self.evidence_drivers = [
            TimeoutDriver(self.smart_search),
            ContextMenuDriver(self.smart_search),
            SpellcheckDriver(self.smart_search),
            SourceCodeDriver(self.smart_search),  # fallback driver
        ]
        self.investigation_engine = InvestigationEngine(
            kernel=self.kernel,
            drivers=self.evidence_drivers,
        )
        self.evidence_ranker = EvidenceRanker()
        self.recommendation_engine = RecommendationEngine()

    @staticmethod
    def normalize_operator_query(query):
        """Remove only a leading explicit Engineer invocation token.

        This preserves ordinary words such as "engineers" inside the task while
        ensuring Engineer subsystems receive the actual operator request.
        """
        text = (query or "").strip()
        return re.sub(
            r"^(?:/engineer\b|engineer\s*[:,])\s*",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip()

    def handle(
        self,
        text,
        payload=None,
        caller="operator",
        operator_approved=False,
        *,
        correlation_id=None,
        mission_id=None,
        route_audit_receipt=None,
    ):
        """Handle an explicit Engineer request without security containment.

        Caller, approval, correlation, mission, and route-receipt arguments stay
        in the signature for compatibility with existing FOXAI routing. They are
        not authorization gates. Read-only inspection and lab work run directly;
        actual project changes remain behind Workshop preview/apply/rollback.
        """
        _ = (
            caller,
            operator_approved,
            correlation_id,
            mission_id,
            route_audit_receipt,
        )
        query = (payload or text or "").strip()

        if self.engineering_workshop is not None:
            workshop_report = self.engineering_workshop.handle(
                query,
                caller="operator",
                operator_approved=True,
            )
            if workshop_report is not None:
                self.app.add_chat("ERIC", query)
                self.app.mission_status(
                    "Engineering Workshop online.\n\n"
                    "Stable preview, validation, apply, and rollback tools active."
                )
                self.app.add_chat("ENGINEER", workshop_report)
                self.app.mission_memory.save()
                if hasattr(self.app, "complete_workshop_mission"):
                    self.app.complete_workshop_mission("ONLINE")
                return "break"

        self.app.add_chat("ERIC", query)
        self.app.mission_status(
            "Engineer online.\n\n"
            "Performing direct read-only source analysis."
        )

        try:
            report = self.analyze(query)
            self.app.add_chat("ENGINEER", report)
            self.app.mission_memory.save()
            if hasattr(self.app, "complete_workshop_mission"):
                self.app.complete_workshop_mission("ONLINE")
            return "break"
        except Exception as error:
            if hasattr(self.app, "fail_workshop_mission"):
                self.app.fail_workshop_mission(str(error))
            self.app.add_chat(
                "ENGINEER",
                f"Engineering analysis failed:\n{type(error).__name__}: {error}",
            )
            return "break"

    def build_index(self):
        self.index = ProjectIndex(self.project_root).build()
        return self.index

    def get_index(self):
        if self.index is None:
            return self.build_index()
        return self.index

    def build_dependency_graph(self):
        self.dependency_graph = DependencyGraph(self.project_root).build()
        return self.dependency_graph

    def get_dependency_graph(self):
        if self.dependency_graph is None:
            return self.build_dependency_graph()
        return self.dependency_graph

    def build_runtime_graph(self):
        self.runtime_graph = RuntimeGraph(self.project_root).build()
        return self.runtime_graph

    def get_runtime_graph(self):
        if self.runtime_graph is None:
            return self.build_runtime_graph()
        return self.runtime_graph

    def build_technical_debt(self):
        self.technical_debt = TechnicalDebtEngine(self.project_root).build()
        return self.technical_debt

    def get_technical_debt(self):
        if self.technical_debt is None:
            return self.build_technical_debt()
        return self.technical_debt

    def confidence_card(self, evidence, reason="", base=50, uncertainty=0):
        return self.confidence.card(
            evidence=evidence,
            base=base,
            uncertainty=uncertainty,
            reason=reason,
        )

    def _after_phrase(self, text, phrases):
        lowered = text.lower()
        for phrase in phrases:
            idx = lowered.find(phrase)
            if idx >= 0:
                return text[idx + len(phrase):].strip()
        return text.strip()

    def _split_project_note(self, text):
        """
        Simple RC1 parser.

        Supports:
        - chisel decision for FOXAI: Title - reason
        - log lesson for FOXAI: Lesson - reason
        - open project memory for Web Spider Toolkit
        """
        if ":" in text:
            left, right = text.split(":", 1)
        else:
            left, right = text, ""

        project = self._after_phrase(
            left,
            [
                "chisel decision for ",
                "log decision for ",
                "record decision for ",
                "log lesson for ",
                "chisel lesson for ",
                "open project memory for ",
                "open project for ",
            ],
        )

        note = right.strip()

        if " - " in note:
            title, reason = note.split(" - ", 1)
        else:
            title, reason = note, ""

        return project.strip() or "FOXAI", title.strip(), reason.strip()

    def architecture_review(self, query):
        report = self.build_technical_debt().review()

        return (
            "ENGINEER ARCHITECTURE REVIEW\n\n"
            "Intent:\n"
            "Architecture Review\n\n"
            "Reason:\n"
            "The request asks Engineer to evaluate code/design rather than perform a raw text search.\n\n"
            f"{report}"
        )

    def ui_investigation(self, query):
        self.kernel.publish(
            "INVESTIGATION_STARTED",
            {"intent": "UI Investigation", "query": query},
            source="Engineer"
        )

        search_terms = [
            "bind(\"<Button-3>\"",
            "bind('<Button-3>'",
            "context menu",
            "right click",
            "right-click",
            "tk.Menu",
            "CTkTextbox",
            "input_box",
            "chat_box",
            "engineer_box",
        ]

        lines = [
            "ENGINEER UI INVESTIGATION",
            "",
            "Intent:",
            "UI Investigation",
            "",
            "Question:",
            query,
            "",
            "What Engineer checked:",
            "• Right-click bindings such as <Button-3>",
            "• Context menu references",
            "• Tk menu references",
            "• Textbox widgets that may need menu binding",
            "",
            "Findings:",
        ]

        matches = []
        for term in search_terms:
            result = self.smart_search.layered_search(term, limit=5)
            if result.get("primary"):
                matches.append((term, result, "primary"))
            elif result.get("history"):
                matches.append((term, result, "history"))
            elif result.get("vendor"):
                matches.append((term, result, "vendor"))

        confidence_base = 55
        evidence_note = "No direct implementation evidence found."

        if matches and matches[0][2] == "primary":
            lines.append("Potential executable/source evidence was found.")
            lines.append("")
            lines.append("Top source result:")
            first = matches[0][1]["primary"][0]
            lines.append(f"--- {first['file']} ---")
            lines.append(f"Class: {first['evidence_label']}")
            lines.append(first["snippet"])
            confidence_base = 82
            evidence_note = "Source/config evidence was found."
        elif matches and matches[0][2] == "history":
            lines.append("Only historical/project-memory evidence was found.")
            lines.append("")
            lines.append("Top historical result:")
            first = matches[0][1]["history"][0]
            lines.append(f"--- {first['file']} ---")
            lines.append(f"Class: {first['evidence_label']}")
            lines.append(first["snippet"])
            confidence_base = 58
            evidence_note = "History is useful context but weak implementation evidence."
        elif matches and matches[0][2] == "vendor":
            lines.append("Only vendor fallback evidence was found.")
            lines.append("")
            lines.append("Top vendor result:")
            first = matches[0][1]["vendor"][0]
            lines.append(f"--- {first['file']} ---")
            lines.append(f"Class: {first['evidence_label']}")
            lines.append(first["snippet"])
            confidence_base = 35
            evidence_note = "Vendor evidence does not prove FOXAI implementation behavior."
        else:
            lines.extend([
                "No obvious right-click/context-menu binding was found in the scanned project files.",
                "",
                "Likely fix:",
                "Add a reusable context menu helper and bind it to the text widgets that need right-click support.",
                "",
                "Typical widgets to bind:",
                "• input_box",
                "• chat_box",
                "• engineer_box",
                "• library_box",
                "• canvas_prompt",
                "• canvas_negative",
                "",
                "Expected implementation shape:",
                "1. Create a right-click menu with Cut, Copy, Paste, Select All.",
                "2. Bind <Button-3> to each editable textbox.",
                "3. Use widget.focus_set() before showing the menu.",
                "4. Use tk_popup(event.x_root, event.y_root).",
                "5. Release the grab after menu closes.",
            ])

        lines.extend([
            "",
            self.confidence_card(
                evidence=[
                    {"type": "direct_file_match", "detail": "Engineer searched for context-menu and right-click binding patterns."},
                    {"type": "inference", "detail": "Recommendation is based on missing or weak UI binding evidence."},
                ],
                base=confidence_base,
                reason=f"UI investigation uses evidence-weighted search. {evidence_note}"
            ),
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        result = "\n".join(lines)

        self.kernel.publish(
            "INVESTIGATION_COMPLETED",
            {"intent": "UI Investigation", "query": query},
            source="Engineer"
        )

        return result

    def performance_review(self, query):
        return (
            "ENGINEER PERFORMANCE REVIEW\n\n"
            "Intent:\nPerformance Review\n\n"
            "Recommended first checks:\n"
            "• Long-running requests should use ChatResilience.\n"
            "• UI should not block during neural requests.\n"
            "• Background threads should report status through Mission Control.\n"
            "• Large scans should ignore ComfyUI/vendor folders unless explicitly requested.\n\n"
            + self.build_technical_debt().refactor_plan()
        )

    def security_review(self, query):
        return (
            "ENGINEER SECURITY REVIEW\n\n"
            "Security hardening is currently deferred by operator direction.\n\n"
            "Engineer will focus on useful source analysis, isolated testing, "
            "stable previews, validation, snapshots, receipts, and rollback. "
            "No authorization or containment recommendation is being added."
        )

    def parse_exact_path_inspection(self, query):
        """Return one file path from a natural read/explain request.

        Examples:
        - inspect core\\director.py
        - explain what core\\director.py does
        - read "Z:\\FOXAI\\core\\director.py"

        Requests without both a read/explain action and a supported file path
        return None so ordinary Engineer routing can continue.
        """
        first_line = (query or "").splitlines()[0].strip()
        if not first_line:
            return None

        action_match = re.search(
            r"\b(?:inspect|explain|read|open|review|summarize|describe)\b",
            first_line,
            flags=re.IGNORECASE,
        )
        if not action_match:
            return None

        extensions = "|".join(
            sorted(
                suffix.lstrip(".")
                for suffix in self.CODE_EXTENSIONS
            )
        )

        quoted_match = re.search(
            rf"""["'](?P<path>[^"']+\.(?:{extensions}))["']""",
            first_line,
            flags=re.IGNORECASE,
        )
        if quoted_match:
            return quoted_match.group("path").strip()

        path_match = re.search(
            rf"""(?P<path>
                (?:[A-Za-z]:[\\/])?
                (?:[A-Za-z0-9_.()\-]+[\\/])+
                [A-Za-z0-9_.()\-]+\.(?:{extensions})
            )""",
            first_line,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if path_match:
            return path_match.group("path").strip()

        if re.match(r"^inspect\b", first_line, flags=re.IGNORECASE):
            return ""

        return None

    def resolve_exact_inspection_path(self, raw_path):
        """Resolve one exact local FOXAI text file without policy gating."""
        value = (raw_path or "").strip()
        if not value:
            return None, "No file path was supplied."

        if value.startswith("\\\\") or value.startswith("//"):
            return None, "Network paths are not part of this local FOXAI request."

        drive_match = re.match(r"^[A-Za-z]:", value)
        remainder = value[2:] if drive_match else value
        if ":" in remainder:
            return None, "Alternate data streams are not supported."

        normalized_value = value.replace("\\", os.sep).replace("/", os.sep)
        candidate = Path(normalized_value)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate

        try:
            root = self.project_root.resolve(strict=True)
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            return None, "The requested file does not exist."
        except Exception as error:
            return None, (
                "The requested path could not be resolved: "
                f"{type(error).__name__}."
            )

        try:
            resolved.relative_to(root)
        except ValueError:
            return None, "The requested file resolves outside Z:\\FOXAI."

        if not resolved.is_file():
            return None, "The requested path is not a regular file."
        if resolved.suffix.lower() not in self.CODE_EXTENSIONS:
            return None, "The requested file type is not a supported text format."

        try:
            size = resolved.stat().st_size
        except OSError as error:
            return None, (
                "The requested file metadata could not be read: "
                f"{type(error).__name__}."
            )
        if size > self.EXACT_INSPECTION_MAX_BYTES:
            return None, (
                "The requested file is too large for bounded exact-path "
                f"inspection ({size} bytes; limit "
                f"{self.EXACT_INSPECTION_MAX_BYTES})."
            )

        return resolved, ""

    def _brief_exact_file_summary(self, path, text):
        """Build a source-grounded explanation from the file's actual content."""
        lines = text.splitlines()
        nonempty = [line.strip() for line in lines if line.strip()]
        suffix = path.suffix.lower()

        if suffix == ".py":
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError as error:
                return (
                    f"This is a Python source file with {len(lines)} lines.\n\n"
                    "Syntax status: FAILED\n"
                    f"- {error.msg} at line {error.lineno}, "
                    f"column {error.offset or 0}."
                )

            imports = []
            definitions = []
            function_nodes = []
            broad_exception_count = 0
            bare_exception_count = 0
            top_level_prints = 0

            for node in tree.body:
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "[relative import]")
                elif isinstance(node, ast.ClassDef):
                    class_doc = ast.get_docstring(node)
                    detail = f"class {node.name} at line {node.lineno}"
                    if class_doc:
                        detail += " — " + class_doc.strip().splitlines()[0]
                    definitions.append(detail)
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            function_nodes.append(child)
                            method_doc = ast.get_docstring(child)
                            item = (
                                f"method {node.name}.{child.name} "
                                f"at line {child.lineno}"
                            )
                            if method_doc:
                                item += " — " + method_doc.strip().splitlines()[0]
                            definitions.append(item)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_nodes.append(node)
                    function_doc = ast.get_docstring(node)
                    item = f"function {node.name} at line {node.lineno}"
                    if function_doc:
                        item += " — " + function_doc.strip().splitlines()[0]
                    definitions.append(item)
                elif (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "print"
                ):
                    top_level_prints += 1

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        bare_exception_count += 1
                    elif (
                        isinstance(node.type, ast.Name)
                        and node.type.id in {"Exception", "BaseException"}
                    ):
                        broad_exception_count += 1

            todos = []
            try:
                for token in tokenize.generate_tokens(io.StringIO(text).readline):
                    if token.type != tokenize.COMMENT:
                        continue
                    upper = token.string.upper()
                    if "TODO" in upper or "FIXME" in upper:
                        todos.append((token.start[0], token.string.strip()))
            except (tokenize.TokenError, IndentationError):
                # AST parsing already passed. Tokenization failure should not
                # prevent the rest of the source explanation.
                todos = []

            largest = None
            if function_nodes:
                largest = max(
                    function_nodes,
                    key=lambda item: (
                        (getattr(item, "end_lineno", item.lineno) or item.lineno)
                        - item.lineno
                    ),
                )

            output = [
                f"This is a Python source file with {len(lines)} lines.",
                "",
                "Syntax status: PASSED",
            ]

            module_doc = ast.get_docstring(tree)
            if module_doc:
                output.extend(
                    [
                        "",
                        "Module purpose:",
                        module_doc.strip().splitlines()[0],
                    ]
                )

            if imports:
                unique_imports = list(dict.fromkeys(imports))
                shown = ", ".join(unique_imports[:16])
                extra = len(unique_imports) - min(len(unique_imports), 16)
                output.extend(
                    [
                        "",
                        "Imports:",
                        shown + (f", plus {extra} more" if extra else ""),
                    ]
                )

            output.extend(["", "Key definitions:"])
            if definitions:
                output.extend(f"- {item}" for item in definitions[:28])
                if len(definitions) > 28:
                    output.append(
                        f"- ... {len(definitions) - 28} additional definitions"
                    )
            else:
                output.append("- No top-level functions or classes were found.")

            output.extend(
                [
                    "",
                    "Bounded code observations:",
                    f"- Broad `except Exception/BaseException` handlers: "
                    f"{broad_exception_count}",
                    f"- Bare `except` handlers: {bare_exception_count}",
                    f"- Top-level print calls: {top_level_prints}",
                    f"- TODO/FIXME markers: {len(todos)}",
                ]
            )

            if largest is not None:
                end_line = getattr(largest, "end_lineno", largest.lineno)
                output.append(
                    f"- Largest function/method: {largest.name}, "
                    f"lines {largest.lineno}-{end_line}"
                )

            if todos:
                output.append("")
                output.append("TODO/FIXME locations:")
                output.extend(
                    f"- line {number}: {value[:180]}"
                    for number, value in todos[:12]
                )

            return "\n".join(output)

        title = ""
        if suffix == ".md":
            for line in nonempty:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break

        opening_lines = nonempty[:12]
        opening = "\n".join(opening_lines)
        if len(opening) > 1800:
            opening = opening[:1797].rstrip() + "..."

        kind = {
            ".md": "Markdown document",
            ".json": "JSON document",
            ".bat": "Windows batch script",
            ".ps1": "PowerShell script",
            ".yaml": "YAML document",
            ".yml": "YAML document",
            ".ini": "INI configuration file",
            ".txt": "text document",
        }.get(suffix, "text file")

        output = [f"This is a {kind} with {len(lines)} lines."]
        if title:
            output.extend(["", f"Title: {title}"])
        if opening:
            output.extend(["", "Opening content:", opening])
        else:
            output.extend(["", "The file contains no non-empty text lines."])
        return "\n".join(output)




    def inspect_exact_path(self, raw_path):
        """Read and explain exactly one bounded FOXAI source or text file."""
        resolved, error = self.resolve_exact_inspection_path(raw_path)
        if resolved is None:
            return (
                "ENGINEER EXACT-FILE INSPECTION\n\n"
                f"Requested path: {raw_path or '[not supplied]'}\n"
                f"Result: NOT OPENED\n"
                f"Reason: {error}\n\n"
                "Nothing was modified."
            )

        try:
            data = resolved.read_bytes()
        except OSError as read_error:
            return (
                "ENGINEER EXACT-FILE INSPECTION\n\n"
                f"File: {resolved}\n"
                "Result: NOT OPENED\n"
                f"Reason: {type(read_error).__name__}: {read_error}\n\n"
                "Nothing was modified."
            )

        if b"\x00" in data:
            return (
                "ENGINEER EXACT-FILE INSPECTION\n\n"
                f"File: {resolved}\n"
                "Result: NOT OPENED\n"
                "Reason: Binary content was detected.\n\n"
                "Nothing was modified."
            )

        decoded = data.decode("utf-8", errors="replace")
        bounded_text = decoded[:self.EXACT_INSPECTION_MAX_CHARS]
        summary = self._brief_exact_file_summary(resolved, bounded_text)
        digest = hashlib.sha256(data).hexdigest()

        return (
            "ENGINEER SOURCE EXPLANATION\n\n"
            f"File:\n{resolved}\n\n"
            f"SHA-256:\n{digest}\n\n"
            f"Source-grounded explanation:\n{summary}\n\n"
            "Read-only: one exact FOXAI file was opened and nothing was changed."
        )

    def parse_engineering_lab_request(self, query):
        """Return one exact Python path from a Lab compile/test request."""
        first_line = (query or "").splitlines()[0].strip()
        if not first_line:
            return None

        if not re.search(
            r"\b(?:lab\s+test|lab\s+compile|python\s+lab|"
            r"test\s+in\s+lab|compile\s+in\s+lab|isolated\s+test)\b",
            first_line,
            flags=re.IGNORECASE,
        ):
            return None

        quoted = re.search(
            r"""["'](?P<path>[^"']+\.py)["']""",
            first_line,
            flags=re.IGNORECASE,
        )
        if quoted:
            return quoted.group("path").strip()

        unquoted = re.search(
            r"""(?P<path>
                (?:[A-Za-z]:[\\/])?
                (?:[A-Za-z0-9_.()\-]+[\\/])+
                [A-Za-z0-9_.()\-]+\.py
            )""",
            first_line,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if unquoted:
            return unquoted.group("path").strip()

        return ""

    def engineering_lab_test(self, raw_path):
        """Compile one copied Python file in a disposable isolated process.

        The live FOXAI source is never executed or modified. The selected file
        is copied into an operating-system temporary directory, compiled with
        the active FOXAI Python using ``-I -B``, inspected with AST, and then the
        temporary directory is removed.
        """
        resolved, error = self.resolve_exact_inspection_path(raw_path)
        if resolved is None:
            return (
                "ENGINEERING LAB\n\n"
                f"Requested path: {raw_path or '[not supplied]'}\n"
                "Result: NOT RUN\n"
                f"Reason: {error}\n\n"
                "The live project was not modified."
            )

        if resolved.suffix.lower() != ".py":
            return (
                "ENGINEERING LAB\n\n"
                f"File: {resolved}\n"
                "Result: NOT RUN\n"
                "Reason: the first Lab increment supports Python files only.\n\n"
                "The live project was not modified."
            )

        try:
            source_bytes = resolved.read_bytes()
            source_text = source_bytes.decode("utf-8", errors="replace")
        except OSError as read_error:
            return (
                "ENGINEERING LAB\n\n"
                f"File: {resolved}\n"
                "Result: NOT RUN\n"
                f"Reason: {type(read_error).__name__}: {read_error}\n\n"
                "The live project was not modified."
            )

        started = time.perf_counter()
        compile_status = "FAILED"
        compile_output = ""
        temporary_removed = False

        try:
            with tempfile.TemporaryDirectory(
                prefix="FOXAI_EngineeringLab_"
            ) as temp_name:
                temp_root = Path(temp_name)
                lab_source = temp_root / resolved.name
                shutil.copy2(resolved, lab_source)
                pyc_path = temp_root / (resolved.stem + ".lab.pyc")

                command = [
                    sys.executable,
                    "-I",
                    "-B",
                    "-m",
                    "py_compile",
                    str(lab_source),
                ]
                completed = subprocess.run(
                    command,
                    cwd=str(temp_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                compile_status = (
                    "PASSED" if completed.returncode == 0 else "FAILED"
                )
                compile_output = (
                    (completed.stdout or "") + (completed.stderr or "")
                ).strip()

                # py_compile may use __pycache__; all files remain inside the
                # temporary directory and disappear at context exit.
                _ = pyc_path
            temporary_removed = True
        except subprocess.TimeoutExpired:
            compile_status = "FAILED"
            compile_output = "The isolated compile exceeded 30 seconds."
        except Exception as lab_error:
            compile_status = "FAILED"
            compile_output = f"{type(lab_error).__name__}: {lab_error}"

        syntax_status = "PASSED"
        classes = []
        functions = []
        imports = []
        broad_exceptions = 0
        bare_exceptions = 0

        try:
            tree = ast.parse(source_text, filename=str(resolved))
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "[relative import]")
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(node.name)

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        bare_exceptions += 1
                    elif (
                        isinstance(node.type, ast.Name)
                        and node.type.id in {"Exception", "BaseException"}
                    ):
                        broad_exceptions += 1
        except SyntaxError as syntax_error:
            syntax_status = (
                f"FAILED — {syntax_error.msg} at line "
                f"{syntax_error.lineno}, column {syntax_error.offset or 0}"
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        relative = resolved.relative_to(self.project_root.resolve())
        digest = hashlib.sha256(source_bytes).hexdigest()
        unique_imports = list(dict.fromkeys(imports))

        output = [
            "ENGINEERING LAB — DISPOSABLE PYTHON TEST",
            "",
            f"Source: {resolved}",
            f"Relative path: {relative}",
            f"Source SHA-256: {digest}",
            f"Python executable: {sys.executable}",
            "",
            f"Isolated compile: {compile_status}",
            f"AST parse: {syntax_status}",
            f"Elapsed: {elapsed_ms} ms",
            f"Temporary workspace removed: {temporary_removed}",
            "",
            "Static structure:",
            f"- Imports: {len(unique_imports)}",
            f"- Top-level classes: {len(classes)}",
            f"- Top-level functions: {len(functions)}",
            f"- Broad exception handlers: {broad_exceptions}",
            f"- Bare exception handlers: {bare_exceptions}",
        ]

        if unique_imports:
            output.append(
                "- Import names: " + ", ".join(unique_imports[:20])
                + (
                    f", plus {len(unique_imports) - 20} more"
                    if len(unique_imports) > 20
                    else ""
                )
            )
        if classes:
            output.append("- Classes: " + ", ".join(classes[:20]))
        if functions:
            output.append("- Functions: " + ", ".join(functions[:20]))

        if compile_output:
            output.extend(["", "Compiler output:", compile_output[:4000]])

        output.extend(
            [
                "",
                "Lab boundary:",
                "- The live source file was not modified.",
                "- Module top-level code was not imported or executed.",
                "- The copied file was compiled in an isolated Python process.",
                "- The temporary workspace was removed after the test.",
                "",
                (
                    "Result: PASS"
                    if compile_status == "PASSED" and syntax_status == "PASSED"
                    else "Result: ATTENTION REQUIRED"
                ),
            ]
        )
        return "\n".join(output)

    def parse_context_trace_request(self, query):
        """Return the engineering question for a manifest-bounded context trace."""
        text = (query or "").strip()
        if not text:
            return None

        patterns = (
            r"^(?:context\s+trace|trace\s+context|build\s+context)\b",
            r"^(?:trace|call\s+path|routing\s+path)\b",
            r"^investigate\s+(?:how|why|where)\b",
            r"^(?:who\s+calls|what\s+calls|who\s+uses)\b",
        )
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                remainder = text[match.end():].strip(" :,-")
                return remainder or text
        return None

    def _load_context_manifest_records(self):
        """Load current files from the authoritative manifest's bounded list."""
        manifest_path = self.project_root / self.REFERENCE_MANIFEST_RELATIVE_PATH
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Technical Core reference manifest not found: {manifest_path}"
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = (
            (manifest.get("source_inventory") or {}).get("files") or []
        )
        root = self.project_root.resolve()
        records = []
        missing = []
        skipped = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            relative_text = str(entry.get("path") or "").strip()
            if not relative_text or not relative_text.lower().endswith(".py"):
                continue
            relative = Path(relative_text.replace("\\", "/"))
            candidate = self.project_root / relative
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(root)
            except FileNotFoundError:
                missing.append(relative_text)
                continue
            except Exception:
                skipped.append(relative_text)
                continue
            if not resolved.is_file():
                skipped.append(relative_text)
                continue
            size = resolved.stat().st_size
            if size > self.CONTEXT_TRACE_MAX_FILE_BYTES:
                skipped.append(
                    f"{relative_text} ({size} bytes exceeds bounded limit)"
                )
                continue
            data = resolved.read_bytes()
            text = data.decode("utf-8", errors="replace")
            current_hash = hashlib.sha256(data).hexdigest()
            expected_hash = str(entry.get("sha256") or "")
            records.append(
                {
                    "relative": relative.as_posix(),
                    "path": resolved,
                    "size": size,
                    "text": text,
                    "text_lower": text.casefold(),
                    "sha256": current_hash,
                    "manifest_sha256": expected_hash,
                    "manifest_hash_match": (
                        current_hash == expected_hash if expected_hash else None
                    ),
                }
            )

        return manifest_path, manifest, records, missing, skipped

    @staticmethod
    def _context_module_name(relative):
        path = Path(str(relative).replace("\\", "/"))
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)

    def _analyze_context_record(self, record):
        """Parse one current source file, including function-local imports.

        Imports inside functions are important in FOXAI because WebUI loads
        EngineerAgent lazily. Module-only import scanning cannot prove that
        relationship, so every Import/ImportFrom node is recorded with scope.
        """
        text = record["text"]
        relative = record["relative"]
        module_name = self._context_module_name(relative)
        imports = []
        import_bindings = []
        definitions = []
        calls = []
        names = set()
        syntax_error = ""
        tree = None

        def resolve_from_module(node):
            module = node.module or ""
            level = int(getattr(node, "level", 0) or 0)
            if level <= 0:
                return module
            current_parts = module_name.split(".")
            package_parts = current_parts[:-1]
            keep = max(0, len(package_parts) - (level - 1))
            base = package_parts[:keep]
            if module:
                base.extend(module.split("."))
            return ".".join(part for part in base if part)

        def flatten_target(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                prefix = flatten_target(node.value)
                return f"{prefix}.{node.attr}" if prefix else node.attr
            return ""

        try:
            tree = ast.parse(text, filename=relative)
        except SyntaxError as error:
            syntax_error = (
                f"{error.msg} at line {error.lineno}, "
                f"column {error.offset or 0}"
            )

        if tree is not None:
            parent = {}
            for owner in ast.walk(tree):
                for child in ast.iter_child_nodes(owner):
                    parent[child] = owner

            def scope_for(node):
                scopes = []
                current = parent.get(node)
                while current is not None:
                    if isinstance(
                        current,
                        (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                    ):
                        scopes.append(current.name)
                    current = parent.get(current)
                return ".".join(reversed(scopes)) or "<module>"

            for node in tree.body:
                if isinstance(
                    node,
                    (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    definitions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "kind": (
                                "class"
                                if isinstance(node, ast.ClassDef)
                                else "function"
                            ),
                        }
                    )

            seen_bindings = set()
            seen_calls = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        binding = {
                            "kind": "module",
                            "module": alias.name,
                            "symbol": "",
                            "local": alias.asname or alias.name.split(".", 1)[0],
                            "line": int(node.lineno),
                            "scope": scope_for(node),
                        }
                        key = tuple(binding[item] for item in (
                            "kind", "module", "symbol", "local", "line", "scope"
                        ))
                        if key not in seen_bindings:
                            imports.append(alias.name)
                            import_bindings.append(binding)
                            seen_bindings.add(key)
                elif isinstance(node, ast.ImportFrom):
                    imported_module = resolve_from_module(node)
                    imports.append(imported_module or "[relative import]")
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        binding = {
                            "kind": "symbol",
                            "module": imported_module,
                            "symbol": alias.name,
                            "local": alias.asname or alias.name,
                            "line": int(node.lineno),
                            "scope": scope_for(node),
                        }
                        key = tuple(binding[item] for item in (
                            "kind", "module", "symbol", "local", "line", "scope"
                        ))
                        if key not in seen_bindings:
                            import_bindings.append(binding)
                            seen_bindings.add(key)
                elif isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr)
                elif isinstance(node, ast.Call):
                    target = flatten_target(node.func)
                    key = (target, int(getattr(node, "lineno", 0) or 0))
                    if target and key not in seen_calls:
                        calls.append({"target": target, "line": key[1]})
                        seen_calls.add(key)

        record = dict(record)
        record.update(
            {
                "module": module_name,
                "imports": list(dict.fromkeys(imports)),
                "import_bindings": import_bindings,
                "definitions": definitions,
                "calls": calls,
                "names": names,
                "syntax_error": syntax_error,
                "line_count": len(text.splitlines()),
            }
        )
        return record

    @staticmethod
    def _context_query_terms(question):
        lowered = (question or "").casefold()
        quoted = re.findall(r'["\']([^"\']+)["\']', lowered)
        filenames = re.findall(r"[a-z0-9_.()\-]+\.py", lowered)
        words = re.findall(r"[a-z0-9_\-]+", lowered)
        stop = {
            "trace", "context", "build", "investigate", "how", "why",
            "where", "what", "which", "who", "calls", "called", "from",
            "into", "through", "does", "reach", "the", "this", "that",
            "with", "and", "for", "are", "is", "was", "were", "file",
            "files", "code", "foxai", "engineer", "please",
        }
        terms = []
        terms.extend(quoted)
        terms.extend(filenames)
        terms.extend(
            word for word in words
            if len(word) >= 3 and word not in stop
        )

        phrase_expansions = {
            "current-state": ["current_state", "current state", "live state"],
            "current": ["current_state", "current state"],
            "webui": ["webui", "foxai_web", "route_http_request"],
            "model": ["model", "dispatch", "llama", "ordinary_chat"],
            "chat": ["chat", "route_message", "route_http_request"],
            "route": ["route", "routing", "dispatch", "handle"],
        }
        expanded = []
        for term in terms:
            expanded.append(term)
            expanded.extend(phrase_expansions.get(term, []))
        return list(dict.fromkeys(item for item in expanded if item))

    def _score_context_record(self, record, question, terms):
        path_lower = record["relative"].casefold()
        source_lower = record["text_lower"]
        score = 0
        reasons = []

        requested_files = re.findall(
            r"[a-z0-9_.()\-]+\.py", (question or "").casefold()
        )
        for filename in requested_files:
            if path_lower.endswith(filename):
                score += 120
                reasons.append(f"exact requested filename: {filename}")

        for term in terms:
            normalized = term.casefold()
            if normalized in path_lower:
                score += 24
                reasons.append(f"path matches {term}")
            occurrences = source_lower.count(normalized)
            if occurrences:
                score += min(occurrences, 12) * 2
                reasons.append(f"source contains {term} ({occurrences})")
            if any(
                normalized == item["name"].casefold()
                or normalized in item["name"].casefold()
                for item in record["definitions"]
            ):
                score += 18
                reasons.append(f"definition matches {term}")
            if any(normalized in item.casefold() for item in record["imports"]):
                score += 12
                reasons.append(f"import matches {term}")

        lowered = (question or "").casefold()
        basename = Path(record["relative"]).name.casefold()
        anchor_boosts = {
            "webui_self_knowledge_integration_v1.py": (
                55 if any(word in lowered for word in ("webui", "chat", "current", "model")) else 0
            ),
            "self_knowledge_chat_adapter_v1.py": (
                45 if any(word in lowered for word in ("chat", "current", "model", "adapter")) else 0
            ),
            "foxai_web.py": (
                40 if any(word in lowered for word in ("webui", "chat", "model", "route")) else 0
            ),
            "director.py": (
                28 if any(word in lowered for word in ("route", "department", "engineer")) else 0
            ),
            "engineer_agent.py": (
                35 if "engineer" in lowered else 0
            ),
        }
        boost = anchor_boosts.get(basename, 0)
        if boost:
            score += boost
            reasons.append("known live seam for this question")

        return score, list(dict.fromkeys(reasons))

    @staticmethod
    def _context_snippets(record, terms, limit):
        snippets = []
        lines = record["text"].splitlines()
        for number, line in enumerate(lines, start=1):
            folded = line.casefold()
            matched = next(
                (term for term in terms if term.casefold() in folded),
                None,
            )
            if matched is None:
                continue
            value = line.strip()
            if not value:
                continue
            snippets.append(
                {
                    "line": number,
                    "text": value[:220],
                    "term": matched,
                }
            )
            if len(snippets) >= limit:
                break
        return snippets

    def _context_connections(self, selected, all_records):
        """Return only import-resolved cross-file source connections.

        A call edge is emitted only when its local name or module alias can be
        traced to an explicit import statement. Shared function names in
        unrelated files are never treated as evidence of a call relationship.
        """
        by_module = {
            record["module"]: record
            for record in all_records
            if record.get("module")
        }
        selected_paths = {record["relative"] for record in selected}
        definition_names = {
            record["module"]: {
                item["name"] for item in record.get("definitions", [])
            }
            for record in all_records
        }
        connections = []

        def add(value):
            if value not in connections:
                connections.append(value)

        def module_for_module_binding(binding, call_target):
            parts = call_target.split(".")
            local = binding["local"]
            imported_module = binding["module"]
            if not parts or parts[0] != local:
                return None, ""

            if local != imported_module.split(".", 1)[0] or len(parts) == 2:
                return imported_module, parts[-1]

            # ``import core.adapter`` binds ``core``. Resolve the longest
            # explicit module prefix in ``core.adapter.route_message``.
            for stop in range(len(parts) - 1, 0, -1):
                candidate = ".".join(parts[:stop])
                if candidate in by_module:
                    return candidate, parts[-1]
            return imported_module, parts[-1]

        for source in all_records:
            for binding in source.get("import_bindings", []):
                target = by_module.get(binding.get("module", ""))
                if (
                    target is not None
                    and target["relative"] != source["relative"]
                    and target["relative"] in selected_paths
                ):
                    scope = str(binding.get("scope") or "<module>")
                    scope_text = (
                        "" if scope == "<module>" else f" inside {scope}"
                    )
                    add(
                        f"{source['relative']} imports "
                        f"{target['relative']} at line {binding['line']}"
                        f"{scope_text}"
                    )

            for call in source.get("calls", []):
                call_target = call.get("target", "")
                if not call_target:
                    continue
                parts = call_target.split(".")
                resolved_module = ""
                resolved_symbol = ""
                import_line = 0

                if len(parts) == 1:
                    for binding in source.get("import_bindings", []):
                        if (
                            binding.get("kind") == "symbol"
                            and binding.get("local") == call_target
                        ):
                            resolved_module = binding.get("module", "")
                            resolved_symbol = binding.get("symbol", "")
                            import_line = int(binding.get("line", 0) or 0)
                            break
                else:
                    head = parts[0]
                    for binding in source.get("import_bindings", []):
                        if binding.get("local") != head:
                            continue
                        import_line = int(binding.get("line", 0) or 0)
                        if binding.get("kind") == "module":
                            resolved_module, resolved_symbol = (
                                module_for_module_binding(binding, call_target)
                            )
                        else:
                            combined = ".".join(
                                part
                                for part in (
                                    binding.get("module", ""),
                                    binding.get("symbol", ""),
                                )
                                if part
                            )
                            if combined in by_module:
                                resolved_module = combined
                                resolved_symbol = parts[-1]
                        if resolved_module:
                            break

                target = by_module.get(resolved_module)
                if (
                    target is None
                    or target["relative"] == source["relative"]
                    or target["relative"] not in selected_paths
                ):
                    continue
                if (
                    resolved_symbol
                    and resolved_symbol
                    not in definition_names.get(resolved_module, set())
                ):
                    continue

                binding_scope = "<module>"
                for candidate_binding in source.get("import_bindings", []):
                    if int(candidate_binding.get("line", 0) or 0) == import_line:
                        binding_scope = str(
                            candidate_binding.get("scope") or "<module>"
                        )
                        break
                scope_text = (
                    "" if binding_scope == "<module>"
                    else f", import scope {binding_scope}"
                )
                add(
                    f"{source['relative']} calls {resolved_symbol} from "
                    f"{target['relative']} at line {call['line']} "
                    f"(import line {import_line}{scope_text})"
                )

        return connections[:24]

    def _compile_context_bundle(self, selected):
        started = time.perf_counter()
        results = []
        removed = False
        try:
            with tempfile.TemporaryDirectory(
                prefix="FOXAI_ContextLab_"
            ) as temp_name:
                temp_root = Path(temp_name)
                for record in selected:
                    relative = Path(record["relative"])
                    copied = temp_root / relative
                    copied.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(record["path"], copied)
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-I",
                            "-B",
                            "-m",
                            "py_compile",
                            str(copied),
                        ],
                        cwd=str(temp_root),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    results.append(
                        {
                            "relative": record["relative"],
                            "passed": completed.returncode == 0,
                            "output": (
                                (completed.stdout or "")
                                + (completed.stderr or "")
                            ).strip()[:1000],
                        }
                    )
            removed = True
        except Exception as error:
            results.append(
                {
                    "relative": "[context lab]",
                    "passed": False,
                    "output": f"{type(error).__name__}: {error}",
                }
            )
        return {
            "results": results,
            "removed": removed,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    def trace_engineering_context(self, question):
        """Assemble and test a bounded multi-file source context."""
        try:
            manifest_path, _, raw_records, missing, skipped = (
                self._load_context_manifest_records()
            )
        except Exception as error:
            return (
                "ENGINEER CONTEXT TRACE\n\n"
                "Result: NOT AVAILABLE\n"
                f"Reason: {type(error).__name__}: {error}\n\n"
                "No project files were modified."
            )

        records = [
            self._analyze_context_record(record) for record in raw_records
        ]
        terms = self._context_query_terms(question)
        ranked = []
        for record in records:
            score, reasons = self._score_context_record(
                record, question, terms
            )
            if score > 0:
                candidate = dict(record)
                candidate["score"] = score
                candidate["reasons"] = reasons
                candidate["snippets"] = self._context_snippets(
                    record,
                    terms,
                    self.CONTEXT_TRACE_MAX_SNIPPETS_PER_FILE,
                )
                ranked.append(candidate)

        ranked.sort(
            key=lambda item: (
                item["score"],
                -len(item["relative"]),
            ),
            reverse=True,
        )
        selected = ranked[:self.CONTEXT_TRACE_MAX_FILES]
        if not selected:
            return (
                "ENGINEER CONTEXT TRACE — MANIFEST-BOUNDED\n\n"
                f"Question: {question}\n"
                f"Manifest: {manifest_path}\n"
                f"Manifest-listed Python files considered: {len(records)}\n\n"
                "No relevant bounded source context was found.\n\n"
                "Read-only: no files were modified."
            )

        connections = self._context_connections(selected, records)
        lab = self._compile_context_bundle(selected)
        passed = sum(1 for item in lab["results"] if item["passed"])
        drifted = [
            item for item in selected
            if item["manifest_hash_match"] is False
        ]

        lines = [
            "ENGINEER CONTEXT TRACE — MANIFEST-BOUNDED",
            "",
            f"Question: {question}",
            f"Manifest: {manifest_path}",
            (
                "Source basis: current live files at manifest-listed paths; "
                "the manifest is used as the bounded file list."
            ),
            "",
            f"Manifest-listed Python files considered: {len(records)}",
            f"Relevant files selected: {len(selected)}",
            f"Missing manifest-listed Python files: {len(missing)}",
            f"Skipped files: {len(skipped)}",
            f"Selected files changed since manifest hash: {len(drifted)}",
            "",
            "Disposable multi-file Lab:",
            f"- Compiled successfully: {passed}/{len(lab['results'])}",
            f"- Elapsed: {lab['elapsed_ms']} ms",
            f"- Temporary workspace removed: {lab['removed']}",
            "",
            "Ranked source context:",
        ]

        for index, record in enumerate(selected, start=1):
            hash_state = (
                "MATCHES MANIFEST"
                if record["manifest_hash_match"] is True
                else "CHANGED SINCE MANIFEST"
                if record["manifest_hash_match"] is False
                else "NO MANIFEST HASH"
            )
            lines.extend(
                [
                    "",
                    f"{index}. {record['relative']}",
                    f"   Score: {record['score']}",
                    f"   SHA-256: {record['sha256']}",
                    f"   Manifest state: {hash_state}",
                    f"   Lines: {record['line_count']}",
                ]
            )
            if record["syntax_error"]:
                lines.append(f"   Syntax: FAILED — {record['syntax_error']}")
            else:
                lines.append("   Syntax: PASSED")
            if record["reasons"]:
                lines.append(
                    "   Why selected: " + "; ".join(record["reasons"][:5])
                )
            if record["definitions"]:
                definitions = ", ".join(
                    f"{item['name']}@{item['line']}"
                    for item in record["definitions"][:8]
                )
                lines.append("   Definitions: " + definitions)
            if record["imports"]:
                lines.append(
                    "   Imports: " + ", ".join(record["imports"][:8])
                )
            for snippet in record["snippets"]:
                lines.append(
                    f"   Evidence line {snippet['line']}: {snippet['text']}"
                )

        lines.extend(["", "Import-resolved source connections:"])
        if connections:
            lines.extend(f"- {item}" for item in connections)
        else:
            lines.append(
                "- No import-resolved cross-file connection was "
                "detected within the bounded set."
            )

        failed = [item for item in lab["results"] if not item["passed"]]
        if failed:
            lines.extend(["", "Lab attention:"])
            for item in failed[:6]:
                lines.append(
                    f"- {item['relative']}: {item['output'] or 'compile failed'}"
                )

        lines.extend(
            [
                "",
                "Context bundle status:",
                (
                    f"Assembled from {len(selected)} current source files and "
                    "tested as disposable copies."
                ),
                (
                    "Call edges require an explicit import binding. This remains "
                    "a static source graph, not a complete runtime trace."
                ),
                "",
                "Boundary:",
                "- No live source file was modified.",
                "- No selected module was imported or executed.",
                "- Only manifest-listed Python paths were considered.",
                "- The temporary context workspace was removed.",
            ]
        )
        return "\n".join(lines)

    def parse_grounded_reasoning_request(self, query):
        """Return a question for source-grounded local-model reasoning."""
        text = (query or "").strip()
        if not text:
            return None

        patterns = (
            r"^(?:reason|reasoning)\b",
            r"^(?:grounded\s+analysis|analyze\s+context)\b",
            r"^(?:diagnose|root\s+cause)\b",
            r"^(?:propose\s+(?:a\s+)?patch|draft\s+(?:a\s+)?patch)\b",
            r"^(?:explain\s+(?:the\s+)?cause)\b",
        )
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                remainder = text[match.end():].strip(" :,-")
                return remainder or text
        return None

    @staticmethod
    def _grounded_reasoning_windows(record, terms, limit, radius):
        """Choose evidence windows, prioritizing local imports and calls."""
        lines = record["text"].splitlines()
        folded_terms = [str(term).casefold() for term in terms if str(term)]
        import_question = any(
            term in {"import", "dynamic", "runtime", "lazy", "webui"}
            for term in folded_terms
        )
        candidates = []

        def add(priority, line, reason):
            line = int(line or 0)
            if line >= 1:
                candidates.append((priority, line, reason))

        for binding in record.get("import_bindings", []):
            haystack = " ".join(
                str(binding.get(key) or "")
                for key in ("module", "symbol", "local", "scope")
            ).casefold()
            scope = str(binding.get("scope") or "<module>")
            matched = any(term in haystack for term in folded_terms)
            if matched or (import_question and scope != "<module>"):
                add(0, binding.get("line"), "import binding")
                local = str(binding.get("local") or "")
                if local:
                    for call in record.get("calls", []):
                        target = str(call.get("target") or "")
                        if target == local or target.startswith(local + "."):
                            add(0, call.get("line"), "import-resolved call")

        for snippet in record.get("snippets", []):
            add(1, snippet.get("line"), "query match")

        for definition in record.get("definitions", []):
            name = str(definition.get("name") or "").casefold()
            if any(term in name for term in folded_terms):
                add(2, definition.get("line"), "matching definition")

        if not candidates and record.get("definitions"):
            add(3, record["definitions"][0].get("line", 1), "first definition")
        if not candidates and lines:
            add(4, 1, "file start")

        candidates.sort(key=lambda item: (item[0], item[1]))
        windows = []
        used_ranges = []
        for _priority, center, _reason in candidates:
            if center < 1 or not lines:
                continue
            start = max(1, center - radius)
            end = min(len(lines), center + radius)
            if any(
                not (end < used_start or start > used_end)
                for used_start, used_end in used_ranges
            ):
                continue
            text = "\n".join(
                f"{number:>6}: {lines[number - 1]}"
                for number in range(start, end + 1)
            )
            windows.append({"start": start, "end": end, "text": text})
            used_ranges.append((start, end))
            if len(windows) >= limit:
                break
        return windows

    @staticmethod
    def _grounded_question_mode(question):
        lower = (question or "").casefold()
        historical_markers = (
            "used to", "previously", "before the", "prior version",
            "historical", "formerly", "why did", "used to reach",
        )
        return (
            "historical"
            if any(marker in lower for marker in historical_markers)
            else "current"
        )

    @staticmethod
    def _grounded_proven_facts(selected, connections, question_mode, question=""):
        facts = []

        def add(value):
            if value and value not in facts:
                facts.append(value)

        for connection in connections:
            add(connection)

        selected_paths = {item["relative"] for item in selected}
        for record in selected:
            for binding in record.get("import_bindings", []):
                scope = str(binding.get("scope") or "<module>")
                if scope == "<module>":
                    continue
                module = str(binding.get("module") or "")
                symbol = str(binding.get("symbol") or "")
                target = module.replace(".", "/") + ".py" if module else ""
                if target not in selected_paths:
                    continue
                detail = f" symbol {symbol}" if symbol else ""
                add(
                    f"{record['relative']} has a function-local import of "
                    f"{target}{detail} at line {binding['line']} inside {scope}"
                )

        question_lower = (question or "").casefold()
        function_local_engineer = any(
            "core/foxai_web.py has a function-local import of "
            "core/engineer_agent.py" in item
            for item in facts
        )
        if (
            function_local_engineer
            and "does not show" in question_lower
            and "engineer" in question_lower
        ):
            add(
                "PREMISE CORRECTION: the current analyzer does show the "
                "function-local WebUI Engineer import; explaining why an earlier "
                "trace missed it requires the earlier analyzer source or receipt"
            )

        if question_mode == "historical":
            add(
                "HISTORICAL LIMIT: the supplied bundle contains current live "
                "source and current manifest metadata, not a prior source snapshot; "
                "current code alone cannot prove why an older version behaved differently"
            )
        add(
            "RETRIEVAL LIMIT: query-term mappings, ranking scores, selection "
            "reasons, and imported module names are retrieval metadata—not proof "
            "that a runtime branch executed or caused the reported behavior"
        )
        return facts[:30]

    @staticmethod
    def _grounded_allowed_evidence_lines(selected, connections):
        allowed = {record["relative"]: set() for record in selected}
        for record in selected:
            for window in record.get("reasoning_windows", []):
                allowed[record["relative"]].update(
                    range(int(window["start"]), int(window["end"]) + 1)
                )

        for connection in connections:
            match = re.match(
                r"^(.+?\.py) (?:imports|calls).*? at line (\d+)",
                connection,
            )
            if match and match.group(1) in allowed:
                allowed[match.group(1)].add(int(match.group(2)))
            import_match = re.search(r"import line (\d+)", connection)
            if import_match and match and match.group(1) in allowed:
                allowed[match.group(1)].add(int(import_match.group(1)))
        return allowed

    @staticmethod
    def _grounded_evidence_line_map(selected, allowed):
        line_map = {}
        for record in selected:
            relative = record["relative"]
            source_lines = record.get("text", "").splitlines()
            for number in sorted(allowed.get(relative, set())):
                if 1 <= number <= len(source_lines):
                    line_map[f"{relative}:{number}"] = source_lines[number - 1]
        return line_map

    @staticmethod
    def _grounded_claim_units(answer):
        units = []
        buffer = []
        for raw_line in (answer or "").splitlines():
            stripped = raw_line.strip()
            if not stripped:
                if buffer:
                    units.append(" ".join(buffer))
                    buffer = []
                continue
            if stripped in {
                "LIKELY CAUSE",
                "EVIDENCE",
                "PROPOSED PATCH OR NEXT INSPECTION",
                "RISKS",
                "VALIDATION TESTS",
                "CONFIDENCE",
            }:
                if buffer:
                    units.append(" ".join(buffer))
                    buffer = []
                continue
            buffer.append(stripped)
            if re.search(r"[.!?](?:\s*\[[^\]]+\])?\s*$", stripped):
                units.append(" ".join(buffer))
                buffer = []
        if buffer:
            units.append(" ".join(buffer))
        return units

    @staticmethod
    def _grounded_technical_tokens(claim):
        tokens = set()
        for value in re.findall(r"`([^`]+)`", claim or ""):
            tokens.update(
                item for item in re.findall(
                    r"[A-Za-z_][A-Za-z0-9_.]*(?:\.py)?", value
                )
                if len(item) >= 3
            )
        tokens.update(
            item for item in re.findall(
                r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b",
                claim or "",
            )
            if not item.endswith((".py", ".json", ".md"))
        )
        return sorted(tokens)

    @staticmethod
    def _grounded_mechanism_claims(claim):
        folded = (claim or "").casefold()
        mechanisms = []
        patterns = {
            "importlib.util": ("importlib.util",),
            "__import__": ("__import__",),
            "eval": ("eval(", "via eval", "using eval"),
            "exec": ("exec(", "via exec", "using exec"),
            "configuration-driven loading": (
                "configuration-driven",
                "config-driven",
                "loaded via configuration",
            ),
            "reflection": ("reflection", "reflective loading"),
            "plugin loading": ("plugin loading", "plugin-based loading"),
        }
        for label, markers in patterns.items():
            if any(marker in folded for marker in markers):
                mechanisms.append(label)
        return mechanisms

    @staticmethod
    def _grounded_uncited_required_claims(answer):
        headings = (
            "LIKELY CAUSE",
            "EVIDENCE",
            "PROPOSED PATCH OR NEXT INSPECTION",
            "RISKS",
            "VALIDATION TESTS",
            "CONFIDENCE",
        )
        required = {"LIKELY CAUSE", "EVIDENCE"}
        current = ""
        paragraphs = []
        buffer = []

        def flush():
            nonlocal buffer
            if current in required and buffer:
                paragraphs.append((current, " ".join(buffer)))
            buffer = []

        for raw_line in (answer or "").splitlines():
            stripped = raw_line.strip()
            if stripped in headings:
                flush()
                current = stripped
                continue
            if not stripped:
                flush()
                continue
            if current in required:
                buffer.append(stripped)
        flush()

        citation_pattern = re.compile(
            r"\[[A-Za-z0-9_./()\-]+\.py:\d+\]"
        )
        return [
            {"section": section, "claim": claim}
            for section, claim in paragraphs
            if not citation_pattern.search(claim)
        ]

    def _grounded_claim_support(self, answer, bundle):
        citation_pattern = re.compile(
            r"\[([A-Za-z0-9_./()\-]+\.py):(\d+)\]"
        )
        line_map = bundle.get("evidence_line_map", {})
        proven_text = "\n".join(bundle.get("proven_facts") or []).casefold()
        unsupported = []

        for claim in self._grounded_claim_units(answer):
            citations = citation_pattern.findall(claim)
            if not citations:
                continue
            cited_text = "\n".join(
                line_map.get(f"{relative}:{int(number)}", "")
                for relative, number in citations
            )
            support_text = (cited_text + "\n" + proven_text).casefold()

            for mechanism in self._grounded_mechanism_claims(claim):
                if mechanism.casefold() not in support_text:
                    unsupported.append(
                        {
                            "claim": claim,
                            "reason": (
                                f"technical mechanism '{mechanism}' is absent "
                                "from the cited source and deterministic facts"
                            ),
                        }
                    )

            for token in self._grounded_technical_tokens(claim):
                folded = token.casefold()
                if folded in {
                    "core", "python", "webui", "static", "runtime",
                }:
                    continue
                if folded not in support_text:
                    unsupported.append(
                        {
                            "claim": claim,
                            "reason": (
                                f"technical identifier '{token}' is absent "
                                "from the cited source and deterministic facts"
                            ),
                        }
                    )
        deduped = []
        seen = set()
        for item in unsupported:
            key = (item["claim"], item["reason"])
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    def _validate_grounded_model_answer(self, answer, bundle):
        required_sections = (
            "LIKELY CAUSE",
            "EVIDENCE",
            "PROPOSED PATCH OR NEXT INSPECTION",
            "RISKS",
            "VALIDATION TESTS",
            "CONFIDENCE",
        )
        missing_sections = [
            section for section in required_sections if section not in answer
        ]
        citation_pattern = re.compile(
            r"\[([A-Za-z0-9_./()\-]+\.py):(\d+)\]"
        )
        allowed = bundle.get("allowed_evidence_lines", {})
        valid = []
        invalid = []
        for relative, number_text in citation_pattern.findall(answer):
            number = int(number_text)
            citation = f"[{relative}:{number}]"
            if relative in allowed and number in allowed[relative]:
                valid.append(citation)
            else:
                invalid.append(citation)

        historical_ok = True
        if bundle.get("question_mode") == "historical":
            folded = answer.casefold()
            historical_ok = any(
                phrase in folded
                for phrase in (
                    "insufficient historical evidence",
                    "current live source does not prove",
                    "cannot prove why an older version",
                    "prior source snapshot",
                    "historical evidence is not supplied",
                    "without historical code snapshots",
                    "cannot confirm why older versions",
                    "cannot confirm the historical cause",
                    "current code demonstrates the mechanism, not the historical",
                    "current code alone cannot establish the historical",
                )
            )

        unsupported_claims = self._grounded_claim_support(answer, bundle)
        uncited_required_claims = self._grounded_uncited_required_claims(answer)

        accepted = (
            bool(valid)
            and not missing_sections
            and not invalid
            and historical_ok
            and not unsupported_claims
            and not uncited_required_claims
        )
        return {
            "status": "PASSED" if accepted else "FAILED",
            "valid_citations": list(dict.fromkeys(valid)),
            "invalid_citations": list(dict.fromkeys(invalid)),
            "missing_sections": missing_sections,
            "historical_limit_acknowledged": historical_ok,
            "unsupported_claims": unsupported_claims,
            "uncited_required_claims": uncited_required_claims,
        }

    def _assemble_grounded_reasoning_bundle(self, question):
        manifest_path, _, raw_records, missing, skipped = (
            self._load_context_manifest_records()
        )
        records = [self._analyze_context_record(item) for item in raw_records]
        terms = self._context_query_terms(question)
        question_mode = self._grounded_question_mode(question)
        ranked = []

        for record in records:
            score, reasons = self._score_context_record(record, question, terms)
            if score <= 0:
                continue
            candidate = dict(record)
            candidate["score"] = score
            candidate["reasons"] = reasons
            candidate["snippets"] = self._context_snippets(
                record,
                terms,
                self.CONTEXT_TRACE_MAX_SNIPPETS_PER_FILE,
            )
            ranked.append(candidate)

        ranked.sort(
            key=lambda item: (item["score"], -len(item["relative"])),
            reverse=True,
        )
        selected = ranked[:self.GROUNDED_REASONING_MAX_FILES]
        if not selected:
            return {
                "manifest_path": manifest_path,
                "records": records,
                "selected": [],
                "connections": [],
                "proven_facts": [],
                "allowed_evidence_lines": {},
                "evidence_line_map": {},
                "question_mode": question_mode,
                "lab": {"results": [], "removed": True, "elapsed_ms": 0},
                "missing": missing,
                "skipped": skipped,
                "terms": terms,
                "prompt": "",
            }

        for record in selected:
            record["reasoning_windows"] = self._grounded_reasoning_windows(
                record,
                terms,
                self.GROUNDED_REASONING_MAX_WINDOWS_PER_FILE,
                self.GROUNDED_REASONING_WINDOW_RADIUS,
            )

        connections = self._context_connections(selected, records)
        proven_facts = self._grounded_proven_facts(
            selected, connections, question_mode, question
        )
        allowed_evidence_lines = self._grounded_allowed_evidence_lines(
            selected, connections
        )
        evidence_line_map = self._grounded_evidence_line_map(
            selected, allowed_evidence_lines
        )
        lab = self._compile_context_bundle(selected)

        prompt_lines = [
            "FOXAI ENGINEER GROUNDED SOURCE ANALYSIS — CITATION REQUIRED",
            "",
            "Operator question:",
            question,
            f"Question mode: {question_mode}",
            "",
            "Rules:",
            "1. Use only the supplied deterministic facts, source excerpts, and compile results.",
            "2. Every factual code claim in LIKELY CAUSE and EVIDENCE must cite an exact supplied source line as [relative/path.py:line].",
            "3. Do not cite a line that is absent from the supplied excerpts or deterministic facts.",
            "4. Separate direct observations from engineering inference.",
            "5. Do not claim a runtime path unless an import-resolved connection or excerpt proves it.",
            "6. Query-term mappings, ranking reasons, file selection, and module names are retrieval aids—not proof of causation or execution.",
            "7. Security-related identifiers or imports are not evidence that security caused a behavior unless an executed branch is shown.",
            "8. Do not treat manifest drift as proof of how a prior version behaved.",
            "9. When evidence is insufficient, state that clearly and name the exact prior source, receipt, backup, or additional lines needed.",
            "10. Do not claim that any patch was applied.",
            "11. A proposed diff must be minimal and reviewable; use next-inspection steps when an exact edit is not grounded.",
            "12. A citation is not enough by itself: the cited line must support the specific identifier and mechanism claimed.",
            "13. Never claim importlib, eval, exec, configuration-driven loading, reflection, or plugin loading unless those exact mechanisms appear in cited evidence.",
            "14. A normal import statement inside a function is a function-local or lazy import; do not call it importlib-based loading.",
            "15. If deterministic facts contradict the question's premise, correct the premise before explaining anything else.",
        ]
        if question_mode == "historical":
            prompt_lines.extend(
                [
                    "16. This is a historical question, but the bundle contains current live source only.",
                    "17. You must explicitly say that current live source does not prove the historical cause unless a prior source snapshot is supplied.",
                ]
            )

        prompt_lines.extend(
            [
                "",
                "Return exactly these sections:",
                "LIKELY CAUSE",
                "EVIDENCE",
                "PROPOSED PATCH OR NEXT INSPECTION",
                "RISKS",
                "VALIDATION TESTS",
                "CONFIDENCE",
                "",
                f"Manifest: {manifest_path}",
                f"Selected files: {len(selected)}",
                f"Missing manifest files: {len(missing)}",
                f"Skipped manifest files: {len(skipped)}",
                "",
                "DISPOSABLE LAB RESULTS:",
            ]
        )
        for result in lab["results"]:
            prompt_lines.append(
                f"- {result['relative']}: {'PASS' if result['passed'] else 'FAIL'}"
                + (f" — {result['output']}" if result.get("output") else "")
            )

        prompt_lines.extend(["", "DETERMINISTIC PROVEN FACTS:"])
        if proven_facts:
            prompt_lines.extend(f"- {item}" for item in proven_facts)
        else:
            prompt_lines.append("- No cross-file fact was proven in the bounded set.")

        prompt_lines.extend(["", "SOURCE EVIDENCE:"])
        for index, record in enumerate(selected, start=1):
            state = (
                "MATCHES MANIFEST"
                if record["manifest_hash_match"] is True
                else "CHANGED SINCE MANIFEST"
                if record["manifest_hash_match"] is False
                else "NO MANIFEST HASH"
            )
            prompt_lines.extend(
                [
                    "",
                    f"FILE {index}: {record['relative']}",
                    f"SHA-256: {record['sha256']}",
                    f"Manifest state: {state}",
                    f"Syntax: {'FAILED — ' + record['syntax_error'] if record['syntax_error'] else 'PASSED'}",
                    "Definitions: " + ", ".join(
                        f"{item['name']}@{item['line']}"
                        for item in record["definitions"][:12]
                    ),
                ]
            )
            local_imports = [
                item for item in record.get("import_bindings", [])
                if str(item.get("scope") or "<module>") != "<module>"
            ]
            if local_imports:
                prompt_lines.append(
                    "Function-local imports: " + "; ".join(
                        f"{item.get('module')}.{item.get('symbol')}@{item.get('line')} inside {item.get('scope')}"
                        for item in local_imports[:8]
                    )
                )
            for window in record["reasoning_windows"]:
                prompt_lines.extend(
                    [
                        f"Excerpt lines {window['start']}-{window['end']}:",
                        window["text"],
                    ]
                )

        prompt = "\n".join(prompt_lines)
        if len(prompt) > self.GROUNDED_REASONING_MAX_PROMPT_CHARS:
            prompt = (
                prompt[:self.GROUNDED_REASONING_MAX_PROMPT_CHARS]
                + "\n[CONTEXT TRUNCATED AT BOUNDED PROMPT LIMIT]"
            )

        return {
            "manifest_path": manifest_path,
            "records": records,
            "selected": selected,
            "connections": connections,
            "proven_facts": proven_facts,
            "allowed_evidence_lines": allowed_evidence_lines,
            "evidence_line_map": evidence_line_map,
            "question_mode": question_mode,
            "lab": lab,
            "missing": missing,
            "skipped": skipped,
            "terms": terms,
            "prompt": prompt,
        }

    @staticmethod
    def _grounded_deterministic_resolution(question, bundle):
        """Resolve questions that do not need or cannot support a model call."""
        facts = list(bundle.get("proven_facts") or [])
        question_mode = str(bundle.get("question_mode") or "current")
        question_lower = (question or "").casefold()

        premise_correction = next(
            (
                item for item in facts
                if str(item).startswith("PREMISE CORRECTION:")
            ),
            None,
        )
        import_fact = next(
            (
                item for item in facts
                if "core/foxai_web.py imports core/engineer_agent.py"
                in str(item)
                and "inside web_engineer_analyze" in str(item)
            ),
            None,
        )
        call_fact = next(
            (
                item for item in facts
                if "core/foxai_web.py calls EngineerAgent"
                in str(item)
            ),
            None,
        )

        if premise_correction and import_fact:
            citations = []
            for fact in (import_fact, call_fact):
                match = re.search(r"^(.+?\.py).*? at line (\d+)", str(fact or ""))
                if match:
                    citation = f"[{match.group(1)}:{match.group(2)}]"
                    if citation not in citations:
                        citations.append(citation)
            return {
                "kind": "premise_corrected",
                "title": "DETERMINISTIC RESOLUTION — MODEL NOT NEEDED",
                "summary": (
                    "The current analyzer already detects the function-local "
                    "WebUI Engineer import. Current live source cannot prove why "
                    "an earlier analyzer omitted it."
                ),
                "evidence": [
                    import_fact,
                    *([call_fact] if call_fact else []),
                    premise_correction,
                ],
                "citations": citations,
                "next_step": (
                    "Inspect the earlier Engineer analyzer source, its package "
                    "backup, or the earlier trace receipt to establish the exact "
                    "historical limitation."
                ),
                "reason_model_skipped": (
                    "The current premise is contradicted by deterministic source "
                    "facts, and the historical part requires earlier evidence."
                ),
            }

        if question_mode == "historical":
            historical_limit = next(
                (
                    item for item in facts
                    if str(item).startswith("HISTORICAL LIMIT:")
                ),
                None,
            )
            requested_artifact = (
                "prior source snapshot, backup, mission receipt, diff, or exact "
                "historical source lines"
            )
            return {
                "kind": "historical_evidence_gap",
                "title": "DETERMINISTIC EVIDENCE GAP — MODEL SKIPPED",
                "summary": (
                    "The supplied bundle contains current live source only, so it "
                    "cannot establish why the older route behaved differently."
                ),
                "evidence": [historical_limit] if historical_limit else [],
                "citations": [],
                "next_step": f"Provide a {requested_artifact}.",
                "reason_model_skipped": (
                    "A model cannot convert current source into historical proof; "
                    "calling it would invite unsupported reconstruction."
                ),
            }

        return None

    @staticmethod
    def _format_grounded_deterministic_report(question, bundle, resolution):
        selected = bundle.get("selected") or []
        lab = bundle.get("lab") or {"results": [], "removed": True, "elapsed_ms": 0}
        passed = sum(1 for item in lab.get("results", []) if item.get("passed"))
        lines = [
            "ENGINEER GROUNDED REASONING — " + resolution["title"],
            "",
            f"Question: {question}",
            f"Question mode: {bundle.get('question_mode')}",
            f"Manifest: {bundle.get('manifest_path')}",
            f"Selected source files: {len(selected)}",
            f"Disposable compile results: {passed}/{len(lab.get('results', []))}",
            f"Lab elapsed: {lab.get('elapsed_ms', 0)} ms",
            f"Temporary workspace removed: {lab.get('removed', True)}",
            "Model call: SKIPPED",
            "",
            "DETERMINISTIC ANSWER:",
            resolution["summary"],
        ]
        citations = resolution.get("citations") or []
        if citations:
            lines.append("Source citations: " + " ".join(citations))
        evidence = [item for item in resolution.get("evidence", []) if item]
        if evidence:
            lines.extend(["", "Proven evidence:"])
            lines.extend(f"- {item}" for item in evidence)
        lines.extend(
            [
                "",
                "Why the model was not called:",
                resolution["reason_model_skipped"],
                "",
                "Required next evidence or action:",
                resolution["next_step"],
                "",
                "Evidence boundary:",
                "- Deterministic source selection and disposable compilation completed.",
                "- No model inference was used for this answer.",
                "- No live module was imported or executed.",
                "- No patch was applied and no project file was modified.",
            ]
        )
        return "\\n".join(lines)

    def grounded_reasoning_report(self, question):
        """Ask the local model to reason only over a verified source bundle."""
        try:
            bundle = self._assemble_grounded_reasoning_bundle(question)
        except Exception as error:
            return (
                "ENGINEER GROUNDED REASONING\n\n"
                "Result: CONTEXT ASSEMBLY FAILED\n"
                f"{type(error).__name__}: {error}\n\n"
                "No project files were modified."
            )

        selected = bundle["selected"]
        if not selected:
            return (
                "ENGINEER GROUNDED REASONING — NO CONTEXT\n\n"
                f"Question: {question}\n"
                f"Manifest: {bundle['manifest_path']}\n\n"
                "No relevant manifest-bounded source files were found.\n\n"
                "No model call was made and no files were modified."
            )

        lab = bundle["lab"]
        passed = sum(1 for item in lab["results"] if item["passed"])

        deterministic_resolution = self._grounded_deterministic_resolution(
            question, bundle
        )
        if deterministic_resolution is not None:
            return self._format_grounded_deterministic_report(
                question, bundle, deterministic_resolution
            )

        runner = getattr(self.app, "reason_about_code", None)
        if not callable(runner):
            return (
                "ENGINEER GROUNDED REASONING — MODEL BRIDGE UNAVAILABLE\n\n"
                f"Question: {question}\n"
                f"Selected source files: {len(selected)}\n"
                f"Disposable compile results: {passed}/{len(lab['results'])}\n"
                f"Temporary workspace removed: {lab['removed']}\n\n"
                "The deterministic source bundle was assembled, but this interface "
                "does not provide a local-model reasoning callback.\n\n"
                "No model claim was generated and no files were modified."
            )

        try:
            model_result = runner(bundle["prompt"])
        except Exception as error:
            model_result = {
                "ok": False,
                "answer": "",
                "error": f"{type(error).__name__}: {error}",
            }

        if isinstance(model_result, str):
            ok = bool(model_result.strip())
            answer = model_result.strip()
            error = ""
            model_name = "local model"
        elif isinstance(model_result, dict):
            ok = bool(model_result.get("ok"))
            answer = str(model_result.get("answer") or "").strip()
            error = str(model_result.get("error") or "").strip()
            model_name = str(model_result.get("model") or "local model")
        else:
            ok = False
            answer = ""
            error = "Unsupported model callback result"
            model_name = "local model"

        lines = [
            "ENGINEER GROUNDED REASONING — CITATION-CHECKED SOURCE + LOCAL MODEL",
            "",
            f"Question: {question}",
            f"Question mode: {bundle['question_mode']}",
            f"Manifest: {bundle['manifest_path']}",
            f"Selected source files: {len(selected)}",
            f"Disposable compile results: {passed}/{len(lab['results'])}",
            f"Lab elapsed: {lab['elapsed_ms']} ms",
            f"Temporary workspace removed: {lab['removed']}",
            f"Model: {model_name}",
            "",
            "Deterministic proven facts:",
        ]
        facts = bundle.get("proven_facts") or []
        if facts:
            lines.extend(f"- {item}" for item in facts[:10])
        else:
            lines.append("- No cross-file fact was proven in the bounded set.")
        lines.append("")

        if ok and answer:
            grounding = self._validate_grounded_model_answer(answer, bundle)
            lines.extend(
                [
                    f"Model grounding check: {grounding['status']}",
                    f"Valid source citations: {len(grounding['valid_citations'])}",
                    f"Invalid source citations: {len(grounding['invalid_citations'])}",
                    f"Missing required sections: {len(grounding['missing_sections'])}",
                    f"Unsupported cited claims: {len(grounding['unsupported_claims'])}",
                    f"Uncited LIKELY CAUSE/EVIDENCE claims: {len(grounding['uncited_required_claims'])}",
                ]
            )
            if bundle["question_mode"] == "historical":
                lines.append(
                    "Historical evidence limit acknowledged: "
                    + str(grounding["historical_limit_acknowledged"])
                )
            lines.append("")
            if grounding["status"] == "FAILED":
                lines.extend(
                    [
                        "MODEL DRAFT REJECTED AS GROUNDED:",
                        answer,
                        "",
                        "The draft is shown for inspection but is not accepted as "
                        "grounded because one or more citations were invalid, missing, "
                        "historically insufficient, or did not support the mechanism claimed.",
                    ]
                )
            else:
                lines.extend(["GROUNDED MODEL ANALYSIS:", answer])
            if grounding["invalid_citations"]:
                lines.extend(
                    [
                        "",
                        "Invalid citations:",
                        *(
                            f"- {item}"
                            for item in grounding["invalid_citations"][:12]
                        ),
                    ]
                )
            if grounding["missing_sections"]:
                lines.extend(
                    [
                        "",
                        "Missing sections:",
                        *(
                            f"- {item}"
                            for item in grounding["missing_sections"]
                        ),
                    ]
                )
            if grounding["unsupported_claims"]:
                lines.extend(
                    [
                        "",
                        "Unsupported cited claims:",
                        *(
                            f"- {item['reason']}: {item['claim']}"
                            for item in grounding["unsupported_claims"][:8]
                        ),
                    ]
                )
            if grounding["uncited_required_claims"]:
                lines.extend(
                    [
                        "",
                        "Uncited required claims:",
                        *(
                            f"- {item['section']}: {item['claim']}"
                            for item in grounding["uncited_required_claims"][:8]
                        ),
                    ]
                )
        else:
            lines.extend(
                [
                    "MODEL ANALYSIS UNAVAILABLE:",
                    error or "The local model returned no usable analysis.",
                    "",
                    "The deterministic source selection, proven facts, and compile checks still completed.",
                ]
            )

        lines.extend(
            [
                "",
                "Evidence boundary:",
                "- The model received only bounded excerpts from manifest-listed current source files.",
                "- Function-local imports and import-resolved connections were included.",
                "- Model claims were checked for exact source-line citations.",
                "- Historical claims require historical evidence rather than current-code inference.",
                "- No live module was imported or executed.",
                "- No patch was applied and no project file was modified.",
            ]
        )
        return "\n".join(lines)

    def smart_search_report(self, query):
        target = self.normalize_operator_query(query)

        command_match = re.match(
            r"^(?:smart\s+search|search\s+smart|foxai\s+search)\s+for(?:\s+(.*))?$",
            target,
            flags=re.IGNORECASE,
        )
        if command_match:
            target = (command_match.group(1) or "").strip()

        target = target.strip().strip('"').strip("'").strip()
        if not target:
            return (
                "SMART SEARCH REPORT\n\n"
                "No search target was provided.\n\n"
                "Example:\n"
                "/engineer smart search for COMFY_MAIN\n\n"
                "Safety Status:\n"
                "Read-only. No files were modified."
            )

        return self.smart_search.format_report(target)

    def mission_router_report(self, query, route, reason, pipeline):
        lines = [
            "MISSION ROUTER",
            "",
            "Route:",
            route,
            "",
            "Reason:",
            reason,
            "",
            "Pipeline:",
        ]
        for step in pipeline:
            lines.append(f"• {step}")
        lines.extend([
            "",
            "Query:",
            query,
        ])
        return "\n".join(lines)

    def scan_new_files(self, query):
        """
        Scan/index project files without entering Forge Build mode.
        """
        index = self.build_index()
        summary = index.summary()

        return (
            "ENGINEER FILE SCAN\\n\\n"
            "Route:\\n"
            "Project Index\\n\\n"
            f"Project Root:\\n{self.project_root}\\n\\n"
            f"Files indexed: {summary['file_count']}\\n"
            f"Python files: {summary['python_file_count']}\\n"
            f"Classes detected: {summary['class_count']}\\n"
            f"Functions detected: {summary['function_count']}\\n"
            f"Imports detected: {summary['import_count']}\\n\\n"
            "Safety Status:\\n"
            "Read-only. No files were modified."
        )

    def select_evidence_drivers(self, mission):
        """
        Select relevant evidence drivers for a mission.

        Specialized drivers run first. SourceCodeDriver remains a fallback.
        """
        selected = []

        for driver in self.evidence_drivers:
            can_handle = getattr(driver, "can_handle", None)
            if callable(can_handle) and can_handle(mission):
                selected.append(driver)

        if not selected:
            # Fallback to generic source driver.
            selected = [self.evidence_drivers[-1]]

        return selected

    def investigation_engine_test(self, query):
        """
        Run a real end-to-end Investigation Engine mission through SourceCodeDriver.
        """
        mission = Mission.create(
            department="Engineer",
            intent="Investigation Engine Test",
            query=query,
            requested_drivers=["SourceCodeDriver"],
            metadata={"rc": "20B"},
        )

        selected_drivers = self.select_evidence_drivers(mission)
        self.investigation_engine.drivers = selected_drivers

        result = self.investigation_engine.investigate(mission)

        ranked_evidence = self.evidence_ranker.rank(
            result.evidence,
            query=query,
            department="Engineer",
        )

        lines = [
            "INVESTIGATION ENGINE TEST",
            "",
            "Mission:",
            result.mission.id,
            "",
            "Query:",
            result.mission.query,
            "",
            "Selected Drivers:",
            ", ".join(driver.name for driver in selected_drivers),
            "",
            "Ranked Evidence:",
        ]

        if ranked_evidence:
            for ranked in ranked_evidence[:5]:
                item = ranked.evidence
                lines.append(f"--- {item.path or item.source} ---")
                lines.append(f"Rank Score: {ranked.score}")
                lines.append(f"Category: {item.category}")
                lines.append(f"Confidence: {item.confidence}")
                lines.append(f"Weight: {item.weight}")
                lines.append("Ranking Reasons:")
                for reason in ranked.reasons[:6]:
                    lines.append(f"• {reason}")
                lines.append("")
                lines.append(item.snippet.strip() or "[No snippet]")
                lines.append("")
        else:
            lines.append("No evidence collected.")
            lines.append("")

        assessment = self.recommendation_engine.assess(
            mission=result.mission,
            ranked_evidence=ranked_evidence,
            confidence_report=result.confidence,
            gaps=result.gaps,
        )

        lines.extend([
            "Confidence:",
            f"Evidence Quality: {result.confidence.evidence_quality}",
            f"Coverage: {result.confidence.coverage}",
            f"Agreement: {result.confidence.agreement}",
            f"Overall: {result.confidence.overall}",
            "",
            assessment.report(),
            "",
            "Investigation Engine Raw Recommendation:",
            result.recommendation,
            "",
            "Timeline:",
        ])

        for step in result.timeline:
            lines.append(f"• {step}")

        lines.extend([
            "",
            "Safety Status:",
            "Read-only. Investigation Engine collected evidence but modified no files.",
        ])

        return "\n".join(lines)

    def forge_build(self, query):
        """
        Forge Build RC2

        Handles explicit implementation requests such as Forge Sprint 20A.

        RC2 is intentionally narrow. General scan/search/review requests must
        not enter Forge Build mode.
        """
        lowered = query.lower()

        forge_markers = [
            "forge sprint",
            "begin forge",
            "start forge",
            "build component",
            "create component",
            "create a new file",
            "generate implementation",
            "write the code",
            "build the skeleton",
        ]

        if not any(marker in lowered for marker in forge_markers):
            return self.search_project(query)

        if "investigation_engine.py" in lowered or "investigation engine" in lowered or "forge sprint 20a" in lowered:
            code = 'from __future__ import annotations\n\nfrom abc import ABC, abstractmethod\nfrom dataclasses import dataclass, field\nfrom datetime import datetime\nfrom time import perf_counter\nfrom typing import Any, Dict, List, Optional\nfrom uuid import uuid4\n\n\n@dataclass(frozen=True)\nclass Mission:\n    """\n    A structured investigation request.\n\n    Departments create Missions instead of passing raw strings into the\n    Investigation Engine.\n    """\n    id: str\n    department: str\n    intent: str\n    query: str\n    priority: str = "normal"\n    requested_drivers: List[str] = field(default_factory=list)\n    metadata: Dict[str, Any] = field(default_factory=dict)\n    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))\n\n    @classmethod\n    def create(\n        cls,\n        department: str,\n        intent: str,\n        query: str,\n        priority: str = "normal",\n        requested_drivers: Optional[List[str]] = None,\n        metadata: Optional[Dict[str, Any]] = None,\n    ) -> "Mission":\n        return cls(\n            id=f"INV-{datetime.now().strftime(\'%Y%m%d\')}-{uuid4().hex[:8]}",\n            department=department,\n            intent=intent,\n            query=query,\n            priority=priority,\n            requested_drivers=requested_drivers or [],\n            metadata=metadata or {},\n        )\n\n\n@dataclass(frozen=True)\nclass Evidence:\n    """\n    A single piece of structured evidence.\n    """\n    source: str\n    category: str\n    path: str = ""\n    snippet: str = ""\n    confidence: int = 0\n    weight: int = 0\n    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))\n    metadata: Dict[str, Any] = field(default_factory=dict)\n\n\n@dataclass(frozen=True)\nclass EvidenceGap:\n    """\n    Expected evidence that was not found or not checked.\n    """\n    expected: str\n    reason: str\n    impact: str = "unknown"\n    suggested_driver: str = ""\n\n\n@dataclass(frozen=True)\nclass ConfidenceReport:\n    """\n    Explainable confidence summary for an investigation.\n    """\n    evidence_quality: int = 0\n    coverage: int = 0\n    agreement: int = 0\n    overall: int = 0\n    notes: List[str] = field(default_factory=list)\n\n\n@dataclass(frozen=True)\nclass InvestigationResult:\n    """\n    Final structured result returned by the Investigation Engine.\n    """\n    mission: Mission\n    evidence: List[Evidence]\n    gaps: List[EvidenceGap]\n    confidence: ConfidenceReport\n    recommendation: str\n    risk: str\n    alternatives: List[str]\n    next_step: str\n    timeline: List[str]\n    duration: float\n    metadata: Dict[str, Any] = field(default_factory=dict)\n\n\nclass EvidenceDriver(ABC):\n    """\n    Abstract evidence driver contract.\n\n    Future drivers may inspect source code, configuration, project memory,\n    mission history, Windows logs, images, video, or other evidence sources.\n    """\n\n    name = "EvidenceDriver"\n\n    @abstractmethod\n    def collect(self, mission: Mission) -> List[Evidence]:\n        """Collect evidence for a Mission."""\n        raise NotImplementedError\n\n\nclass InvestigationEngine:\n    """\n    FOXAI Investigation Engine RC1\n\n    Kernel-grade reasoning pipeline skeleton.\n\n    RC1 intentionally contains no SmartSearch integration, filesystem scanning,\n    AI calls, web access, Windows APIs, threading, async, or caching.\n    """\n\n    def __init__(self, kernel=None, drivers: Optional[List[EvidenceDriver]] = None):\n        self.kernel = kernel\n        self.drivers = drivers or []\n\n    def investigate(self, mission: Mission) -> InvestigationResult:\n        """\n        Run the investigation pipeline and return an InvestigationResult.\n        """\n        started = perf_counter()\n        timeline: List[str] = []\n\n        self._publish("MISSION_STARTED", {\n            "mission_id": mission.id,\n            "department": mission.department,\n            "intent": mission.intent,\n        })\n\n        timeline.append(self._stamp("Mission received"))\n\n        plan = self._plan(mission, timeline)\n        evidence = self._collect(mission, plan, timeline)\n        gaps = self._analyze_gaps(mission, plan, evidence, timeline)\n        confidence = self._build_confidence(mission, evidence, gaps, timeline)\n        recommendation, risk, alternatives, next_step = self._build_recommendation(\n            mission,\n            evidence,\n            gaps,\n            confidence,\n            timeline,\n        )\n\n        result = self._build_result(\n            mission=mission,\n            evidence=evidence,\n            gaps=gaps,\n            confidence=confidence,\n            recommendation=recommendation,\n            risk=risk,\n            alternatives=alternatives,\n            next_step=next_step,\n            timeline=timeline,\n            duration=perf_counter() - started,\n            metadata={"plan": plan},\n        )\n\n        self._publish("MISSION_COMPLETED", {\n            "mission_id": mission.id,\n            "department": mission.department,\n            "intent": mission.intent,\n            "duration": result.duration,\n        })\n\n        return result\n\n    def _plan(self, mission: Mission, timeline: List[str]) -> Dict[str, Any]:\n        timeline.append(self._stamp("Plan created"))\n\n        return {\n            "requested_drivers": mission.requested_drivers,\n            "driver_count": len(self.drivers),\n            "rc1_scope": "skeleton_only",\n        }\n\n    def _collect(\n        self,\n        mission: Mission,\n        plan: Dict[str, Any],\n        timeline: List[str],\n    ) -> List[Evidence]:\n        timeline.append(self._stamp("Evidence collection started"))\n\n        evidence: List[Evidence] = []\n\n        for driver in self.drivers:\n            collected = driver.collect(mission)\n            evidence.extend(collected)\n\n        timeline.append(self._stamp(f"Evidence collection completed: {len(evidence)} items"))\n        return evidence\n\n    def _analyze_gaps(\n        self,\n        mission: Mission,\n        plan: Dict[str, Any],\n        evidence: List[Evidence],\n        timeline: List[str],\n    ) -> List[EvidenceGap]:\n        timeline.append(self._stamp("Gap analysis completed"))\n\n        # RC1 skeleton: no required gaps until real drivers define expectations.\n        return []\n\n    def _build_confidence(\n        self,\n        mission: Mission,\n        evidence: List[Evidence],\n        gaps: List[EvidenceGap],\n        timeline: List[str],\n    ) -> ConfidenceReport:\n        timeline.append(self._stamp("Confidence report built"))\n\n        if not evidence:\n            return ConfidenceReport(\n                evidence_quality=0,\n                coverage=0,\n                agreement=0,\n                overall=0,\n                notes=["RC1 skeleton: no evidence drivers produced evidence."],\n            )\n\n        average_quality = int(sum(item.confidence for item in evidence) / len(evidence))\n        average_weight = int(sum(item.weight for item in evidence) / len(evidence))\n\n        return ConfidenceReport(\n            evidence_quality=average_quality,\n            coverage=min(100, len(evidence) * 10),\n            agreement=average_weight,\n            overall=int((average_quality + min(100, len(evidence) * 10) + average_weight) / 3),\n            notes=["Confidence is provisional until RC2 evidence drivers are integrated."],\n        )\n\n    def _build_recommendation(\n        self,\n        mission: Mission,\n        evidence: List[Evidence],\n        gaps: List[EvidenceGap],\n        confidence: ConfidenceReport,\n        timeline: List[str],\n    ) -> tuple[str, str, List[str], str]:\n        timeline.append(self._stamp("Recommendation built"))\n\n        if not evidence:\n            return (\n                "Investigation Engine RC1 completed the pipeline. No evidence was collected because no evidence drivers are active yet.",\n                "low",\n                ["Add SourceCodeDriver in RC2.", "Integrate SmartSearch as an evidence driver."],\n                "Implement the first EvidenceDriver and rerun this mission.",\n            )\n\n        return (\n            "Evidence was collected. Review the structured evidence list before taking action.",\n            "medium",\n            ["Collect additional evidence with more drivers."],\n            "Review evidence and proceed with a department-specific recommendation.",\n        )\n\n    def _build_result(\n        self,\n        mission: Mission,\n        evidence: List[Evidence],\n        gaps: List[EvidenceGap],\n        confidence: ConfidenceReport,\n        recommendation: str,\n        risk: str,\n        alternatives: List[str],\n        next_step: str,\n        timeline: List[str],\n        duration: float,\n        metadata: Optional[Dict[str, Any]] = None,\n    ) -> InvestigationResult:\n        timeline.append(self._stamp("Investigation result assembled"))\n\n        return InvestigationResult(\n            mission=mission,\n            evidence=evidence,\n            gaps=gaps,\n            confidence=confidence,\n            recommendation=recommendation,\n            risk=risk,\n            alternatives=alternatives,\n            next_step=next_step,\n            timeline=timeline,\n            duration=duration,\n            metadata=metadata or {},\n        )\n\n    def _publish(self, event_type: str, payload: Dict[str, Any]):\n        if not self.kernel:\n            return\n\n        try:\n            self.kernel.publish(event_type, payload, source="InvestigationEngine")\n        except Exception:\n            # RC1 must not let event publishing break investigations.\n            pass\n\n    def _stamp(self, message: str) -> str:\n        return f"{datetime.now().isoformat(timespec=\'seconds\')} | {message}"\n'
            return (
                "FORGE BUILD RESULT\n\n"
                "Target:\n"
                "core/investigation_engine.py\n\n"
                "Status:\n"
                "Generated source code for operator review. No files were modified by Engineer.\n\n"
                "```python\n"
                f"{code}\n"
                "```\n\n"
                "Architecture Summary:\n"
                "• Defines kernel-grade dataclasses for missions, evidence, gaps, confidence, and results.\n"
                "• Defines EvidenceDriver as the future pluggable evidence source contract.\n"
                "• Defines InvestigationEngine.investigate() as the single public entry point.\n"
                "• Publishes only MISSION_STARTED and MISSION_COMPLETED when a kernel is supplied.\n"
                "• Contains no filesystem scanning, SmartSearch integration, AI calls, web access, threading, or caching.\n\n"
                "Recommended Integration:\n"
                "• Add this file as core/investigation_engine.py after Chief Architect review.\n"
                "• Later expose it through core/kernel.py.\n"
                "• Later refactor Engineer UI investigations to use this engine."
            )

        return (
            "FORGE BUILD\n\n"
            "Forge Build intent detected, but RC1 only knows how to generate "
            "core/investigation_engine.py for Forge Sprint 20A.\n\n"
            "Next step:\n"
            "Specify the target component or include investigation_engine.py in the request."
        )

    def workshop_status(self):
        """
        Workshop Status RC1

        Reports installed reasoning components and known teaching modules.
        """
        driver_names = [driver.name for driver in getattr(self, "evidence_drivers", [])]
        heuristic_names = [
            getattr(heuristic, "name", heuristic.__class__.__name__)
            for heuristic in getattr(self.recommendation_engine, "heuristics", [])
        ]

        return (
            "FOXAI WORKSHOP STATUS\n\n"
            "Kernel Components:\n"
            "• Investigation Engine: Online\n"
            "• Evidence Ranker: Online\n"
            "• Recommendation Engine: Online\n"
            "• Engineering Assessment: Online\n"
            "• Mission Router: Online\n\n"
            f"Evidence Drivers Installed: {len(driver_names)}\n"
            + "\n".join(f"• {name}" for name in driver_names)
            + "\n\n"
            f"Heuristics Installed: {len(heuristic_names)}\n"
            + "\n".join(f"• {name}" for name in heuristic_names)
            + "\n\n"
            "Current Teaching Domains:\n"
            "• Timeout investigation\n"
            "• Context menu investigation\n"
            "• Spellcheck investigation\n\n"
            "Safety Status:\n"
            "Read-only. Status report only."
        )

    def analyze(self, query):
        query = self.normalize_operator_query(query)
        # FOXAI_ENGINEERING_WORKSHOP_V1_2_ANALYZE_ROUTE
        if re.match(r"^workshop\b", query, flags=re.IGNORECASE):
            workshop_bridge = (
                getattr(self, "engineering_workshop", None)
                or getattr(self, "_engineering_workshop_bridge", None)
            )
            if workshop_bridge is None:
                try:
                    from core.engineering_workshop_bridge import EngineeringWorkshopBridge
                    workshop_bridge = EngineeringWorkshopBridge(self)
                    self._engineering_workshop_bridge = workshop_bridge
                    self.engineering_workshop = workshop_bridge
                except Exception as workshop_error:
                    return (
                        "ENGINEERING WORKSHOP — ROUTE UNAVAILABLE\n\n"
                        "The explicit Workshop command was recognized, but the "
                        "Workshop bridge could not load.\n\n"
                        f"{type(workshop_error).__name__}: {workshop_error}"
                    )
            workshop_report = workshop_bridge.handle(
                query,
                caller="operator",
                operator_approved=True,
            )
            if workshop_report is not None:
                return workshop_report

        lab_path = self.parse_engineering_lab_request(query)
        if lab_path is not None:
            return self.engineering_lab_test(lab_path)

        exact_path = self.parse_exact_path_inspection(query)
        if exact_path is not None:
            return self.inspect_exact_path(exact_path)

        grounded_question = self.parse_grounded_reasoning_request(query)
        if grounded_question is not None:
            return self.grounded_reasoning_report(grounded_question)

        context_question = self.parse_context_trace_request(query)
        if context_question is not None:
            return self.trace_engineering_context(context_question)

        lowered = query.lower()
        intent = self.intent.classify(query)

        if any(term in lowered for term in ["boot report", "kernel boot", "startup readiness", "boot manager"]):
            return self.boot_manager.report()

        if any(term in lowered for term in ["workshop status", "show workshop status", "what do you know", "known domains"]):
            return self.workshop_status()

        if any(term in lowered for term in ["kernel report", "show kernel", "kernel status"]):
            return self.kernel.report()

        if any(term in lowered for term in ["bus report", "workshop bus report", "show bus"]):
            return self.kernel.bus_report()

        if any(term in lowered for term in ["kernel plan", "kernel decision"]):
            return self.kernel.plan(
                query,
                available_models=getattr(self.app, "models", []),
                hardware={"recommended_threads": int(getattr(self.app, "threads", 10))}
            )

        if any(term in lowered for term in ["scan for new files", "scan new files", "rescan files", "reindex project", "scan project files"]):
            return self.scan_new_files(query)

        if any(term in lowered for term in ["router report", "mission router", "show route"]):
            return self.mission_router_report(
                query,
                route="diagnostic",
                reason="Operator requested routing explanation.",
                pipeline=["Engineer", "Mission Router", "Diagnostic Report"],
            )

        if any(term in lowered for term in ["investigation engine test", "test investigation engine", "kernel investigation test"]):
            return self.investigation_engine_test(query)

        if lowered.startswith("engineer, investigate") or any(term in lowered for term in ["investigate timeout", "investigate right click", "investigate context menu", "investigate investigation engine"]):
            return self.investigation_engine_test(query)

        if any(term in lowered for term in ["smart search", "search smart", "foxai search"]):
            return self.smart_search_report(query)

        if any(term in lowered for term in ["show engineer intent", "classify intent", "what intent"]):
            return self.intent.report(query)

        if intent["intent"] == "forge_build":
            # Safety: only explicit creation/build requests should enter Forge Build.
            if any(marker in lowered for marker in [
                "forge sprint", "begin forge", "start forge", "build component",
                "create component", "create a new file", "generate implementation",
                "write the code", "build the skeleton"
            ]):
                return self.forge_build(query)
            return self.search_project(query)

        if intent["intent"] == "architecture_review":
            return self.architecture_review(query)

        if intent["intent"] == "ui_investigation":
            return self.ui_investigation(query)

        if intent["intent"] == "performance_review":
            return self.performance_review(query)

        if intent["intent"] == "security_review":
            return self.security_review(query)

        if any(term in lowered for term in ["project index", "index the project", "build index", "scan the project"]):
            return self.build_index().architecture_report()

        if any(term in lowered for term in ["show project memory", "project memory report", "show forge journal"]):
            return self.kernel.project_memory_report()

        if any(term in lowered for term in ["open project memory for", "open project for"]):
            project, _, _ = self._split_project_note(query)
            return self.kernel.open_project(project)

        if any(term in lowered for term in ["chisel decision for", "log decision for", "record decision for"]):
            project, title, reason = self._split_project_note(query)
            if not title:
                title = "Untitled decision"
            if not reason:
                reason = "No reason provided."
            return self.kernel.chisel_decision(project, title, reason)

        if any(term in lowered for term in ["log lesson for", "chisel lesson for"]):
            project, lesson, reason = self._split_project_note(query)
            if not lesson:
                lesson = "Untitled lesson"
            return self.kernel.record_lesson(project, lesson, reason)

        if any(term in lowered for term in ["log forge for", "forge journal entry for"]):
            project, summary, reason = self._split_project_note(query)
            if not summary:
                summary = "Forge entry recorded"
            lessons = [reason] if reason else []
            return self.kernel.forge_entry(
                project,
                summary=summary,
                lessons=lessons,
                next_hammer="Not specified",
            )

        if any(term in lowered for term in ["project charter", "charter for", "create charter"]):
            return self.forge_master.charter(query)

        if any(term in lowered for term in ["show forge templates", "forge templates", "mission templates"]):
            return self.forge_master.templates_report()

        if any(term in lowered for term in ["forge plan", "forge blueprint", "forge master", "blueprint for"]):
            return self.forge_master.blueprint(query)

        if any(term in lowered for term in ["department registry", "show registry", "show department registry"]):
            return self.decision_layer.registry_report()

        if any(term in lowered for term in ["execution plan", "execution planner", "capability plan", "workflow plan"]):
            return self.decision_layer.execution_plan_report(query)

        if any(term in lowered for term in ["decision report", "decision layer", "recommend model", "model recommendation"]):
            return self.decision_layer.report(
                query,
                available_models=getattr(self.app, "models", []),
                hardware={"recommended_threads": int(getattr(self.app, "threads", 10))}
            )

        if any(term in lowered for term in ["confidence engine", "show confidence", "confidence report"]):
            return self.confidence.card(
                evidence=[
                    {"type": "project_index", "detail": "Engineer can inspect project structure."},
                    {"type": "dependency_graph", "detail": "Engineer can inspect import relationships."},
                    {"type": "runtime_graph", "detail": "Engineer can inspect runtime references."},
                    {"type": "mission_flow", "detail": "Engineer can explain mission paths."},
                    {"type": "technical_debt", "detail": "Engineer can evaluate architecture health."},
                ],
                base=70,
                reason="Confidence Engine RC1 is installed and available to Engineer."
            )

        if any(term in lowered for term in ["technical debt", "debt report", "review the workshop", "architecture review", "workshop review"]):
            report = self.build_technical_debt().review()
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "technical_debt", "detail": "Report is based on AST scanning and file metrics."},
                    {"type": "project_index", "detail": "Reviewed files are limited to FOXAI source scope."},
                ],
                base=75,
                reason="Technical debt findings are metric-based, but recommendations are still engineering guidance."
            )

        if any(term in lowered for term in ["refactor plan", "what should we refactor", "refactor next", "improve architecture"]):
            report = self.build_technical_debt().refactor_plan()
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "technical_debt", "detail": "Refactor targets are based on measured file/function size."},
                    {"type": "inference", "detail": "Suggested extraction boundaries are architectural recommendations."},
                ],
                base=65,
                reason="Refactor plan is grounded in code metrics but should be reviewed before implementation."
            )

        if any(term in lowered for term in ["mission flow", "show mission flows", "show flows"]):
            return self.mission_flow.list_flows()

        if any(term in lowered for term in ["trace", "flow for", "mission path", "mission route"]):
            return self.mission_flow.trace(query)

        if any(term in lowered for term in ["runtime graph", "runtime relationship", "show runtime", "show runtime graph"]):
            report = self.get_runtime_graph().report()
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "runtime_graph", "detail": "Runtime references and call sites were scanned."},
                ],
                base=80,
                reason="Runtime graph reports are grounded in AST-detected attributes, calls, and strings."
            )

        if any(term in lowered for term in ["who uses", "what touches", "runtime uses", "who touches"]):
            report = self.get_runtime_graph().relationship_answer(query)
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "runtime_graph", "detail": "Relationship answer is based on runtime reference scanning."},
                ],
                base=75,
                reason="Runtime relationship analysis can include noisy string references, so review grouped results."
            )

        if any(term in lowered for term in ["dependency graph", "show dependencies", "show dependency graph", "build dependency graph"]):
            report = self.get_dependency_graph().report()
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "dependency_graph", "detail": "Import relationships were scanned."},
                ],
                base=85,
                reason="Dependency graph reports are based on Python import statements."
            )

        if any(term in lowered for term in ["what depends on", "what imports", "used by", "depends on"]):
            report = self.get_dependency_graph().dependency_answer(query)
            return report + "\n\n" + self.confidence_card(
                evidence=[
                    {"type": "dependency_graph", "detail": "Dependency answer is based on import statements."},
                ],
                base=85,
                reason="Import dependency analysis is strong for direct imports but does not capture every runtime relationship."
            )

        if any(term in lowered for term in ["project map", "map the project", "show project map"]):
            return self.project_map()

        if any(term in lowered for term in ["find symbol", "where is function", "where is class", "find class", "find function"]):
            return self.symbol_search(query)

        if any(term in lowered for term in ["review your own code", "review your code", "scan your own code", "scan your code"]):
            return self.project_overview()

        if any(term in lowered for term in ["architecture", "explain the project", "explain this project", "how are you built"]):
            return self.architecture_summary()

        return self.search_project(query)

    def iter_project_files(self):
        for path in self.project_root.rglob("*"):
            if not path.is_file():
                continue

            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue

            if path.suffix.lower() in self.IGNORE_SUFFIXES:
                continue

            if path.suffix.lower() not in self.CODE_EXTENSIONS:
                continue

            yield path

    def read_text_safely(self, path, limit=120000):
        try:
            return path.read_text(
                encoding="utf-8",
                errors="replace",
            )[:limit]
        except Exception:
            return ""

    def project_overview(self):
        index = self.build_index()
        summary = index.summary()

        important = [
            "foxai.py",
            "ui/main_window.py",
            "core/director.py",
            "core/brainstem.py",
            "core/diagnostics.py",
            "core/project_index.py",
            "core/comfy_bridge.py",
            "core/promptsmith.py",
            "core/chat_agent.py",
            "core/red_canvas_agent.py",
            "core/library_agent.py",
            "core/engineer_agent.py",
        ]

        found = []
        missing = []

        for rel in important:
            path = self.project_root / rel
            if path.exists():
                found.append(rel)
            else:
                missing.append(rel)

        return (
            "ENGINEER REPORT\n\n"
            "Mission:\nRead-only self-review\n\n"
            f"Project Root:\n{self.project_root}\n\n"
            f"Files indexed:\n{summary['file_count']}\n"
            f"Python files:\n{summary['python_file_count']}\n"
            f"Classes detected:\n{summary['class_count']}\n"
            f"Functions detected:\n{summary['function_count']}\n"
            f"Imports detected:\n{summary['import_count']}\n\n"
            "Core files found:\n"
            + "\n".join(f"✓ {item}" for item in found)
            + ("\n\nCore files not found:\n" + "\n".join(f"⚠ {item}" for item in missing) if missing else "")
            + "\n\nInitial Assessment:\n"
            "FOXAI is organized around a clear workshop architecture:\n\n"
            "Director → routes missions\n"
            "Brainstem → tracks workshop state\n"
            "Diagnostics → reports system health\n"
            "Project Index → maps code structure\nDependency Graph → maps import relationships\nRuntime Graph → maps object and call-site relationships\nMission Flow → explains request paths through the Workshop\nTechnical Debt Engine → reviews architecture health and refactor candidates\nDecision Layer → recommends department, model, and settings\nForge Master → creates mission blueprints and quality gates\nForge Journal → stores project memory, decisions, lessons, and forge logs\nEngineer Intent → routes engineering questions before raw search and build requests\nSmartSearch → searches FOXAI source before vendor dependencies\nKernel → unified front door for shared Workshop services\nBoot Manager → startup readiness inspection\nInvestigation Engine → shared evidence-driven investigation pipeline\nEvidence Ranker → prioritizes source evidence over backups/vendor/history\nRecommendation Engine → turns ranked evidence into structured assessments\nMission Router → keeps scan/investigate/build paths separated\nEvidence Drivers → specialized source discovery for timeout, context menu, and spellcheck investigations\n"
            "Mission Control → narrates operations\n"
            "Specialists → perform department work\n\n"
            "\n\n"
            + self.confidence_card(
                evidence=[
                    {"type": "project_index", "detail": "Project files, classes, functions, and imports were indexed."},
                    {"type": "direct_file_match", "detail": "Core files were checked directly."},
                ],
                base=70,
                reason="The self-review is based on direct project indexing and known core file checks."
            )
            + "\n\nSafety Status:\nRead-only. No files were modified."
        )

    def architecture_summary(self):
        return (
            "ENGINEER ARCHITECTURE SUMMARY\n\n"
            "FOXAI currently behaves like a modular AI workshop.\n\n"
            "Primary flow:\n"
            "1. Operator enters a request.\n"
            "2. Director classifies the mission.\n"
            "3. Brainstem marks the workshop busy.\n"
            "4. Mission Control narrates the routing.\n"
            "5. A specialist performs the work.\n"
            "6. Brainstem returns the workshop to ready.\n\n"
            "Main departments:\n"
            "• Agent Fox: conversation\n"
            "• Engineer: code and architecture analysis\n"
            "• Diagnostics: workshop health\n"
            "• Dependency Graph: import relationship analysis\n"
            "• Red Canvas: image generation\n"
            "• Iron Library: local file search\n\n"
            "Recommended next architecture improvement:\n"
            "Move identity and theme settings into a profile system so FOXAI, Kayock's Forge, and future variants can share one codebase.\n\n"
            + self.confidence_card(
                evidence=[
                    {"type": "mission_flow", "detail": "Architecture flow is based on known mission routing."},
                    {"type": "project_index", "detail": "Project modules are indexed."},
                    {"type": "inference", "detail": "Identity recommendation is architectural guidance."},
                ],
                base=65,
                reason="The architecture summary combines known Workshop modules with an inferred next design step."
            )
        )

    def project_map(self):
        index = self.get_index()
        summary = index.summary()

        return (
            "ENGINEER PROJECT MAP\n\n"
            "FOXAI\n"
            "│\n"
            "├── foxai.py\n"
            "│   └── Application entry point\n"
            "│\n"
            "├── ui/\n"
            "│   └── main_window.py\n"
            "│       └── Workshop interface and department panels\n"
            "│\n"
            "├── core/\n"
            "│   ├── director.py\n"
            "│   │   └── Mission routing\n"
            "│   ├── brainstem.py\n"
            "│   │   └── Workshop state and neural health\n"
            "│   ├── diagnostics.py\n"
            "│   │   └── Health checks and Workshop Advisor\n"
            "│   ├── project_index.py\n"
            "│   │   └── Read-only code structure index\n"
            "│   ├── engineer_agent.py\n"
            "│   │   └── Engineering specialist\n"
            "│   ├── runtime_graph.py\n"
            "│   │   └── Runtime relationship scanner\n"
            "│   ├── mission_flow.py\n"
            "│   │   └── Mission flow blueprint\n"
            "│   ├── technical_debt.py\n"
            "│   │   └── Architecture review and refactor guidance\n"
            "│   ├── department_registry.py\n"
            "│   │   └── Department capability registry\n"
            "│   ├── decision_layer.py\n"
            "│   │   └── Advisory mission/model/settings recommendation layer\n"
            "│   ├── mission_templates.py\n"
            "│   │   └── Reusable Forge Master templates\n"
            "│   ├── forge_master.py\n"
            "│   │   └── Mission blueprints and quality gates\n"
            "│   ├── project_memory.py\n"
            "│   │   └── Persistent project memory store\n"
            "│   ├── forge_journal.py\n"
            "│   │   └── Decisions, lessons, and forge logs\n"
            "│   ├── engineer_intent.py\n"
            "│   │   └── Engineer mission intent classifier\n"
            "│   ├── smart_search.py\n"
            "│   │   └── Evidence-weighted FOXAI-first search\n"
            "│   ├── kernel.py\n"
            "│   │   └── Unified Kernel facade for shared Workshop services\n"
            "│   ├── boot_manager.py\n"
            "│   │   └── Kernel startup readiness inspection\n"
            "│   ├── comfy_bridge.py\n"
            "│   │   └── ComfyUI bridge\n"
            "│   └── promptsmith.py\n"
            "│       └── Image prompt enhancement\n"
            "│\n"
            "├── Library/\n"
            "│   └── Iron Library content\n"
            "│\n"
            "├── Red Canvas/\n"
            "│   └── Workflows, prompts, and outputs\n"
            "│\n"
            "└── Mission Archive/\n"
            "    └── Saved mission logs\n\n"
            f"Index Summary:\n"
            f"Files indexed: {summary['file_count']}\n"
            f"Python files: {summary['python_file_count']}\n"
            f"Classes: {summary['class_count']}\n"
            f"Functions: {summary['function_count']}\n\n"
            "\n\n"
            + self.confidence_card(
                evidence=[
                    {"type": "project_index", "detail": "Project map uses indexed core files."},
                    {"type": "mission_flow", "detail": "Department responsibilities align with mission flows."},
                ],
                base=70,
                reason="The project map is based on known module locations and established Workshop responsibilities."
            )
            + "\n\nSafety Status:\nRead-only. No files were modified."
        )

    def symbol_search(self, query):
        index = self.get_index()
        terms = self.extract_terms(query)

        # Prefer last meaningful token as likely symbol name.
        symbol = terms[-1] if terms else query.strip()
        hits = index.find_symbol(symbol)

        lines = [
            "ENGINEER SYMBOL SEARCH",
            "",
            f"Symbol Query: {symbol}",
            "",
        ]

        for label, key in [
            ("Classes", "classes"),
            ("Functions", "functions"),
            ("Imports", "imports"),
            ("Files", "files"),
        ]:
            values = hits[key]
            lines.append(f"{label}: {len(values)}")
            for item in values[:10]:
                if key == "files":
                    lines.append(f"• {item['relative']}")
                elif key == "imports":
                    lines.append(f"• {item['module']} in {item['file']}:{item.get('line')}")
                else:
                    lines.append(f"• {item['name']} in {item['file']}:{item.get('line')}")
            lines.append("")

        lines.append("")
        lines.append(self.confidence_card(
            evidence=[
                {"type": "project_index", "detail": "Symbol lookup uses the Project Index."},
            ],
            base=70,
            reason="Symbol search results are based on the read-only project index."
        ))
        lines.append("")
        lines.append("")
        lines.append(self.confidence_card(
            evidence=[
                {"type": "direct_file_match", "detail": "Search results come from direct file text matches."},
                {"type": "project_index", "detail": "Files are filtered through Engineer project scanning."},
            ],
            base=65,
            reason="Project search confidence depends on direct text matches, not semantic understanding."
        ))
        lines.append("")
        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def search_project(self, query):
        terms = self.extract_terms(query)
        if not terms:
            terms = [query.lower()]

        results = []

        for path in self.iter_project_files():
            text = self.read_text_safely(path)
            lowered = text.lower()
            score = 0

            for term in terms:
                if term and term in lowered:
                    score += lowered.count(term)

            if score:
                snippet = self.make_snippet(text, terms)
                results.append((score, path, snippet))

        results.sort(key=lambda item: item[0], reverse=True)

        if not results:
            return (
                "ENGINEER REPORT\n\n"
                f"Query:\n{query}\n\n"
                "No matching project files were found.\n\n"
                "Safety Status:\nRead-only. No files were modified."
            )

        lines = [
            "ENGINEER REPORT",
            "",
            "Mission:",
            "Project search",
            "",
            "Query:",
            query,
            "",
            f"Matches found: {len(results)}",
            "",
            "Top results:",
            "",
        ]

        for score, path, snippet in results[:8]:
            rel = path.relative_to(self.project_root)
            lines.append(f"--- {rel} ---")
            lines.append(f"Score: {score}")
            lines.append(snippet.strip() or "[No readable snippet]")
            lines.append("")

        lines.append("Safety Status:")
        lines.append("Read-only. No files were modified.")

        return "\n".join(lines)

    def extract_terms(self, query):
        lowered = query.lower()

        stop_words = {
            "engineer", "please", "can", "you", "your", "own", "code",
            "find", "where", "what", "why", "how", "the", "is", "are",
            "to", "in", "of", "for", "with", "and", "or", "a", "an",
            "symbol", "function", "class"
        }

        quoted = re.findall(r'"([^"]+)"', lowered)
        words = re.findall(r"[a-zA-Z0-9_\\-]+", lowered)

        terms = quoted[:]
        terms.extend(w for w in words if len(w) > 2 and w not in stop_words)

        compounds = [
            "red canvas", "iron library", "mission control", "workshop advisor",
            "brainstem", "promptsmith", "comfyui", "director", "diagnostics",
            "project index", "kayock's forge"
        ]

        for compound in compounds:
            if compound in lowered and compound not in terms:
                terms.append(compound)

        return list(dict.fromkeys(terms))

    def make_snippet(self, text, terms, radius=350):
        lowered = text.lower()

        for term in terms:
            if not term:
                continue

            index = lowered.find(term.lower())
            if index >= 0:
                start = max(0, index - radius)
                end = min(len(text), index + len(term) + radius)
                snippet = text[start:end]
                return snippet.replace("\r\n", "\n")

        return text[:700].replace("\r\n", "\n")
