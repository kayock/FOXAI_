AGENT FOX TECHNICAL CORE V1B-2E R4
PARTIAL-APPLY RECONCILIATION AND CLOSURE VERIFICATION

Mission: ENG-20260722-225500-4D0517

Purpose
-------
The Workshop reported BLOCKED — NOTHING CHANGED after an archive lookup failure,
but subsequent hashes show both intended cleanup edits are present. This package
verifies the exact intended post-state without attempting another edit.

Run
---
Extract AGENT_FOX_V1B2E_R4_RECONCILIATION directly into Z:\FOXAI, then run:

Z:\FOXAI\AGENT_FOX_V1B2E_R4_RECONCILIATION\RUN_V1B2E_R4_RECONCILIATION.cmd

This check writes only two evidence JSON files under the mission evidence folder.
It does not modify FOXAI source, launch a GUI or model, use the network, perform
live process/listener scans, or access K:.
