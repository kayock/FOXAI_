# FOXAI Portable Desktop Runtime Phase 3B
## Corrected Exact Portable-Runtime Design

- State: **exact_design_verified**
- Verified: **True**
- Read only: **True**
- Elapsed seconds: **2.71**
- Live files modified: **False**
- Desktop or ComfyUI launched: **False**
- Packages installed or downloaded: **False**
- Drive recursion: **False**

## Corrected shortcut contract

### Desktop
- Shortcut: `Z:\Launch FOXAI Workshop.bat - Shortcut.lnk`
- Target: `Z:\FOXAI\Launch FOXAI Workshop.bat`
- Working directory: `Z:\FOXAI`
- Icon: `Z:\FOXAI\Icons\foxai_fixed.ico`
- Contract valid: **True**

### Web
- Shortcut: `Z:\START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk`
- Target: `Z:\FOXAI\START_FOXAI_WEB_PORTABLE.bat`
- Working directory: `Z:\FOXAI`
- Icon: `Z:\FOXAI\Icons\ChatGPT Image Jul 6, 2026, 09_28_59 PM.ico`
- Contract valid: **True**

## Existing launcher facts

- Entry point: `foxai.py`
- Uses bare host `python`: **True**
- Starts ComfyUI: **True**
- The existing stable launcher remains unchanged.

## Dependency closure

- Local Python files: **56**
- External module roots: `PIL, casbin, customtkinter, psutil, requests`
- Special runtime requirement: `tkinter`

## Runtime conclusion

- Embedded USB tkinter available: **False**
- Host tkinter available: **True**

**The Desktop requires its own USB-owned full Windows Python runtime with Tcl/Tk.**
The small embedded Core runtime remains the WebUI/security runtime and its verified shared packages are reused.

## Proposed portable layout

```text
Runtime/Desktop/python/**
Runtime/Desktop/site-packages/**
Runtime/Desktop/DESKTOP_RUNTIME_MANIFEST.json
START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat
START_FOXAI_DESKTOP_PORTABLE.bat
```

## Package split

- Shared Core: `casbin, psutil, requests`
- Desktop direct: `PIL, customtkinter`

## Phase 3C gate

- Design ready for Phase 3C: **True**
- No design blockers found.
- Phase 3C may acquire into quarantine only; no live apply is authorized.

## Safety

- No shortcut, launcher, runtime, source, configuration, model, or package was modified.
- No FOXAI, Desktop UI, ComfyUI process, browser, or network operation was started.
- The only writes are this timestamped report and receipt inside the extracted probe bundle.
