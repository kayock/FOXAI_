# Engineering Workshop V1.1 integration

This package connects the existing controlled Workshop worker to the live
`core/engineer_agent.py` route documented in the public FOXAI repository.

## Integration boundary

The patch is intentionally narrow:

1. import `EngineeringWorkshopBridge` with a fail-soft fallback;
2. instantiate it beside `EngineerIntent`;
3. intercept only explicit `/engineer workshop ...` commands before the normal
   read-only Engineer analysis path;
4. leave all ordinary Engineer routes unchanged.

## Write boundary

A write requires all of the following:

- a staged mission classified as `implement` or `repair`;
- explicit implementation authorization language in that mission;
- a valid `foxai.engineering.plan.v1` JSON plan;
- a successful exact diff preview;
- the operator repeating `APPLY <exact plan SHA-256>` through the UI;
- a targeted snapshot;
- atomic text-file writes only;
- approved local validations;
- automatic snapshot restoration after any failure;
- a JSON receipt generated from actual tool results.

Deletion, rename, shell command strings, network use, package installation,
symlink writes, protected-path writes, and paths outside the approved FOXAI
root remain unsupported.
