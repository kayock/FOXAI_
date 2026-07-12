@echo off
title KayocktheOS Selected Model Runtime
color 0A
echo ==========================================
echo KayocktheOS Local AI Runtime
echo ==========================================
echo.
echo Runtime: llama-server.exe
echo Model: Qwen3VL-8B-Instruct-Q4_K_M.gguf
echo Port: 8845
echo.
echo Leave this window open while chatting.
echo.
Z:\FOXAI\Engine\llama-server.exe -m Z:\FOXAI\Models\Chat\Qwen3VL-8B-Instruct-Q4_K_M.gguf --host 127.0.0.1 --port 8845
pause
