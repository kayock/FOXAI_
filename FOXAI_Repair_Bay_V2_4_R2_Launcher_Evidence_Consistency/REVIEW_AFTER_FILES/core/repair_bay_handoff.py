from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "foxai.repair_bay.guarded_handoff.v2_3"
MAX_EVIDENCE_ITEMS = 12
MAX_AFFECTED_PATHS = 24

SUPPORTED_FINDINGS: dict[str, dict[str, Any]] = {
    "known_good_launchers": {
        "repair_kind": "restore_known_good_launcher",
        "label": "Restore one missing or empty known-good launcher",
        "backup_required": True,
        "path_required": True,
    },
    "essential_components": {
        "repair_kind": "restore_known_good_component",
        "label": "Restore one clearly identified missing FOXAI component",
        "backup_required": True,
        "path_required": True,
    },
    "key_source_syntax": {
        "repair_kind": "correct_python_exact_diff",
        "label": "Correct one damaged key Python file through an exact diff",
        "backup_required": True,
        "path_required": True,
    },
    "full_python_syntax": {
        "repair_kind": "correct_python_exact_diff",
        "label": "Correct damaged Python through exact per-file diffs",
        "backup_required": True,
        "path_required": True,
    },
    "configuration_json": {
        "repair_kind": "correct_json_exact_diff",
        "label": "Correct one invalid JSON configuration through an exact diff",
        "backup_required": True,
        "path_required": True,
    },
    "zero_byte_live_files": {
        "repair_kind": "restore_empty_known_good_file",
        "label": "Restore one suspicious empty live file from verified evidence",
        "backup_required": True,
        "path_required": True,
    },
    "log_growth": {
        "repair_kind": "prepare_reversible_log_archive_plan",
        "label": "Prepare a reversible log archive plan",
        "backup_required": True,
        "path_required": False,
    },
    "root_launcher_inventory": {
        "repair_kind": "review_launcher_duplicate_evidence",
        "label": "Review launcher duplicate evidence and prepare a reversible proposal",
        "backup_required": True,
        "path_required": False,
    },
}

PROTECTED_PARTS = {
    ".ssh", ".gnupg", ".aws", ".azure", ".kube",
    "credentials", "credential", "secrets", "secret", "vault", "keys", "key",
}
PATH_EXTENSIONS = (
    "bat", "cmd", "ps1", "py", "json", "yaml", "yml", "toml", "ini", "cfg",
    "conf", "txt", "md", "log", "sqlite", "sqlite3", "db", "exe", "dll", "zip",
)
PATH_RE = re.compile(
    r"(?i)(?:(?:[A-Z]:[\\/])|(?:[A-Za-z0-9_.() -]+[\\/])+)[^<>\"|\r\n:*?]+\."
    r"(?:" + "|".join(PATH_EXTENSIONS) + r")"
)
BARE_PATH_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_.-])([A-Za-z0-9_.() -]+\.(?:"
    + "|".join(PATH_EXTENSIONS)
    + r"))(?![A-Za-z0-9_.-])"
)


def _clean(value: Any, limit: int = 1600) -> str:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    return text[:limit]


def _safe_title(value: Any) -> str:
    text = _clean(value, 100)
    text = re.sub(r"[^A-Za-z0-9 _().,'’&+\-—]", "", text).strip(" .-")
    return text or "Repair Bay finding"


def _inside_root(root: Path, candidate: Path) -> bool:
    try:
        resolved_root = root.resolve()
        resolved = candidate.resolve(strict=False)
        return resolved == resolved_root or resolved_root in resolved.parents
    except Exception:
        return False


def _protected(relative: str) -> bool:
    parts = {part.casefold() for part in re.split(r"[\\/]", relative) if part}
    return bool(parts.intersection(PROTECTED_PARTS))


def _normalize_candidate(root: Path, raw: str) -> str | None:
    value = raw.strip().strip("'\"`()[]{}<>,;")
    value = re.sub(r"\s+\((?:missing|empty|invalid|damaged)\)$", "", value, flags=re.I)
    if not value:
        return None
    try:
        path = Path(value)
        if not path.is_absolute():
            path = root / value.replace("\\", "/")
        if not _inside_root(root, path):
            return None
        relative = str(path.resolve(strict=False).relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return None
    if not relative or relative == "." or _protected(relative):
        return None
    return relative


def _paths_from_text(root: Path, values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    root_text = str(root)
    for value in values:
        text = str(value or "")
        candidates = [match.group(0) for match in PATH_RE.finditer(text)]
        candidates.extend(match.group(1) for match in BARE_PATH_RE.finditer(text))
        # Evidence sometimes contains a plain root-relative path with no extension.
        if root_text and root_text in text:
            tail = text[text.index(root_text):].split(" | ", 1)[0]
            candidates.append(tail)
        for candidate in candidates:
            normalized = _normalize_candidate(root, candidate)
            if normalized and normalized.casefold() not in seen:
                seen.add(normalized.casefold())
                result.append(normalized)
                if len(result) >= MAX_AFFECTED_PATHS:
                    return result
    return result


def _finding_paths(root: Path, report: dict[str, Any], finding: dict[str, Any]) -> list[str]:
    finding_id = str(finding.get("id") or "")
    evidence = list(finding.get("evidence") or [])
    paths = _paths_from_text(root, evidence)

    report_evidence = report.get("evidence") or {}
    if finding_id == "root_launcher_inventory":
        inventory = report_evidence.get("launcher_inventory") or {}
        protected_names = {
            str(item.get("name") or "").casefold()
            for item in ((inventory.get("protected_baseline") or {}).get("root") or [])
        }
        paths = []
        for item in inventory.get("obsolete_looking_candidates") or []:
            name = str(item.get("name") or "").strip()
            basis = set(item.get("candidate_basis") or [])
            if (
                not name
                or name.casefold() in protected_names
                or "exact_duplicate_content" not in basis
            ):
                continue
            normalized = _normalize_candidate(root, name)
            if normalized and normalized not in paths:
                paths.append(normalized)
                if len(paths) >= MAX_AFFECTED_PATHS:
                    break

    if finding_id == "log_growth" and not paths:
        logs = root / "Logs"
        if logs.exists():
            paths.append("Logs")

    return paths[:MAX_AFFECTED_PATHS]


def _support_decision(finding: dict[str, Any], paths: list[str]) -> tuple[bool, str, dict[str, Any] | None]:
    finding_id = str(finding.get("id") or "")
    severity = str(finding.get("severity") or "informational").casefold()
    profile = SUPPORTED_FINDINGS.get(finding_id)
    if severity not in {"urgent", "recommended"}:
        return False, "Only urgent or recommended findings can request an exact repair plan.", profile
    if profile is None:
        return False, "This finding is advisory or too broad for the initial guarded repair set.", None
    if profile.get("path_required") and not paths:
        return False, "The finding does not identify a bounded FOXAI path clearly enough for an exact plan.", profile
    return True, "This finding fits the initial bounded low-risk planning set.", profile


_ROUTE_SEARCH = re.compile(r"\b(find|locate|search|where is|show references?|grep)\b", re.I)
_ROUTE_DIAGNOSE = re.compile(r"\b(inspect|diagnose|analy[sz]e|why|determine|review)\b", re.I)
_ROUTE_PLAN = re.compile(r"\b(plan|preview|propose|what would change|do not modify|read[- ]only)\b", re.I)
_ROUTE_IMPLEMENT = re.compile(r"\b(build|implement|create|add|integrate|patch|update|deploy|install feature)\b", re.I)
_ROUTE_REPAIR = re.compile(r"\b(fix|repair|apply|proceed with the approved|execute the approved)\b", re.I)
_ROUTE_AUTH = re.compile(
    r"\b(authoriz(?:e|ed|ation)|approved|proceed|apply|implement|targeted source changes|do not stop at planning)\b",
    re.I,
)

_ROUTER_SAFE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bauthoriz(?:e|ed|ation)\b", re.I), "permission"),
    (re.compile(r"\bapproved\b", re.I), "verified"),
    (re.compile(r"\bproceed\b", re.I), "continue later"),
    (re.compile(r"\bapply\b", re.I), "carry out"),
    (re.compile(r"\bimplement(?:ation|ed|ing)?\b", re.I), "put into place"),
    (re.compile(r"\bbuild\b", re.I), "assemble"),
    (re.compile(r"\bcreate\b", re.I), "produce"),
    (re.compile(r"\badd\b", re.I), "include"),
    (re.compile(r"\bintegrate\b", re.I), "connect"),
    (re.compile(r"\bpatch\b", re.I), "correction package"),
    (re.compile(r"\bupdate\b", re.I), "refresh"),
    (re.compile(r"\bdeploy\b", re.I), "release"),
    (re.compile(r"\binstall feature\b", re.I), "enable capability"),
    (re.compile(r"\bfix\b", re.I), "correction"),
    (re.compile(r"\brepair\b", re.I), "remediation"),
    (re.compile(r"\btargeted source changes\b", re.I), "bounded file edits"),
    (re.compile(r"\bdo not stop at planning\b", re.I), "planning ends here"),
)


def predict_engineer_route(text: str) -> dict[str, Any]:
    normalized = str(text or "").strip()
    scores = {
        "search": 35 if _ROUTE_SEARCH.search(normalized) else 0,
        "diagnose": 30 if _ROUTE_DIAGNOSE.search(normalized) else 0,
        "plan": 45 if _ROUTE_PLAN.search(normalized) else 0,
        "implement": 60 if _ROUTE_IMPLEMENT.search(normalized) else 0,
        "repair": 55 if _ROUTE_REPAIR.search(normalized) else 0,
    }
    authorized = bool(_ROUTE_AUTH.search(normalized))
    if authorized and scores["implement"]:
        scores["implement"] += 25
    if authorized and scores["repair"]:
        scores["repair"] += 20
    if not any(scores.values()):
        return {
            "route": "unknown",
            "implementation_authorized": authorized,
            "scores": scores,
            "safe_for_repair_bay_send": False,
        }
    route = max(("search", "diagnose", "plan", "implement", "repair"), key=lambda key: scores[key])
    return {
        "route": route,
        "implementation_authorized": authorized,
        "scores": scores,
        "safe_for_repair_bay_send": route == "plan" and not authorized,
    }


def _router_safe(value: Any, limit: int) -> str:
    text = _clean(value, limit)
    for pattern, replacement in _ROUTER_SAFE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def _command_text(packet: dict[str, Any]) -> str:
    finding = packet["finding"]
    paths = packet.get("affected_paths") or []
    evidence = packet.get("technical_evidence") or []
    title = _router_safe(_safe_title(finding.get("title")), 120)
    finding_id = _router_safe(finding.get("id"), 80)
    severity = _router_safe(finding.get("severity"), 30)
    explanation = _router_safe(packet.get("plain_english_explanation"), 650)
    proposed = _router_safe(packet.get("proposed_action"), 650)
    path_text = _router_safe(
        ", ".join(paths) if paths else "No path is bounded yet; keep all paths advisory.",
        1200,
    )
    evidence_text = _router_safe(
        " | ".join(evidence[:6]) or "No additional evidence supplied.",
        1400,
    )
    review_kind = "Planning Review" if packet.get("eligible") else "Advisory Planning Review"
    return (
        f"/engineer workshop begin System Health {review_kind} — {title} :: "
        "Read-only plan request. Inspect this finding and produce a proposed exact JSON plan draft for human review. "
        "No file changes are permitted in this request. No file writes, moves, renames, deletions, package actions, "
        "restarts, command execution, or network access. "
        f"Finding ID: {finding_id}. Severity: {severity}. "
        f"Plain explanation: {explanation}. "
        f"Proposed next step: {proposed}. "
        f"Affected FOXAI paths: {path_text}. "
        f"Technical evidence: {evidence_text}. "
        "The draft should list exact before hashes, a targeted snapshot approach, validation, rollback protection, "
        "and a final receipt. A later separate operator decision is required before any file change. "
        "Uncertain paths must remain advisory."
    )

def build_repair_handoff(
    root: str | Path,
    report: dict[str, Any],
    finding_id: str | None = None,
    *,
    level: str = "guided",
) -> dict[str, Any]:
    root_path = Path(root)
    findings = list(report.get("findings") or [])
    selected = None
    requested = str(finding_id or "").strip()
    if requested:
        selected = next((item for item in findings if str(item.get("id") or "") == requested), None)
        if selected is None:
            return {
                "ok": False,
                "schema": SCHEMA,
                "message": "The selected Repair Bay finding could not be resolved from the latest read-only scan.",
                "requested_finding_id": _clean(requested, 100),
                "read_only": True,
                "changes_applied": 0,
                "mission_staged": False,
                "implementation_authorized": False,
            }
    else:
        selected = next(
            (item for item in findings if str(item.get("severity") or "") == "urgent"),
            None,
        ) or next(
            (item for item in findings if str(item.get("severity") or "") == "recommended"),
            None,
        )
    if selected is None:
        return {
            "ok": False,
            "schema": SCHEMA,
            "message": "No urgent or recommended Repair Bay finding is available for handoff.",
            "read_only": True,
            "changes_applied": 0,
            "mission_staged": False,
            "implementation_authorized": False,
        }

    evidence = [_clean(item, 900) for item in list(selected.get("evidence") or [])[:MAX_EVIDENCE_ITEMS]]
    paths = _finding_paths(root_path, report, selected)
    eligible, reason, profile = _support_decision(selected, paths)
    finding = {
        "id": _clean(selected.get("id"), 100),
        "title": _safe_title(selected.get("title") or selected.get("id")),
        "severity": _clean(selected.get("severity"), 30).casefold(),
    }
    plain = _clean(selected.get("summary") or "Repair Bay found an item that deserves review.", 1200)
    proposed = _clean(selected.get("suggested_action") or "Review the evidence before any change.", 1200)
    packet: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA,
        "version": "2.3",
        "level": "advanced" if str(level).casefold() == "advanced" else "guided",
        "read_only": True,
        "eligible": eligible,
        "status": "ready_for_engineer_review" if eligible else "advisory_only",
        "eligibility_reason": reason,
        "finding": finding,
        "plain_english_explanation": plain,
        "technical_evidence": evidence,
        "affected_paths": paths,
        "proposed_action": proposed,
        "repair_kind": profile.get("repair_kind") if profile else None,
        "repair_label": profile.get("label") if profile else "Advisory review only",
        "backup_required": bool(profile and profile.get("backup_required")),
        "safety_limits": {
            "repair_bay_may_modify": False,
            "mission_staged": False,
            "exact_plan_created": False,
            "network_allowed": False,
            "commands_allowed": False,
            "restart_allowed": False,
            "install_allowed": False,
            "delete_allowed": False,
            "move_allowed": False,
            "rename_allowed": False,
            "automatic_apply_allowed": False,
        },
        "exact_plan_requirements": [
            "Resolve every affected path from verified evidence.",
            "Show exact before hashes and the complete proposed diff or move list.",
            "Create a targeted snapshot before any later implementation.",
            "Require a separate exact APPLY hash and explicit operator approval.",
            "Validate the result and roll back automatically on failure.",
            "Preserve a final receipt with before-and-after evidence.",
        ],
        "changes_applied": 0,
        "mission_staged": False,
        "operator_next_step": (
            "Review the handoff in Mission Console and press Send to stage a planning mission."
            if eligible
            else "Review the advisory explanation in Mission Console; no exact repair plan is authorized."
        ),
    }
    packet["engineer_command"] = _command_text(packet)
    packet["implementation_authorized"] = False
    packet["expected_workshop_route"] = "plan"
    packet["expected_implementation_authorized"] = False
    packet["route_guard"] = predict_engineer_route(packet["engineer_command"])
    if not packet["route_guard"].get("safe_for_repair_bay_send"):
        return {
            "ok": False,
            "schema": SCHEMA,
            "message": (
                "The generated Engineer request did not satisfy the Repair Bay planning-only route guard. "
                "Nothing was staged or changed."
            ),
            "finding": finding,
            "read_only": True,
            "changes_applied": 0,
            "mission_staged": False,
            "implementation_authorized": False,
            "route_guard": packet["route_guard"],
        }
    packet["handoff_id"] = hashlib.sha256(
        json.dumps(
            {
                "finding": finding,
                "paths": paths,
                "repair_kind": packet.get("repair_kind"),
                "command": packet["engineer_command"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:20]
    return packet
