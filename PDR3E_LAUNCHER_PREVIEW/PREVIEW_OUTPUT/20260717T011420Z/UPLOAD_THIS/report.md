# FOXAI Portable Desktop Runtime Phase 3E-P
## Separate Portable Launcher Preview

- State: **launcher_preview_verified_ready_for_operator_review**
- Verified: **True**
- Elapsed seconds: **0.1**
- Preview only: **True**
- Live files modified: **False**
- FOXAI launched: **False**
- ComfyUI launched: **False**

## Exact proposed addition

- Destination: `Z:\FOXAI\START_FOXAI_DESKTOP_PORTABLE.bat`
- Status: **ADD**
- Size: **1020 bytes**
- SHA-256: `89e906d805f99392b4ecc2ea85aa688577517a26e577de3542159a1f5eaf046c`

## Launcher behavior

- Uses only `Runtime\Desktop\python\python.exe`.
- Runs the existing portable-runtime verifier before FOXAI.
- Stops without launching FOXAI if verification fails.
- Launches `foxai.py` directly.
- Does not start ComfyUI.
- Does not use host Python or user-site packages.

## Explicitly unchanged

- Both USB-root shortcuts
- `Launch FOXAI Workshop.bat`
- `START_FOXAI_WEB_PORTABLE.bat`
- FOXAI source and protected baselines

## Approval

- Plan ID: `f7b8ef66eebbd5d7e960da9a0019e828ed2b0908fa2ce4d06cd6de30a19bd808`
- Exact approval phrase: **`APPROVE PDR3E F7B8EF66EEBB`**

**No apply package is included.**
