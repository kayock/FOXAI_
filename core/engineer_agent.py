print("=" * 60)
print("ENGINEER_AGENT RC22 LOADED")
print(__file__)
print("=" * 60)
from pathlib import Path
import re

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
from core.smart_search import SmartSearch
from core.security_containment import (
    authorize_department_route,
    is_protected_path,
    new_airlock_correlation_id,
    record_authorization_decision,
    redact_secrets,
    record_boundary_denial,
    validate_airlock_route_receipt,
)
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
    Engineer is FOXAI's read-only code and architecture specialist.

    Current goals:
    - Search the FOXAI project.
    - Build a project index.
    - Locate relevant code files.
    - Explain likely architecture areas.
    - Never modify files.
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
        self._active_airlock_context = {}

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
        query = (payload or text or "").strip()
        correlation_id = correlation_id or new_airlock_correlation_id()
        mission_id = (mission_id or "").strip()

        route_receipt_id = ""
        route_context_status = "not_supplied"
        if route_audit_receipt is not None:
            if isinstance(route_audit_receipt, dict):
                route_receipt_id = str(route_audit_receipt.get("receipt_id") or "")
            route_validation = validate_airlock_route_receipt(
                route_audit_receipt,
                expected_actor=caller,
                expected_object="engineering_airlock",
                expected_action="route",
                correlation_id=correlation_id,
                mission_id=mission_id,
            )
            if not route_validation.get("verified"):
                validation_reason = str(
                    (route_validation.get("details") or {}).get("reason")
                    or "Forwarded Engineering Airlock route context is invalid."
                )
                denial_receipt = record_boundary_denial(
                    actor=caller,
                    obj="engineering_airlock",
                    action="route_context",
                    reason=validation_reason,
                    incident_kind="context_mismatch",
                    correlation_id=correlation_id,
                    mission_id=mission_id,
                    receipt_id=route_receipt_id,
                    context_status="mismatch",
                )
                if not denial_receipt.get("verified"):
                    self.app.add_chat(
                        "SYSTEM",
                        (
                            "Engineering Airlock denied: route context validation "
                            "failed and the boundary incident audit also failed closed."
                        ),
                    )
                else:
                    self.app.add_chat(
                        "SYSTEM",
                        f"Engineering Airlock denied: {validation_reason}",
                    )
                return "break"
            route_context_status = "verified"

        authorization = authorize_department_route(
            caller,
            "engineering_airlock",
            "inspect",
            operator_approved=operator_approved,
        )
        audit_receipt = record_authorization_decision(
            authorization,
            correlation_id=correlation_id,
            mission_id=mission_id,
            receipt_id=route_receipt_id,
            context_status=route_context_status,
        )
        if not audit_receipt.get("verified"):
            self.app.add_chat(
                "SYSTEM",
                (
                    "Engineering Airlock denied: the security audit "
                    "receipt could not be verified."
                ),
            )
            return "break"
        if not authorization.allowed:
            self.app.add_chat(
                "SYSTEM",
                f"Engineering Airlock denied: {authorization.reason}",
            )
            return "break"
        self.app.add_chat("ERIC", query)
        self.app.mission_status("Engineer online.\n\nPerforming read-only project analysis.")

        self._active_airlock_context = {
            "actor": authorization.actor,
            "authorization_allowed": bool(authorization.allowed),
            "authorization_reason": authorization.reason,
            "authorization_policy_source": authorization.policy_source,
            "correlation_id": correlation_id,
            "mission_id": mission_id,
            "fox_sentry_receipt_id": str(audit_receipt.get("receipt_id") or ""),
            "route_receipt_id": route_receipt_id,
            "route_context_status": route_context_status,
        }

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
            self.app.add_chat("ENGINEER", f"Engineering analysis failed:\n{error}")
            return "break"
        finally:
            self._active_airlock_context = {}

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
            "Intent:\nSecurity Review\n\n"
            "Initial recommendations:\n"
            "• Keep Engineer read-only by default.\n"
            "• Require operator approval before file writes.\n"
            "• Keep password storage out of plain text.\n"
            "• Avoid executing generated scripts automatically.\n"
            "• Treat browser/download features as a separate trust boundary.\n\n"
            "Safety Status:\nRead-only. No files were modified."
        )

    def parse_exact_path_inspection(self, query):
        """Return the literal path from an explicit Inspect command.

        A recognized Inspect command returns a string, including an empty
        string for a missing path. Non-Inspect requests return None so normal
        Engineer routing can continue.
        """
        first_line = (query or "").splitlines()[0].strip()
        match = re.match(
            r"^inspect(?:\s+file)?(?:\s+(.*))?$",
            first_line,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        raw_path = (match.group(1) or "").strip()
        if len(raw_path) >= 2 and raw_path[0] == raw_path[-1]:
            if raw_path[0] in {'"', "'"}:
                raw_path = raw_path[1:-1].strip()
        return raw_path

    def resolve_exact_inspection_path(self, raw_path):
        """Resolve one absolute path and keep it inside the project root."""
        value = (raw_path or "").strip()
        if not value:
            return None, "No file path was supplied after Inspect."

        if value.startswith("\\\\") or value.startswith("//"):
            return None, "UNC and network paths are outside the Engineering Airlock."

        drive_match = re.match(r"^[A-Za-z]:", value)
        remainder = value[2:] if drive_match else value
        if ":" in remainder:
            return None, "Alternate data streams are not allowed."

        candidate = Path(value)
        if not candidate.is_absolute():
            return None, "Exact-path inspection requires an absolute file path."

        try:
            root = self.project_root.resolve(strict=True)
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            return None, "The requested file does not exist."
        except Exception as error:
            return None, f"The requested path could not be resolved: {type(error).__name__}."

        try:
            resolved.relative_to(root)
        except ValueError:
            return None, "The requested file resolves outside the FOXAI project root."

        if is_protected_path(resolved, root):
            return None, "The requested file is protected by the Engineering Airlock."
        if not resolved.is_file():
            return None, "The requested path is not a regular file."
        if resolved.suffix.lower() not in self.CODE_EXTENSIONS:
            return None, "The requested file type is not approved for text inspection."

        try:
            size = resolved.stat().st_size
        except OSError as error:
            return None, f"The requested file metadata could not be read: {type(error).__name__}."
        if size > self.EXACT_INSPECTION_MAX_BYTES:
            return None, (
                "The requested file is too large for bounded exact-path "
                f"inspection ({size} bytes; limit {self.EXACT_INSPECTION_MAX_BYTES})."
            )

        return resolved, ""

    def _brief_exact_file_summary(self, path, text):
        lines = text.splitlines()
        nonempty = [line.strip() for line in lines if line.strip()]
        title = ""
        if path.suffix.lower() == ".md":
            for line in nonempty:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break

        opening_lines = nonempty[:6]
        opening = " ".join(opening_lines)
        if len(opening) > 700:
            opening = opening[:697].rstrip() + "..."

        kind = {
            ".md": "Markdown document",
            ".py": "Python source file",
            ".json": "JSON document",
            ".bat": "Windows batch script",
            ".ps1": "PowerShell script",
            ".yaml": "YAML document",
            ".yml": "YAML document",
            ".ini": "INI configuration file",
            ".txt": "text document",
        }.get(path.suffix.lower(), "text file")

        parts = [
            f"{kind} with {len(lines)} line(s).",
        ]
        if title:
            parts.append(f"Title: {title}.")
        if opening:
            parts.append(f"Opening content: {opening}")
        else:
            parts.append("The file contains no non-empty text lines.")
        return " ".join(parts)

    def _record_exact_path_denial(self, denial_reason):
        context = dict(getattr(self, "_active_airlock_context", {}) or {})
        if not context.get("correlation_id") or not context.get("mission_id"):
            return {
                "state": "context_not_supplied",
                "verified": False,
                "receipt_id": "",
                "details": {
                    "event": {
                        "severity": "WARNING",
                        "incident_kind": "protected_resource_denial",
                        "attempt_count": 1,
                        "context_status": "not_supplied",
                    },
                    "reason": (
                        "Boundary denial remained enforced, but no trusted mission "
                        "context was supplied for an immutable incident append."
                    ),
                },
            }
        return record_boundary_denial(
            actor=context.get("actor") or "engineer",
            obj="engineering_airlock",
            action="inspect_path",
            reason=f"Exact-path inspection denied: {denial_reason}",
            incident_kind="protected_resource_denial",
            correlation_id=context.get("correlation_id"),
            mission_id=context.get("mission_id"),
            receipt_id=context.get("fox_sentry_receipt_id"),
            context_status=context.get("route_context_status") or "not_supplied",
        )


    def _format_exact_path_denial(
        self,
        raw_path,
        denial_reason,
        boundary_receipt,
        *,
        resolved_path=None,
    ):
        context = dict(getattr(self, "_active_airlock_context", {}) or {})
        event = (boundary_receipt.get("details") or {}).get("event") or {}
        boundary_verified = bool(boundary_receipt.get("verified"))
        if boundary_verified:
            boundary_state = "RECORDED"
        elif boundary_receipt.get("state") == "context_not_supplied":
            boundary_state = "NOT RECORDED — TRUSTED CONTEXT NOT SUPPLIED"
        else:
            boundary_state = "AUDIT FAILED CLOSED"
        displayed_path = resolved_path or raw_path or "[not supplied]"
        return (
            "ENGINEER EXACT-PATH INSPECTION\n\n"
            "Mission:\nExact file inspection\n\n"
            "Authorization:\nAUTHORIZED FOR READ-ONLY INSPECTION\n\n"
            "Path Decision:\nDENIED\n\n"
            f"Requested Path:\n{displayed_path}\n\n"
            f"Reason:\n{denial_reason}\n\n"
            f"Correlation ID:\n{context.get('correlation_id') or '[not supplied]'}\n\n"
            f"Mission ID:\n{context.get('mission_id') or '[not supplied]'}\n\n"
            "Fox Sentry Authorization Receipt ID:\n"
            f"{context.get('fox_sentry_receipt_id') or '[not supplied]'}\n\n"
            f"Boundary Incident:\n{boundary_state}\n\n"
            f"Boundary Severity:\n{event.get('severity') or '[unverified]'}\n\n"
            f"Incident Kind:\n{event.get('incident_kind') or 'protected_resource_denial'}\n\n"
            f"Attempt Count:\n{event.get('attempt_count') or '[unverified]'}\n\n"
            f"Context Status:\n{event.get('context_status') or context.get('route_context_status') or '[not supplied]'}\n\n"
            "Boundary Receipt ID:\n"
            f"{boundary_receipt.get('receipt_id') or '[not supplied]'}\n\n"
            "Safety Status:\n"
            "Read-only. No file was opened and no files were modified."
        )

    def inspect_exact_path(self, raw_path):
        """Read and summarize exactly one approved project text file."""
        context = dict(getattr(self, "_active_airlock_context", {}) or {})
        resolved, denial_reason = self.resolve_exact_inspection_path(raw_path)

        if resolved is None:
            receipt = self._record_exact_path_denial(denial_reason)
            return self._format_exact_path_denial(
                raw_path,
                denial_reason,
                receipt,
            )

        try:
            data = resolved.read_bytes()
        except OSError as error:
            denial_reason = f"The file could not be read: {type(error).__name__}."
            receipt = self._record_exact_path_denial(denial_reason)
            return self._format_exact_path_denial(
                raw_path,
                denial_reason,
                receipt,
                resolved_path=resolved,
            )

        if b"\x00" in data:
            denial_reason = "Binary content was detected."
            receipt = self._record_exact_path_denial(denial_reason)
            return self._format_exact_path_denial(
                raw_path,
                denial_reason,
                receipt,
                resolved_path=resolved,
            )

        decoded = data.decode("utf-8", errors="replace")
        redacted, redaction_count = redact_secrets(
            decoded[:self.EXACT_INSPECTION_MAX_CHARS]
        )
        summary = self._brief_exact_file_summary(resolved, redacted)
        authorization = (
            "AUTHORIZED"
            if context.get("authorization_allowed", True)
            else "DENIED"
        )

        return (
            "ENGINEER EXACT-PATH INSPECTION\n\n"
            "Mission:\nExact file inspection\n\n"
            f"Authorization:\n{authorization}\n\n"
            "Authorization Reason:\n"
            f"{context.get('authorization_reason') or 'Read-only Engineer inspection authorized.'}\n\n"
            f"Inspected Path:\n{resolved}\n\n"
            f"Correlation ID:\n{context.get('correlation_id') or '[not supplied]'}\n\n"
            f"Mission ID:\n{context.get('mission_id') or '[not supplied]'}\n\n"
            "Fox Sentry Receipt ID:\n"
            f"{context.get('fox_sentry_receipt_id') or '[not supplied]'}\n\n"
            f"Route Context Status:\n{context.get('route_context_status') or 'not_supplied'}\n\n"
            f"File Size:\n{len(data)} bytes\n\n"
            f"Secret Redactions Applied:\n{redaction_count}\n\n"
            f"Brief Summary:\n{summary}\n\n"
            "Safety Status:\n"
            "Read-only. Exactly one file was read. No files were modified."
        )

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
        exact_path = self.parse_exact_path_inspection(query)
        if exact_path is not None:
            return self.inspect_exact_path(exact_path)

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

            if is_protected_path(path, self.project_root):
                continue

            if path.suffix.lower() in self.IGNORE_SUFFIXES:
                continue

            if path.suffix.lower() not in self.CODE_EXTENSIONS:
                continue

            yield path

    def read_text_safely(self, path, limit=120000):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            redacted, _ = redact_secrets(text[:limit])
            return redacted
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
