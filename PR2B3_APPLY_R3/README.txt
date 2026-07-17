FOXAI Portable Core Runtime Phase 2B3 — Guarded Apply R2

The operator explicitly approved:

  APPROVE PORTABLE CORE RUNTIME PHASE 2B3 APPLY

Extract PR2B3_APPLY directly inside the FOXAI root:

  Z:\FOXAI\PR2B3_APPLY\

First run:

  VERIFY_PACKAGE.bat

Expected:
  State: apply_package_verified
  Verified: True
  Live files modified: False

Then run:

  APPLY_PORTABLE_CORE_RUNTIME.bat

Type the exact approval phrase when prompted:

  APPROVE PORTABLE CORE RUNTIME PHASE 2B3 APPLY

The apply:
- reconstructs the exact 329-file runtime from the verified USB wheels;
- backs up both modified files;
- adds Runtime/Core atomically;
- disables host user-site use in the primary launcher;
- verifies all imports and functional tests;
- runs all five Boundary Watch tests;
- runs USB commissioning in no-write mode;
- never starts FOXAI automatically.

Upload APPLY_REPORT.md and APPLY_RECEIPT.json from the timestamped report
folder printed after the run.

R2 correction:
  The R1 candidate manifest was written with Windows CRLF line endings,
  changing only its byte hash. R2 writes the exact verified UTF-8/LF bytes.
  The live change scope and approval phrase are unchanged.

Use a fresh folder named:
  Z:\FOXAI\PR2B3_APPLY_R3\

R3 correction:
  R2 passed candidate imports and Boundary Watch but generated
  138 Python cache files before the live move.
  R3 suppresses bytecode creation during every verification step,
  rechecks the candidate immediately before the transaction, and
  verifies the 329 wheel-owned files separately from cache files.

R2 rollback:
  State: rolled_back_fail_closed
  Original _pth restored: yes
  Original launcher restored: yes
  Attempted Runtime/Core preserved in backup: yes

The approved live scope and approval phrase are unchanged.
