# FOXAI Guarded Streaming — Phase 2 Exact Preview

## State

- State: **exact_preview_ready**
- Verified: **True**
- Live files modified: **False**
- Apply capability present: **False**
- Changed files: **one — `core/foxai_web.py`**
- Delete operations: **none**

## Exact hashes

- Locked live baseline: `b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48`
- Candidate: `e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb`
- Exact diff: `33da716cd9e6065a8d4b8eaec21253e15a75d4b1c7f39cf4a5a45aebf4662123`

## Candidate behavior

1. Keeps `/api/chat/send` byte-for-byte intact as the verified non-streaming fallback.
2. Adds a separate `/api/chat/stream` NDJSON route.
3. Requests the installed llama-server with `stream: true`.
4. Buffers until a complete sentence or newline.
5. Runs each completed unit through `guard_model_action_claims` before browser exposure.
6. Never writes a raw model token directly to the browser.
7. Re-runs the guard against the complete answer before committing chat history, Mission Archive, state, and the final receipt.
8. Sends a final canonical replacement event after archive verification.
9. Adds **Cancel Generation** through `AbortController`.
10. Does not commit or archive a partial assistant turn when the browser disconnects.
11. Routes explicit Engineer commands and unsupported streaming browsers to the verified non-streaming endpoint.
12. Extends timing with **first guarded chunk**, while preserving total/model timing.
13. Updates PsyLLM's evidence label to **BRAINSTORMING SUPPORTED • LONG-FORM PENDING**.

## Verification

- Candidate Python compile: **PASS**
- Embedded JavaScript `node --check`: **PASS**
- Fragmented NDJSON browser harness: **PASS**
- Guard-before-exposure helper harness: **PASS**
- Existing non-streaming route byte identity: **PASS**
- Boundary Watch: **5/5 PASS**

## Deliberate limitation

This is sentence-level guarded streaming, not raw token streaming. That means it may wait for punctuation before showing text. The safety benefit is that unguarded tokens never reach the browser.

No patch has been applied.
