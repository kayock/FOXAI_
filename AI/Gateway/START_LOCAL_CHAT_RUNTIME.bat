@echo off
title KayocktheOS Local Chat Runtime
color 0A
echo ==========================================
echo KayocktheOS Local Chat Runtime
echo ==========================================
echo.
echo This starter expects an OpenAI-compatible local server on port 8845.
echo.
echo Selected model:
echo Z:\FOXAI\Models\Chat\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
echo.
echo Option A: If using llamafile, run something like:
echo llamafile.exe -m "Z:\FOXAI\Models\Chat\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf" --server --host 127.0.0.1 --port 8845
echo.
echo Option B: If using llama.cpp server, run something like:
echo llama-server.exe -m "Z:\FOXAI\Models\Chat\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf" --host 127.0.0.1 --port 8845
echo.
echo After the runtime is started, test:
echo http://127.0.0.1:8844/api/runtime
echo.
pause
