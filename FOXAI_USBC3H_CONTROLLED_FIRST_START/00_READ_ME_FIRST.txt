FOXAI USB C3H — Controlled First Start

This is the first approved live ComfyUI start under the reviewed C3G contract.
It starts only the isolated CPU launcher on 127.0.0.1:8188, waits for local
health, records logs/process/network evidence, then stops ComfyUI before exit.

It does not edit launchers, install packages, enable custom nodes, expose the
server beyond localhost, or leave ComfyUI running.

Run:
  RUN_USB_C3H_FIRST_START.bat

After completion upload the generated UPLOAD_THIS_C3H_REVIEW.zip from the
newest START_OUTPUT folder.
