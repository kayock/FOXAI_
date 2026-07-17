FOXAI Portable Host Model Library Phase 2C2 R2 — Exact Preview

Extract PHM2C2 directly inside the FOXAI root:

  Z:\FOXAI\PHM2C2_R2\

First run:

  VERIFY_PACKAGE.bat

Expected:
  State: exact_preview_package_verified
  Verified: True
  Apply capability present: False
  Live files modified: False

Then run:

  RUN_EXACT_PREVIEW.bat

Expected:
  State: exact_preview_verified
  Verified: True
  Apply capability present: False
  Live files modified: False
  Model files modified: False

Upload report.md and receipt.json from:

  Reports\HostModelPreview\PHM2C2_<timestamp>\

This package has no apply capability. It proposes one modified source file and
three new files. It deletes nothing, starts no model, contacts no provider,
and never changes a GGUF file.

R2 correction:
  R1 relied on PYTHONPATH, which the bundled python314._pth isolated runtime
  ignores. R2 inserts the candidate folder directly into sys.path.

The four proposed live files and their hashes are unchanged.
Do not rerun the R1 exact preview.
