# Shared Neural Runtime — Preview Only

Desktop and WebUI currently target the same llama endpoint, but each frontend
has separate launch ownership. The desktop only recognizes its own local
`Popen` handle, while WebUI separately launches and tracks another process.

## Proposed scope

Only:

- `core\server.py`
- `ui\main_window.py`
- `core\foxai_web.py`

## Proposed behavior

- Use one shared runtime state file:
  `Logs\shared_llama_runtime.json`
- Use an atomic lock to prevent simultaneous duplicate launches.
- Register Desktop and WebUI as live clients of the same server.
- Attach to a healthy compatible model instead of opening another server.
- When the same model is already loading, wait for it instead of launching a
  duplicate.
- Block a different or unverified model on the same endpoint.
- Check `/health`, the TCP port, shared state, process identity, and
  `/v1/models` when needed.
- Read WebUI context and thread settings from `Config\FoxAI.ini`, matching the
  desktop configuration.
- Detach one interface without stopping the server while another live FOXAI
  interface remains connected.
- Terminate only a verified managed llama-server when the final client stops.
- Leave an unverified external process online rather than terminating it.

## Explicit non-changes

No changes to ComfyUI, Engineer, security containment, Director, SmartSearch,
MissionSession, archives, memory, or `core_v10`.

## Reviewed hashes

### Baselines

- `core\server.py`
  `e0a840396045e728794a64edfeee5d1465471feb975da76dc97b44f6ce14884c`
- `ui\main_window.py`
  `32dae792dd84417d7f3fb131eef9d523c8b339f8fd9a86beec79803d1a22e8a1`
- `core\foxai_web.py`
  `0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda`

### Candidates

- `core\server.py`
  `6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505`
- `ui\main_window.py`
  `cd537dc74e106c436d50928a57598fe666155ddcdc445c49b74a0eb5292f55eb`
- `core\foxai_web.py`
  `bd34f97b7580310fa1a25bd031a5afcb91f8079b74167252b68db3cb7e418952`

- Exact combined diff:
  `9af4cf49d71249d4f167898fcf57a1c1503dc9dac80a3a0219ce6cdf3f0d05f6`

## Verification completed

- Candidate compilation: 3 PASS
- Shared-runtime unit tests: 8 PASS
- Shared-runtime source/integration tests: 9 PASS
- Phase 1 security regression tests: 15 PASS
- Engineer intake regression tests: 8 PASS
- Mission-session regression tests: 6 PASS
- WebUI shared-mission static tests: 11 PASS
- Apply script included: NO
- Live FOXAI files modified: NO

## Run the local preview

1. Extract this folder directly inside `Z:\FOXAI`.
2. Run `PREVIEW_SHARED_NEURAL_RUNTIME.bat`.
3. A valid run must report `State: preview_ready`.
4. Upload `preview_output\Shared_Neural_Runtime_PREVIEW_RECEIPT.json`.

Do not copy the candidate files into the live project manually. An apply bundle
should be created only after the local preview receipt is reviewed and approved.
