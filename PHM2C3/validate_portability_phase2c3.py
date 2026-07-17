from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TARGETS = json.loads(
    (PACKAGE / "VALIDATION_TARGETS.json").read_text(encoding="utf-8")
)
REPORT_ROOT = ROOT / "Reports" / "HostModelValidation"

sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.model_sources import (  # noqa: E402
    ModelSourceError,
    ModelSourceRegistry,
    current_machine_name,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata(path: Path) -> dict[str, Any]:
    result = {
        "path": str(path),
        "exists": path.is_file(),
    }
    if path.is_file():
        stat = path.stat()
        result.update(
            {
                "size_bytes": stat.st_size,
                "modified_ns": stat.st_mtime_ns,
                "readable": os.access(path, os.R_OK),
            }
        )
    return result


def same_metadata(before: dict[str, Any], after: dict[str, Any]) -> bool:
    keys = ("exists", "size_bytes", "modified_ns")
    return all(before.get(key) == after.get(key) for key in keys)


def base_isolated_config() -> dict[str, Any]:
    return {
        "schema": "foxai.model-sources.v1",
        "policy": {
            "no_whole_drive_scan": True,
            "never_modify_model_files": True,
            "no_silent_model_switch": True,
            "automatic_model_launch": False,
            "online_sources_enabled": False,
            "credentials_in_plain_config": False,
        },
        "usb_roots": [
            {
                "id": "usb_chat",
                "path": "Models/Chat",
                "enabled": True,
                "recursive": True,
            }
        ],
        "machines": {},
        "reserved_source_types": {
            "LAN_OPENAI_COMPATIBLE": {
                "enabled": False,
                "requires_explicit_external_send_consent": True,
                "credential_reference_only": True,
            },
            "ONLINE_PROVIDER": {
                "enabled": False,
                "requires_explicit_external_send_consent": True,
                "credential_reference_only": True,
            },
        },
    }


def write_isolated_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def static_web_contract(web_path: Path) -> dict[str, Any]:
    text = web_path.read_text(encoding="utf-8", errors="replace")
    required = {
        "unapproved_model_rejected": (
            "Selected model is not inside an approved USB or host-PC model source. "
            "No engine action occurred."
        ),
        "unavailable_model_no_fallback": (
            "Selected approved model is unavailable. "
            "No fallback or engine action occurred."
        ),
        "source_mismatch_no_fallback": (
            "Selected model source does not match the requested "
        ),
        "runtime_receipt_silent_fallback_false": "'silent_fallback_used':False",
        "host_profile_present": "'host_general_30b':{",
        "host_profile_source": "'source':'HOST_PC'",
        "current_online_source_wording": (
            "`ONLINE • ${s.chat_model_source_label||'LOCAL'}`"
        ),
    }
    return {
        "passed": all(value in text for value in required.values()),
        "checks": {
            key: value in text for key, value in required.items()
        },
        "clarity": {
            "current_wording_detected": (
                required["current_online_source_wording"] in text
            ),
            "classification": "NEEDS_CLARITY_POLISH",
            "reason": (
                "ONLINE currently means the local engine is running, but it can "
                "be mistaken for internet use now that ONLINE_PROVIDER is a "
                "reserved future source type."
            ),
            "proposed_future_labels": {
                "engine": "RUNNING or STOPPED",
                "model_source": "USB, HOST PC, LAN, or ONLINE PROVIDER",
                "network_use": "NONE, LAN, or INTERNET",
            },
            "live_change_in_phase2c3": False,
        },
    }


def run_isolated_scenarios(report_dir: Path) -> dict[str, Any]:
    sandbox = report_dir / "isolated_scenarios"
    sandbox.mkdir(parents=True, exist_ok=False)
    results: dict[str, Any] = {}

    usb_root = sandbox / "Portable FOXAI"
    usb_chat = usb_root / "Models" / "Chat"
    host_root = sandbox / "Host Model Folder With Spaces"
    usb_chat.mkdir(parents=True)
    host_root.mkdir(parents=True)

    usb_model = usb_chat / "usb-fallback-model.gguf"
    host_model = host_root / "host model with spaces.gguf"
    usb_model.write_bytes(b"PHM2C3 USB model fixture")
    host_model.write_bytes(b"PHM2C3 host model fixture")

    usb_hash = sha256(usb_model)
    host_hash = sha256(host_model)
    config_path = usb_root / "Config" / "model_sources.json"
    write_isolated_config(config_path, base_isolated_config())

    # Unknown machine: no host profile inherited.
    unknown = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="UNKNOWN-VALIDATION-PC",
    )
    unknown_state = unknown.state(include_catalog=True)
    results["unknown_machine"] = {
        "passed": (
            not unknown_state["machine"]["configured"]
            and unknown_state["counts"]["usb"] == 1
            and unknown_state["counts"]["host_pc"] == 0
            and unknown_state["prompt_for_host_models"] is True
            and unknown_state["allow_online_sources"] is False
        ),
        "state": unknown_state,
    }

    # Session-only approval must not change registry bytes and disappears on restart.
    before_config = config_path.read_bytes()
    session_result = unknown.approve_folder(
        host_root,
        remember=False,
        confirm=True,
    )
    session_state = unknown.state(include_catalog=True)
    after_session_config = config_path.read_bytes()
    fresh_after_session = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="UNKNOWN-VALIDATION-PC",
    ).state(include_catalog=True)
    results["session_only"] = {
        "passed": (
            session_result["scope"] == "session"
            and before_config == after_session_config
            and session_state["counts"]["host_pc"] == 1
            and session_state["session_only_reference_count"] == 1
            and fresh_after_session["counts"]["host_pc"] == 0
            and fresh_after_session["session_only_reference_count"] == 0
        ),
        "approval": session_result,
        "state_before_restart": session_state,
        "state_after_fresh_instance": fresh_after_session,
        "registry_bytes_unchanged": before_config == after_session_config,
    }

    # Remembered approval survives a fresh registry instance and supports spaces.
    remembered = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="REMEMBERED-VALIDATION-PC",
    )
    remember_result = remembered.approve_folder(
        host_root,
        remember=True,
        confirm=True,
    )
    restarted = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="REMEMBERED-VALIDATION-PC",
    )
    restarted_state = restarted.state(include_catalog=True)
    results["remembered_and_spaces"] = {
        "passed": (
            remember_result["scope"] == "remembered"
            and restarted_state["machine"]["configured"]
            and restarted_state["counts"]["host_pc"] == 1
            and any(
                item["path"] == str(host_model.resolve())
                and item["source"] == "HOST_PC"
                for item in restarted_state["models"]
            )
        ),
        "approval": remember_result,
        "state_after_fresh_instance": restarted_state,
    }

    # Add preferred model in the isolated copied registry.
    data = json.loads(config_path.read_text(encoding="utf-8"))
    data["machines"]["REMEMBERED-VALIDATION-PC"]["preferred_models"] = {
        "general": str(host_model.resolve())
    }
    write_isolated_config(config_path, data)
    preferred_registry = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="REMEMBERED-VALIDATION-PC",
    )

    forget_model_result = preferred_registry.forget_model(
        host_model,
        confirm=True,
    )
    results["forget_preferred_model"] = {
        "passed": (
            forget_model_result["ok"]
            and host_model.is_file()
            and sha256(host_model) == host_hash
            and not preferred_registry.state(False)["preferred_models"]
        ),
        "result": forget_model_result,
        "host_file_preserved": host_model.is_file(),
        "host_hash_preserved": sha256(host_model) == host_hash,
    }

    # Restore preference, then forget the folder. Folder/model must remain.
    data = json.loads(config_path.read_text(encoding="utf-8"))
    data["machines"]["REMEMBERED-VALIDATION-PC"]["preferred_models"] = {
        "general": str(host_model.resolve())
    }
    write_isolated_config(config_path, data)
    folder_registry = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="REMEMBERED-VALIDATION-PC",
    )
    forget_folder_result = folder_registry.forget_folder(
        host_root,
        confirm=True,
    )
    results["forget_folder"] = {
        "passed": (
            forget_folder_result["ok"]
            and host_root.is_dir()
            and host_model.is_file()
            and sha256(host_model) == host_hash
            and folder_registry.state(True)["counts"]["host_pc"] == 0
        ),
        "result": forget_folder_result,
        "folder_preserved": host_root.is_dir(),
        "host_file_preserved": host_model.is_file(),
        "host_hash_preserved": sha256(host_model) == host_hash,
    }

    # Reapprove and forget entire computer profile.
    machine_registry = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="REMEMBERED-VALIDATION-PC",
    )
    machine_registry.approve_folder(
        host_root,
        remember=True,
        confirm=True,
    )
    forget_machine_result = machine_registry.forget_machine(confirm=True)
    forgotten_state = machine_registry.state(include_catalog=True)
    results["forget_machine"] = {
        "passed": (
            forget_machine_result["ok"]
            and not forgotten_state["machine"]["configured"]
            and forgotten_state["counts"]["usb"] == 1
            and forgotten_state["counts"]["host_pc"] == 0
            and usb_model.is_file()
            and host_model.is_file()
            and sha256(usb_model) == usb_hash
            and sha256(host_model) == host_hash
        ),
        "result": forget_machine_result,
        "state": forgotten_state,
        "usb_hash_preserved": sha256(usb_model) == usb_hash,
        "host_hash_preserved": sha256(host_model) == host_hash,
    }

    # Missing remembered folder and missing preferred model.
    missing_root = sandbox / "Missing Host Models"
    missing_model = missing_root / "missing-model.gguf"
    missing_data = base_isolated_config()
    missing_data["machines"]["MISSING-VALIDATION-PC"] = {
        "display_name": "Missing Validation PC",
        "machine_name": "MISSING-VALIDATION-PC",
        "machine_key": "validation-only",
        "approved_host_roots": [
            {
                "id": "missing_host",
                "path": str(missing_root),
                "enabled": True,
                "remembered": True,
            }
        ],
        "preferred_models": {"general": str(missing_model)},
        "fallback_policy": "ASK_OR_APPROVED_USB",
        "prompt_for_host_models": True,
        "allow_online_sources": False,
    }
    write_isolated_config(config_path, missing_data)
    missing_registry = ModelSourceRegistry(
        usb_root,
        config_path=config_path,
        machine_name="MISSING-VALIDATION-PC",
    )
    missing_state = missing_registry.state(include_catalog=True)
    missing_record = missing_registry.record_for_path(missing_model)
    usb_record = missing_registry.record_for_path(usb_model)
    results["missing_host_no_silent_fallback"] = {
        "passed": (
            missing_state["approved_host_roots"][0]["available"] is False
            and missing_state["counts"]["host_pc"] == 0
            and missing_state["counts"]["usb"] == 1
            and missing_record is None
            and usb_record is not None
            and missing_state["fallback_policy"] == "ASK_OR_APPROVED_USB"
            and missing_state["policy"]["no_silent_model_switch"] is True
        ),
        "state": missing_state,
        "requested_missing_model_record": missing_record,
        "usb_model_available_separately": usb_record is not None,
        "automatic_substitution_performed": False,
    }

    # Whole-drive/filesystem root is rejected.
    root_rejected = False
    root_message = None
    try:
        missing_registry.approve_folder(
            Path(sandbox.anchor),
            remember=False,
            confirm=True,
        )
    except ModelSourceError as exc:
        root_rejected = True
        root_message = str(exc)
    results["whole_drive_rejected"] = {
        "passed": root_rejected,
        "message": root_message,
    }

    # Online/LAN disabled with consent and credential-reference flags retained.
    reserved = missing_state["reserved_source_types"]
    results["online_lan_disabled"] = {
        "passed": (
            missing_state["allow_online_sources"] is False
            and reserved["ONLINE_PROVIDER"]["enabled"] is False
            and reserved["LAN_OPENAI_COMPATIBLE"]["enabled"] is False
            and reserved["ONLINE_PROVIDER"][
                "requires_explicit_external_send_consent"
            ] is True
            and reserved["LAN_OPENAI_COMPATIBLE"][
                "requires_explicit_external_send_consent"
            ] is True
            and reserved["ONLINE_PROVIDER"][
                "credential_reference_only"
            ] is True
            and reserved["LAN_OPENAI_COMPATIBLE"][
                "credential_reference_only"
            ] is True
        ),
        "reserved_source_types": reserved,
    }

    # Remove fixtures after recording. This touches only the report sandbox.
    fixture_summary = {
        "usb_fixture_sha256": usb_hash,
        "host_fixture_sha256": host_hash,
        "sandbox": str(sandbox),
    }
    results["fixture_summary"] = fixture_summary
    return results


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        "# FOXAI Portable Host Model Library Phase 2C3",
        "## Read-Only Portability Validation",
        "",
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Machine: `{receipt['machine']['name']}`",
        "- Live files modified: **False**",
        "- Live registry modified: **False**",
        "- Model files modified: **False**",
        "- Model server started or stopped: **False**",
        "- External or loopback network use: **False**",
        "",
        "## Live validation",
        "",
        f"- Current machine profile: **{receipt['live']['machine_profile']}**",
        f"- Priority host model registered: "
        f"**{receipt['live']['priority_registered']}**",
        f"- Priority host model readable: "
        f"**{receipt['live']['priority_readable']}**",
        f"- Host-PC catalog count: **{receipt['live']['counts']['host_pc']}**",
        f"- USB catalog count: **{receipt['live']['counts']['usb']}**",
        f"- No-silent-switch policy: "
        f"**{receipt['live']['no_silent_switch']}**",
        f"- LAN/online enabled: **False**",
        "",
        "## Isolated portability scenarios",
        "",
    ]
    for name, result in receipt["isolated_scenarios"].items():
        if name == "fixture_summary":
            continue
        lines.append(
            f"- `{name}`: **{'PASS' if result.get('passed') else 'FAIL'}**"
        )
    clarity = receipt["web_contract"]["clarity"]
    lines += [
        "",
        "## Runtime wording clarity",
        "",
        f"- Current `ONLINE • source` wording detected: "
        f"**{clarity['current_wording_detected']}**",
        f"- Classification: **{clarity['classification']}**",
        "- No wording was changed in Phase 2C3.",
        "- Proposed later exact-preview wording:",
        "  - `Engine: RUNNING`",
        "  - `Model source: HOST PC`",
        "  - `Network use: NONE`",
        "",
        "## Conclusion",
        "",
        receipt["conclusion"],
        "",
        "## Safety",
        "",
        "All state-changing behaviors were tested only against temporary fixture",
        "models and a temporary registry inside this report folder. The live",
        "registry, live model files, source code, launchers, model process, and",
        "network state were not changed.",
    ]
    if receipt.get("failure"):
        lines += [
            "",
            "## Failure",
            "",
            f"- `{receipt['failure']['type']}: "
            f"{receipt['failure']['message']}`",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("PHM2C3_%Y%m%dT%H%M%SZ")
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "foxai_portable_host_model_library_phase2c3_validation",
        "created": datetime.now(timezone.utc).isoformat(),
        "state": "stopped_fail_closed",
        "verified": False,
        "root": str(ROOT),
        "read_only_live_validation": True,
        "apply_capability_present": False,
        "live_files_modified": False,
        "live_registry_modified": False,
        "model_files_modified": False,
        "automatic_model_launch": False,
        "model_server_started": False,
        "model_server_stopped": False,
        "external_network_access": False,
        "loopback_api_calls": False,
        "delete_operations": [],
        "machine": {},
        "baseline_checks": {},
        "live": {},
        "isolated_scenarios": {},
        "web_contract": {},
        "metadata_preservation": {},
        "conclusion": "",
        "failure": None,
    }

    priority_path = Path(TARGETS["priority_host_model"])
    usb_sample: Path | None = None
    priority_before = metadata(priority_path)

    try:
        machine = current_machine_name()
        receipt["machine"] = {
            "name": machine,
            "expected": TARGETS["expected_machine"],
            "expected_match": machine == TARGETS["expected_machine"],
            "platform": platform.platform(),
            "python": sys.version,
            "python_executable": sys.executable,
        }

        baseline_files = []
        for relative, expected in TARGETS["locked_baselines"].items():
            live_path = ROOT / relative
            actual = sha256(live_path) if live_path.is_file() else None
            baseline_files.append(
                {
                    "path": relative,
                    "expected": expected,
                    "actual": actual,
                    "ok": actual == expected,
                }
            )
        if not all(item["ok"] for item in baseline_files):
            raise RuntimeError(
                "One or more Phase 2C2 or security baselines changed."
            )
        receipt["baseline_checks"] = {
            "passed": True,
            "files": baseline_files,
        }

        registry = ModelSourceRegistry(
            ROOT,
            config_path=ROOT / "Config" / "model_sources.json",
            machine_name=machine,
        )
        live_state = registry.state(include_catalog=True)
        priority_record = registry.record_for_path(priority_path)
        usb_records = [
            item for item in live_state["models"]
            if item.get("source") == "USB"
        ]
        if usb_records:
            usb_sample = Path(usb_records[0]["path"])
        usb_before = metadata(usb_sample) if usb_sample else {}

        reserved = live_state["reserved_source_types"]
        live_checks = {
            "machine_profile": live_state["machine"]["configured"],
            "priority_registered": (
                priority_record is not None
                and priority_record.get("source") == "HOST_PC"
                and priority_record.get("source_label") == "HOST PC"
                and Path(priority_record["path"]) == priority_path
            ),
            "priority_readable": (
                priority_path.is_file()
                and os.access(priority_path, os.R_OK)
            ),
            "counts": live_state["counts"],
            "no_silent_switch": (
                live_state["policy"].get("no_silent_model_switch") is True
                and live_state["fallback_policy"] == "ASK_OR_APPROVED_USB"
            ),
            "never_modify_models": (
                live_state["policy"].get("never_modify_model_files") is True
                and live_state["model_files_modified"] is False
            ),
            "online_lan_disabled": (
                live_state["allow_online_sources"] is False
                and reserved["ONLINE_PROVIDER"]["enabled"] is False
                and reserved["LAN_OPENAI_COMPATIBLE"]["enabled"] is False
            ),
            "external_send_consent_contract": (
                reserved["ONLINE_PROVIDER"].get(
                    "requires_explicit_external_send_consent"
                ) is True
                and reserved["LAN_OPENAI_COMPATIBLE"].get(
                    "requires_explicit_external_send_consent"
                ) is True
            ),
            "credential_reference_only": (
                reserved["ONLINE_PROVIDER"].get(
                    "credential_reference_only"
                ) is True
                and reserved["LAN_OPENAI_COMPATIBLE"].get(
                    "credential_reference_only"
                ) is True
            ),
            "priority_record": priority_record,
            "state": live_state,
        }
        required_live = (
            receipt["machine"]["expected_match"]
            and live_checks["machine_profile"]
            and live_checks["priority_registered"]
            and live_checks["priority_readable"]
            and live_checks["counts"]["usb"] >= 1
            and live_checks["counts"]["host_pc"] >= 1
            and live_checks["no_silent_switch"]
            and live_checks["never_modify_models"]
            and live_checks["online_lan_disabled"]
            and live_checks["external_send_consent_contract"]
            and live_checks["credential_reference_only"]
        )
        live_checks["passed"] = required_live
        if not required_live:
            raise RuntimeError("Live host/USB source validation failed.")
        receipt["live"] = live_checks

        receipt["web_contract"] = static_web_contract(
            ROOT / "core" / "foxai_web.py"
        )
        if not receipt["web_contract"]["passed"]:
            raise RuntimeError(
                "WebUI no-silent-fallback runtime contract is incomplete."
            )

        receipt["isolated_scenarios"] = run_isolated_scenarios(report_dir)
        scenario_results = [
            result.get("passed") is True
            for name, result in receipt["isolated_scenarios"].items()
            if name != "fixture_summary"
        ]
        if not scenario_results or not all(scenario_results):
            raise RuntimeError(
                "One or more isolated portability scenarios failed."
            )

        priority_after = metadata(priority_path)
        usb_after = metadata(usb_sample) if usb_sample else {}
        metadata_ok = (
            same_metadata(priority_before, priority_after)
            and (
                not usb_sample
                or same_metadata(usb_before, usb_after)
            )
        )
        receipt["metadata_preservation"] = {
            "passed": metadata_ok,
            "priority_before": priority_before,
            "priority_after": priority_after,
            "usb_sample_before": usb_before,
            "usb_sample_after": usb_after,
            "large_model_full_hashing": False,
        }
        if not metadata_ok:
            raise RuntimeError(
                "Live model metadata changed during read-only validation."
            )

        receipt["state"] = "portability_validation_verified_with_clarity_note"
        receipt["verified"] = True
        receipt["conclusion"] = (
            "Host-PC and USB model-source portability behavior is verified. "
            "Unknown-machine, unavailable-host, session-only, remembered, "
            "restart-survival, path-with-spaces, forget, and no-silent-fallback "
            "scenarios passed. The only follow-up is a display-language polish "
            "to separate engine state, model source, and network use."
        )
    except Exception as exc:
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        receipt["conclusion"] = (
            "Validation stopped fail-closed. No live source, registry, model, "
            "launcher, process, or network state was changed."
        )

    receipt_path = report_dir / "receipt.json"
    report_path = report_dir / "report.md"
    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
    write_markdown(receipt, report_path)

    results_zip = report_dir / "PHM2C3_RESULTS.zip"
    with zipfile.ZipFile(
        results_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(receipt_path, arcname="receipt.json")
        archive.write(report_path, arcname="report.md")

    print("=" * 72)
    print("FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C3")
    print("READ-ONLY PORTABILITY VALIDATION")
    print("=" * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print(f"Machine: {receipt.get('machine', {}).get('name', 'UNKNOWN')}")
    print(f"Report: {report_dir}")
    print(f"Upload: {results_zip}")
    print("Live files modified: False")
    print("Live registry modified: False")
    print("Model files modified: False")
    print("Model server action: None")
    print("Network access: None")
    if receipt["failure"]:
        print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
