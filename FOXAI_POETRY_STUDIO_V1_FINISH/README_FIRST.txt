FOXAI POETRY STUDIO V1 FINISH

WHAT THIS COMPLETES

1. REAL TITLES
After creating the poem, the active local writing model performs a tiny second
request that returns a concise title. The title is not copied from line one and
remains editable.

2. SAFE WORKING STATES
Controls that could conflict are disabled during CREATING or POLISHING.
The polished result is cleared before a new polish begins, so a prior or
intermediate version cannot be selected accidentally.

3. CLEAR STATUS
Poetry Studio now reports:
- CREATING
- READY TO EDIT
- POLISHING
- READY TO COMPARE
- SAVING
- SAVED
- SAVED BOTH

4. POLISHING STRENGTH
Focus choices include:
- Light touch
- Balanced polish
- Bold rewrite
- Rhythm and line breaks
- Imagery and emotional impact
- Word choice and clarity
- Preserve voice with minimal changes

5. ORIGINAL AND POLISHED VERSIONS
After polishing, choose:
- Keep Original
- Use Polished Version
- Save Both

Save Both creates two separate Markdown files with matching version-group
metadata. No version overwrites the other.

6. SAFER FILENAMES
Saved poems now include microseconds in the filename. Even two saves made in the
same second remain separate files.

INSTALL

1. Close FOXAI WebUI.
2. Extract this entire folder directly inside Z:\FOXAI.
3. Run APPLY_POETRY_STUDIO_V1_FINISH.bat.
4. Press Y once.
5. Restart WebUI and open Poetry Studio.

Only core\foxai_web.py is replaced, after a timestamped backup.

VERIFICATION

Python syntax compilation: passed
Browser JavaScript syntax check with Node: passed

SOURCE SHA-256

Uploaded current WebUI:
2c9f174273f3db98e5b7eba6c5adf4ffd82b97976419af66512ae6d76db43d18

Updated WebUI:
bffbb665c5ba6a4c0aad7aa6b0a583206650ac77b13082d5f6b5b901ae174928
