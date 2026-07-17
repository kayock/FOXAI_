# FOXAI Portable Desktop Runtime Phase 3D-P FIX1
## Preview-First Exact Live Apply Plan

- State: **preview_verified_ready_for_operator_review**
- Verified: **True**
- Elapsed seconds: **2.22**
- Live apply performed: **False**
- Live files modified: **False**
- Apply capability present: **False**

## Verified Phase 3C source

- Quarantine run: `20260717T001919Z`
- Stable source files hash-verified: **3517**
- Ephemeral bytecode cache files excluded: **166**
- Runtime files: **3294**
- Desktop package files: **223**

## Exact proposed additions

- Total planned files: **3520**
- New files to add: **3520**
- Files already matching: **0**
- Conflicts: **0**
- New bytes: **145156301**
- Free bytes on USB: **804337483776**

### New live paths

- `Runtime\Desktop\python\**`
- `Runtime\Desktop\site-packages\**`
- `Runtime\Desktop\DESKTOP_RUNTIME_MANIFEST.json`
- `System\PortableRuntime\verify_desktop_runtime.py`
- `START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat`

### Explicitly unchanged

- Both USB-root shortcuts
- `Launch FOXAI Workshop.bat`
- `START_FOXAI_WEB_PORTABLE.bat`
- `foxai.py`
- `ui\main_window.py`
- `Runtime\Core\**`
- ComfyUI, Models, Config, source, and protected baselines

## Bytecode cache policy

- `__pycache__`, `.pyc`, and `.pyo` files are not part of the portable runtime.
- The diagnostic and future portable launcher set `PYTHONDONTWRITEBYTECODE=1`.

## Deferred

- The normal `START_FOXAI_DESKTOP_PORTABLE.bat` launcher is not part of this apply plan.
- FOXAI will not be launched during Phase 3D apply.
- The diagnostic must pass before a normal portable launcher is considered.

## Approval

- Plan ID: `7123a2a06aa7fa0451151dc0689bb2730e11b2ff7c1d6edc18fe438ab0210424`
- Exact approval phrase: **`APPROVE PDR3D 7123A2A06AA7`**

**No apply package is included. Review and approve this exact plan before Phase 3D-A is created.**
