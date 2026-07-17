MIA1A — FOXAI Mission Image Attachments Phase 1 Transactional Apply

EXTRACT
-------
Extract the complete folder directly to:

    Z:\FOXAI\MIA1A\

Do not run it from inside the ZIP preview.

BEFORE RUNNING
--------------
Close:

- FOXAI WebUI;
- Chat Engine;
- vision benchmark servers;
- other benchmark servers.

RUN
---
    APPLY.bat

EXACT APPROVAL PHRASE
---------------------
    APPROVE MISSION IMAGE ATTACHMENTS PHASE 1 APPLY

ALLOWED LIVE SCOPE
------------------
    core\foxai_web.py
    core\server.py

No other live source or configuration file is allowed to change.
No delete operation is included.

TRANSACTIONAL SAFETY
--------------------
- verifies this package manifest;
- verifies the complete approved preview package;
- verifies the uploaded live exact-preview receipt;
- verifies exact candidate and diff identities;
- verifies locked live FOXAI baselines;
- verifies both Qwen3VL language models and the official projector;
- repeats browser, image-validation, runtime, and Boundary Watch checks;
- asks for the approval phrase only after preflight passes;
- creates and verifies a two-file backup;
- stages both candidates before changing either live file;
- applies server first, then WebUI;
- repeats the complete candidate suite against the live files;
- verifies only the two approved targets changed;
- verifies protected files, projector, and security logs stayed unchanged;
- rolls both files back together after any post-install failure.

SUCCESS
-------
Nothing is considered installed unless the generated receipt says:

    State: applied_verified
    Verified: True

EXPECTED FINAL HASHES
---------------------
    core\foxai_web.py
    3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d

    core\server.py
    238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81
