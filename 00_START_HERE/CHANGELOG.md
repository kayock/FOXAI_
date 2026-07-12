# Changelog

## v0.1.2 - Dashboard Live View

- Improved Bridge Dashboard layout.
- Added live health summary cards.
- Added recent boot log display.
- Dashboard now shows Operator greeting and quote from API.
- Launcher menu now clearly separates raw API status from Shell Dashboard.

## v0.3.0 - Project Unification

- Added backup-first patch workflow.
- Added Git prep documentation.
- Added unified project structure documentation.
- Added no-large-manual-edits engineering rule.
- Preserved Core/Shell architecture.

## v0.4.0 - Living System Scanner

- Added read-only machine scanner.
- Added `/api/system` endpoint.
- Added CPU, RAM, GPU, disk, OS, Python, Git, Node, npm detection.
- Added model and Knowledge file counts.

## v0.5.0 - Dynamic Module Registry

- Added department `module.yaml` manifests.
- Added `System/Registry/build_registry.py`.
- Core API can now discover modules dynamically where safe.
- Added documentation and Forge decision record.

## v0.6.0 - AI Asset Scanner

- Added read-only AI asset scanner.
- Added `AI/scan_ai_assets.py`.
- Added AI inventory output in `AI/Inventory`.
- Added `/api/ai-assets`.
- `/api/status` now includes `ai_assets`.

## v0.7.0 - Service Bus

- Added `System/Services/service_bus.py`.
- Added service registry and event log.
- Added `/api/services`, `/api/events`, and `/api/bridge`.
- Established services as the future communication boundary between departments.

## v0.8.0 - Foundry Release Checker

- Added `Foundry/release_check.py`.
- Added release readiness reports.
- Added `/api/release-check`.
- The Foundry can now answer whether a build is ship-ready.

## v0.9.0 - Git Baseline & Release Packager

- Added Git baseline helper.
- Added Foundry release packager.
- Added release packaging documentation.
- Updated `.gitignore` for releases, temp files, logs, node_modules, and large AI assets.

## v1.0.0-rc.1 - Portable Release Candidate

- Added `Foundry/build_portable_rc.py`.
- Added one-command release candidate builder.
- Release candidate builder runs registry, AI scan, release check, and release packager.

## v1.0.0 - Portable Foundation Release Finalizer

- Added `Foundry/finalize_v1_release.py`.
- Added final release readiness report.
- Added final release notes.
- Establishes v1.0.0 as the Portable Foundation.

## v1.1.0 - Academy Seed

- Added `Academy/academy.py`.
- Added Academy Charter, Colleges, Professors, and mottoes.
- Added `/api/academy`.
- Established Academy data model for future AI behavior.

## v1.2.0 - FOXAI Discovery

- Added `AI/foxai_discovery.py`.
- Added FOXAI inventory output in `AI/Inventory`.
- Added `/api/foxai`.
- Established `Z:\FOXAI` as the canonical AI asset warehouse.

## v1.3.0 - AI Gateway Stub

- Added `AI/ai_gateway.py`.
- Added AI Gateway config.
- Added `/api/ai-gateway`.
- Added guarded placeholder `POST /api/chat`.
- No local model execution yet.

## v1.4.0 - Local Runtime Connector

- Added `AI/local_runtime.py`.
- Added `/api/runtime`.
- Updated `POST /api/chat` to call a localhost OpenAI-compatible runtime when available.
- Safe fallback remains when no runtime is online.

## Feature 001 - Local Chat

- Added `AI/local_chat.py`.
- Added `/api/local-chat`.
- Added local runtime launch helper.
- Starts the first integrated, demonstrable feature milestone.

## Feature 001B - Runtime Auto Launcher

- Added `AI/runtime_launcher.py`.
- Added `/api/runtime-launcher`.
- Added `AI/Gateway/LAUNCH_SELECTED_MODEL_RUNTIME.bat`.
- Runtime launch remains Operator-visible.

## Feature 002 - Bridge Application

- Added `Bridge/` Electron app starter.
- Added `Start_Bridge.bat`.
- Bridge displays Home, Academy, Workshop, Library, Observatory, and Foundry rooms.
- Bridge reads live data from Core API endpoints.

## Feature 002B - Living Bridge Polish

- Added Bridge boot screen.
- Added Workshop Bell notifications.
- Added dynamic capability cards.
- Improved Home mission panel and Academy professor cards.

## Feature 002C - Professor Studies

- Added clickable professor cards.
- Added professor study view.
- Added suggested questions and Ask-this-Professor flow.
- Added FOXAI model team suggestions per professor.

## Feature 002D - Observatory Room

- Added Observatory metric cards.
- Added runtime and FOXAI session status.
- Added recommendation panel.
- Reinforces Observatory as the room that watches and advises.

## Feature 002E - Foundry Room

- Added Foundry room release readiness gauge.
- Added Architecture Laws panel.
- Added Workshop Wall and next-build guidance.
- Added recent build timeline.

## Feature 002F - Library Room

- Added Iron Library shelf cards.
- Added knowledge-file readiness panel.
- Added future Library tools and next-index guidance.

## Feature 002G v2 - Creative Studio Room

- Added visible Creative Studio section in Workshop.
- Added image model and workflow cards.
- Added Prompt Bench and Professor Da Vinci helper.
- Prepared ComfyUI generation workflow for the next build.

## Feature 002H - Repair Bay Room

- Added Repair Bay room to Bridge navigation.
- Added host health and readiness cards.
- Added read-only diagnostic safety rules.
- Added recommended next scan list.

## Feature 002I - Bridge Room Stabilizer

- Added `Foundry/bridge_health.py`.
- Added `Foundry/bridge_health.bat`.
- Added Bridge health report output.
- Added mini Bridge Health panel to Foundry room.

## Feature 002J - Operator Settings Room

- Added Settings room to Bridge navigation.
- Added Operator identity and greeting fields.
- Added Workshop path display.
- Added design parameter panel.

## Feature 002K - Bridge Launcher Polish

- Added `Launch_KayocktheOS_Workshop.bat`.
- Launcher checks Core API and starts Core if needed.
- Launcher installs Bridge dependencies if missing.
- Preferred front-door entry point documented.

## Feature 003 - First Contact

- Added `AI/first_contact.py`.
- Added `AI/Gateway/FIRST_CONTACT_START_RUNTIME.bat`.
- Added `/api/first-contact`.
- Routed `/api/chat` through First Contact.
- Advisor-only local AI conversation path established.

## Feature 003B - First Contact v2

- Corrected runtime selector to prefer `llama-server.exe`.
- Blocked benchmark/developer executables from runtime selection.
- Preserved FOXAI as external engine/model warehouse.
- Rewrote `FIRST_CONTACT_START_RUNTIME.bat`.

## Feature 003C - First Contact Bridge Panel

- Added First Contact panel to Bridge Home room.
- Shows selected model, runtime path, server status, and launch steps.
- Makes First Contact status visible without opening raw API JSON.

## Feature 003D - First Contact Diagnostics

- Added `Foundry/first_contact_diagnostics.py`.
- Added `Foundry/first_contact_diagnostics.bat`.
- Added diagnostic reports for runtime, `/v1/models`, `/api/first-contact`, and `/api/chat`.
- Added Bridge hint near First Contact panel.

## Feature 003E - First Contact Runtime Fixer

- Hard-locked First Contact runtime to `Z:\FOXAI\Engine\llama-server.exe`.
- Preferred `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`.
- Rewrote `AI/Gateway/FIRST_CONTACT_START_RUNTIME.bat`.
- Removed runtime guessing risk from benchmark executables.

## Feature 003F - First Contact Stable Context

- Updated First Contact runtime launcher with `-c 4096`.
- Preserved llama-server runtime path.
- Preserved DeepSeek 14B model selection.
- Prevents KV cache memory failure from default context size.

## Feature 004 - Kobold Engine Adapter

- Added `AI/kobold_engine_adapter.py`.
- Added `AI/Gateway/START_KOBOLD_ENGINE.bat`.
- Added adapter config `AI/Gateway/engine_adapter_config.json`.
- Added `/api/kobold` where Core API patch is available.
- Routed `/api/chat` toward Kobold adapter where possible.

## Feature 004B - Kobold Engine Check Panel

- Added visible KoboldCpp status panel to Bridge Home.
- Shows engine path, selected model, server status, and launcher path.

## Feature 004C - Kobold Core Repair

- Repaired Core API Kobold return values.
- Replaced `AI/kobold_engine_adapter.py` with cleaner adapter implementation.
- `/api/chat` now prefers the Kobold adapter.
- Adapter tries OpenAI-compatible Kobold endpoint, then native Kobold endpoint.

## Feature 004D - Model Profiles

- Added Safe / Power / Vision model profiles.
- Safe profile remains DeepSeek 14B Q4.
- Power profile preserves Qwen Coder 30B for stronger computers.
- Vision profile preserves Qwen3VL for image tasks.

## Feature 006 - Core Working Launch Cleanup

- Added `AI/core_working.py`.
- Added `AI/Gateway/START_CORE_WORKING.bat`.
- Redirected `FIRST_CONTACT_START_RUNTIME.bat` away from `llama-batched-bench.exe`.
- Added `/api/core-working` status route where Core API patch is available.
- Added Bridge Core Working status panel.

## Feature 007 - Academy Bridge Dashboard

- Added Academy Bridge hero to Home.
- Added Engineering Academy, Creative Studio, Knowledge Wing, and Repair Bay cards.
- Added status line for AnythingLLM, ComfyUI, and local runtime.
- Reinforces KayocktheOS as orchestration layer rather than reinvented runtime.
