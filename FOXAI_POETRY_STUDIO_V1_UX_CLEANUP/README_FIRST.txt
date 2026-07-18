FOXAI POETRY STUDIO V1 UX CLEANUP

This is a small follow-up to the completed Poetry Studio v1 build.

TITLE DETECTION

When a poem is pasted directly into Poem Polisher, FOXAI now checks whether the
first non-empty line looks like a short title. For example:

The City Of Sorrows

will be used as the title when saving Original, Polished, or Save Both files,
instead of Untitled_Poem.

FOXAI is deliberately conservative. A long first line or one ending in normal
sentence punctuation remains Untitled Poem until the operator enters a title.

QUIET COMFYUI HEALTH MONITOR

The read-only ComfyUI operations panel still refreshes normally, but its
background health request no longer uses the global toast system. It will not
cover Writer controls with repeated "ComfyUI health endpoint responded" notices.

INSTALLER WARNING

This installer uses PowerShell only to generate the backup timestamp. It avoids
the nested Python command quoting that caused:

'from' is not recognized as an internal or external command

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_POETRY_STUDIO_V1_UX_CLEANUP.bat.
4. Press Y once.
5. Restart WebUI.

Only core\foxai_web.py is replaced after a timestamped backup.

VERIFICATION

Python syntax compilation: passed
Browser JavaScript syntax check with Node: passed

SOURCE SHA-256
Poetry Studio v1 Finish: bffbb665c5ba6a4c0aad7aa6b0a583206650ac77b13082d5f6b5b901ae174928
Updated UX cleanup:       50275afca9c14bab5f33ddc115003fcef654316eeec746a267cc6dbd7bb0a732
