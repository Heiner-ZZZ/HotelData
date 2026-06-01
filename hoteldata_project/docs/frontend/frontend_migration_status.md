# Frontend Migration Status

## Current State

HotelData is in a hybrid but working migration state:

- FastAPI remains the backend source of truth for data, auth, session and legacy HTML.
- Angular is active under `frontend/` with `core`, `shared` and `features`.
- Legacy Jinja routes remain active while Angular consumes JSON contracts incrementally.

## Migrated Angular Areas

### Public

- `/search`
- `/hotels/:hotelId`

### Account

- `/account/bookings/new`
- `/account/bookings/:bookingId`

### Management

- `/management`
- `/management/reservations`
- `/management/check-ins`
- `/management/check-outs`
- `/management/properties`
- `/management/properties/:propertyId`
- `/management/availability`
- `/management/rooms`
- `/management/rates`
- `/management/policies`
- `/management/amenities`

### System

- `/system` shell exists
- detailed system JSON contracts are still incomplete

## What Still Remains Primarily in Jinja

- legacy `/auth/*` screens
- `/dashboard`
- `/partner/*`
- `/revenue/*`
- legacy reservation HTML routes

These remain intentionally active as compatibility surfaces during migration.

## Session / Auth Integration

- Angular uses `/api/auth/me` as the session probe.
- Protected Angular routes use `auth.guard.ts`.
- Angular now has a login wrapper at `/login` that redirects to legacy `/auth/login`.
- `auth.interceptor.ts` applies `withCredentials` on `/api`, `/auth` and `/system` calls and redirects to `/login` on private `401/403`.

## Local Development Flow

### Backend

```powershell
docker compose -f docker-compose.local-mongo.yml up -d mongo redis app
```

### Frontend

```powershell
cd frontend
npm start
```

`npm start` now uses:

```text
ng serve --proxy-config proxy.conf.json
```

## Current Risks

1. If a stale FastAPI process is still running, `/api/*` may keep returning old HTML redirect behavior until the backend is restarted.
2. The `system` experience still needs a cleaner JSON contract map.
3. Some operational fields such as exact room assignment, ETA or guest balance still depend on data actually existing in Mongo; where absent, Angular uses honest fallbacks.

## Next Steps

1. Restart backend stack so runtime matches current code.
2. Run `scripts/validate_frontend_backend_contract.py`.
3. Validate authenticated navigation for:
   - `/management`
   - `/management/check-ins`
   - `/management/check-outs`
   - `/management/properties`
   - `/management/rates`
4. Continue with `system` or guest-facing operational views on top of the now-stable contracts.
