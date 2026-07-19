# Engineering Department — Workshop V1

Generated from the existing Engineering Department foundation on 2026-07-19.

## Purpose

Provide Kayock Command OS with a guarded implementation path in addition to its
existing read-only code and architecture analysis.

## Ownership

- **Key:** `engineering`
- **Kind:** `department`
- **Version:** `1.0.0`
- **Officer:** Chief Engineer Ada
- **Motto:** “Clarity first. Then automation.”

## Engineering Workshop lifecycle

**Locate live source → inspect exact plan → preview diff → snapshot → apply approved
plan → validate → receipt**

Validation failure automatically restores the snapshot.

## Core V1 guarantees

- Read-only by default.
- One exact plan hash is the approval boundary.
- No delete or rename operations.
- No shell command strings.
- No network access or package installation.
- Runtime documentation, quarantine, backups, archives, snapshots, caches,
  wheelhouses, and receipts are excluded from normal source discovery.
- “Continue” resumes active mission state.
- Receipts use actual file hashes and captured command results.
- The system states a capability limitation rather than simulating implementation.

## Main files

- `workshop.py` — implementation workflow coordinator
- `mission_router.py` — separates search, diagnose, plan, implement, and repair
- `mission_state.py` — active mission continuity
- `source_locator.py` — focused live-source discovery
- `patch_engine.py` — exact plan validation, diff preview, and atomic writes
- `snapshot.py` — targeted ZIP snapshots and restoration
- `validator.py` — approved local command execution without a shell
- `evidence.py` — hashes, timestamps, and JSON evidence
- `cli.py` — command-line entry point
- `tests/test_workshop.py` — harmless fixture validation
- `WORKSHOP_GUIDE.md` — operator and integration guide

## Existing optional engineering tools

Ruff, Black, mypy, pydeps, import-linter, grimp, pip-audit, and CycloneDX remain
optional. Workshop V1 itself uses the Python standard library and does not require
them.

## Important integration note

The uploaded folder did not contain the live FOXAI Mission Director, WebUI backend,
or Engineer controller. This package creates the real Workshop worker and CLI, but
it does not falsely claim that the existing read-only Engineer screen is already
connected to it. That integration needs the live controller/server files.
