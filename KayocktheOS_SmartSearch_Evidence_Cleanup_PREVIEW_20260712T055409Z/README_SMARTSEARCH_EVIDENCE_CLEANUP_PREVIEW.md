# SmartSearch Evidence Cleanup — Preview Only

Engineer is correctly finding live source first, but generated deployment bundles,
backup trees, and old `Memory` source copies are still appearing as implementation
evidence.

## Proposed live change

Only:

`core\smart_search.py`

No apply script is included. No live file is changed by this preview.

## Exact behavior change

- Exclude root `Backup` and `Backups` trees from all SmartSearch layers.
- Exclude root folders beginning `KayocktheOS_` when their names identify an
  apply, preview, patch-bundle, or checkpoint artifact.
- Classify `Memory` as project memory. Python files under `Memory` may still be
  used as historical fallback, but cannot outrank live `core` or `ui` source.
- Preserve vendor fallback, protected-path exclusion, secret redaction, source
  priority, and all current containment behavior.
- Add one disclosure line to reports explaining the generated-artifact exclusion.

A normal folder such as `KayocktheOS_Runtime` remains searchable because it does
not contain a generated-artifact marker.

## Verification already completed

- Current SmartSearch baseline SHA-256:
  `f87ff40820e70067ad562ce1ffb57afcb60a3085dcac176deab4d26c4e427d18`
- Candidate SHA-256:
  `be89cfd7c50e00f33f7fb1b0e46384f861b9d4a38395c5c72e9ba6024b52878c`
- Exact diff SHA-256:
  `c32349b345fc32347877e3d8d39d30d89df49ee5fb20ac9397515e169dbd57b3`
- Candidate compilation: PASS
- Targeted cleanup tests: 7 PASS
- Phase 1 containment regression tests: 15 PASS
- Live FOXAI files changed: NO

## Run the local preview

1. Extract this folder directly inside `Z:\FOXAI`.
2. Run `PREVIEW_SMARTSEARCH_EVIDENCE_CLEANUP.bat`.
3. A valid result must report `State: preview_ready`.
4. The preview writes its receipt only inside this extracted preview folder.

Do not copy the candidate into `core` manually. An apply bundle should be created
only after the preview receipt is reviewed and explicitly approved.
