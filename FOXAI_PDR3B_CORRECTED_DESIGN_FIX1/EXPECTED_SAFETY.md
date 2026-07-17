# Expected Safety Contract

The generated receipt must report:

- `read_only: true`
- `recursive_drive_scan: false`
- `apply_capability_present: false`
- `live_files_modified: false`
- `desktop_gui_launched: false`
- `comfyui_launched: false`
- `package_install: false`
- `package_download: false`
- `network_access: false`
- `shortcut_changes: false`
- `launcher_changes: false`
- `runtime_changes: false`
- protected baselines pass before and after

The only permitted writes are timestamped evidence files inside this bundle's `design_output` directory.
