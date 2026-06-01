# Frontend Migration Status

## Current State

HotelData is in a hybrid state:

- FastAPI is still the backend source of truth for data, auth, session and legacy HTML.
- Angular is the target frontend architecture under `frontend/`.
- Legacy Jinja routes remain active while the JSON contract is expanded for Angular.

## What Is Ready in Backend

### Session / auth

- `GET /auth/login` and `POST /auth/login` remain the legacy cookie login flow.
- `GET /api/auth/me` now exists as the Angular session probe.
- Unauthenticated API calls now return JSON `401` instead of HTML redirect.

### Public traveler JSON

- `GET /api/hotels/search`
- `GET /api/hotels/{prop_id}`

### Reservations / account JSON

- `GET /api/reservations`
- `GET /api/reservations/options`
- `POST /api/reservations`
- `GET /api/reservations/{booking_id}`
- `POST /api/reservations/{booking_id}/cancel`

### Management JSON

- `GET /api/dashboard/overview`
- `GET /api/management/properties`
- `GET /api/management/properties/{prop_id}`
- `GET /api/management/rooms?prop_id=...`
- `GET /api/management/availability?prop_id=...`
- `GET /api/management/rates?prop_id=...`
- `POST /api/management/rates/plans`
- `POST /api/management/rates/calendar`
- `GET /api/management/policies?prop_id=...`
- `PUT /api/management/policies`
- `GET /api/management/amenities?prop_id=...`
- `PUT /api/management/amenities`

## What Still Remains in Jinja

These flows still have their primary UI in legacy HTML:

- `/hotels/search`
- `/hotels/{prop_id}`
- `/reservations*`
- `/partner/hotels*`
- `/revenue/*`
- `/dashboard`

## What Is Still Missing for Angular

- Check-ins JSON contract
- Check-outs JSON contract
- Availability write endpoint
- Rooms write endpoint
- System/backoffice JSON contract

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

## Proxy / CORS Baseline

- `frontend/proxy.conf.json` routes:
  - `/api` -> `http://127.0.0.1:8000`
  - `/auth` -> `http://127.0.0.1:8000`
  - `/system` -> `http://127.0.0.1:8000`
- FastAPI allows credentialed CORS from:
  - `http://127.0.0.1:4200`
  - `http://localhost:4200`

## Current Risk

The Angular source tree is still missing from this checkout.

Missing source artifacts include:

- `frontend/src/`
- `frontend/package.json`
- `frontend/angular.json`

Only cache/build/dependency artifacts are present:

- `frontend/.angular`
- `frontend/dist`
- `frontend/node_modules`

Because of that, these frontend tasks are still blocked in source code:

- adding `withCredentials` to real Angular services
- wiring `ng serve --proxy-config proxy.conf.json` in package scripts
- registering an auth interceptor
- creating a real auth guard
- updating Angular route definitions

There is also an operational caveat:

- the backend currently responding on `http://127.0.0.1:8000` may still be an older running process
- after pulling these code changes, the backend stack must be restarted before `/api/*` begins returning the new JSON auth behavior

## Recommended Next Step

Restore the Angular source tree into `frontend/`, then wire the new backend contracts into real services, guards, interceptors and route modules.
