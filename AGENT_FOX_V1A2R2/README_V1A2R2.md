# Agent Fox Technical Core V1A-2R2

Mission: `ENG-20260721-063725-BFCAB9`

This isolated repair preserves the successful V1A-2R1 parser and sharding work while correcting its failed determinism validation. The live FOXAI tree is captured once into memory. Two complete core-and-shard builds are generated from that same immutable capture and compared byte for byte. A later bounded hash-only pass reports live drift separately.

No raw source capture is persisted. No launcher, model, FOXAI module, PowerShell script, service, task, or repair action is executed. No network or package installation is used.
