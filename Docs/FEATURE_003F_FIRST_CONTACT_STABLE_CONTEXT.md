# Feature 003F - First Contact Stable Context

This patch applies the known-good runtime command:

```text
Z:\FOXAI\Engine\llama-server.exe -m Z:\FOXAI\Models\Chat\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf --host 127.0.0.1 --port 8845 -c 4096
```

The important fix is:

```text
-c 4096
```

This prevents the KV cache allocation failure caused by the huge default context.
