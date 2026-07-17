FOXAI Portable Runtime Phase 2B3 — Core Install Exact Preview

Extract PR2B3 directly inside the FOXAI root:

  Z:\FOXAI\PR2B3\

Run:

  VERIFY_PREVIEW.bat

Expected:
  State: exact_preview_verified
  Verified: True
  Live files modified: False
  Apply capability present: False

The verifier reconstructs the candidate runtime only under PR2B3\candidate.
It never writes to Runtime\Core, env\python, or the live launcher.
