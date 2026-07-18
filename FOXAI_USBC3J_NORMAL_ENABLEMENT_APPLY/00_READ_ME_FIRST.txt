FOXAI USB C3J — Normal Enablement Apply

This is a controlled write stage authorized by the operator after accepted C3I.
It applies the Safe Normal CPU lifecycle controller and wiring but DOES NOT run
any new launcher, controller, FOXAI interface, or ComfyUI.

Exact scope:
- Add five files: normal lifecycle manager, policy, and start/stop/status BATs.
- Replace six reviewed live launcher/WebUI files.
- Keep the isolated dependency target, portable Python, ComfyUI source, custom
  nodes, models, workflows, input/output, user files, and archives unchanged.
- Do not create Runtime\ComfyUI\state or Runtime\ComfyUI\logs\normal.

Run RUN_USB_C3J_APPLY.bat. The window pauses on success or failure.
Upload UPLOAD_THIS_C3J_REVIEW.zip from the newest APPLY_OUTPUT folder.
Do not perform a normal ComfyUI start until the C3J evidence is reviewed and
C3K receives fresh explicit operator approval.
