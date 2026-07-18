FOXAI USB C4E-R4 - CONTROLLED WEBUI TWO-PROFILE LIFECYCLE TEST

R4 REVIEWED REPAIR
C4E-R3 completed the complete two-profile lifecycle successfully:

- FOXAI WebUI became healthy.
- Legacy GET selected Safe Normal CPU.
- Safe Normal CPU became healthy and stopped cleanly.
- Explicit POST selected Approved Custom Nodes CPU.
- SaveImageWebsocket registered and its approved hash remained verified.
- Switching to Safe Normal CPU while approved mode was healthy was refused.
- Approved mode stopped cleanly.
- Final ComfyUI state was STOPPED.
- FOXAI WebUI stopped and port 8765 closed.
- No browser or external network activity occurred.

R3 then stopped on a false final audit-parser mismatch. The R3 wrapper records:
  c4e.guard.Popen / allowed_exact_manager_command
followed by:
  subprocess.Popen / allowed_guarded_manager_command

The older parser still searched subprocess.Popen for the first label.

R4 changes only the sealed C4E evidence parser:
- Recognizes the R3 high-level guarded-command records.
- Requires each guarded command to pair one-for-one with an authorized
  platform subprocess audit event.
- Allows only status, stop, Safe Normal CPU spawn, and Approved Custom Nodes
  CPU spawn.
- Requires the expected lifecycle command counts.
- Rejects denied events, unknown commands, unpaired process events, and
  external socket denials.
- Continues to run the complete post-test boundary, runtime, node, operational
  storage, and final-process checks.
- Does not change FOXAI, ComfyUI, either profile, or any live file.

RUN
Extract this complete folder directly under Z:\FOXAI, replacing files only
inside this C4E package folder. Preserve the existing TEST_OUTPUT directory.
Then run:
  RUN_USB_C4E_TEST.bat

EXPECTED SUCCESS
  C4E_WEBUI_TWO_PROFILE_LIFECYCLE_VERIFIED_STOPPED_READY_FOR_C4F_BASELINE_SEAL_REVIEW

UPLOAD
Upload the newest:
  TEST_OUTPUT\<UTC-run>\UPLOAD_THIS_C4E_REVIEW.zip
