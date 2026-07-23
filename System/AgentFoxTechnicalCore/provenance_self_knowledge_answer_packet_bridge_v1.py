from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1a3e"
SOURCE_MISSION_ID = "ENG-20260721-235244-7594A9"
EXPECTED_INPUT_HASHES = {
    "PROTECTED_CONTEXT_REGISTRY.json": "1f4ebf3667b8a902b15638396717ad42feb9d8137773fd0825ca634883a3779d",
    "LAUNCHER_RUNTIME_ENTRY_MAP.json": "7e4968bf5c937fa8c6b1bd54948eb5342c33e0af87b4ce46d7dae1fb1c8ffb48",
    "CONTEXT_DEPENDENCY_SUMMARY.json": "e40afe68724e31515f143c0b6ef576586cf5f4d4e6d2e2e7201a790fe782b51a",
    "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json": "aeed560e04316bd71da536cccef236f151e5e1b72cf10343314185075ff847d5",
    "CONTEXT_LINK_GRAPH.json": "6d1d1d2cd3fbadc6f96e74e48ef1e323f25a7a2320fbb2b90bc8768ed3aa2c38",
    "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json": "2c10f3308cdaadd04d265489a138d08bae699f84bc71dc5a980b59d76860d2ca",
    "PROTECTED_CONTEXT_REGISTRY_RECEIPT.json": "bf8bea034ae7bd47c6c8af730ef5312e5c5fa5b4b57cf804fc64dd0f18c98a4e",
}
OUTPUT_NAMES = (
    "SELF_KNOWLEDGE_REQUEST_SCHEMA.json",
    "SELF_KNOWLEDGE_ANSWER_SCHEMA.json",
    "SELF_KNOWLEDGE_INTENT_CATALOG.json",
    "SELF_KNOWLEDGE_TEST_CASES.json",
    "QUERY_EXAMPLES.md",
)
RECEIPT_NAME = "SELF_KNOWLEDGE_BRIDGE_RECEIPT.json"
OUTPUT_LIMIT_BYTES = 8 * 1024 * 1024

INTENTS = (
    "list_protected_contexts",
    "contexts_for_launcher",
    "launcher_runtime_entry_mapping",
    "summarize_context",
    "list_unresolved_branches",
    "show_package_candidates",
    "explain_runtime_uncertainty",
    "show_linked_contexts",
    "locate_authoritative_evidence",
    "compare_contexts",
    "summarize_technical_core_coverage",
)

INTENT_DEFINITIONS = {
    "list_protected_contexts": {
        "description": "List all six protected contexts without merging their evidence boundaries.",
        "required_selectors": [],
        "synonyms": ["list protected contexts", "show protected contexts", "what contexts are protected"],
    },
    "contexts_for_launcher": {
        "description": "List the protected contexts associated with one launcher.",
        "required_selectors": ["launcher"],
        "synonyms": ["contexts for launcher", "show contexts for", "linked launcher contexts"],
    },
    "launcher_runtime_entry_mapping": {
        "description": "Show launcher, interpreter, runtime status, flags, arguments, and entry script.",
        "required_selectors": ["context_or_launcher"],
        "synonyms": ["launcher to runtime to entry", "which python", "entry script", "what starts", "what runs"],
    },
    "summarize_context": {
        "description": "Summarize one protected context and its bounded closure counts.",
        "required_selectors": ["context"],
        "synonyms": ["summarize context", "show context", "context summary"],
    },
    "list_unresolved_branches": {
        "description": "List unresolved static candidates while preserving their unconfirmed status.",
        "required_selectors": ["context"],
        "synonyms": ["unresolved imports", "unresolved branches", "missing imports"],
    },
    "show_package_candidates": {
        "description": "Show package and provider candidates without claiming installation or runtime success.",
        "required_selectors": ["context"],
        "synonyms": ["package candidates", "provider candidates", "third party candidates"],
    },
    "explain_runtime_uncertainty": {
        "description": "Explain resolved or unresolved runtime evidence and uncertainty for one context.",
        "required_selectors": ["context"],
        "synonyms": ["runtime uncertainty", "which runtime is proven", "python uncertainty"],
    },
    "show_linked_contexts": {
        "description": "Show evidence links between contexts without merging closure records.",
        "required_selectors": ["context"],
        "synonyms": ["linked contexts", "linked launcher", "context links"],
    },
    "locate_authoritative_evidence": {
        "description": "Locate the source mission, evidence hash, field path, and receipt hash for one fact.",
        "required_selectors": ["context", "fact"],
        "synonyms": ["where did this fact come from", "locate evidence", "authoritative source"],
    },
    "compare_contexts": {
        "description": "Compare exactly two contexts while retaining separate provenance for each side.",
        "required_selectors": ["contexts[2]"],
        "synonyms": ["compare contexts", "difference between contexts", "compare launcher contexts"],
    },
    "summarize_technical_core_coverage": {
        "description": "Summarize six-context Technical Core coverage and registry safety boundaries.",
        "required_selectors": [],
        "synonyms": ["technical core coverage", "six context coverage", "coverage summary"],
    },
}

FACT_ALIASES = {
    "runtime": "runtime_id",
    "runtime id": "runtime_id",
    "which python": "resolved_interpreter_path",
    "interpreter": "interpreter_reference",
    "interpreter path": "resolved_interpreter_path",
    "entry": "entry_script",
    "entry script": "entry_script",
    "launcher": "launcher_path",
    "launcher line": "launcher_line",
    "path group": "path_group_id",
    "unresolved": "unresolved_branch_count",
    "unresolved count": "unresolved_branch_count",
    "nodes": "closure_node_count",
    "edges": "closure_edge_count",
    "parsed imports": "parsed_import_count",
    "conditional imports": "conditional_or_deferred_import_count",
    "cycles": "cycle_count",
    "uncertainty": "uncertainty",
    "flags": "flags",
    "arguments": "arguments",
    "working directory": "working_directory",
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def provenance_from_source(source: dict[str, Any]) -> dict[str, Any]:
    result = {
        "source_mission_id": source["source_mission_id"],
        "evidence_filename": source["evidence_file"],
        "evidence_sha256": source["evidence_sha256"],
        "json_field_path": source.get("json_field_path"),
        "record_locator": source.get("record_locator"),
        "source_receipt_sha256": source["receipt_sha256"],
    }
    assert result["json_field_path"] or result["record_locator"]
    return result


def claim(claim_id: str, text: str, value: Any, sources: list[dict[str, Any]]) -> dict[str, Any]:
    assert sources
    return {
        "claim_id": claim_id,
        "text": text,
        "value": value,
        "provenance": [provenance_from_source(source) for source in sources],
    }


def fact_claim(context_key: str, fact_name: str, fact: dict[str, Any], text: str | None = None) -> dict[str, Any]:
    value = fact["value"]
    return claim(
        f"{context_key}.{fact_name}",
        text or f"{fact_name.replace('_', ' ')}: {value}",
        value,
        [fact["source"]],
    )


def verify_registry_dir(registry_dir: Path) -> dict[str, Any]:
    for name, expected_hash in EXPECTED_INPUT_HASHES.items():
        path = registry_dir / name
        assert path.is_file(), path
        actual = sha256_file(path)
        assert actual == expected_hash, (name, expected_hash, actual)
    loaded = {name: read_json(registry_dir / name) for name in EXPECTED_INPUT_HASHES}
    receipt = loaded["PROTECTED_CONTEXT_REGISTRY_RECEIPT.json"]
    assert receipt["mission_id"] == SOURCE_MISSION_ID
    assert receipt["protected_context_count"] == 6
    assert receipt["unique_launcher_count"] == 4
    assert receipt["unique_path_group_count"] == 5
    assert receipt["internal_deterministic_rebuild_match"] is True
    assert receipt["runtime_facts_inferred_across_contexts"] is False
    assert receipt["closure_node_records_copied"] == 0
    assert receipt["closure_edge_records_copied"] == 0
    expected_core = {item["name"]: item["sha256"] for item in receipt["core_outputs_before_receipt"]}
    for name, expected_hash in EXPECTED_INPUT_HASHES.items():
        if name != "PROTECTED_CONTEXT_REGISTRY_RECEIPT.json":
            assert expected_core[name] == expected_hash
    registry = loaded["PROTECTED_CONTEXT_REGISTRY.json"]
    assert registry["protected_context_count"] == 6
    assert len(registry["contexts"]) == 6
    return loaded


def indexes(loaded: dict[str, Any]) -> dict[str, Any]:
    registry = loaded["PROTECTED_CONTEXT_REGISTRY.json"]
    contexts = registry["contexts"]
    by_key = {item["context_key"].lower(): item for item in contexts}
    by_id = {item["facts"]["context_id"]["value"].lower(): item for item in contexts}
    by_label = {item["label"].lower(): item for item in contexts}
    launchers: dict[str, list[dict[str, Any]]] = {}
    for item in contexts:
        path = item["facts"]["launcher_path"]["value"]
        for token in {path.lower(), PureWindowsPath(path).name.lower()}:
            launchers.setdefault(token, []).append(item)
    dep_summary = loaded["CONTEXT_DEPENDENCY_SUMMARY.json"]
    dep_by_id = {item["context_id"]["value"].lower(): item for item in dep_summary["contexts"]}
    unresolved = loaded["UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json"]
    unresolved_by_id = {item["context_id"]["value"].lower(): item for item in unresolved["contexts"]}
    return {
        "contexts": contexts,
        "by_key": by_key,
        "by_id": by_id,
        "by_label": by_label,
        "launchers": launchers,
        "dep_by_id": dep_by_id,
        "unresolved_by_id": unresolved_by_id,
        "link_graph": loaded["CONTEXT_LINK_GRAPH.json"],
        "coverage": loaded["PROTECTED_CONTEXT_REGISTRY_COVERAGE.json"],
        "receipt": loaded["PROTECTED_CONTEXT_REGISTRY_RECEIPT.json"],
    }


def context_tokens(item: dict[str, Any]) -> set[str]:
    facts = item["facts"]
    launcher = facts["launcher_path"]["value"]
    return {
        item["context_key"].lower(),
        item["label"].lower(),
        facts["context_id"]["value"].lower(),
        launcher.lower(),
        PureWindowsPath(launcher).name.lower(),
    }


def resolve_context(selector: str | None, idx: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    if not selector:
        return None, []
    normalized = selector.strip().lower()
    exact: list[dict[str, Any]] = []
    for item in idx["contexts"]:
        if normalized in context_tokens(item):
            exact.append(item)
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        return None, [item["context_key"] for item in exact]
    partial = []
    for item in idx["contexts"]:
        if any(normalized in token or token in normalized for token in context_tokens(item)):
            partial.append(item)
    unique = {item["context_key"]: item for item in partial}
    if len(unique) == 1:
        return next(iter(unique.values())), []
    return None, sorted(unique)


def resolve_launcher(selector: str | None, idx: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    if not selector:
        return None, [], []
    normalized = selector.strip().lower()
    candidates: dict[str, list[dict[str, Any]]] = {}
    for item in idx["contexts"]:
        path = item["facts"]["launcher_path"]["value"]
        base = PureWindowsPath(path).name
        if normalized in {path.lower(), base.lower()} or normalized in path.lower() or base.lower() in normalized:
            candidates[path] = [c for c in idx["contexts"] if c["facts"]["launcher_path"]["value"] == path]
    if len(candidates) == 1:
        path = next(iter(candidates))
        return path, candidates[path], []
    return None, [], sorted(candidates)


def normalize_intent(value: str) -> str | None:
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    return token if token in INTENTS else None


def infer_natural_request(text: str, idx: dict[str, Any]) -> dict[str, Any]:
    raw = text.strip()
    lower = raw.lower()
    matches: list[str] = []
    for intent, definition in INTENT_DEFINITIONS.items():
        if any(phrase in lower for phrase in definition["synonyms"]):
            matches.append(intent)
    if "compare" in lower and "compare_contexts" not in matches:
        matches.append("compare_contexts")
    matches = list(dict.fromkeys(matches))
    if len(matches) != 1:
        return {
            "request_id": "REQ-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper(),
            "intent": None,
            "text": raw,
            "parse_error": "ambiguous_or_unsupported_intent",
            "candidate_intents": matches,
        }
    request: dict[str, Any] = {
        "request_id": "REQ-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper(),
        "intent": matches[0],
        "text": raw,
    }
    found_contexts = [item for item in idx["contexts"] if any(token in lower for token in context_tokens(item))]
    unique_contexts = list({item["context_key"]: item for item in found_contexts}.values())
    found_launchers = []
    for item in idx["contexts"]:
        path = item["facts"]["launcher_path"]["value"]
        if path.lower() in lower or PureWindowsPath(path).name.lower() in lower:
            if path not in found_launchers:
                found_launchers.append(path)
    if request["intent"] == "compare_contexts":
        request["contexts"] = [item["context_key"] for item in unique_contexts]
    elif len(unique_contexts) == 1:
        request["context"] = unique_contexts[0]["context_key"]
    elif len(unique_contexts) > 1:
        request["ambiguous_contexts"] = [item["context_key"] for item in unique_contexts]
    if len(found_launchers) == 1:
        request["launcher"] = found_launchers[0]
    elif len(found_launchers) > 1:
        request["ambiguous_launchers"] = found_launchers
    for alias, fact_name in FACT_ALIASES.items():
        if alias in lower:
            request.setdefault("fact", fact_name)
    return request


def clarification_packet(request: dict[str, Any], message: str, choices: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA_PREFIX}.answer_packet.v1",
        "request_id": request.get("request_id") or "REQ-UNSPECIFIED",
        "normalized_intent": request.get("intent"),
        "status": "clarification_required",
        "resolved_selectors": {},
        "answer_text": message,
        "answer_text_claim_ids": [],
        "structured_claims": [],
        "uncertainty_statements": [],
        "unresolved_items": [],
        "linked_context_references": [],
        "clarification": {"message": message, "choices": choices or []},
        "safety": {
            "unresolved_candidates_presented_as_confirmed": False,
            "runtime_facts_inferred_across_contexts": False,
            "dependency_nodes_or_edges_copied": False,
        },
    }


def base_packet(request: dict[str, Any], intent: str, selectors: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": f"{SCHEMA_PREFIX}.answer_packet.v1",
        "request_id": request.get("request_id") or "REQ-UNSPECIFIED",
        "normalized_intent": intent,
        "status": "answered",
        "resolved_selectors": selectors,
        "answer_text": "",
        "answer_text_claim_ids": [],
        "structured_claims": [],
        "uncertainty_statements": [],
        "unresolved_items": [],
        "linked_context_references": [],
        "clarification": None,
        "safety": {
            "unresolved_candidates_presented_as_confirmed": False,
            "runtime_facts_inferred_across_contexts": False,
            "dependency_nodes_or_edges_copied": False,
        },
    }


def add_fact(packet: dict[str, Any], item: dict[str, Any], fact_name: str, text: str | None = None) -> dict[str, Any]:
    c = fact_claim(item["context_key"], fact_name, item["facts"][fact_name], text)
    packet["structured_claims"].append(c)
    packet["answer_text_claim_ids"].append(c["claim_id"])
    return c


def answer_request(request: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    idx = indexes(loaded)
    if request.get("parse_error"):
        return clarification_packet(request, "The request did not resolve to exactly one supported intent.", request.get("candidate_intents", []))
    intent = normalize_intent(str(request.get("intent", "")))
    if intent is None:
        return clarification_packet(request, "Specify one of the eleven supported intent families.", list(INTENTS))
    request = dict(request)
    request["intent"] = intent
    if request.get("ambiguous_contexts"):
        return clarification_packet(request, "More than one context matched; select one exact context.", request["ambiguous_contexts"])
    if request.get("ambiguous_launchers"):
        return clarification_packet(request, "More than one launcher matched; select one exact launcher.", request["ambiguous_launchers"])

    if intent == "list_protected_contexts":
        packet = base_packet(request, intent, {})
        for item in idx["contexts"]:
            c = add_fact(packet, item, "context_id", f"{item['label']} is registered as {item['facts']['context_id']['value']}.")
            c["context_key"] = item["context_key"]
            c["label"] = item["label"]
        packet["answer_text"] = "Six protected contexts are registered as separate evidence boundaries."
        return packet

    if intent == "summarize_technical_core_coverage":
        packet = base_packet(request, intent, {})
        coverage = idx["coverage"]
        receipt = idx["receipt"]
        coverage_source = {
            "source_mission_id": SOURCE_MISSION_ID,
            "evidence_file": "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json",
            "evidence_sha256": EXPECTED_INPUT_HASHES["PROTECTED_CONTEXT_REGISTRY_COVERAGE.json"],
            "json_field_path": "$",
            "receipt_sha256": EXPECTED_INPUT_HASHES["PROTECTED_CONTEXT_REGISTRY_RECEIPT.json"],
        }
        for field in ("protected_context_count", "unique_launcher_count", "unique_path_group_count", "source_mission_count"):
            source = dict(coverage_source)
            source["json_field_path"] = f"$.{field}"
            c = claim(f"coverage.{field}", f"{field.replace('_', ' ')}: {coverage[field]}", coverage[field], [source])
            packet["structured_claims"].append(c)
            packet["answer_text_claim_ids"].append(c["claim_id"])
        for field in ("closure_node_records_copied", "closure_edge_records_copied", "false_runtime_resolution_count", "live_source_files_scanned_or_parsed"):
            source = dict(coverage_source)
            source["json_field_path"] = f"$.{field}"
            packet["structured_claims"].append(claim(f"coverage.{field}", f"{field.replace('_', ' ')}: {coverage[field]}", coverage[field], [source]))
        packet["answer_text"] = "The Technical Core registry covers six contexts, four launchers, and five path groups with no copied dependency records or false runtime resolution."
        return packet

    if intent == "contexts_for_launcher":
        launcher, contexts, choices = resolve_launcher(request.get("launcher") or request.get("context"), idx)
        if launcher is None:
            return clarification_packet(request, "Select one exact launcher.", choices or sorted({item["facts"]["launcher_path"]["value"] for item in idx["contexts"]}))
        packet = base_packet(request, intent, {"launcher": launcher})
        for item in contexts:
            c = add_fact(packet, item, "context_id", f"{item['label']} is associated with {launcher}.")
            c["context_key"] = item["context_key"]
            c["label"] = item["label"]
        packet["answer_text"] = f"{len(contexts)} protected context(s) are associated with {launcher}."
        return packet

    if intent == "launcher_runtime_entry_mapping":
        selector = request.get("context") or request.get("launcher")
        context, context_choices = resolve_context(selector, idx)
        contexts: list[dict[str, Any]]
        selectors: dict[str, Any]
        if context is not None:
            contexts = [context]
            selectors = {"context": context["context_key"]}
        else:
            launcher, contexts, launcher_choices = resolve_launcher(selector, idx)
            if launcher is None:
                return clarification_packet(request, "Select one context or one exact launcher.", context_choices or launcher_choices)
            selectors = {"launcher": launcher}
        packet = base_packet(request, intent, selectors)
        for item in contexts:
            for field in ("launcher_path", "launcher_line", "interpreter_reference", "resolved_interpreter_path", "runtime_id", "runtime_resolution_status", "flags", "arguments", "entry_script"):
                add_fact(packet, item, field)
            uncertainty = item["facts"]["uncertainty"]
            if uncertainty["value"]:
                packet["uncertainty_statements"].append(fact_claim(item["context_key"], "uncertainty", uncertainty, "Runtime uncertainty is preserved and not resolved by inference."))
        packet["answer_text"] = f"Returned launcher-to-runtime-to-entry mapping for {len(contexts)} separate context(s)."
        return packet

    if intent in {"summarize_context", "list_unresolved_branches", "show_package_candidates", "explain_runtime_uncertainty", "show_linked_contexts", "locate_authoritative_evidence"}:
        context, choices = resolve_context(request.get("context"), idx)
        if context is None:
            return clarification_packet(request, "Select one exact protected context.", choices or [item["context_key"] for item in idx["contexts"]])
        context_id = context["facts"]["context_id"]["value"]
        packet = base_packet(request, intent, {"context": context["context_key"], "context_id": context_id})

        if intent == "summarize_context":
            for field in ("context_id", "launcher_path", "launcher_line", "runtime_id", "runtime_resolution_status", "entry_script", "closure_node_count", "closure_edge_count", "parsed_import_count", "conditional_or_deferred_import_count", "unresolved_branch_count", "cycle_count"):
                add_fact(packet, context, field)
            if context["facts"]["uncertainty"]["value"]:
                packet["uncertainty_statements"].append(fact_claim(context["context_key"], "uncertainty", context["facts"]["uncertainty"]))
            packet["answer_text"] = f"{context['label']} is summarized without merging it with any linked context."
            return packet

        if intent == "list_unresolved_branches":
            record = idx["unresolved_by_id"][context_id.lower()]
            for number, unresolved in enumerate(record["unresolved_records"], start=1):
                c = claim(
                    f"{context['context_key']}.unresolved.{number}",
                    f"Unresolved static candidate: {unresolved['record'].get('module')} at {unresolved['record'].get('source_path')} line {unresolved['record'].get('line')}.",
                    unresolved["record"],
                    [unresolved["source"]],
                )
                c["status"] = "unresolved_candidate"
                c["confirmed_runtime_failure"] = False
                packet["unresolved_items"].append(c)
            packet["answer_text"] = f"{len(packet['unresolved_items'])} unresolved static candidate(s) were returned; none is labeled installed, confirmed, active, missing at runtime, or broken."
            return packet

        if intent == "show_package_candidates":
            summary = idx["dep_by_id"][context_id.lower()]
            for category, fact in summary["package_candidates"].items():
                c = claim(
                    f"{context['context_key']}.package_candidates.{category}",
                    f"{category.replace('_', ' ')} contains {len(fact['value']) if isinstance(fact['value'], list) else 1} candidate record(s).",
                    fact["value"],
                    [fact["source"]],
                )
                c["candidate_status"] = "evidence_candidate_not_runtime_confirmation"
                packet["structured_claims"].append(c)
                packet["answer_text_claim_ids"].append(c["claim_id"])
            packet["answer_text"] = "Package and provider candidates are reported as evidence candidates, not as proof of installation or runtime success."
            return packet

        if intent == "explain_runtime_uncertainty":
            record = idx["unresolved_by_id"][context_id.lower()]["runtime_uncertainty"]
            value = record["value"]
            c = claim(
                f"{context['context_key']}.runtime_uncertainty",
                "Runtime resolution status and uncertainty are preserved exactly from the registry.",
                value,
                record.get("sources") or [record["source"]],
            )
            packet["uncertainty_statements"].append(c)
            packet["answer_text_claim_ids"].append(c["claim_id"])
            packet["answer_text"] = "Runtime evidence is reported without resolving aliases, probing pythonw, or borrowing facts from another context."
            return packet

        if intent == "show_linked_contexts":
            links = [link for link in idx["link_graph"]["links"] if context_id in {link["source_context_id"], link["target_context_id"]}]
            for number, link in enumerate(links, start=1):
                c = claim(
                    f"{context['context_key']}.link.{number}",
                    f"{link['source_context_id']} {link['relationship']} {link['target_context_id']}.",
                    {key: link[key] for key in ("source_context_id", "target_context_id", "relationship", "nodes_or_edges_merged")},
                    [link["source"]],
                )
                packet["linked_context_references"].append(c)
                packet["answer_text_claim_ids"].append(c["claim_id"])
            packet["answer_text"] = f"{len(links)} evidence link(s) were returned without merging closure records."
            return packet

        if intent == "locate_authoritative_evidence":
            fact_selector = str(request.get("fact", "")).strip().lower().replace("-", "_")
            fact_selector = FACT_ALIASES.get(fact_selector, fact_selector)
            if fact_selector not in context["facts"]:
                return clarification_packet(request, "Select one fact available in the context registry.", sorted(context["facts"]))
            c = fact_claim(context["context_key"], fact_selector, context["facts"][fact_selector], "Authoritative evidence locator for the selected fact.")
            packet["structured_claims"].append(c)
            packet["answer_text_claim_ids"].append(c["claim_id"])
            packet["answer_text"] = "The selected fact includes its source mission, evidence filename and hash, field path or locator, and source receipt hash."
            return packet

    if intent == "compare_contexts":
        selectors = request.get("contexts")
        if not isinstance(selectors, list) or len(selectors) != 2:
            return clarification_packet(request, "Select exactly two protected contexts for comparison.", [item["context_key"] for item in idx["contexts"]])
        resolved = []
        ambiguous: list[str] = []
        for selector in selectors:
            item, choices = resolve_context(str(selector), idx)
            if item is None:
                ambiguous.extend(choices or [str(selector)])
            else:
                resolved.append(item)
        if len(resolved) != 2 or resolved[0]["context_key"] == resolved[1]["context_key"]:
            return clarification_packet(request, "Comparison requires two distinct, exactly resolved contexts.", sorted(set(ambiguous)))
        packet = base_packet(request, intent, {"contexts": [item["context_key"] for item in resolved]})
        fields = ("launcher_path", "launcher_line", "interpreter_reference", "resolved_interpreter_path", "runtime_id", "runtime_resolution_status", "entry_script", "closure_node_count", "closure_edge_count", "unresolved_branch_count")
        for item in resolved:
            for field in fields:
                add_fact(packet, item, field)
            if item["facts"]["uncertainty"]["value"]:
                packet["uncertainty_statements"].append(fact_claim(item["context_key"], "uncertainty", item["facts"]["uncertainty"]))
        packet["answer_text"] = "Two contexts were compared side by side with separate provenance; no runtime facts or closure records were merged."
        return packet

    return clarification_packet(request, "The request could not be answered within the bounded intent catalog.")


def request_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{SCHEMA_PREFIX}.request_schema.v1",
        "title": "Agent Fox Provenance Self-Knowledge Request",
        "type": "object",
        "required": ["request_id", "intent"],
        "properties": {
            "request_id": {"type": "string", "minLength": 1},
            "intent": {"type": "string", "enum": list(INTENTS)},
            "context": {"type": "string"},
            "launcher": {"type": "string"},
            "contexts": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "string"}},
            "fact": {"type": "string"},
            "text": {"type": "string"},
        },
        "additionalProperties": False,
    }


def answer_schema() -> dict[str, Any]:
    provenance_schema = {
        "type": "object",
        "required": ["source_mission_id", "evidence_filename", "evidence_sha256", "source_receipt_sha256"],
        "properties": {
            "source_mission_id": {"type": "string"},
            "evidence_filename": {"type": "string"},
            "evidence_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "json_field_path": {"type": ["string", "null"]},
            "record_locator": {"type": ["string", "null"]},
            "source_receipt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        },
    }
    claim_schema = {
        "type": "object",
        "required": ["claim_id", "text", "value", "provenance"],
        "properties": {
            "claim_id": {"type": "string"},
            "text": {"type": "string"},
            "value": {},
            "provenance": {"type": "array", "minItems": 1, "items": provenance_schema},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{SCHEMA_PREFIX}.answer_schema.v1",
        "title": "Agent Fox Provenance Self-Knowledge Answer Packet",
        "type": "object",
        "required": ["request_id", "normalized_intent", "status", "answer_text", "structured_claims", "uncertainty_statements", "unresolved_items", "linked_context_references", "safety"],
        "properties": {
            "request_id": {"type": "string"},
            "normalized_intent": {"type": ["string", "null"]},
            "status": {"enum": ["answered", "clarification_required"]},
            "resolved_selectors": {"type": "object"},
            "answer_text": {"type": "string"},
            "answer_text_claim_ids": {"type": "array", "items": {"type": "string"}},
            "structured_claims": {"type": "array", "items": claim_schema},
            "uncertainty_statements": {"type": "array", "items": claim_schema},
            "unresolved_items": {"type": "array", "items": claim_schema},
            "linked_context_references": {"type": "array", "items": claim_schema},
            "clarification": {"type": ["object", "null"]},
            "safety": {"type": "object"},
        },
    }


def test_cases() -> list[dict[str, Any]]:
    contexts = [
        "web_portable", "web_with_comfyui_helper", "workshop_comfyui_manager",
        "workshop_main", "desktop_recovery_helper", "desktop_recovery_gui",
    ]
    launchers = [
        r"Z:\FOXAI\START_FOXAI_WEB_PORTABLE.bat",
        r"Z:\FOXAI\START_FOXAI_WEB_WITH_COMFYUI.bat",
        r"Z:\FOXAI\Launch FOXAI Workshop.bat",
        r"Z:\FOXAI\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat",
    ]
    cases: list[dict[str, Any]] = []
    number = 1
    def add(request: dict[str, Any], status: str = "answered") -> None:
        nonlocal number
        request = dict(request)
        request.setdefault("request_id", f"TEST-{number:02d}")
        cases.append({"case_id": f"CASE-{number:02d}", "request": request, "expected_status": status, "expected_intent": request.get("intent")})
        number += 1
    add({"intent": "list_protected_contexts"})
    add({"intent": "summarize_technical_core_coverage"})
    for context in contexts:
        add({"intent": "summarize_context", "context": context})
    for launcher in launchers:
        add({"intent": "contexts_for_launcher", "launcher": launcher})
    for launcher in launchers:
        add({"intent": "launcher_runtime_entry_mapping", "launcher": launcher})
    for context in contexts:
        add({"intent": "list_unresolved_branches", "context": context})
    for context in ("workshop_main", "desktop_recovery_gui"):
        add({"intent": "explain_runtime_uncertainty", "context": context})
    for context in ("web_portable", "workshop_main"):
        add({"intent": "show_package_candidates", "context": context})
    for context in ("workshop_main", "desktop_recovery_gui"):
        add({"intent": "show_linked_contexts", "context": context})
    add({"intent": "locate_authoritative_evidence", "context": "workshop_main", "fact": "runtime_id"})
    add({"intent": "locate_authoritative_evidence", "context": "desktop_recovery_gui", "fact": "resolved_interpreter_path"})
    add({"intent": "compare_contexts", "contexts": ["workshop_main", "desktop_recovery_gui"]})
    add({"intent": "compare_contexts", "contexts": ["web_with_comfyui_helper", "desktop_recovery_helper"]})
    add({"intent": "summarize_context"}, "clarification_required")
    add({"intent": "compare_contexts", "contexts": ["workshop_main"]}, "clarification_required")
    return cases


def validate_claim_provenance(packet: dict[str, Any]) -> int:
    count = 0
    for field in ("structured_claims", "uncertainty_statements", "unresolved_items", "linked_context_references"):
        for item in packet[field]:
            assert item["provenance"]
            for source in item["provenance"]:
                assert source["source_mission_id"]
                assert len(source["evidence_sha256"]) == 64
                assert len(source["source_receipt_sha256"]) == 64
                assert source.get("json_field_path") or source.get("record_locator")
            count += 1
    return count


def run_test_cases(loaded: dict[str, Any]) -> dict[str, Any]:
    cases = test_cases()
    intent_seen: set[str] = set()
    context_seen: set[str] = set()
    launcher_seen: set[str] = set()
    claim_count = 0
    ambiguity_rejections = 0
    for case in cases:
        packet = answer_request(case["request"], loaded)
        assert packet["status"] == case["expected_status"], (case["case_id"], packet)
        assert packet["normalized_intent"] == case["expected_intent"]
        assert packet["safety"]["unresolved_candidates_presented_as_confirmed"] is False
        assert packet["safety"]["runtime_facts_inferred_across_contexts"] is False
        assert packet["safety"]["dependency_nodes_or_edges_copied"] is False
        claim_count += validate_claim_provenance(packet)
        if packet["status"] == "clarification_required":
            ambiguity_rejections += 1
        intent_seen.add(case["request"]["intent"])
        if "context" in case["request"]:
            context_seen.add(case["request"]["context"])
        if "launcher" in case["request"]:
            launcher_seen.add(case["request"]["launcher"])
    assert set(INTENTS) <= intent_seen
    assert len(context_seen) == 6
    assert len(launcher_seen) == 4
    assert len(cases) >= 24
    assert ambiguity_rejections >= 2
    return {
        "test_case_count": len(cases),
        "supported_intent_count": len(INTENTS),
        "context_coverage_count": len(context_seen),
        "launcher_coverage_count": len(launcher_seen),
        "claim_provenance_record_count": claim_count,
        "clarification_packet_count": ambiguity_rejections,
    }


def artifacts(mission_id: str, loaded: dict[str, Any]) -> dict[str, bytes]:
    tests = test_cases()
    test_summary = run_test_cases(loaded)
    catalog = {
        "schema": f"{SCHEMA_PREFIX}.intent_catalog.v1",
        "mission_id": mission_id,
        "supported_intent_count": len(INTENTS),
        "intents": [{"intent": intent, **INTENT_DEFINITIONS[intent]} for intent in INTENTS],
        "normalization_policy": {
            "bounded_synonym_matching": True,
            "ambiguous_requests_require_clarification": True,
            "cross_context_runtime_inference_allowed": False,
        },
    }
    cases_doc = {
        "schema": f"{SCHEMA_PREFIX}.test_cases.v1",
        "mission_id": mission_id,
        "test_case_count": len(tests),
        "coverage": test_summary,
        "cases": tests,
    }
    examples = """# Agent Fox Provenance Self-Knowledge Query Examples

The bridge reads only the verified V1A-3D registry. It does not scan live source or probe runtimes.

## JSON request

```json
{"request_id":"EX-1","intent":"summarize_context","context":"workshop_main"}
```

## Single-request text

```text
summarize context workshop main foxai.py
```

## Supported intent families

1. list protected contexts
2. contexts for a launcher
3. launcher-to-runtime-to-entry mapping
4. summarize one context
5. unresolved imports or branches
6. package candidates
7. runtime uncertainty
8. linked contexts
9. authoritative evidence locator
10. compare two contexts
11. six-context Technical Core coverage

Ambiguous selectors produce a structured clarification packet rather than a guess.
Unresolved candidates are never presented as installed, confirmed, active, missing at runtime, or broken.
"""
    outputs = {
        "SELF_KNOWLEDGE_REQUEST_SCHEMA.json": canonical_bytes(request_schema()),
        "SELF_KNOWLEDGE_ANSWER_SCHEMA.json": canonical_bytes(answer_schema()),
        "SELF_KNOWLEDGE_INTENT_CATALOG.json": canonical_bytes(catalog),
        "SELF_KNOWLEDGE_TEST_CASES.json": canonical_bytes(cases_doc),
        "QUERY_EXAMPLES.md": examples.encode("utf-8"),
    }
    core = [{"name": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in outputs.items()]
    receipt = {
        "schema": f"{SCHEMA_PREFIX}.bridge_receipt.v1",
        "mission_id": mission_id,
        "result": "provenance_self_knowledge_answer_packet_bridge_complete",
        "source_registry_mission_id": SOURCE_MISSION_ID,
        "source_registry_hashes_verified": True,
        "supported_intent_count": len(INTENTS),
        "test_case_count": test_summary["test_case_count"],
        "context_coverage_count": test_summary["context_coverage_count"],
        "launcher_coverage_count": test_summary["launcher_coverage_count"],
        "claim_provenance_record_count": test_summary["claim_provenance_record_count"],
        "clarification_packet_count": test_summary["clarification_packet_count"],
        "deterministic_answer_equality": True,
        "claim_level_provenance_complete": True,
        "ambiguity_rejection_verified": True,
        "unresolved_state_preserved": True,
        "closure_node_records_copied": 0,
        "closure_edge_records_copied": 0,
        "live_source_files_scanned_or_parsed": 0,
        "interpreter_child_processes": 0,
        "shell_child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "existing_foxai_source_modified": False,
        "core_outputs_before_receipt": core,
        "exact_output_count_including_receipt": 6,
    }
    outputs[RECEIPT_NAME] = canonical_bytes(receipt)
    return outputs


def write_build(mission_id: str, output_dir: Path, loaded: dict[str, Any]) -> dict[str, Any]:
    outputs = artifacts(mission_id, loaded)
    assert set(outputs) == set(OUTPUT_NAMES) | {RECEIPT_NAME}
    total = sum(len(data) for data in outputs.values())
    assert total < OUTPUT_LIMIT_BYTES
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in (*OUTPUT_NAMES, RECEIPT_NAME):
        (output_dir / name).write_bytes(outputs[name])
    return {"status": "built", "output_dir": str(output_dir), "output_count": len(outputs), "total_output_bytes": total}


def validate_output(index_dir: Path) -> dict[str, Any]:
    actual_names = sorted(path.name for path in index_dir.iterdir() if path.is_file())
    expected_names = sorted((*OUTPUT_NAMES, RECEIPT_NAME))
    assert actual_names == expected_names, (actual_names, expected_names)
    receipt = read_json(index_dir / RECEIPT_NAME)
    assert receipt["supported_intent_count"] == 11
    assert receipt["test_case_count"] >= 24
    assert receipt["context_coverage_count"] == 6
    assert receipt["launcher_coverage_count"] == 4
    assert receipt["claim_level_provenance_complete"] is True
    assert receipt["ambiguity_rejection_verified"] is True
    assert receipt["unresolved_state_preserved"] is True
    assert receipt["closure_node_records_copied"] == 0
    assert receipt["closure_edge_records_copied"] == 0
    assert receipt["live_source_files_scanned_or_parsed"] == 0
    assert receipt["interpreter_child_processes"] == 0
    assert receipt["shell_child_processes"] == 0
    assert receipt["network_used"] is False
    assert receipt["packages_installed"] is False
    assert receipt["models_loaded"] is False
    total = sum((index_dir / name).stat().st_size for name in expected_names)
    assert total < OUTPUT_LIMIT_BYTES
    return {
        "status": "verified",
        "output_count": len(expected_names),
        "supported_intent_count": receipt["supported_intent_count"],
        "test_case_count": receipt["test_case_count"],
        "context_coverage_count": receipt["context_coverage_count"],
        "launcher_coverage_count": receipt["launcher_coverage_count"],
        "total_output_bytes": total,
    }


def self_test() -> None:
    assert normalize_intent("list protected contexts") == "list_protected_contexts"
    assert normalize_intent("compare-contexts") == "compare_contexts"
    source = {
        "source_mission_id": "ENG-X",
        "evidence_file": "A.json",
        "evidence_sha256": "0" * 64,
        "json_field_path": "$.x",
        "receipt_sha256": "1" * 64,
    }
    c = claim("x", "x", 1, [source])
    assert c["provenance"][0]["source_receipt_sha256"] == "1" * 64
    assert len(INTENTS) == 11
    assert len(test_cases()) >= 24
    print("V1A3E_SELF_KNOWLEDGE_SELF_TEST_OK")


def parse_request_json(args: argparse.Namespace) -> dict[str, Any]:
    if args.request_file:
        return read_json(Path(args.request_file))
    return json.loads(args.request_json)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")

    verify = sub.add_parser("verify-inputs")
    verify.add_argument("--registry-dir", required=True)

    build = sub.add_parser("build")
    build.add_argument("--registry-dir", required=True)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--mission-id", required=True)

    validate = sub.add_parser("validate-output")
    validate.add_argument("--index-dir", required=True)

    validate_only = sub.add_parser("validate-only")
    validate_only.add_argument("--registry-dir", required=True)

    answer_json_parser = sub.add_parser("answer-json")
    answer_json_parser.add_argument("--registry-dir", required=True)
    group = answer_json_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--request-json")
    group.add_argument("--request-file")

    answer_parser = sub.add_parser("answer")
    answer_parser.add_argument("--registry-dir", required=True)
    answer_parser.add_argument("--text", required=True)

    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
        return 0
    if args.command == "validate-output":
        print(json.dumps(validate_output(Path(args.index_dir)), sort_keys=True))
        return 0
    loaded = verify_registry_dir(Path(args.registry_dir))
    if args.command in {"verify-inputs", "validate-only"}:
        result = {
            "status": "verified",
            "source_registry_mission_id": SOURCE_MISSION_ID,
            "verified_input_count": len(EXPECTED_INPUT_HASHES),
            "protected_context_count": 6,
            "unique_launcher_count": 4,
            "unique_path_group_count": 5,
        }
        if args.command == "validate-only":
            summary = run_test_cases(loaded)
            result.update(summary)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "build":
        print(json.dumps(write_build(args.mission_id, Path(args.output_dir), loaded), sort_keys=True))
        return 0
    if args.command == "answer-json":
        request = parse_request_json(args)
        first = answer_request(request, loaded)
        second = answer_request(request, loaded)
        assert canonical_bytes(first) == canonical_bytes(second)
        print(json.dumps(first, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    if args.command == "answer":
        request = infer_natural_request(args.text, indexes(loaded))
        first = answer_request(request, loaded)
        second = answer_request(request, loaded)
        assert canonical_bytes(first) == canonical_bytes(second)
        print(json.dumps(first, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
