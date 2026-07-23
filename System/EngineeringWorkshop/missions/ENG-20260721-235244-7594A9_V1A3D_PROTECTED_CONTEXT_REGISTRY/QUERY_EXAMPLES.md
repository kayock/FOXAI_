# Protected Context Registry Query Examples

The query bridge reads only the generated V1A-3D registry outputs. It does not reopen or merge the six large closure graphs.

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action list-contexts
```

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action contexts-for-launcher --launcher "Z:\FOXAI\Launch FOXAI Workshop.bat"
```

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-context --context-id CTX-68030A15EE97A526
```

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-package-candidates --context-id CTX-5A02B9D4A8E26D64
```

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action show-runtime-uncertainty --context-id CTX-68030A15EE97A526
```

```bat
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S Z:\FOXAI\System\AgentFoxTechnicalCore\protected_context_registry_query_bridge_v1.py query --index-dir Z:\FOXAI\System\EngineeringWorkshop\missions\ENG-20260721-235244-7594A9_V1A3D_PROTECTED_CONTEXT_REGISTRY --action locate-fact --context-id CTX-5A02B9D4A8E26D64 --fact resolved_interpreter_path
```
