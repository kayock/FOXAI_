# Kayock Repair Action Detail Viewer

Created: 2026-07-08T14:35:13
Status: **verified**
Action ID: `single_file_rollback`
Action created: 2026-07-08T10:38:01
Action OK: True
Verified state: `passed`
Message: Single-file rollback completed and verified.

## Safety

- Read-only detail viewer.
- No repair action.
- No restore.
- No rollback.
- No overwrite.
- No copy-back.
- No delete.
- No install.
- No model cleanup.

## Log

- JSON: `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.json`
- Markdown: `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.md`

## Target

- Path: `Z:\FOXAI\Departments\Engineering\README.md`
- Exists: True
- Inside root: True
- Size: 1828
- Modified: 2026-07-07T23:59:16
- SHA256: `8b2dc31e222346459024d5f16534158e0d516ed27af2b884d3c153b78af0dd5a`

## Backup

- Path: `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- Exists: True
- Inside root: True
- Size: 1828
- Modified: 2026-07-07T22:52:50
- SHA256: `b2bd4cd4b14c7f0de9816c64252d3cd4e7db1429e4aacd531a740803ee33e2f4`

## Verification

- Recorded: True
- OK: True
- Checked: 10
- Passed: 10
- Failed: 0
- Message: Single-file rollback verification passed: 10/10 check(s) passed.

- PASS `confirmation_phrase_exact` — Exact rollback confirmation phrase matched. 
- PASS `rollback_preview_had_no_hard_blocks` — Rollback preview had no hard blocks except intentional rollback lock. 
- PASS `target_hash_before_matched_preview` — Target hash before rollback matched rollback preview. `Z:\FOXAI\Departments\Engineering\README.md`
- PASS `pre_rollback_current_target_backup_created` — Current target backup before rollback exists. `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- PASS `pre_rollback_backup_hash_matches_current_target` — Pre-rollback backup hash matches current target before rollback. `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- PASS `rollback_source_backup_hash_matches_recorded_old_target` — Rollback source hash matches recorded old target hash. `Z:\FOXAI\Backups\RestoreLiveTargets\PRE_RESTORE_README_20260708_094618.md`
- PASS `rollback_source_backup_hash_matches_recorded_live_backup` — Rollback source hash matches recorded live backup hash. `Z:\FOXAI\Backups\RestoreLiveTargets\PRE_RESTORE_README_20260708_094618.md`
- PASS `target_hash_after_matches_rollback_source` — Target hash after rollback matches pre-restore backup. `Z:\FOXAI\Departments\Engineering\README.md`
- PASS `target_size_after_matches_rollback_source` — Target size after rollback matches pre-restore backup. `Z:\FOXAI\Departments\Engineering\README.md`
- PASS `no_delete_no_install_no_model_cleanup` — Rollback action performed only single-file copy with no delete/install/model cleanup. 

## Detail Checks

- PASS `action_log_json_exists` — RepairActions JSON log exists. `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.json`
- PASS `action_log_json_parsed` — RepairActions JSON log parsed successfully. `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.json`
- PASS `action_log_markdown_exists` — RepairActions Markdown log exists. `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.md`
- PASS `action_reported_ok` — Action reported OK. 
- PASS `user_approved_action` — Action was user-approved. 
- PASS `verification_passed_or_legacy` — Verification passed or this is an older successful legacy log. 
- PASS `target_inside_root_or_empty` — Target path is empty or inside FOXAI root. `Z:\FOXAI\Departments\Engineering\README.md`
- PASS `backup_inside_root_or_empty` — Backup path is empty or inside FOXAI root. `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- PASS `no_detail_side_effects` — Detail viewer performed read-only inspection only. 

## Related Paths

- `rollback_report` — file — exists=True — `Z:\FOXAI\Reports\Backups\RollbackActions\Single_File_Rollback_README_20260708_103801.md`
- `rollback_source_backup` — file — exists=True — `Z:\FOXAI\Backups\RestoreLiveTargets\PRE_RESTORE_README_20260708_094618.md`
- `backup` — file — exists=True — `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- `target` — file — exists=True — `Z:\FOXAI\Departments\Engineering\README.md`