@echo off
title Install FOXAI Requirements
cd /d "%~dp0"
python -m pip install -r requirements.txt
pause
