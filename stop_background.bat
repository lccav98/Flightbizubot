@echo off
chcp 65001 > nul
echo Encerrando instâncias em segundo plano do Radar de Viagens...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Concluído! O agente foi finalizado.
pause
