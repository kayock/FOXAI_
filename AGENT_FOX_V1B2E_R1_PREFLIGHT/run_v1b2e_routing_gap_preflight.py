from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

MISSION_ID = "ENG-20260722-223348-83B942"
TITLE = "Agent Fox Technical Core V1B-2E R1 Real GUI Shared Resource Routing Gap Preflight"
ROOT = Path(r"Z:\FOXAI")
CORE = ROOT / "System" / "AgentFoxTechnicalCore"
MISSIONS = ROOT / "System" / "EngineeringWorkshop" / "missions"
FINAL_DIR = MISSIONS / f"{MISSION_ID}_V1B2E_R1_REAL_GUI_ROUTING_GAP_PREFLIGHT"
TEMP_DIR = MISSIONS / f".{MISSION_ID}_V1B2E_R1_REAL_GUI_ROUTING_GAP_PREFLIGHT_BUILDING"

PRIMARY_PATHS = {
    "webui_source": ROOT / "core" / "foxai_web.py",
    "desktop_source": ROOT / "ui" / "main_window.py",
    "adapter": CORE / "self_knowledge_chat_adapter_v1.py",
    "webui_helper": CORE / "webui_self_knowledge_integration_v1.py",
    "desktop_helper": CORE / "desktop_self_knowledge_integration_v1.py",
    "resource_provider": CORE / "resource_evidence_provider_v1.py",
    "contract": CORE / "SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json",
    "fixtures": CORE / "SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json",
}

KNOWN_HASHES = {
    "webui_source": "d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952",
    "desktop_source": "a9c5bb86878e5f0cd27d221dbb32688b337e6026073a4b66d83339e0aef294a3",
    "adapter": "1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275",
    "webui_helper": "451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69",
    "desktop_helper": "1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4",
    "resource_provider": "41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680",
    "contract": "60b6b5394849a5cd0a192be137deb01be39d2c3f8fd3e4fa75421b94ab5a9ab1",
    "fixtures": "f2fab44d7926a4f46706e369eb853b790137a29ff4b6df689deeab44e9327b13",
}

OUTPUT_NAMES = (
    "REAL_GUI_ROUTE_TRACE.json",
    "WEBUI_MESSAGE_PATH.json",
    "DESKTOP_MESSAGE_PATH.json",
    "DIRECTOR_KEYWORD_FINDINGS.json",
    "COMMAND_PRECEDENCE_FINDINGS.json",
    "MODEL_LABEL_FINDINGS.json",
    "MINIMAL_IMPLEMENTATION_RECOMMENDATION.json",
    "V1B2E_R1_PREFLIGHT_RECEIPT.json",
)

# Bounded candidate modules only. The script does not recurse through the project tree.
ROUTING_MODULE_HINTS = (
    "director",
    "route",
    "router",
    "department",
    "mission",
    "engineer",
    "workshop",
    "chat",
    "agent",
)

SELF_KNOWLEDGE_TERMS = (
    "FOXAI_SELF_KNOWLEDGE",
    "route_http_request",
    "route_desktop_message",
    "self_knowledge_chat_adapter_v1",
    "webui_self_knowledge_integration_v1",
    "desktop_self_knowledge_integration_v1",
)
COMMAND_TERMS = (
    "startswith(\"/\")",
    "startswith('/')",
    "/engineer",
    "/help",
    "slash command",
    "workshop status",
)
DIRECTOR_TERMS = (
    "DIRECTOR ANALYSIS",
    "director",
    "Selected Department",
    "engineering trigger",
    "Mission Type",
    "Confidence Score",
)
MODEL_TERMS = (
    "[Model:",
    "model_label",
    "model name",
    "Initializing neural engine",
    "Shared neural engine online",
)
DISPATCH_TERMS = (
    "get_ai_response",
    "model",
    "specialist",
    "department",
    "engineer",
    "director",
    "dispatch",
    "route",
    "send_message",
    "do_POST",
)


@dataclass(frozen=True)
class SourceFile:
    logical_name: str
    path: Path
    text: str
    lines: list[str]
    tree: ast.AST
    sha256: str
    size_bytes: int


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:16].upper()}"


def is_k_path(path: Path | str) -> bool:
    return str(path).casefold().startswith("k:\\")


def read_source(logical_name: str, path: Path) -> SourceFile:
    if is_k_path(path):
        raise AssertionError("K path rejected")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    tree = ast.parse(text, filename=str(path))
    return SourceFile(
        logical_name=logical_name,
        path=path,
        text=text,
        lines=text.splitlines(),
        tree=tree,
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
    )


def bounded_snippet(source: SourceFile, start_line: int, end_line: int, padding: int = 2, ceiling: int = 24) -> dict[str, Any]:
    start = max(1, int(start_line) - padding)
    end = min(len(source.lines), int(end_line) + padding)
    if end - start + 1 > ceiling:
        end = start + ceiling - 1
    return {
        "path": str(source.path),
        "start_line": start,
        "end_line": end,
        "lines": [
            {"line": number, "text": source.lines[number - 1][:500]}
            for number in range(start, end + 1)
        ],
    }


def full_name(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def function_records(source: SourceFile) -> list[dict[str, Any]]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(source.tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    rows: list[dict[str, Any]] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        owner = None
        cursor = parents.get(node)
        while cursor is not None:
            if isinstance(cursor, ast.ClassDef):
                owner = cursor.name
                break
            cursor = parents.get(cursor)
        qualified = f"{owner}.{node.name}" if owner else node.name
        calls: list[dict[str, Any]] = []
        strings: list[dict[str, Any]] = []
        names: list[dict[str, Any]] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = full_name(child.func)
                if name:
                    calls.append({"name": name, "line": getattr(child, "lineno", None)})
            elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                strings.append({"value": child.value[:500], "line": getattr(child, "lineno", None)})
            elif isinstance(child, ast.Name):
                names.append({"name": child.id, "line": getattr(child, "lineno", None)})
        rows.append({
            "qualified_name": qualified,
            "name": node.name,
            "owner": owner,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "calls": sorted(calls, key=lambda row: (row["line"] or 0, row["name"])),
            "strings": sorted(strings, key=lambda row: (row["line"] or 0, row["value"])),
            "names": sorted(names, key=lambda row: (row["line"] or 0, row["name"])),
        })
    return sorted(rows, key=lambda row: (row["start_line"], row["qualified_name"]))


def line_hits(source: SourceFile, terms: Iterable[str], *, case_sensitive: bool = False, max_hits: int = 200) -> list[dict[str, Any]]:
    needles = list(terms)
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(source.lines, start=1):
        haystack = line if case_sensitive else line.casefold()
        matched = [term for term in needles if (term if case_sensitive else term.casefold()) in haystack]
        if matched:
            rows.append({"line": index, "matched_terms": matched, "text": line[:1000]})
            if len(rows) >= max_hits:
                break
    return rows


def imported_modules(source: SourceFile) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                rows.append({"module": alias.name, "name": None, "alias": alias.asname, "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                rows.append({"module": module, "name": alias.name, "alias": alias.asname, "line": node.lineno})
    return sorted(rows, key=lambda row: (row["line"], row["module"], row["name"] or ""))


def module_to_path(module: str) -> Path | None:
    if not module:
        return None
    parts = module.split(".")
    if parts[0] not in {"core", "ui", "System"}:
        return None
    py = ROOT.joinpath(*parts).with_suffix(".py")
    init = ROOT.joinpath(*parts) / "__init__.py"
    if py.is_file():
        return py
    if init.is_file():
        return init
    return None


def discover_relevant_imports(primary_sources: list[SourceFile]) -> list[Path]:
    paths: dict[str, Path] = {}
    for source in primary_sources:
        for row in imported_modules(source):
            combined = f"{row['module']} {row['name'] or ''}".casefold()
            if not any(hint in combined for hint in ROUTING_MODULE_HINTS):
                continue
            candidate = module_to_path(row["module"])
            if candidate is not None and candidate not in PRIMARY_PATHS.values():
                paths[str(candidate).casefold()] = candidate
    # One bounded second hop through discovered routing modules.
    first_hop = list(paths.values())[:24]
    for index, path in enumerate(first_hop):
        try:
            source = read_source(f"routing_import_{index+1}", path)
        except Exception:
            continue
        for row in imported_modules(source):
            combined = f"{row['module']} {row['name'] or ''}".casefold()
            if not any(hint in combined for hint in ROUTING_MODULE_HINTS):
                continue
            candidate = module_to_path(row["module"])
            if candidate is not None and candidate not in PRIMARY_PATHS.values():
                paths[str(candidate).casefold()] = candidate
            if len(paths) >= 40:
                break
        if len(paths) >= 40:
            break
    return sorted(paths.values(), key=lambda path: str(path).casefold())[:40]


def relevant_functions(source: SourceFile) -> list[dict[str, Any]]:
    rows = function_records(source)
    selected: list[dict[str, Any]] = []
    for row in rows:
        corpus = " ".join(
            [row["qualified_name"]]
            + [call["name"] for call in row["calls"]]
            + [item["value"] for item in row["strings"]]
            + [item["name"] for item in row["names"]]
        ).casefold()
        if any(term.casefold() in corpus for term in SELF_KNOWLEDGE_TERMS + COMMAND_TERMS + DIRECTOR_TERMS + DISPATCH_TERMS):
            selected.append(row)
    return selected


def event_rows_for_function(row: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for call in row["calls"]:
        name = call["name"]
        lowered = name.casefold()
        kind = None
        if "route_http_request" in lowered or "route_desktop_message" in lowered or "self_knowledge" in lowered:
            kind = "self_knowledge"
        elif "director" in lowered or "department" in lowered:
            kind = "director_or_department"
        elif "engineer" in lowered or "workshop" in lowered:
            kind = "engineer_or_workshop"
        elif any(term in lowered for term in ("model", "get_ai_response", "specialist", "generate", "completion")):
            kind = "model_or_specialist"
        elif "add_chat" in lowered or "send" in lowered or "write" in lowered:
            kind = "render_or_send"
        if kind:
            events.append({"kind": kind, "line": call["line"], "symbol": name})
    for item in row["strings"]:
        lowered = item["value"].casefold()
        if item["value"].lstrip().startswith("/") or "slash command" in lowered:
            events.append({"kind": "slash_command_literal", "line": item["line"], "symbol": item["value"][:160]})
        if "[model:" in lowered:
            events.append({"kind": "model_label_literal", "line": item["line"], "symbol": item["value"][:160]})
    return sorted(events, key=lambda event: (event["line"] or 0, event["kind"], event["symbol"]))


def build_surface_path(source: SourceFile, surface: str) -> dict[str, Any]:
    funcs = relevant_functions(source)
    rows: list[dict[str, Any]] = []
    for function in funcs:
        events = event_rows_for_function(function)
        if not events:
            continue
        first_self = min((event["line"] for event in events if event["kind"] == "self_knowledge" and event["line"]), default=None)
        first_director = min((event["line"] for event in events if event["kind"] in {"director_or_department", "engineer_or_workshop"} and event["line"]), default=None)
        first_model = min((event["line"] for event in events if event["kind"] == "model_or_specialist" and event["line"]), default=None)
        rows.append({
            "qualified_name": function["qualified_name"],
            "start_line": function["start_line"],
            "end_line": function["end_line"],
            "events": events,
            "first_self_knowledge_line": first_self,
            "first_director_or_department_line": first_director,
            "first_model_or_specialist_line": first_model,
            "self_knowledge_before_director": bool(first_self and (not first_director or first_self < first_director)),
            "self_knowledge_before_model": bool(first_self and (not first_model or first_self < first_model)),
            "snippet": bounded_snippet(source, function["start_line"], min(function["end_line"], function["start_line"] + 22), padding=0),
        })
    likely = [
        row for row in rows
        if (surface == "webui" and ("do_POST" in row["qualified_name"] or "chat" in row["qualified_name"].casefold()))
        or (surface == "desktop" and ("send_message" in row["qualified_name"] or "submit" in row["qualified_name"].casefold()))
    ]
    if not likely:
        likely = rows[:20]
    seam_hits = line_hits(source, SELF_KNOWLEDGE_TERMS, max_hits=80)
    command_hits = line_hits(source, COMMAND_TERMS, max_hits=80)
    return {
        "schema": "foxai.agent_fox.technical_core.v1b2e.surface_path.v1",
        "mission_id": MISSION_ID,
        "surface": surface,
        "source": str(source.path),
        "source_sha256": source.sha256,
        "source_size_bytes": source.size_bytes,
        "self_knowledge_seam_hits": seam_hits,
        "command_hits": command_hits,
        "candidate_message_functions": likely,
        "static_only": True,
    }


def scan_director_findings(sources: list[SourceFile]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    evidence_literals: list[dict[str, Any]] = []
    engineering_literals: list[dict[str, Any]] = []
    for source in sources:
        for node in ast.walk(source.tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value
            lowered = value.casefold()
            if "evidence" in lowered:
                evidence_literals.append({
                    "path": str(source.path),
                    "line": getattr(node, "lineno", None),
                    "literal": value[:500],
                    "snippet": bounded_snippet(source, getattr(node, "lineno", 1), getattr(node, "end_lineno", getattr(node, "lineno", 1))),
                })
            if any(term in lowered for term in ("engineering trigger", "mission type", "selected department", "engineer mission")):
                engineering_literals.append({
                    "path": str(source.path),
                    "line": getattr(node, "lineno", None),
                    "literal": value[:500],
                    "snippet": bounded_snippet(source, getattr(node, "lineno", 1), getattr(node, "end_lineno", getattr(node, "lineno", 1))),
                })
        for function in function_records(source):
            function_corpus = " ".join(
                [function["qualified_name"]]
                + [item["value"] for item in function["strings"]]
                + [item["name"] for item in function["names"]]
            ).casefold()
            if "evidence" not in function_corpus:
                continue
            if not any(term in function_corpus for term in ("engineer", "engineering", "department", "director", "mission")):
                continue
            findings.append({
                "finding_id": stable_id("DIRECTOR-EVIDENCE", source.path, function["qualified_name"], function["start_line"]),
                "path": str(source.path),
                "qualified_name": function["qualified_name"],
                "start_line": function["start_line"],
                "end_line": function["end_line"],
                "classification": "evidence_and_engineering_terms_share_routing_scope",
                "risk": "ordinary self-knowledge questions containing the noun evidence may be classified as Engineering before the shared adapter",
                "snippet": bounded_snippet(source, function["start_line"], min(function["end_line"], function["start_line"] + 28), padding=0, ceiling=30),
            })
    return {
        "schema": "foxai.agent_fox.technical_core.v1b2e.director_keywords.v1",
        "mission_id": MISSION_ID,
        "files_examined": len(sources),
        "evidence_literal_count": len(evidence_literals),
        "engineering_literal_count": len(engineering_literals),
        "scope_collision_findings": findings,
        "evidence_literals": evidence_literals[:120],
        "engineering_literals": engineering_literals[:120],
        "static_only": True,
    }


def scan_command_precedence(sources: list[SourceFile], web_path: dict[str, Any], desktop_path: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source in sources:
        functions = function_records(source)
        for function in functions:
            slash_lines = sorted({item["line"] for item in function["strings"] if item["value"].lstrip().startswith("/") or "slash command" in item["value"].casefold() if item["line"]})
            self_lines = sorted({call["line"] for call in function["calls"] if "self_knowledge" in call["name"].casefold() or "route_http_request" in call["name"].casefold() or "route_desktop_message" in call["name"].casefold() if call["line"]})
            director_lines = sorted({call["line"] for call in function["calls"] if any(term in call["name"].casefold() for term in ("director", "department", "engineer", "workshop")) if call["line"]})
            if not (slash_lines or self_lines or director_lines):
                continue
            rows.append({
                "path": str(source.path),
                "qualified_name": function["qualified_name"],
                "start_line": function["start_line"],
                "slash_literal_lines": slash_lines,
                "self_knowledge_call_lines": self_lines,
                "director_or_command_call_lines": director_lines,
                "observed_precedence": {
                    "slash_before_self_knowledge": bool(slash_lines and self_lines and min(slash_lines) < min(self_lines)),
                    "self_knowledge_before_director": bool(self_lines and (not director_lines or min(self_lines) < min(director_lines))),
                },
                "snippet": bounded_snippet(source, function["start_line"], min(function["end_line"], function["start_line"] + 24), padding=0, ceiling=26),
            })
    return {
        "schema": "foxai.agent_fox.technical_core.v1b2e.command_precedence.v1",
        "mission_id": MISSION_ID,
        "webui_surface_summary": {
            "slash_hits": len(web_path["command_hits"]),
            "self_knowledge_hits": len(web_path["self_knowledge_seam_hits"]),
        },
        "desktop_surface_summary": {
            "slash_hits": len(desktop_path["command_hits"]),
            "self_knowledge_hits": len(desktop_path["self_knowledge_seam_hits"]),
        },
        "function_precedence_rows": rows,
        "required_order": [
            "exact slash-command handling",
            "shared self-knowledge adapter",
            "department/director routing",
            "ordinary model dispatch",
        ],
        "static_only": True,
    }


def scan_model_labels(sources: list[SourceFile]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source in sources:
        hits = line_hits(source, MODEL_TERMS, max_hits=160)
        for hit in hits:
            rows.append({
                "finding_id": stable_id("MODEL-LABEL", source.path, hit["line"], hit["text"]),
                "path": str(source.path),
                "line": hit["line"],
                "matched_terms": hit["matched_terms"],
                "text": hit["text"],
                "snippet": bounded_snippet(source, hit["line"], hit["line"], padding=3, ceiling=12),
            })
    return {
        "schema": "foxai.agent_fox.technical_core.v1b2e.model_labels.v1",
        "mission_id": MISSION_ID,
        "candidate_label_site_count": len(rows),
        "candidate_label_sites": rows,
        "observed_gui_symptom": "Desktop transcript accumulated repeated [Model: ...] prefixes across later responses.",
        "implementation_constraint": "The renderer should add at most one model label and should not prepend when the response already begins with a model label.",
        "static_only": True,
    }


def first_line_for_kind(surface_doc: dict[str, Any], kind: str) -> int | None:
    values: list[int] = []
    for function in surface_doc["candidate_message_functions"]:
        for event in function["events"]:
            if event["kind"] == kind and event["line"]:
                values.append(event["line"])
    return min(values) if values else None


def build_recommendation(web: dict[str, Any], desktop: dict[str, Any], director: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    web_self = first_line_for_kind(web, "self_knowledge")
    web_director = first_line_for_kind(web, "director_or_department") or first_line_for_kind(web, "engineer_or_workshop")
    web_model = first_line_for_kind(web, "model_or_specialist")
    desktop_self = first_line_for_kind(desktop, "self_knowledge")
    desktop_director = first_line_for_kind(desktop, "director_or_department") or first_line_for_kind(desktop, "engineer_or_workshop")
    desktop_model = first_line_for_kind(desktop, "model_or_specialist")

    actions = [
        {
            "priority": 1,
            "surface": "webui",
            "change": "Place the existing webui_self_knowledge_integration_v1.route_http_request interception after exact slash-command dispatch but before any model request construction or model invocation for both /api/chat/send and /api/chat/stream.",
            "existing_component": str(PRIMARY_PATHS["webui_helper"]),
            "source_candidate": str(PRIMARY_PATHS["webui_source"]),
            "bounded": True,
        },
        {
            "priority": 2,
            "surface": "desktop",
            "change": "Place the existing desktop_self_knowledge_integration_v1.route_desktop_message interception in the actual visible send path before Director classification, department selection, Engineer project search, and model-thread dispatch.",
            "existing_component": str(PRIMARY_PATHS["desktop_helper"]),
            "source_candidate": str(PRIMARY_PATHS["desktop_source"]),
            "bounded": True,
        },
        {
            "priority": 3,
            "surface": "desktop_director",
            "change": "Remove the bare ordinary noun evidence as an independent Engineering trigger. Require an explicit engineering action, command prefix, project-analysis phrase, or stronger multi-token condition.",
            "reason": "Visible Desktop questions about the evidence provider and supporting evidence were routed to Engineer project search.",
            "collision_findings": len(director["scope_collision_findings"]),
            "bounded": True,
        },
        {
            "priority": 4,
            "surface": "both",
            "change": "Preserve pass-through for current-live questions and ordinary chat, but render handled self-knowledge answer_text directly without sending it to the model.",
            "bounded": True,
        },
        {
            "priority": 5,
            "surface": "desktop_renderer",
            "change": "Deduplicate model labels at the display boundary: add one label only when configured and when answer text does not already begin with [Model:.",
            "candidate_label_sites": model["candidate_label_site_count"],
            "bounded": True,
        },
    ]
    return {
        "schema": "foxai.agent_fox.technical_core.v1b2e.recommendation.v1",
        "mission_id": MISSION_ID,
        "status": "implementation_recommended_after_exact_review",
        "inferred_current_order": {
            "webui": {
                "first_self_knowledge_line": web_self,
                "first_director_line": web_director,
                "first_model_line": web_model,
            },
            "desktop": {
                "first_self_knowledge_line": desktop_self,
                "first_director_line": desktop_director,
                "first_model_line": desktop_model,
            },
        },
        "required_order": [
            "exact slash-command handler",
            "shared self-knowledge adapter",
            "department/director routing",
            "ordinary model dispatch",
        ],
        "actions": actions,
        "do_not_change": [
            str(PRIMARY_PATHS["adapter"]),
            str(PRIMARY_PATHS["resource_provider"]),
            str(PRIMARY_PATHS["contract"]),
            str(PRIMARY_PATHS["fixtures"]),
        ],
        "implementation_should_begin_with_new_explicitly_authorized_mission": True,
        "static_only": True,
    }


def write_outputs(output_dir: Path, docs: dict[str, Any], inputs: list[dict[str, Any]], discovered: list[dict[str, Any]]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for name in OUTPUT_NAMES[:-1]:
        data = canonical_bytes(docs[name])
        path = output_dir / name
        path.write_bytes(data)
        rows.append({"name": name, "sha256": sha256_bytes(data), "size_bytes": len(data)})
    receipt = {
        "schema": "foxai.agent_fox.technical_core.v1b2e.preflight_receipt.v1",
        "mission_id": MISSION_ID,
        "title": TITLE,
        "status": "preflight_complete_ready_for_exact_review",
        "core_outputs_before_receipt": rows,
        "exact_output_count_including_receipt": 8,
        "verified_primary_inputs": inputs,
        "discovered_routing_inputs": discovered,
        "source_files_modified": 0,
        "existing_live_source_files_modified": 0,
        "models_loaded": 0,
        "model_calls": 0,
        "guis_launched": 0,
        "live_scans": 0,
        "process_inspection": False,
        "listener_inspection": False,
        "network_used": False,
        "packages_installed": False,
        "services_changed": False,
        "startup_items_changed": False,
        "registry_writes": 0,
        "k_access": False,
        "analysis_class": "bounded_static_source_and_ast_trace",
    }
    receipt_data = canonical_bytes(receipt)
    receipt_path = output_dir / OUTPUT_NAMES[-1]
    receipt_path.write_bytes(receipt_data)
    return {
        "receipt_path": receipt_path,
        "receipt_sha256": sha256_bytes(receipt_data),
        "output_count": len(OUTPUT_NAMES),
    }


def verify_output(output_dir: Path) -> None:
    names = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if names != sorted(OUTPUT_NAMES):
        raise AssertionError((names, OUTPUT_NAMES))
    receipt = json.loads((output_dir / OUTPUT_NAMES[-1]).read_text(encoding="utf-8"))
    if receipt["exact_output_count_including_receipt"] != 8:
        raise AssertionError("receipt output count mismatch")
    for row in receipt["core_outputs_before_receipt"]:
        path = output_dir / row["name"]
        if sha256_file(path) != row["sha256"]:
            raise AssertionError(f"output hash mismatch: {path}")
    for path in output_dir.iterdir():
        if path.is_file():
            json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    for path in list(PRIMARY_PATHS.values()) + [FINAL_DIR, TEMP_DIR]:
        if is_k_path(path):
            raise AssertionError("K path entered configuration")

    if FINAL_DIR.exists():
        raise FileExistsError(f"final evidence directory already exists: {FINAL_DIR}")
    if TEMP_DIR.exists():
        raise FileExistsError(f"temporary evidence directory already exists: {TEMP_DIR}")

    primary_sources: list[SourceFile] = []
    primary_inputs: list[dict[str, Any]] = []
    for logical_name, path in PRIMARY_PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(f"required input missing: {path}")
        digest = sha256_file(path)
        row = {
            "logical_name": logical_name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": digest,
            "known_baseline_sha256": KNOWN_HASHES.get(logical_name),
            "known_baseline_match": digest == KNOWN_HASHES.get(logical_name),
        }
        primary_inputs.append(row)
        if path.suffix.casefold() == ".py":
            primary_sources.append(read_source(logical_name, path))

    web_source = next(source for source in primary_sources if source.logical_name == "webui_source")
    desktop_source = next(source for source in primary_sources if source.logical_name == "desktop_source")

    discovered_paths = discover_relevant_imports([web_source, desktop_source])
    discovered_sources: list[SourceFile] = []
    discovered_rows: list[dict[str, Any]] = []
    for index, path in enumerate(discovered_paths, start=1):
        try:
            source = read_source(f"discovered_routing_{index}", path)
        except Exception as exc:
            discovered_rows.append({
                "path": str(path),
                "parsed": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        discovered_sources.append(source)
        discovered_rows.append({
            "path": str(path),
            "parsed": True,
            "sha256": source.sha256,
            "size_bytes": source.size_bytes,
            "relevant_line_hits": len(line_hits(source, SELF_KNOWLEDGE_TERMS + DIRECTOR_TERMS + COMMAND_TERMS + MODEL_TERMS, max_hits=500)),
        })

    all_sources = primary_sources + discovered_sources
    web_doc = build_surface_path(web_source, "webui")
    desktop_doc = build_surface_path(desktop_source, "desktop")
    director_doc = scan_director_findings(all_sources)
    command_doc = scan_command_precedence(all_sources, web_doc, desktop_doc)
    model_doc = scan_model_labels(all_sources)
    recommendation_doc = build_recommendation(web_doc, desktop_doc, director_doc, model_doc)

    route_trace_doc = {
        "schema": "foxai.agent_fox.technical_core.v1b2e.real_gui_route_trace.v1",
        "mission_id": MISSION_ID,
        "title": TITLE,
        "status": "preflight_complete_ready_for_exact_review",
        "primary_input_count": len(primary_inputs),
        "all_primary_baselines_match": all(row["known_baseline_match"] for row in primary_inputs),
        "discovered_routing_file_count": len(discovered_rows),
        "parsed_discovered_routing_file_count": sum(1 for row in discovered_rows if row["parsed"]),
        "webui_source": str(web_source.path),
        "desktop_source": str(desktop_source.path),
        "shared_adapter": str(PRIMARY_PATHS["adapter"]),
        "webui_helper": str(PRIMARY_PATHS["webui_helper"]),
        "desktop_helper": str(PRIMARY_PATHS["desktop_helper"]),
        "observed_gui_test_findings": [
            "Visible WebUI Technical Core/resource questions were answered by the model without grounded provider metadata.",
            "Visible Desktop resource/evidence questions were routed to Engineer or the model rather than the shared provider.",
            "Both surfaces correctly avoided unsupported current-live-state claims.",
            "Desktop accumulated repeated model-name prefixes.",
        ],
        "preflight_scope": [
            "actual WebUI message path",
            "actual Desktop message path",
            "slash-command precedence",
            "Director/department keyword routing including evidence",
            "model dispatch ordering",
            "model-label rendering sites",
        ],
        "source_files_modified": 0,
        "model_calls": 0,
        "guis_launched": 0,
        "live_scans": 0,
        "network_used": False,
        "k_access": False,
    }

    docs = {
        "REAL_GUI_ROUTE_TRACE.json": route_trace_doc,
        "WEBUI_MESSAGE_PATH.json": web_doc,
        "DESKTOP_MESSAGE_PATH.json": desktop_doc,
        "DIRECTOR_KEYWORD_FINDINGS.json": director_doc,
        "COMMAND_PRECEDENCE_FINDINGS.json": command_doc,
        "MODEL_LABEL_FINDINGS.json": model_doc,
        "MINIMAL_IMPLEMENTATION_RECOMMENDATION.json": recommendation_doc,
    }

    result = write_outputs(TEMP_DIR, docs, primary_inputs, discovered_rows)
    verify_output(TEMP_DIR)
    TEMP_DIR.replace(FINAL_DIR)

    final_receipt = FINAL_DIR / OUTPUT_NAMES[-1]
    final = {
        "mission_id": MISSION_ID,
        "status": "preflight_complete_ready_for_exact_review",
        "output_dir": str(FINAL_DIR),
        "preflight_receipt": str(final_receipt),
        "preflight_receipt_sha256": sha256_file(final_receipt),
        "generated_evidence_files": result["output_count"],
        "primary_files_verified": len(primary_inputs),
        "discovered_routing_files_examined": len(discovered_rows),
        "source_files_modified": 0,
        "model_calls": 0,
        "guis_launched": 0,
        "live_scans": 0,
        "network_used": False,
        "k_access": False,
    }
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "mission_id": MISSION_ID,
            "status": "blocked_nothing_changed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source_files_modified": 0,
            "model_calls": 0,
            "guis_launched": 0,
            "live_scans": 0,
            "network_used": False,
            "k_access": False,
        }, indent=2, sort_keys=True))
        raise
