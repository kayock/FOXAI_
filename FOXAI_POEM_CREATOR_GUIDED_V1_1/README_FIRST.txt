ENGINEERING WORKSHOP — RECOMMENDED INSTALL
==========================================

This package now includes the exact Workshop plan tied to mission:

  ENG-20260720-223229-01ED0C

Because that mission is already staged, use:

  /engineer workshop preview "Z:\FOXAI\FOXAI_POEM_CREATOR_GUIDED_V1_1\POEM_CREATOR_GUIDED_V1_1_EXACT_PLAN.json"

Then copy the exact hashed Apply command returned by Engineer.

Do not use plain "Continue mission..." text; it routes to Agent Fox.

The Workshop will create the targeted snapshot, apply only core\foxai_web.py,
run the approved validations, roll back automatically if a validation fails,
and produce the Workshop receipt.

FOXAI POEM CREATOR — GUIDED V1.1
================================

Purpose
-------
This controlled build continues from the uploaded live known-good
Z:\FOXAI\core\foxai_web.py baseline.

It finishes the next Poem Creator refinement without redesigning or replacing:
- Poetry Studio V1 foundations
- Poem Polisher
- Selected Lines / Stanza Workshop
- Rhyme & Rhythm Coach
- My Poems / Legacy Archive
- Eric — Poet/Narrator and the existing voice profiles
- Kayock Writer V2
- Repair Bay V2.5
- Kayock's Study / The Bibliotheca
- portable runtimes or launchers

What changes
------------
Poem Creator now has a calm layered path:

1. Core idea
   - Theme
   - Emotion
   - Scene or imagery

2. Add personal meaning — optional
   - Speaker or character voice
   - Personal memory or truth
   - Intended audience

3. Advanced craft choices — optional
   - Creative voice profile
   - Poetic form
   - Rhyme preference
   - Rhythm preference
   - Length
   - Canon or established project details
   - Opening line

The backend now:
- treats personal memory and canon as authoritative
- refuses to invent extra biographical or project facts
- treats rhyme and rhythm as preferences rather than rigid rules
- preserves the exact user-provided opening line
- stores the new guidance fields in new Markdown saves
- reopens those fields from later saved poems
- keeps old Markdown files compatible

The screen also explains:
- which guidance came from the writer
- whether the draft was generated, pasted, duplicated, or reopened
- how many selected revisions were explicitly applied
- how many new versions were saved in the current session
- whether a separate original is held in Poem Polisher

Nothing applies or saves itself.

Install
-------
1. Close FOXAI WebUI.
2. Extract this entire folder.
3. Double-click:
      APPLY_POEM_CREATOR_GUIDED_V1_1.bat
4. The installer checks the exact uploaded baseline SHA-256.
5. It creates and verifies a backup.
6. It replaces only:
      Z:\FOXAI\core\foxai_web.py
7. It verifies the installed Python source and writes a receipt.
8. Restart FOXAI WebUI.

Different FOXAI location
------------------------
You may drag a FOXAI root folder or the full foxai_web.py path onto the BAT file,
or run:

  APPLY_POEM_CREATOR_GUIDED_V1_1.bat "D:\FOXAI"

Safety
------
The installer refuses to replace a live file that does not match the uploaded
known-good baseline. That prevents this package from erasing newer work.

The installer does not:
- open, rewrite, move, or delete existing poem Markdown files
- modify the archive manifest
- modify Repair Bay
- modify Bibliotheca
- modify models, runtimes, launchers, or ComfyUI
- use the network

Rollback
--------
Close FOXAI WebUI and double-click:

  ROLLBACK_POEM_CREATOR_GUIDED_V1_1.bat

Rollback is allowed only when the current file still matches this V1.1 payload,
so it will not erase later work.

Quick test
----------
After restart:

1. Open Kayock Writer > Create a Poem.
2. Enter only a Theme and create a poem.
3. Confirm the simple path still works.
4. Open Add personal meaning and test a speaker, memory, or audience.
5. Open Advanced craft choices and test Natural rhyme and spoken cadence.
6. Confirm What belongs to whom updates.
7. Save a draft and confirm a new Markdown file is created.
8. Reopen it from My Poems and confirm the new guidance fields return.

Hashes
------
Uploaded baseline SHA-256:
0b20128bb67aa757e03162612a97b99383b41d0a3ce7a4eb35a493f26bcc1d48

Payload SHA-256:
229d45ac0b7b10182bd4b6a45faf7e09deb8bd56e2da8ed002b8e502d762e086

Scope:
one live file only — core\foxai_web.py
