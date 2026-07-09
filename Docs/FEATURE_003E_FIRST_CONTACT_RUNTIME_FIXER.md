# Feature 003E - First Contact Runtime Fixer

This patch hard-locks First Contact to:

```text
Z:\FOXAI\Engine\llama-server.exe
```

It chooses a chat model from:

```text
Z:\FOXAI\Models\Chat
```

Preferred model:

```text
DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
```

Then it rewrites:

```text
AI\Gateway\FIRST_CONTACT_START_RUNTIME.bat
```

Run that BAT after installing this patch.
