# Agent Fox Technical Core V1B-2E R2

Mission: `ENG-20260722-225500-4D0517`

This is a bounded two-file cleanup after successful real-GUI acceptance of the shared historical resource provider.

## Changes

1. `core\director.py`
   - Removes only the standalone `evidence` entry from `ENGINEER_TRIGGERS`.
   - Retains `ranked evidence`, explicit `/engineer` commands, investigation, code review, debugging, and other strong engineering routes.

2. `ui\main_window.py`
   - Adds an idempotence guard before the existing `[Model: ...]` prefix.
   - A model label is added only when the response does not already begin with one.

## Explicit exclusions

No Technical Core adapter/provider/helper is modified. `core\foxai_web.py` is not modified. No model or GUI is launched by validation. No live scan, network use, package installation, service/startup/registry change, or K: access occurs.

Restart FOXAI Desktop after Apply.
