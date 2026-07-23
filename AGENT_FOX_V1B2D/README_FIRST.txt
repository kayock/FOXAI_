AGENT FOX TECHNICAL CORE V1B-2D
Dual-Interface Live Acceptance Verification

Mission ID
ENG-20260722-183657-F5AF85

Purpose
Verify the completed V1B-2C shared resource-provider integration through the installed WebUI and Desktop routing helpers and the shared adapter.

What it verifies
- The same historical resource question is answered on both surfaces.
- WebUI and Desktop produce identical answer text and answer packets when given the same request ID.
- WebUI send and stream response envelopes remain accepted.
- Desktop display routing remains accepted.
- Current-live questions pass through rather than using historical evidence.
- Ordinary chat passes through.
- Slash commands bypass evidence loading.
- All 18 resource categories pass across both surfaces.
- Protected-context overlap keeps priority.
- Evidence failure boundaries remain fail-closed.

What it does not do
- It does not launch FOXAI WebUI or Desktop.
- It does not load or call a model.
- It does not scan processes, listeners, memory, or current machine state.
- It does not use the network.
- It does not modify FOXAI source files or prior evidence.
- It does not access K:.

Generated evidence
Exactly five JSON files are atomically created at:
Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260722-183657-F5AF85_V1B2D_DUAL_INTERFACE_LIVE_ACCEPTANCE

Run
Extract AGENT_FOX_V1B2D directly into Z:\FOXAI, then double-click:
Z:\FOXAI\AGENT_FOX_V1B2D\RUN_V1B2D_ACCEPTANCE.cmd

There is no Workshop Apply step for this read-only acceptance mission.
