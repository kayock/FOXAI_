# Portable Runtime Phase 2B3 — Core Install Exact Preview

## Verified foundation

Phase 2B2 acquired twelve exact wheels from official PyPI storage. Every
wheel passed SHA-256, package identity, version, Python compatibility, and
dependency checks. The isolated staging test imported all twelve packages
from the USB and successfully exercised Psutil, Requests, and Casbin.

## Exact proposed change

The later guarded apply would:

1. Reconstruct `Runtime/Core/site-packages` from the twelve verified wheels.
2. Add a generated `Runtime/Core/CORE_RUNTIME_MANIFEST.json`.
3. Add that USB-owned package folder to embedded Python's `_pth`.
4. Harden the primary WebUI launcher with `PYTHONNOUSERSITE=1` and `-s`.

The standard `site` helper remains enabled, but the primary WebUI process
cannot borrow packages from the Windows user-site folder.

## Explicitly unchanged

- FOXAI WebUI and server source
- Fox Sentry and Engineering Airlock source
- commissioner source
- model profiles and model files
- Desktop launcher and Desktop runtime
- ComfyUI and Torch
- fleet registry and Hanger Bay paths
- alternate shell and Bridge
- historical launchers

## Preview verification

The preview reconstructs the full candidate tree inside `PR2B3/candidate`,
never in the live runtime. It verifies all wheel hashes again, rejects unsafe
ZIP paths and file conflicts, generates a complete file manifest, runs all
isolated imports, exercises Psutil, Requests, and Casbin, and runs the locked
five-test Boundary Watch suite with the candidate Casbin runtime active.
