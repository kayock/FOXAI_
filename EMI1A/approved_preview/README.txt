EMI1P — FOXAI Extension Manager Inventory & Health Dashboard

STATE
-----
Exact preview only. No apply or installation capability is included.

EXTRACT
-------
Extract the complete EMI1P folder directly to:

    Z:\FOXAI\EMI1P\

RUN
---
    VERIFY_PREVIEW.bat

EXPECTED RESULT
---------------
    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Apply capability present: False

PROPOSED LIVE SCOPE
-------------------
    core\foxai_web.py

Explicitly unchanged:

    core\server.py
    Config\application_registry.json
    Config\fleet_registry.json
    core\service_registry.py
    Config\extension_state.json

No delete operation is proposed.

ABOUT extension_state.json
--------------------------
It is normal for this file not to exist. The current FOXAI shell creates it
only after an explicit enable/disable action. The Phase 1 inventory reads
manifest defaults and never creates the file.

PHASE 1 FEATURES
----------------
- Read-only inventory dashboard inside Extension Manager.
- Statuses: VERIFIED, INSTALLED, MISSING, NEEDS ATTENTION.
- Required versus optional components.
- Exact path, version, size, modified time, source, and health basis.
- Canonical application-registry inventory.
- Passive fleet-registry inventory.
- Recursive department/extension manifest discovery.
- Declared Python-tool availability checks.
- Chat-model and Creative Studio model metadata.
- Vision projector classified separately and excluded from language models.
- Search and category/status/requirement filters.
- Safe Open Folder controls.
- Backend-allowlisted launch controls only.
- Mission Console handoff with preview-first wording.
- Existing manifest controls preserved unchanged and clearly separated.

PHASE 1 DOES NOT
----------------
- install anything;
- remove anything;
- update anything;
- create extension_state.json;
- alter enabled states;
- rewrite registries or manifests;
- hash every multi-gigabyte model during routine refresh;
- silently launch applications.

The later apply stage requires a separate exact approval phrase.
Running this preview does not authorize an apply.
