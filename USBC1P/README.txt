USBC1P — FOXAI USB Commissioning Phase 1 Exact Preview

Extract the complete USBC1P folder directly inside the live FOXAI root:

    Z:\FOXAI\USBC1P\

Run:

    VERIFY_PREVIEW.bat

The verifier is read-only. It does not install the commissioner and does not write a commissioning report. It verifies live baseline identities, candidate hashes and compilation, a live `--no-write` commissioning pass, and Boundary Watch.

Expected final lines:

    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Apply capability present: False
