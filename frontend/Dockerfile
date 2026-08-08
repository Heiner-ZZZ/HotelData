FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` es determinista: instala EXACTAMENTE lo que fija package-lock.json
# (a diferencia de `npm install`, no resuelve versiones ni muta el lock).
# El `--mount=type=cache,target=/root/.npm` (BuildKit) persiste la caché de
# tarballs de npm en el HOST entre builds: aunque package.json cambie y la
# capa se invalide, `npm ci` vuelve a ejecutarse sirviéndose de la caché sin
# re-descargar del registry. `--prefer-offline` evita revalidar contra
# registry.npmjs.org cuando el paquete ya está en caché.
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline
COPY . .
# `npm run build` ahora encadena `ng build && node scripts/post-build.mjs`
# (ver scripts/post-build.mjs): el post-build sella assets/version.json con el
# timestamp del build (al FINAL, sobre el dist ya compilado — antes vivía en
# una RUN previa con $(date) cuya fecha dinámica se congelaba al cachearse la
# capa) y re-copia runtime-config.js al dist. El entrypoint del contenedor
# SOBRESCRIBE runtime-config.js en el arranque desde SYNCFUSION_LICENSE_KEY,
# así que la clave nunca se hornea en la imagen.
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
