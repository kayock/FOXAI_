# Agent Fox Technical Core V1A-3E

Mission: `ENG-20260722-001310-533BE2`

V1A-3E converts the verified V1A-3D protected-context registry into deterministic,
claim-level provenance answer packets. It supports exactly eleven bounded intent
families, JSON requests, single-request text normalization, and validation-only mode.

Every factual claim carries the authoritative source mission ID, evidence filename,
evidence SHA-256, JSON field path or record locator, and source receipt SHA-256.
Ambiguous requests return a clarification packet instead of a guess.

The bridge never resolves the Workshop `python` command alias, never treats the
Desktop Recovery `pythonw.exe` identity or sys.path as directly probed, and never
infers runtime facts across contexts. Unresolved candidates are not labeled installed,
confirmed, active, missing at runtime, or broken.

This mission does not integrate the bridge into `foxai.py`, WebUI, or Agent Fox chat
routing. It does not scan live FOXAI source, execute launchers or runtimes, load models,
use the network, install packages, or access `K:`.
