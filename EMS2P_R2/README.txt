EMS2P — Extension Manager Safe State Controls Phase 2 Exact Preview

EXTRACT
-------
Extract the complete EMS2P folder directly to:

    Z:\FOXAI\EMS2P\

RUN
---
    VERIFY_PREVIEW.bat

EXPECTED
--------
    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Installer apply capability present: False

PROPOSED LIVE SOURCE CHANGE
---------------------------
    core\foxai_web.py

Candidate SHA-256:
    5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548

Exact diff SHA-256:
    86e65fec472f6b5701af24de7e683a81a8340726f1a6fc460feeb0f33a5bdb51

The preview package cannot install the source candidate and never calls the
runtime state-apply endpoint against the live root. It tests actual state
creation, approval, backup, receipt, dependency checks, restore, and rollback
only inside isolated temporary FOXAI roots.

After a later separately approved source apply, an operator-approved extension
state action may create:

    Config\extension_state.json
    Backups\ExtensionState\...
    Reports\ExtensionState\...

No state file is created merely by opening or refreshing the dashboard.
No install, update, removal, or download capability is included.


R2 VERIFIER CORRECTION
----------------------
The candidate and exact diff are unchanged. R2 corrects only the
grounding-index verifier path described in CORRECTION_R2.md.
