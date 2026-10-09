@echo off
chcp 65001 > nul
echo Configurando Inicialização Automática no Windows para rodar 24/7...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut(\"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\RadarViagens.lnk\"); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%~dp0start_background.vbs\"'; $s.WorkingDirectory = '%~dp0'; $s.Save()"
echo.
echo Pronto! O atalho foi adicionado à pasta de Inicialização do Windows.
echo O Radar de Viagens iniciará automaticamente em segundo plano sempre que você ligar o computador.
echo.
pause
