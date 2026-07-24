# FOXAI Mission Archive

- Session ID: `20260723T012303705443_b5dec6`
- Interface: WebUI
- Project: Default_Mission
- Professor: Agent Fox
- Model: Qwen3-30B-A3B-Q4_K_M.gguf
- Started: 2026-07-23T01:23:03

## Transcript

### ERIC — 2026-07-23T07:23:31+00:00

/engineer workshop read core\security_containment.py :: LINES 1-200

### ENGINEER — 2026-07-23T07:23:31+00:00

ENGINEERING WORKSHOP — EXACT FILE CONTENT

Mission ID: ENG-20260723-071407-27BDEA
Path: Z:\FOXAI\core\security_containment.py
Relative path: core\security_containment.py
Encoding: utf-8
Size: 37899 bytes
Total lines: 1159
Showing lines: 1-200

    1: from __future__ import annotations
    2: 
    3: """KayocktheOS Phase 1 security-containment helpers.
    4: 
    5: This module is deliberately deterministic. Model text is never treated as
    6: operator approval. Casbin support is optional and defaults to the hard-coded,
    7: default-deny fallback until the dependency is installed and the policy files
    8: are present.
    9: """
   10: 
   11: from contextlib import contextmanager
   12: from dataclasses import asdict, dataclass
   13: from datetime import datetime, timezone
   14: from functools import lru_cache
   15: from hashlib import sha256
   16: import json
   17: import os
   18: from pathlib import Path
   19: import re
   20: import secrets
   21: from threading import RLock
   22: import time
   23: from typing import Any, Iterable
   24: 
   25: OPERATOR_ACTORS = {"operator", "human_operator", "eric", "ui_operator"}
   26: MODEL_ACTORS = {
   27:     "agent_fox", "assistant", "model", "llm", "professor", "mission_console",
   28:     "unknown_model", "generated_prompt",
   29: }
   30: PRIVILEGED_DEPARTMENTS = {
   31:     "engineer", "engineering_airlock", "repair_bay", "repair_chamber",
   32: }
   33: 
   34: PROTECTED_DIR_NAMES = {
   35:     ".ssh", ".gnupg", ".aws", ".azure", ".kube",
   36:     "credentials", "credential", "secrets", "secret",
   37:     "vault", "vaults", "keystore", "keyring", "keyrings",
   38:     "passwords", "private_keys", "windows_credentials",
   39: }
   40: PROTECTED_FILE_NAMES = {
   41:     ".env", "credentials.json", "credential.json", "client_secret.json",
   42:     "client_secrets.json", "secrets.json", "secret.json", "token.json",
   43:     "tokens.json", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
   44:     "authorized_keys", "passwords.txt", "passwords.csv",
   45: }
   46: PROTECTED_SUFFIXES = {
   47:     ".pem", ".key", ".p12", ".pfx", ".kdbx", ".jks", ".keystore",
   48:     ".ovpn", ".ppk",
   49: }
   50: 
   51: _EXPLICIT_ENGINEER = re.compile(r"^\s*(?:/engineer(?:\s+|$)|engineer\s*[:,]\s*\S)", re.I)
   52: 
   53: _SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
   54:     (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----", re.S), "[REDACTED PRIVATE KEY]"),
   55:     (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"), "[REDACTED OPENAI KEY]"),
   56:     (re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{16,}\b"), "[REDACTED GITHUB TOKEN]"),
   57:     (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED AWS ACCESS KEY]"),
   58:     (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[REDACTED GOOGLE API KEY]"),
   59:     (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[REDACTED JWT]"),
   60:     (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"), "Bearer [REDACTED TOKEN]"),
   61:     (re.compile(r"(?i)(\b(?:password|passwd|pwd|api[_-]?key|secret|token|client[_-]?secret|access[_-]?key|private[_-]?key)\b\s*[:=]\s*[\"']?)([^\s,;\"']{4,})"), r"\1[REDACTED]"),
   62:     (re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:/@]+:)([^\s/@]+)(@)"), r"\1[REDACTED]\3"),
   63: ]
   64: 
   65: _ACTION_CLAIM = re.compile(
   66:     r"(?i)\b(?:I|we|the system|FOXAI|Agent Fox)\s+(?:have\s+)?(?:successfully\s+)?"
   67:     r"(?:opened|launched|created|deleted|removed|moved|installed|modified|overwrote|saved|fixed|repaired|applied|executed|completed|restored|rolled back)\b"
   68: )
   69: 
   70: 
   71: AIRLOCK_AUDIT_RELATIVE_PATH = (
   72:     Path("Logs") / "Security" / "engineering_airlock_events.jsonl"
   73: )
   74: 
   75: _MUTATING_REPAIR_ACTIONS = {
   76:     "apply",
   77:     "execute_structured_action",
   78: }
   79: 
   80: 
   81: _AIRLOCK_PROCESS_LOCK = RLock()
   82: _AIRLOCK_LOCK_TIMEOUT_SECONDS = 5.0
   83: 
   84: 
   85: @contextmanager
   86: def _airlock_audit_lock(
   87:     path: str | Path,
   88:     *,
   89:     timeout_seconds: float = _AIRLOCK_LOCK_TIMEOUT_SECONDS,
   90: ):
   91:     """Serialize the shared audit chain across threads and processes."""
   92:     audit_path = Path(path)
   93:     lock_path = audit_path.with_name(audit_path.name + ".lock")
   94:     lock_path.parent.mkdir(parents=True, exist_ok=True)
   95: 
   96:     with _AIRLOCK_PROCESS_LOCK:
   97:         with lock_path.open("a+b") as handle:
   98:             handle.seek(0, 2)
   99:             if handle.tell() == 0:
  100:                 handle.write(b"\0")
  101:                 handle.flush()
  102:                 os.fsync(handle.fileno())
  103:             handle.seek(0)
  104: 
  105:             deadline = time.monotonic() + max(
  106:                 0.1,
  107:                 float(timeout_seconds),
  108:             )
  109:             lock_kind = "process_only"
  110:             lock_module = None
  111: 
  112:             if os.name == "nt":
  113:                 import msvcrt  # type: ignore
  114: 
  115:                 while True:
  116:                     try:
  117:                         handle.seek(0)
  118:                         msvcrt.locking(
  119:                             handle.fileno(),
  120:                             msvcrt.LK_NBLCK,
  121:                             1,
  122:                         )
  123:                         lock_kind = "msvcrt"
  124:                         lock_module = msvcrt
  125:                         break
  126:                     except OSError:
  127:                         if time.monotonic() >= deadline:
  128:                             raise TimeoutError(
  129:                                 "Timed out waiting for the shared "
  130:                                 "Airlock audit lock."
  131:                             )
  132:                         time.sleep(0.05)
  133:             else:
  134:                 try:
  135:                     import fcntl  # type: ignore
  136:                 except ImportError:
  137:                     fcntl = None
  138: 
  139:                 if fcntl is not None:
  140:                     while True:
  141:                         try:
  142:                             fcntl.flock(
  143:                                 handle.fileno(),
  144:                                 fcntl.LOCK_EX | fcntl.LOCK_NB,
  145:                             )
  146:                             lock_kind = "fcntl"
  147:                             lock_module = fcntl
  148:                             break
  149:                         except BlockingIOError:
  150:                             if time.monotonic() >= deadline:
  151:                                 raise TimeoutError(
  152:                                     "Timed out waiting for the shared "
  153:                                     "Airlock audit lock."
  154:                                 )
  155:                             time.sleep(0.05)
  156: 
  157:             try:
  158:                 yield {
  159:                     "lock_path": str(lock_path),
  160:                     "lock_kind": lock_kind,
  161:                 }
  162:             finally:
  163:                 if lock_kind == "msvcrt" and lock_module is not None:
  164:                     handle.seek(0)
  165:                     lock_module.locking(
  166:                         handle.fileno(),
  167:                         lock_module.LK_UNLCK,
  168:                         1,
  169:                     )
  170:                 elif lock_kind == "fcntl" and lock_module is not None:
  171:                     lock_module.flock(
  172:                         handle.fileno(),
  173:                         lock_module.LOCK_UN,
  174:                     )
  175: 
  176: 
  177: def normalize_actor(actor: str | None) -> str:
  178:     return (actor or "unknown").strip().lower().replace(" ", "_")
  179: 
  180: 
  181: def is_explicit_engineer_command(text: str | None) -> bool:
  182:     return bool(_EXPLICIT_ENGINEER.search(text or ""))
  183: 
  184: 
  185: @dataclass(frozen=True)
  186: class AuthorizationDecision:
  187:     allowed: bool
  188:     actor: str
  189:     object: str
  190:     action: str
  191:     reason: str
  192:     policy_source: str = "deterministic_fallback"
  193: 
  194:     def to_dict(self) -> dict[str, Any]:
  195:         return asdict(self)
  196: 
  197: 
  198: def _hard_deny(actor: str, obj: str) -> AuthorizationDecision | None:
  199:     if actor in MODEL_ACTORS and obj in PRIVILEGED_DEPARTMENTS:
  200:         return AuthorizationDecision(

More content is available. Continue with:
/engineer workshop read core\security_containment.py :: LINES 201-400

Safety: exact-path, bounded, read-only file access; nothing changed.
