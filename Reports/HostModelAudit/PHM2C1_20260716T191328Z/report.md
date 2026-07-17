# FOXAI Portable Host Model Library Phase 2C1 — Read-Only Audit

- Created: `2026-07-16T19:13:28.612389+00:00`
- Root: `Z:\FOXAI`
- Machine: `DESKTOP-G9ERN9B`
- Expected primary machine: `DESKTOP-G9ERN9B`
- Expected-machine match: **True**
- Automatic launch: **False**
- Network access: **False**
- Model hashing: **Deferred**
- Source/config/model changes: **None**

## Host model inventory

- `C:\KayockModels` — exists: **True**, models: **1**
  - `Qwen3-30B-A3B-Q4_K_M.gguf` — 17.28 GiB, readable: **True**

## USB model inventory

- `Z:\FOXAI\Models\Chat` — models: **10**
- `Z:\FOXAI\Models\Vision` — models: **1**

## Static model-path handoff

- Absolute host-path handoff likely supported: **True**
- Verified USB/HOST PC source-label contract detected: **False**
- Provider/endpoint hook detected: **True**

## Phase 2C2 required scope

- Config/model_sources.json or equivalent backend-owned source registry
- Config/machine_profiles/<stable-machine-id>.json or equivalent
- host-folder allowlist and read-only discovery
- runtime receipt field for selected model source and exact model path
- UI badge showing USB or HOST PC from backend runtime identity
- explicit unavailable/fallback state with no silent switching

## Future online/LAN readiness

- source type LAN_OPENAI_COMPATIBLE
- source type ONLINE_PROVIDER
- endpoint health probe separated from local GGUF discovery
- external-send consent gate
- credential-manager reference field rather than API key value

## Preserve

- existing approved USB model profiles
- model files on USB or host PC
- llama-server executable
- portable core runtime
- Desktop and ComfyUI runtimes
- Engineering Airlock approval rules

## Safety

The audit does not start llama-server, load a GGUF, call a provider,
hash large model files, copy or move models, or modify source,
configuration, launchers, credentials, or registries. Its only writes
are this timestamped report and receipt.
