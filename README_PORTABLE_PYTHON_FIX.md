# KayocktheOS Portable Python Compatibility Fix — Preview

## Scope

This preview proposes **one source-file change only**:

`core/foxai_web.py`

It does not alter portable Python, `python._pth`, the launcher, the security policy files, or any other FOXAI file.

## Why the change is needed

The Phase 1 WebUI works when the FOXAI project root is explicitly inserted into Python's module search path. The portable Python environment did not automatically expose either `Z:\FOXAI` or `Z:\FOXAI\core`, so both of these imports failed:

- `core.security_containment`
- fallback `security_containment`

The proposed code computes the project root from `__file__`, inserts it into `sys.path` before the containment import, and reuses the same value as `ROOT`.

## Exact proposed change

```diff
--- a/core/foxai_web.py
+++ b/core/foxai_web.py
@@ -9,8 +9,12 @@
 from datetime import datetime
 from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
 from urllib.parse import urlparse, parse_qs, unquote
 
+PROJECT_ROOT = Path(__file__).resolve().parents[1]
+if str(PROJECT_ROOT) not in sys.path:
+    sys.path.insert(0, str(PROJECT_ROOT))
+
 try:
     from core.security_containment import (
         authorize_repair_action, guard_model_action_claims, is_protected_path,
         make_tool_receipt, redact_mapping, redact_secrets,
@@ -20,9 +24,9 @@
         authorize_repair_action, guard_model_action_claims, is_protected_path,
         make_tool_receipt, redact_mapping, redact_secrets,
     )
 
-ROOT=Path(__file__).resolve().parents[1]; DRIVE=Path(ROOT.anchor); PORT=8765; URL=f"http://127.0.0.1:{PORT}"
+ROOT=PROJECT_ROOT; DRIVE=Path(ROOT.anchor); PORT=8765; URL=f"http://127.0.0.1:{PORT}"
 KAYOCK=DRIVE/'Kayock-Browser-2.5.3-rc.1-Portable.exe'; LOGS=ROOT/'Logs'; LOG=LOGS/'web_gui.log'
 ENGINE=ROOT/'Engine'/'llama-server.exe'; CHAT_HEALTH='http://127.0.0.1:8080/health'; CHAT_API='http://127.0.0.1:8080/v1/chat/completions'
 COMFY=ROOT/'ComfyUI'; COMFY_MAIN=COMFY/'main.py'; LIB=ROOT/'Library'; PROJECTS=ROOT/'Projects'
 SECURITY_SYSTEM_RULES=(
```

## Candidate verification performed

- Reviewed Phase 1 baseline SHA-256 matched:
  `5feb632c5d44d260dba706019beeacf2f5e210ab5a495b9ede3fbe287a6b899e`
- Candidate Python compilation: PASS
- Existing Phase 1 regression tests: PASS (15 tests)
- Restricted module-path import test: PASS
- Live files modified while preparing this preview: NO

Candidate SHA-256:

`4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43`

## On the USB

Extract this entire folder directly inside `Z:\FOXAI`, so the layout is:

`Z:\FOXAI\KayocktheOS_Portable_Python_Compatibility_Preview_20260712T015118Z\PREVIEW_PORTABLE_PYTHON_FIX.bat`

Run only:

`PREVIEW_PORTABLE_PYTHON_FIX.bat`

The preview command verifies that live `core\foxai_web.py` still has the exact reviewed Phase 1 hash and then generates a local exact diff and receipt. It does not apply the change.

Do not manually copy the candidate file over the live file. An apply-and-rollback command should be prepared only after the preview is approved.
