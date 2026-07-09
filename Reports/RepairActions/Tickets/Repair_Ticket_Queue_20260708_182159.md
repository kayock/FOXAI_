# Kayock Repair Ticket Queue

Created: 2026-07-08T18:21:59
Health: **REPAIR TICKET QUEUE HEALTHY**
Read only: True
Report only: True

## Safety

- Read-only ticket queue.
- No repair action.
- No restore.
- No rollback.
- No overwrite.
- No copy-back.
- No delete.
- No install.
- No model cleanup.

## Summary

- tickets: 10
- active_tickets: 4
- open_tickets: 0
- available_action_tickets: 2
- informational_tickets: 2
- healthy_tickets: 6
- critical: 0
- high: 0
- medium: 0
- low: 2
- info: 2
- healthy: 6
- errors: 0
- repair_shop_health: REPAIR SHOP HEALTHY
- recovery_health: HEALTHY — ROLLED BACK
- latest_repair_action: single_file_rollback
- latest_recovery_event: Rollback_Audit_20260708_105608

## Tickets

### [LOW / available_action] Optional Repair Bay tools are not fully installed

- ID: `optional_repair_tools_missing`
- Source: Env Verify
- Risk: `low`
- Summary: 8 optional Repair Bay tool(s) appear missing. This is not a blocker.
- Suggested action: Generate the optional dependency plan; do not auto-install packages.
- Safe action ID: `generate_optional_dependency_plan`

Evidence:
- Optional tools available: 0/8
- Optional tools are advisory only.

### [LOW / available_action] Safe Repair Shop actions are available

- ID: `safe_actions_available`
- Source: Repair Shop
- Risk: `low`
- Summary: 3 safe action(s) are currently available.
- Suggested action: Use Repair Actions page only when you intentionally want to run one.
- Safe action ID: ``

Evidence:
- Blocked actions: 2
- All listed actions still require explicit approval.

### [INFO / informational] Unassociated backup files exist

- ID: `unassociated_backups`
- Source: Backup Vault
- Risk: `low`
- Summary: 1 backup file(s) are not linked to a verified action log.
- Suggested action: Leave as historical unless later cleanup/migration is built.
- Safe action ID: ``

Evidence:
- Backups: 7
- Verified backups: 3

### [INFO / informational] Legacy RepairActions logs without verification

- ID: `legacy_repair_logs`
- Source: Repair History
- Risk: `low`
- Summary: 4 older successful log(s) predate verified-action logging.
- Suggested action: Leave as historical unless a later migration tool is built.
- Safe action ID: ``

Evidence:
- Repair logs: 10
- These are historical, not failures.

### [HEALTHY / clear] Build verification clear

- ID: `build_verify_clear`
- Source: Build Verify
- Risk: `low`
- Summary: Build verification currently reports no problems.
- Suggested action: No action needed.
- Safe action ID: ``

Evidence:
- Checks: 7
- Passed: 7

### [HEALTHY / clear] Required environment checks clear

- ID: `env_required_clear`
- Source: Env Verify
- Risk: `low`
- Summary: Required environment checks currently report no problems.
- Suggested action: No required action needed.
- Safe action ID: ``

Evidence:
- Checks: 10
- Passed: 9

### [HEALTHY / clear] No true model duplicates detected

- ID: `model_duplicates_clear`
- Source: Model Check
- Risk: `low`
- Summary: Model Check currently reports no true duplicate GGUF model files.
- Suggested action: No action needed.
- Safe action ID: ``

Evidence:
- Physical model files: 6
- Unique model keys: 6

### [HEALTHY / clear] Portable readiness clear

- ID: `portable_ready_clear`
- Source: Portable Ready
- Risk: `low`
- Summary: Portable readiness currently reports no blockers or warnings.
- Suggested action: No action needed.
- Safe action ID: ``

Evidence:
- Score: 100
- Blockers: 0
- Warnings: 0

### [HEALTHY / clear] Recovery Foundation healthy

- ID: `recovery_clear`
- Source: Recovery Foundation
- Risk: `low`
- Summary: Recovery Foundation reports HEALTHY — ROLLED BACK.
- Suggested action: No action needed.
- Safe action ID: ``

Evidence:
- Current chain: rolled_back
- Events: 14

### [HEALTHY / clear] Latest Scan Bridge report has no parsed problems

- ID: `latest_scan_clear`
- Source: Scan Bridge
- Risk: `low`
- Summary: Latest scan report did not expose parsed problems in its summary.
- Suggested action: No action needed from ticket queue.
- Safe action ID: ``

Evidence:
- Report: Z:\FOXAI\Reports\Scans\Folder_Scan_Departments_20260707_201456.json
- Files: 
- Warnings: 0
