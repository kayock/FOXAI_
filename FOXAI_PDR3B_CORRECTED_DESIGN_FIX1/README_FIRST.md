# FOXAI Portable Desktop Runtime Phase 3B — Corrected Design FIX1

This is the corrected read-only Phase 3B design probe.

It uses the shortcut evidence already confirmed on the USB:

- `Z:\Launch FOXAI Workshop.bat - Shortcut.lnk`
- `Z:\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk`

Unlike the earlier probes, it checks only those two exact shortcut files. It does not enumerate the Start Menu, Desktop, other partitions, or any drive tree.

## What it does

- Revalidates all protected live baseline hashes before and after.
- Resolves the exact two USB-root shortcuts.
- Reads the existing launcher chain without executing it.
- Builds a bounded local Python dependency closure beginning at `foxai.py`.
- Probes the USB embedded Python in isolated mode.
- Probes only the first working host `python` command, with a short timeout, to document Tcl/Tk and currently functioning Desktop-package versions.
- Produces the exact `Runtime\Desktop` design and Phase 3C quarantine scope.

## What it never does

- No recursive drive scan.
- No FOXAI, Desktop UI, ComfyUI, browser, model server, or service launch.
- No package installation or download.
- No shortcut, launcher, runtime, source, configuration, registry, or model change.
- No live apply capability.

## Run

1. Extract this entire folder inside `Z:\FOXAI`.
2. Double-click `RUN_PHASE3B_CORRECTED_DESIGN.bat`.
3. It should normally complete in seconds.
4. Zip the newest timestamped folder under `design_output` and upload it.

Phase 3C remains blocked unless this receipt reports:

- `state: exact_design_verified`
- `verified: true`


## FIX1 correction

The earlier launcher passed `%~dp0` with a trailing backslash inside quotes. Windows interpreted the final backslash as escaping the closing quote, so the Python `--bundle` value ended with a literal quotation mark.

FIX1 passes `%~dp0.` instead. This resolves to the same folder without the quote-parsing ambiguity.

No FOXAI file was changed by the failed run because Python stopped before creating the output directory or beginning the design checks.
