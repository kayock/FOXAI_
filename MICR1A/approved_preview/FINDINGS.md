# Mission Image Continuity + Payload Leakage Repair

## Root cause

The applied image-attachment implementation retained the multimodal
`image_url` data URL inside the shared conversation-history list. Each later
turn could therefore carry older image strings forward.

The follow-up path also relied on the older image inside history. The local
Qwen3VL/llama-server path is more reliable when the current image is attached
to the **current user turn**, so Agent Fox could answer from its previous text
description instead of re-inspecting the pixels.

## Exact repair

The candidate changes only `core/foxai_web.py`.

- One current image is held in volatile server memory.
- The shared conversation history is compacted to text and metadata only.
- A vision follow-up reattaches exactly one current image to the current user
  message.
- The browser sends raw image data only for the initial/new attachment.
- After verified acceptance, browser state retains metadata and an optional
  `blob:` preview URL—not the base64 data URL.
- Cancellation preserves the active image.
- Explicit removal, replacement, reset, stop, or starting a text profile
  clears the relevant image state.
- Mission Archive, receipts, status responses, visible transcript, and normal
  history receive filename/type/dimensions/size/SHA-256 only.
- Raw `data:image/` or `;base64,` markers are blocked from archive/history
  text.
- Existing Engineer restrictions and guarded streaming remain unchanged.

## Exact scope

- Proposed changed file: `core/foxai_web.py`
- Explicitly unchanged: `core/server.py`
- Delete operations: none
- Apply capability: none

## Hashes

- Baseline: `3b1a8d9a1bc63c6d0a6a333edf315a4c1aff06f9ffae44f9ddd679c96b7c1d4d`
- Candidate: `7fcbddeae22904af7f9aa75e9546e3e28721d455222fbfc42c27c5186ba45180`
- Exact diff: `2a847670fc10575b9eb3c1e25c305dbd087784ceccb3f488b4d07626422a2165`

## Regression tests

- poisoned old history is stripped of image payloads;
- initial image request contains exactly one image;
- follow-up request contains exactly one current image;
- earlier history contains zero image payloads;
- visible transcript contains zero data URLs;
- active browser state contains metadata only;
- cancellation preserves active image context;
- text profiles refuse image-context use;
- explicit removal clears active context;
- archive marker blocks raw image payloads;
- missing active context fails closed;
- every embedded JavaScript block passes `node --check`;
- Boundary Watch remains 5/5.

## Existing persisted strings

The live verifier performs a bounded, read-only scan of likely Logs, Reports,
Projects, and Mission Archive folders for `data:image/` or `;base64,` markers.
It reports findings but does not alter them. Any cleanup of already-persisted
content must be a separate preview-first action.

Restarting FOXAI after a later approved apply clears the old volatile
in-memory conversation strings automatically.
