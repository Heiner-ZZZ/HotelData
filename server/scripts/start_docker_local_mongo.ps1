param(
    [switch]$WithPocketBase
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.local-mongo.yml"
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

Write-Host "Iniciando entorno Docker con Mongo local de Windows..." -ForegroundColor Cyan

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
    if ($WithPocketBase) {
        docker compose -f $composeFile --profile pocketbase up -d --build
        docker compose -f $composeFile --profile pocketbase ps
    } else {
        docker compose -f $composeFile up -d --build
        docker compose -f $composeFile ps
    }
    Write-Host ""
    Write-Host "Servicios listos:" -ForegroundColor Green
    Write-Host "  App:        http://127.0.0.1:8000"
    Write-Host "  Login:      http://127.0.0.1:8000/auth/login"
    Write-Host "  Redis:      redis://127.0.0.1:6379"
    Write-Host "  PocketBase: http://127.0.0.1:8090 (si usaste -WithPocketBase)"
    Write-Host ""
    Write-Host "Para ver logs:"
    if ($WithPocketBase) {
        Write-Host "  docker compose -f docker-compose.local-mongo.yml --profile pocketbase logs -f app"
    } else {
        Write-Host "  docker compose -f docker-compose.local-mongo.yml logs -f app"
    }
} finally {
    Pop-Location
}
