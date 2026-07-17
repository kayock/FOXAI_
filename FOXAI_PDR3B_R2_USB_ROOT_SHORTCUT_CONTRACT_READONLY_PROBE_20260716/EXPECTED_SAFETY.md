# Expected Safety Receipt

The receipt should report:

- `read_only: true`
- `apply_capability_present: false`
- `live_files_modified: false`
- `shortcut_changes: false`
- `launcher_changes: false`
- `runtime_changes: false`
- `package_install: false`
- `network_access: false`
- `desktop_gui_launched: false`
- protected baselines pass before and after
- shortcut/source/icon hashes remain unchanged
- `phase3c_blocked: true`

A missing shortcut is a diagnostic result, not permission to create or replace one.
