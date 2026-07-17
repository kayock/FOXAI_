PCTQ1 — PsyLLM Creative Text Quality Benchmark

PURPOSE
-------
Test whether PsyLLM-8B-Q5_K_M.gguf genuinely deserves FOXAI's Creative Text
label.

This is not another speed-only test. It evaluates:

- atmospheric fiction;
- distinct character dialogue;
- constrained poetry;
- original worldbuilding;
- roleplay voice consistency;
- three-tone revision;
- long-scene continuity;
- non-cliché brainstorming.

The benchmark records objective compliance and every raw response. It does not
award itself a creative-quality badge. Creative merit requires review of the
actual writing.

INSTALL
-------
Extract the complete folder directly to:

    Z:\FOXAI\PCTQ1\

Do not run it from inside the ZIP preview.

BEFORE RUNNING
--------------
Close:

- FOXAI WebUI, port 8765;
- Chat Engine, port 8080;
- any benchmark server, port 8099.

RUN
---
Preferred complete evaluation:

    RUN_FULL.bat

Faster initial evaluation:

    RUN_QUICK.bat

FULL mode includes all eight measured creative tasks.
QUICK mode includes fiction, dialogue, poetry, and story hooks.

RUNTIME
-------
Model:
    Models\Chat\PsyLLM-8B-Q5_K_M.gguf

Isolated server:
    127.0.0.1:8099

Settings:
    context 8192
    threads 12
    --reasoning off
    --reasoning-budget 0
    temperature 0.80
    top_p 0.92
    fixed per-prompt seeds

EXPECTED SUCCESS
----------------
    State: benchmark_complete
    Verified: True
    Live files modified: False
    Apply capability present: False

OUTPUT
------
The benchmark automatically creates and ZIPs a short output folder containing:

- receipt.json
- findings.md
- summary.json and summary.csv
- results.json
- prompts.json
- responses.md
- one TXT and JSON file per response
- human_review.md
- llama_server.log

Upload the generated PCTQ_<timestamp>.zip.

SAFETY
------
- verifies the newly applied live WebUI and server hashes;
- verifies all locked dependencies, config, engine, and security baselines;
- requires normal WebUI/chat/benchmark ports to be closed;
- launches only PsyLLM on isolated port 8099;
- uses the verified reasoning-off runtime;
- never changes FOXAI source, configuration, defaults, archives, or security logs;
- stops the server and verifies port 8099 is released;
- records a fail-closed receipt on any problem;
- contains no apply capability.
