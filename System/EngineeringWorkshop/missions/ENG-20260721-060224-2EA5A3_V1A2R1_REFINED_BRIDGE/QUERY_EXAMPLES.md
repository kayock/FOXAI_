# Agent Fox Technical Core V1A-2R1 Query Examples

All queries are static and read-only. A reference is not proof that a component is active or was executed.

```text
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode search --term source_locator
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode explain --path core\foxai_web.py
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode trace-launcher --path START_FOXAI_WEB_WITH_COMFYUI.bat
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode find-symbol --term run_app
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode find-setting --term model
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode find-references --term source_locator
python static_code_launcher_bridge_v1r1.py query --index-dir <V1A2R1_OUTPUT> --mode compare-known-good
```
