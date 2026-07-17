MIA1P — FOXAI Mission Image Attachments Phase 1 Exact Preview

STATE
-----
Preview only. No apply or install capability is included.

EXTRACT
-------
Extract the complete MIA1P folder directly to:

    Z:\FOXAI\MIA1P\

Do not run it from inside the ZIP preview.

RUN
---
    VERIFY_PREVIEW.bat

EXPECTED VERIFIED RESULT
------------------------
    State: exact_preview_verified
    Verified: True
    Live files modified: False
    Apply capability present: False

PROPOSED LIVE SCOPE
-------------------
    core\foxai_web.py
    core\server.py

No deletion is proposed.

FEATURES IN THE CANDIDATE
-------------------------
- Drag-and-drop and file-picker image attachment.
- One PNG, JPEG, or WebP at a time.
- 6 MB image limit and 9 MB JSON request limit.
- Browser thumbnail, dimensions, size, and SHA-256 preview.
- Server verification of base64, size, SHA-256, actual byte format,
  actual dimensions, and declared metadata.
- Explicit Fast Vision or Quality Vision requirement.
- No automatic model start, restart, or silent switching.
- Verified official Qwen3VL Q8 projector on vision-profile startup.
- Projector-aware shared runtime identity and conflict checks.
- Guarded streaming and cancellation preserved for image prompts.
- A canceled or failed generation retains the pending image for retry.
- The pending image clears only after a verified successful answer.
- Engineer image inspection remains disabled.
- Mission Archive stores image metadata and SHA-256, never base64 bytes.
- A newer attached image compacts older image payloads out of chat history.
- Projector GGUF files no longer appear as selectable language models.
- Fast Vision and Quality Vision evidence labels reflect the passed
  real-image benchmark.

VERIFIER CHECKS
---------------
- Package manifest.
- Locked live FOXAI hashes.
- Official projector SHA-256 and Qwen3VL model sizes.
- Exact candidate and exact-diff hashes.
- Exact diff reconstruction.
- Baseline and candidate Python compile.
- Every embedded JavaScript block through node --check.
- Browser image-send, no-silent-switch, cancellation, and success behavior.
- PNG, JPEG, and WebP byte/MIME/dimension verification.
- SHA-256, size, and metadata rejection paths.
- No base64 in Mission Archive metadata or receipts.
- Projector filtering from the model selector.
- Backend-owned vision profile/runtime contract.
- Projector-aware llama-server command and process identity.
- Boundary Watch 5/5.
- Protected files and security logs unchanged.

The later transactional apply will require a new explicit approval phrase.
Running this preview does not authorize an apply.
