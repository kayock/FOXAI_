# FOXAI USB C2 — Portable Path Patch Preview

The verified capture proves:

- The full portable Python runs.
- `customtkinter` and `PIL` load from `Runtime\Desktop\site-packages`.
- `requests` and `psutil` load from `Runtime\Core\site-packages`.
- The current commissioner still selects legacy `env\python` first and does not
  expose those sibling package folders.

## Exact proposed scope

Modify only:

```text
COMMISSION_FOXAI_USB.bat
System\Commissioning\commission_usb.py
```

No guide, launcher other than the commissioner BAT, runtime, package, model,
configuration, shortcut, or ComfyUI file changes.

## Proposed result

- Commissioning prefers the full portable Desktop Python.
- Portable Desktop/Core package paths are explicit.
- Portable and host-assisted environments are probed separately.
- The report includes `runtime_mode`:
  - `PORTABLE_READY`
  - `HOST_ASSISTED_READY`
  - `NEEDS_ATTENTION`
- Commissioning remains read-only and performs no installation, repair, or
  automatic launch.

## Approval

Plan ID:

```text
ae46a1151cd4abd717204a79fc5e53c6c98acd84713668f66d96e0abe8911eed
```

Exact approval phrase:

```text
APPROVE USBC2 AE46A1151CD4
```

This package has no apply capability.
