# HotelData — Project Knowledge

## What is this?

**HotelData** is a modular hotel management platform (PMS + CRS + Booking Engine) built with Angular 22, FastAPI, and MongoDB. It covers daily hotel operations (check-in/out, housekeeping, billing, reservations), central reservation management (rates, availability, inventory), and a direct booking engine.

## Quickstart

```bash
# Full stack (Docker)
docker compose -f infra/docker-compose.yml up -d

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

### Docker rebuild rules

| Situation | Command |
|-----------|---------|
| Code changes (TS, HTML, Python) only | `docker compose -f infra/docker-compose.yml up -d <service>` — no rebuild needed |
| Dockerfile/package.json/requirements.txt changed | `docker compose -f infra/docker-compose.yml up -d --build <service>` |
| Stale cache / weird errors | `docker compose build --no-cache <service>` — slow, only when needed |

**NEVER** run `docker compose down --volumes` or `docker compose down -v`.

## Architecture

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | Angular 22, TypeScript 6.x, SCSS | Signals + OnPush, esbuild builder |
| Backend | FastAPI, Python 3.12 | Pydantic v2, async, uvicorn |
| Database | MongoDB 8.0 (replica set) | Port 27018, RS `rs0` |
| Analytics | ClickHouse | *Coming soon* |
| ETL | Airflow, PocketBase (legacy source) | GA03 pipeline, incremental mode |
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

## Backend Conventions

- FastAPI async routes with Pydantic v2 models
- MongoDB via PyMongo (MongoClient)
- Ruff for linting, MyPy for type checking, pytest for tests
- Permission-based access control (PBAC) via DB-backed navigation & permissions
- JWT auth with python-jose + bcrypt (passlib)

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
