Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "C:\Python314\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "No se encontro Python en: $pythonExe"
}

Write-Host "Levantando la app local en http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/c","cd /d $projectRoot && $pythonExe -m uvicorn src.app.main:app --host 127.0.0.1 --port 8000" -WindowStyle Hidden
Start-Sleep -Seconds 4

$portCheck = Test-NetConnection 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue
if (-not $portCheck.TcpTestSucceeded) {
    throw "La app no quedo escuchando en el puerto 8000. Revisa si hay otra instancia ocupando el puerto."
}

Write-Host "App lista:" -ForegroundColor Green
Write-Host "  Login:     http://127.0.0.1:8000/auth/login"
Write-Host "  Dashboard: http://127.0.0.1:8000/dashboard"
