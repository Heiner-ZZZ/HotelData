# Compila el frontend Angular DENTRO de Docker (Node efímero: levanta, compila
# y se apaga — nunca queda un proceso Node residente en el host).
#
# Usa un VOLUME NOMBRADO para node_modules: el contenedor es Linux y necesita
# sus propios binarios (esbuild/ng) — montar el node_modules del host (Windows)
# rompe la compilación. La primera corrida hace `npm ci` (descarga, ~1-2 min);
# las siguientes reutilizan el volume y solo compilan. El `dist` se escribe en
# frontend/dist/frontend/browser, que el contenedor nginx sirve vía volumen
# (infra/docker-compose.yml → servicio frontend). Así un cambio de código NO
# requiere rebuild de imagen.
#
# Uso:   powershell -File scripts/build-frontend.ps1
#        bash scripts/build-frontend.sh   (POSIX)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'frontend')
try {
  # Volumes nombrados con los node_modules/cache de Linux (persistentes).
  $nodeModulesVol = 'hoteldata_frontend_build_modules'
  $npmCacheVol = 'hoteldata_frontend_npm_cache'

  docker run --rm `
    -v "${nodeModulesVol}:/app/node_modules" `
    -v "${npmCacheVol}:/root/.npm" `
    -v "$root/frontend:/app" `
    -w /app `
    node:24-alpine `
    sh -lc 'test -x node_modules/.bin/ng || npm ci --prefer-offline; npm run build'

  if ($LASTEXITCODE -ne 0) { throw "Build de frontend falló (exit $LASTEXITCODE)." }
  Write-Host ""
  Write-Host "Build OK. nginx sirve el dist en http://localhost:4200 (refrescá con Ctrl+F5)."
} finally {
  Pop-Location
}
