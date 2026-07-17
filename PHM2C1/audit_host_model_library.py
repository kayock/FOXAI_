from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import platform
import re
import socket
import sys
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads((PACKAGE / "AUDIT_TARGETS.json").read_text(encoding="utf-8"))
REPORT_ROOT = ROOT / "Reports" / "HostModelAudit"

KEYWORD_GROUPS = {
    "model_profiles": [
        "MODEL_PROFILES", "model_profiles", "model profile", "profile_id",
        "profile_name", "raw exact", "gguf",
    ],
    "llama_server_launch": [
        "llama-server", "llama_server", "--model", "model_path",
        "model_file", "subprocess.Popen", "subprocess.run",
    ],
    "model_source_labels": [
        "model source", "source:", "USB", "HOST PC", "host model",
        "external model", "local model",
    ],
    "fallback_and_selection": [
        "fallback", "silent", "selected_profile", "active_model",
        "operator start", "start model", "stop model",
    ],
    "online_provider_readiness": [
        "openai", "base_url", "endpoint", "provider", "api_key",
        "credential", "authorization", "bearer", "http://", "https://",
    ],
    "machine_profiles": [
        "COMPUTERNAME", "hostname", "machine", "per-machine",
        "machine_profile", "host_profile",
    ],
}

MODEL_SUFFIXES = {".gguf", ".bin", ".safetensors"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_machine_name() -> str:
    values = [
        os.environ.get("COMPUTERNAME"),
        platform.node(),
        socket.gethostname(),
    ]
    for value in values:
        if value and value.strip():
            return value.strip().upper()
    return "UNKNOWN"


def classify_location(path: Path) -> str:
    try:
        resolved = path.resolve()
        resolved.relative_to(ROOT.resolve())
        return "USB"
    except Exception:
        pass
    for approved in TARGETS["approved_host_roots"]:
        try:
            resolved.relative_to(Path(approved).resolve())
            return "HOST_PC_APPROVED"
        except Exception:
            pass
    return "EXTERNAL_UNAPPROVED"


def file_record(path: Path, include_hash: bool = True) -> dict[str, Any]:
    result = {
        "path": str(path),
        "exists": path.is_file(),
    }
    if not path.is_file():
        return result
    stat = path.stat()
    result.update({
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "location_class": classify_location(path),
    })
    if include_hash:
        result["sha256"] = sha256(path)
    return result


def model_inventory(root: Path, source_label: str) -> dict[str, Any]:
    result = {
        "root": str(root),
        "source": source_label,
        "exists": root.is_dir(),
        "models": [],
        "error": None,
    }
    if not root.is_dir():
        return result
    try:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in MODEL_SUFFIXES:
                continue
            stat = path.stat()
            result["models"].append({
                "path": str(path),
                "relative_path": (
                    path.relative_to(root).as_posix()
                    if path.is_relative_to(root)
                    else path.name
                ),
                "filename": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "source": source_label,
                "readable": os.access(path, os.R_OK),
                "full_sha256": None,
                "hash_policy": "deferred_for_large_model",
            })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["count"] = len(result["models"])
    result["total_bytes"] = sum(
        item["size_bytes"] for item in result["models"]
    )
    return result


def keyword_hits(path: Path) -> dict[str, Any]:
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "groups": {},
        "python_ast": {},
    }
    if not path.is_file():
        return result

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    for group, terms in KEYWORD_GROUPS.items():
        hits = []
        for index, line in enumerate(lines, start=1):
            lower = line.lower()
            matched = [term for term in terms if term.lower() in lower]
            if not matched:
                continue
            hits.append({
                "line": index,
                "matched": matched,
                "text": line[:500],
            })
        result["groups"][group] = {
            "count": len(hits),
            "hits": hits[:120],
            "truncated": len(hits) > 120,
        }

    if path.suffix.lower() == ".py":
        try:
            tree = ast.parse(text, filename=str(path))
            string_constants = []
            dict_keys = set()
            subprocess_calls = []
            assignments = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    value = node.value
                    if (
                        ".gguf" in value.lower()
                        or "llama-server" in value.lower()
                        or "openai" in value.lower()
                        or "endpoint" in value.lower()
                    ):
                        string_constants.append(value[:1000])
                elif isinstance(node, ast.Dict):
                    for key in node.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            dict_keys.add(key.value)
                elif isinstance(node, ast.Call):
                    name = ""
                    if isinstance(node.func, ast.Attribute):
                        name = node.func.attr
                    elif isinstance(node.func, ast.Name):
                        name = node.func.id
                    if name in {"Popen", "run", "call", "check_call", "check_output"}:
                        subprocess_calls.append({
                            "line": getattr(node, "lineno", None),
                            "name": name,
                        })
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    line = getattr(node, "lineno", None)
                    segment = ast.get_source_segment(text, node)
                    if segment and any(
                        term in segment.lower()
                        for term in ("model", "profile", "endpoint", "provider")
                    ):
                        assignments.append({
                            "line": line,
                            "text": segment[:1000],
                        })
            result["python_ast"] = {
                "parsed": True,
                "interesting_string_constants": string_constants[:100],
                "dict_keys": sorted(dict_keys),
                "subprocess_calls": subprocess_calls[:100],
                "model_related_assignments": assignments[:150],
            }
        except Exception as exc:
            result["python_ast"] = {
                "parsed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
    return result


def infer_architecture(source_results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {group: 0 for group in KEYWORD_GROUPS}
    for source in source_results:
        for group, data in source.get("groups", {}).items():
            totals[group] += int(data.get("count", 0))

    observations = []
    if totals["model_profiles"]:
        observations.append(
            "Current model/profile logic is present in live source and can be "
            "extended rather than replaced."
        )
    if totals["llama_server_launch"]:
        observations.append(
            "Current local runtime contains llama-server/model-path handoff logic."
        )
    if totals["model_source_labels"] == 0:
        observations.append(
            "No reliable USB versus HOST PC source-label contract was detected."
        )
    else:
        observations.append(
            "Some source-related UI text exists, but the audit must determine "
            "whether it is a verified runtime identity or display-only wording."
        )
    if totals["machine_profiles"] == 0:
        observations.append(
            "No clear per-machine model-library profile was detected."
        )
    if totals["online_provider_readiness"]:
        observations.append(
            "Provider/endpoint vocabulary already exists and may support later "
            "LAN or online adapters after explicit consent and credential design."
        )
    else:
        observations.append(
            "No reusable online-provider hook was detected in the inspected files."
        )

    return {
        "keyword_totals": totals,
        "observations": observations,
        "phase2c2_required_capabilities": [
            "backend-owned model-source registry",
            "per-machine profile keyed by stable machine identifier",
            "approved external folder allowlist",
            "dynamic root/drive resolution with no hard-coded global C: dependency",
            "explicit USB/HOST_PC/LAN/ONLINE source enum",
            "verified active source returned by runtime receipt",
            "no silent source or model switching",
            "explicit fallback policy per profile",
            "host model read-only handling",
            "operator-visible unavailable state",
            "future provider adapter boundary for OpenAI-compatible endpoints",
            "explicit external-send consent before ONLINE activation",
            "credential reference only; never store secret values in plain config",
        ],
    }


def static_path_handoff_assessment(
    source_results: list[dict[str, Any]]
) -> dict[str, Any]:
    evidence = []
    absolute_path_support = False
    source_label_contract = False
    provider_hook = False

    for source in source_results:
        path = source.get("path", "")
        for hit in source.get("groups", {}).get("llama_server_launch", {}).get("hits", []):
            text = hit["text"]
            evidence.append({
                "path": path,
                "line": hit["line"],
                "kind": "llama_server_launch",
                "text": text,
            })
            lower = text.lower()
            if "model" in lower and (
                "str(" in lower or "path" in lower or "--model" in lower
            ):
                absolute_path_support = True

        for hit in source.get("groups", {}).get("model_source_labels", {}).get("hits", []):
            lower = hit["text"].lower()
            if "host pc" in lower and "usb" in lower:
                source_label_contract = True

        if source.get("groups", {}).get("online_provider_readiness", {}).get("count", 0):
            provider_hook = True

    return {
        "static_only": True,
        "model_server_not_started": True,
        "absolute_path_handoff_likely_supported": absolute_path_support,
        "verified_source_label_contract_detected": source_label_contract,
        "provider_or_endpoint_hook_detected": provider_hook,
        "evidence": evidence[:120],
        "limitations": [
            "Static inspection cannot prove a host GGUF starts successfully.",
            "No model process or port is started during Phase 2C1.",
            "No prompt is sent to a local, LAN, or online model.",
        ],
    }


def classify_next_scope(
    machine: str,
    host_inventory: list[dict[str, Any]],
    architecture: dict[str, Any],
    handoff: dict[str, Any],
) -> dict[str, Any]:
    approved_models = [
        model
        for inventory in host_inventory
        for model in inventory.get("models", [])
        if model.get("source") == "HOST_PC_APPROVED"
    ]
    must_add = [
        "Config/model_sources.json or equivalent backend-owned source registry",
        "Config/machine_profiles/<stable-machine-id>.json or equivalent",
        "host-folder allowlist and read-only discovery",
        "runtime receipt field for selected model source and exact model path",
        "UI badge showing USB or HOST PC from backend runtime identity",
        "explicit unavailable/fallback state with no silent switching",
    ]
    future_ready = [
        "source type LAN_OPENAI_COMPATIBLE",
        "source type ONLINE_PROVIDER",
        "endpoint health probe separated from local GGUF discovery",
        "external-send consent gate",
        "credential-manager reference field rather than API key value",
    ]
    do_not_change = [
        "existing approved USB model profiles",
        "model files on USB or host PC",
        "llama-server executable",
        "portable core runtime",
        "Desktop and ComfyUI runtimes",
        "Engineering Airlock approval rules",
    ]
    return {
        "machine": machine,
        "approved_host_model_count": len(approved_models),
        "priority_host_model_found": any(
            model["filename"].lower()
            == "qwen3-30b-a3b-q4_k_m.gguf".lower()
            for model in approved_models
        ),
        "must_add_in_phase2c2": must_add,
        "future_online_ready_contract": future_ready,
        "explicitly_preserve": do_not_change,
        "recommended_test_matrix": [
            "approved host model present and readable",
            "approved host folder missing",
            "approved host model renamed or unavailable",
            "USB model fallback explicitly selected",
            "USB moved to a machine with no host profile",
            "machine profile exists but hostname differs",
            "host absolute path contains spaces",
            "online/LAN source remains disabled unless explicitly configured",
        ],
        "current_static_handoff_assessment": handoff,
        "architecture": architecture,
    }


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    machine = receipt["machine"]
    source_scope = receipt["next_scope"]
    lines = [
        "# FOXAI Portable Host Model Library Phase 2C1 — Read-Only Audit",
        "",
        f"- Created: `{receipt['created']}`",
        f"- Root: `{receipt['root']}`",
        f"- Machine: `{machine['name']}`",
        f"- Expected primary machine: `{machine['expected_primary']}`",
        f"- Expected-machine match: **{machine['expected_match']}**",
        "- Automatic launch: **False**",
        "- Network access: **False**",
        "- Model hashing: **Deferred**",
        "- Source/config/model changes: **None**",
        "",
        "## Host model inventory",
        "",
    ]
    for inventory in receipt["host_model_inventory"]:
        lines.append(
            f"- `{inventory['root']}` — exists: **{inventory['exists']}**, "
            f"models: **{inventory.get('count', 0)}**"
        )
        for model in inventory.get("models", []):
            gib = model["size_bytes"] / (1024 ** 3)
            lines.append(
                f"  - `{model['filename']}` — {gib:.2f} GiB, "
                f"readable: **{model['readable']}**"
            )

    lines += [
        "",
        "## USB model inventory",
        "",
    ]
    for inventory in receipt["usb_model_inventory"]:
        lines.append(
            f"- `{inventory['root']}` — models: **{inventory.get('count', 0)}**"
        )

    lines += [
        "",
        "## Static model-path handoff",
        "",
        f"- Absolute host-path handoff likely supported: "
        f"**{receipt['path_handoff']['absolute_path_handoff_likely_supported']}**",
        f"- Verified USB/HOST PC source-label contract detected: "
        f"**{receipt['path_handoff']['verified_source_label_contract_detected']}**",
        f"- Provider/endpoint hook detected: "
        f"**{receipt['path_handoff']['provider_or_endpoint_hook_detected']}**",
        "",
        "## Phase 2C2 required scope",
        "",
    ]
    for item in source_scope["must_add_in_phase2c2"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Future online/LAN readiness",
        "",
    ]
    for item in source_scope["future_online_ready_contract"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Preserve",
        "",
    ]
    for item in source_scope["explicitly_preserve"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Safety",
        "",
        "The audit does not start llama-server, load a GGUF, call a provider,",
        "hash large model files, copy or move models, or modify source,",
        "configuration, launchers, credentials, or registries. Its only writes",
        "are this timestamped report and receipt.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("PHM2C1_%Y%m%dT%H%M%SZ")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    machine_name = normalized_machine_name()
    expected_machine = TARGETS["expected_primary_machine"].upper()

    receipt: dict[str, Any] = {
        "action": "foxai_portable_host_model_library_phase2c1_audit",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "read_only_audit": True,
        "automatic_launch": False,
        "network_access": False,
        "full_gguf_hashing": False,
        "source_or_config_modified": False,
        "model_modified": False,
        "delete_operations": [],
        "writes": [
            str((report_dir / "receipt.json").relative_to(ROOT)),
            str((report_dir / "report.md").relative_to(ROOT)),
        ],
        "machine": {
            "name": machine_name,
            "expected_primary": expected_machine,
            "expected_match": machine_name == expected_machine,
            "platform": platform.platform(),
            "computername_env": os.environ.get("COMPUTERNAME"),
            "python": sys.version,
            "python_executable": sys.executable,
            "foxai_root_drive": ROOT.drive,
        },
        "locked_baselines": [],
        "source_files": [],
        "usb_model_inventory": [],
        "host_model_inventory": [],
        "priority_host_models": [],
        "path_handoff": {},
        "architecture": {},
        "next_scope": {},
        "failure": None,
    }

    try:
        for relative, expected in TARGETS["locked_baselines"].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            item = {
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
            receipt["locked_baselines"].append(item)
        if not all(item["ok"] for item in receipt["locked_baselines"]):
            raise RuntimeError(
                "One or more locked model-source baselines changed."
            )

        for relative in TARGETS["source_files"]:
            path = ROOT / relative
            record = file_record(path, include_hash=True)
            record["inspection"] = keyword_hits(path)
            receipt["source_files"].append(record)

        for relative in TARGETS["usb_model_roots"]:
            receipt["usb_model_inventory"].append(
                model_inventory(ROOT / relative, "USB")
            )

        for approved in TARGETS["approved_host_roots"]:
            receipt["host_model_inventory"].append(
                model_inventory(Path(approved), "HOST_PC_APPROVED")
            )

        for priority in TARGETS["priority_host_models"]:
            path = Path(priority["directory"]) / priority["filename"]
            record = file_record(path, include_hash=False)
            record.update(priority)
            receipt["priority_host_models"].append(record)

        source_inspections = [
            item["inspection"]
            for item in receipt["source_files"]
        ]
        receipt["architecture"] = infer_architecture(source_inspections)
        receipt["path_handoff"] = static_path_handoff_assessment(
            source_inspections
        )
        receipt["next_scope"] = classify_next_scope(
            machine_name,
            receipt["host_model_inventory"],
            receipt["architecture"],
            receipt["path_handoff"],
        )

        priority_found = any(
            item.get("exists") and item.get("size_bytes", 0) > 0
            for item in receipt["priority_host_models"]
        )
        receipt["priority_host_model_available"] = priority_found
        receipt["state"] = "host_model_audit_verified"
        receipt["verified"] = True
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    receipt_path = report_dir / "receipt.json"
    report_path = report_dir / "report.md"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    write_markdown(receipt, report_path)

    print("=" * 72)
    print("FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C1")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(f"Machine: {machine_name}")
    print(
        "Priority host model available: "
        f"{receipt.get('priority_host_model_available', False)}"
    )
    print(f"Report: {report_dir}")
    print("Automatic launch: False")
    print("Network access: False")
    print("Model changes: None")
    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
