from __future__ import annotations

"""KayocktheOS Phase 1 security-containment helpers.

This module is deliberately deterministic. Model text is never treated as
operator approval. Casbin support is optional and defaults to the hard-coded,
default-deny fallback until the dependency is installed and the policy files
are present.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
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
    subject = normalize_actor(actor)
    obj = (department or "").strip().lower()
    deny = _hard_deny(subject, obj)
    if deny:
        return AuthorizationDecision(False, subject, obj, action, deny.reason, deny.policy_source)

    if obj not in PRIVILEGED_DEPARTMENTS:
        return AuthorizationDecision(True, subject, obj, action, "Non-privileged route.")

    enforcer = _casbin_enforcer()
    if enforcer is not None:
        try:
            allowed = bool(enforcer.enforce(subject, obj, action))
            return AuthorizationDecision(
                allowed, subject, obj, action,
                "Casbin policy allowed the request." if allowed else "Casbin policy denied the request.",
                "casbin",
            )
        except Exception:
            pass

    if subject in OPERATOR_ACTORS:
        if obj in {"engineer", "engineering_airlock"} and action in {"route", "inspect", "search", "preview"}:
            return AuthorizationDecision(True, subject, obj, action, "Trusted operator may request scoped Engineering Airlock inspection.")
        if obj in {"repair_bay", "repair_chamber"} and action == "preview":
            return AuthorizationDecision(True, subject, obj, action, "Trusted operator may preview Repair Chamber actions.")
        if obj in {"repair_bay", "repair_chamber"} and action in {"apply", "execute_structured_action"} and operator_approved:
            return AuthorizationDecision(True, subject, obj, action, "Trusted operator supplied the structured approval gate.")

    if subject == "engineer" and obj in {"engineer", "engineering_airlock"} and action in {"inspect", "search"}:
        return AuthorizationDecision(True, subject, obj, action, "Engineer may perform read-only inspection inside the Engineering Airlock.")

    if subject == "repair_bay" and obj == "repair_chamber" and action == "execute_structured_action" and operator_approved:
        return AuthorizationDecision(True, subject, obj, action, "Repair Bay may execute only the operator-approved structured action.")

    return AuthorizationDecision(False, subject, obj, action, "Default deny: privileged route lacks trusted operator authorization.")


def authorize_repair_action(
    actor: str | None,
    approval_source: str | None,
    confirmation: str | None,
    action_id: str,
) -> AuthorizationDecision:
    subject = normalize_actor(actor)
    expected = f"APPLY {action_id}".strip().upper()
    supplied = (confirmation or "").strip().upper()
    source = (approval_source or "").strip().lower()
    operator_approved = subject in OPERATOR_ACTORS and source == "ui_operator" and supplied == expected
    decision = authorize_department_route(
        subject,
        "repair_chamber",
        "apply",
        operator_approved=operator_approved,
    )
    if not decision.allowed:
        reason = decision.reason
        if subject not in OPERATOR_ACTORS:
            reason = "Repair Chamber denied: caller is not the trusted operator."
        elif source != "ui_operator":
            reason = "Repair Chamber denied: approval did not originate from the operator UI gate."
        elif supplied != expected:
            reason = f"Repair Chamber denied: exact confirmation required: {expected}"
        return AuthorizationDecision(False, subject, "repair_chamber", "apply", reason, decision.policy_source)
    return AuthorizationDecision(True, subject, "repair_chamber", "apply", "Exact operator approval phrase accepted.", decision.policy_source)


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


def make_tool_receipt(
    action: str,
    state: str,
    *,
    checks: Iterable[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
    actor: str = "system",
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
    digest_source = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    payload["receipt_id"] = sha256(digest_source).hexdigest()[:24]
    return payload


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
