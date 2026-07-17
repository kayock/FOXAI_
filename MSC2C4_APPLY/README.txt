FOXAI Model Status Clarity Phase 2C4 — Guarded Apply

APPROVED LIVE SCOPE

  MODIFIED
    core\foxai_web.py

  ADDED
    None

  DELETED
    None

The display changes from a combined local-runtime label to:

  Engine: RUNNING or STOPPED
  Model source: USB, HOST PC, LAN, or ONLINE PROVIDER
  Network use: NONE, LAN, or INTERNET

No model, registry, source-selection, fallback, security, launcher, or engine
behavior is changed.

Before applying, close the FOXAI WebUI black server window. The apply stops
fail-closed if port 8765 is still open; it does not stop the server itself.

Extract MSC2C4_APPLY directly into:

  Z:\FOXAI\MSC2C4_APPLY\

First run:

  Z:\FOXAI\MSC2C4_APPLY\VERIFY_PACKAGE.bat

Then run:

  Z:\FOXAI\MSC2C4_APPLY\APPLY_MODEL_STATUS_CLARITY_PHASE2C4.bat

Enter exactly:

  APPROVE MODEL STATUS CLARITY PHASE 2C4 APPLY

After completion, upload:

  Reports\ModelStatusClarityApply\MSC2C4_APPLY_<timestamp>\APPLY_REPORT.md
  Reports\ModelStatusClarityApply\MSC2C4_APPLY_<timestamp>\APPLY_RECEIPT.json

Safety:
  - one live file modified;
  - transactional backup and automatic rollback;
  - no automatic launch;
  - no model-server action;
  - no network access;
  - no model or registry changes;
  - no live deletions.
