FOXAI POEM SELECTION / STANZA WORKSHOP v1

PURPOSE

Improve only the lines that need help without asking the model to rewrite an
entire poem you already like.

HOW TO USE IT

1. Open Poetry Studio.
2. Highlight one or more lines in Your Poem.
3. Press Revise Selection / Stanza.

When no text is highlighted, FOXAI captures the stanza containing the cursor.

4. Choose what should improve:
   - Keep meaning, improve the lines
   - Stronger imagery
   - Smoother rhyme and rhythm
   - More emotional impact
   - Clearer wording
   - Make it stranger and more memorable
   - Preserve voice with minimal changes

5. Add optional direction.
6. Press Create 3 Alternatives.
7. Edit any alternative if desired.
8. Press Use This Alternative beneath the preferred choice.

SAFETY AND VERSION BEHAVIOR

- Nothing changes while alternatives are generated.
- Only the captured character range can be replaced.
- If the poem changes after capture, FOXAI refuses to apply a choice until the
  passage is captured again.
- Applying a choice does not save over any existing file.
- Save Draft creates a separate new Markdown file as before.
- The current Eric — Poet/Narrator voice and strength are passed into the
  workshop.
- Protected source poems remain unchanged.

COMFYUI BAR CLEANUP

The collapsed ComfyUI Operations dock is narrower and the page has additional
bottom space, reducing overlap with My Poems and other lower content. Expanding
the dock still provides the full operations panel.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_POEM_SELECTION_WORKSHOP_V1.bat.
4. Press Y once.
5. Restart WebUI and open Poetry Studio.

FILES CHANGED

Replaced after backup:

core\foxai_web.py

VERIFICATION

Python syntax compilation: passed
Browser JavaScript syntax check with Node: passed
Workshop panel marker: passed
Selection capture marker: passed
Three-choice request marker: passed
Selection-only replacement marker: passed
Revision endpoint marker: passed
Compact ComfyUI dock marker: passed

BASE WEBUI SHA-256

146070e53d58fbbd8244343b83b70d693da8361191ea5a0c067c132bc9db51f7

UPDATED WEBUI SHA-256

1cb27e896424a095bb97450f1a077c24c5b36c88fa462ff5c3ee1895c03bfff3
