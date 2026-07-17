MMQ8A — Official Qwen3VL 8B Q8 Vision Projector Downloader

WHY THIS IS NEEDED
------------------
The VIT1 real-image benchmark verified that both Qwen3VL language-model GGUFs
are present, but no multimodal projector file exists under the FOXAI Models
tree.

llama-server therefore loaded Fast Vision as a text model and returned:

    image input is not supported
    hint: you may need to provide the mmproj

OFFICIAL FILE
-------------
Repository:
    Qwen/Qwen3-VL-8B-Instruct-GGUF

Pinned commit:
    00e7d63528e65d7b64e80e1293a8360b4af6a594

File:
    mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf

Official SHA-256:
    c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd

Target:
    Z:\FOXAI\Models\Chat\mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf

Qwen's official repository states that language-model and vision-projector
precision levels may be mixed. The Q8 projector can therefore be tested with
both the Q4 Fast Vision language model and the Q8 Quality Vision language
model.

INSTALL
-------
Extract the complete folder to:

    Z:\FOXAI\MMQ8A\

Run:

    DOWNLOAD.bat

Exact approval phrase:

    DOWNLOAD OFFICIAL QWEN3VL Q8 MMPROJ

SAFETY
------
- source URL is pinned to an exact official Qwen repository commit;
- expected SHA-256 is pinned to the official file;
- downloads to a .part file;
- supports resuming after a network interruption;
- never treats a partial file as installed;
- refuses to overwrite a different existing target;
- atomically renames only after the complete SHA-256 passes;
- changes no FOXAI source, configuration, archive, or security log;
- creates RECEIPT.json.

SUCCESS
-------
The receipt must say:

    State: installed_verified
    Verified: True

It may instead say:

    State: already_installed_verified
    Verified: True

AFTER SUCCESS
-------------
Rerun:

    Z:\FOXAI\VIT1\RUN_BOTH.bat
