@echo off
cd /d "%~dp0"
"%~dp0env\python\python.exe" -c "import sys,json,os,pathlib,http.server,urllib.parse,datetime,subprocess,py_compile,shutil,importlib.util; print('PORTABLE PYTHON OK'); print(sys.version); print(sys.executable)"
pause
