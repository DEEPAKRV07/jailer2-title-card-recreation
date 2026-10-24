@echo off
setlocal
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer and enable Add Python to PATH.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" setup_tools.py
exit /b %errorlevel%
