# Shared Neural Runtime — Approved Apply Bundle

The local preview is verified. It matched all reviewed hashes, compiled all
three candidates, passed 17 shared-runtime tests, and passed 40 existing
security and integration regression tests.

## Scope

Only:

- `core\server.py`
- `ui\main_window.py`
- `core\foxai_web.py`

## Resulting behavior

- Desktop and WebUI coordinate one llama server through
  `Logs\shared_llama_runtime.json`.
- An atomic lock prevents simultaneous duplicate launches.
- The second interface attaches to, or waits for, the compatible server.
- A different or unverified model on port 8080 is blocked.
- Each interface is tracked as a client.
- One interface can close without stopping the server used by the other.
- The final client stops only a verified managed llama-server process.
- WebUI uses the context and thread values from `Config\FoxAI.ini`.

## Reviewed hashes

Baselines:

- `core\server.py` — `e0a840396045e728794a64edfeee5d1465471feb975da76dc97b44f6ce14884c`
- `ui\main_window.py` — `32dae792dd84417d7f3fb131eef9d523c8b339f8fd9a86beec79803d1a22e8a1`
- `core\foxai_web.py` — `0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda`

Candidates:

- `core\server.py` — `6d2b43616d6130469c057da070f8c4cf7ee3a965b563d1f704b0cc8ce6a49505`
- `ui\main_window.py` — `cd537dc74e106c436d50928a57598fe666155ddcdc445c49b74a0eb5292f55eb`
- `core\foxai_web.py` — `bd34f97b7580310fa1a25bd031a5afcb91f8079b74167252b68db3cb7e418952`

Exact combined diff:

`9af4cf49d71249d4f167898fcf57a1c1503dc9dac80a3a0219ce6cdf3f0d05f6`

## Safety sequence

The apply verifies baselines, candidates, diff, preview receipt, closed service
ports, and the exact approval phrase. It creates a three-file backup, runs all
57 tests before installation, installs with temporary-file replacement,
verifies exact live hashes, runs all 57 tests against the live project, and
automatically restores all three baselines if a post-backup step fails.

Exact approval phrase:

`APPLY SHARED NEURAL RUNTIME`

## Run

1. Extract this folder directly inside `Z:\FOXAI`.
2. Close the desktop UI, WebUI, and llama-server console.
3. ComfyUI may remain running.
4. Run `APPLY_SHARED_NEURAL_RUNTIME.bat`.
5. Type the exact approval phrase.
6. Upload the generated
   `Reports\SecurityMilestone\Shared_Neural_Runtime_Apply_Receipt_*.json`.
