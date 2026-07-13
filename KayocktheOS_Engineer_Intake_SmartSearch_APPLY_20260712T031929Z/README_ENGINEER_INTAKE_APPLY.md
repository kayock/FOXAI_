# Engineer Intake & SmartSearch Repair — Apply Bundle

## Scope

This bundle changes only:

`core\engineer_agent.py`

Reviewed baseline SHA-256:

`bf32b0ab80b6cc3a177698101a5c2121a4224d0bf55bbe78c047f541fb3a6339`

Reviewed candidate SHA-256:

`a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a`

Engineer remains read-only. This bundle does not grant file-write permission,
Repair Chamber authority, or autonomous approval.

## Before running

Close the FOXAI desktop UI and WebUI. The repaired Python module will not be
loaded by an already-running desktop process.

Extract this entire bundle into its own folder inside `Z:\FOXAI`.

## Apply

Run:

`APPLY_ENGINEER_INTAKE_REPAIR.bat`

Type exactly:

`APPLY ENGINEER INTAKE REPAIR`

## Safeguards and verification

The deterministic apply command:

1. detects `Z:\FOXAI` by reviewed file hashes;
2. verifies the bundled baseline and candidate;
3. refuses unknown live-file versions;
4. creates and hash-verifies a timestamped backup;
5. atomically installs only the reviewed candidate;
6. compiles the live file using FOXAI portable Python;
7. runs 8 targeted intake/target-parsing tests against the live file;
8. reruns all 15 Phase 1 security regression tests;
9. runs a live SmartSearch functional test requiring:
   - query normalization to `COMFY_MAIN`;
   - executable/source evidence;
   - a match in `core/foxai_web.py`;
   - no `.venv` or `site-packages` leakage;
10. verifies the final live SHA-256;
11. writes a detailed receipt;
12. automatically restores the exact backup if a required check fails.

Successful receipt location:

`Z:\FOXAI\Reports\SecurityMilestone\EngineerIntake_Apply_Receipt_*.json`

Backup location:

`Z:\FOXAI\Backups\SecurityMilestone\EngineerIntake_*`

## After success

Restart the FOXAI desktop UI and test:

`/engineer smart search for COMFY_MAIN`

The report should show:

- `Query: COMFY_MAIN`
- `Scope: Executable/source evidence`
- `core/foxai_web.py`

Then test:

`/engineer smart search for "launch(pycmd()"`

## Rollback

A manual rollback command is included but should only be used if the verified
repair later needs to be removed:

`ROLLBACK_ENGINEER_INTAKE_REPAIR.bat`
