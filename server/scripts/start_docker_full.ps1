Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.yml"
$dockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

function Wait-ForDocker {
    param(
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            docker info *> $null
            return $true
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    return $false
}

Write-Host "Iniciando entorno Docker completo..." -ForegroundColor Cyan

if (-not (Test-Path $dockerDesktopExe)) {
    throw "No se encontro Docker Desktop en: $dockerDesktopExe"
}

if (-not (Wait-ForDocker -TimeoutSeconds 3)) {
    Write-Host "Docker Desktop no estaba activo. Abriendo Docker Desktop..." -ForegroundColor Yellow
    Start-Process -FilePath $dockerDesktopExe -WindowStyle Hidden
}

if (-not (Wait-ForDocker)) {
    throw "Docker Desktop no quedo disponible a tiempo. Abre Docker Desktop y espera a que el motor inicie."
}

Push-Location $projectRoot
try {
    docker compose -f $composeFile up -d --build
    docker compose -f $composeFile ps
    Write-Host ""
    Write-Host "Servicios listos:" -ForegroundColor Green
    Write-Host "  App:        http://127.0.0.1:8000"
    Write-Host "  Login:      http://127.0.0.1:8000/auth/login"
    Write-Host "  MongoDB:    mongodb://127.0.0.1:27017"
    Write-Host "  Redis:      redis://127.0.0.1:6379"
    Write-Host "  PocketBase: http://127.0.0.1:8090"
    Write-Host ""
    Write-Host "Para ver logs:"
    Write-Host "  docker compose logs -f app"
} finally {
    Pop-Location
}
