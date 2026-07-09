# FOXKernel Specification

FOXKernel is the central entry point for FOXAI Command OS.

Responsibilities:

- Boot core services
- Load department manifests
- Initialize MissionBus
- Initialize Fleet Registry
- Initialize Extension Manager
- Initialize Bridge API
- Expose system status
- Write kernel reports
- Provide a stable API for all modules

FOXKernel should not contain department-specific business logic.

FOXKernel asks departments what they provide.
It does not assume what they provide.

## Required Kernel API v1

- boot()
- status()
- shutdown()
- command(request)
- list_departments()
- list_services()
- list_capabilities()
- publish_event(event)
- subscribe(event_type, handler)
