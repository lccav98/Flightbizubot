$ErrorActionPreference = 'Stop'
$botRoot = $PSScriptRoot
$botPython = Join-Path $botRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $botPython)) {
    $botPython = (Get-Command python -ErrorAction Stop).Source
}
$botMain = Join-Path $botRoot 'main.py'
$botStop = Join-Path $botRoot '.radar-stop'
$botLock = Join-Path $botRoot '.radar.lock'
$botSupervisorLog = Join-Path $botRoot 'supervisor.log'
Set-Location -LiteralPath $botRoot

# Hold an exclusive handle for the entire supervisor lifetime.
try {
    $botHandle = [IO.File]::Open($botLock, 'OpenOrCreate', 'ReadWrite', 'None')
} catch [IO.IOException] {
    exit 0 # Another supervisor already owns this checkout.
}
try {
    if (Test-Path -LiteralPath $botStop) { Remove-Item -LiteralPath $botStop }
    while (-not (Test-Path -LiteralPath $botStop)) {
        Add-Content -LiteralPath $botSupervisorLog -Value "$(Get-Date -Format o) Starting bot."
        $botProcess = Start-Process -FilePath $botPython -ArgumentList @('-u', ('"' + $botMain + '"')) `
            -WorkingDirectory $botRoot -WindowStyle Hidden -Wait -PassThru `
            -RedirectStandardOutput (Join-Path $botRoot 'radar.log') `
            -RedirectStandardError (Join-Path $botRoot 'radar_err.log')
        Add-Content -LiteralPath $botSupervisorLog -Value "$(Get-Date -Format o) Bot stopped; exit=$($botProcess.ExitCode)."
        if (-not (Test-Path -LiteralPath $botStop)) { Start-Sleep -Seconds 15 }
    }
} finally {
    $botHandle.Dispose()
}
