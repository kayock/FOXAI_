# SmartSearch Root Staging Cleanup — Apply Bundle

This bundle is based on the locally verified preview receipt created at
`2026-07-12T14:27:05+00:00`.

## Scope

Only:

`core\smart_search.py`

## Correction

The first SmartSearch cleanup correctly excluded named KayocktheOS deployment
bundles and backup trees. This correction also excludes the evidenced generic
root staging directories:

- `candidate`
- `payload`
- `baseline`

Only root folders with those exact names are excluded. Nested legitimate files
such as `Projects\Example\candidate_notes.md` remain searchable.

## Reviewed hashes

- Baseline: `be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c`
- Candidate: `f9b6d67557d0038725c8b05f293f303e639c95f57c73df260ea012d6e44c4efd`
- Exact diff: `ca5aa9c1edb1805760862de3ec1a47bb47f41ae82fd47541e3f4d80166f015c6`

## Safety sequence

1. Confirm the live baseline hash.
2. Confirm the candidate and exact-diff hashes.
3. Confirm the verified preview receipt.
4. Require WebUI and chat-engine service ports to be closed.
5. Require the exact operator approval phrase.
6. Create and verify a backup.
7. Compile the candidate.
8. Run 8 targeted root-staging tests.
9. Run 15 Phase 1 containment regression tests.
10. Install atomically.
11. Compile the live file.
12. Run a real live-root SmartSearch smoke test.
13. Restore the exact baseline automatically if a post-backup check fails.

Exact approval phrase:

`APPLY SMARTSEARCH ROOT STAGING CLEANUP`

## Run

1. Extract this folder directly inside `Z:\FOXAI`.
2. Close the desktop Mission Console, WebUI, and chat-engine console.
3. Run `APPLY_SMARTSEARCH_ROOT_STAGING_CLEANUP.bat`.
4. Type the exact approval phrase shown above.
5. Upload the receipt generated under `Reports\SecurityMilestone`.

Do not manually copy the candidate into `core`.
