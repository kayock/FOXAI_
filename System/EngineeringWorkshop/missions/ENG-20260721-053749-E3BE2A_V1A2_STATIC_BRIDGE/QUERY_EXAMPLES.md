# Agent Fox Technical Core V1A-2 Query Examples

All queries are read-only and search the generated static indexes. A static reference does not prove that a component is running.

```text
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode search --term source_locator
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode explain --path core\foxai_web.py
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode trace-launcher --path START_FOXAI_WEB_WITH_COMFYUI.bat
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-symbol --term run_app
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-setting --term model
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode find-references --term source_locator
python static_code_launcher_bridge_v1.py query --index-dir <V1A2_OUTPUT> --mode compare-known-good
```
