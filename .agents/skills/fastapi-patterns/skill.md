---
name: fastapi-patterns
description: FastAPI + Pydantic v2 + MongoDB patterns for HotelData Hub. Cubre estructura de proyecto, schemas con ObjectIdStr, dependency injection, async routers, integration con MongoDB a través de services que retornan docs nativos, *Response wire-shape convention, jsonable_encoder monkey-patch defensa-en-profundidad, y testing con pytest-asyncio + httpx + MongoDB real en hoteldata_hub_test.
metadata:
  origin: ecc
  origin_path: https://github.com/affaan-m/ECC/tree/main/skills/fastapi-patterns
  license: MIT (origen)
  adaptation: 2026-07-28
  adr: .specify/decisions/ADR-0002-poach-fastapi-patterns.md
---

# fastapi-patterns — HotelData Hub (adaptación de ECC)

> **Origen**: adaptación de `https://github.com/affaan-m/ECC/tree/main/skills/fastapi-patterns` — prompt MIT-licensed de affaan-m. NO instalamos ECC completo: solo poachamos el contenido y lo reescribimos con reglas duras del proyecto verificadas contra código real (`server/src/app/main.py`, `server/src/database/connection.py`, `server/src/app/core/types.py`, `server/src/app/modules/partner/services/_inventory.py`).
> **Razón de ser**: matar los bugs recurrentes que `knowledge.md` documenta (PydanticUserError, model_rebuild, banner-collapse, stale __pycache__) y alinear las decisiones de código con la Constitución v0.9 + ADRs vigentes.
> **KEEP IN SYNC**: si una regla del proyecto cambia (e.g. ADR-0001 estableció un patrón de cutover), actualizá este skill en el mismo PR. NO edites la Constitución para acomodar el skill — el skill refleja la Constitución.

> **Smoke-test de este skill**: las reglas §A/§B/§C/§D se validan con `python -m pytest -q server/tests/test_reservations.py`. Si ese test pasa + status 200/401 (no 500), las reglas están bien aplicadas. Si retorna 500 con `TypeAdapter not fully defined` o `PydanticUndefinedAnnotation`, **es bug del skill o del route**, no del test. Ver §Smoke Test Post-Authoring más abajo.

---

## Project Structure (HotelData — paths VERIFICADOS contra código real)

```text
hoteldata_project/
├── frontend/                       # Angular 22 standalone (NO toca este skill)
├── server/
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/                # Pydantic v2 type aliases (ObjectIdStr, ListToCommaStr, to_json_safe)
│   │   │   │   └── types.py         # ← IMPORTANTE. Todos los *Response usan ObjectIdStr aquí.
│   │   │   ├── modules/             # 27 módulos FastAPI. Cada uno con routes/ + service/ + schemas.py.
│   │   │   │   └── <module>/
│   │   │   │       ├── routes.py    # Service → *Response (NO lógica de negocio)
│   │   │   │       ├── service/     # Lógica de negocio + acceso MongoDB
│   │   │   │       └── schemas.py   # *Response classes con ObjectIdStr + model_rebuild()
│   │   │   └── main.py              # create_app() + lifespan() (root de la FastAPI app)
│   │   ├── database/                # NOT under `app/`. MongoClient singleton + connection lifecycle.
│   │   │   └── connection.py        # ← REAL: `from src.database.connection import get_database`
│   │   └── security/                # rate_limit, session, middleware
│   ├── tests/                       # pytest-asyncio + httpx ASGITransport (no live server)
│   │   ├── conftest.py              # Fixtures: app, client, db, cliente_user, admin_user
│   │   └── test_*.py
│   ├── dags/                        # Airflow DAGs — CERO imports de src.app (ver §G abajo)
│   ├── scripts/                     # Idempotent scripts (migrations + ETL)
│   └── pyproject.toml
└── infra/
    └── docker-compose.yml           # 8 servicios. NO docker volume rm. (Docker Safety §)
```

Diferencias con la estructura de ECC en su repo de origen:

| ECC default | HotelData |
|---|---|
| `app/database.py` (SQLAlchemy) | `src/database/connection.py` con `MongoClient` singleton lazy |
| `app/models/` (SQLAlchemy ORM) | NO existe. MongoDB no usa ORM.  En su lugar: `service/` retorna dicts nativos |
| `app/schemas/` (Pydantic-only) | `schemas.py` con **`*Request` + `*Response` exclusivamente** — entidades NO |
| `tests/` con sqlite+aiosqlite | `tests/` con MongoDB REAL contra `hoteldata_hub_test` (drop on each test) |
| Lifespan centralizado con `Base.metadata.create_all` | Lifespan **descentralizado**: cada módulo llama `ensure_<feature>_collections()` en su `__init__.py` o `service/collections.py` |
| Sin global ObjectId → str encoder | **Both required together**: per-model `ObjectIdStr` annotations + global `jsonable_encoder` monkey-patch (líneas 17-44 main.py) — quitar uno introduce bugs — ver §A |

---

## Reglas Duras de HotelData (la columna vertebral del skill)

### A. Wire shape convention (services → routes → `*Response`) + jsonable_encoder double-defensa

**EL patrón canónico para endpoints nuevos** (startó en `partner/routes/hotels.py` y `partner/routes/hotel_products.py`, **NO** es válido todavía en `instay/`, `reservations/`, `billing/`, `expenses/`, `hr/`, `auth/`, `admin/` — esos están en backlog):

```python
# service.py — retorna RAW MongoDB docs (sin transformación)
async def list_reservations(filter: dict) -> list[dict]:
    return list(db.booking_orders.find(filter).limit(50))

# routes.py — usa *Response para serializar al wire (NUNCA retorna dict directo)
@router.get("/reservations", response_model=list[ReservationResponse])
async def list_(
    filter: Annotated[ReservationFilter, Depends()],
) -> list[ReservationResponse]:
    docs = await service.list_reservations(filter.model_dump())
    # Belt-and-suspenders: pre-clean antes de model_validate
    safe_docs = [to_json_safe(d) for d in docs]
    return [ReservationResponse.model_validate(d) for d in safe_docs]


# schemas.py — pydantic owns wire shape
from src.app.core.types import ObjectIdStr

class ReservationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    booking_id: str
    guest_name: str
    check_in_date: date
    ...
```

**Por qué**: Pydantic v2 + FastAPI `TypeAdapter` son la única fuente que debe hacer `_id → "id"`, `datetime → ISO`, `Decimal128 → float`. Service layer queda limpio (retorna nativos), route layer queda limpio (delega a Pydantic), y el bug del frontend que recibía `{"$oid": "..."}` queda eliminado.

**Doble defensa — el `jsonable_encoder` monkey-patch en `server/src/app/main.py` líneas 17-44**:

El proyecto tiene **AMBAS** defensas corriendo en paralelo:

1. **Per-model**: cada `*Response` define su(s) campo(s) `id: ObjectIdStr = Field(...)`. Cuando el model se valida, Pydantic hace `_id → "id"` automáticamente.
2. **Global encoder**: el patch al inicio de `main.py` reescribe `fastapi.encoders.jsonable_encoder` y `fastapi.routing.jsonable_encoder` para que cualquier `ObjectId` (incluso anidado en `dict[BaseModel]`, `model_dump(mode="json")`, Response JSON manual) se serialice a `str` recursivamente.

Las dos son **complementarias**, no redundantes. Borrar una u otra introduces bugs. Las dos deben coexistir siempre.

**Post-migration cleaning pattern — `assigned_rooms` reshape**:

Si una collection post-FK-migration tiene `assigned_rooms: list[dict]` (cada dict con `hotel_room_id`, `room_id`, `status`, etc.) pero el `*Response` espera `assigned_rooms: list[str]` (los IDs), hay dos ubicaciones válidas para el reshape:

```python
# OPCIÓN 1 (recomendada por el user): dentro de `to_json_safe()` en `core/types.py`.
# Cross-cutting: aplica a TODO route que pase por to_json_safe.
def to_json_safe(value):
    if isinstance(value, dict) and "assigned_rooms" in value:
        raw = value["assigned_rooms"]
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            value["assigned_rooms"] = [
                r.get("hotel_room_id") or r.get("room_id") or r.get("_id")
                for r in raw
            ]
    # ... resto del walker
```

```python
# OPCIÓN 2: route-local helper en `reservations/routes/reservations.py:166`.
# Surgical: solo este endpoint. Sin cross-cutting effect.
def _flatten_assigned_rooms(doc):
    raw = doc.get("assigned_rooms")
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        doc["assigned_rooms"] = [r.get("hotel_room_id") or r.get("room_id") or r.get("_id") for r in raw]
    return doc

@router.get("/reservations/{booking_id}", response_model=ReservationResponse)
async def get_(booking_id: str, _user=Depends(...)):
    raw = await service.get_by_booking_id(booking_id)
    if raw is None:
        raise HTTPException(404, ...)
    return ReservationResponse.model_validate(_flatten_assigned_rooms(to_json_safe(raw)))
```

Cualquiera de las dos opciones es válida. La consistencia con el resto del route layer decide cuál.

**Anti-pattern explícito** (NO hacer):

```python
# MAL: str(x['_id']) en cada callsite (esto es lo que el revert-2026-Q2 eliminó).
return {"id": str(doc["_id"]), "name": doc["name"]}

# BIEN: Pydantic *Response owns wire shape.
class ReservationResponse(BaseModel):
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    name: str
return ReservationResponse.model_validate(doc)
```

### B. `from __future__ import annotations` + banner-collapse (TRIPLE GUARD)

Bugs históricos documentados en `knowledge.md` (Fase 6 COGS 500, Auth + Account migration). Las TRES condiciones son necesarias para que la regla aplique. **Cualquier ruta con `from __future__ import annotations` + `response_model=` + `ObjectIdStr` debe cumplir las tres reglas**.

**Regla B1 — Banner separation**: NUNCA colapse `# ── Section Banner ──` con `class X(BaseModel):` en el mismo renglón. Python trata `#` como comentario, convierte todo el resto de la línea en comentario, así que la clase no se agrega al módulo.

```python
# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ───    ← banner solo


class HotelProductResponse(BaseModel):                                       ← clase en su propia línea
    ...
```

**Regla B2 — Every model with `ObjectIdStr` needs `model_config = ConfigDict(populate_by_name=True)`**. Sin esto, cuando los `$`-prefixed field aliases de Field chocan con populate-by-name o cuando FastAPI construye el response_model, los campos no se matchean.

**Regla B3 — Explicit `model_rebuild()` call** AFTER all class definitions AND BEFORE first `@router.` decorator:

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
@router.get(...)
```

### C. `ObjectIdStr` y `ListToCommaStr` desde `core/types.py`

NO reinventes el type alias en cada archivo. El canónico es (`server/src/app/core/types.py`):

```python
from src.app.core.types import ObjectIdStr, ListToCommaStr, to_json_safe
```

- `ObjectIdStr = Annotated[str, BeforeValidator(_serialize_object_id)]` — usado en todo campo ID derivado de Mongo `_id` o FK-by-ObjectId post-migration.
- `ListToCommaStr = Annotated[str, BeforeValidator(_join_list_to_str)]` — usado en campos como `special_requests` que históricamente son `list[str]` en Mongo pero `str` en el wire.
- `to_json_safe(v)` — helper pre-clean recursivo, paralelizable a `model_validate()`. Usar SIEMPRE antes de `model_validate(...)` en rutas que aún no estén migradas al patrón A (defense in depth).

### D. Cache-clear ritual (post-merge de delete/alias mutation en `*Response`)

> **Canonical reference**: `knowledge.md` §API convention — Cache-clear ritual (texto íntegro del ritual allí).

Después de **borrar** cualquier `*Response` Pydantic class (o mutar `validation_alias` / `serialization_alias`), stale `.pyc` puede seguir cargándose desde `__pycache__/`. **OBLIGATORIO** correr:

```bash
docker compose -f infra/docker-compose.yml exec -T server find /app/server -name __pycache__ -exec rm -rf {} + \
  && docker compose -f infra/docker-compose.yml restart server
```

El primer comando borra cada `__pycache__/` para que el próximo interpreter boot lea de `.py` source. El `restart` es necesario porque Python cargó el bytecode stale en el boot previo. Sin este ritual,`ImportError: cannot import name 'XResponse'` aparece como fantasma de una clase ya eliminada (regression reportada en `knowledge.md`).

### E. MongoDB dual-write §VII (módulos operacionales → analytics)

Cualquier módulo que produzca data que también se trackea en `fact_*` debe implementar dual-write en el mismo request.

**Patrón atómico verificado contra código real** (`server/src/app/modules/partner/services/_inventory.py`):

```python
def _atomic_layer_decrement(db, layer_id, take):
    """Atomically consume `take` units from one `fact_inventory` layer (Fase 6 FIFO/LIFO)."""
    if take <= 0:
        return True
    dec = round(float(take), 4)
    now = now_utc()
    result = db.fact_inventory.update_one(
        {
            "_id": layer_id,
            "qty_remaining": {"$gte": dec},        # ← guard: layer must still have enough
        },
        [
            {
                "$set": {
                    # ``$round`` keeps precision consistent with restocks + migration script.
                    "qty_remaining": {
                        "$round": [{"$subtract": ["$qty_remaining", dec]}, 4],
                    },
                    # ``$lte`` (PRE-decrement value). When pre-decrement qty_remaining <= take,
                    # the layer reaches 0 (or below) — stamp consumed_at and flip is_active.
                    "consumed_at": {
                        "$cond": [
                            {"$lte": [{"$subtract": ["$qty_remaining", dec]}, 0]},
                            now,
                            "$consumed_at",
                        ],
                    },
                    "is_active": {
                        "$cond": [
                            {"$lte": [{"$subtract": ["$qty_remaining", dec]}, 0]},
                            False,
                            "$is_active",
                        ],
                    },
                }
            }
        ],
    )
    return result.modified_count >= 1
```

**Caller pattern — `drain_layers_for_sale`**:

FIFO/LIFO drain sobre `fact_inventory` con re-fetch del layer contended si `$gte` guard rechaza el update. Ver implementación completa en `_inventory.py:97-225`. Cada layer-drain es una llamada atómica separada — si dos coroutines compiten por el mismo layer, solo una gana; la otra re-fetchea y ajusta `take` o pop-ea el layer según el nuevo estado.

Para dual-write compensar use `etl_executions.pending_resume` con timestamp. Ver §VII de la Constitución.

### F. Airflow DAG boundary §II — La regla más ignorada

Cada nuevo DAG debe pasar `test_dag_boundaries.py`. La regla:

```python
# CORRECTO en dags/<pipeline>.py:
from config.settings import get_settings                # OK (Airflow's)
from src.etl.ta02_dimensions import build_dimensions    # OK (etl layer)
DB = get_settings().mongo_url                          # OK via settings

# MAL (rompe §II):
from src.app.main import app                           # NUNCA
from src.app.modules.billing import service_user        # NUNCA
import fastapi                                          # NUNCA en DAGs
from jinja2 import Template                             # NUNCA (templates son UI)
```

Test boundary en `tests/test_dag_boundaries.py` verifica el AST. Si introduce un import prohibido, el test falla antes que el DAG boot.

### G. NO `BashOperator`. PythonOperator en TODA tarea Airflow.

```python
# MAL:
BashOperator(task_id="extract", bash_command="python extract.py")

# BIEN:
@task
def extract() -> dict:
    ...
```

### H. Imports order (Ruff-friendly)

```python
from __future__ import annotations      # OBLIGATORIO en archivos con response_model=

# Standard library
import json
import threading
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

# Third party
import fastapi.encoders          # ← canónico para el jsonable_encoder patch
import fastapi.routing
from bson import ObjectId
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Local (absolute imports — NUNCA relativos)
from src.app.core.types import ObjectIdStr, ListToCommaStr, to_json_safe              # type aliases (canonical)
from src.database.connection import get_database                          # MongoClient singleton (NOT src.app.database)
from src.app.security.middleware import role_access_middleware    # app-level middleware
from config.settings import get_settings                          # project-level config
```

### I. Testing — pytest-asyncio + httpx ASGITransport (NO live server)

`server/tests/conftest.py` debe incluir:

```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.database.connection import get_database

@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Drop all collections in hoteldata_hub_test BEFORE each test."""
    await get_database().client.drop_database("hoteldata_hub_test")
    yield
```

**Reglas**:
- MongoDB REAL (no mock). Tests contra `hoteldata_hub_test` (DB aislada).
- Fixtures requeridos: `app`, `client`, `db`, `cliente_user`, `admin_user`.
- NO live server (uvicorn separado). ASGITransport en memoria.

---

## App Factory y Lifespan (HotelData-flavored, FAITHFUL contra `server/src/app/main.py`)

```python
# server/src/app/main.py — create_app() + lifespan() (scaled-down, see repo for full)
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

# ── Global ObjectId → str serialization — CRITICAL HotelData pattern ──
# Patch JSON encoder BEFORE FastAPI routes wire up. This complements
# `ObjectIdStr` annotated fields (defense-in-depth for nested structures
# where model_dump(mode="json") bypasses custom encoders).
import fastapi.encoders
import fastapi.routing
_original_je = fastapi.encoders.jsonable_encoder

def _patched_jsonable_encoder(obj, **kwargs):
    def _walk(o):
        if isinstance(o, ObjectId): return str(o)
        if isinstance(o, dict): return {k: _walk(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return type(o)(_walk(v) for v in o)
        if isinstance(o, BaseModel):
            valid_keys = {"include", "exclude", "by_alias", "exclude_unset", "exclude_defaults", "exclude_none"}
            kw = {k: v for k, v in kwargs.items() if k in valid_keys}
            d = getattr(o, "model_dump", getattr(o, "dict", None))(**kw)
            return _walk(d)
        return o
    custom_encoder = kwargs.pop("custom_encoder", {}) or {}
    custom_encoder[ObjectId] = str
    kwargs["custom_encoder"] = custom_encoder
    return _original_je(_walk(obj), **kwargs)

fastapi.encoders.jsonable_encoder = _patched_jsonable_encoder
fastapi.routing.jsonable_encoder = _patched_jsonable_encoder
# ──────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import get_settings
from src.database.connection import get_database          # ← REAL path (NOT src.app.database!)
from src.app.security.rate_limit import limiter
from src.app.security.middleware import role_access_middleware
from src.app.security.session import ensure_user_sessions_indexes, ensure_users_indexes
# 27+ ensure_*_collections imports from each module (one per feature module)
from src.app.core.outbox import (
    ensure_outbox_collection,
    process_pending_outbox,
    process_pending_outbox_forever,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HotelData", version="1.0.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=list(settings.cors_allowed_methods),
        allow_headers=list(settings.cors_allowed_headers),
    )
    app.middleware("http")(role_access_middleware)
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    # 50+ app.include_router(...) calls
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DECENTRALIZED bootstrap: cada módulo owns its own index/collections bootstrap.
    # No hay un singleton central `MongoClientSingleton.ensure_indexes()` —
    # cada `service.py` de cada feature expone su `ensure_<feature>_collections(db)`.
    ensure_users_indexes(get_database())
    ensure_user_sessions_indexes(get_database())
    ensure_default_catalogs()
    ensure_user_status_field()
    ensure_hotel_content_collections()
    ensure_hotel_profile_collections()
    ensure_inventory_collections()
    ensure_rate_collections()
    ensure_revenue_collections()
    ensure_reviews_collections()
    ensure_billing_collections()
    ensure_housekeeping_collections()
    ensure_reservation_collections()
    ensure_reception_collections()
    ensure_global_settings_collections()
    ensure_geo_collections()
    ensure_auth_collections()
    ensure_room_features_collections()
    ensure_lost_and_found_collections()
    ensure_hr_collections()
    ensure_expenses_collections()
    from src.app.modules.instay.routes import ensure_stay_collections
    ensure_stay_collections()
    ensure_audit_indexes()
    ensure_outbox_collection()
    process_pending_outbox(get_database())
    # Periodic outbox drainer for audit_log writes que fallaron inline (rare).
    # Daemon thread: uvicorn shutdown teardown natural, sin hang.
    threading.Thread(
        target=process_pending_outbox_forever,
        args=(get_database(),),
        daemon=True,
    ).start()
    threading.Thread(target=refresh_kpis_background, daemon=True).start()
    yield  # uvicorn toma el control; daemon threads mueren con el proceso — no explicit close


app = create_app()  # module-level ASGI entrypoint for uvicorn
```

**Camera traps ECC vs HotelData**:

| ECC default | HotelData reality (verificado en main.py) |
|---|---|
| `db = MongoClient(...)` module-level global | `from src.database.connection import get_database` (lazy pool, NO global) |
| `await engine.begin() ... create_all` en lifespan centralizado | DECENTRALIZED: 27+ `ensure_<feature>_collections()` calls (uno por módulo) |
| `app.add_middleware(CORSMiddleware, ...)` con valores hardcoded | Lee `settings.cors_allowed_*` desde `config/settings.py` |
| SlowAPI ausente | `SlowAPIMiddleware` + `limiter` desde `src.app.security.rate_limit` |
| Static mounts ausente | `app.mount("/static", StaticFiles(...))` + `app.mount("/uploads", ...)` |
| `await engine.dispose()` en shutdown | **Sin explicit close**; daemon threads die con uvicorn |
| Sin global encoder patch | **`jsonable_encoder` monkey-patch** (líneas 17-44 main.py) — defensa-en-profundidad complementaria a `ObjectIdStr` |

**Importante**: `MongoClientSingleton` era una propuesta ilustrativa del initial draft del skill (ya rechazada como hallucination por el code-reviewer). El patrón REAL es lazy connection via `get_database()`. NO copies `MongoClientSingleton` al código — no existe.

---

## Routers y Service Layer (dual pattern)

```python
# routes/reservations.py — thin
@router.get("/reservations/{booking_id}", response_model=ReservationResponse)
async def get_(
    booking_id: str,
    _user: Annotated[User, Depends(require_role(["recepcion", "gerente"]))],
) -> ReservationResponse:
    raw = await service.get_by_booking_id(booking_id)
    if raw is None:
        raise HTTPException(404, f"Booking {booking_id} not found")
    safe = to_json_safe(raw)  # belt-and-suspenders pre-clean
    return ReservationResponse.model_validate(safe)
```

```python
# service/queries.py — returns raw Mongo docs
async def get_by_booking_id(booking_id: str) -> dict | None:
    return await db.booking_orders.find_one({"booking_id": booking_id})
```

Si `assigned_rooms` viene como `list[dict]` post-migration y la route debe mantener wire shape `list[str]`, ver §A.

---

## Anti-Patterns (HotelData)

```python
# MAL: colapsar banner con class declaration
# ─── Pydantic *Response ───class XResponse(BaseModel):     ← todo después de # es comentario
#     la clase NO se agrega al módulo; model_rebuild() después → PydanticUndefinedAnnotation

# BIEN: banner solo, blank line, clase en su propia línea
# ─── Pydantic *Response ───

class XResponse(BaseModel):
    ...


# MAL: usar to_id_str() helper que se reintrodujo y luego se revirtió
return {"id": to_id_str(doc)}                              # NO reintroducir — ver §history del knowledge.md

# BIEN: dejar que Pydantic *Response haga la conversión
class ReservationResponse(BaseModel):
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
return ReservationResponse.model_validate(doc)


# MAL: str(x['_id']) en cada callsite (33 sites restantes aún en instay/billing/expenses/etc)
#     NO migrar más a esto. Migrar a *Response.

# MAL: import src.app en DAGs Airflow (rompe §II test_dag_boundaries)

# MAL: docker compose down --volumes o docker volume rm mongo_data
#     Docker Safety Rule, jamás, ni siquiera en rollback

# MAL: forgot model_rebuild() tras modificar validación/serialización aliases

# MAL: usar MongoClientSingleton (hallucinado — no existe en el codebase)

# MAL: module-level global `db = MongoClient(...)` (rompe test fixtures + worker restart)
#     REAL pattern: `from src.database.connection import get_database` lazy pool
```

---

## Best Practices (HotelData)

- **Wire shape siempre en `*Response`**, nunca en dict retornado directamente desde route.
- **Dual defense**: `ObjectIdStr` per-model + `jsonable_encoder` monkey-patch global. Ambos deben coexistir.
- **DI consolidada** via `Annotated[T, Depends(...)]` type aliases: `DbDep`, `CurrentUserDep`, `ActiveUserDep`.
- **Cache-clear ritual** después de delete/mutation de `*Response` (ver §D).
- **`from __future__ import annotations`** en TODO módulo que tenga `response_model=...`.
- **Banner de sección separado del `class X(BaseModel):` por blank line, SIEMPRE**.
- **Test isolation**: drop entire `hoteldata_hub_test` antes de cada test (autouse fixture).
- **Imports absolutos** desde `src.*` (NO relative).
- **DECENTRALIZED bootstrap** en lifespan — cada módulo owns su `ensure_*_collections(db)` call (no central MongoClientSingleton).

---

## Smoke Test Post-Authoring (cómo verificar que escribiste bien el skill)

### Status codes esperados al testear `/api/reservations/<id>`:

| HTTP code | Significa | Clasificación |
|---|---|---|
| `200` | booking exists + auth válido + wire shape correcto | ✅ PASS — skill bien aplicado |
| `401` | server alive + endpoint reachable + auth gate funciona | ✅ PASS Preliminar (server health check) |
| `403` | auth válido pero role insuficiente | ✅ PASS — role guard funciona |
| `404` | booking_id no existe | ✅ PASS — wire shape correcto |
| `500` con `TypeAdapter not fully defined` | **Falla §A + §B3** | ❌ FAIL — falta `model_rebuild()` después de las *Response |
| `500` con `PydanticUndefinedAnnotation` | **Falla §B1** (banner-collapse) | ❌ FAIL — banner colapsado |
| `500` con `ImportError: cannot import name 'XResponse'` post-merge | **Falla §D** (cache stale) | ❌ FAIL — falta `__pycache__` clear + restart |
| `500` con Mongo object serialization error | **Falla §A** (ObjectId leak) | ❌ FAIL — falta `ObjectIdStr` o pre-clean |

### Comando de verificación:

```bash
docker compose -f infra/docker-compose.yml exec -T server \
  python -m pytest -q server/tests/test_reservations.py -k "test_get or test_list"
```

Si pasa, el skill refleja el comportamiento esperado del código. Si falla con uno de los 500s ↑, **es un bug del skill o del route, no del test**. Volver a leer §A-§D y comparar contra `server/src/app/main.py` + `server/src/app/core/types.py`.

---

## References internas (cross-verificadas post-reviewer)

- `knowledge.md` §API convention + §Docker Safety Rules + §Cache-clear ritual
- `.specify/memory/constitution.md` §I/§II/§V/§VII/§9/§14
- `.specify/decisions/ADR-0002-poach-fastapi-patterns.md` (este skill es el artefacto principal del ADR)
- `server/src/app/core/types.py` (ObjectIdStr / ListToCommaStr / to_json_safe — canónico)
- `server/src/app/main.py` (create_app + lifespan + **jsonable_encoder monkey-patch** líneas 17-44)
- `server/src/database/connection.py` (get_database — MongoClient lazy singleton)
- `server/src/app/modules/partner/services/_inventory.py` (atomic layer decrement — patrón §E)
- ECC origin: `https://github.com/affaan-m/ECC/tree/main/skills/fastapi-patterns` (MIT-licensed, adaptation 2026-07-28)

---

**Versión**: 1.1 (post-reviewer fixes) | **Ratificada**: 2026-07-28 | **Mantenimiento**: cuando cambie §A/B/C/D de la Constitución o cuando aterrice nuevo ADR; también trimestral contra upstream ECC
