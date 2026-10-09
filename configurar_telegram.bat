@echo off
chcp 65001 > nul
title Configuração do Telegram - Flight Bizu Bot
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe obter_chat_id.py
) else (
    python obter_chat_id.py
)

pause
