# Expected safety result

A normal completed receipt should report:

```text
state: read_only_probe_complete
read_only: true
apply_capability_present: false
live_files_modified: false
shortcut_changes: false
launcher_changes: false
runtime_changes: false
package_install: false
network_access: false
desktop_gui_launched: false
```

The shortcut contract itself may still report `not_found` or `duplicate_target_matches`. That does not make the diagnostic unsafe; it tells us what must be corrected before Phase 3B can pass.
