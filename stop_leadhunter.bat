@echo off
title LeadHunter AI Stopper
cd /d "%~dp0"

echo ===================================================
echo   LeadHunter AI - Local Shutdown Script
echo ===================================================

echo.
echo Stopping PostgreSQL Database...
.\pgsql\bin\pg_ctl.exe -D ".\pgsql\data" stop

echo.
echo Database stopped safely. You can now close this window.
pause
