# Phase 2C3 R1 Failure Diagnosis

R1 completed all live read-only checks successfully:

- protected baselines matched;
- the `DESKTOP-G9ERN9B` profile was present;
- the host model was registered and readable;
- 10 USB models and 1 host-PC model were detected;
- no-silent-switch and never-modify-model policies passed;
- LAN and online providers remained disabled;
- the WebUI no-fallback contract passed.

It then stopped before the isolated scenario matrix because the temporary
validator called a keyword-only method positionally:

```text
state(False)
state(True)
```

R2 uses:

```text
state(include_catalog=False)
state(include_catalog=True)
```

No live file, registry, model, process, launcher, or network state changed.
The validation scope is unchanged.
