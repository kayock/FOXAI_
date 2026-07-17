# FOXAI Portable Desktop Runtime Phase 3B
## Exact Portable-Runtime Design

- State: **stopped_fail_closed**
- Verified: **False**
- Live files modified: **False**
- Desktop launched: **False**
- Packages installed: **False**
- Network access: **False**

## Protected stable chain

- `Launch FOXAI Workshop.bat - Shortcut.lnk`
- `Launch FOXAI Workshop.bat`
- `foxai.py`
- `Icons\foxai_fixed.ico`

The stable shortcut and launcher remain unchanged.

## Proposed portable layout

```text
Runtime\Desktop\python\
Runtime\Desktop\site-packages\
Runtime\Desktop\DESKTOP_RUNTIME_MANIFEST.json
START_FOXAI_DESKTOP_PORTABLE_DIAGNOSTIC.bat
START_FOXAI_DESKTOP_PORTABLE.bat
```

## Desktop-only packages


## Reusable portable core


## Dependency closure

- Local Python files: **0**
- External module roots:

## Later apply scope

Modified existing files: **None**

Added:

Deleted: **None**

## Verification gates


## Next

**Phase 3C — Quarantined Desktop Runtime Acquisition**

## Failure

- `RuntimeError: Protected shortcut discovery or validation failed: desktop_resolved, desktop_unique_target_match, desktop_target, desktop_working_directory, desktop_icon_is_usb_owned, desktop_icon_exists, web_resolved, web_unique_target_match, web_target, web_working_directory, web_icon_is_usb_owned, web_icon_exists`
