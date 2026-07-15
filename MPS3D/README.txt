MPS3D — FOXAI Model Profile Selector Runtime Apply

This is the short-path edition of the already verified Phase 3 transactional
apply. It exists only to avoid Windows error:

    0x80010135 — Path too long

INSTALL LOCATION
----------------
Extract the complete MPS3D folder directly here:

    Z:\FOXAI\MPS3D\

Do not open or run files from inside the ZIP preview.

BEFORE RUNNING
--------------
Close FOXAI WebUI, Chat Engine, and benchmark servers.

RUN
---
Double-click:

    APPLY.bat

Exact approval phrase:

    APPLY MODEL PROFILE SELECTOR RUNTIME PHASE 3

Expected success:

    State: applied_verified
    Verified: True
    Changed files: ['core/server.py', 'core/foxai_web.py']
    Delete operations: []
    Rollback performed: False

The approved candidates and exact diffs are byte-for-byte identical to the
verified V4 preview. Only package and output path names were shortened.

Expected live hashes:

    core/foxai_web.py
    b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48

    core/server.py
    9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07


MPS3D correction
----------------
The MPS3A startup wrapper reached Python correctly, but the portable Python
runtime did not include the extracted package folder in `sys.path`. Therefore
the main apply script could not import `phase3_verifier.py`.

MPS3D explicitly inserts its own verified package folder into `sys.path`
before loading the unchanged apply script.

No candidate, exact diff, approval phrase, backup behavior, rollback behavior,
or proposed live file changed.


MPS3D correction
----------------
MPS3B stopped safely because the short-path package renamed the package
manifest to `sums.txt`, while the transactional apply still searched for
`PACKAGE_SHA256SUMS.txt`.

MPS3D changes that one package reference to `sums.txt`.

No candidate, exact diff, approval phrase, backup behavior, rollback behavior,
or proposed live file changed.


MPS3D correction
----------------
MPS3C stopped safely during preflight because the transactional wrapper had not
created the nested JavaScript/backend/server harness-output directories before
the verifier attempted to write into them.

MPS3D explicitly creates every required preflight and postflight harness
directory before invoking the unchanged verifier functions.

No candidate, exact diff, approval phrase, backup behavior, rollback behavior,
or proposed live file changed.
