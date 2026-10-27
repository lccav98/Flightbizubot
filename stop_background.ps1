$ErrorActionPreference = 'Stop'
$botRoot = $PSScriptRoot
$botMain = Join-Path $botRoot 'main.py'
New-Item -ItemType File -Path (Join-Path $botRoot '.radar-stop') -Force | Out-Null
# Only stop this checkout, never unrelated Python scripts named main.py.
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($botMain) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
Write-Output 'Radar stopped. Start start_background.vbs to resume.'
