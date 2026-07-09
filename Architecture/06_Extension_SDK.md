# FOXAI Extension SDK

Extensions allow FOXAI to grow without modifying the protected core.

## Extension Types

- Department
- Shuttle
- Tool Adapter
- Professor
- UI Panel
- Knowledge Pack
- Model Provider

## Required Extension Contract

- manifest
- health()
- capabilities()
- invoke(action, payload)
- shutdown()

## Recommended Lifecycle

- discover
- validate
- register
- health_check
- activate
- invoke
- deactivate

## Compatibility Rule

Extensions declare the FOXAI API version they support.

Example:

api_version: foxai.extension.v1
