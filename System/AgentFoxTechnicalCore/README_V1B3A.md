# Agent Fox Technical Core V1B-3A

Mission: `ENG-20260723-022511-401206`

This package installs an isolated policy-and-routing broker for explicit current-state
questions. It does not integrate the broker into Desktop, WebUI, or the shared chat
adapter in this stage.

## Installed files

- `current_state_request_broker_v1.py`
- `CURRENT_STATE_REQUEST_BROKER_CONTRACT_V1.json`
- `CURRENT_STATE_REQUEST_FIXTURES_V1.json`
- `README_V1B3A.md`

## Safety boundary

- Zero live-state providers are shipped.
- Providers must be injected through an allowlisted registry.
- Authorization must be explicitly approved and exactly `read_only`.
- Historical evidence is never substituted for current measurement.
- Slash commands bypass the broker.
- Diagnosis, repair, optimization, recommendations, writes, installs, monitoring,
  provider discovery, network access, and background scans are excluded.
- No existing Technical Core, Desktop, WebUI, Writer, Study, Repair Bay, runtime,
  model, launcher, archive, or personal file is modified.

A later separately approved mission may integrate this proven broker contract at the
canonical shared routing seam and may add individually approved bounded live providers.
