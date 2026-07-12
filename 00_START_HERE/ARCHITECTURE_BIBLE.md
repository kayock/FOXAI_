# KayocktheOS Architecture Bible

## Core/Shell Architecture

The Core manages logic, configuration, health checks, logs, module registry, and local APIs.

The Shell is Kayock Browser. It owns the Operator-facing experience.

## v0.1.2 Principle

The Operator should see the Bridge Dashboard, not raw JSON.

Raw JSON remains available for debugging at:

```text
http://127.0.0.1:8844/api/status
```
