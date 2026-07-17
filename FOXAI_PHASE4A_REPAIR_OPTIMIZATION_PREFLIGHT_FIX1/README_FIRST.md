# FOXAI Phase 4A FIX1 — Repair & Optimization Preflight

This corrected read-only preflight fixes the original host-ComfyUI probe. The original probe inherited `PYTHONNOUSERSITE=1` from the USB controller, even though the proven ComfyUI launcher starts ordinary host Python with user-site packages enabled. That produced a false `torch` failure.

## What it verifies

- Exact known-good FOXAI files, launchers, and both USB-root shortcuts
- Every file in the live Desktop runtime manifest
- USB-owned Desktop Python behavior and required module origins
- Repair Bay structure, bounded Python syntax checks, and test inventory
- Offline `Wheelhouse` integrity and direct-requirement coverage
- USB and HOST PC availability of Git, ripgrep, Gitleaks, Semgrep, KeePassXC, and Sandboxie
- Required and recommended Python modules
- Current host-Python/torch readiness used by the proven ComfyUI launcher
- CPU, RAM, storage, and volume profile
- Model locations and sizes without hashing huge model files

## Readiness states

- `READY`: critical and recommended readiness checks passed.
- `READY_WITH_NOTES`: safe to continue, with missing optional or recommended components.
- `NEEDS_ATTENTION`: at least one critical integrity or runtime requirement failed.

## Safety

The preflight does not repair, install, download, delete, overwrite, launch FOXAI, launch ComfyUI, or recursively scan entire drives. It writes only timestamped evidence inside this package.

## Run

1. Extract the complete folder inside `Z:\FOXAI`.
2. Run `RUN_REPAIR_OPTIMIZATION_PREFLIGHT.bat`.
3. Desktop runtime hash verification may take roughly 20 seconds to several minutes depending on USB speed.
4. Zip and upload only the newest:

```text
FOXAI_PHASE4A_REPAIR_OPTIMIZATION_PREFLIGHT\PREFLIGHT_OUTPUT\<timestamp>\UPLOAD_THIS
```


## FIX1 correction

The host ComfyUI probe now mirrors the working launcher:

- Uses the PATH-resolved host `python.exe`
- Does not use Python `-s`
- Clears `PYTHONHOME` and `PYTHONPATH`
- Removes the controller-only `PYTHONNOUSERSITE=1`
- Disables bytecode writes
- Reports the resolved `torch` origin, user-site path, and effective `sys.path`

No repair or installation capability was added.
