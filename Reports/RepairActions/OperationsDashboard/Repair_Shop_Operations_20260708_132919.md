# Kayock Repair Shop Operations Dashboard

Created: 2026-07-08T13:29:19
Health: **REPAIR SHOP HEALTHY**
Read only: True
Report only: True

## Safety

- Read-only operations dashboard.
- No repair action.
- No restore.
- No rollback.
- No overwrite.
- No copy-back.
- No delete.
- No install.
- No model cleanup.

## Summary

- Repair logs: 10
- Repair OK: 10
- Repair failed: 0
- User-approved actions: 10
- Verification passed: 6
- Verification failed: 0
- Legacy logs without verification: 4
- Available safe actions: 3
- Blocked safe actions: 2
- Generated backups: 7
- Associated backups: 6
- Verified backups: 3
- Backup errors: 0
- Recovery health: HEALTHY — ROLLED BACK
- Recovery chain: rolled_back
- Recovery attention: 0
- Recovery errors: 0
- Latest action: `single_file_rollback`
- Latest action created: 2026-07-08T10:38:01
- Latest backup: `manifest_20260708_000110.json`
- Latest recovery event: `Rollback_Audit_20260708_105608`

## Safe Actions

### BLOCKED: Create Missing Standard Folders

- ID: `create_missing_standard_folders`
- Risk: `low`
- Reason: No standard folders are missing.
- Writes: none

### AVAILABLE: Refresh Root Project Manifest

- ID: `refresh_root_manifest`
- Risk: `low`
- Reason: Available. Existing file will be backed up first.
- Writes: `Z:\FOXAI\manifest.json`

### AVAILABLE: Refresh Engineering README

- ID: `refresh_engineering_readme`
- Risk: `low`
- Reason: Available. Existing README will be backed up first.
- Writes: `Z:\FOXAI\Departments\Engineering\README.md`

### AVAILABLE: Generate Optional Dependency Plan

- ID: `generate_optional_dependency_plan`
- Risk: `low`
- Reason: Available. No installs will run.
- Writes: `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`

### BLOCKED: Move Suspicious Root Launchers

- ID: `move_suspicious_root_launchers`
- Risk: `low`
- Reason: No suspicious root launcher filenames found.
- Writes: none

## Action Types

- `single_file_rollback` — count 1, ok 1, failed 0, verified 1, older logs 0
- `single_file_restore` — count 1, ok 1, failed 0, verified 1, older logs 0
- `restore_staging_copy` — count 1, ok 1, failed 0, verified 1, older logs 0
- `refresh_root_manifest` — count 2, ok 2, failed 0, verified 1, older logs 1
- `refresh_engineering_readme` — count 3, ok 3, failed 0, verified 1, older logs 2
- `generate_optional_dependency_plan` — count 2, ok 2, failed 0, verified 1, older logs 1

## Recent Logs

### 2026-07-08T10:38:01 — single_file_rollback

- OK: True
- Verified state: passed
- Message: Single-file rollback completed and verified.
- Target: `Z:\FOXAI\Departments\Engineering\README.md`
- Backup: `Z:\FOXAI\Backups\RollbackLiveTargets\PRE_ROLLBACK_README_20260708_103801.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_rollback_20260708_103801.md`

### 2026-07-08T09:46:18 — single_file_restore

- OK: True
- Verified state: passed
- Message: Single-file restore completed and verified.
- Target: `Z:\FOXAI\Departments\Engineering\README.md`
- Backup: `Z:\FOXAI\Backups\RestoreLiveTargets\PRE_RESTORE_README_20260708_094618.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_single_file_restore_20260708_094618.md`

### 2026-07-08T08:27:10 — restore_staging_copy

- OK: True
- Verified state: passed
- Message: Restore staging copy prepared safely.
- Target: `Z:\FOXAI\Reports\Backups\RestoreStaging\Stage_README_20260707_235915_20260708_082710\STAGED_COPY_README_20260707_235915.md`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\README_20260707_235915.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_restore_staging_copy_20260708_082710.md`

### 2026-07-08T00:01:10 — refresh_root_manifest

- OK: True
- Verified state: passed
- Message: Root project manifest written safely.
- Target: `Z:\FOXAI\manifest.json`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\manifest_20260708_000110.json`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_refresh_root_manifest_20260708_000110.md`

### 2026-07-07T23:59:15 — refresh_engineering_readme

- OK: True
- Verified state: passed
- Message: Department README written safely.
- Target: `Z:\FOXAI\Departments\Engineering\README.md`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\README_20260707_235915.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_refresh_engineering_readme_20260707_235915.md`

### 2026-07-07T23:54:38 — generate_optional_dependency_plan

- OK: True
- Verified state: passed
- Message: Optional dependency plan written.
- Target: `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\Optional_Dependency_Install_Plan_20260707_235438.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_generate_optional_dependency_plan_20260707_235438.md`

### 2026-07-07T22:54:28 — refresh_root_manifest

- OK: True
- Verified state: not_recorded
- Message: Root project manifest written safely.
- Target: `Z:\FOXAI\manifest.json`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\manifest_20260707_225428.json`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_refresh_root_manifest_20260707_225428.md`

### 2026-07-07T22:52:49 — refresh_engineering_readme

- OK: True
- Verified state: not_recorded
- Message: Department README written safely.
- Target: `Z:\FOXAI\Departments\Engineering\README.md`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\README_20260707_225249.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_refresh_engineering_readme_20260707_225249.md`

### 2026-07-07T22:51:21 — refresh_engineering_readme

- OK: True
- Verified state: not_recorded
- Message: Department README written safely.
- Target: `Z:\FOXAI\Departments\Engineering\README.md`
- Backup: `Z:\FOXAI\Backups\GeneratedFiles\README_20260707_225121.md`
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_refresh_engineering_readme_20260707_225121.md`

### 2026-07-07T22:43:28 — generate_optional_dependency_plan

- OK: True
- Verified state: not_recorded
- Message: Optional dependency plan written.
- Target: `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`
- Backup: ``
- Log: `Z:\FOXAI\Reports\RepairActions\Repair_Action_generate_optional_dependency_plan_20260707_224328.md`
