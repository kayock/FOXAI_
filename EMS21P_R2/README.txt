EMS21P — Extension Manager Operator Clarity Phase 2.1 Exact Preview

Extract the complete EMS21P folder directly to:

    Z:\FOXAI\EMS21P\

Run:

    VERIFY_PREVIEW.bat

Expected:

    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Apply capability present: False

This preview proposes only core\foxai_web.py. It cannot apply the source change and cannot alter extension state.


R2 PORTABILITY CORRECTION
-------------------------
The Phase 2.1 candidate and exact diff are unchanged.
R2 removes the verifier's dependency on the Unix `patch` command and
reconstructs the candidate from the unified diff using pure Python.
