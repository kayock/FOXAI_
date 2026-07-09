@echo off
title Install ComfyUI Requirements
cd /d "%~dp0ComfyUI"
python -m pip install -r requirements.txt
pause
