# Kayock Repair Bay Action Plan

Created: 2026-07-15T16:26:40
Read only: True
Report only: True

## Summary

- Actions: 5
- Available: 3
- Blocked: 2
- Low risk: 5

## Safety Rules

- No action runs without explicit user confirmation.
- Actions are applied one at a time.
- Backups are created before overwriting generated files.
- Every action writes a repair log.
- No model deletion.
- No dependency installation.

## Actions

### BLOCKED: Create Missing Standard Folders

- ID: `create_missing_standard_folders`
- Risk: `low`
- Available: `False`
- Reason: No standard folders are missing.

Creates safe standard Kayock folders that are missing. It does not delete, move, or overwrite files.

Writes:
- none

### AVAILABLE: Refresh Root Project Manifest

- ID: `refresh_root_manifest`
- Risk: `low`
- Available: `True`
- Reason: Available. Existing file will be backed up first.

Regenerates Z:\FOXAI\manifest.json from current module and scan state. Existing manifest is backed up before overwrite.

Writes:
- `Z:\FOXAI\manifest.json`

### AVAILABLE: Refresh Engineering README

- ID: `refresh_engineering_readme`
- Risk: `low`
- Available: `True`
- Reason: Available. Existing README will be backed up first.

Regenerates the Engineering README from the Engineering manifest. Existing README is backed up before overwrite.

Writes:
- `Z:\FOXAI\Departments\Engineering\README.md`

### AVAILABLE: Generate Optional Dependency Plan

- ID: `generate_optional_dependency_plan`
- Risk: `low`
- Available: `True`
- Reason: Available. No installs will run.

Writes a report-only plan for optional Repair Bay tools. It does not install packages.

Writes:
- `Z:\FOXAI\Reports\RepairActions\Optional_Dependency_Install_Plan.md`

### BLOCKED: Move Suspicious Root Launchers

- ID: `move_suspicious_root_launchers`
- Risk: `low`
- Available: `False`
- Reason: No suspicious root launcher filenames found.

Moves suspicious root BAT/CMD files into LegacyLaunchers with safer names. No deletion.

Writes:
- none
