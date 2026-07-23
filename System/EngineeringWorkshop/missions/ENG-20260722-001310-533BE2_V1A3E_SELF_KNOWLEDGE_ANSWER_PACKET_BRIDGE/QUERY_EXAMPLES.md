# Agent Fox Provenance Self-Knowledge Query Examples

The bridge reads only the verified V1A-3D registry. It does not scan live source or probe runtimes.

## JSON request

```json
{"request_id":"EX-1","intent":"summarize_context","context":"workshop_main"}
```

## Single-request text

```text
summarize context workshop main foxai.py
```

## Supported intent families

1. list protected contexts
2. contexts for a launcher
3. launcher-to-runtime-to-entry mapping
4. summarize one context
5. unresolved imports or branches
6. package candidates
7. runtime uncertainty
8. linked contexts
9. authoritative evidence locator
10. compare two contexts
11. six-context Technical Core coverage

Ambiguous selectors produce a structured clarification packet rather than a guess.
Unresolved candidates are never presented as installed, confirmed, active, missing at runtime, or broken.
