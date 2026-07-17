# FOXAI Portable Core Runtime Phase 2B3 — Apply Report

- Created: `2026-07-16T18:40:49.377823+00:00`
- State: **rolled_back_fail_closed**
- Verified: **False**
- Approval verified: **True**
- Backup: `Z:\FOXAI\Backups\SecurityMilestone\PR2B3_20260716T184049Z`
- Automatic launch: **False**
- Network access: **False**
- Deletes: **None**

## Approved transaction

- Add `Runtime/Core/site-packages` from 12 verified wheels.
- Add `Runtime/Core/CORE_RUNTIME_MANIFEST.json`.
- Update `env/python/python314._pth`.
- Update `START_FOXAI_WEB_PORTABLE.bat`.

## Verification

- Candidate preflight: **True**
- Candidate Boundary Watch: **True**
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

- `RuntimeError: Post-apply file verification failed.`
