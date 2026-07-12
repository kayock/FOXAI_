# Feature 001 - Local Chat

This is the first complete feature target for KayocktheOS.

## Goal

A local model answers through:

```text
POST http://127.0.0.1:8844/api/chat
```

## What this patch adds

- `AI/local_chat.py`
- `/api/local-chat`
- `AI/Gateway/START_LOCAL_CHAT_RUNTIME.bat`
- automatic suggested model selection from FOXAI inventory

## Manual runtime start

Open:

```text
Z:\KayocktheOS\AI\Gateway\START_LOCAL_CHAT_RUNTIME.bat
```

It shows the exact model selected and the expected llamafile or llama.cpp command shape.

## Next confirmation needed

We still need the actual runtime executable path, such as:

```text
Z:\FOXAI\llamafile.exe
```

or:

```text
Z:\FOXAI\llama.cpp\llama-server.exe
```
