# KayocktheOS Phase 1 Airlock Patch Bundle

Created: 2026-07-12T01:13:49+00:00

This bundle does **not** modify the uploaded originals. It contains a deterministic preview/apply workflow.

## Phase 1 scope

- Removes bare-word `Engineer` routing while preserving explicit and specific engineering intents.
- Adds caller identity to routing and denies Agent Fox/model actors access to Engineer/Engineering Airlock.
- Adds exact operator approval for Repair Chamber actions: `APPLY <action_id>`.
- Adds verified/requested/failed tool receipts and flags model action claims without receipts.
- Adds shared protected-path exclusions and secret redaction to SmartSearch, Engineer direct search, folder scans, scan-report previews, and Iron Library list/search/preview/index.
- Replaces the giant flat sidebar at runtime with grouped departments, Favorites, Recents, collapsible groups, and Ctrl+K search while preserving every existing page ID and page loader.
- Adds Casbin-compatible Engineering Airlock and Repair Chamber policy files. Casbin remains optional until installed.

## Files changed or added

- `core/director.py`
- `core/agents.py`
- `core/engineer_agent.py`
- `core/smart_search.py`
- `core/foxai_web.py`
- `core/security_containment.py` (new)
- `Config/engineering_airlock_model.conf` (new)
- `Config/engineering_airlock_policy.csv` (new)

The launcher remains unchanged and still starts `core\foxai_web.py`.

## Run order

1. Extract this folder into `Z:\FOXAI` so it sits beside `core`, or pass the FOXAI root to the BAT file.
2. Run `PREVIEW_PHASE1.bat`.
3. Read `preview_output\PHASE1_EXACT.diff` and `preview_output\PREVIEW_RECEIPT.json`.
4. Do not run APPLY until the exact diff is approved.
5. Run `APPLY_PHASE1.bat`; type `APPLY KAYOCK PHASE1` when prompted.

## Safety behavior

- Preview writes only inside this bundle.
- Apply refuses if reviewed baseline hashes changed.
- Apply checks Git only for the reviewed target files. Known unrelated Git anomalies and the extracted bundle are reported as advisories and preserved. Exact baseline hashes remain mandatory.
- Apply creates `Backups\SecurityMilestone\Phase1_<timestamp>` first.
- Python compilation, targeted security tests, and payload hash verification run after copy.
- Any failed post-check triggers restoration of the exact baseline and verifies restored hashes.
- Receipts are written to `Reports\SecurityMilestone`.

## Known Phase 1 boundary

`ProjectIndex`, dependency graph, runtime graph, and other scanners not uploaded for this milestone may have their own traversal rules. Direct Engineer search, SmartSearch, WebUI folder scans, and Iron Library paths are protected here. Those additional scanner modules should be brought under the same shared policy in the next containment increment.


## Fixed Git gate

This corrected bundle does **not** require the entire FOXAI repository to be clean. It blocks only staged or unstaged changes to the exact files Phase 1 will touch, while continuing to require exact SHA-256 baseline matches. Unrelated entries—including the previously known suspicious root BAT filename and untracked patch-bundle files—are displayed but not modified.
