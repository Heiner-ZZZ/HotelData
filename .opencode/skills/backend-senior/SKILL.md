---
name: backend-senior
description: Use when designing, reviewing, or refactoring FastAPI backend code. Covers application factory pattern, modular routers, service layer, Pydantic v2, MongoDB patterns, dependency injection, async, testing, error handling, and production deployment with Uvicorn/Gunicorn.
---

# Senior Backend Engineer — FastAPI + Python 3.12

## 2026 Stack
- **FastAPI** 0.115+ / Python 3.12+
- **Starlette** 1.0.0 (stable ASGI foundation)
- **Pydantic v2** (model_config, BeforeValidator, computed fields)
- **MongoDB** 7+ via `pymongo` (sync driver — FastAPI sync routes are fine)
- **Redis** via `redis-py` for caching + rate limiting
- **Auth**: Session-based with `passlib[bcrypt]` + `httpOnly` cookies
- **Testing**: `pytest` + `httpx.AsyncClient` + `mongomock`
- **Deploy**: Uvicorn (multi-worker via Gunicorn) in Docker

## Architecture Principles

### 1. Application Factory Pattern
```python
def create_app() -> FastAPI:
    app = FastAPI(title="HotelData Hub", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=[...])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[...])
    app.mount("/static", StaticFiles(directory=...), name="static")

    # Register routers — order matters (specific before generic)
    app.include_router(dashboard_router)
    app.include_router(auth_web_router)
    app.include_router(auth_api_router)
    app.include_router(admin_router)
    # ... one per module

    @app.on_event("startup")
    def _seed():
        ensure_default_catalogs()
        ensure_user_status_field()

    return app

app = create_app()
```

### 2. Modular Router Organization (This Project)
```
routes.py    → HTTP only (parse request, call service, return response)
service.py   → Business logic (orchestration, validation, domain rules)
```

Each domain has 1–3 routers depending on interface:
```python
web_router = APIRouter(prefix="/auth", tags=["auth"])           # Jinja2 HTML
api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])   # JSON API
router = APIRouter(prefix="/modules/auth", tags=["modules"])    # Internal
```

### 3. Service Layer Patterns
Routes are thin — delegate to services immediately:
```python
@api_router.post("/login")
def login_api(request: Request, payload: dict = Body(...)):
    identifier = str(payload.get("identifier") or "").strip()
    password = str(payload.get("password") or "")
    # ... validation then:
    user = find_user_by_identifier(db, identifier)
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")
    token = create_user_session(db, user, request)
    return JSONResponse(_auth_payload(user, session, home_href))
```

### 4. Pydantic v2 Best Practices
```python
class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )
    id: str = Field(alias="_id")
    username: str
    email: EmailStr
    is_active: bool
    primary_role: str
```

### 5. MongoDB Patterns
```python
def get_database() -> Database:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        yield client[settings.mongo_database]
    finally:
        client.close()

@api_router.get("/users")
def list_users(db: Database = Depends(get_database)):
    return list(db.users.find({}, {"password_hash": 0}).sort("created_at", -1))
```

**Index strategy:**
- Every collection needs at minimum: `_id` (auto) + query/join fields
- Unique indexes on `username`, `email`, `session_token`
- Compound indexes on `(tenant_id, created_at)` for multi-tenant queries
- Use `hint()` in production queries to force index usage

### 6. Error Handling
```python
# Consistent error response shape
raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={
    "authenticated": False,
    "login_url": "/login",
})

# Custom error classes for domain logic
class BusinessRuleError(Exception):
    def __init__(self, message: str, code: str = "business_rule"):
        self.message = message
        self.code = code
```

### 7. Async vs Sync Decision
| Scenario | Use |
|---|---|
| CPU-bound computation | `def` (sync) — FastAPI runs in threadpool |
| I/O bound (DB queries) | `def` for MongoDB (sync driver), `async def` for HTTP calls |
| Mixed | `async def` with `run_in_executor` for blocking calls |
| Long-lived connections | `async def` with websockets |

### 8. Configuration Management
```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "hoteldata_hub"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_enabled: bool = False
    pocketbase_url: str = "http://localhost:8090"
    debug: bool = False
```

### 9. Session Auth Pattern
```python
# Security model (this project)
SESSION_COOKIE_NAME = "hoteldata_session"

def create_user_session(db, user, request) -> str:
    token = secrets.token_urlsafe(48)
    db.user_sessions.insert_one({
        "user_id": user["_id"],
        "session_token": token,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", ""),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8),
    })
    return token

def verify_password(plain: str, hashed: str) -> bool:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain, hashed)
```

### 10. Testing
```python
# tests/conftest.py
from httpx import AsyncClient
from src.app.main import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Test route
@pytest.mark.asyncio
async def test_login(client):
    response = await client.post("/api/auth/login", json={
        "identifier": "superadmin",
        "password": "Admin12345*"
    })
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
```

### 11. Production Deployment
```
Server:   Uvicorn behind Gunicorn (multi-worker)
Workers:  2 * CPU cores + 1
Graceful shutdown: 30s timeout
Health check: GET /api/health → 200
Logging: JSON structured logs (loguru or structlog)
Monitoring: Prometheus metrics via starlette-exporter
```

### 12. Common Pitfalls
- ❌ `async def` with synchronous MongoDB — use `def` instead
- ❌ Importing `Request` in service layer — services get plain params
- ❌ Hardcoding collection names — use constants/settings
- ❌ No indexes on query fields — O(n) scans on every request
- ❌ `Session` per request without `finally` — connection leak
- ❌ `allow_origins=["*"]` in CORS — specify exact origins
- ❌ **`service.py` > 400 lines or mixing 2+ sub-domains → god class (see §13)**
- ❌ 4+ routers per module with no clear ownership
- ❌ Cross-module coupling via free functions (use `Depends()` or protocols)

---

## 13. Scalability via Sectioning (anti god-class)

> **Core idea:** scalability in a modular monolith is not "more code per file" —
> it is **composition of small files with clear contracts**. A 1800-line
> `service.py` is a 2000s monolith wearing a 2026 suit. Section early.

### 13.1 Hard thresholds (review-time gates)

If any of these is true in a code review, the PR **must** split the file
or the reviewer blocks it:

| Metric | Threshold | Action |
|---|---|---|
| Lines in any `service.py` | > 400 | Split into `services/` package |
| Top-level functions in a single file | > 15 | Split by sub-domain |
| Distinct MongoDB collections touched | > 3 | Extract repositories (§14) |
| Distinct sub-domains in one file | > 1 (e.g. "rooms" + "rates" + "content") | Split into sibling files |
| Routers per module | > 3 without a documented reason | Consolidate to 1 `api_router` + 1 `web_router` |
| Cyclic imports between modules | any | Break with sub-domain split |

### 13.2 The sectioning pattern

When a `service.py` exceeds 400 lines or mixes sub-domains, replace it
with a package:

```
src/app/modules/<bounded_context>/
├── __init__.py
├── routes.py              # thin: parse, validate, call services, format
├── schemas.py             # Pydantic models
└── services/              # NEW: one file per sub-domain
    ├── __init__.py        # re-exports public API (the "facade")
    ├── _common.py         # cross-cutting helpers (no peer imports)
    ├── bootstrap.py       # ensure_*_collections, module_status
    ├── <sub_domain_a>.py  # one bounded concern
    ├── <sub_domain_b>.py
    └── ...
```

**Sub-domain split** is by *change frequency* and *data ownership*, not
by function name. Examples:

| Sub-domain | Owns | Touches |
|---|---|---|
| `properties` | `dim_hotels`, `hotel_profile_changes` | hotel identity, list, performance |
| `content` | `hotel_content_pages`, `hotel_images`, `hotel_policies`, `hotel_content_changes` | content, amenities, images |
| `rooms` | `room_types`, `hotel_rooms`, `room_inventory_calendar`, `blackout_dates` | inventory ops |
| `rates` | `rate_plans`, `hotel_rate_calendar`, `rate_rules`, `promotion_campaigns`, `coupon_codes` | rate plans |
| `dashboard` | (read-only) | aggregations from all of the above |
| `bootstrap` | `ensure_*_collections` + `module_status` | idempotent schema setup |
| `_common` | `safe_int`, `money`, `number`, `slugify`, `register_content_change`, `active_fact_collection` | formatting + cross-cutting |

### 13.3 Dependency rules (no cycles)

```
_common  →   (nothing in package)
bootstrap →  _common
<sub>     →  _common, bootstrap, peer modules (NEVER upward)
routes.py → services.<sub>.*    (NEVER services.service import the old facade)
```

If `<sub_a>` needs a function in `<sub_b>`:
- It is probably a sign that one of them owns the wrong concern. Move it.
- If it really must cross, **lazy-import inside the function**, not at
  module top, to break the load-time cycle:

```python
def save_partner_hotel_profile(prop_id: int, ...):
    from src.app.modules.partner.services.content import content_page_for_prop
    ...
```

### 13.4 Public API stability — the `__init__.py` facade

Callers (routes.py, scripts/, other modules) should import from the
package, not from individual sub-files:

```python
# GOOD: stable surface, easy to refactor internals later
from src.app.modules.partner.services import list_partner_hotels

# BAD: leaks internal layout, breaks when you rename a sub-file
from src.app.modules.partner.services.properties import list_partner_hotels
```

The facade also serves as the explicit **public API contract**:

```python
# services/__init__.py
__all__ = [
    "add_partner_hotel_image",
    "create_blackout_block",
    "create_rate_plan",
    # ... full list, alphabetized
]
```

Anything *not* in `__all__` is internal, can change without notice, and
must start with `_` (or live in `_common.py` / `_views.py`).

### 13.5 Worked example from this repo

Before (the antipattern):
```
src/app/modules/partner/service.py     1834 lines
  ├── 78 functions
  ├── 5 sub-domains: properties, content, rooms, rates, dashboard
  ├── 4 routers in routes.py importing 30+ functions
  └── 6 external callers (reservations, revenue, 4 scripts)
```

After (the fix):
```
src/app/modules/partner/
├── routes.py                          587 lines (unchanged functionally)
├── schemas.py                           6
└── services/
    ├── __init__.py                    public facade
    ├── _common.py                      99  formatters + cross-cutting
    ├── bootstrap.py                   166  ensure_*_collections
    ├── properties.py                  426  list/detail/performance/profile
    ├── content.py                     355  content/amenities/policies/images
    ├── rooms.py                       268  rooms/inventory/blackout
    ├── rates.py                       162  rate plans/calendar
    └── dashboard.py                   308  flags/reports/dashboard
```

Verification gates (must all pass before merge):
- `python -c "import src.app.main"` loads with no exceptions
- `python -m pytest -q` green
- `grep -r "from src.app.modules.partner.service import" .` returns nothing
- Smoke: hit one endpoint per refactored sub-domain via `httpx.AsyncClient`

### 13.6 Why not just split `service.py` into more files in the same dir?

You can, but a package signals intent: a folder named `services/`
communicates "this is a sub-domain cluster, not a pile of utilities".
A flat `service_helpers.py` + `service_rooms.py` + `service_rates.py` is
harder to test, easier to litter, and weaker as a unit of ownership.

### 13.7 Tests are the safety net for sectioning

Splitting a 1800-line file into 7 is high-risk without tests. Before
sectioning:

1. Add a smoke test that exercises each public function once (even just
   `assert callable(fn)` is better than nothing).
2. Run pytest. If green, proceed.
3. After sectioning, run pytest again. Any failure is a missing import
   or a circular dependency.

See `backend-senior` §10 for the test pattern.

### 13.8 Code-review checklist (anti-god-class)

```
[ ] No `service.py` > 400 lines
[ ] No file mixes 2+ sub-domains
[ ] `services/__init__.py` re-exports the full public API
[ ] No top-level imports between sibling sub-files (only lazy if needed)
[ ] `routes.py` imports from `services`, not from `service`
[ ] Scripts import from `services`, not from `service`
[ ] `grep "<module>.service\b" <module>/` returns no hits
[ ] `python -c "import src.app.main"` loads
[ ] pytest green
[ ] No new file > 500 lines
```
