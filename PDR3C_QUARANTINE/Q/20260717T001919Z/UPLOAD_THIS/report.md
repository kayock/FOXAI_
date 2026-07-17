# FOXAI Portable Desktop Runtime Phase 3C
## Quarantined Acquisition and Verification

- State: **quarantine_acquisition_verified**
- Verified: **True**
- Elapsed seconds: **18.0**
- Read only with respect to live FOXAI: **True**
- Live files modified: **False**
- Network or installation used: **False**
- FOXAI or ComfyUI launched: **False**

## Sources

- Full runtime source: `C:\Users\kayoc\AppData\Local\Python\pythoncore-3.14-64`
- Runtime version: `3.14.6 (tags/v3.14.6:c63aec6, Jun 10 2026, 10:26:10) [MSC v.1944 64 bit (AMD64)]`
- Desktop package source interpreter: `C:\Python314\python.exe`
- Package source user site: `C:\Users\kayoc\AppData\Roaming\Python\Python314\site-packages`

## Acquired quarantine

- Runtime files: **3294**
- Runtime size: **122.4 MiB**
- Desktop package files: **389**

### Desktop distributions

- `customtkinter==6.0.0` — 103 files
- `darkdetect==0.8.0` — 18 files
- `packaging==26.2` — 48 files
- `pillow==12.3.0` — 220 files

## Isolated verification

- executable_inside_quarantine: **True**
- prefix_inside_quarantine: **True**
- base_prefix_inside_quarantine: **True**
- user_site_disabled: **True**
- user_site_absent_from_sys_path: **True**
- all_required_modules_available: **True**
- all_module_origins_correct: **True**
- dependency_closure_compiles: **True**

## Boundary result

- `tkinter` loads from the quarantined full USB-owned Python runtime.
- `customtkinter` and `PIL` load from quarantined Desktop site-packages.
- `casbin`, `psutil`, and `requests` load from verified Runtime/Core site-packages.
- No user-site package path is used by the quarantined runtime.
- All Phase 3B local dependency files compile in memory without writing `.pyc` files.

## Next gate

**Phase 3D may prepare a preview-first live apply package. No live apply is authorized by this receipt.**
