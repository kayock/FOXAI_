FOXAI OPEN POEM PROJECT v1

WHAT IT ADDS

My Poems now provides:

- Open Original
- Open Polished
- Duplicate as New Poem
- Open on every individual version-history row

OPENING A SAVED POEM

A saved version restores:

- poem text
- title
- author
- copyright notice
- theme
- emotion
- scene / imagery
- voice
- Eric voice strength
- form
- length
- optional opening line
- model record
- source-file lineage

The poem opens as an editable working copy in Poetry Studio.

NO OVERWRITE

Opening does not modify the archived Markdown file.

Pressing Save Draft always creates a new Markdown file. That new file records
the filename it was reopened from, providing visible project lineage.

DUPLICATE AS NEW POEM

Duplicate loads the poem and fields but gives it a new working title ending in:

— New Work

It does not attach source lineage, so it begins a separate poem path.

FULL PROMPT AND FIELD SAVES

Future Markdown saves now include:

- theme
- emotion
- imagery
- voice
- voice strength
- form
- length
- opening line
- author
- copyright
- complete prompt_fields JSON snapshot
- reopened source filename and mode when applicable

Older poem files remain readable. Fields that were not recorded in older saves
will simply reopen blank rather than being invented.

MY POEMS DISPLAY

Each poem detail now has a collapsible:

Saved Prompt & Creation Fields

This shows the recorded brief without changing the poem.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_OPEN_POEM_PROJECT_V1.bat.
4. Press Y.
5. Restart WebUI.
6. Open Kayock Writer > My Poems.

Only core\foxai_web.py changes after an automatic backup.

VERIFICATION

Python syntax: passed
Browser JavaScript syntax: passed
Open Original workflow: present
Open Polished workflow: present
Duplicate workflow: present
Version-history Open buttons: present
Full creator-field save: present
Source-lineage save: present
My Poems, Eric Voice, and Selection Workshop: preserved

BASE SHA-256

85da2781eeeba69786ff4aa91dcfdc88d5e94997ad727a89a1a177d3e4f46cf8

UPDATED SHA-256

f52fcef1a61279c2fa539404dc6a5b04f9913c516e696faa8d9550058008916e
