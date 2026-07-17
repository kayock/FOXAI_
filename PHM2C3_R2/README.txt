FOXAI Portable Host Model Library Phase 2C3 R2
Read-Only Portability Validation

Extract the PHM2C3 folder directly inside the FOXAI root:

  Z:\FOXAI\PHM2C3_R2\

First run:

  Z:\FOXAI\PHM2C3_R2\VERIFY_PACKAGE.bat

Expected:

  State: portability_validation_package_verified
  Verified: True
  Apply capability present: False
  Live files modified: False
  Live registry modified: False
  Model files modified: False

Then run:

  Z:\FOXAI\PHM2C3_R2\RUN_PORTABILITY_VALIDATION.bat

The validator uses the live registry only for read-only inventory. Every
state-changing behavior is tested with tiny temporary fixtures in the
timestamped report folder.

When it finishes, upload the file it prints:

  Reports\HostModelValidation\PHM2C3_R2_<timestamp>\PHM2C3_RESULTS.zip

No approval phrase is needed because this package has no apply capability.

R2 correction:
  R1 passed all live read-only checks, then stopped before the isolated
  matrix because state() was called positionally even though its
  include_catalog argument is keyword-only.

  R2 corrects both calls and was build-tested through the complete isolated
  scenario matrix.

Do not rerun the R1 package.
