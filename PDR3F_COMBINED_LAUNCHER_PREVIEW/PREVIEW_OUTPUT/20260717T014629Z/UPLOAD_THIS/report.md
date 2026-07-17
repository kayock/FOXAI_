# FOXAI Portable Desktop Runtime Phase 3F-P
## Combined Portable Workshop Launcher Preview

- State: **combined_launcher_preview_verified_ready_for_operator_review**
- Verified: **True**
- Elapsed seconds: **0.12**
- Preview only: **True**
- Live files modified: **False**
- Shortcuts changed: **False**
- FOXAI launched: **False**
- ComfyUI launched: **False**

## Proposed new file

- Destination: `Z:\FOXAI\START_FOXAI_WORKSHOP_PORTABLE.bat`
- Status: **ADD**
- Size: **2346 bytes**
- SHA-256: `1e6b4bb53b81ba53c88fb6d88bf91f35ac5f730744e3ebd7329c6ec79af6728f`

## Preserved startup behavior

- Verifies the USB-owned Desktop runtime before starting services.
- Starts ComfyUI first with the existing proven host command: `python.exe main.py --cpu`.
- Clears portable Python variables from the ComfyUI process.
- Waits eight seconds.
- Starts FOXAI through the already-verified portable Desktop launcher.
- Leaves the existing shortcut and both existing launchers unchanged.

## Host-Python observation

- Resolved `python.exe`: `C:\Python314\python.exe`

## Approval

- Plan ID: `9418899ab4f89bc9445589015422b8015220c0040bb77c63e864ca7ccdc95dc6`
- Exact approval phrase: **`APPROVE PDR3F 9418899AB4F8`**

**No apply capability is included.**
