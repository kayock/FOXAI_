# Agent Fox Technical Core V1A-3G

Mission: `ENG-20260722-005700-10980D`

V1A-3G installs one isolated, read-only shared chat adapter for the completed V1A-3E
self-knowledge answer-packet bridge. It does not connect the adapter to the WebUI or
Desktop yet and does not modify any live chat or model-routing source.

The public callable is:

`route_message(message, surface, request_id=None, selectors=None)`

Supported surfaces are `webui` and `desktop`. Recognized self-knowledge requests and
supported clarification requests bypass the model. Unsupported ordinary chat returns
a strict pass-through result without reading or verifying the V1A-3D registry.
Recognized requests fail closed with `evidence_error` when authoritative evidence does
not hash-verify; they never fall through to an ordinary model response.

The adapter hash-verifies and invokes the original V1A-3E bridge in-process. It does
not copy or reimplement the eleven-intent engine, registry verification, provenance,
synonym catalog, or uncertainty rules. Display text retains the complete unmodified
V1A-3E packet separately and labels every unresolved import or package item as an
unconfirmed candidate.

The validation suite runs all 34 V1A-3E cases on both chat surfaces, ordinary-chat and
unsupported-technical pass-through tests, supported ambiguity tests, and two copied-
fixture evidence-corruption tests. No live FOXAI source, launcher, runtime, model,
ComfyUI process, service, shell, network, package manager, or rollback drive K: is used.
