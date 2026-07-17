FOXAI Portable Host Model Library Phase 2C2 — Guarded Apply

Extract PHM2C2_APPLY directly inside the FOXAI root:

  Z:\FOXAI\PHM2C2_APPLY\

Before applying:
  1. Close the FOXAI WebUI server window.
  2. Leave all model files exactly where they are.

First run:

  VERIFY_PACKAGE.bat

Expected:
  State: guarded_apply_package_verified
  Verified: True
  Live files modified: False
  Model files modified: False
  Apply capability present: True

Then run:

  APPLY_PORTABLE_HOST_MODEL_LIBRARY_PHASE2C2.bat

Type exactly:

  APPROVE PORTABLE HOST MODEL LIBRARY PHASE 2C2 APPLY

Exact approved live scope:
  MODIFY core\foxai_web.py
  ADD    core\model_sources.py
  ADD    Config\model_sources.json
  ADD    tests\test_model_sources.py
  DELETE nothing

The apply does not start FOXAI or a model, does not access the Internet,
and never copies, moves, renames, overwrites, or deletes a model file.

On success, upload APPLY_REPORT.md and APPLY_RECEIPT.json from:

  Reports\HostModelApply\PHM2C2_APPLY_<timestamp>\
