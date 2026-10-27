@echo off
chcp 65001 > nul
echo Encerrando instâncias em segundo plano do Radar de Viagens...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_background.ps1"
echo Concluído! O agente foi finalizado.
pause
