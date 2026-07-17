VIT1 — FOXAI Real Qwen3VL Image-Input Test

PURPOSE
-------
This is the first real multimodal test for the verified FOXAI Fast Vision and
Quality Vision profiles.

It sends actual PNG image bytes to the local llama-server OpenAI-compatible
vision endpoint. This is different from the earlier text-only model benchmark.

TESTS
-----
1. Exact OCR and counting
2. Spatial relationships
3. Screenshot/UI understanding
4. Detailed scene description
5. Hallucination resistance

MODELS
------
Fast Vision:
    Models\Chat\Qwen3VL-8B-Instruct-Q4_K_M.gguf

Quality Vision:
    Models\Chat\Qwen3VL-8B-Instruct-Q8_0.gguf

The benchmark verifies the locked model sizes and records full SHA-256 hashes.

MULTIMODAL PROJECTOR
--------------------
VIT1 does not guess a fixed projector filename.

It searches the FOXAI Models tree for .gguf files containing "mmproj" or
"projector", scores candidates for Qwen3VL/8B compatibility, records the exact
file/hash used, and tries up to three matching candidates. It also tests
projector-free startup in case the installed GGUF/engine build embeds or
automatically handles the vision projector.

INSTALL
-------
Extract the complete folder directly to:

    Z:\FOXAI\VIT1\

Do not run from inside the ZIP preview.

BEFORE RUNNING
--------------
Close:

- FOXAI WebUI;
- Chat Engine;
- all previous benchmark servers.

RUN
---
Recommended complete comparison:

    RUN_BOTH.bat

Faster first test:

    RUN_FAST_ONLY.bat

Quality-only test:

    RUN_QUALITY_ONLY.bat

RUNTIME
-------
Isolated port:
    8098

Context:
    8192

Threads:
    12

Vision profiles retain the engine's current reasoning behavior, matching the
verified selector contract.

CRASH RECOVERY
--------------
VIT1 checkpoints after every completed response.

Inside the timestamped output folder it continually updates:

    RECOVERY_UPLOAD.zip

If Python or Windows stops unexpectedly, upload that recovery ZIP. A clean
completion also produces:

    VIT_<timestamp>.zip

EXPECTED SUCCESS
----------------
    State: vision_test_complete
    Verified: True
    Live files modified: False
    Apply capability present: False

OUTPUT
------
- receipt.json
- findings.md
- report.html
- summary.json and summary.csv
- results.json
- exact response TXT/JSON files
- model/server logs
- copies of the deterministic test images
- RECOVERY_UPLOAD.zip
- final timestamped ZIP after clean completion

SAFETY
------
- read-only model and source inspection;
- locked FOXAI baseline verification;
- isolated local port;
- no source/configuration/default/archive/security-log changes;
- no apply capability;
- sequential model loading to reduce memory pressure;
- forced cleanup path and port-release verification;
- checkpoint and recovery ZIP after every response.
