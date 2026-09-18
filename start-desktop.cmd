@echo off
cd /d "%~dp0"
echo CekFakta siap untuk ekstensi klik kanan. Biarkan jendela ini terbuka.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
