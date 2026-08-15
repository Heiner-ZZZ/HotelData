# HotelData — Project Knowledge

## What is this?

**HotelData** is a modular hotel management platform (PMS + CRS + Booking Engine) built with Angular 22, FastAPI, and MongoDB. It covers daily hotel operations (check-in/out, housekeeping, billing, reservations), central reservation management (rates, availability, inventory), and a direct booking engine.

## Quickstart

```bash
# Full stack (Docker)
docker compose --env-file .env -f infra/docker-compose.yml up -d

# Frontend standalone
cd frontend && npm install && npm start

# Backend standalone
cd server && pip install -r requirements.txt && uvicorn src.app.main:app --reload
```

### Key URLs (local)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| PocketBase | http://localhost:8090 |
| Airflow | http://localhost:8080 |
| Redis | localhost:6379 |
| MongoDB | localhost:27018 |

### Airflow 3 build note

Airflow 3 se construye desde `apache/airflow:3.2.2-python3.12` en dos pasos: primero `apache-airflow[celery,postgres]==3.2.2` con el constraints oficial de Airflow; después las dependencias propias del DAG sin ese constraints. No agregar providers de Celery/Postgres al requirements del DAG ni imponer rangos que contradigan el constraints. Esto evita `ResolutionImpossible` (por ejemplo, `pyarrow<18` frente al `pyarrow==24` fijado por Airflow).

Si cambian `infra/docker/airflow3.Dockerfile` o `infra/docker/airflow3.requirements.txt`, reconstruir con:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml build airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker airflow-init
docker compose --env-file .env -f infra/docker-compose.yml up -d airflow-postgres airflow-init airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker
```

### Docker rebuild rules

| Situation | Command |
|-----------|---------|
| Code changes (TS, HTML, Python) only | `docker compose --env-file .env -f infra/docker-compose.yml up -d <service>` — no rebuild needed |
| Dockerfile/package.json/requirements.txt changed | `docker compose --env-file .env -f infra/docker-compose.yml up -d --build <service>` |
| Stale cache / weird errors | `docker compose build --no-cache <service>` — slow, only when needed |

**NEVER** run `docker compose down --volumes` or `docker compose down -v`.

## Architecture

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | Angular 22, TypeScript 6.x, SCSS | Signals + OnPush, esbuild builder |
| Backend | FastAPI, Python 3.12 | Pydantic v2, async, uvicorn |
| Database | MongoDB 8.0 (replica set) | Port 27018, RS `rs0` |
| Analytics | ClickHouse 26.7.1 (Docker) | Servicio `clickhouse` en compose · HTTP 8123 · BD `hoteldata` |
| ETL | Airflow 3.2.2, PocketBase (legacy source) | GA03 pipeline, CeleryExecutor, incremental mode |
| Auth | JWT (python-jose) + bcrypt | |
| Cache | Redis 7.4 | |

### Key directories

| Path | Contents |
|------|----------|
| `frontend/src/app/features/` | 34 Angular modules (one per domain) |
| `frontend/src/app/shared/ui/` | Reusable UI components (sidebar-nav, etc.) |
| `frontend/src/styles/` | Global SCSS with design tokens (`_scss-variables.scss`) |
| `server/src/app/modules/` | 27 FastAPI route/service modules |
| `server/config/` | Backend configuration |
| `server/scripts/` | Utility scripts (migrations, ETL, maintenance) |
| `server/dags/` | Airflow DAGs |
| `server/tests/` | Backend tests (pytest) |
| `infra/` | Docker Compose, Dockerfiles |
| `data/` | Mounted data volumes |
| `.credentials/` | Login credentials (gitignored) |

## Frontend Conventions

### Angular 22 (stable APIs — MUST use)

| API | Usage |
|-----|-------|
| `httpResource()` | ✅ **Always** for GET requests. 30+ pages migrated. |
| `rxResource()` | Only when request depends on an Observable. |
| `signal()` / `computed()` / `linkedSignal()` / `effect()` | Never use `BehaviorSubject` for UI state — always `signal()`. 177+ signals in use. |
| `ChangeDetectionStrategy.OnPush` | **Always** add to new components. 160+ components use it. |
| `@if` / `@for` / `@switch` | **Always** use new control flow. Never `*ngIf`, `*ngFor`, `*ngSwitch`. |
| Reactive Forms (FormGroup/FormControl) | Still used (wrapped in `signal()`). Signal Forms not yet adopted. |
| `provideZonelessChangeDetection()` | Stable in v22 but **not enabled** in this project yet. |

### Design system
- **Colors**: All defined as CSS custom properties in `frontend/src/styles/_scss-variables.scss`. Light + dark theme via `[data-theme="dark"]`.
- **No hardcoded colors** (`#fff`, `#191c1e`, etc.) in new SCSS — always use design tokens.
- **No emojis** in UI — use Google Material Symbols via `<span class="material-symbols-outlined">icon_name</span>`.
- **Scrollbars globales (2026-08):** un solo diseño verde de marca para TODA la app, sin tocar componente por componente — `frontend/src/styles/_scss-scrollbar.scss` (importado en `styles.scss` tras el reset) aplica a *cualquier* elemento con scroll vía `*:::-webkit-scrollbar` (píldora `border-radius: 999px` con anillo integrador de 2px del color del track + `background-clip: padding-box`; thumb con `min-height/min-width: 40px` para agarre usable) y a Firefox vía `scrollbar-width: thin` + `scrollbar-color`. Los colores viven en `_scss-variables.scss` como tokens `--scrollbar-*` (size 10px, track un paso sobre el fondo, thumb = `--accent` con hover/active profundizando; corner = track para que la intersección V+H no deje hueco) — canónico en `:root` y `[data-theme="dark"]`. Contraste thumb≥track ≥3:1 (WCAG 1.4.11) en ambos temas. Regla: componentes con scrollbar propio deben usar los mismos tokens (`--scrollbar-thumb`/`-hover`) — ya alineados: cart-drawer, ledger ag-grid, staff-inbox sidebar/chat. Los `scrollbar-width: none` intencionales (carruseles welcome header, category chips) se conservan.
- **No `:root` blocks** in partials — inherit from the global variables file.
- Use `color-mix(in srgb, var(--token) X%, transparent)` for lighter variants instead of new tokens.

### TypeScript / Build
- TypeScript 6.x, target ES2024
- `application` builder (esbuild) — Webpack is deprecated
- Jest for unit tests, Playwright for e2e

### Feature auth services (Signal-based)

**Canonical pattern** when a feature has duplicated role-list computed signals in 2+ components:

- Create `frontend/src/app/features/<feature>/services/<feature>-auth.service.ts` with `@Injectable({providedIn: 'root'})` and `computed signals` backed by `AuthService.currentUser()?.primaryRole`.
- Components inject the service and alias: `readonly canSeeCost = this.productsAuth.canSeeCost;`
- One source of truth per feature — no duplicated role-list computeds in components.
- Examples: `products/services/products-auth.service.ts`, `reservations/services/reservations-auth.service.ts`.
- Long-term direction: replace role-list checks with `auth.hasPermission()` once permission codes are fully centralised in `init_security_model_ga03.py`.

## Backend Conventions

- FastAPI async routes with Pydantic v2 models
- MongoDB via PyMongo (MongoClient)
- Rate limiting con slowapi (`limiter` en `server/src/app/security/rate_limit.py` + `SlowAPIMiddleware`, excedido → 429)
- Ruff for linting, MyPy for type checking, pytest for tests
- Permission-based access control (PBAC) via DB-backed navigation & permissions
- JWT auth with python-jose + bcrypt (passlib)

### API response convention — Pydantic `*Response` owns the wire shape

**Canonical pattern** (started: partner module, in-progress across other modules):

1. The **service** returns raw MongoDB docs (with `_id: ObjectId`, native `datetime`, `Decimal128`, etc.).
2. The **route** declares a `*Response(BaseModel)` class with `Field(validation_alias="_id", serialization_alias="id")` and `response_model=*Response` on the endpoint.
3. Pydantic v2 owns the wire serialization: `_id → "id"` (via `ObjectIdStr` from `server/src/app/core/types.py`), `datetime → ISO`, `Decimal128 → float`.
4. Every shared class has a docstring that says **KEEP IN SYNC** with its TS DTO mirror in `frontend/src/app/features/<feature>/models/`.

**Example** — `server/src/app/modules/partner/routes/hotel_products.py:HotelProductResponse`:

```python
class HotelProductResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    product_id: str
    ...
```

Frontend DTO mirrors it; both files have cross-references in docstrings.

### Anti-pattern: `from __future__ import annotations` + Pydantic v2 + `response_model=…` produces 500

**Failure mode observed**: routes return `500 PydanticUserError` even after successful `import`. Symptom in the server log:

```
pydantic.errors.PydanticUserError:
  TypeAdapter[…CogsReportResponse…] is not fully defined;
  you should define … and all referenced types, then call .rebuild() on the instance.
```

Or after adding a `model_rebuild()` call:

```
pydantic.errors.PydanticUndefinedAnnotation:
  name 'CogsSummaryResponse' is not defined
```

Both errors are silent at module import time — the route LOOKS correct, the server boots, the first HTTP request hits the failure. Caught only via smoke curl + log inspection, not via `py_compile` or `import m`.

### Three conditions that trigger the failure (ALL must hold)

1. The route file declares `from __future__ import annotations` at the top (delays ALL type hints as forward-ref strings).
2. `*Response(BaseModel)` classes use `id: ObjectIdStr = Field(validation_alias=..., serialization_alias=...)` — `ObjectIdStr` itself is `Annotated[str, BeforeValidator(_serialize_object_id)]`, which is a forward ref Pydantic cannot resolve lazily.
3. At least one route is decorated with `response_model=*Response`.

### Two compounding root causes (BOTH must be fixed; fixing one is not enough)

**1. Banner-collapse bug** — NEVER collapse a section banner `# ─── Section Name ───` with `class X(BaseModel):` on the SAME line. Python treats the entire rest of the line as comment, so the class is NEVER added to module globals. `from __future__ import annotations` hides this at import (lazy strings are OK) but `model_rebuild()` forces eager resolution and surfaces the missing name as `PydanticUndefinedAnnotation`.

Correct shape (banner then blank then class on its own line):

```python
# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ───


class HotelProductResponse(BaseModel):
    ...
```

Wrong shape (banner + class collapsed — every character after `#` is comment):

```python
# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ───class HotelProductResponse(BaseModel):
```

The COGS 500 bug was caused by exactly this collapse in `partner/routes/hotel_products.py`. The fix was a single `str_replace` splitting the dominant banner from the first class declaration.

**2. Missing `model_rebuild()` calls** — Pydantic v2 does NOT auto-rebuild the model graph when `from __future__ import annotations` defers annotation evaluation as strings. FastAPI's `TypeAdapter` binding at `response_model=...` then raises `TypeAdapter is not fully defined`. Fix: add an explicit `XResponse.model_rebuild()` call for EVERY class with `ObjectIdStr` (or any other `Annotated` forward-ref), AFTER all class definitions and BEFORE the first `@router.` / `@api_router.` decorator.

Canonical pre-route-decorator block (use for every new routes file):

```python
# Rebuild Pydantic v2 models to resolve string-lazy annotations from
# ``from __future__ import annotations``. Without this explicit rebuild,
# FastAPI's ``TypeAdapter`` binding at ``response_model=…`` raises
# ``pydantic.errors.PydanticUserError`` on the first request, and any
# nested ``ObjectIdStr`` field surfaces as ``PydanticUndefinedAnnotation``
# when the eager rebuild graph walk hits it.
HotelProductResponse.model_rebuild()
MarginReportResponse.model_rebuild()
CogsReportResponse.model_rebuild()
StockValueReportResponse.model_rebuild()


# ─── Hotel Products CRUD ──────────────────────────────────
```

### Pre-merge validation checklist (mandatory for routes files with new `*Response` classes)

Quick smoke that catches BOTH failure modes above (banner collapse + missing rebuild) BEFORE hitting the server:

```bash
# From project root, inside the server container:
docker compose --env-file .env -f infra/docker-compose.yml exec -T server python -c "
import src.app.modules.<module_path>.<routes_file> as m
needed = ['ClassA', 'ClassB', 'ClassC']  # every *Response class in the new file
missing = [n for n in needed if not hasattr(m, n)]
assert not missing, f'missing classes (banner collapse?): {missing}'
print('OK')
"
```

If the assertion fails with `missing classes (banner collapse?)`, the banner-class collapse is the cause — split the lines and re-run. If it passes but the route still returns 500, add the explicit `model_rebuild()` calls.

**Pre-merge checklist** for every new routes file with `*Response` models:
- [ ] Each `class X(BaseModel):` is on its OWN line (no banner collapse).
- [ ] Every model using `ObjectIdStr` has `model_config = ConfigDict(populate_by_name=True)`.
- [ ] Every model with `ObjectIdStr` (or any `Annotated` forward-ref) has an explicit `XResponse.model_rebuild()` call AFTER all class definitions and BEFORE the first `@router.` decorator.
- [ ] The class list smoke test (above) passes locally via `docker compose exec`.
- [ ] A live curl smoke (e.g. `python -m pytest tests/test_<feature>.py -v` or a curl-based script under docker) hits the new endpoint and returns 200, NOT 500 or `TypeAdapter not fully defined`.

### Cache-clear ritual after `*Response` deletes or alias changes

Pydantic v2 + FastAPI + Docker source mount + `from __future__ import annotations` = stale bytecode risk. After **deleting** any `*Response` Pydantic class (or modifying a field's `validation_alias` / `serialization_alias`), stale `.pyc` files inside `__pycache__/` can still be loaded by the running Python interpreter, surfacing as `ImportError: cannot import name 'XResponse' from …` for symbols that were already removed.

**Required cleanup** (mandatory after every delete or alias mutation; skipping it leaves the running server carrying deleted-class ghosts from cached bytecode):

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec -T server find /app/server -name __pycache__ -exec rm -rf {} + && docker compose --env-file .env -f infra/docker-compose.yml restart server
```

The first command clears every `__pycache__/` directory under the server tree so the next interpreter boot reads source from disk. The `docker compose restart server` cold-restarts the uvicorn process — required because Python already loaded the stale `.pyc` at boot and is now holding the deleted symbol in `sys.modules`. The `&&` ensures the restart only runs if the cache clear succeeds — if `find` errors out (e.g. permission denied), halt the ritual and investigate instead of restarting with stale bytecode still on disk.

This is mandatory even when `py_compile` reports OK: the static check reads from `.py` source and does not exercise the import cache of a running interpreter. A model that compiles cleanly can still fail at runtime if its `.pyc` from a previous boot is cached on disk.

If you skip this ritual and the server starts returning 500s referencing symbols you already deleted, the failure mode is loud but the source of the leak is not obvious — check `docker compose exec server ls /app/server/src/app/modules/<your_module>/__pycache__/` and confirm the deleted class names.

### Historical incidents (this is the lesson not yet forgotten)

- **Fase 6 COGS 500** (2026-Q2): `partner/routes/hotel_products.py` had the COGS section banner-collapsed onto `class CogsSummaryResponse(BaseModel):`. Pre-existing 500 (`TypeAdapter not fully defined`) was masked by `from __future__ import annotations`. After the explicit `model_rebuild()` was added during the migration, the symptom flipped to `PydanticUndefinedAnnotation: name 'CogsSummaryResponse' is not defined`. Both fixes (banner split + model_rebuild) were needed; one alone was insufficient.
- **Auth + Account migration** (2026-Q2): 7 endpoints migrated to `*Response` in `auth/routes/login.py` and `account/routes.py`. Each followed the post-rewrite invariant — banner on its own line, all classes before any decorator, explicit `model_rebuild()` block before `@api_router.get(...)` — and shipped green in the first smoke run.

### Layer Separation: FastAPI ↔ Pydantic v2 ↔ Mongo (renaming-to-avoid-confusion)

Migration waves a backend deben precisar **a qué capa tocan** para evitar reportes ambiguos. Tres librerías distintas en tres capas distintas:

| Capa | Librería | Rol en HotelData | Símbolo en código |
|------|----------|------------------|-------------------|
| Web framework | **FastAPI** | Rutas, async, deps, middleware, OpenAPI gen | `@router.get`, `Depends(...)`, `BackgroundTasks` |
| Data models | **Pydantic v2** | Validación + serialización (`_id → "id"`) | `BaseModel`, `Field(validation_alias=...)`, `model_rebuild()` |
| Database driver | **Motor + PyMongo** | CRUD async/sync sobre MongoDB | `collection.find_one(...)`, `await db.insert_one(...)` |

**Reglas de naming** para reports de waves:

- Si tu wave toca `@router.get/post`, `Depends`, async endpoints → llamala **"FastAPI-layer migration"**.
- Si tu wave toca `BaseModel`, `model_rebuild()`, `ObjectIdStr`, alias mapping → llamala **"Pydantic v2-layer migration"** (correcto para los waves 2026-Q2 como el `partner/routes/hotels.py` rebuild block).
- Si tu wave toca collection queries, indexes, `ensure_indexes` → llamala **"Mongo driver migration"**.

**Test mental rápido**: **"¿El cambio sobreviviría si quitara FastAPI/Django/Flask y siguiera usando Pydantic v2 puro?"** Si la respuesta es **sí**, es migración Pydantic v2, no FastAPI. FastAPI como framework nunca reemplaza a Pydantic — siempre los usamos **juntos**, porque FastAPI depende internamente de Pydantic para type-driven request/response.

Cross-reference: el mismo principio vive en `docs/knowledge.md#19-convenciones-del-proyecto` (formato tabla de arquitectura).

### Layer atomic-write pattern (concurrent-safe inventory drains)

For inventory-style concurrency-sensitive operations (e.g. `fact_inventory` layer drain in `server/src/app/modules/partner/services/_inventory.py`):

- Use **aggregation-pipeline `update_one`** with `$gte: take` guard so the read+decrement+state-flip happens in one roundtrip.
- `$cond` evaluates `$subtract: ["$qty_remaining", take]` against the **pre-decrement** value to flip `is_active=False` + stamp `consumed_at` only when the layer hits zero.
- Drain loops retry by re-fetching the **contested layer** (not the whole queue) on `modified_count == 0` to preserve FIFO ordering.

### Migration scripts (`server/scripts/migrate_*.py`)

- **One-shot**, idempotent, accept `--dry-run` + `--skip-seed-source`.
- Stamp inserted docs with `metadata.migration_id` for audit traceability (e.g. `migrate_inventory_layers.py` writes `metadata.migration_id="fase6"`).
- Never `delete_many` + `insert_one`; always `$set` + defaults.
- Sentinel `layer_id` patterns (e.g. `INV-OPENING-XXXX`) for distinguishability from real restock rows.
- Backfill patterns to know:
  - `migrate_inventory_layers.py` (Fase 6) — `opening_stock` layers for products with qty>0 and no layer.
  - `migrate_add_inventory_fields.py` (Fase 5) — cost_price/type/default_supplier defaults.
  - Other `migrate_*.py` follow the same shape.

### PBAC sync (`server/scripts/sync_pbac_permissions.py`)

- **Canonical-driven sync** (agosto 2026): converge una BD a `init_security_model_ga03.py` sin conocer el delta. Tres superficies, todas derivadas del catálogo canónico (`PERMISSION_CATALOG` + `ROLE_PERMISSION_CODES`): `permissions` (upsert de códigos faltantes), `roles` globales (`$set` — el template es fuente de verdad, misma semántica que `sync_role_permissions.py`) y `hotel_roles` (`$addToSet` ADITIVO — los clones por hotel admiten personalización, nunca se eliminan códigos).
- **Idempotente** por diseño (segunda pasada = 0 modificaciones; no churnea `updated_at`). Acepta `--dry-run`. Tests: `server/tests/test_pbac_sync.py`.
- Uso: `docker compose --env-file .env -f infra/docker-compose.yml exec -T server python -m scripts.sync_pbac_permissions [--dry-run]` (apunta a la BD de la env var).
- Caso real: tras Sprint 3 (`check-ins.early_approve`), el rol global `gerente_hotel` de dev y los clones de `hotel_roles` estaban stale (sin la familia `check-ins.*`) y `socio.gta6` no podía aprobar early check-in ni abrir la vista; el sync los alineó.

### Fact-inventory layer model (Fase 6 — FIFO/LIFO COGS)

- Collection: `fact_inventory` (one row per acquisition).
- Schema fields: `prop_id`, `product_id`, `layer_id` (sentinel), `qty_initial`, `qty_remaining`, `cost_per_unit`, `acquired_at`, `source` (`restock|opening_stock|manual_adjustment`), `supplier_name`, `invoice_ref`, `consumed_at`, `is_active`.
- Write path: `restock_product()` calls `insert_inventory_layer()`; migration script inserts `opening_stock` for pre-Fase 6 products.
- Read path: `compute_cogs_report()` calls `drain_layers_for_sale(method=fifo|lifo|approx, persist=True)` per product.
- Wire shape extension on `/api/management/products/reports/cogs`: `method` (echo), `summary.fallback_units_across_products`, `items[].layer_breakdown[]`.

## Docker Safety Rules

- **NEVER** `docker compose down --volumes` or `docker compose down -v`
- **NEVER** `git commit` / `git push` without explicit authorization
- **NEVER** delete files, MongoDB collections, or data without asking
- **NEVER** overwrite `.env` or `docker-compose.yml` without informing
- Code volume mounts mean no rebuild needed for source code changes

## Credentials

See `.credentials/credenciales.md` for actual login credentials.
**NEVER** guess passwords. If account is locked (423), unlock via MongoDB command documented in AGENTS.md.

## ETL Pipeline (GA03)

| Mode | Behavior |
|------|----------|
| **Full** (`GA03_INCREMENTAL_MODE=false`, default) | Deletes all + re-inserts from PocketBase |
| **Incremental** (`GA03_INCREMENTAL_MODE=true`) | Uses `last_extracted_at` state file, only processes new records |

## Migration history (decisions that were reverted or changed)

Read this before suggesting any new ObjectId/JSON serialisation refactor — there is context that was lost in prior sessions.

### 🚫 ObjectIdStr helper at every callsite — REVERTED

**HARD RULE — DO NOT reintroduce a `to_id_str()` helper, DO NOT migrate more sites to it.** The previous attempt was explicitly reverted by the user. If you are tempted to refactor ObjectId→string serialisation, use the Pydantic `*Response` pattern below instead.

- Earlier session introduced a `to_id_str()` helper in `server/src/app/core/types.py` and migrated ~33 call sites in `server/src/app/modules/` to use it (services that previously did `str(x['_id'])` would call `to_id_str(x)` instead).
- User explicitly reverted: *"Revertir to_id_str(): borrar el helper de core/types.py, los 4 tests, y restaurar `str(x['_id'])` en los 33 sitios migrateados. Quedarse solo con el POC HotelProductResponse en hotel_products."*
- Current canonical (as of 2026-Q2):
  - `ObjectIdStr` exists in `server/src/app/core/types.py` ONLY for use **inside** a `*Response(BaseModel)` class via `Field(validation_alias="_id", serialization_alias="id")`. ~5 call sites (POC + sparse references).
  - Services return raw MongoDB docs (`_id: ObjectId`); Pydantic owns wire shape at the route boundary.
  - `str(_id)` sites remaining in `server/src/app/modules/`: ~50 (intentional — those services don't have `*Response` yet; they await migration).

### Pydantic `*Response` migration — IN PROGRESS (canonical direction)

- **Scope so far (reference examples to follow)**:
  - `server/src/app/modules/partner/routes/hotels.py` (history module — **first wave of `*Response` work**, before products feature) — 5 `*Response` classes: `ChangeRecordResponse`, `PaginationResponse`, `FilterOptionsResponse`, `PropertyHistoryListResponse`, `ChangeDetailResponse`; 2 endpoints with `response_model=`.
  - `server/src/app/modules/partner/routes/hotel_products.py` (products + reports — **second wave**, layered on during Fase 5 + Fase 6 of the products feature; grew incrementally with the feature) — ~12 `*Response` classes: `HotelProductResponse`, `MarginSummaryResponse`, `MarginReportItemResponse`, `MarginReportResponse`, `CogsSummaryResponse`, `CogsReportItemResponse`, `CogsReportResponse`, `LayerBreakdownItemResponse`, `StockValueSummaryResponse`, `StockCategorySummary`, `StockValueItemResponse`, `StockValueReportResponse`.
- **Pattern**: service returns raw docs; route adds `response_model=*Response`; Pydantic + `ObjectIdStr` handle `_id → "id"` and `datetime → ISO`.
- **NOT yet migrated**: ~21 sites across `instay/`, `reservations/`, `billing/`, `expenses/`, `hr/`, `auth/`, `admin/`, plus other `partner/` routes. They still return raw `dict` and rely on the frontend's defensive `str(x.get('_id', ''))` patterns. When migrating a module: 1 `*Response` per endpoint, docstring says **KEEP IN SYNC** with the TS DTO.

### Feature auth services — IN PROGRESS (canonical direction)

- Created `products/services/products-auth.service.ts` and `reservations/services/reservations-auth.service.ts` to centralise duplicated role-list computed signals.
- Audit found `housekeeping/` and `reception/` had 0 real role-gate duplications → no service created for those (creating empty services would be debt). Do not create services speculatively.

### Sprint llegadas tardías y no-show — matriz de autorización (2026-08)

| Capacidad | Endpoint | Permiso | Roles |
|---|---|---|---|
| Ver detalle/lista de check-ins | `GET /api/management/check-ins/...` | `check-ins.read` | recepcionista, gerente_hotel, super_admin |
| Completar check-in normal/cortesía | `POST .../check-ins/{id}/complete` | `check-ins.manage` | recepcionista, gerente_hotel, super_admin |
| Aprobar early check-in fuera de cortesía | `POST .../check-ins/{id}/complete` (`early_approved`) | `check-ins.early_approve` + role allow-list (`MANAGER_AUTHORIZATION_ROLES`) | gerente_hotel, super_admin |
| Aprobar late check-out fuera de cortesía | `complete_check_out` (`late_approved`) | `check-ins.late_checkout_approve` + role allow-list (`MANAGER_AUTHORIZATION_ROLES`) | gerente_hotel, super_admin |
| Marcar no-show manual | `POST /api/management/bookings/{id}/no-show` | `reservations.update` | recepcionista, gerente_hotel, super_admin |
| Declarar/retirar llegada tardía | `POST .../check-ins/{id}/declare-late-arrival` | `check-ins.manage` | recepcionista, gerente_hotel, super_admin |
| Reabrir no-show (caso gerente) | `POST /api/management/bookings/{id}/reopen-no-show` | `check-ins.no_show_reopen` + role allow-list (`MANAGER_AUTHORIZATION_ROLES`) | gerente_hotel, super_admin |
| Cerrar folio con saldo (write-off / cortesía / settlement externo) | `POST /api/billing/folios/{id}/close` (`close_reason` de excepción) | `billing.write_off.approve` + role allow-list (`SUPERVISOR_AUTHORIZATION_ROLES`) | gerente_hotel, admin_sistema, super_admin |

**State machine Stay** (`src/app/core/state_machine.py`): `pending → checked_in / no_show`; `checked_in → checked_out`; **`no_show → pending`** (única salida del no-show, reapertura gerencial; el guard de `reopen_no_show` usa `stay_sm.can_transition`). La llegada tardía (`declared_late_arrival`, `estimated_arrival_time`, `late_checkin`) son **señales de política**, no estados de `stay_status`. Los códigos `check-ins.early_approve` / `check-ins.no_show_reopen` / `check-ins.late_checkout_approve` viven en el catálogo canónico (`init_security_model_ga03.py`) y en `server/src/app/security/permissions.py`. Los tres comparten **un solo gate**: `require_manager_authorization(db, user, permission_code=...)` con role allow-list `MANAGER_AUTHORIZATION_ROLES` (defensa en profundidad — un grant ad-hoc a recepción no alcanza sin el rol primario en la lista); NO se otorgan a `recepcionista`. Pruebas de autorización: `test_no_show_reopen.py`, `test_early_check_in_permissions.py`, `test_late_arrival_auth.py`, `test_late_checkout_permissions.py` (incluye los casos límite: **super_admin inactivo** → denegado — la inactividad antecede al bypass — y **grant solo vía `hotel_roles` con `prop_id`** → el gate global lo deniega (no hay fuga del RBAC por hotel a la autoridad global); `user_has_permission` con `prop_id` honra el grant y otro hotel sin asignación cae en deny-by-default).

**Autorización de supervisor para ajustes del folio (2026-08):** cierre unificado del patrón gerencial a otras áreas. `require_supervisor_authorization(db, user, permission_code=...)` reusa `require_manager_authorization` completo (inactivo → False, super_admin bypass, role allow-list + permiso embebido) cambiando el default a `SUPERVISOR_AUTHORIZATION_ROLES` (gerente_hotel, admin_sistema, super_admin). Primer caso real: `billing.write_off.approve` en el catálogo canónico (`init_security_model_ga03.py`; en super_admin vía la comprehensión del catálogo, admin_sistema y gerente_hotel; NO en recepcionista) gatea `close_folio_api` — la recepción conserva `billing.manage` (cierre normal/cortesía sin saldo) pero un `close_reason` de excepción (`approved_write_off` / `complimentary_stay` / `approved_external_settlement`) exige supervisor (403 antes de tocar el folio). La base de la ruta usa `require_any_permission("billing.manage", "billing.write_off.approve")` — **varargs, nunca una lista** (pasar una lista hace que `code` sea la lista completa y `user_has_permission` explota con `TypeError: unhashable type: 'list'`). Tests: `test_folio_write_off_approval.py` (catálogo, unit del gate con allow-list custom e inactivos, RBAC por hotel sin fuga, y 403 recepcionista / 200 gerente y admin_sistema / cierre normal de recepción intacto vía ruta).

**Ventana de reapertura (2026-08):** solo se reabren no-shows con **check-in de HOY o AYER y estadía vigente** (check-out sin vencer) — guard en `reopen_no_show` (400 con reserva intacta) y gate+copy en la UI (botón oculto y bloque "Ventana de reapertura cerrada" con copy `too_late`/`stay_ended": "Ajustá las fechas o creá una reserva nueva"). Reabrir un no-show antiguo colapsaría la estancia con las de otras fechas (inventario, folios, facturación). Tests: `test_no_show_reopen.py` (ayer vigente permitido, 2+ días bloqueado, estadía terminada bloqueada, mensaje guía a nueva reserva) y `check-in-detail-page.spec.ts`.

**Ventana de reapertura en el calendario de Recepción (2026-08):** el endpoint `/api/management/reception/calendar` expone por reserva `stay_status` + `reopen_window` (`'open'` / `'too_late'` / `'stay_ended'` / `null`), calculado con `reopen_window_reason` — helper extraído del guard de `reopen_no_show` (una sola regla: check-in de hoy/ayer + estadía vigente, sin duplicación backend/UI). El timeline (Syncfusion Schedule) marca los no-shows con el icono `event_busy` (`appendNoShowMarker`, mismo patrón DOM-runtime que el late-checkin) y los reabribles agregan la clase `is-reopenable` + chip ámbar "Reabrible"; los antiguos quedan sin chip (la API los rechazaría). El modal de detalle (abre desde el calendario) refleja la ventana: alert `is-warning`/`is-danger` con copy que orienta (reapertura abierta vs "Ajustá las fechas o creá una reserva nueva") y el botón **Reabrir no-show** SOLO dentro de la ventana + permiso `check-ins.no_show_reopen` (oculto en antiguos o sin permiso), con diálogo de motivo que reusa `CheckInsApiService.reopenNoShow` y emite `reopened` → el timeline recarga. Tests: `test_reception_calendar.py` (ruta expone stay_status/reopen_window), `test_no_show_reopen.py` (unit del helper), `reception-timeline.spec.ts` (marcador reabrible/antiguo/no-aplica) y `reservation-detail-modal.spec.ts` (nuevo: gate por ventana + permiso, copy, flujo de reapertura con motivo).

**Diagnóstico read-only de no-shows (2026-08):** `/api/management/reception/no-shows/reopen-window` (mismo gate que el calendario: `reservations.read` — la recepción consulta qué derivar al gerente, pero la ACCIÓN sigue exigiendo `check-ins.no_show_reopen`). Lista los no-shows del hotel con `reopen_window` (`open`/`too_late`/`stay_ended`), `reopenable`, `days_late`, `no_show_penalty_amount`, `no_show_processed_at` y `room_number` resuelto; devuelve totales `reopenable`/`closed`. Misma regla `reopen_window_reason` — cero duplicación de ventana. Tests: `test_no_show_window_diagnostic_splits_reopenable_vs_closed` (separación open/too_late/stay_ended, no-no-shows excluidos, habitación resuelta) y `test_receptionist_can_read_no_show_window_diagnostic` (recepción con `reservations.manage`→read alcanza el endpoint; la acción sigue siendo gerencial).

**Mensajes con acción concreta (2026-08):** los errores del flujo check-in/no-show apuntan a acciones (ajustar fechas, crear reserva, contactar gerencia) en vez de describir el estado — mismo criterio que la ventana de reapertura. Backend: no_show (estado inválido → verificar estado; antes del check-in → esperar/ajustar fecha; no-no-show → check-in normal; estadía terminada → ajustar fechas/crear reserva), _checkin (no-show explícito → pedir reapertura/ajustar/crear; vencido → crear reserva; fecha futura → esperar/ajustar; habitaciones no disponibles → liberar/limpiar/asignar otra; early sin habitación → asignar antes; ya en horario normal → check-in sin early; aprobación requerida → marcar autorización/contactar gerencia; fee inválido → verificar política; traducción de los guards ingleses), late_arrival (cancelada/rechazada → crear/contactar; no-show → pedir reapertura) y _checkin_detail (cancelada/rechazada → crear/contactar). Frontend: los bloques gate de check-in-detail-page (no-show, fecha futura, early sin permiso) agregan la acción al copy accesible. Tests: `test_noshow_checkin_checkout_guards.py` (clase `TestErrorMessagesGuideToActions`, 7 tests que fijan las acciones por subcadena).

**Endurecimiento de inventario en reapertura (2026-08):** el no-show liberó las noches (`_restore_inventory`); `reopen_no_show` **revalida y re-deduce** TODA la estancia (`_deduct_inventory`, transacción all-or-nothing) ANTES de mutar la reserva y estampa `inventory_re_deducted_at/by` (marca de idempotencia). Si una noche ya fue re-vendida o falta la fila de calendario, la reapertura falla (400) con la reserva intacta en `no_show`. `complete_check_in` tiene la red de seguridad para reabiertas pre-endurecimiento: sin la marca → re-deduce y la estampa; con la marca → NO vuelve a deducir (sin doble conteo). Reservas sin `room_type_id` se reabren sin re-deducción (misma semántica del restore). Tests: `test_no_show_reopen.py` (re-deducción en ruta, fallo por inventario insuficiente y por filas faltantes — reserva intacta, check-in sin marca re-deduce, con marca no duplica).

### Late check-out — ventana gobernada (2026-08)

Implementado de punta a punta. **Política** (`late_checkout_enabled` default True, `late_checkout_courtesy_minutes` default 60 clamp 0–240, `late_checkout_default_fee` default 0) en `hotel_policies` (hotel-wide, mismo contrato que `early_check_in_*`; filas por tipo/plan nunca la pisan), editable en Políticas. **Contexto/validación** `get_late_checkout_context` / `validate_late_checkout` (`_checkinout/_checkout.py`): la ventana aplica solo el día del check-out tras la hora; dentro de la cortesía → `late_courtesy` sin cargo; fuera → `late_approved` (permiso + motivo + cargo); **política deshabilitada = no hay ventana** (la salida no se bloquea — el huésped se va — a diferencia del early check-in que sí bloquea la llegada). **Flujo**: `complete_check_out` valida el modo, registra `check_out_mode`/`late_checkout_minutes`/`late_checkout_fee`/`late_checkout_approved_by/at/reason`/`late_checkout_policy_time`, y **postea el fee derivado del reloj al folio** (`post_to_folio`, categoría "Late check-out", antes de liquidar/cerrar). **Ruta** `POST /check-outs/{id}/complete`: gate 403 `check-ins.late_checkout_approve` cuando el modo es `late_approved` (defensa en profundidad también en el servicio). El detalle expone `late_checkout_context` (server-authoritative) y la UI (paso Liquidación) muestra cortesía / aprobación con motivo+cargo / bloqueo sin permiso. **Corrección de catálogo**: `gerente_hotel` no tenía `check-outs.manage` (no podía completar ningún check-out — el flujo del gerente era inalcanzable); se agregó al rol canónico. Tests: `test_late_checkout_policy.py`, `test_late_checkout_permissions.py` (incluye 403 de recepcionista y 200 del gerente vía ruta), `test_late_checkout_flow.py` (cortesía, aprobación, fee al folio, defensa en profundidad, disabled). **Endurecimiento del turno:** `register_transaction` re-lee el folio DESPUÉS del posting del fee (el fetch inicial quedaba antes y el reporte de turno sub-colectaba el late) — test de conciliación `test_approved_late_fee_reconciles_in_folio_and_shift` (shift.amount == folio.total_due == fee). **Mismo endurecimiento en el check-in (2026-08):** el txn de `check_in` corría con `amount=0` ANTES de crear el folio y postear el early fee — el early check-in desaparecía del reporte de turno. Ahora `register_transaction` se mueve al final del flujo (después de `create_folio` + `post_to_folio` del early) y re-lee el folio fresco: `amount = folio.total_due` (habitación + cargos − descuentos − pagos), fallback a `total_price` si no hay folio. Test de conciliación `TestEarlyFeeEntersShift::test_early_fee_reconciles_in_folio_and_shift` en `test_early_check_in.py` (shift.amount == folio.total_due == 243 = 218 habitación + 25 fee). **Notificación al equipo:** `late_approved` inserta en `notification_log` (`notification_type=late_checkout_approved`, patrón `housekeeping_check_in` del check-in) avisando a recepción/housekeeping que la salida se extendió, con la hora real (`actual_check_out_time` = `local_now`), minutos de retraso y cargo — `_notify_staff_late_checkout` en `_helpers.py`; test `test_approved_late_checkout_notifies_team_with_real_time`. **Cortesía también notifica (2026-08):** `late_courtesy` dispara la misma notificación (`notification_type=late_checkout_courtesy`, subject y mensaje distintos, sin línea de cargo, `metadata.late_checkout_mode` distingue la traza) — la salida extendida afecta igual a la limpieza aunque no haya fee; el caller de `complete_check_out` cubre ambos modos (`late_mode in ("late_approved", "late_courtesy")`); test `test_courtesy_late_checkout_notifies_team_without_fee`. **Mismo criterio en el early check-in (2026-08):** `_notify_staff_early_checkin` (espejo del late en `_helpers.py`) cubre ambos modos — `early_approved` → `notification_type=early_checkin_approved` (con cargo y motivo) y `early_courtesy` → `notification_type=early_checkin_courtesy` (sin cargo, dentro de la cortesía; la limpieza se ajusta igual aunque no haya fee) — con hora real (`actual_check_in_time` = `local_now`), minutos de antelación, hora de política y `metadata.early_checkin_mode` distinguiendo la traza (sin campos heredados del late). El caller de `complete_check_in` dispara cuando `early_mode in ("early_approved", "early_courtesy")`; tests `test_approved_early_checkin_notifies_team_with_real_time` y `test_courtesy_early_checkin_notifies_team_without_fee` en `test_early_check_in.py`. **Hora real de salida en el detalle (2026-08):** además de la notificación, recepción lee la salida extendida en el detalle del check-out. `get_late_checkout_context` expone `real_time` (hora local del servidor cuando hay ventana late) — el paso Liquidación muestra "Salida real: HH:MM hrs (hora actual del hotel)". Al completar, `complete_check_out` estampa `check_out_time_actual`/`check_out_date_actual` en **hora LOCAL del hotel** (antes UTC — mezclaba relojes con la política, la notificación y el check-in; es el campo legible para recepción) y el detalle (`_checkout_detail.py`) expone además `late_checkout_policy_time` (estampada al completar, fuente de verdad vs el contexto en vivo). La vista de check-out completado muestra la fila "Salida extendida — Aprobado/Cortesía · N min tras las HH:MM de política" cuando el modo es late. Tests: `test_late_context_exposes_real_departure_time` y `test_check_out_detail_exposes_extended_departure_fields` (backend) + `check-out-detail-page.spec.ts` (panel "Salida real" en Liquidación y fila "Salida extendida" en la vista completada).

### Postings automáticos — categoría por id de catálogo (2026-08)

Los postings automáticos (late check-out, early check-in, penalización no-show) ahora usan el **id canónico del catálogo** (`category_id`: `late_checkout`/`early_checkin`/`no_show` en `FOLIO_CATEGORIES` — `folio.py` — con label e icono) y **el frontend resuelve label/icono por el id**, no por string-matching del label. `post_to_folio` acepta `category_id`, resuelve el label del catálogo (el `category` guardado sigue siendo el label para los consumidores de texto: facturas, revenue) y estampa `category_id` en el posting; además normaliza el quirk histórico de los postings manuales que guardaban el id como `category` (id → label + `category_id`). El detalle del folio (`folio-detail-page.ts`): agrupa por `categoryId ?? category`, `categoryIcon`/`categoryLabel` resuelven por id del catálogo con fallback a labels legados (`'Late check-out'`, `'Late Check-Out'`, `'Early check-in'`, `'Penalización'` → `schedule`/`alarm`/`event_busy`) y genérico `receipt_long`. Antes: el frontend compensaba con `labelAliases` de strings y "Penalización"/"Early check-in" caían al default — el mismatch de icono que esto evita. Tests: `test_late_checkout_flow.py` (posting late con `category_id` + label resuelto), `test_early_check_in.py`, `test_no_show_reopen.py` (fixture del seed en forma canónica) y `folio-detail-page.spec.ts` (6 tests: icono/label por id para no-show y early, fallback legado, sin atribución).

### Sync PBAC — 4ª superficie: navegación (2026-08)

`sync_pbac_permissions.py` alinea ahora CUATRO superficies: `permissions` (upsert), **`navigation`** (convergencia con `NAVIGATION_CATALOG`: nodos nuevos con `permission_id`/`parent_id` resueltos; huérfanos reportados sin eliminar), `roles` ($set) y `hotel_roles` ($addToSet aditivo). El editor de roles del frontend NO necesita sync extra: lee las colecciones `permissions`/`roles`/`navigation` (cubiertas por el sync) y su agrupación por secciones es función pura del código (`role-permission-sections.ts`). El hueco original: el catálogo define `NAVIGATION_CATALOG` pero el sync no lo aplicaba — un nodo nuevo (ej. `gestion.pms.promociones`) nunca aparecía en dev aunque los roles estuvieran alineados.
