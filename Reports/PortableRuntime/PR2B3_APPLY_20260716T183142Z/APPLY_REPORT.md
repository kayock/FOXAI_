# FOXAI Portable Core Runtime Phase 2B3 — Apply Report

- Created: `2026-07-16T18:31:43.122982+00:00`
- State: **stopped_fail_closed**
- Verified: **False**
- Approval verified: **True**
- Backup: `Z:\FOXAI\Backups\SecurityMilestone\PR2B3_20260716T183142Z`
- Automatic launch: **False**
- Network access: **False**
- Deletes: **None**

## Applied

- Added `Runtime/Core/site-packages` from 12 verified wheels.
- Added `Runtime/Core/CORE_RUNTIME_MANIFEST.json`.
- Updated `env/python/python314._pth`.
- Updated `START_FOXAI_WEB_PORTABLE.bat`.

## Verification

- Candidate preflight: **False**
- Candidate Boundary Watch: **False**
- Live file verification: **False**
- Live portable imports: **False**
- Live Boundary Watch: **False**
- No-write commissioning: **False**

## Safety

No source, model, fleet registry, Desktop runtime, ComfyUI runtime,
alternate shell, or Bridge file was changed. On a failed verification,
the attempted Runtime/Core tree is moved into the backup and both
modified files are restored.

## Failure

- `RuntimeError: Runtime manifest hash mismatch: 8827ce801b082732d20c65ea2b2afa88dbcebd97cc95d0cad470c649bd3d35bb`
