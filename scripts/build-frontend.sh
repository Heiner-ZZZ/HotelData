#!/usr/bin/env bash
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
# Uso:   bash scripts/build-frontend.sh
#        powershell -File scripts/build-frontend.ps1   (Windows)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

# Volume nombrado con los node_modules de Linux (persistente entre corridas).
NODE_MODULES_VOL="hoteldata_frontend_build_modules"
NPM_CACHE_VOL="hoteldata_frontend_npm_cache"

docker run --rm \
  -v "$NODE_MODULES_VOL:/app/node_modules" \
  -v "$NPM_CACHE_VOL:/root/.npm" \
  -v "$ROOT/frontend:/app" \
  -w /app \
  node:24-alpine \
  sh -lc 'test -x node_modules/.bin/ng || npm ci --prefer-offline; npm run build'

echo ""
echo "Build OK. nginx sirve el dist en http://localhost:4200 (refrescá con Ctrl+F5)."
