# SmartSearch Root Staging Cleanup — Preview Only

The first cleanup worked for named `KayocktheOS_*` bundles and backup trees, but
the extracted installer also left generic root staging folders:

- `candidate`
- `payload`
- `baseline`

Because those names do not contain the `KayocktheOS_*` artifact marker, they
still appeared in both desktop and WebUI Engineer results.

## Proposed correction

Only `core\smart_search.py`.

The candidate adds those three evidenced root staging directories to the existing
generated-artifact exclusion set. Nested filenames such as
`Projects\Example\candidate_notes.md` remain searchable.

## Hashes

- Current live baseline:
  `be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c`
- Candidate:
  `f9b6d67557d0038725c8b05f293f303e639c95f57c73df260ea012d6e44c4efd`
- Exact diff:
  `ca5aa9c1edb1805760862de3ec1a47bb47f41ae82fd47541e3f4d80166f015c6`

## Verification

- Candidate compile: PASS
- Targeted root-staging tests: 8 PASS
- Phase 1 containment tests: 15 PASS
- Apply script included: NO
- Live files modified: NO

## Run

Extract this folder directly inside `Z:\FOXAI` and run:

`PREVIEW_SMARTSEARCH_ROOT_STAGING_CLEANUP.bat`

Upload the receipt from the generated `preview_output` folder. Do not manually
copy the candidate into `core`.
