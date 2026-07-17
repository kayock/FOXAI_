# FOXAI Mission Image Attachments — Phase 1 Exact Preview

## State

- State: **exact_preview_ready**
- Verified local build: **True**
- Live files modified: **False**
- Apply capability present: **False**
- Proposed files: `core/foxai_web.py`, `core/server.py`
- Delete operations: **none**

## Operator experience

The Mission Console gains a visible image drop area, **Attach Image** button,
thumbnail, filename, type, dimensions, size, SHA-256, and **Remove Image**.

The operator must explicitly start either:

- 👁️ **Fast Vision**
- 🔎 **Quality Vision**

Selecting a card still changes only the pending choice. Attaching an image does
not start, stop, restart, or silently switch a model.

## Runtime contract

Vision profiles pin the verified official projector:

`mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf`

SHA-256:

`c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd`

`core/server.py` adds the projector to the shared runtime identity, state,
launch command, compatibility checks, conflict details, and safe process
verification. Existing positional callers remain compatible because the new
optional argument is appended after the existing public parameters.

## Image safety and privacy

The browser and server enforce one PNG, JPEG, or WebP image, no larger than
6 MB and no larger than 8192×8192 pixels. The backend independently validates:

- data-URL structure;
- base64 decoding;
- actual byte size;
- SHA-256;
- actual PNG/JPEG/WebP signature;
- actual image dimensions;
- declared MIME and dimension agreement.

The multimodal data URL is sent only to the local model request. Mission
Archive and receipts retain the prompt plus image filename, MIME, dimensions,
size, and SHA-256—not the base64 image.

The latest successful image remains available to the active vision model for
follow-up questions. Attaching a newer image compacts older image payloads to a
text marker so conversation memory does not grow without bound.

## Guarded streaming

Image prompts use the existing sentence/newline-level guarded stream. The
complete answer is still claim-guarded before archive and canonical final
display. Cancellation still archives no partial assistant answer and now
keeps the pending image available for retry.

## Deliberate boundaries

- Engineer image inspection is not enabled.
- Raw/unverified GGUF selection cannot submit an image.
- Text profiles cannot submit an image.
- There is no automatic profile selection.
- The preview does not apply either candidate.

## Local build verification

- Both candidates compile.
- Embedded JavaScript passes `node --check`.
- Browser multimodal behavior harness passes.
- PNG, JPEG, and WebP helper harness passes.
- Projector runtime identity harness passes.
- Model selector filters projector files.
- Boundary Watch passes 5/5.
