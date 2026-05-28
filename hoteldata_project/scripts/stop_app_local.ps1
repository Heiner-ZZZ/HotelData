Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if (-not $pythonProcesses) {
    Write-Host "No hay procesos python activos para detener."
    exit 0
}

foreach ($process in $pythonProcesses) {
    try {
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        Write-Host "Proceso detenido: $($process.Id)"
    } catch {
        Write-Host "No se pudo detener el proceso $($process.Id): $($_.Exception.Message)"
    }
}
