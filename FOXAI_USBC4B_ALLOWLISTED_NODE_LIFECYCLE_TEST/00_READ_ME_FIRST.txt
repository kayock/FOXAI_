FOXAI USB C4B — CONTROLLED ALLOWLISTED CUSTOM-NODE TEST

This is a controlled live test. It starts ComfyUI only on 127.0.0.1:8188
with CPU mode, disables all custom nodes, and native-whitelists exactly:

  websocket_image_save.py
  SHA-256 0b66b69eb7dab007d55bf63c5bd0f1343dcfbc2f5a350983f906ba2cd3dd5d23

The test verifies node registration, child audit events, local health, process
ownership, localhost-only networking, graceful stop, and all sealed boundaries.
It does not modify the WebUI or install/enable any permanent profile.

Extract this complete folder under Z:\FOXAI and run:
  RUN_USB_C4B_TEST.bat

After completion upload the newest:
  TEST_OUTPUT\<timestamp>\UPLOAD_THIS_C4B_REVIEW.zip
