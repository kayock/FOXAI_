# Agent Fox Technical Core V1B-2C

This integration adds the verified historical resource-evidence provider to the existing shared self-knowledge adapter used by both WebUI and Desktop.

Routing remains slash commands first, protected-context self-knowledge second, historical resource evidence third, and ordinary chat last. Current-live questions are not answered from historical evidence.

The WebUI and Desktop application source files remain unchanged. Their integration helpers only receive the new verified adapter hash and optional test-path parameters.

After a verified apply, restart both the FOXAI WebUI backend and FOXAI Desktop before live testing because already-running Python processes may retain the previous helper or adapter module.

No network access, model call, live system scan, process change, service change, startup change, registry write, source-evidence modification, or K: access is performed by this integration mission.
