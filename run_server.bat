@echo off
cd /d "%~dp0"
echo Iniciando desde: %CD%
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
