# Kayock Repair Ticket Detail Viewer

Created: 2026-07-08T18:39:02
Status: **available_action**
Ticket ID: `optional_repair_tools_missing`
Title: Optional Repair Bay tools are not fully installed
Source: Env Verify
Severity: `low`
Ticket status: `available_action`
Read only: True
Report only: True

## Safety

- Read-only ticket detail viewer.
- No repair action.
- No restore.
- No rollback.
- No overwrite.
- No copy-back.
- No delete.
- No install.
- No model cleanup.

## Summary

8 optional Repair Bay tool(s) appear missing. This is not a blocker.

## Evidence

- Optional tools available: 0/8
- Optional tools are advisory only.

## Suggested Action

Generate the optional dependency plan; do not auto-install packages.

## Matching Safe Action

- ID: `generate_optional_dependency_plan`
- Title: Generate Optional Dependency Plan
- Available: True
- Requires confirmation: True
- Risk: `low`
- Reason: Available. No installs will run.
- Writes: `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`

## Detail Checks

- PASS `ticket_selected` — Ticket was selected from current Repair Ticket Queue. 
- PASS `ticket_queue_loaded` — Repair Ticket Queue loaded. 
- PASS `ticket_queue_read_only` — Ticket Queue is read-only/report-only. 
- PASS `source_declared` — Ticket source is declared. `Env Verify`
- PASS `severity_declared` — Ticket severity is declared. `low`
- PASS `safe_action_resolved_or_not_required` — Safe action is either not required or resolved from Repair Shop action list. `generate_optional_dependency_plan`
- PASS `safe_action_requires_confirmation_or_not_required` — Matching safe action still requires explicit confirmation. `generate_optional_dependency_plan`
- PASS `no_ticket_detail_side_effects` — Ticket detail viewer performed read-only inspection only. 

## Related Paths

- `source_folder` — folder — exists=True — `Z:\FOXAI\Reports\Environment`
- `repair_reports` — folder — exists=True — `Z:\FOXAI\Reports\RepairActions`
- `optional_dependency_plan` — file — exists=True — `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`