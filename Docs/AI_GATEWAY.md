# AI Gateway

v1.3.0 creates the safe AI Gateway layer.

## Endpoints

```text
GET  http://127.0.0.1:8844/api/ai-gateway
POST http://127.0.0.1:8844/api/chat
```

`/api/chat` is a placeholder until a local model runtime is connected.

## Safety

- Advisor-only mode by default
- No write access
- Operator approval required
- No automatic project edits
