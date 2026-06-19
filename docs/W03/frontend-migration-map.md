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
  - Legacy JSON alias kept: `GET /api/admin/properties`
  - Legacy HTML kept: `GET /partner/hotels`
- Angular target: `/management/properties/:propertyId`
  - Backend JSON: `GET /api/management/properties/{prop_id}`
  - Legacy JSON alias kept: `GET /api/admin/properties/{prop_id}`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}`
- Angular target: `/management/rooms`
  - Backend JSON:
    - `GET /api/management/rooms/options`
    - `GET /api/management/rooms?prop_id=...`
    - `POST /api/management/rooms`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}/rooms`
- Angular target: `/management/availability`
  - Backend JSON:
    - `GET /api/management/availability/options`
    - `GET /api/management/availability?prop_id=...`
    - `PATCH /api/management/availability`
  - Legacy HTML kept: `GET /partner/hotels/{prop_id}/inventory`
- Angular target: `/management/rates`
  - Backend JSON:
    - `GET /api/management/rates/options`
    - `GET /api/management/rates?prop_id=...`
    - `POST /api/management/rates/plans`
    - `POST /api/management/rates/calendar`
  - Legacy HTML kept: `GET /revenue/hotel/{prop_id}/rates`
- Angular target: `/management/policies`
  - Backend JSON:
    - `GET /api/management/policies/options`
    - `GET /api/management/policies?prop_id=...`
    - `PUT /api/management/policies`
  - Legacy HTML kept: `GET/POST /partner/hotels/{prop_id}/policies`
- Angular target: `/management/amenities`
  - Backend JSON:
    - `GET /api/management/amenities/options`
    - `GET /api/management/amenities?prop_id=...`
    - `PUT /api/management/amenities`
  - Legacy HTML kept: `GET/POST /partner/hotels/{prop_id}/content/edit`
- Angular target: `/management/check-ins`
  - Backend JSON:
    - `GET /api/management/check-ins?date=...`
    - `POST /api/management/check-ins/{booking_id}/complete`
  - Legacy HTML kept: none dedicated; powered by reservations data
- Angular target: `/management/check-outs`
  - Backend JSON:
    - `GET /api/management/check-outs?date=...`
    - `POST /api/management/check-outs/{booking_id}/complete`
  - Legacy HTML kept: none dedicated; powered by reservations data

## Still In Progress

These Angular-targeted contracts are still missing in the current backend snapshot:

- richer management write endpoints for:
  - room updates and deactivation flows
  - rate calendar bulk edit ergonomics

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

## Frontend State

The Angular source tree is present again in `frontend/`, and the route architecture is now being aligned to the intended product split:

- `public`
- `account`
- `management`
- `system`

Current frontend status:

- public traveler routes are active
- account shell is restored
- management shell is restored
- system admin shell is restored
- management dashboard is now mounted from `features/management/pages/dashboard-page`
- `/admin` remains only as a legacy alias toward `/management`
- reservations are available both as legacy public alias (`/reservations`) and account path (`/account/bookings`)
- properties are migrated under `/management/properties`
- availability is active under `/management/availability`
- rooms are active under `/management/rooms`
- rates are active under `/management/rates`
- policies are active under `/management/policies`
- amenities are active under `/management/amenities`
- check-ins are active under `/management/check-ins`
- check-outs are active under `/management/check-outs`
