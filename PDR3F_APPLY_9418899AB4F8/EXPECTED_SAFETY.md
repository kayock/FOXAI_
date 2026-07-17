# Phase 3F-A Safety Contract

Authorized:

- Add exactly one approved combined launcher:
  `START_FOXAI_WORKSHOP_PORTABLE.bat`

Prohibited:

- Overwrite or modify any existing file
- Delete any preexisting file
- Change either USB-root shortcut
- Change existing launchers or FOXAI/ComfyUI source
- Install or download packages
- Use network access
- Launch FOXAI, ComfyUI, or a browser
- Run the new launcher during apply

On failure after addition, rollback may remove only the newly created launcher while its hash still matches the approved file.
