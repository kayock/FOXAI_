FOXAI ERIC VOICE — EXACT LIVE FIX

DIAGNOSIS

The uploaded live core\foxai_web.py contained the Poetry Studio v1 UX cleanup,
but did not contain:

- the Eric — Poet/Narrator dropdown option;
- the voice-strength control;
- the protected source profile;
- Creator or Polisher voice-profile handling.

This proves the missing option was not caused by browser caching. The previous
preset installer did not replace the live WebUI file.

THIS FIX

This package was built directly from that uploaded live file.

It changes only:

core\foxai_web.py

The complete verified profile is embedded directly in foxai_web.py, avoiding a
second module or import.

INSTALL

1. Close FOXAI WebUI.
2. Extract this folder directly inside Z:\FOXAI.
3. Run APPLY_ERIC_VOICE_EXACT_LIVE_FIX.bat.
4. Press Y.
5. Restart WebUI.

The dropdown will show:

My natural voice
Eric — Poet/Narrator
Lyrical
...

Selecting Eric — Poet/Narrator reveals:

Light Influence
Recognizably Eric
Strong Eric Voice

VERIFICATION

Python syntax compilation: passed
Browser JavaScript syntax check: passed
Dropdown marker: verified
Strength control marker: verified
Protected profile marker: verified
Creator profile handling: verified
Polisher profile handling: verified

SOURCE SHA-256
50275afca9c14bab5f33ddc115003fcef654316eeec746a267cc6dbd7bb0a732

UPDATED SHA-256
6aa33c3aa7f1aa49a444d38581cb0e89b188b54d07caf6e009ed07df2dedda5d
