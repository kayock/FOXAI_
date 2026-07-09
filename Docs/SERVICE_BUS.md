# Service Bus

v0.7.0 introduces the first internal Service Bus.

## Purpose

The Service Bus lets KayocktheOS departments advertise services and capabilities without every department directly depending on every other department.

## Current services

- System Service
- Model Service
- Module Service
- Bridge Service
- Academy Service
- Repair Bay Service
- Knowledge Service
- Creative Studio Service

## API endpoints

```text
/api/services
/api/events
/api/bridge
```

## Rule

Departments should communicate through services, not through random direct file coupling.
