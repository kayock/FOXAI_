# FOXAI Model Profile Selector + Verified Runtime — Apply Report

- State: **applied_verified**
- Verified: **True**
- Operator approved: **True**
- Changed files: **['core/server.py', 'core/foxai_web.py']**
- Delete operations: **[]**
- Rollback performed: **False**
- Live files modified: **True**

## Backup

- Location: `Z:\FOXAI\Backups\SecurityMilestone\MPS3_20260715T142805Z`
- Verified: **True**

## Final hashes

- `core/foxai_web.py`: `b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48`
- `core/server.py`: `9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07`

## Locked behavior

- Profile-card selection remains pending-only.
- Starting remains an explicit operator action.
- Text profiles use reasoning off with budget 0.
- Vision profiles preserve current engine reasoning behavior.
- Raw exact-GGUF fallback remains.
- Chat Timing, claim guard, Mission Archive, receipts, Navigation Focus, accordion behavior, and Fox Sentry remain verified.
