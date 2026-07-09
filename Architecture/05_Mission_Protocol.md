# Mission Protocol

A mission is work submitted to FOXAI.

## Mission Flow

1. Request received
2. Mission Planner classifies intent
3. Capability Gap Analyzer checks requirements
4. Fleet Command assigns shuttles
5. Bridge Officers review responsibilities
6. Mission Executor runs safe actions
7. Vault records results
8. Captain's Log receives summary
9. Bridge UI displays final report

## Mission Status Values

- queued
- planning
- blocked
- running
- complete
- complete_with_warnings
- failed
- cancelled

## Safety Modes

- plan_only
- safe
- supervised
- full

Default mode is safe.
Dangerous file/system changes require explicit approval.
