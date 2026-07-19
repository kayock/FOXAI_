FOXAI RHYME & RHYTHM COACH v1

PURPOSE

PsyLLM-8B is good at atmosphere and emotional images, but it is loose with
strict rhyme and meter. The Coach provides a fast local check before asking a
model to revise anything.

WHAT IT DOES

Press:

Check Rhyme & Rhythm

The Coach separates the poem into stanzas and reports:

- an approximate rhyme scheme;
- the final word and rhyme label for each line;
- estimated syllables per line;
- Strong, Partial, or Loose rhyme;
- Steady, Mostly Steady, or Uneven rhythm.

The analysis runs in the browser and does not call the language model.

WORKSHOP TARGETS

Choose:

- Natural rhyme — model chooses
- Couplets — AABB
- Alternating — ABAB
- Monorhyme — AAAA
- Rhythm only — do not force rhyme

Then press Revise This Stanza. The exact stanza is transferred into the already
working Selected Lines / Stanza Workshop. The rest of the poem remains
protected.

HONEST LIMITATION

The Coach uses spelling-based rhyme families and estimated English syllables.
Names, dialect, performance, and irregular pronunciation can differ. Use the
Coach to locate possible trouble; use Eric's ear as the final authority.

NO AUTOMATIC WRITES

The Coach:

- does not edit the poem;
- does not save a file;
- does not start a model;
- does not alter archived versions.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_RHYME_RHYTHM_COACH_V1.bat.
4. Press Y.
5. Restart WebUI.
6. Open Poetry Studio and press Check Rhyme & Rhythm.

Only core\foxai_web.py changes after an automatic backup.

VERIFICATION

Python syntax: passed
Browser JavaScript syntax: passed
Syllable-estimate function: present
Rhyme-family function: present
Stanza-to-Workshop handoff: present
AABB / ABAB / AAAA targets: present
Open Poem Project and Selection Workshop: preserved

BASE SHA-256

f52fcef1a61279c2fa539404dc6a5b04f9913c516e696faa8d9550058008916e

UPDATED SHA-256

4a5d6dfbd98293b4ec8645bf78dd203db33df67cebc0517c5ed1c3e8b6dc815f
