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
