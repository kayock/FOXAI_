FOXAI POEM SELECTION SCOPE FIX

OBSERVED FAILURE

The workshop correctly captured one stanza, but PsyLLM returned most of the
entire poem as Alternative 1. Using that choice would have inserted the large
answer into the selected location and duplicated poem content.

CAUSE

The small model received:

- up to 1,200 characters of context on each side;
- the complete four-poem Eric voice profile;
- the selected stanza.

That made the local editing task look too much like a whole-poem rewrite.

FIX

The workshop now:

1. Sends only the nearest two nonblank lines before and after the selection.
2. Uses a compact Eric voice fingerprint rather than all four source poems.
3. Specifies the exact permitted line-count range.
4. Uses a smaller response budget suited to three short alternatives.
5. Rejects alternatives that:
   - are much longer than the selected passage;
   - contain too many lines;
   - repeat protected context lines;
   - simply return the unchanged selection.

A rejected whole-poem answer never appears as a usable choice and never changes
the poem.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_POEM_SELECTION_SCOPE_FIX.bat.
4. Press Y.
5. Restart WebUI.
6. Capture and revise the same stanza again.

Only core\foxai_web.py changes after an automatic backup.

VERIFICATION

Python syntax: passed
Browser JavaScript syntax: passed
Whole-poem rejection regression: passed
Valid four-line alternative acceptance: passed
Compact Eric workshop guide: present
My Poems and prompt metadata: preserved

SOURCE SHA-256

9028dcc24c26fdc4e3fe447fc27541e57f1bcb471a5721f8ec8c2a0cf6f5a86f

UPDATED SHA-256

85da2781eeeba69786ff4aa91dcfdc88d5e94997ad727a89a1a177d3e4f46cf8
