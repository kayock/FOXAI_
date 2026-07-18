# C3F design boundary

C3F separates **activation proof** from **operational launch**.

The portable activation contract is:

1. Start the USB-owned `Runtime\Desktop\python\python.exe` with `-I -B -S`.
2. Clear inherited `PYTHONHOME` and `PYTHONPATH`.
3. Add only `Runtime\ComfyUI\site-packages` through `site.addsitedir()`.
4. Add only the USB `ComfyUI` source directory.
5. Forward the reviewed CPU arguments to `ComfyUI\main.py`.

C3F proves steps 1–4 and compiles `main.py`, but deliberately does not execute it.
It inventories current direct launch paths and generates proposals. C3G may apply a
reviewed integration with no launch. The first actual ComfyUI process remains a
later controlled-start gate.
