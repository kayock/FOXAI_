FOXAI POEM SELECTION MATCH FIX

WHAT WAS WRONG

The browser captured the selected passage and its exact character positions
correctly.

The Python endpoint then used the general Writer text helper, which calls
strip(). That could remove leading or trailing whitespace before validating the
browser positions. The poem had not changed, but the position check could still
fail with:

The captured passage no longer matches the poem.

WHAT CHANGED

- Poem and selected-passage text now preserve exact whitespace during position
  validation.
- A safe recovery handles harmless whitespace differences at the captured
  edges.
- The backend returns its verified positions to the browser before displaying
  alternatives.
- The strict protection against replacing the wrong passage remains active.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_POEM_SELECTION_MATCH_FIX.bat.
4. Press Y.
5. Restart WebUI.
6. Repeat the same selected-stanza test.

Only core\foxai_web.py changes after an automatic backup.

PRESERVED FEATURES

- Eric — Poet/Narrator
- Strong Eric Voice
- Copyright and author fields
- My Poems / Legacy Archive
- Selected Lines / Stanza Workshop
- Compact ComfyUI dock
- no-overwrite poem saves

VERIFICATION

Python syntax: passed
Browser JavaScript syntax: passed
Whitespace-position regression test: passed
Exact selection helper: present
Verified position synchronization: present

SOURCE SHA-256

1cb27e896424a095bb97450f1a077c24c5b36c88fa462ff5c3ee1895c03bfff3

UPDATED SHA-256

9028dcc24c26fdc4e3fe447fc27541e57f1bcb471a5721f8ec8c2a0cf6f5a86f
