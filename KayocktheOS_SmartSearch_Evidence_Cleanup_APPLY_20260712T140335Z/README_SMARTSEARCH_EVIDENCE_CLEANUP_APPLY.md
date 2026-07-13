# SmartSearch Evidence Cleanup — Approved Apply Bundle

This bundle is based on the locally verified preview receipt dated
`2026-07-12T13:53:33+00:00`.

## Scope

Only:

`core\smart_search.py`

## Application behavior

- Excludes root `Backup` and `Backups` trees.
- Excludes generated `KayocktheOS_*` apply, preview, patch-bundle, and
  checkpoint folders.
- Treats `Memory` as project-memory fallback instead of executable source.
- Preserves vendor fallback, secret redaction, protected-path exclusion, and
  source-priority behavior.
- Adds a visible report line disclosing generated-artifact exclusion.

## Reviewed hashes

- Baseline: `f87ff40820e70067ad562ce1ffb57afcb60a3085dcac176deab4d26c4e427d18`
- Candidate: `be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c`
- Exact diff: `c32349b345fc32347877e3d8d39d30d89df49ee5fb20ac9397515e169dbd57b3`

## Safety

The installer:

1. Requires the live baseline hash to match.
2. Requires the desktop, chat engine, and WebUI to be closed.
3. Requires the exact operator approval phrase.
4. Creates and verifies a backup.
5. Compiles the candidate.
6. Runs 7 targeted cleanup tests.
7. Runs 15 Phase 1 containment regression tests.
8. Installs atomically.
9. Compiles the live file.
10. Runs a real live-root SmartSearch smoke test.
11. Automatically restores the exact baseline if any post-backup check fails.

Exact approval phrase:

`APPLY SMARTSEARCH EVIDENCE CLEANUP`

## Run

1. Extract this folder directly inside `Z:\FOXAI`.
2. Close the desktop Mission Console, WebUI window, and chat-engine console.
3. Run `APPLY_SMARTSEARCH_EVIDENCE_CLEANUP.bat`.
4. Type the exact approval phrase.
5. Upload the generated receipt from `Reports\SecurityMilestone`.

Do not copy the candidate into `core` manually.
