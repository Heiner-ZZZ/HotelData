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

## 🔧 Backend Conventions

- Rate limiting con **slowapi** (`slowapi>=0.1.10` en `server/requirements.txt`): `limiter` en `server/src/app/security/rate_limit.py` + `SlowAPIMiddleware` → 429. Detalles en `knowledge.md`.

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

- ⚠️ **Dotfiles:** `.credentials/` es un directorio **oculto** — `glob`/`code_search` lo omiten por diseño (ignoran archivos ocultos). Leer el archivo SIEMPRE con `find`/`cat` o `read_files` con la ruta exacta; **nunca** depender de búsqueda por patrón (`*credencial*` no lo encuentra).
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

### 🧪 Aislamiento de BD — tests y diagnósticos NUNCA tocan la BD dev (regla dura)

#### ¿Qué es `hoteldata_hub_test`?

`hoteldata_hub_test` es una base de datos MongoDB **desechable y exclusiva para pytest y diagnósticos aislados**. Vive en la misma instancia local de MongoDB que `hoteldata_hub`, pero no contiene datos de negocio del entorno dev:

- Los tests la fuerzan mediante `server/tests/conftest.py` antes de importar `src.app.*`.
- Las fixtures siembran allí usuarios, roles, reservas, facturas, empleados y demás documentos mínimos necesarios para cada caso.
- Su contenido normal son **fixtures y residuos de pruebas**: documentos creados por tests anteriores o por una corrida interrumpida. Esos residuos no representan datos reales ni deben interpretarse como una copia de `hoteldata_hub`.
- El cleanup del conftest vacía las colecciones operativas antes de cada test. Si una ejecución se corta, pueden quedar residuos hasta la siguiente corrida.
- Si el usuario autoriza explícitamente borrar la base completa, puede hacerse sin riesgo para dev: pytest vuelve a crear las colecciones, índices y fixtures que necesita al iniciar. **Desechable no significa que se pueda borrar automáticamente ni sin autorización; no contiene información que deba conservarse.**

**Por qué existe:** en el incidente de agosto de 2026 se perdieron aproximadamente 30 minutos porque un script de diagnóstico conectó por defecto a `hoteldata_hub` y eliminó las cinco colecciones de seguridad `users`, `roles`, `permissions`, `hotel_roles` y `role_assignments`. Desde entonces, `hoteldata_hub_test` es el cortafuegos obligatorio para pruebas, migraciones de prueba y exploración técnica.

**Regla operativa:** los tests y diagnósticos rutinarios van **SIEMPRE** a `hoteldata_hub_test`, con la base fijada explícitamente antes de importar cualquier módulo de la aplicación. Solo una auditoría dev solicitada expresamente puede leer `hoteldata_hub`, y debe ser estrictamente read-only: sin inserts, updates, deletes, drops, seeds, migraciones ni creación de índices.

Desde entonces, estas reglas son obligatorias:

1. **Los tests pytest SIEMPRE corren contra la BD de test `hoteldata_hub_test`** — el
   `server/tests/conftest.py` setea `os.environ["MONGO_DATABASE"]="hoteldata_hub_test"` ANTES de
   importar `src.app.*`. No modificar ese contrato.
2. **🚫 NUNCA ejecutar scripts de diagnóstico/exploración con `get_database()` a secas** — dentro
   del contenedor server la env var del compose es `MONGO_DATABASE=hoteldata_hub` (dev). Un
   `python -c "from src.database.connection import get_database"` sin aislar conecta a DEV.
   Para explorar Mongo aislado, forzar la BD de test explícitamente:
   ```bash
   docker compose --env-file .env -f infra/docker-compose.yml exec -T server python -c "
   import os
   os.environ['MONGO_DATABASE'] = 'hoteldata_hub_test'  # ANTES de importar src.*
   from src.database.connection import get_database
   ..."
   ```
3. **Diagnóstico = solo lectura + BD de test.** 🚫 NUNCA `drop_collection` / `delete_many` /
   writes desde un script de diagnóstico, ni siquiera contra la BD de test, sin autorización.
   Si necesitas replicar una fixture para debuggear, hazlo dentro de un test pytest (el conftest
   ya dropea y recrea las colecciones de test por test) — nunca con un `python -c` suelto.
4. **Comando canónico de tests** (el contenedor monta el server en `/app`, por eso el path es
   `tests/...` y NO `server/tests/...`):
   ```bash
   docker compose --env-file .env -f infra/docker-compose.yml exec -T server python -m pytest -q tests/<archivo>.py
   ```
5. Los seeds/migraciones de RESTAURACIÓN (`init_security_model_ga03.py`, `seed_roles_users.py`,
   `sync_hotel_manage_roles.py`, `migrate_hotel_roles.py`) sí apuntan a dev — pero SOLO se corren
   cuando el usuario lo pide explícitamente o para deshacer un error, nunca como parte de un
   diagnóstico rutinario. Nota: `seed_roles_users.py` ya NO es fuente divergente de roles/permisos
   (migrado 2026-08) — importa `BASE_ROLES`/`PERMISSION_CATALOG`/`ROLE_PERMISSION_CODES` y las
   funciones de upsert del canónico `init_security_model_ga03.py`; su único aporte propio son los
   usuarios demo. Re-ejecutarlo es CONVERGENTE con el canónico, nunca pisa permisos.
6. **🚫 NUNCA correr DOS procesos pytest a la vez contra la misma BD de test.** El conftest adquiere
   un flock exclusivo (`/tmp/hoteldata_test_db.lock`) al arrancar; el segundo proceso falla con
   "Otro proceso pytest está corriendo...". La causa de los 401/403/duplicate-key intermitentes de
   `test_role_permissions_notifications.py` fue exactamente esto: dos suites simultáneas, y el
   `delete_many` del cleanup de una borraba los usuarios/sesiones/roles que la otra acababa de
   sembrar. Espera a que termine el otro proceso (o mátalo) antes de relanzar.

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
