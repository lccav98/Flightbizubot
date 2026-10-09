@echo off
chcp 65001 > nul
title Flight Bizu Bot (@Flightbizubot) 24/7
cd /d "%~dp0"
echo ===================================================
echo   ✈️ Flight Bizu Bot (@Flightbizubot) 24/7
echo ===================================================

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)

pause
