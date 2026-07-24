from __future__ import annotations

"""KayocktheOS Phase 1 security-containment helpers.

This module is deliberately deterministic. Model text is never treated as
operator approval. Casbin support is optional and defaults to the hard-coded,
default-deny fallback until the dependency is installed and the policy files
are present.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
from threading import RLock
import time
from typing import Any, Iterable

OPERATOR_ACTORS = {"operator", "human_operator", "eric", "ui_operator"}
MODEL_ACTORS = {
    "agent_fox", "assistant", "model", "llm", "professor", "mission_console",
    "unknown_model", "generated_prompt",
}
PRIVILEGED_DEPARTMENTS = {
    "engineer", "engineering_airlock", "repair_bay", "repair_chamber",
}

PROTECTED_DIR_NAMES = {
    ".ssh", ".gnupg", ".aws", ".azure", ".kube",
    "credentials", "credential", "secrets", "secret",
    "vault", "vaults", "keystore", "keyring", "keyrings",
    "passwords", "private_keys", "windows_credentials",
}
PROTECTED_FILE_NAMES = {
    ".env", "credentials.json", "credential.json", "client_secret.json",
    "client_secrets.json", "secrets.json", "secret.json", "token.json",
    "tokens.json", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "authorized_keys", "passwords.txt", "passwords.csv",
}
PROTECTED_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".kdbx", ".jks", ".keystore",
    ".ovpn", ".ppk",
}

_EXPLICIT_ENGINEER = re.compile(r"^\s*(?:/engineer(?:\s+|$)|engineer\s*[:,]\s*\S)", re.I)

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----", re.S), "[REDACTED PRIVATE KEY]"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"), "[REDACTED OPENAI KEY]"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{16,}\b"), "[REDACTED GITHUB TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED AWS ACCESS KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[REDACTED GOOGLE API KEY]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[REDACTED JWT]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"), "Bearer [REDACTED TOKEN]"),
    (re.compile(r"(?i)(\b(?:password|passwd|pwd|api[_-]?key|secret|token|client[_-]?secret|access[_-]?key|private[_-]?key)\b\s*[:=]\s*[\"']?)([^\s,;\"']{4,})"), r"\1[REDACTED]"),
    (re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:/@]+:)([^\s/@]+)(@)"), r"\1[REDACTED]\3"),
]

_ACTION_CLAIM = re.compile(
    r"(?i)\b(?:I|we|the system|FOXAI|Agent Fox)\s+(?:have\s+)?(?:successfully\s+)?"
    r"(?:opened|launched|created|deleted|removed|moved|installed|modified|overwrote|saved|fixed|repaired|applied|executed|completed|restored|rolled back)\b"
)


AIRLOCK_AUDIT_RELATIVE_PATH = (
    Path("Logs") / "Security" / "engineering_airlock_events.jsonl"
)

_MUTATING_REPAIR_ACTIONS = {
    "apply",
    "execute_structured_action",
}


_AIRLOCK_PROCESS_LOCK = RLock()
_AIRLOCK_LOCK_TIMEOUT_SECONDS = 5.0


@contextmanager
def _airlock_audit_lock(
    path: str | Path,
    *,
    timeout_seconds: float = _AIRLOCK_LOCK_TIMEOUT_SECONDS,
):
    """Serialize the shared audit chain across threads and processes."""
    audit_path = Path(path)
    lock_path = audit_path.with_name(audit_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with _AIRLOCK_PROCESS_LOCK:
        with lock_path.open("a+b") as handle:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)

            deadline = time.monotonic() + max(
                0.1,
                float(timeout_seconds),
            )
            lock_kind = "process_only"
            lock_module = None

            if os.name == "nt":
                import msvcrt  # type: ignore

                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(
                            handle.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )
                        lock_kind = "msvcrt"
                        lock_module = msvcrt
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError(
                                "Timed out waiting for the shared "
                                "Airlock audit lock."
                            )
                        time.sleep(0.05)
            else:
                try:
                    import fcntl  # type: ignore
                except ImportError:
                    fcntl = None

                if fcntl is not None:
                    while True:
                        try:
                            fcntl.flock(
                                handle.fileno(),
                                fcntl.LOCK_EX | fcntl.LOCK_NB,
                            )
                            lock_kind = "fcntl"
                            lock_module = fcntl
                            break
                        except BlockingIOError:
                            if time.monotonic() >= deadline:
                                raise TimeoutError(
                                    "Timed out waiting for the shared "
                                    "Airlock audit lock."
                                )
                            time.sleep(0.05)

            try:
                yield {
                    "lock_path": str(lock_path),
                    "lock_kind": lock_kind,
                }
            finally:
                if lock_kind == "msvcrt" and lock_module is not None:
                    handle.seek(0)
                    lock_module.locking(
                        handle.fileno(),
                        lock_module.LK_UNLCK,
                        1,
                    )
                elif lock_kind == "fcntl" and lock_module is not None:
                    lock_module.flock(
                        handle.fileno(),
                        lock_module.LOCK_UN,
                    )


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
    policy_source: str = "deterministic_fallback"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hard_deny(actor: str, obj: str) -> AuthorizationDecision | None:
    if actor in MODEL_ACTORS and obj in PRIVILEGED_DEPARTMENTS:
        return AuthorizationDecision(
            False, actor, obj, "invoke",
            "Model and prompt actors cannot invoke privileged departments. Operator approval must come from a trusted UI workflow.",
            "hard_deny",
        )
    return None


@lru_cache(maxsize=1)
def _casbin_enforcer():
    try:
        import casbin  # type: ignore
    except Exception:
        return None
    root = Path(__file__).resolve().parents[1]
    model = root / "Config" / "engineering_airlock_model.conf"
    policy = root / "Config" / "engineering_airlock_policy.csv"
    if not model.exists() or not policy.exists():
        return None
    try:
        return casbin.Enforcer(str(model), str(policy))
    except Exception:
        return None


def authorize_department_route(
    actor: str | None,
    department: str,
    action: str = "route",
    *,
    operator_approved: bool = False,
) -> AuthorizationDecision:
    """Authorize routing and read-only access.

    Mutating Repair Chamber actions are deliberately denied here, even when
    ``operator_approved=True``. They must pass through the exact-phrase
    ``authorize_repair_action`` gate so a caller cannot turn a Boolean into
    operator consent.
    """
    subject = normalize_actor(actor)
    obj = (department or "").strip().lower()
    normalized_action = (action or "").strip().lower()

    deny = _hard_deny(subject, obj)
    if deny:
        return AuthorizationDecision(
            False,
            subject,
            obj,
            normalized_action,
            deny.reason,
            deny.policy_source,
        )

    if obj not in PRIVILEGED_DEPARTMENTS:
        return AuthorizationDecision(
            True,
            subject,
            obj,
            normalized_action,
            "Non-privileged route.",
        )

    if (
        obj in {"repair_bay", "repair_chamber"}
        and normalized_action in _MUTATING_REPAIR_ACTIONS
    ):
        return AuthorizationDecision(
            False,
            subject,
            obj,
            normalized_action,
            (
                "Structured approval required: mutating Repair Chamber "
                "actions must use authorize_repair_action with the exact "
                "operator UI confirmation phrase."
            ),
            "structured_approval_gate",
        )

    enforcer = _casbin_enforcer()
    if enforcer is not None:
        try:
            allowed = bool(
                enforcer.enforce(subject, obj, normalized_action)
            )
            return AuthorizationDecision(
                allowed,
                subject,
                obj,
                normalized_action,
                (
                    "Casbin policy allowed the request."
                    if allowed
                    else "Casbin policy denied the request."
                ),
                "casbin",
            )
        except Exception:
            pass

    if subject in OPERATOR_ACTORS:
        if (
            obj in {"engineer", "engineering_airlock"}
            and normalized_action in {"route", "inspect", "search", "preview"}
        ):
            return AuthorizationDecision(
                True,
                subject,
                obj,
                normalized_action,
                (
                    "Trusted operator may request scoped Engineering "
                    "Airlock inspection."
                ),
            )
        if (
            obj in {"repair_bay", "repair_chamber"}
            and normalized_action == "preview"
        ):
            return AuthorizationDecision(
                True,
                subject,
                obj,
                normalized_action,
                "Trusted operator may preview Repair Chamber actions.",
            )

    if (
        subject == "engineer"
        and obj in {"engineer", "engineering_airlock"}
        and normalized_action in {"inspect", "search"}
    ):
        return AuthorizationDecision(
            True,
            subject,
            obj,
            normalized_action,
            (
                "Engineer may perform read-only inspection inside the "
                "Engineering Airlock."
            ),
        )

    return AuthorizationDecision(
        False,
        subject,
        obj,
        normalized_action,
        "Default deny: privileged route lacks trusted operator authorization.",
    )


def authorize_repair_action(
    actor: str | None,
    approval_source: str | None,
    confirmation: str | None,
    action_id: str,
) -> AuthorizationDecision:
    """Validate the exact trusted-UI approval phrase for one action ID."""
    subject = normalize_actor(actor)
    normalized_action_id = (action_id or "").strip()
    expected = f"APPLY {normalized_action_id}".strip().upper()
    supplied = (confirmation or "").strip().upper()
    source = (approval_source or "").strip().lower()

    if subject not in OPERATOR_ACTORS:
        return AuthorizationDecision(
            False,
            subject,
            "repair_chamber",
            "apply",
            "Repair Chamber denied: caller is not the trusted operator.",
            "structured_approval_gate",
        )

    if source != "ui_operator":
        return AuthorizationDecision(
            False,
            subject,
            "repair_chamber",
            "apply",
            (
                "Repair Chamber denied: approval did not originate from "
                "the operator UI gate."
            ),
            "structured_approval_gate",
        )

    if not normalized_action_id or supplied != expected:
        return AuthorizationDecision(
            False,
            subject,
            "repair_chamber",
            "apply",
            (
                "Repair Chamber denied: exact confirmation required: "
                f"{expected}"
            ),
            "structured_approval_gate",
        )

    return AuthorizationDecision(
        True,
        subject,
        "repair_chamber",
        "apply",
        "Exact operator approval phrase accepted.",
        "structured_approval_gate",
    )


def is_protected_path(path: str | Path, root: str | Path | None = None) -> bool:
    p = Path(path)
    try:
        if root is not None:
            p = p.resolve().relative_to(Path(root).resolve())
    except Exception:
        try:
            p = p.resolve()
        except Exception:
            pass
    parts = [part.casefold() for part in p.parts]
    if any(part in PROTECTED_DIR_NAMES for part in parts):
        return True
    name = p.name.casefold()
    if name in PROTECTED_FILE_NAMES or name.startswith(".env."):
        return True
    if p.suffix.casefold() in PROTECTED_SUFFIXES:
        return True
    return False


def redact_secrets(text: str | None) -> tuple[str, int]:
    value = text or ""
    count = 0
    for pattern, replacement in _SECRET_PATTERNS:
        value, found = pattern.subn(replacement, value)
        count += found
    return value, count


def redact_mapping(value: Any) -> tuple[Any, int]:
    """Recursively redact strings before data is shown to a model or UI."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        out = []
        total = 0
        for item in value:
            clean, count = redact_mapping(item)
            out.append(clean)
            total += count
        return out, total
    if isinstance(value, tuple):
        clean, total = redact_mapping(list(value))
        return tuple(clean), total
    if isinstance(value, dict):
        out = {}
        total = 0
        for key, item in value.items():
            clean, count = redact_mapping(item)
            out[key] = clean
            total += count
        return out, total
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
    incident_kind: str = "approved_sensitive_operation"
    attempt_count: int = 1
    context_status: str = "verified"
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


_AIRLOCK_INCIDENT_KINDS = {
    "approved_sensitive_operation",
    "authorization_denial",
    "protected_resource_denial",
    "context_mismatch",
    "unauthorized_mutation_attempt",
    "trip_sentry_test",
}

_AIRLOCK_CONTEXT_STATUSES = {
    "verified",
    "not_supplied",
    "mismatch",
    "invalid",
    "failed_closed",
}


def _normalize_airlock_incident_kind(
    decision: str,
    action: str,
    *,
    test_event: bool = False,
    incident_kind: str | None = None,
) -> str:
    normalized_decision = (decision or "deny").strip().lower()
    normalized_action = (action or "").strip().lower()
    requested = (incident_kind or "").strip().lower()
    if test_event or normalized_action == "trip_sentry_test":
        return "trip_sentry_test"
    if requested in _AIRLOCK_INCIDENT_KINDS:
        return requested
    if normalized_decision == "allow":
        return "approved_sensitive_operation"
    return "authorization_denial"


def _normalize_airlock_context_status(value: str | None) -> str:
    normalized = (value or "verified").strip().lower()
    return (
        normalized
        if normalized in _AIRLOCK_CONTEXT_STATUSES
        else "invalid"
    )


def _airlock_event_severity(
    decision: str,
    incident_kind: str,
    attempt_count: int,
) -> str:
    normalized_decision = (decision or "deny").strip().lower()
    if incident_kind == "trip_sentry_test":
        return "TEST"
    if incident_kind == "unauthorized_mutation_attempt":
        return "CRITICAL"
    if incident_kind == "context_mismatch":
        return "WARNING"
    if normalized_decision == "deny" and int(attempt_count or 1) > 1:
        return "WARNING"
    if normalized_decision == "deny":
        return "NOTICE"
    return "INFO"


def _next_airlock_denial_attempt_count(
    path: Path,
    *,
    mission_id: str,
    incident_kind: str,
) -> int:
    normalized_mission = (mission_id or "").strip()
    if not normalized_mission or not path.exists():
        return 1

    count = 0
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
    except Exception:
        return 1

    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if str(event.get("decision") or "").lower() != "deny":
            continue
        if str(event.get("mission_id") or "").strip() != normalized_mission:
            continue
        if str(event.get("incident_kind") or "").strip().lower() != incident_kind:
            continue
        count += 1
    return count + 1


def airlock_chain_alert(verification: dict[str, Any] | None) -> dict[str, Any]:
    """Return a synthetic viewer-only CRITICAL state for an invalid chain."""
    result = dict(verification or {})
    if bool(result.get("valid")):
        return {
            "active": False,
            "severity": "INFO",
            "incident_kind": "audit_chain_verified",
            "message": "The Fox Sentry audit chain is verified.",
            "failures": [],
        }
    failures = list(result.get("failures") or [])
    return {
        "active": True,
        "severity": "CRITICAL",
        "incident_kind": "audit_chain_failure",
        "message": (
            "Fox Sentry is fail-closed because the audit chain is invalid. "
            "No synthetic alert is appended to the untrusted chain."
        ),
        "failures": failures,
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
    """Create one redacted, deterministically classified audit event."""
    clean_object, _ = redact_secrets(obj or "")
    clean_reason, _ = redact_secrets(reason or "")
    normalized_decision = (decision or "deny").strip().lower()
    if normalized_decision not in {"allow", "deny"}:
        normalized_decision = "deny"
    normalized_attempt = max(1, int(attempt_count or 1))
    normalized_kind = _normalize_airlock_incident_kind(
        normalized_decision,
        action,
        test_event=test_event,
        incident_kind=incident_kind,
    )

    payload = {
        "event_id": event_id or _new_airlock_id("evt"),
        "correlation_id": correlation_id or new_airlock_correlation_id(),
        "mission_id": (mission_id or "").strip(),
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": normalize_actor(actor),
        "object": clean_object,
        "action": (action or "").strip().lower(),
        "decision": normalized_decision,
        "reason": clean_reason,
        "policy_source": (policy_source or "").strip(),
        "approval_id": (approval_id or "").strip(),
        "receipt_id": (receipt_id or "").strip(),
        "previous_hash": (previous_hash or "").strip(),
        "severity": _airlock_event_severity(
            normalized_decision,
            normalized_kind,
            normalized_attempt,
        ),
        "incident_kind": normalized_kind,
        "attempt_count": normalized_attempt,
        "context_status": _normalize_airlock_context_status(context_status),
        "test_event": bool(test_event),
    }
    payload["event_hash"] = sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return AirlockAuditEvent(**payload)


def verify_airlock_audit_log(
    log_path: str | Path,
) -> dict[str, Any]:
    """Verify JSONL parsing, event hashes, and the previous-hash chain."""
    path = Path(log_path)
    if not path.exists():
        return {
            "valid": True,
            "event_count": 0,
            "final_hash": "",
            "failures": [],
        }

    failures: list[dict[str, Any]] = []
    previous_hash = ""
    event_count = 0

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
    except Exception as exc:
        return {
            "valid": False,
            "event_count": 0,
            "final_hash": "",
            "failures": [
                {
                    "line": 0,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            ],
        }

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        try:
            event = json.loads(line)
        except Exception as exc:
            failures.append(
                {
                    "line": line_number,
                    "reason": f"Invalid JSON: {type(exc).__name__}: {exc}",
                }
            )
            continue

        supplied_hash = str(event.get("event_hash") or "")
        supplied_previous = str(event.get("previous_hash") or "")
        payload = dict(event)
        payload.pop("event_hash", None)
        calculated_hash = sha256(
            _canonical_json(payload).encode("utf-8")
        ).hexdigest()

        if supplied_previous != previous_hash:
            failures.append(
                {
                    "line": line_number,
                    "reason": "Previous-hash chain mismatch.",
                    "expected": previous_hash,
                    "actual": supplied_previous,
                }
            )

        if supplied_hash != calculated_hash:
            failures.append(
                {
                    "line": line_number,
                    "reason": "Event hash mismatch.",
                    "expected": calculated_hash,
                    "actual": supplied_hash,
                }
            )

        previous_hash = supplied_hash
        event_count += 1

    return {
        "valid": not failures,
        "event_count": event_count,
        "final_hash": previous_hash,
        "failures": failures,
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
    allowed_states = {"verified", "requested", "unverified", "failed", "denied", "rolled_back"}
    state = state if state in allowed_states else "unverified"
    check_list = list(checks or [])
    checks_pass = bool(check_list) and all(bool(item.get("ok")) for item in check_list)
    if state == "verified" and not checks_pass:
        state = "unverified"
    payload = {
        "action": action,
        "state": state,
        "verified": state == "verified",
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
    digest_source = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
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
    """Append one classified event under a verified cross-process chain lock."""
    if log_path is not None:
        path = Path(log_path)
    else:
        project_root = (
            Path(root)
            if root is not None
            else Path(__file__).resolve().parents[1]
        )
        path = project_root / AIRLOCK_AUDIT_RELATIVE_PATH

    event = None
    lock_details: dict[str, Any] = {}

    try:
        with _airlock_audit_lock(path) as acquired_lock:
            lock_details = dict(acquired_lock)
            before = verify_airlock_audit_log(path)
            if not before["valid"]:
                return make_tool_receipt(
                    "append_airlock_audit_event",
                    "failed",
                    actor=actor,
                    correlation_id=correlation_id,
                    mission_id=mission_id,
                    approval_id=approval_id,
                    checks=[{
                        "id": "existing_chain_valid",
                        "ok": False,
                        "detail": before,
                    }],
                    details={
                        "log_path": str(path),
                        "lock": lock_details,
                        "reason": (
                            "Audit append refused because the existing "
                            "chain did not verify."
                        ),
                        "chain_alert": airlock_chain_alert(before),
                    },
                )

            normalized_kind = _normalize_airlock_incident_kind(
                decision,
                action,
                test_event=test_event,
                incident_kind=incident_kind,
            )
            attempt_count = (
                _next_airlock_denial_attempt_count(
                    path,
                    mission_id=(mission_id or ""),
                    incident_kind=normalized_kind,
                )
                if (decision or "").strip().lower() == "deny"
                else 1
            )
            event = make_airlock_audit_event(
                actor=actor,
                obj=obj,
                action=action,
                decision=decision,
                reason=reason,
                policy_source=policy_source,
                correlation_id=correlation_id,
                mission_id=mission_id,
                approval_id=approval_id,
                receipt_id=receipt_id,
                previous_hash=before["final_hash"],
                test_event=test_event,
                incident_kind=normalized_kind,
                attempt_count=attempt_count,
                context_status=context_status,
            )

            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(event.to_dict()) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

            after = verify_airlock_audit_log(path)
            event_written = (
                after["valid"]
                and after["event_count"] == before["event_count"] + 1
                and after["final_hash"] == event.event_hash
            )

            return make_tool_receipt(
                "append_airlock_audit_event",
                "verified" if event_written else "failed",
                actor=actor,
                correlation_id=event.correlation_id,
                mission_id=mission_id,
                approval_id=approval_id,
                checks=[
                    {"id": "shared_audit_lock_acquired", "ok": True, "detail": lock_details},
                    {"id": "existing_chain_valid", "ok": before["valid"]},
                    {
                        "id": "event_count_incremented",
                        "ok": after["event_count"] == before["event_count"] + 1,
                    },
                    {
                        "id": "final_hash_matches_event",
                        "ok": after["final_hash"] == event.event_hash,
                    },
                    {
                        "id": "full_chain_valid",
                        "ok": after["valid"],
                        "detail": after,
                    },
                ],
                details={
                    "log_path": str(path),
                    "lock": lock_details,
                    "event": event.to_dict(),
                },
            )
    except Exception as exc:
        return make_tool_receipt(
            "append_airlock_audit_event",
            "failed",
            actor=actor,
            correlation_id=(
                event.correlation_id if event is not None else correlation_id
            ),
            mission_id=mission_id,
            approval_id=approval_id,
            checks=[{
                "id": "audit_append_completed",
                "ok": False,
                "detail": f"{type(exc).__name__}: {exc}",
            }],
            details={
                "log_path": str(path),
                "lock": lock_details,
                "event": event.to_dict() if event is not None else None,
            },
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
    return append_airlock_audit_event(
        actor=decision.actor,
        obj=decision.object,
        action=decision.action,
        decision="allow" if decision.allowed else "deny",
        reason=decision.reason,
        policy_source=decision.policy_source,
        correlation_id=correlation_id,
        mission_id=mission_id,
        approval_id=approval_id,
        receipt_id=receipt_id,
        test_event=test_event,
        incident_kind=incident_kind,
        context_status=context_status,
        root=root,
        log_path=log_path,
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
    """Validate that one forwarded route receipt matches trusted context."""
    receipt = route_audit_receipt if isinstance(route_audit_receipt, dict) else {}
    event = (receipt.get("details") or {}).get("event")
    event = event if isinstance(event, dict) else {}
    receipt_checks = receipt.get("checks")
    receipt_checks = receipt_checks if isinstance(receipt_checks, list) else []

    normalized_actor = normalize_actor(expected_actor)
    normalized_object = (expected_object or "").strip().lower()
    normalized_action = (expected_action or "").strip().lower()
    normalized_correlation = (correlation_id or "").strip()
    normalized_mission = (mission_id or "").strip()

    checks = [
        {"id": "route_receipt_is_mapping", "ok": isinstance(route_audit_receipt, dict)},
        {"id": "route_receipt_verified", "ok": receipt.get("verified") is True and receipt.get("state") == "verified"},
        {"id": "route_receipt_action", "ok": receipt.get("action") == "append_airlock_audit_event"},
        {"id": "route_receipt_id_present", "ok": bool(str(receipt.get("receipt_id") or "").strip())},
        {"id": "route_event_present", "ok": bool(event)},
        {"id": "expected_correlation_present", "ok": bool(normalized_correlation)},
        {"id": "expected_mission_present", "ok": bool(normalized_mission)},
        {"id": "route_decision_allow", "ok": str(event.get("decision") or "").lower() == "allow"},
        {"id": "route_actor_matches", "ok": normalize_actor(event.get("actor")) == normalized_actor},
        {"id": "route_object_matches", "ok": str(event.get("object") or "").lower() == normalized_object},
        {"id": "route_action_matches", "ok": str(event.get("action") or "").lower() == normalized_action},
        {"id": "route_correlation_matches", "ok": str(event.get("correlation_id") or "").strip() == normalized_correlation},
        {"id": "route_mission_matches", "ok": str(event.get("mission_id") or "").strip() == normalized_mission},
        {"id": "route_event_hash_present", "ok": bool(str(event.get("event_hash") or "").strip())},
        {"id": "route_receipt_checks_pass", "ok": bool(receipt_checks) and all(isinstance(item, dict) and bool(item.get("ok")) for item in receipt_checks)},
    ]
    valid = all(bool(item.get("ok")) for item in checks)
    failed_ids = [item["id"] for item in checks if not item["ok"]]
    reason = (
        "Forwarded Engineering Airlock route receipt verified."
        if valid
        else "Forwarded route context failed validation: " + ", ".join(failed_ids)
    )
    return make_tool_receipt(
        "validate_airlock_route_receipt",
        "verified" if valid else "denied",
        actor=expected_actor,
        correlation_id=correlation_id,
        mission_id=mission_id,
        checks=checks,
        details={
            "reason": reason,
            "route_receipt_id": str(receipt.get("receipt_id") or ""),
            "context_status": "verified" if valid else "mismatch",
            "failed_check_ids": failed_ids,
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
    """Append one deterministic DENY boundary event through the verified chain."""
    decision = AuthorizationDecision(
        False,
        normalize_actor(actor),
        (obj or "engineering_airlock").strip().lower(),
        (action or "boundary").strip().lower(),
        reason,
        "boundary_watch",
    )
    return record_authorization_decision(
        decision,
        correlation_id=correlation_id,
        mission_id=mission_id,
        approval_id=approval_id,
        receipt_id=receipt_id,
        incident_kind=incident_kind,
        context_status=context_status,
        root=root,
        log_path=log_path,
    )

def record_trip_sentry_test_event(
    *,
    correlation_id: str | None = None,
    mission_id: str | None = None,
    root: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Record a harmless, operator-initiated TEST denial event."""
    decision = AuthorizationDecision(
        False,
        "ui_operator",
        "engineering_airlock",
        "trip_sentry_test",
        (
            "TEST incident: operator deliberately exercised the Fox "
            "Sentry audit and alert path. No access or mutation occurred."
        ),
        "trip_sentry_test",
    )
    return record_authorization_decision(
        decision,
        correlation_id=correlation_id,
        mission_id=mission_id,
        test_event=True,
        root=root,
        log_path=log_path,
    )

def guard_model_action_claims(text: str | None) -> dict[str, Any]:
    value = text or ""
    flagged = bool(_ACTION_CLAIM.search(value))
    if flagged:
        value = (
            "[UNVERIFIED ACTION CLAIM — no external tool receipt was supplied. "
            "Treat the following as model text, not proof that an action occurred.]\n\n" + value
        )
    return {
        "text": value,
        "flagged": flagged,
        "external_action_verified": False,
        "reason": "Model output cannot prove an external action without a verified tool receipt.",
    }
