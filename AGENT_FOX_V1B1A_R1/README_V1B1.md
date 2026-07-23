Agent Fox Technical Core V1B-1A — Minimal-Load Resource Baseline

Mission: ENG-20260722-054027-DEFA9D

This component captures one read-only minimal-operational-load snapshot for later idle-versus-loaded comparison.

Before Apply, leave the WebUI and Engineering Workshop running, but close FOXAI Desktop, stop ComfyUI, and stop the llama-server/model engine. The collector never closes processes itself. If a blocker remains, collection returns minimal_load_precondition_not_met and writes no comparison evidence.

It records bounded memory, page-file, process, known local listener, C:/Z:/S: capacity, active Z:/FOXAI identity, and known-good component hashes. It does not access K:, inspect personal files, record process arguments, connect to ports, modify Windows, or diagnose the PC.

Expected evidence count: 4 UTF-8 LF-only JSON files.
