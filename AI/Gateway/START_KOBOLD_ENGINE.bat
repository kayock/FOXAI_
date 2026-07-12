@echo off
title KayocktheOS KoboldCpp Engine - Safe Portable
color 0A
echo ==========================================
echo KayocktheOS KoboldCpp Engine Adapter
echo Profile: Safe Portable
echo ==========================================
echo.
echo Engine:
echo Z:/KayocktheOS/Engine/KoboldCpp/koboldcpp.exe
echo.
echo Model:
echo Z:/FOXAI/Models/Chat/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf
echo.
echo Context:
echo 4096
echo.
echo Server:
echo http://127.0.0.1:5001
echo.
echo Leave this window open.
echo.
"Z:/KayocktheOS/Engine/KoboldCpp/koboldcpp.exe" --model "Z:/FOXAI/Models/Chat/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf" --port 5001 --contextsize 4096
pause
