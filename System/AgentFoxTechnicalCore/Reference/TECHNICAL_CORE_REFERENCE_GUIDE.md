# Agent Fox Technical Core — Authoritative Reference Guide

**Reference build mission:** `ENG-20260723-013919-9712A1`  
**Preflight mission:** `ENG-20260723-012205-B039AE`  
**Current milestone:** V1B-2 complete; V1B-3A is the next bounded capability.

## 1. Purpose and authority

This guide is a static architecture and dependency reference generated only from the six verified V1B-2G preflight evidence files. It does not claim current live system state.

## 2. Architecture layers and entry points

- **Desktop Helper:** `Z:\FOXAI\System\AgentFoxTechnicalCore\desktop_self_knowledge_integration_v1.py`
- **Desktop Source:** `Z:\FOXAI\ui\main_window.py`
- **Director:** `Z:\FOXAI\core\director.py`
- **Resource Provider:** `Z:\FOXAI\System\AgentFoxTechnicalCore\resource_evidence_provider_v1.py`
- **Shared Adapter:** `Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py`
- **Webui Helper:** `Z:\FOXAI\System\AgentFoxTechnicalCore\webui_self_knowledge_integration_v1.py`
- **Webui Source:** `Z:\FOXAI\core\foxai_web.py`

## 3. Routing precedence

1. exact slash-command handling
2. shared self-knowledge adapter/provider
3. department or Director routing
4. ordinary model dispatch

The shared self-knowledge adapter is expected to receive eligible ordinary questions before department/Director routing and before ordinary model dispatch. Exact slash commands retain precedence.

## 4. Official names and extracted maps

The preflight evidence did not expose a normalized official-name map. Source-specific extracted maps remain in the machine-readable manifest.

## 5. Providers, adapters, contracts, and fixtures

- **Resource Evidence Provider:** `Z:\FOXAI\System\AgentFoxTechnicalCore\resource_evidence_provider_v1.py`
- **Shared Chat Adapter:** `Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py`
- **Webui Integration Helper:** `Z:\FOXAI\System\AgentFoxTechnicalCore\webui_self_knowledge_integration_v1.py`
- **Desktop Integration Helper:** `Z:\FOXAI\System\AgentFoxTechnicalCore\desktop_self_knowledge_integration_v1.py`
- **Integration Verifier:** `Z:\FOXAI\System\AgentFoxTechnicalCore\shared_resource_provider_integration_verifier_v1.py`
- **Integration Contract:** `Z:\FOXAI\System\AgentFoxTechnicalCore\SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json`
- **Integration Fixtures:** `Z:\FOXAI\System\AgentFoxTechnicalCore\SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json`
- **Integration Readme:** `Z:\FOXAI\System\AgentFoxTechnicalCore\README_V1B2C.md`

## 6. Source inventory and protected hashes

The bounded inventory contains **25 present files** and **0 missing files**.

| Path | SHA-256 | Historical comparison |
|---|---|---|
| `System/AgentFoxTechnicalCore/README_V1B2C.md` | `09c64402aa1f1315f0cc07eec1c2d0a52de0391748bb2a1a8096cd6535bcff62` | match |
| `System/AgentFoxTechnicalCore/SHARED_RESOURCE_PROVIDER_INTEGRATION_CONTRACT_V1.json` | `60b6b5394849a5cd0a192be137deb01be39d2c3f8fd3e4fa75421b94ab5a9ab1` | match |
| `System/AgentFoxTechnicalCore/SHARED_RESOURCE_PROVIDER_INTEGRATION_FIXTURES_V1.json` | `f2fab44d7926a4f46706e369eb853b790137a29ff4b6df689deeab44e9327b13` | match |
| `System/AgentFoxTechnicalCore/desktop_self_knowledge_integration_v1.py` | `1b3aa2e3ab0409112ca602209285e27df1ab6b0216f5d9a9480766e4509078c4` | match |
| `System/AgentFoxTechnicalCore/resource_evidence_provider_v1.py` | `41a1663cd30af8a3800c8082d351f8d0338e75cd1df39d3c801a39cc3075f680` | match |
| `System/AgentFoxTechnicalCore/self_knowledge_chat_adapter_v1.py` | `1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275` | match |
| `System/AgentFoxTechnicalCore/shared_resource_provider_integration_verifier_v1.py` | `fdf30e7b33ac1fda8d88d2ac761fae3ca93f3a01a3261b03e3832a55898d39ce` | match |
| `System/AgentFoxTechnicalCore/webui_self_knowledge_integration_v1.py` | `451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69` | match |
| `core/agents.py` | `a822bc012da7f7fd6b3166ad14a57844c402ace21cc1bb971190b43c823b0a65` | not pinned |
| `core/chat_agent.py` | `7720092b9a6a616c6a572450a64bcb204de1dc40f4375b85a75eba63e58404f9` | not pinned |
| `core/chat_resilience.py` | `af53270881eee1f0c4d23fb3deafed2dceb44bd684d9bd6e66221f3d05a29838` | not pinned |
| `core/director.py` | `1397b0ce5d1e21b9fc49eabef76ffa64467d716061b12d1a2c670167597d7d55` | match |
| `core/engineer_agent.py` | `d01bd8e6e6ec1b8be896c828177caf3d5eea4bd58a6ea54e95b5976779683b28` | not pinned |
| `core/engineer_intent.py` | `a74a4982dc08cda8175d20c60541ae670369ee9a30695d024115c69d66f2002f` | not pinned |
| `core/engineering_workshop_bridge.py` | `2a2ee1b46266aac04a70554f90e6d33416267c18e0689c36c7c88d0ad220f4da` | not pinned |
| `core/foxai_web.py` | `d7bf0a2042d55ef7f0a5869556015e42c7427e7ff88636b28e1795f3adf7b952` | match |
| `core/investigation_engine.py` | `6e6ff3a97c5c1f72407c20ff805514ce9bff68dabd07ff22144791b3ad7a44ca` | not pinned |
| `core/library_agent.py` | `846b7ee2eea7417ce7a258cf592896d5d2cce73b496a5528ce8881aeb70d7fa4` | not pinned |
| `core/memory.py` | `05117cb38a179ca66761dfb7495f799bf008c423de8db0e531a226c24af538bf` | not pinned |
| `core/mission_flow.py` | `30c1c3ef910d944e0a3ea899b517938da942e69218dc1a68f9b7a9a50865172a` | not pinned |
| `core/mission_session.py` | `d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a` | not pinned |
| `core/red_canvas_agent.py` | `7b02daa842635fa922eec6e03d69ed71805383222ea8b2cbceb19556125e201d` | not pinned |
| `core/security_containment.py` | `9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24` | not pinned |
| `core/workshop_config.py` | `91236db004335645db467962028de638e19046cff2d349fa3af0dd4c9d5e4265` | not pinned |
| `ui/main_window.py` | `c232ce7f14a9fc7e898c13afcdfc7e56be1826b51d18d3c71979ac3f0b2acdc9` | match |

## 7. Dependencies

- Static import statements analyzed: **224**
- Standard-library roots: `__future__`, `abc`, `argparse`, `base64`, `binascii`, `configparser`, `contextlib`, `dataclasses`, `datetime`, `functools`, `hashlib`, `http`, `importlib`, `io`, `json`, `os`, `pathlib`, `platform`, `py_compile`, `re`, `secrets`, `shlex`, `shutil`, `subprocess`, `sys`, `tempfile`, `textwrap`, `threading`, `time`, `tkinter`, `typing`, `urllib`, `uuid`
- Local module roots: `core`, `core.agents`, `core.application_registry`, `core.boot_manager`, `core.brainstem`, `core.chat_agent`, `core.chat_resilience`, `core.comfy_bridge`, `core.comfy_ops_monitor`, `core.confidence_engine`, `core.decision_layer`, `core.dependency_graph`, `core.director`, `core.engineer_agent`, `core.engineer_intent`, `core.evidence_drivers`, `core.evidence_ranker`, `core.forge_journal`, `core.forge_master`, `core.image_models`, `core.investigation_engine`, `core.kernel`, `core.library`, `core.library_agent`, `core.memory`, `core.mission_flow`, `core.mission_session`, `core.model_sources`, `core.models`, `core.paths`, `core.project_index`, `core.promptsmith`, `core.recommendation_engine`, `core.red_canvas`, `core.red_canvas_agent`, `core.runtime_graph`, `core.security_containment`, `core.server`, `core.smart_search`, `core.technical_debt`, `core.workshop_config`
- Third-party or unresolved roots: `Departments`, `PIL`, `customtkinter`, `psutil`, `requests`

`third-party or unresolved` is a static classification only. It is not proof that a package is installed, required on every path, or external. In particular, `Departments` remains unresolved by the six-file evidence boundary.

## 8. Allowed and prohibited operations

- Allowed: Bounded static inspection of explicitly relevant Technical Core files.
- Allowed: Historical resource-evidence answers grounded in verified evidence sources.
- Allowed: Exact slash-command bypass before self-knowledge evidence loading.
- Allowed: Explicit, fixed-file Z-to-K mirroring with post-copy hash verification.
- Prohibited: Automatic current-live-state claims from historical evidence.
- Prohibited: Unapproved live scans, process/listener inspection, or network access.
- Prohibited: Model calls or GUI launches by the historical resource provider.
- Prohibited: Filesystem-wide search, service/startup/registry changes, or K: access without explicit scope.
- Prohibited: Diagnosis or performance recommendations from the historical resource provider.

## 9. Known-good behavior

- Historical resource questions are intercepted in both Desktop and WebUI through the shared adapter.
- Current-live resource questions pass through rather than receiving stale historical claims.
- The provider preserves the existing V1A-3E answer-packet envelope.
- The provider supports 18 bounded resource-evidence categories.
- Slash commands bypass the provider before evidence loading.
- Ordinary use of the bare word evidence no longer routes to Engineer.
- Desktop model labels are not repeatedly stacked.

## 10. Mission, receipt, and snapshot history

The preflight indexed **48 artifacts** across the bounded mission set.

- `ENG-20260722-153014-F39AF7`
- `ENG-20260722-154330-42BAE0`
- `ENG-20260722-165746-DF7E34`
- `ENG-20260722-183657-F5AF85`
- `ENG-20260722-223348-83B942`
- `ENG-20260722-225500-4D0517`
- `ENG-20260723-001455-43C31D`
- `ENG-20260723-002238-CD8A83`
- `ENG-20260723-012205-B039AE`

## 11. Known anomalies

- V1B-2E source edits were verified by exact post-hash reconciliation because Workshop archive bookkeeping failed after writes; no normal applied_verified implementation receipt exists for those two edits.
- The Workshop previously reported BLOCKED — NOTHING CHANGED despite evidence that source writes had occurred; transactional semantics and archive path normalization require a separate read-only self-repair preflight.
- Static dependency classification leaves Departments unresolved as local-versus-external within the six-evidence-file boundary.

## 12. Z: active build and K: mirror

- `Z:\FOXAI` is the active build and test workspace.
- `K:\FOXAI` is the staged portable mirror.
- Small verified increments should use a fixed-file copy plus post-copy hash verification; no deletions unless explicitly authorized.

## 13. Next boundary: V1B-3A

V1B-3A is the **Approved Read-Only Current-State Request Broker**. It should recognize explicit current-state questions, request or enforce read-only authorization, invoke only approved bounded providers, distinguish live evidence from historical evidence, and preserve pass-through when authorization or a suitable provider is unavailable.

### Non-goals

- No automatic scans merely because a user opens Desktop or WebUI.
- No diagnosis, repair, tuning, optimization, or recommendations.
- No write operations, installs, network activity, or background monitoring.
- No reuse of historical evidence as a substitute for current measurements.

## 14. Evidence limitations

- The reference is static and reflects the six verified preflight files, not future source changes.
- Import presence does not prove installation, runtime use, or universal necessity.
- Extracted names and maps are preserved as found; unresolved naming is not silently normalized.
- The mission index is bounded to the mission IDs selected by V1B-2G preflight, not every Engineering Workshop mission.
