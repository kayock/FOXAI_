# FOXAI USB C3B
## Exact Isolated Dependency Closure Plan

- State: **plan_complete_ready_for_exact_review**
- Verified: **True**
- Root: `Z:\FOXAI`
- Portable Python: `Z:\FOXAI\Runtime\Desktop\python\python.exe`
- Preferred isolated target: `Z:\FOXAI\Runtime\ComfyUI\site-packages`
- Target existed before/after: **False / False**
- Classification: **C3B_READY_FOR_EXACT_WHEEL_ACQUISITION_REVIEW**
- Exact package count: **96**
- Exact compressed wheel bytes: **718175632**
- Metadata requests: **97**
- Metadata bytes retrieved: **4330753**
- Wheel payloads retrieved: **False**
- Live runtime/ComfyUI files modified: **False**
- Install/download/copy/launcher change/launch: **False**

## Blocking findings

- None detected by this planning run.

## Important findings

- Pinned 36 direct ComfyUI dependencies to the exact C3A-verified host versions.
- Resolved and independently verified 96 exact packages and 118 active dependency edges.
- Every selected artifact is a compatible Windows CPython 3.14 wheel from files.pythonhosted.org with an exact SHA-256 and size.
- Only PyPI JSON metadata was retrieved; no wheel payload was fetched and the isolated target was not created.
- Transitive packages that could not reuse the host version were resolved to the latest compatible wheel: setuptools.

## Next gate

- Upload the newest C3B PLAN_OUTPUT folder for exact review before any wheel acquisition, target creation, install, launcher change, or ComfyUI launch.
