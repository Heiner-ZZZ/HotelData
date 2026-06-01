# Frontend Migration Map

## Context

HotelData is in a split migration:

- FastAPI remains the source of truth for auth, session, data access and legacy Jinja routes.
- Angular is the intended frontend under `frontend/`.
- Legacy Jinja routes must remain active during the migration.

## Current Backend Contract

### Public traveler routes

- Angular target: `/search`
  - Backend JSON: `GET /api/hotels/search`
  - Legacy HTML kept: `GET /hotels/search`
- Angular target: `/hotels/:hotelId`
  - Backend JSON: `GET /api/hotels/{prop_id}`
  - Legacy HTML kept: `GET /hotels/{prop_id}`

### Account / reservations

- Angular target: `/account/bookings/new`
  - Backend JSON:
    - `GET /api/reservations/options`
    - `POST /api/reservations`
  - Legacy HTML kept: `GET/POST /reservations/new`
- Angular target: `/account/bookings/:bookingId`
  - Backend JSON: `GET /api/reservations/{booking_id}`
  - Legacy HTML kept: `GET /reservations/{booking_id}`

### Management

- Angular target: `/management`
  - Backend JSON: `GET /api/dashboard/overview`
  - Legacy HTML kept: `GET /dashboard`
- Angular target: `/management/properties`
  - Backend JSON: `GET /api/management/properties`
  - Legacy HTML kept: `GET /partner/hotels`
- Angular target: `/management/properties/:propertyId`
  - Backend JSON: `GET /api/management/properties/{prop_id}`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}`
- Angular target: `/management/rooms`
  - Backend JSON: `GET /api/management/rooms?prop_id=...`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}/rooms`
- Angular target: `/management/availability`
  - Backend JSON: `GET /api/management/availability?prop_id=...`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}/inventory`
- Angular target: `/management/rates`
  - Backend JSON: `GET /api/management/rates?prop_id=...`
  - Legacy HTML kept: `GET /revenue/hotel/{prop_id}/rates`
- Angular target: `/management/policies`
  - Backend JSON:
    - `GET /api/management/policies?prop_id=...`
    - `PUT /api/management/policies`
  - Legacy HTML kept: `GET/POST /partner/hotels/{prop_id}/policies`
- Angular target: `/management/amenities`
  - Backend JSON:
    - `GET /api/management/amenities?prop_id=...`
    - `PUT /api/management/amenities`
  - Legacy HTML kept: `GET/POST /partner/hotels/{prop_id}/content/edit`

## Still In Progress

These Angular-targeted contracts are still missing in the current backend snapshot:

- `/management/check-ins`
  - `GET /api/management/check-ins`
  - `POST /api/management/check-ins/{booking_id}/complete`
- `/management/check-outs`
  - `GET /api/management/check-outs`
  - `POST /api/management/check-outs/{booking_id}/complete`
- richer management write endpoints for:
  - rooms creation/update
  - availability patch/update
  - rate options and rate calendar ergonomics

## Session / Auth Contract

- Legacy HTML login remains:
  - `GET /auth/login`
  - `POST /auth/login`
- Angular session probe:
  - `GET /api/auth/me`
  - returns `401` JSON when there is no session
  - returns authenticated JSON when there is a valid session

## Proxy / Local Dev

- Backend stack:
  - `docker compose -f docker-compose.local-mongo.yml up -d mongo redis app`
- Frontend:
  - `cd frontend`
  - `npm start`
- Proxy baseline file:
  - `frontend/proxy.conf.json`
  - `/api`, `/auth`, `/system` -> `http://127.0.0.1:8000`

## Workspace Limitation

The current workspace snapshot still does not contain the Angular source tree itself (`frontend/src`, `frontend/package.json`, `frontend/angular.json`). Because of that, route guards, interceptors, service-level `withCredentials` and route registration cannot be patched safely in this checkout until the frontend sources are restored.
