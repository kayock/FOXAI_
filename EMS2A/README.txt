EMS2A — Extension Manager Safe State Controls Phase 2

This package installs the verified Phase 2 source code only.

It does NOT enable, disable, or restore any extension.
It does NOT create Config\extension_state.json.
It does NOT create ExtensionState backup or report folders.
Those actions remain separately previewed and operator-approved inside FOXAI.

EXTRACT
-------
Extract the complete folder directly to:

    Z:\FOXAI\EMS2A\

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
    APPROVE EXTENSION MANAGER SAFE STATE CONTROLS PHASE 2 APPLY

ALLOWED LIVE SOURCE SCOPE
-------------------------
    core\foxai_web.py

EXPLICITLY UNCHANGED
--------------------
    core\server.py
    Config\application_registry.json
    Config\fleet_registry.json
    core\service_registry.py

RUNTIME STATE MUST REMAIN UNCHANGED
-----------------------------------
    Config\extension_state.json
    Backups\ExtensionState\
    Reports\ExtensionState\

No delete operation is included.

TRANSACTIONAL SAFETY
--------------------
- verifies this package manifest;
- verifies the complete approved R2 preview;
- verifies the successful live R2 receipt;
- verifies exact baseline, candidate, and diff identities;
- verifies all locked source, registries, manifests, and security files;
- runs embedded JavaScript through node --check;
- runs browser preview/apply/Why-panel behavior tests;
- runs backend wrong-phrase, dependency, required-extension,
  restore-default, expiration, receipt, malformed-state, and rollback tests;
- runs a live read-only inventory/state preview;
- confirms extension_state.json remains absent;
- runs Boundary Watch 5/5;
- creates and verifies a source backup after explicit approval;
- installs through staged atomic replacement;
- repeats the full suite against the live installed source;
- verifies only core\foxai_web.py changed;
- verifies all extension runtime state paths remained unchanged;
- automatically rolls the source file back after any post-install failure.

SUCCESS
-------
Nothing is considered installed unless the generated receipt says:

    State: applied_verified
    Verified: True
    Runtime state created: False

EXPECTED FINAL HASH
-------------------
    core\foxai_web.py
    5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548
