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
