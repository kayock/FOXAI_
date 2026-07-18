FOXAI MY POEMS / LEGACY ARCHIVE v1

PURPOSE

This turns Poetry Studio's saved Markdown files into a calm body-of-work and
voice-legacy archive without changing the poem files themselves.

WHAT APPEARS

A new Kayock Writer navigation item:

My Poems

The page automatically scans:

Z:\FOXAI\Projects\KayockWriter\Poetry\Drafts

FEATURES

1. PAIRED ORIGINAL AND POLISHED VIEW

When Save Both created related versions, My Poems displays the newest Original
and Polished copies side by side.

2. NO-OVERWRITE VERSION HISTORY

Every saved Markdown file remains available in a collapsible version history.
Reading the archive never edits a poem.

3. FIRST ERIC VOICE MILESTONE

"Voices That Carry Home" is recognized as the first official poem created with
the Eric — Poet/Narrator profile when its saved metadata confirms that profile.

4. LEGACY DESIGNATIONS

Each poem may be marked as:

- Legacy Work
- For Akaysha
- For Nevaeh

These settings are stored separately in:

Z:\FOXAI\Projects\KayockWriter\Poetry\Legacy\legacy_manifest.json

They never rewrite the poem Markdown files.

5. VOICE-LEGACY RECORDING SLOTS

Each poem shows three slots:

- Original Reading
- Polished Reading
- Personal Message

"Prepare Recording Folder" creates a dedicated folder only after you press it.
It also creates a README with suggested master filenames and the rule that raw
master recordings remain read-only.

6. AUTHOR AND COPYRIGHT

Future Poetry Studio saves include editable fields for:

- Author
- Copyright notice

The defaults are Eric Z. Fox and Copyright © 2026 by Eric Z. Fox. Existing
poem files are not rewritten to add missing metadata.

INSTALL

1. Close FOXAI WebUI.
2. Extract this whole folder directly inside Z:\FOXAI.
3. Run APPLY_MY_POEMS_LEGACY_ARCHIVE_V1.bat.
4. Press Y once.
5. Restart WebUI.
6. Open Kayock Writer > My Poems.

FILES CHANGED

Replaced after backup:

core\foxai_web.py

No other live file is changed during installation.

USER-CONTROLLED FUTURE WRITES

Only buttons inside My Poems can create:

- a separate legacy_manifest.json sidecar;
- dedicated recording folders and README files.

The source poem Markdown files remain unchanged.

VERIFICATION

Python syntax compilation: passed
Browser JavaScript syntax check with Node: passed
My Poems page marker: passed
Archive loader marker: passed
Archive backend marker: passed
Recording preparation marker: passed
Legacy setting marker: passed
First Eric Voice milestone marker: passed

BASE WEBUI SHA-256

6aa33c3aa7f1aa49a444d38581cb0e89b188b54d07caf6e009ed07df2dedda5d

UPDATED WEBUI SHA-256

146070e53d58fbbd8244343b83b70d693da8361191ea5a0c067c132bc9db51f7
