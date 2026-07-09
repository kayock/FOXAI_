# Engineering Department

Generated: 2026-07-07T23:59:15

## Purpose

Engineering Department module for Kayock Command OS.

## Ownership

- **Key:** `engineering`
- **Kind:** `department`
- **Version:** `0.1.0`
- **Enabled:** `True`
- **Status:** `VALID`
- **Officer:** Chief Engineer Ada (Ada) — Chief Engineer

## Manifest

`Z:\FOXAI\Departments\Engineering\manifest.json`

## Dependencies

- `foxkernel`
- `missionbus`
- `vault`

## Provides

- `engineering.health`
- `code.format`
- `code.lint`
- `code.typecheck`
- `architecture.inspect`
- `security.audit`
- `sbom.generate`

## Services

- Repair Bay
- Diagnostics
- Build Verification
- Code Review
- Architecture Inspection
- Security Inspection

## Tools

- **ruff** (`ruff`): Fast linting and formatting checks
- **black** (`black`): Python formatting
- **mypy** (`mypy`): Static type checking
- **pydeps** (`pydeps`): Import graph visualization
- **import-linter** (`importlinter`): Architecture boundary enforcement
- **grimp** (`grimp`): Import graph analysis
- **pip-audit** (`pip_audit`): Dependency vulnerability scanning
- **cyclonedx-bom** (`cyclonedx_py`): SBOM generation

## Files

This department currently contains the manifest and Python service files discovered by the Folder Scan Bridge.

## Safety Notes

- Treat department scans as read-only by default.
- Back up manifests before automated changes.
- Keep tool execution behind explicit user approval.
- Prefer report-first workflows before repair actions.

## Next Maintenance Steps

- Keep this README updated when services or tools change.
- Add docstrings to Python modules explaining ownership and purpose.
- Add health-check expectations and example outputs.
- Add tests when the Repair Bay test runner is connected.
