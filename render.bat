@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
if errorlevel 1 goto failed
".venv\Scripts\python.exe" setup_tools.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" main.py --config config.json --user-config user_config.json --render
if errorlevel 1 goto failed
echo Render and verification complete. See output and qa folders.
pause
exit /b 0
:failed
echo Render did not complete successfully. Read the error above and README.md.
pause
exit /b 1
