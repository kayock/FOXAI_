# Kayock Optional Dependency Install Plan

Generated: 2026-07-07T23:54:38

This is a planning document only. No packages were installed.

## Safety Rules

- Install optional tools only after core workflows are stable.
- Prefer the portable Python runtime: `Z:\FOXAI\env\python\python.exe`
- Keep installation commands user-approved.
- Install to the portable environment, not the system Python.
- Export a verification report after installation.

## Suggested Later Install Order

1. `ruff` — fast linting and formatting checks.
2. `black` — Python formatting.
3. `mypy` — static type checking.
4. `pip-audit` — dependency vulnerability scanning.
5. `cyclonedx-bom` — SBOM generation.
6. `pydeps` — import graph visualization.
7. `grimp` — import graph analysis.
8. `import-linter` — architecture boundary enforcement.

## Future User-Approved Command Pattern

```bat
Z:\FOXAI\env\python\python.exe -m pip install ruff black mypy
```

Do not run this automatically. Use a future Repair Bay approved action with confirmation and logging.
