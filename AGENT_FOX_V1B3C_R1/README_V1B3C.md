# Agent Fox Technical Core V1B-3C

Mission: `ENG-20260723-031118-BF49AE`

This mission integrates the already installed V1B-3A current-state request broker into
the canonical shared chat adapter in classification-only mode. The confirmed seam is
after the adapter's exact slash-command bypass and before selector normalization.

## Behavior

- Slash commands still pass through first.
- The broker is called with `authorization=None` and `providers={}`.
- Recognized current-state requests receive a clearly labeled non-execution answer.
- Historical/resource, unrelated, ambiguous, and disallowed requests continue through
  the existing proven adapter route.
- Unsupported-category interception requires a strong explicit live cue so phrases such
  as “which Python currently runs Workshop Main?” remain historical self-knowledge.

## Safety boundary

No live provider is connected. No live inspection, scan, process/service/listener query,
network access, model call, diagnosis, repair, optimization, recommendation, install,
service/startup/registry change, K: access, move, rename, or deletion occurs. No
current-state measurement is claimed.
