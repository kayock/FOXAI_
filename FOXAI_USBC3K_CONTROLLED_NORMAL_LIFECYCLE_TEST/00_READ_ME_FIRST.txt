FOXAI USB C3K — Controlled Normal Lifecycle Test

This gate exercises the installed Safe Normal CPU lifecycle exactly once:
  STOPPED -> start without browser -> HEALTHY -> graceful stop -> STOPPED

It uses the C3J normal controller, localhost 127.0.0.1:8188, CPU mode, and
disables all custom nodes. It does not edit launchers, install packages, open
a browser, force-kill a process, or leave ComfyUI running.

Run:
  RUN_USB_C3K_TEST.bat

After completion upload UPLOAD_THIS_C3K_REVIEW.zip from the newest TEST_OUTPUT folder.
