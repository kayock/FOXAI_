# FOXAI USB C2 FIX1 — Portable Path Patch Preview

The verified capture proves that the full USB-owned portable runtime already
contains and imports `customtkinter`, `PIL`, `requests`, and `psutil`.

## Exact proposed scope

Modify only:

```text
COMMISSION_FOXAI_USB.bat
System\Commissioning\commission_usb.py
```

The correction:

- Prefers `Runtime\Desktop\python\python.exe`
- Exposes `Runtime\Desktop\site-packages` and
  `Runtime\Core\site-packages`
- Separates portable, legacy, venv, and host probe environments
- Adds `PORTABLE_READY`, `HOST_ASSISTED_READY`, and `NEEDS_ATTENTION`
- Reports an external `.venv` warning only when that venv is actually selected
- Prevents an unused external `.venv` from downgrading a verified portable result

The guide and every other FOXAI file remain unchanged.

## Approval

Plan ID:

```text
391f401ad6b95565f775d0f232581b0667c46dadbcd4bfa3ffc3aa5822a0b0c4
```

Exact approval phrase:

```text
APPROVE USBC2 391F401AD6B9
```

This package has no apply capability.
