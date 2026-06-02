# Angular + FastAPI Contract Validation (Static)

## Scope
Static validation of Angular routing and API wiring against FastAPI contracts. No ETL/Airflow/Jinja legacy changes.

## Route Inventory (Angular)
Public shell:
- /login
- /search
- /hotels/:hotelId

Account shell (auth required):
- /account/bookings/new
- /account/bookings/:bookingId

Management shell (auth required):
- /management
- /management/reservations
- /management/check-ins
- /management/check-outs
- /management/properties
- /management/properties/:propertyId
- /management/availability
- /management/rooms
- /management/rates
- /management/policies
- /management/amenities

System shell (auth required):
- /system

## Endpoints Consumed (Angular)
Auth:
- /api/auth/me (session probe)
- /auth/login (redirect target from login shell)

Search + hotel detail:
- /api/hotels/search
- /api/hotels/:hotelId

Reservations:
- /api/reservations
- /api/reservations/options
- /api/reservations/:bookingId
- /api/reservations/:bookingId/cancel

Management dashboard:
- /api/dashboard/overview

Management: properties, availability, rooms, rates, policies, amenities
- /api/management/properties
- /api/management/properties/:propertyId
- /api/management/availability
- /api/management/availability/options
- /api/management/availability/blackouts
- /api/management/rooms
- /api/management/rooms/options
- /api/management/rates
- /api/management/rates/options
- /api/management/rates/plans
- /api/management/rates/calendar
- /api/management/policies
- /api/management/policies/options
- /api/management/amenities
- /api/management/amenities/options

Management: check-ins / check-outs
- /api/management/check-ins
- /api/management/check-ins/:bookingId/complete
- /api/management/check-outs
- /api/management/check-outs/:bookingId/complete

## Session Requirements
- Public (no auth guard): /login, /search, /hotels/:hotelId
- Requires session (auth.guard + /api/auth/me): /account/*, /management/*, /system/*

## Status
- Proxy and npm start wiring present.
- Auth interceptor uses withCredentials for /api, /auth, /system.
- Route map covers public, account, management, and system shells.

## Backend with Docker Desktop + Mongo local
Use MongoDB local in Windows. The compose does not define `mongo` and expects
`host.docker.internal:27017` inside the container.

```powershell
docker compose -f hoteldata_project/docker-compose.local-mongo.yml up -d redis app
```

Do not use:

```powershell
docker compose -f hoteldata_project/docker-compose.local-mongo.yml up -d mongo redis app
```

## Gaps / Pending
- /system area is partial: shell implementado, contratos JSON especificos pendientes.
- Runtime contract validation still pending on a running backend (Docker Desktop must be running and FastAPI reachable).
