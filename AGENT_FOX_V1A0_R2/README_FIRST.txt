AGENT FOX TECHNICAL CORE V1A-0 R2
Mission: ENG-20260721-042128-CF3008

This R2 package supersedes the first V1A-0 package.
Do not preview or apply the earlier package.

DROP/EXTRACT:
Place the included AGENT_FOX_V1A0_R2 folder directly in Z:\FOXAI\

RESULTING PLAN PATH:
Z:\FOXAI\AGENT_FOX_V1A0_R2\PLAN.json

R2 SAFETY NARROWING:
- No subprocess module in the collector
- No discovery or launch-probing of other Python interpreters
- No FOXAI source imports or execution
- No launcher execution
- No model loading
- No Windows process/service/task/port inspection yet
- No network or package installation
- Static, bounded inspection only
- 32 MiB output ceiling

The Engineering Workshop preview and final implementation receipt remain authoritative.
