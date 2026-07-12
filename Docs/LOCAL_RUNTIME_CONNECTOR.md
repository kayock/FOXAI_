# Local Runtime Connector

v1.4.0 connects the AI Gateway to an OpenAI-compatible local model runtime.

## Endpoints

```text
GET  http://127.0.0.1:8844/api/runtime
POST http://127.0.0.1:8844/api/chat
```

## Expected local model runtime

```text
http://127.0.0.1:8845/v1/chat/completions
```

If no model runtime is running, `/api/chat` fails safely and explains what to start.
