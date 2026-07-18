FOXAI USB C4F — DUAL-PROFILE KNOWN-GOOD BASELINE SEAL AND C4 CLOSURE

C4F is a metadata-only closure stage. It creates a second-generation known-good
baseline for the verified FOXAI WebUI dual-profile ComfyUI capability while
preserving the original C3 baseline unchanged as historical rollback evidence.

C4F will:
  * bind to all 41 exact accepted C4E evidence files;
  * verify the immutable C3 baseline and current C3 pointer;
  * require FOXAI WebUI and ComfyUI to be stopped and ports 8765/8188 free;
  * re-hash all 39,046 isolated dependency files before and after sealing;
  * verify the four C4D-integrated files, eight protected files, and approved node;
  * create a new immutable C4 dual-profile baseline;
  * atomically update the current-baseline pointer and offline verifier;
  * preserve backups of every replaced metadata file;
  * create a compact review ZIP.

C4F will NOT launch FOXAI, WebUI, Desktop, ComfyUI, or a browser. It will not
access the external network, install/uninstall packages, modify launchers,
change the approved node, edit the isolated runtime, or delete logs/history.

Run:
  RUN_USB_C4F_SEAL.bat

The window pauses on both success and failure.
