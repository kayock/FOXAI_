FOXAI USB C3L — PORTABILITY CLOSURE AND KNOWN-GOOD BASELINE SEAL

This is the final metadata-only closure stage for the verified portable
ComfyUI CPU runtime.

C3L will:
  * bind to the exact accepted C3K evidence;
  * require the normal controller to be STOPPED and port 8188 to be free;
  * re-hash all 39,046 isolated dependency files before sealing;
  * verify all 11 normal lifecycle files and 4 protected files;
  * create a compact known-good baseline directory and complete file manifest;
  * add an offline baseline verifier and routine-use instructions;
  * re-hash the isolated runtime again after the metadata commit;
  * create a compact review ZIP.

C3L will NOT launch ComfyUI or FOXAI, access the network, modify the isolated
runtime, edit launch behavior, install/uninstall packages, delete logs, or
copy the 1.5 GB runtime into the baseline. The baseline is content-addressed
verification metadata, not a duplicate runtime.

Run:
  RUN_USB_C3L_SEAL.bat

The window pauses on both success and failure.
