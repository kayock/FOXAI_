FOXAI USB Commissioning Phase 1 — Exact Preview R3

R3 keeps all three proposed candidate files byte-for-byte identical to R1
and R2.

R2 correctly stopped fail-closed because the bundled embeddable Python uses
python314._pth isolation. Its current-directory entry refers to env\python,
not to Z:\FOXAI, so the test process could not import core.

R3 runs the same locked five Boundary Watch tests in a separate bundled-Python
process and explicitly inserts the resolved FOXAI root into sys.path first.

Extract USBC1P_R3 directly inside the FOXAI root and run:

  VERIFY_PREVIEW.bat

Expected:
  State: exact_preview_verified
  Verified: True
  Live files modified: False
  Apply capability present: False

This preview package cannot apply the candidate.
