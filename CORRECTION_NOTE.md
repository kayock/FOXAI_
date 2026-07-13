# Phase 1 Git Gate Correction

The original bundle incorrectly required the entire Git working tree to be clean. That conflicted with FOXAI's previously known suspicious root BAT filename and with untracked bundle files.

This corrected bundle:

- does not restore, delete, stage, or modify the known unrelated BAT entry;
- permits unrelated Git entries as advisories;
- blocks staged or unstaged changes to the reviewed Phase 1 target files;
- still requires exact SHA-256 baseline hashes before applying;
- still creates a timestamped backup and verifies post-copy hashes and tests;
- still rolls back and verifies restoration if a post-check fails.
