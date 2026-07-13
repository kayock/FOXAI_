# KayocktheOS Portable Python Compatibility — Apply Bundle

## Approved scope

This bundle changes only:

`core\foxai_web.py`

Reviewed baseline SHA-256:

`5feb632c5d44d260dba706019beeacf2f5e210ab5a495b9ede3fbe287a6b899e`

Reviewed candidate SHA-256:

`4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43`

The exact reviewed diff is included as:

`PORTABLE_PYTHON_COMPATIBILITY_EXACT.diff`

## Before running

Close the temporary Command Prompt currently keeping the working test server online.

The apply tool deliberately refuses to continue while anything responds at:

`http://127.0.0.1:8765/`

It will not kill an existing FOXAI process automatically.

## Run

Extract the entire bundle into its own folder inside `Z:\FOXAI`, then run:

`APPLY_PORTABLE_PYTHON_FIX.bat`

Type exactly:

`APPLY PORTABLE PYTHON FIX`

## Automated safeguards

The command:

1. detects the FOXAI root by reviewed hashes;
2. verifies the bundle, live baseline, candidate, and containment-module hashes;
3. refuses to proceed if port 8765 is already active;
4. creates and verifies a timestamped backup;
5. installs only the reviewed candidate;
6. compiles the live file using portable Python;
7. reruns all 15 Phase 1 security tests;
8. launches the live WebUI using portable Python;
9. requires HTTP 200 plus the `Welcome back, Commander.` and `Search Ctrl+K` markers;
10. stops the temporary verification server;
11. verifies the final live SHA-256;
12. writes a detailed receipt;
13. automatically restores the backup if a required check fails.

Successful receipts are written under:

`Z:\FOXAI\Reports\SecurityMilestone\PortablePythonFix_Apply_Receipt_*.json`

Backups are written under:

`Z:\FOXAI\Backups\SecurityMilestone\PortablePythonFix_*`

## After success

Run your normal:

`START_FOXAI_WEB.bat`

The launcher itself is not changed by this bundle. Correcting its premature “running” message with a real HTTP readiness check should be handled as a separate reviewed change.

## Manual rollback

`ROLLBACK_PORTABLE_PYTHON_FIX.bat` is included, but do not use it unless the verified compatibility change later needs to be removed.


## Corrected HTTP verification

The first apply bundle produced a false negative. The server actually returned:

- HTTP 200
- the `Welcome back, Commander.` marker
- 718,848 bytes of WebUI HTML

The old verifier looked for the literal contiguous text `Search Ctrl+K`. In the real source,
`Search` and `Ctrl+K` are separated by a `<span>` element and are therefore not contiguous
in raw HTML.

This corrected verifier requires all three actual raw-source navigation markers:

- `openCommandPalette()`
- `Ctrl+K`
- `navsearch`

The reviewed live source patch is unchanged.
