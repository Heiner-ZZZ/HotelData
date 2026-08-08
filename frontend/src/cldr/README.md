# Datos CLDR vendidos (src/cldr/)

Estos 6 archivos JSON son **copias byte-a-byte** de `cldr-data@36.0.5`
(`node_modules/cldr-data/`), vendidas en el repo para eliminar la dependencia
del paquete `cldr-data`.

## Por qué se vendieron

`cldr-data` ejecuta un postinstall (`cldr-data-downloader`) que descarga el
dataset CLDR completo (~300 MB) desde GitHub en **cada** `npm ci`. Con redes
lentas o inestables el postinstall muere por timeout TLS y rompe el build
(síntoma: `npm ci` colgado 10+ minutos → `exit code: 1` en
`cldr-data-downloader`).

La app solo usa 6 archivos (~164 KB) para `loadCldr()` + `setCulture('es')`
de Syncfusion en `reception-timeline.ts`. Venderlos hace el build
**offline-capable, determinista y ~300 MB más liviano**.

## Procedencia

| Archivo | Origen en cldr-data@36.0.5 |
|---|---|
| `supplemental/numberingSystems.json` | `cldr-data/supplemental/numberingSystems.json` |
| `supplemental/likelySubtags.json` | `cldr-data/supplemental/likelySubtags.json` |
| `supplemental/weekData.json` | `cldr-data/supplemental/weekData.json` |
| `main/es/ca-gregorian.json` | `cldr-data/main/es/ca-gregorian.json` |
| `main/es/numbers.json` | `cldr-data/main/es/numbers.json` |
| `main/es/timeZoneNames.json` | `cldr-data/main/es/timeZoneNames.json` |

Licencia: datos del **Unicode CLDR** (Unicode License v3), ver
`https://www.unicode.org/license.txt`.

## Cómo actualizar

1. Instalar temporalmente: `npm i -D cldr-data@<versión>` (o `npm i cldr-data@<versión> --no-save`).
2. Copiar los 6 archivos: `cp node_modules/cldr-data/{supplemental/{numberingSystems,likelySubtags,weekData}.json,main/es/{ca-gregorian,numbers,timeZoneNames}.json} src/cldr/…` (preservando estructura).
3. Desinstalar: `npm uninstall cldr-data`.
4. Verificar con `npm run build` y la página de Recepción → Timeline.

## Ojo al actualizar Syncfusion

`loadCldr()` de `@syncfusion/ej2-base` espera datos CLDR compatibles con la
versión de Syncfusion instalada. `cldr-data@36.0.5` fue la versión elegida
para el Syncfusion actual. **Al actualizar `@syncfusion/ej2-schedule` /
`@syncfusion/ej2-base`, re-verificar que estos JSON sigan siendo
compatibles** (si no, re-vender de una versión de cldr-data acorde).
