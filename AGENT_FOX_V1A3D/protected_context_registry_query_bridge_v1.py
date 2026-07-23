from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA_PREFIX = "foxai.agent_fox.technical_core.v1a3d"
OUTPUT_NAMES = (
    "PROTECTED_CONTEXT_REGISTRY.json",
    "LAUNCHER_RUNTIME_ENTRY_MAP.json",
    "CONTEXT_DEPENDENCY_SUMMARY.json",
    "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json",
    "CONTEXT_LINK_GRAPH.json",
    "QUERY_EXAMPLES.md",
    "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json",
)
RECEIPT_NAME = "PROTECTED_CONTEXT_REGISTRY_RECEIPT.json"
OUTPUT_LIMIT_BYTES = 8 * 1024 * 1024

SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "web_portable",
        "label": "Web Portable",
        "mission_id": "ENG-20260721-220855-64D244",
        "context_id": "CTX-23820E95DB51A6C5",
        "path_group_id": "PATHGROUP-8017393F74F3ACD3",
        "context_file": "WEB_PORTABLE_CONTEXT.json",
        "closure_file": "WEB_PORTABLE_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "WEB_PORTABLE_CONDITIONAL_IMPORTS.json",
        "package_file": "WEB_PORTABLE_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "WEB_PORTABLE_UNRESOLVED_BRANCHES.json",
        "coverage_file": "WEB_PORTABLE_COVERAGE.json",
        "runtime_uncertainty_file": None,
        "receipt_file": "WEB_PORTABLE_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 57, "edges": 165, "parsed": 536, "conditional": 126, "unresolved": 1, "cycles": 0},
    },
    {
        "key": "web_with_comfyui_helper",
        "label": "Web With ComfyUI Helper",
        "mission_id": "ENG-20260721-222209-FFD6EF",
        "context_id": "CTX-E47F4DAA05CBCD6B",
        "path_group_id": "PATHGROUP-25300F3FBF74CEEB",
        "context_file": "WEB_WITH_COMFYUI_HELPER_CONTEXT.json",
        "closure_file": "WEB_WITH_COMFYUI_HELPER_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "WEB_WITH_COMFYUI_HELPER_CONDITIONAL_IMPORTS.json",
        "package_file": "WEB_WITH_COMFYUI_HELPER_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "WEB_WITH_COMFYUI_HELPER_UNRESOLVED_BRANCHES.json",
        "coverage_file": "WEB_WITH_COMFYUI_HELPER_COVERAGE.json",
        "runtime_uncertainty_file": None,
        "receipt_file": "WEB_WITH_COMFYUI_HELPER_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 1, "edges": 0, "parsed": 12, "conditional": 1, "unresolved": 1, "cycles": 0},
    },
    {
        "key": "workshop_comfyui_manager",
        "label": "Workshop ComfyUI Manager",
        "mission_id": "ENG-20260721-224437-0FDDE1",
        "context_id": "CTX-EEC78B5B382B239D",
        "path_group_id": "PATHGROUP-25300F3FBF74CEEB",
        "context_file": "WORKSHOP_COMFYUI_MANAGER_CONTEXT.json",
        "closure_file": "WORKSHOP_COMFYUI_MANAGER_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "WORKSHOP_COMFYUI_MANAGER_CONDITIONAL_IMPORTS.json",
        "package_file": "WORKSHOP_COMFYUI_MANAGER_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "WORKSHOP_COMFYUI_MANAGER_UNRESOLVED_BRANCHES.json",
        "coverage_file": "WORKSHOP_COMFYUI_MANAGER_COVERAGE.json",
        "runtime_uncertainty_file": None,
        "receipt_file": "WORKSHOP_COMFYUI_MANAGER_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 1, "edges": 0, "parsed": 18, "conditional": 1, "unresolved": 1, "cycles": 0},
    },
    {
        "key": "workshop_main",
        "label": "Workshop Main foxai.py",
        "mission_id": "ENG-20260721-232230-72B494",
        "context_id": "CTX-68030A15EE97A526",
        "path_group_id": "PATHGROUP-266CA7411F12A68D",
        "context_file": "WORKSHOP_MAIN_CONTEXT.json",
        "closure_file": "WORKSHOP_MAIN_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "WORKSHOP_MAIN_CONDITIONAL_IMPORTS.json",
        "package_file": "WORKSHOP_MAIN_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "WORKSHOP_MAIN_UNRESOLVED_BRANCHES.json",
        "coverage_file": "WORKSHOP_MAIN_COVERAGE.json",
        "runtime_uncertainty_file": "WORKSHOP_MAIN_RUNTIME_UNCERTAINTY.json",
        "receipt_file": "WORKSHOP_MAIN_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 70, "edges": 205, "parsed": 408, "conditional": 7, "unresolved": 15, "cycles": 0},
    },
    {
        "key": "desktop_recovery_helper",
        "label": "Desktop Recovery ComfyUI Helper",
        "mission_id": "ENG-20260721-233008-E93FBD",
        "context_id": "CTX-FCE6D44FA8CBAF96",
        "path_group_id": "PATHGROUP-26C1A7D4F9C70C86",
        "context_file": "DESKTOP_RECOVERY_HELPER_CONTEXT.json",
        "closure_file": "DESKTOP_RECOVERY_HELPER_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "DESKTOP_RECOVERY_HELPER_CONDITIONAL_IMPORTS.json",
        "package_file": "DESKTOP_RECOVERY_HELPER_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "DESKTOP_RECOVERY_HELPER_UNRESOLVED_BRANCHES.json",
        "coverage_file": "DESKTOP_RECOVERY_HELPER_COVERAGE.json",
        "runtime_uncertainty_file": None,
        "receipt_file": "DESKTOP_RECOVERY_HELPER_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 1, "edges": 0, "parsed": 12, "conditional": 1, "unresolved": 1, "cycles": 0},
    },
    {
        "key": "desktop_recovery_gui",
        "label": "Desktop Recovery GUI foxai.py",
        "mission_id": "ENG-20260721-234311-5F92E4",
        "context_id": "CTX-5A02B9D4A8E26D64",
        "path_group_id": "PATHGROUP-529C568E9980095F",
        "context_file": "DESKTOP_RECOVERY_GUI_CONTEXT.json",
        "closure_file": "DESKTOP_RECOVERY_GUI_FIRST_PARTY_CLOSURE.json",
        "conditional_file": "DESKTOP_RECOVERY_GUI_CONDITIONAL_IMPORTS.json",
        "package_file": "DESKTOP_RECOVERY_GUI_PACKAGE_REQUIREMENTS.json",
        "unresolved_file": "DESKTOP_RECOVERY_GUI_UNRESOLVED_BRANCHES.json",
        "coverage_file": "DESKTOP_RECOVERY_GUI_COVERAGE.json",
        "runtime_uncertainty_file": "DESKTOP_RECOVERY_GUI_RUNTIME_UNCERTAINTY.json",
        "receipt_file": "DESKTOP_RECOVERY_GUI_CLOSURE_RECEIPT.json",
        "counts": {"nodes": 70, "edges": 205, "parsed": 408, "conditional": 7, "unresolved": 1, "cycles": 0},
    },
)

LINK_SPECS = (
    {
        "source_context_id": "CTX-E47F4DAA05CBCD6B",
        "target_context_id": "CTX-23820E95DB51A6C5",
        "relationship": "called_launcher",
        "source_spec_key": "web_with_comfyui_helper",
        "source_file": "WEB_WITH_COMFYUI_HELPER_CONTEXT.json",
        "field_path": "$.called_launcher_relationship",
    },
    {
        "source_context_id": "CTX-68030A15EE97A526",
        "target_context_id": "CTX-EEC78B5B382B239D",
        "relationship": "same_launcher_linked_completed_context",
        "source_spec_key": "workshop_main",
        "source_file": "WORKSHOP_MAIN_CONTEXT.json",
        "field_path": "$.linked_completed_manager_context",
    },
    {
        "source_context_id": "CTX-FCE6D44FA8CBAF96",
        "target_context_id": "CTX-E47F4DAA05CBCD6B",
        "relationship": "same_entry_script_distinct_launcher_context",
        "source_spec_key": "desktop_recovery_helper",
        "source_file": "DESKTOP_RECOVERY_HELPER_CONTEXT.json",
        "field_path": "$.linked_completed_same_entry_script_context",
    },
    {
        "source_context_id": "CTX-5A02B9D4A8E26D64",
        "target_context_id": "CTX-68030A15EE97A526",
        "relationship": "same_entry_script_distinct_runtime_boundary",
        "source_spec_key": "desktop_recovery_gui",
        "source_file": "DESKTOP_RECOVERY_GUI_CONTEXT.json",
        "field_path": "$.linked_completed_workshop_main_context",
    },
    {
        "source_context_id": "CTX-5A02B9D4A8E26D64",
        "target_context_id": "CTX-FCE6D44FA8CBAF96",
        "relationship": "same_launcher_linked_completed_context",
        "source_spec_key": "desktop_recovery_gui",
        "source_file": "DESKTOP_RECOVERY_GUI_CONTEXT.json",
        "field_path": "$.linked_completed_desktop_recovery_helper_context",
    },
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm_win(value: Any) -> str:
    if value is None:
        return ""
    return str(PureWindowsPath(str(value).replace("/", "\\"))).casefold()


def value_from_context(context_doc: dict[str, Any], *names: str, default: Any = None) -> Any:
    inner = context_doc.get("context") if isinstance(context_doc.get("context"), dict) else {}
    for name in names:
        if name in inner:
            return inner[name]
        if name in context_doc:
            return context_doc[name]
    return default


def evidence_path(source_dir: Path, filename: str) -> str:
    return str(source_dir / filename)


def source_ref(loaded: dict[str, Any], filename: str, field_path: str, record_locator: str | None = None) -> dict[str, Any]:
    spec = loaded["spec"]
    result = {
        "source_mission_id": spec["mission_id"],
        "evidence_file": filename,
        "evidence_path": evidence_path(loaded["source_dir"], filename),
        "evidence_sha256": loaded["hashes"][filename],
        "json_field_path": field_path,
        "receipt_file": spec["receipt_file"],
        "receipt_path": evidence_path(loaded["source_dir"], spec["receipt_file"]),
        "receipt_sha256": loaded["receipt_sha256"],
    }
    if record_locator is not None:
        result["record_locator"] = record_locator
    return result


def fact(value: Any, loaded: dict[str, Any], filename: str, field_path: str) -> dict[str, Any]:
    return {"value": value, "source": source_ref(loaded, filename, field_path)}


def expected_core_files(spec: dict[str, Any]) -> list[str]:
    files = [
        spec["context_file"], spec["closure_file"], spec["conditional_file"],
        spec["package_file"], spec["unresolved_file"], spec["coverage_file"],
    ]
    if spec.get("runtime_uncertainty_file"):
        files.append(spec["runtime_uncertainty_file"])
    return files


def load_source(spec: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)
    receipt_path = source_dir / spec["receipt_file"]
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)
    receipt = read_json(receipt_path)
    if receipt.get("mission_id") != spec["mission_id"]:
        raise ValueError(f"Mission mismatch for {spec['key']}: {receipt.get('mission_id')}")
    if receipt.get("internal_deterministic_rebuild_match") is not True:
        raise ValueError(f"Source closure is not deterministic: {spec['key']}")
    if receipt.get("imports_or_source_executed") is not False:
        raise ValueError(f"Source closure execution flag changed: {spec['key']}")
    if int(receipt.get("interpreter_child_processes") or 0) != 0:
        raise ValueError(f"Source closure child process count changed: {spec['key']}")

    recorded = {str(row.get("name")): row for row in receipt.get("core_outputs_before_receipt", [])}
    hashes: dict[str, str] = {}
    docs: dict[str, Any] = {}
    for filename in expected_core_files(spec):
        path = source_dir / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = sha256_file(path)
        size = path.stat().st_size
        row = recorded.get(filename)
        if row is None:
            raise ValueError(f"Receipt lacks output record: {spec['key']} {filename}")
        if int(row.get("size_bytes")) != size or str(row.get("sha256")) != digest:
            raise ValueError(f"Receipt hash/size mismatch: {spec['key']} {filename}")
        hashes[filename] = digest
        docs[filename] = read_json(path)

    hashes[spec["receipt_file"]] = sha256_file(receipt_path)
    context_doc = docs[spec["context_file"]]
    coverage_doc = docs[spec["coverage_file"]]
    closure_doc = docs[spec["closure_file"]]
    unresolved_doc = docs[spec["unresolved_file"]]

    context_id = value_from_context(context_doc, "context_id")
    path_group_id = value_from_context(context_doc, "path_group_id")
    mission_id = context_doc.get("mission_id") or receipt.get("mission_id")
    if mission_id != spec["mission_id"] or context_id != spec["context_id"] or path_group_id != spec["path_group_id"]:
        raise ValueError(f"Context identity changed for {spec['key']}")

    counts = spec["counts"]
    checks = {
        "nodes": coverage_doc.get("closure_node_count"),
        "edges": coverage_doc.get("closure_edge_count"),
        "parsed": coverage_doc.get("parsed_import_count"),
        "conditional": coverage_doc.get("conditional_or_deferred_import_count"),
        "unresolved": coverage_doc.get("unresolved_branch_count"),
        "cycles": coverage_doc.get("cycle_count"),
    }
    if checks != counts:
        raise ValueError(f"Coverage counts changed for {spec['key']}: {checks}")
    if int(closure_doc.get("node_count")) != counts["nodes"] or int(closure_doc.get("edge_count")) != counts["edges"]:
        raise ValueError(f"Closure topology mismatch for {spec['key']}")
    if len(unresolved_doc.get("records", [])) != counts["unresolved"]:
        raise ValueError(f"Unresolved count mismatch for {spec['key']}")

    return {
        "spec": spec,
        "source_dir": source_dir,
        "receipt": receipt,
        "receipt_sha256": hashes[spec["receipt_file"]],
        "hashes": hashes,
        "docs": docs,
    }


def build_context_registry_entry(loaded: dict[str, Any]) -> dict[str, Any]:
    spec = loaded["spec"]
    context_file = spec["context_file"]
    coverage_file = spec["coverage_file"]
    receipt_file = spec["receipt_file"]
    context_doc = loaded["docs"][context_file]
    coverage = loaded["docs"][coverage_file]
    receipt = loaded["receipt"]
    inner_path = "$.context" if isinstance(context_doc.get("context"), dict) else "$"

    def context_fact(names: tuple[str, ...], output_name: str | None = None, default: Any = None) -> dict[str, Any]:
        value = value_from_context(context_doc, *names, default=default)
        field = names[0]
        if isinstance(context_doc.get("context"), dict) and field in context_doc["context"]:
            field_path = f"$.context.{field}"
        else:
            field_path = f"$.{field}"
        return fact(value, loaded, context_file, field_path)

    facts = {
        "context_id": context_fact(("context_id",)),
        "path_group_id": context_fact(("path_group_id",)),
        "launcher_path": context_fact(("launcher_path",)),
        "launcher_line": context_fact(("line", "launcher_line")),
        "interpreter_reference": context_fact(("interpreter_reference",)),
        "interpreter_reference_kind": context_fact(("interpreter_reference_kind",)),
        "resolved_interpreter_path": context_fact(("resolved_interpreter_path",)),
        "runtime_id": context_fact(("runtime_id",)),
        "runtime_portability_classification": context_fact(("runtime_portability_classification",)),
        "runtime_resolution_status": context_fact(("runtime_resolution_status",), default=(
            "resolved_static_evidence" if value_from_context(context_doc, "resolved_interpreter_path") else "unresolved"
        )),
        "entry_script": context_fact(("script_path", "entry_script")),
        "flags": context_fact(("flags",), default=[]),
        "arguments": context_fact(("arguments",), default=[]),
        "working_directory": context_fact(("working_directory",)),
        "source_kind": context_fact(("source_kind",)),
        "uncertainty": context_fact(("uncertainty",), default=[]),
        "launcher_environment": context_fact(("launcher_environment",), default={}),
        "effective_path_entries": context_fact(("effective_path_entries",), default=[]),
        "closure_node_count": fact(coverage["closure_node_count"], loaded, coverage_file, "$.closure_node_count"),
        "closure_edge_count": fact(coverage["closure_edge_count"], loaded, coverage_file, "$.closure_edge_count"),
        "parsed_import_count": fact(coverage["parsed_import_count"], loaded, coverage_file, "$.parsed_import_count"),
        "conditional_or_deferred_import_count": fact(coverage["conditional_or_deferred_import_count"], loaded, coverage_file, "$.conditional_or_deferred_import_count"),
        "unresolved_branch_count": fact(coverage["unresolved_branch_count"], loaded, coverage_file, "$.unresolved_branch_count"),
        "cycle_count": fact(coverage["cycle_count"], loaded, coverage_file, "$.cycle_count"),
        "maximum_reads_per_source_file": fact(coverage["maximum_reads_per_source_file"], loaded, coverage_file, "$.maximum_reads_per_source_file"),
        "peak_source_bytes_in_memory": fact(coverage["peak_source_bytes_in_memory"], loaded, coverage_file, "$.peak_source_bytes_in_memory"),
        "internal_deterministic_rebuild_match": fact(receipt["internal_deterministic_rebuild_match"], loaded, receipt_file, "$.internal_deterministic_rebuild_match"),
    }
    return {
        "context_key": spec["key"],
        "label": spec["label"],
        "source_mission_id": spec["mission_id"],
        "source_directory": str(loaded["source_dir"]),
        "source_receipt": {
            "file": receipt_file,
            "path": str(loaded["source_dir"] / receipt_file),
            "sha256": loaded["receipt_sha256"],
        },
        "facts": facts,
    }


def build_outputs(mission_id: str, loaded_sources: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {item["spec"]["key"]: item for item in loaded_sources}
    contexts = [build_context_registry_entry(item) for item in loaded_sources]
    context_by_id = {entry["facts"]["context_id"]["value"]: entry for entry in contexts}

    registry = {
        "schema": f"{SCHEMA_PREFIX}.protected_context_registry.v1",
        "mission_id": mission_id,
        "protected_context_count": len(contexts),
        "unique_launcher_count": len({norm_win(c["facts"]["launcher_path"]["value"]) for c in contexts}),
        "unique_path_group_count": len({c["facts"]["path_group_id"]["value"] for c in contexts}),
        "contexts": contexts,
        "registry_policy": {
            "separate_context_evidence_boundaries_preserved": True,
            "closure_nodes_or_edges_copied": False,
            "cartesian_expansion_used": False,
            "runtime_facts_inferred_across_contexts": False,
        },
    }

    launcher_groups: dict[str, dict[str, Any]] = {}
    for entry in contexts:
        launcher = entry["facts"]["launcher_path"]["value"]
        key = norm_win(launcher)
        group = launcher_groups.setdefault(key, {
            "launcher_path": launcher,
            "contexts": [],
        })
        group["contexts"].append({
            "context_id": entry["facts"]["context_id"],
            "launcher_line": entry["facts"]["launcher_line"],
            "interpreter_reference": entry["facts"]["interpreter_reference"],
            "resolved_interpreter_path": entry["facts"]["resolved_interpreter_path"],
            "runtime_id": entry["facts"]["runtime_id"],
            "runtime_resolution_status": entry["facts"]["runtime_resolution_status"],
            "entry_script": entry["facts"]["entry_script"],
            "flags": entry["facts"]["flags"],
            "arguments": entry["facts"]["arguments"],
            "working_directory": entry["facts"]["working_directory"],
        })
    launcher_map = {
        "schema": f"{SCHEMA_PREFIX}.launcher_runtime_entry_map.v1",
        "mission_id": mission_id,
        "unique_launcher_count": len(launcher_groups),
        "context_count": len(contexts),
        "launchers": sorted(launcher_groups.values(), key=lambda row: norm_win(row["launcher_path"])),
    }

    dependency_contexts = []
    for loaded, entry in zip(loaded_sources, contexts):
        spec = loaded["spec"]
        package_doc = loaded["docs"][spec["package_file"]]
        package_fields = {}
        for field in (
            "standard_library_candidates",
            "probable_module_load_candidates",
            "deferred_optional_or_conditional_candidates",
            "missing_or_incomplete_candidates",
            "packages_imported",
        ):
            package_fields[field] = fact(package_doc.get(field), loaded, spec["package_file"], f"$.{field}")
        dependency_contexts.append({
            "context_id": entry["facts"]["context_id"],
            "label": spec["label"],
            "counts": {
                name: entry["facts"][name]
                for name in (
                    "closure_node_count", "closure_edge_count", "parsed_import_count",
                    "conditional_or_deferred_import_count", "unresolved_branch_count",
                    "cycle_count", "maximum_reads_per_source_file", "peak_source_bytes_in_memory",
                )
            },
            "package_candidates": package_fields,
            "closure_record_policy": {
                "node_records_included": False,
                "edge_records_included": False,
                "authoritative_closure_file": source_ref(loaded, spec["closure_file"], "$"),
            },
        })
    dependency_summary = {
        "schema": f"{SCHEMA_PREFIX}.context_dependency_summary.v1",
        "mission_id": mission_id,
        "context_count": len(dependency_contexts),
        "contexts": dependency_contexts,
        "merged_closure_nodes_or_edges": False,
    }

    unresolved_contexts = []
    for loaded, entry in zip(loaded_sources, contexts):
        spec = loaded["spec"]
        unresolved_doc = loaded["docs"][spec["unresolved_file"]]
        unresolved_records = []
        for index, record in enumerate(unresolved_doc.get("records", [])):
            unresolved_records.append({
                "record": record,
                "confirmed_runtime_failure": False,
                "source": source_ref(
                    loaded, spec["unresolved_file"], f"$.records[{index}]",
                    record_locator=f"records[{index}]",
                ),
            })
        runtime_file = spec.get("runtime_uncertainty_file")
        if runtime_file:
            runtime_uncertainty = {
                "value": loaded["docs"][runtime_file],
                "source": source_ref(loaded, runtime_file, "$"),
            }
        else:
            runtime_uncertainty = {
                "value": {
                    "runtime_resolution_status": entry["facts"]["runtime_resolution_status"]["value"],
                    "uncertainty": entry["facts"]["uncertainty"]["value"],
                    "resolved_interpreter_path": entry["facts"]["resolved_interpreter_path"]["value"],
                    "runtime_id": entry["facts"]["runtime_id"]["value"],
                },
                "sources": [
                    entry["facts"]["runtime_resolution_status"]["source"],
                    entry["facts"]["uncertainty"]["source"],
                    entry["facts"]["resolved_interpreter_path"]["source"],
                    entry["facts"]["runtime_id"]["source"],
                ],
            }
        unresolved_contexts.append({
            "context_id": entry["facts"]["context_id"],
            "label": spec["label"],
            "unresolved_records": unresolved_records,
            "runtime_uncertainty": runtime_uncertainty,
        })
    unresolved_index = {
        "schema": f"{SCHEMA_PREFIX}.unresolved_and_runtime_uncertainty_index.v1",
        "mission_id": mission_id,
        "context_count": len(unresolved_contexts),
        "unresolved_record_count": sum(len(row["unresolved_records"]) for row in unresolved_contexts),
        "contexts": unresolved_contexts,
        "unresolved_branches_labeled_confirmed": False,
    }

    links = []
    for link in LINK_SPECS:
        loaded = by_key[link["source_spec_key"]]
        links.append({
            "source_context_id": link["source_context_id"],
            "target_context_id": link["target_context_id"],
            "relationship": link["relationship"],
            "nodes_or_edges_merged": False,
            "source": source_ref(loaded, link["source_file"], link["field_path"]),
        })
    link_graph = {
        "schema": f"{SCHEMA_PREFIX}.context_link_graph.v1",
        "mission_id": mission_id,
        "context_nodes": [
            {
                "context_id": entry["facts"]["context_id"]["value"],
                "label": entry["label"],
                "launcher_path": entry["facts"]["launcher_path"]["value"],
                "source_mission_id": entry["source_mission_id"],
            }
            for entry in contexts
        ],
        "links": links,
        "link_count": len(links),
        "dependency_nodes_or_edges_included": False,
        "cartesian_expansion_used": False,
    }

    query_examples = f"""# Protected Context Registry Query Examples\n\nThe query bridge reads only the generated V1A-3D registry outputs. It does not reopen or merge the six large closure graphs.\n\n```bat\n{Path('Z:/FOXAI/Runtime/Desktop/python/python.exe')} -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action list-contexts\n```\n\n```bat\nZ:\\FOXAI\\Runtime\\Desktop\\python\\python.exe -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action contexts-for-launcher --launcher \"Z:\\FOXAI\\Launch FOXAI Workshop.bat\"\n```\n\n```bat\nZ:\\FOXAI\\Runtime\\Desktop\\python\\python.exe -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-context --context-id CTX-68030A15EE97A526\n```\n\n```bat\nZ:\\FOXAI\\Runtime\\Desktop\\python\\python.exe -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-package-candidates --context-id CTX-5A02B9D4A8E26D64\n```\n\n```bat\nZ:\\FOXAI\\Runtime\\Desktop\\python\\python.exe -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-runtime-uncertainty --context-id CTX-68030A15EE97A526\n```\n\n```bat\nZ:\\FOXAI\\Runtime\\Desktop\\python\\python.exe -I -B -S Z:\\FOXAI\\System\\AgentFoxTechnicalCore\\protected_context_registry_query_bridge_v1.py query --index-dir Z:\\FOXAI\\System\\EngineeringWorkshop\\missions\\{mission_id}_V1A3D_PROTECTED_CONTEXT_REGISTRY --action locate-fact --context-id CTX-5A02B9D4A8E26D64 --fact resolved_interpreter_path\n```\n"""

    source_receipts = [
        {
            "mission_id": loaded["spec"]["mission_id"],
            "context_id": loaded["spec"]["context_id"],
            "receipt_file": loaded["spec"]["receipt_file"],
            "receipt_path": str(loaded["source_dir"] / loaded["spec"]["receipt_file"]),
            "receipt_sha256": loaded["receipt_sha256"],
            "verified_core_outputs": [
                {
                    "name": filename,
                    "sha256": loaded["hashes"][filename],
                    "size_bytes": (loaded["source_dir"] / filename).stat().st_size,
                }
                for filename in expected_core_files(loaded["spec"])
            ],
        }
        for loaded in loaded_sources
    ]

    coverage = {
        "schema": f"{SCHEMA_PREFIX}.protected_context_registry_coverage.v1",
        "mission_id": mission_id,
        "protected_context_count": len(contexts),
        "unique_launcher_count": registry["unique_launcher_count"],
        "unique_path_group_count": registry["unique_path_group_count"],
        "source_mission_count": len(source_receipts),
        "source_receipts_and_hashes_verified": True,
        "source_receipts": source_receipts,
        "closure_node_records_copied": 0,
        "closure_edge_records_copied": 0,
        "merged_closure_nodes_or_edges": False,
        "cartesian_expansion_used": False,
        "false_runtime_resolution_count": 0,
        "unresolved_branches_labeled_confirmed": False,
        "live_source_files_scanned_or_parsed": 0,
        "interpreter_child_processes": 0,
        "shell_child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "existing_foxai_source_modified": False,
    }

    return {
        "PROTECTED_CONTEXT_REGISTRY.json": registry,
        "LAUNCHER_RUNTIME_ENTRY_MAP.json": launcher_map,
        "CONTEXT_DEPENDENCY_SUMMARY.json": dependency_summary,
        "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json": unresolved_index,
        "CONTEXT_LINK_GRAPH.json": link_graph,
        "QUERY_EXAMPLES.md": query_examples,
        "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json": coverage,
    }


def serialize_core_outputs(outputs: dict[str, Any]) -> dict[str, bytes]:
    serialized: dict[str, bytes] = {}
    for name in OUTPUT_NAMES:
        value = outputs[name]
        serialized[name] = value.encode("utf-8") if isinstance(value, str) else canonical_bytes(value)
    return serialized


def verify_loaded_set(loaded_sources: list[dict[str, Any]]) -> None:
    if len(loaded_sources) != 6:
        raise ValueError(f"Expected six protected contexts, found {len(loaded_sources)}")
    if {item["spec"]["context_id"] for item in loaded_sources} != {spec["context_id"] for spec in SPECS}:
        raise ValueError("Protected context set changed")


def write_build(mission_id: str, output_dir: Path, loaded_sources: list[dict[str, Any]]) -> dict[str, Any]:
    verify_loaded_set(loaded_sources)
    first = build_outputs(mission_id, loaded_sources)
    second = build_outputs(mission_id, loaded_sources)
    first_bytes = serialize_core_outputs(first)
    second_bytes = serialize_core_outputs(second)
    if first_bytes != second_bytes:
        raise ValueError("Deterministic registry rebuild mismatch")
    total_core = sum(len(data) for data in first_bytes.values())
    if total_core >= OUTPUT_LIMIT_BYTES:
        raise ValueError(f"Core output exceeds limit: {total_core}")

    output_dir.mkdir(parents=True, exist_ok=False)
    core_records = []
    for name in OUTPUT_NAMES:
        path = output_dir / name
        path.write_bytes(first_bytes[name])
        core_records.append({
            "name": name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    receipt = {
        "schema": f"{SCHEMA_PREFIX}.protected_context_registry_receipt.v1",
        "mission_id": mission_id,
        "result": "protected_context_registry_complete",
        "protected_context_count": 6,
        "unique_launcher_count": 4,
        "unique_path_group_count": 5,
        "source_mission_count": 6,
        "source_receipts_and_hashes_verified": True,
        "internal_deterministic_rebuild_match": True,
        "core_outputs_before_receipt": core_records,
        "exact_output_count_including_receipt": 8,
        "closure_node_records_copied": 0,
        "closure_edge_records_copied": 0,
        "merged_closure_nodes_or_edges": False,
        "cartesian_expansion_used": False,
        "runtime_facts_inferred_across_contexts": False,
        "unresolved_branches_labeled_confirmed": False,
        "live_source_files_scanned_or_parsed": 0,
        "interpreter_child_processes": 0,
        "shell_child_processes": 0,
        "network_used": False,
        "packages_installed": False,
        "models_loaded": False,
        "existing_foxai_source_modified": False,
    }
    receipt_path = output_dir / RECEIPT_NAME
    receipt_path.write_bytes(canonical_bytes(receipt))
    total = sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file())
    if total >= OUTPUT_LIMIT_BYTES:
        raise ValueError(f"Total output exceeds limit: {total}")
    return {
        "status": "built",
        "output_dir": str(output_dir),
        "protected_context_count": 6,
        "unique_launcher_count": 4,
        "unique_path_group_count": 5,
        "total_output_bytes": total,
    }


def recursively_validate_fact_sources(value: Any) -> int:
    count = 0
    if isinstance(value, dict):
        if "value" in value and "source" in value and isinstance(value["source"], dict):
            source = value["source"]
            required = {
                "source_mission_id", "evidence_file", "evidence_path", "evidence_sha256",
                "json_field_path", "receipt_file", "receipt_path", "receipt_sha256",
            }
            if not required.issubset(source):
                raise ValueError(f"Incomplete fact provenance: {sorted(required - set(source))}")
            count += 1
        for item in value.values():
            count += recursively_validate_fact_sources(item)
    elif isinstance(value, list):
        for item in value:
            count += recursively_validate_fact_sources(item)
    return count


def validate_output(index_dir: Path) -> dict[str, Any]:
    required = set(OUTPUT_NAMES) | {RECEIPT_NAME}
    present = {path.name for path in index_dir.iterdir() if path.is_file()}
    if present != required:
        raise ValueError(f"Output set mismatch: {present ^ required}")
    registry = read_json(index_dir / "PROTECTED_CONTEXT_REGISTRY.json")
    launcher_map = read_json(index_dir / "LAUNCHER_RUNTIME_ENTRY_MAP.json")
    dependency = read_json(index_dir / "CONTEXT_DEPENDENCY_SUMMARY.json")
    unresolved = read_json(index_dir / "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json")
    links = read_json(index_dir / "CONTEXT_LINK_GRAPH.json")
    coverage = read_json(index_dir / "PROTECTED_CONTEXT_REGISTRY_COVERAGE.json")
    receipt = read_json(index_dir / RECEIPT_NAME)

    if registry.get("protected_context_count") != 6 or len(registry.get("contexts", [])) != 6:
        raise ValueError("Registry context count mismatch")
    if registry.get("unique_launcher_count") != 4 or launcher_map.get("unique_launcher_count") != 4:
        raise ValueError("Launcher count mismatch")
    if registry.get("unique_path_group_count") != 5:
        raise ValueError("Path-group count mismatch")
    if dependency.get("merged_closure_nodes_or_edges") is not False:
        raise ValueError("Dependency closure merge flag changed")
    if links.get("dependency_nodes_or_edges_included") is not False or links.get("cartesian_expansion_used") is not False:
        raise ValueError("Link graph boundary changed")
    if unresolved.get("unresolved_branches_labeled_confirmed") is not False:
        raise ValueError("Unresolved branches were mislabeled confirmed")
    if coverage.get("source_receipts_and_hashes_verified") is not True or len(coverage.get("source_receipts", [])) != 6:
        raise ValueError("Source receipt verification incomplete")

    contexts = {row["facts"]["context_id"]["value"]: row for row in registry["contexts"]}
    workshop = contexts["CTX-68030A15EE97A526"]["facts"]
    if workshop["resolved_interpreter_path"]["value"] is not None or workshop["runtime_id"]["value"] is not None:
        raise ValueError("Workshop command alias was falsely resolved")
    desktop_gui = contexts["CTX-5A02B9D4A8E26D64"]["facts"]
    if desktop_gui["runtime_resolution_status"]["value"] != "statically_inferred_pythonw_sibling_not_directly_probed":
        raise ValueError("pythonw uncertainty status changed")
    if "pythonw_runtime_identity_not_directly_probed" not in desktop_gui["uncertainty"]["value"]:
        raise ValueError("pythonw direct-probe uncertainty missing")

    fact_source_count = recursively_validate_fact_sources(registry)
    fact_source_count += recursively_validate_fact_sources(launcher_map)
    fact_source_count += recursively_validate_fact_sources(dependency)
    if fact_source_count < 100:
        raise ValueError(f"Too few provenance-bearing facts: {fact_source_count}")

    recorded = {row["name"]: row for row in receipt.get("core_outputs_before_receipt", [])}
    if set(recorded) != set(OUTPUT_NAMES):
        raise ValueError("Receipt core output set mismatch")
    for name in OUTPUT_NAMES:
        path = index_dir / name
        row = recorded[name]
        if path.stat().st_size != int(row["size_bytes"]) or sha256_file(path) != row["sha256"]:
            raise ValueError(f"Receipt output hash mismatch: {name}")
    if receipt.get("internal_deterministic_rebuild_match") is not True:
        raise ValueError("Registry deterministic status changed")
    if any(receipt.get(name) not in (False, 0) for name in (
        "merged_closure_nodes_or_edges", "cartesian_expansion_used",
        "runtime_facts_inferred_across_contexts", "unresolved_branches_labeled_confirmed",
        "live_source_files_scanned_or_parsed", "interpreter_child_processes", "shell_child_processes",
        "network_used", "packages_installed", "models_loaded", "existing_foxai_source_modified",
    )):
        raise ValueError("Safety receipt contains a nonzero/true forbidden condition")
    total = sum(path.stat().st_size for path in index_dir.iterdir() if path.is_file())
    if total >= OUTPUT_LIMIT_BYTES:
        raise ValueError(f"Output size exceeds limit: {total}")
    return {
        "status": "valid",
        "protected_context_count": 6,
        "unique_launcher_count": 4,
        "unique_path_group_count": 5,
        "fact_source_count": fact_source_count,
        "total_output_bytes": total,
    }


def load_registry_indexes(index_dir: Path) -> dict[str, Any]:
    return {
        "registry": read_json(index_dir / "PROTECTED_CONTEXT_REGISTRY.json"),
        "launcher_map": read_json(index_dir / "LAUNCHER_RUNTIME_ENTRY_MAP.json"),
        "dependency": read_json(index_dir / "CONTEXT_DEPENDENCY_SUMMARY.json"),
        "unresolved": read_json(index_dir / "UNRESOLVED_AND_RUNTIME_UNCERTAINTY_INDEX.json"),
        "links": read_json(index_dir / "CONTEXT_LINK_GRAPH.json"),
    }


def query(index_dir: Path, action: str, context_id: str | None, launcher: str | None, fact_name: str | None) -> Any:
    data = load_registry_indexes(index_dir)
    contexts = data["registry"]["contexts"]
    by_id = {row["facts"]["context_id"]["value"]: row for row in contexts}
    if action == "list-contexts":
        return [
            {
                "context_id": row["facts"]["context_id"],
                "label": row["label"],
                "launcher_path": row["facts"]["launcher_path"],
                "entry_script": row["facts"]["entry_script"],
            }
            for row in contexts
        ]
    if action == "contexts-for-launcher":
        if not launcher:
            raise ValueError("--launcher is required")
        matches = [row for row in data["launcher_map"]["launchers"] if norm_win(row["launcher_path"]) == norm_win(launcher)]
        return {"launcher": launcher, "matches": matches}
    if action == "show-mapping":
        return data["launcher_map"]
    if action == "show-context":
        if context_id not in by_id:
            raise KeyError(context_id)
        return by_id[context_id]
    if action == "show-unresolved":
        rows = data["unresolved"]["contexts"]
        return next(row for row in rows if row["context_id"]["value"] == context_id) if context_id else rows
    if action == "show-package-candidates":
        rows = data["dependency"]["contexts"]
        return next(row for row in rows if row["context_id"]["value"] == context_id) if context_id else rows
    if action == "show-runtime-uncertainty":
        if not context_id:
            raise ValueError("--context-id is required")
        rows = data["unresolved"]["contexts"]
        row = next(row for row in rows if row["context_id"]["value"] == context_id)
        return {"context_id": row["context_id"], "label": row["label"], "runtime_uncertainty": row["runtime_uncertainty"]}
    if action == "show-links":
        return data["links"]
    if action == "locate-fact":
        if not context_id or not fact_name:
            raise ValueError("--context-id and --fact are required")
        row = by_id[context_id]
        if fact_name not in row["facts"]:
            raise KeyError(fact_name)
        return {"context_id": context_id, "fact": fact_name, "result": row["facts"][fact_name]}
    raise ValueError(f"Unknown action: {action}")


def source_dir_args(parser: argparse.ArgumentParser) -> None:
    for spec in SPECS:
        parser.add_argument(f"--{spec['key'].replace('_', '-')}-dir", required=True)


def source_dirs_from_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    loaded = []
    for spec in SPECS:
        attr = spec["key"] + "_dir"
        loaded.append(load_source(spec, Path(getattr(args, attr))))
    return loaded


def self_test() -> None:
    assert norm_win("Z:/FOXAI/core/foxai_web.py") == norm_win(r"z:\foxai\core\foxai_web.py")
    assert len(SPECS) == 6
    assert len({spec["context_id"] for spec in SPECS}) == 6
    assert len({spec["path_group_id"] for spec in SPECS}) == 5
    assert len(LINK_SPECS) == 5
    print("V1A3D_REGISTRY_SELF_TEST_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")

    verify = sub.add_parser("verify-inputs")
    source_dir_args(verify)

    build = sub.add_parser("build")
    source_dir_args(build)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--mission-id", required=True)

    validate = sub.add_parser("validate-output")
    validate.add_argument("--index-dir", required=True)

    query_parser = sub.add_parser("query")
    query_parser.add_argument("--index-dir", required=True)
    query_parser.add_argument("--action", required=True, choices=(
        "list-contexts", "contexts-for-launcher", "show-mapping", "show-context",
        "show-unresolved", "show-package-candidates", "show-runtime-uncertainty",
        "show-links", "locate-fact",
    ))
    query_parser.add_argument("--context-id")
    query_parser.add_argument("--launcher")
    query_parser.add_argument("--fact")

    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
        return 0
    if args.command == "verify-inputs":
        loaded = source_dirs_from_args(args)
        verify_loaded_set(loaded)
        print(json.dumps({
            "status": "verified",
            "protected_context_count": 6,
            "unique_launcher_count": len({norm_win(value_from_context(item['docs'][item['spec']['context_file']], 'launcher_path')) for item in loaded}),
            "unique_path_group_count": len({item['spec']['path_group_id'] for item in loaded}),
            "source_receipt_count": 6,
            "source_core_output_hashes_verified": True,
        }, sort_keys=True))
        return 0
    if args.command == "build":
        loaded = source_dirs_from_args(args)
        result = write_build(args.mission_id, Path(args.output_dir), loaded)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "validate-output":
        print(json.dumps(validate_output(Path(args.index_dir)), sort_keys=True))
        return 0
    if args.command == "query":
        result = query(Path(args.index_dir), args.action, args.context_id, args.launcher, args.fact)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
