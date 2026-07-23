AGENT FOX TECHNICAL CORE V1B-2E R1
REAL GUI SHARED RESOURCE ROUTING GAP PREFLIGHT

Mission: ENG-20260722-223348-83B942

1. Extract this AGENT_FOX_V1B2E_R1_PREFLIGHT folder directly into Z:\FOXAI.
2. Double-click RUN_V1B2E_R1_PREFLIGHT.cmd.
3. Return the final JSON result to Sol.

This is a bounded read-only static preflight. It reads the installed WebUI,
Desktop, Technical Core routing helpers, and only relevant first-party modules
imported by the two GUI entry sources. It does not recursively search the drive.

It does not launch FOXAI or ComfyUI, load a model, call a model, inspect live
processes/listeners, use the network, modify source files, install packages,
change services/startup/registry, or access K:.

It writes exactly eight evidence JSON files under:
Z:\FOXAI\System\EngineeringWorkshop\missions\
ENG-20260722-223348-83B942_V1B2E_R1_REAL_GUI_ROUTING_GAP_PREFLIGHT
