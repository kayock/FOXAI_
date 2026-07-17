# USB C2 Patch Preview Safety Contract

Allowed:

- Verify the captured source hashes and module-origin evidence
- Generate exact proposed copies of two commissioning files
- Generate an exact unified diff, plan ID, and approval phrase
- Parse the proposed Python source for syntax

Forbidden:

- Modify live FOXAI files
- Install, download, or repair packages
- Create ComfyUI folders
- Launch FOXAI, WebUI, Desktop, ComfyUI, browser, or models
- Change shortcuts, configuration, models, runtime files, or unrelated launchers
- Apply the patch


## FIX1 clarification

The corrected proposal removes only the unconditional overall-status penalty
from an unused external `.venv`. The warning remains active when that `.venv`
is actually selected as the Desktop runtime. No apply or launch capability was
added.


## FIX2 verifier correction

Only the preview verifier's expected live/proposed hashes were corrected.
No apply, install, repair, launch, or additional write capability was added.
