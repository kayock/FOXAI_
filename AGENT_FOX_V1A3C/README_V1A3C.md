# Agent Fox Technical Core V1A-3C

This isolated component builds recursive static Python dependency closures for the six protected known-good launcher contexts. It uses the verified V1A-2R2, V1A-3A-R1, and V1A-3B evidence sets.

It reads each indexed Python source file at most once into an in-memory immutable capture, verifies its current hash against the V1A-2R2 source index, and builds both deterministic passes from that same capture. Raw source content is not written into the generated evidence.

The mapper distinguishes module-load, function-local, class-body, optional ImportError-guarded, TYPE_CHECKING, platform, Python-version, literal-condition, and evidence-incomplete conditional imports. It follows only statically reachable first-party providers from each protected entry point and preserves cycles, unresolved branches, dynamic-import references, and path mutations as evidence rather than proof of execution.

No FOXAI source, launcher, package, model, Python entry point, shell command, or network operation is executed by the payload.
