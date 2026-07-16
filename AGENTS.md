<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# Reglas para Codebuff (Buffy)

## 🏗️ Stack del Frontend — Angular 22 (ESTABLE)

Este proyecto usa **Angular 22** (lanzado junio 2026). Las siguientes APIs son **ESTABLES** (NO experimentales) y deben usarse:

### APIs estables y obligatorias

| API | Estado en v22 | Uso en el proyecto |
|-----|---------------|-------------------|
| `httpResource()` | ✅ Estable | ~30+ páginas ya migradas. **Siempre** usar `httpResource` para GETs. POST/PUT/DELETE se mantienen en servicios con `HttpClient`. |
| `rxResource()` | ✅ Estable | Usar solo cuando el request depende de un Observable. Preferir `httpResource` para casos simples. |
| `resource()` | ✅ Estable | Para recursos no-HTTP. |
| `signal()` / `computed()` / `linkedSignal()` / `effect()` | ✅ Estable | 177+ signals, 160+ componentes con OnPush, 37 effects. **Nunca** usar `BehaviorSubject` para estado de UI — siempre `signal`. |
| `ChangeDetectionStrategy.OnPush` | ✅ Default en v22 | 160+ componentes ya lo usan. **Siempre** agregar `OnPush` a componentes nuevos. |
| `provideZonelessChangeDetection()` | ✅ Estable (sin prefijo "Experimental") | **NO habilitado aún** en este proyecto. Requiere migración completa a signals. |
| Signal Forms | ✅ Estable en v22 | **NO adoptado aún.** Se sigue usando Reactive Forms tradicional con `FormGroup`/`FormControl` envueltos en `signal()`. |
| Nuevo control flow (`@if`, `@for`, `@switch`) | ✅ Estable | Ya en uso. **Nunca** usar `*ngIf`, `*ngFor`, `*ngSwitch` en código nuevo. |

### APIs NO disponibles aún en v22

| API | Estado | Nota |
|-----|--------|------|
| `@boundary` / `@error` | ❌ No existe en v22 | Esperado en v22.1 o v23. Seguir usando `resource.error()` como alternativa. |

### TypeScript y toolchain

| Herramienta | Versión | Nota |
|-------------|---------|------|
| TypeScript | **6.x** (target: ES2024) | Ver `frontend/tsconfig.json`. TS 5.9- ya no funciona en v22. |
| Node.js | **24.x** (node:24-alpine) | Node 20 discontinuado para Angular 22. Ver `frontend/Dockerfile`. |
| Build system | `application` builder (esbuild) | Webpack deprecado. Usar el builder por defecto de Angular 22. |

### 🎨 Design Tokens — Sistema de colores

**ARCHIVO CANÓNICO:** `frontend/src/styles/_scss-variables.scss`

Este archivo define **TODOS** los colores de la app mediante CSS custom properties con light + dark theme.

| Categoría | Tokens | Uso |
|-----------|--------|-----|
| Surface | `--surface`, `--surface-raised`, `--surface-soft`, `--surface-hover` | Fondos de cards, modales, paneles |
| Texto | `--app-text`, `--muted-text` | Texto principal y secundario |
| Accent (azul) | `--accent-light`, `--accent`, `--accent-hover`, `--accent-active`, `--accent-strong`, `--on-accent` | Botones, links, focus rings |
| Success (verde) | `--success-light`, `--success`, `--success-strong`, `--on-success` | Badges positivos, KPIs |
| Warning (ámbar) | `--warning-light`, `--warning`, `--warning-strong`, `--on-warning` | Badges de advertencia |
| Danger (rojo) | `--danger-light`, `--danger`, `--danger-strong`, `--on-danger` | Errores, badges negativos |
| Purple | `--purple-light`, `--purple`, `--purple-strong` | Badges de entidad, UI indicators |
| Indigo | `--indigo-light`, `--indigo`, `--indigo-strong` | Badges de entidad |
| Extended | `--teal`, `--cyan`, `--yellow` | Colores semánticos adicionales |
| Gray scale | `--gray-50` → `--gray-900` | Texto secundario, bordes, fondos sutiles |
| Border | `--app-border` | Bordes de cards, inputs, tablas |

**REGLAS:**
- 🚫 **NUNCA** usar colores hardcodeados (`#fff`, `#191c1e`, etc.) en SCSS nuevo. Siempre usar tokens.
- 🚫 **NUNCA** crear bloques `:root` duplicados en partials — heredar del `_scss-variables.scss` global.
- ✅ Para colores de marca (ej: gradientes decorativos de hotel-card) se permite mantener hex si son identidad visual, no UI semántica.
- ✅ Usar `color-mix(in srgb, var(--token) X%, transparent)` para variantes claras en vez de crear tokens nuevos.
- ✅ El sistema soporta **dark mode** vía `[data-theme="dark"]`.

## 🔴 NUNCA hacer sin autorización explícita del usuario

- **🚫 ABSOLUTAMENTE NUNCA** ejecutar `docker compose down` sin `--volumes` ni ningún comando que elimine volúmenes de Docker.
- **🚫 NUNCA** ejecutar `docker compose down` para reconstruir contenedores — usar `up --build` en su lugar.
- **🚫 NUNCA** ejecutar `docker compose down -v`.
- **NUNCA** hacer `git commit`, `git push` ni ningún comando de git que modifique el historial sin autorización.
- **NUNCA** eliminar archivos, directorios, colecciones de MongoDB, tablas o datos sin preguntar.
- **NUNCA** ejecutar scripts que modifiquen la base de datos en producción (seed, drop, reset) sin confirmación.
- **NUNCA** sobrescribir archivos de configuración (`.env`, `docker-compose.yml`, etc.) sin informar.

## ✅ Docker — Estándar para desarrollo

Basado en [Docker docs: build best practices](https://docs.docker.com/build/building/best-practices/):

| Situación | Comando | Por qué |
|-----------|---------|---------|
| Solo cambió código fuente (TS, HTML, Python) | `docker compose up -d <servicio>` | Sin rebuild — el código se monta por volumen en dev. Para producción sí rebuild. |
| Cambió `Dockerfile`, `package.json`, `requirements.txt` o similar | `docker compose up -d --build <servicio>` | Rebuild inteligente — Docker reusa capas inalteradas (ej: `npm install` solo si cambió `package.json`). |
| Cache corrompido, error extraño de build, o dependencias stale | `docker compose build --no-cache <servicio>` | Solo cuando sea necesario — rebuild completo de todas las capas (lento). |

**Reglas:**
- Usar `docker compose -f infra/docker-compose.yml up --build <servicio>` para rebuild + logs visibles en primer plano.
- **NO** usar `--no-cache` en rebuilds rutinarios — desperdicia tiempo redescargando dependencias inalteradas.
- Si el servicio monta volúmenes de código (dev), no hace falta rebuild para cambios de código fuente.
- Preferir `docker compose up -d` (detached) cuando no se necesiten logs en terminal.
- **NUNCA** usar datos hardcodeados (`standard`, `deluxe`, `suite`, etc.) en seed scripts o queries — siempre leer dinámicamente de la BD.

## ⚙️ ETL (Incremental)

El pipeline GA03 soporta dos modos controlados por la env var `GA03_INCREMENTAL_MODE` (default: `"false"`):

### Modo Full (default, `GA03_INCREMENTAL_MODE=false`)
- Extrae TODOS los registros de PocketBase
- `delete_many({})` + inserciones en MongoDB (borra y reescribe todo)
- El comportamiento histórico no cambia

### Modo Incremental (`GA03_INCREMENTAL_MODE=true`)
- **1er run**: Extrae todo, guarda `last_extracted_at` (max `created` de PocketBase) en `ga03_execution_state.json`
- **Runs siguientes**: El extract filtra por `(created>last_extracted_at)`, solo extrae registros nuevos
- Las dimensiones se cargan con `UpdateOne` + `upsert=True` (no borra lo existente)
- Los hechos se cargan con `UpdateOne` por `source_record_id` + `upsert=True` (no borra nada, solo agrega nuevos)
- `expected_records` en estado = cantidad de registros **nuevos** extraídos (no el total)
- Si se pierde el archivo de estado, el próximo run será full automáticamente

### Elección
- Para recargar todo desde 0: `GA03_INCREMENTAL_MODE=false` (o no setearla)
- Para agregar solo nuevos: `GA03_INCREMENTAL_MODE=true`
