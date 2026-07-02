@echo off
title LeadHunter AI Starter
cd /d "%~dp0"

echo ===================================================
echo   LeadHunter AI - Local Startup Script
echo ===================================================

echo.
echo [1/3] Checking/Starting PostgreSQL Database...
.\pgsql\bin\pg_ctl.exe -D ".\pgsql\data" -l logfile start

echo.
echo [2/3] Scheduling Browser Launch...
start /b cmd /c "timeout /t 3 >nul & start http://localhost:5000"

echo.
echo [3/3] Starting Flask Application Server...
echo Press CTRL+C to stop the server.
echo.
.\.venv\Scripts\python.exe app.py

pause
