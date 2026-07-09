# Kayock Ticket-to-Approved-Action Bridge

Created: 2026-07-08T18:50:50
Bridge status: **READY — MANUAL APPROVAL REQUIRED**
Ticket: `optional_repair_tools_missing` — Optional Repair Bay tools are not fully installed
Source: Env Verify
Severity: low
Ticket status: available_action

## Safety

- Read-only bridge.
- No repair action.
- No restore.
- No rollback.
- No overwrite.
- No copy-back.
- No delete.
- No install.
- No model cleanup.

## Ticket Summary

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

## Manual Next Steps

- Open Repair Actions.
- Build Repair Action Plan.
- Review action ID: generate_optional_dependency_plan.
- Only click Apply This Action if you intentionally approve it.
- Browser confirmation and backend confirmation are still required.

## Bridge Checks

- PASS `ticket_detail_loaded` — Ticket detail loaded. `optional_repair_tools_missing`
- PASS `repair_action_plan_loaded` — Repair Actions plan loaded. 
- PASS `bridge_is_read_only` — Bridge generated context only and ran no repair action. 
- PASS `safe_action_resolved_when_declared` — Declared safe action was resolved from current Repair Actions plan, if one was declared. `generate_optional_dependency_plan`
- PASS `manual_confirmation_required_when_action_exists` — Matching safe action still requires explicit confirmation. `generate_optional_dependency_plan`
- PASS `no_auto_apply` — Bridge did not call /api/repair/actions/apply and did not write target files. 
- PASS `no_install_no_delete_no_model_cleanup` — Bridge performed no install, delete, or model cleanup. 

## Related Paths

- `source_folder` — folder — exists=True — `Z:\FOXAI\Reports\Environment`
- `repair_reports` — folder — exists=True — `Z:\FOXAI\Reports\RepairActions`
- `optional_dependency_plan` — file — exists=True — `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`
- `repair_actions_page` — internal — exists=False — `internal:repairactions`
- `ticket_detail_page` — internal — exists=False — `internal:repairticketdetail`
- `ticket_queue_page` — internal — exists=False — `internal:repairtickets`
- `repair_reports` — folder — exists=True — `Z:\FOXAI\Reports\RepairActions`
- `ticket_bridge_reports` — path — exists=False — `Z:\FOXAI\Reports\RepairActions\TicketBridges`