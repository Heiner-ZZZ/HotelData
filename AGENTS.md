<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## 📚 Convenciones de código (canonical reference)

**Las convenciones estables del proyecto viven en `knowledge.md`** (raíz).
Las reglas de abajo (stack, Docker, credenciales, ETL) son operativas.
Las convenciones de código (Pydantic `*Response`, atomic-write pattern,
migration scripts, feature auth services, qué NO hacer — ObjectIdStr
helper revertido) están en `knowledge.md` y deben leerse **antes** de
tocar el código o proponer refactors.

## 🔧 Backend Conventions (mirror del cache-clear ritual)

Se mirrora aquí el único patrón de **`knowledge.md → Backend Conventions`**
que se rompe recurrentemente cuando un agente lee solo `AGENTS.md` y se
salta `knowledge.md`. **Mismo wording canónico que `knowledge.md`** —
si la fuente y este mirror divergen, corregir ambos y usar
`diff knowledge.md AGENTS.md` después.

### Cache-clear ritual after `*Response` deletes or alias changes

Pydantic v2 + FastAPI + Docker source mount + `from __future__ import annotations` = stale bytecode risk. After **deleting** any `*Response` Pydantic class (or modifying a field's `validation_alias` / `serialization_alias`), stale `.pyc` files inside `__pycache__/` can still be loaded by the running Python interpreter, surfacing as `ImportError: cannot import name 'XResponse' from …` for symbols that were already removed.

**Required cleanup** (mandatory after every delete or alias mutation; skipping it leaves the running server carrying deleted-class ghosts from cached bytecode):

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec -T server find /app/server -name __pycache__ -exec rm -rf {} + && docker compose --env-file .env -f infra/docker-compose.yml restart server
```

The first command clears every `__pycache__/` directory under the server tree so the next interpreter boot reads source from disk. The `docker compose restart server` cold-restarts the uvicorn process — required because Python already loaded the stale `.pyc` at boot and is now holding the deleted symbol in `sys.modules`. The `&&` ensures the restart only runs if the cache clear succeeds — if `find` errors out (e.g. permission denied), halt the ritual and investigate instead of restarting with stale bytecode still on disk.

This is mandatory even when `py_compile` reports OK: the static check reads from `.py` source and does not exercise the import cache of a running interpreter. A model that compiles cleanly can still fail at runtime if its `.pyc` from a previous boot is cached on disk.

**Wrapper script** for both shells (preferred over pasting two commands):
- POSIX: `bash server/scripts/clear_pydantic_cache.sh`
- Windows: `powershell -File server/scripts/clear_pydantic_cache.ps1`

If you skip this ritual and the server starts returning 500s referencing symbols you already deleted, the failure mode is loud but the source of the leak is not obvious — check `docker compose exec server ls /app/server/src/app/modules/<your_module>/__pycache__/` and confirm the deleted class names.

## Skills disponibles

El proyecto tiene skills de dominio ubicadas en `.opencode/skills/`:

| Skill | Propósito |
|---|---|
| `architect` | Design-review y planning de arquitectura técnica |
| `arquitectura-software-senior` | Patrones arquitectónicos (Clean Arch, Hexagonal, DDD, C4, monolith vs microservices) |
| `backend-senior` | Diseño/review de FastAPI, Pydantic v2, MongoDB, async, testing |
| `ciberseguridad-senior` | Seguridad: OWASP Top 10, CORS, rate limiting, auth, threat modeling |
| `frontend-senior` | Angular Signals, zoneless, lazy loading, SSR/SSG, micro-frontends |
| `frontend-specialist` | UI/UX: componentes, SCSS, responsive, accesibilidad |
| `gobierno-datos-senior` | Data pipelines, ETL/ELT, Medallion architecture, data quality/lakehouse/mesh |

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
|-----------|--------|------|
| App Background | `--app-bg` | Fondo general de toda la app (detrás de todo) |
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
| Shadows | `--shadow-sm`, `--shadow-md` | Sombras de cards, modales, dropdowns |

**REGLAS:**
- 🚫 **NUNCA** usar colores hardcodeados (`#fff`, `#191c1e`, etc.) en SCSS nuevo. Siempre usar tokens.
- 🚫 **NUNCA** usar emojis en la UI (`✅`, `⚠️`, `⭐`, etc.). Siempre usar iconos del sistema de diseño vía `<span class="material-symbols-outlined">icon_name</span>` (Google Material Symbols). Los nombres de iconos se pasan como texto interno, ej: `check_circle`, `warning`, `star`, `search`, `chevron_right`.
- 🚫 **NUNCA** crear bloques `:root` duplicados en partials — heredar del `_scss-variables.scss` global.
- ✅ Para colores de marca (ej: gradientes decorativos de hotel-card) se permite mantener hex si son identidad visual, no UI semántica.
- ✅ Usar `color-mix(in srgb, var(--token) X%, transparent)` para variantes claras en vez de crear tokens nuevos.
- ✅ El sistema soporta **dark mode** vía `[data-theme="dark"]`.

## 🔐 Credenciales — LEER ANTES DE INTENTAR LOGIN

**ARCHIVO CANÓNICO:** `.credentials/credenciales.md` (oculto, en `.gitignore`)

- **SIEMPRE** leer `.credentials/credenciales.md` antes de hacer `POST /api/auth/login`.
- **NUNCA** adivinar contraseñas (`admin123`, `password`, `test`, etc.).
- **NUNCA** probar más de 2 intentos sin verificar credenciales en el archivo.
- Si una cuenta responde `423 Locked`, desbloquear con el comando documentado abajo.

### Credenciales reales (canónicas en `.credentials/credenciales.md`)

| Usuario | Contraseña | Rol |
|---|---|---|
| `superadmin` | `Admin12345*` | super_admin (admin total) |
| `Socio GTA6` | `socio12345*` | gerente_hotel (single-hotel) |
| `Horuz` | `Horuz12345*` | cliente (huésped) |
| `carlos.mendoza@hoteldata.local` | `yn_ncfT2TqevSA` | mantenimiento |

### Desbloquear cuenta (423 Locked)

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec -T server python -c "
from config.settings import get_settings
from pymongo import MongoClient
s = get_settings()
c = MongoClient(s.mongo_uri)
db = c[s.mongo_database]
db.users.update_one(
    {'username': 'superadmin'},
    {'\$set': {'failed_login_attempts': 0, 'locked_until': None}}
)
print('Desbloqueado')
c.close()
"

## 🔴 NUNCA hacer sin autorización explícita del usuario

- **🚫 ABSOLUTAMENTE NUNCA** ejecutar `docker compose down --volumes` ni `docker compose down -v`, porque eliminan volúmenes y datos persistentes.
- **🚫 NUNCA** ejecutar `docker compose down` para reconstruir contenedores — usar `up --build` en su lugar.
- Si solo necesitas detener servicios sin borrar volúmenes, usa `docker compose stop`.
- **NUNCA** hacer `git commit`, `git push` ni ningún comando de git que modifique el historial sin autorización.
- **NUNCA** eliminar archivos, directorios, colecciones de MongoDB, tablas o datos sin preguntar.
- **NUNCA** ejecutar scripts que modifiquen la base de datos en producción (seed, drop, reset) sin confirmación.
- **NUNCA** sobrescribir archivos de configuración (`.env`, `docker-compose.yml`, etc.) sin informar.

## Airflow 3 — instalación y dependencias

La imagen `infra/docker/airflow3.Dockerfile` usa `apache/airflow:3.2.2-python3.12`.
La instalación se realiza en dos pasos obligatorios:

1. `apache-airflow[celery,postgres]==3.2.2` con el constraints oficial de Airflow para Python 3.12.
2. Dependencias propias del DAG desde `infra/docker/airflow3.requirements.txt`, sin reutilizar ese constraints.

**No** agregar providers de Celery/Postgres ni rangos incompatibles al requirements del DAG: los providers del executor y de PostgreSQL los resuelven los extras oficiales de Airflow. El constraints de Airflow fija versiones exactas; imponer rangos externos puede producir `ResolutionImpossible`.

Si cambia `airflow3.Dockerfile` o `airflow3.requirements.txt`, reconstruir únicamente la imagen Airflow:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml build airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker airflow-init
```

Después aplicar los servicios sin borrar volúmenes:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d airflow-postgres airflow-init airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker
```

## ✅ Docker — Estándar para desarrollo

Basado en [Docker docs: build best practices](https://docs.docker.com/build/building/best-practices/):

| Situación | Comando | Por qué |
|-----------|---------|---------|
| Solo cambió código fuente (TS, HTML, Python) | `docker compose up -d <servicio>` | Sin rebuild — el código se monta por volumen en dev. Para producción sí rebuild. |
| Cambió `Dockerfile`, `package.json`, `requirements.txt` o similar | `docker compose up -d --build <servicio>` | Rebuild inteligente — Docker reusa capas inalteradas (ej: `npm install` solo si cambió `package.json`). |
| Cache corrompido, error extraño de build, o dependencias stale | `docker compose build --no-cache <servicio>` | Solo cuando sea necesario — rebuild completo de todas las capas (lento). |

**Reglas:**
- Usar `docker compose --env-file .env -f infra/docker-compose.yml up --build <servicio>` para rebuild + logs visibles en primer plano.
- **NO** usar `--no-cache` en rebuilds rutinarios — desperdicia tiempo redescargando dependencias inalteradas.
- Si el servicio monta volúmenes de código (dev), no hace falta rebuild para cambios de código fuente.
- Preferir `docker compose up -d` (detached) cuando no se necesiten logs en terminal.
- **NUNCA** usar datos hardcodeados (`standard`, `deluxe`, `suite`, etc.) en seed scripts o queries — siempre leer dinámicamente de la BD.

## ⚙️ ETL (Incremental)

El pipeline GA03 soporta dos modos controlados por la env var `GA03_INCREMENTAL_MODE` (default: `"false"`):

### Modo Full (default, `GA03_INCREMENTAL_MODE=false`)
- Extrae TODOS los registros de PocketBase
- `delete_many({})` + inserciones en MongoDB (borra y reescribe todo)

### Modo Incremental (`GA03_INCREMENTAL_MODE=true`)
- **1er run**: Extrae todo, guarda `last_extracted_at` en `ga03_execution_state.json`
- **Runs siguientes**: Filtra por `(created>last_extracted_at)`, solo extrae registros nuevos
- Dimensiones/hechos cargan con `UpdateOne` + `upsert=True` (no borra existente)
- Si se pierde el archivo de estado, el próximo run será full automáticamente
