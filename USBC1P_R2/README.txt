FOXAI USB Commissioning Phase 1 — Exact Preview R2

R2 keeps the candidate files byte-for-byte identical to R1.

R1 correctly stopped fail-closed because its verifier tried to load
tests.test_boundary_watch as a package module. The live tests folder is not
a Python package. R2 runs the same locked five tests with unittest discovery.

Extract this USBC1P_R2 folder directly inside the FOXAI root, then run:

  VERIFY_PREVIEW.bat

Expected:
  State: exact_preview_verified
  Verified: True
  Live files modified: False
  Apply capability present: False

This package cannot apply the candidate.
