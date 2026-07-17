# FOXAI USB C2 FIX2 — Portable Path Patch Preview

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


## FIX2 correction

FIX1 failed closed because its verifier contained two incorrect comparison
values:

- It expected the proposed Python hash in the live-file slot.
- It retained the prior preview's proposed Python hash in the proposed-file slot.

FIX2 now verifies the exact reviewed values:

```text
Live before: cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869
Proposed:    39785314b4dca4e8fc51076cea97e8e7f73c2c655613d61acfa4dcdf72954654
```

The proposed patch and plan are unchanged. The only valid approval phrase remains:

```text
APPROVE USBC2 391F401AD6B9
```
