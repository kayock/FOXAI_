# Agent Fox Technical Core V1A-2

V1A-2 adds a bounded, static-only code and launcher evidence bridge under `System\AgentFoxTechnicalCore`.

It reuses the verified V1A-1 normalized manifest and evidence contract. It does not replace Engineering Workshop, Repair Bay, Agent Fox routing, or the Writer/WebUI.

## Capabilities

- Search indexed source lines with exact paths and line numbers.
- Explain an indexed source or launcher file.
- Find Python functions, classes, methods, imports, assignments, and references without importing the target source.
- Trace BAT, CMD, and PowerShell launcher text through static `SET`, `CALL`, `START`, working-directory, label, `GOTO`, port, Python, and chained-launcher evidence.
- Compare current protected file hashes with V1A-1 known-good hashes.

## Boundaries

- Static evidence is not runtime proof.
- Unresolved batch variables remain unresolved.
- No subprocesses, networking, package installation, model loading, elevation, deletion, renaming, repair, or existing source modification is performed.
- Third-party runtimes, ComfyUI internals, models, personal writing, Library content, archives, backups, snapshots, package folders, and Engineering mission history are excluded from first-party source indexing.
- Search and indexing use explicit file, byte, line-record, result, trace-depth, and output ceilings.
- Secret-like assignment values and matching source lines are redacted.

## Installed files

- `static_code_launcher_bridge_v1.py`
- `STATIC_CODE_LAUNCHER_CONTRACT_V1.json`
- `README_V1A2.md`

Generated indexes are mission-scoped and rebuildable. They are not authoritative unless the Engineering Workshop implementation receipt reports `applied_verified`.
