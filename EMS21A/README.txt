EMS21A — Extension Manager Operator Clarity Phase 2.1

Installs only the verified operator-clarity source update.

Adds:
- in-app Quick Cheat Sheet;
- full Operator Manual;
- Safe / Preview / Approval legend;
- Protected labels for system/core records;
- clearer state-file EXISTS / NOT CREATED wording;
- separate inventory and advanced-manifest totals;
- Advanced Manifest Tools collapsed by default.

It does not enable, disable, install, update, remove, or download anything.
It must not create Config\extension_state.json.

Extract to Z:\FOXAI\EMS21A\ and run APPLY.bat after closing FOXAI WebUI, Chat Engine, and benchmark servers.

Exact approval phrase:
APPROVE EXTENSION MANAGER OPERATOR CLARITY PHASE 2.1 APPLY

Allowed live change:
core\foxai_web.py

Expected final SHA-256:
e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525

Success requires:
State: applied_verified
Verified: True
Runtime state created: False
