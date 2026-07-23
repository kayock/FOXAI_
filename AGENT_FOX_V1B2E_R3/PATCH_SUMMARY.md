# Agent Fox V1B-2E R3 — Targeted Replace-Text Repair

Mission: `ENG-20260722-225500-4D0517`

This replacement package fixes the R2 archive lookup defect without broadening scope.

Changes:
1. Remove the standalone `"evidence"` entry from `ENGINEER_TRIGGERS` while preserving `"ranked evidence"` and all explicit/strong engineering routes.
2. Add one idempotence guard before Desktop prepends `[Model: ...]`.

Key packaging corrections:
- Uses `replace_text`, not full-file `write_file`.
- Uses forward-slash relative paths: `core/director.py` and `ui/main_window.py`.
- Contains no source payload archive members; exact old/new text is inline in `PLAN.json`.

The resource provider, shared adapter, integration helpers, contract, fixtures, and WebUI source remain unchanged.
