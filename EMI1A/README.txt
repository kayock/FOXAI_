EMI1A — Extension Manager Inventory & Health Phase 1

EXTRACT
-------
Extract the complete folder directly to:

    Z:\FOXAI\EMI1A\

Do not run it from inside the ZIP preview.

BEFORE RUNNING
--------------
Close:

- FOXAI WebUI;
- Chat Engine;
- vision benchmark servers;
- other benchmark servers.

RUN
---
    APPLY.bat

EXACT APPROVAL PHRASE
---------------------
    APPROVE EXTENSION MANAGER INVENTORY HEALTH PHASE 1 APPLY

ALLOWED LIVE SCOPE
------------------
    core\foxai_web.py

EXPLICITLY UNCHANGED
--------------------
    core\server.py
    Config\application_registry.json
    Config\fleet_registry.json
    core\service_registry.py
    Config\extension_state.json remains absent

No delete operation is included.

TRANSACTIONAL SAFETY
--------------------
- verifies this package manifest;
- verifies the complete approved exact preview;
- verifies the uploaded live exact-preview receipt;
- verifies exact baseline, candidate, and diff identities;
- verifies registries, service registry, server, manifests, and security files;
- runs every embedded JavaScript block through node --check;
- runs browser filter, projector, read-only, action, and handoff tests;
- runs nested-manifest and backend inventory regression tests;
- performs a live read-only inventory before and after installation;
- verifies projector files remain outside the language-model list;
- verifies extension_state.json is not created;
- verifies legacy extension controls stayed byte-for-byte unchanged;
- runs Boundary Watch 5/5;
- creates and verifies a backup after explicit approval;
- installs through staged atomic replacement;
- verifies only core\foxai_web.py changed;
- automatically rolls back on any post-install failure.

SUCCESS
-------
Nothing is considered installed unless the generated receipt says:

    State: applied_verified
    Verified: True

EXPECTED FINAL HASH
-------------------
    core\foxai_web.py
    ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0
