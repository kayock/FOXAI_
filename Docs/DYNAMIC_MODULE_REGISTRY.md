# Dynamic Module Registry

v0.5.0 introduces department-level `module.yaml` files.

The Core can discover modules from major departments and build:

```text
System/Registry/modules/
System/Registry/modules/modules.json
```

Run manually:

```bat
python System\Registry\build_registry.py
```

## Why

Departments should advertise themselves. The Bridge should not depend on hardcoded module lists forever.
