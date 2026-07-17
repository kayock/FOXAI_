GS2A — FOXAI Guarded Streaming Phase 2 Transactional Apply

EXTRACT
-------
Extract the complete folder directly to:

    Z:\FOXAI\GS2A\

Do not run it from inside the ZIP preview.

BEFORE RUNNING
--------------
Close:

- FOXAI WebUI;
- Chat Engine;
- benchmark servers.

RUN
---
    APPLY.bat

The package performs a complete fail-closed preflight before asking for
authorization.

EXACT APPROVAL PHRASE
---------------------
    APPROVE GUARDED STREAMING PHASE 2 APPLY

ALLOWED LIVE SCOPE
------------------
    core\foxai_web.py

No other live source or configuration file is allowed to change.
No delete operation is included.

TRANSACTIONAL SAFETY
--------------------
- verifies the package manifest;
- verifies the locked live baseline;
- verifies the approved preview receipt;
- reconstructs the exact candidate from the approved diff;
- checks every embedded JavaScript block with node --check;
- runs the guard-before-exposure helper harness;
- runs the fragmented NDJSON browser harness;
- verifies /api/chat/send is byte-identical;
- runs Boundary Watch 5/5;
- creates and verifies a backup only after operator approval;
- installs through a staged atomic replacement;
- repeats all postflight checks against the live file;
- verifies security logs and protected non-targets did not change;
- rolls back automatically on any post-install failure.

SUCCESS
-------
Nothing is considered installed unless the generated receipt says:

    State: applied_verified
    Verified: True

EXPECTED FINAL HASH
-------------------
    core\foxai_web.py
    e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb
