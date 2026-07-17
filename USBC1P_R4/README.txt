FOXAI USB Commissioning Phase 1 — Exact Preview R4

R4 keeps the three proposed candidate files byte-for-byte identical to R1, R2, and R3.

R3 correctly stopped fail-closed because its verifier passed literal \n characters to Python -c. R4 uses a semicolon-separated single-line runner.

Extract USBC1P_R4 inside the FOXAI root and run VERIFY_PREVIEW.bat.

Expected:
  State: exact_preview_verified
  Verified: True
  Live files modified: False
  Apply capability present: False

This package cannot apply the candidate.
