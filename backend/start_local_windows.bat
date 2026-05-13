@echo off
cd /d "%~dp0"
set VITALMOTION_DB=%~dp0VitalMotion_v20_6_MVP_v077_SQLITE_CONNECTED.sqlite
python -m uvicorn app_v077_sqlite_connected:app --host 127.0.0.1 --port 8080
pause
