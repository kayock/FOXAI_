FOXAI Portable Host Model Library Phase 2C1 — Read-Only Audit

Extract PHM2C1 directly inside the FOXAI root:

  Z:\FOXAI\PHM2C1\

First run:

  VERIFY_PACKAGE.bat

Expected:
  State: host_model_audit_package_verified
  Verified: True
  Live files modified: False
  Apply capability present: False

Then run:

  RUN_HOST_MODEL_AUDIT.bat

The audit checks:
- the current model-profile and llama-server launch implementation;
- USB model inventory;
- approved host model inventory under C:\KayockModels;
- the planned Qwen3-30B-A3B host model;
- source labels, fallback, and per-machine profile gaps;
- reusable hooks for future LAN and online providers.

It does not start a model, contact a provider, hash large GGUF files, or
modify source, configuration, launchers, credentials, registries, or models.

Upload report.md and receipt.json from the timestamped folder printed after
the audit:

  Reports\HostModelAudit\PHM2C1_<timestamp>\
