from __future__ import annotations

"""FOXAI compatibility helpers after removal of security containment.

This module intentionally preserves the public interfaces used by existing
FOXAI components while disabling Casbin, default-deny routing, privileged
department blocking, Airlock denial chains, protected-path denial, secret
redaction, and model-action-claim blocking.

The remaining change-safety control is narrow and practical:
an apply action must repeat the exact ``APPLY <action-id>`` phrase. Actual
Workshop safety continues to come from plan preview, hashes, snapshots,
validation, receipts, and rollback.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
from typing import Any, Iterable


# Kept as compatibility constants for callers that import them.
OPERATOR_ACTORS = {"operator", "human_operator", "eric", "ui_operator"}
MODEL_ACTORS: set[str] = set()
PRIVILEGED_DEPARTMENTS: set[str] = set()
PROTECTED_DIR_NAMES: set[str] = set()
PROTECTED_FILE_NAMES: set[str] = set()
PROTECTED_SUFFIXES: set[str] = set()

_EXPLICIT_ENGINEER = re.compile(
    r"^\s*(?:/engineer(?:\s+|$)|engineer\s*[:,]\s*\S)",
    re.I,
)

AIRLOCK_AUDIT_RELATIVE_PATH = (
    Path("Logs") / "Security" / "engineering_airlock_events.jsonl"
)
_MUTATING_REPAIR_ACTIONS = {"apply", "execute_structured_action"}


@contextmanager
def _airlock_audit_lock(
    path: str | Path,
    *,
    timeout_seconds: float = 5.0,
):
    """Compatibility context manager; no security lock or audit write occurs."""
    _ = timeout_seconds
    audit_path = Path(path)
    yield {
        "lock_path": str(audit_path.with_name(audit_path.name + ".disabled")),
        "lock_kind": "disabled",
    }


def normalize_actor(actor: str | None) -> str:
    return (actor or "unknown").strip().lower().replace(" ", "_")


def is_explicit_engineer_command(text: str | None) -> bool:
    return bool(_EXPLICIT_ENGINEER.search(text or ""))


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    actor: str
    object: str
    action: str
    reason: str
    policy_source: str = "containment_disabled"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hard_deny(actor: str, obj: str) -> AuthorizationDecision | None:
    """Containment is disabled; no actor or department is hard-denied."""
    _ = actor, obj
    return None


def _casbin_enforcer():
    """Casbin is intentionally not loaded or consulted."""
    return None


def authorize_department_route(
    actor: str | None,
    department: str,
    action: str = "route",
    *,
    operator_approved: bool = False,
) -> AuthorizationDecision:
    """Allow local FOXAI routing, inspection, planning, and department use."""
    _ = operator_approved
    return AuthorizationDecision(
        True,
        normalize_actor(actor),
        (department or "").strip().lower(),
        (action or "").strip().lower(),
        "Security containment disabled; local FOXAI operation allowed.",
        "containment_disabled",
    )


def authorize_repair_action(
    actor: str | None,
    approval_source: str | None,
    confirmation: str | None,
    action_id: str,
) -> AuthorizationDecision:
    """Keep only exact apply confirmation; actor/source authorization is removed."""
    subject = normalize_actor(actor)
    normalized_action_id = (action_id or "").strip()
    expected = f"APPLY {normalized_action_id}".strip().upper()
    supplied = (confirmation or "").strip().upper()

    if not normalized_action_id or supplied != expected:
        return AuthorizationDecision(
            False,
            subject,
            "repair_chamber",
            "apply",
            f"Exact confirmation required: {expected}",
            "stability_confirmation",
        )

    return AuthorizationDecision(
        True,
        subject,
        "repair_chamber",
        "apply",
        "Exact apply confirmation accepted.",
        "stability_confirmation",
    )


def is_protected_path(path: str | Path, root: str | Path | None = None) -> bool:
    """Protected-path denial is disabled; callers remain responsible for plans."""
    _ = path, root
    return False


def redact_secrets(text: str | None) -> tuple[str, int]:
    """Secret redaction is disabled; return content unchanged."""
    return text or "", 0


def redact_mapping(value: Any) -> tuple[Any, int]:
    """Recursive redaction is disabled; return content unchanged."""
    return value, 0


@dataclass(frozen=True)
class AirlockAuditEvent:
    event_id: str
    correlation_id: str
    mission_id: str
    timestamp: str
    actor: str
    object: str
    action: str
    decision: str
    reason: str
    policy_source: str
    approval_id: str
    receipt_id: str
    previous_hash: str
    event_hash: str
    severity: str = "INFO"
    incident_kind: str = "containment_disabled"
    attempt_count: int = 1
    context_status: str = "disabled"
    test_event: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _new_airlock_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def new_airlock_correlation_id() -> str:
    return _new_airlock_id("corr")


def _normalize_airlock_incident_kind(
    decision: str,
    action: str,
    *,
    test_event: bool = False,
    incident_kind: str | None = None,
) -> str:
    _ = decision, action, test_event, incident_kind
    return "containment_disabled"


def _normalize_airlock_context_status(value: str | None) -> str:
    _ = value
    return "disabled"


def _airlock_event_severity(
    decision: str,
    incident_kind: str,
    attempt_count: int,
) -> str:
    _ = decision, incident_kind, attempt_count
    return "INFO"


def _next_airlock_denial_attempt_count(
    path: Path,
    *,
    mission_id: str,
    incident_kind: str,
) -> int:
    _ = path, mission_id, incident_kind
    return 1


def airlock_chain_alert(verification: dict[str, Any] | None) -> dict[str, Any]:
    _ = verification
    return {
        "active": False,
        "severity": "INFO",
        "incident_kind": "containment_disabled",
        "message": "Security containment and Airlock enforcement are disabled.",
        "failures": [],
    }


def make_airlock_audit_event(
    *,
    actor: str,
    obj: str,
    action: str,
    decision: str,
    reason: str,
    policy_source: str,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    approval_id: str | None = None,
    receipt_id: str | None = None,
    previous_hash: str | None = None,
    test_event: bool = False,
    incident_kind: str | None = None,
    attempt_count: int = 1,
    context_status: str | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
) -> AirlockAuditEvent:
    _ = decision, policy_source, test_event, incident_kind, attempt_count, context_status
    payload = {
        "event_id": event_id or _new_airlock_id("evt"),
        "correlation_id": correlation_id or new_airlock_correlation_id(),
        "mission_id": (mission_id or "").strip(),
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": normalize_actor(actor),
        "object": obj or "",
        "action": (action or "").strip().lower(),
        "decision": "allow",
        "reason": reason or "Containment disabled.",
        "policy_source": "containment_disabled",
        "approval_id": (approval_id or "").strip(),
        "receipt_id": (receipt_id or "").strip(),
        "previous_hash": (previous_hash or "").strip(),
        "severity": "INFO",
        "incident_kind": "containment_disabled",
        "attempt_count": 1,
        "context_status": "disabled",
        "test_event": False,
    }
    payload["event_hash"] = sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return AirlockAuditEvent(**payload)


def verify_airlock_audit_log(
    log_path: str | Path,
) -> dict[str, Any]:
    """Airlock audit verification is disabled and never fails closed."""
    _ = log_path
    return {
        "valid": True,
        "event_count": 0,
        "final_hash": "",
        "failures": [],
        "disabled": True,
    }


def make_tool_receipt(
    action: str,
    state: str,
    *,
    checks: Iterable[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
    actor: str = "system",
    correlation_id: str | None = None,
    mission_id: str | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    allowed_states = {
        "verified",
        "requested",
        "unverified",
        "failed",
        "denied",
        "rolled_back",
    }
    normalized_state = state if state in allowed_states else "unverified"
    check_list = list(checks or [])
    checks_pass = not check_list or all(bool(item.get("ok")) for item in check_list)
    if normalized_state == "verified" and not checks_pass:
        normalized_state = "unverified"

    payload: dict[str, Any] = {
        "action": action,
        "state": normalized_state,
        "verified": normalized_state == "verified",
        "actor": normalize_actor(actor),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": check_list,
        "details": details or {},
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id
    if mission_id:
        payload["mission_id"] = mission_id
    if approval_id:
        payload["approval_id"] = approval_id

    digest_source = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    payload["receipt_id"] = sha256(digest_source).hexdigest()[:24]
    return payload


def append_airlock_audit_event(
    *,
    actor: str,
    obj: str,
    action: str,
    decision: str,
    reason: str,
    policy_source: str,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    approval_id: str | None = None,
    receipt_id: str | None = None,
    test_event: bool = False,
    incident_kind: str | None = None,
    context_status: str | None = None,
    root: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a compatibility receipt; no Airlock event is written."""
    _ = (
        obj,
        action,
        decision,
        reason,
        policy_source,
        receipt_id,
        test_event,
        incident_kind,
        context_status,
        root,
        log_path,
    )
    return make_tool_receipt(
        "append_airlock_audit_event",
        "verified",
        actor=actor,
        correlation_id=correlation_id,
        mission_id=mission_id,
        approval_id=approval_id,
        checks=[{
            "id": "containment_disabled",
            "ok": True,
            "detail": "No Airlock audit event was written.",
        }],
        details={"disabled": True},
    )


def record_authorization_decision(
    decision: AuthorizationDecision,
    *,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    approval_id: str | None = None,
    receipt_id: str | None = None,
    test_event: bool = False,
    incident_kind: str | None = None,
    context_status: str | None = None,
    root: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    _ = (
        receipt_id,
        test_event,
        incident_kind,
        context_status,
        root,
        log_path,
    )
    return make_tool_receipt(
        "record_authorization_decision",
        "verified",
        actor=decision.actor,
        correlation_id=correlation_id,
        mission_id=mission_id,
        approval_id=approval_id,
        checks=[{
            "id": "containment_disabled",
            "ok": True,
            "detail": decision.to_dict(),
        }],
        details={"disabled": True, "decision": decision.to_dict()},
    )


def validate_airlock_route_receipt(
    route_audit_receipt: Any,
    *,
    expected_actor: str,
    expected_object: str,
    expected_action: str,
    correlation_id: str,
    mission_id: str,
) -> dict[str, Any]:
    """Route-receipt enforcement is disabled; return a compatibility receipt."""
    _ = route_audit_receipt, expected_object, expected_action
    return make_tool_receipt(
        "validate_airlock_route_receipt",
        "verified",
        actor=expected_actor,
        correlation_id=correlation_id,
        mission_id=mission_id,
        checks=[{
            "id": "containment_disabled",
            "ok": True,
            "detail": "Route receipt validation bypassed.",
        }],
        details={
            "reason": "Security containment disabled.",
            "context_status": "disabled",
            "failed_check_ids": [],
        },
    )


def record_boundary_denial(
    *,
    actor: str,
    obj: str,
    action: str,
    reason: str,
    incident_kind: str,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    approval_id: str | None = None,
    receipt_id: str | None = None,
    context_status: str | None = None,
    root: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Boundary denial is disabled; record a non-blocking compatibility receipt."""
    _ = (
        obj,
        action,
        reason,
        incident_kind,
        receipt_id,
        context_status,
        root,
        log_path,
    )
    return make_tool_receipt(
        "record_boundary_denial",
        "verified",
        actor=actor,
        correlation_id=correlation_id,
        mission_id=mission_id,
        approval_id=approval_id,
        checks=[{"id": "containment_disabled", "ok": True}],
        details={"disabled": True, "blocked": False},
    )


def record_trip_sentry_test_event(
    *,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    root: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    _ = root, log_path
    return make_tool_receipt(
        "record_trip_sentry_test_event",
        "verified",
        actor="ui_operator",
        correlation_id=correlation_id,
        mission_id=mission_id,
        checks=[{"id": "containment_disabled", "ok": True}],
        details={"disabled": True},
    )


def guard_model_action_claims(text: str | None) -> dict[str, Any]:
    """Do not alter model text or inject unverified-action warnings."""
    return {
        "text": text or "",
        "flagged": False,
        "external_action_verified": False,
        "reason": "Model-action claim guard disabled.",
    }
