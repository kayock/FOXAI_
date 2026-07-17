# FOXAI USB C2-A — Approved Portable Path Commissioning Patch Apply

Exact operator approval received:

```text
APPROVE USBC2 391F401AD6B9
```

Approved plan ID:

```text
391f401ad6b95565f775d0f232581b0667c46dadbcd4bfa3ffc3aa5822a0b0c4
```

## Exact operation

Back up and modify only:

```text
COMMISSION_FOXAI_USB.bat
System\Commissioning\commission_usb.py
```

The commissioning guide remains unchanged.

Expected hash transitions:

```text
COMMISSION_FOXAI_USB.bat
Before: 3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b
After:  253fda6a7b57271e688063374bd6be8507671a540a42984c60a40dc9b8ce5663

System\Commissioning\commission_usb.py
Before: cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869
After:  39785314b4dca4e8fc51076cea97e8e7f73c2c655613d61acfa4dcdf72954654
```

Backups are created under:

```text
Backups\USBC2_Commissioning\<timestamp>\
```

The package stages both files, verifies hashes and Python syntax, creates verified
backups, replaces only the two approved files, rechecks the unchanged guide, and
rolls both files back if verification fails.

It does not rerun commissioning automatically. Upload the receipt first.
