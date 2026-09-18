@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m app.local_desktop %*
if errorlevel 1 pause
