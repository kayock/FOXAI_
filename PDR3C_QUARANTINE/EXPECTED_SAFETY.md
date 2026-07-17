# Phase 3C Safety Contract

This package has no live-apply function.

Required receipt fields:

- `read_only_live_foxai: true`
- `recursive_drive_scan: false`
- `apply_capability_present: false`
- `live_files_modified: false`
- `shortcut_changes: false`
- `launcher_changes: false`
- `runtime_live_changes: false`
- `source_changes: false`
- `package_install: false`
- `package_download: false`
- `network_access: false`
- `desktop_gui_launched: false`
- `comfyui_launched: false`
- `phase3d_live_apply_authorized: false`

The only allowed writes are under this bundle's timestamped `Q` directory.
