# API Gaps Report

## Scope

This report reflects the current backend code in this workspace, not an assumed future Angular build.

- FastAPI remains the source of truth.
- Legacy Jinja pages remain active.
- Angular source files are still missing from this checkout, so this report focuses on backend JSON readiness.

## Contract Matrix

| Angular route | Backend endpoint | Exists | Returns JSON | Requires session | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `/login` or auth wrapper | `GET /api/auth/me` | yes | yes | no for probe, yes for authenticated payload | ok | Without session it returns `401` JSON; with session it returns the current user/session payload. |
| `/search` | `GET /api/hotels/search` | yes | yes | no | ok | Public JSON search endpoint now exists. |
| `/hotels/:hotelId` | `GET /api/hotels/{prop_id}` | yes | yes | no | ok | Public JSON hotel detail endpoint now exists. |
| `/account/bookings/new` | `GET /api/reservations/options` | yes | yes | yes | ok | Mounted in FastAPI. |
| `/account/bookings/new` | `POST /api/reservations` | yes | yes | yes | ok | Mounted in FastAPI. |
| `/account/bookings/:bookingId` | `GET /api/reservations/{booking_id}` | yes | yes | yes | ok | Mounted in FastAPI. |
| `/management` | `GET /api/dashboard/overview` | yes | yes | yes | ok | JSON dashboard overview now exists. |
| `/management/reservations` | `GET /api/reservations` | yes | yes | yes | ok | Reuses reservations API. |
| `/management/check-ins` | `GET /api/management/check-ins` | no | no | yes | falta endpoint | No JSON reception/check-in endpoint exists in this workspace snapshot. |
| `/management/check-ins` | `POST /api/management/check-ins/{booking_id}/complete` | no | no | yes | falta endpoint | Missing completion endpoint. |
| `/management/check-outs` | `GET /api/management/check-outs` | no | no | yes | falta endpoint | No JSON reception/check-out endpoint exists in this workspace snapshot. |
| `/management/check-outs` | `POST /api/management/check-outs/{booking_id}/complete` | no | no | yes | falta endpoint | Missing completion endpoint. |
| `/management/properties` | `GET /api/management/properties` | yes | yes | yes | ok | JSON management property list now exists. |
| `/management/properties/:propertyId` | `GET /api/management/properties/{prop_id}` | yes | yes | yes | ok | JSON management property detail now exists. |
| `/management/availability` | `GET /api/management/availability` | yes | yes | yes | ok | Requires `prop_id` query param. |
| `/management/availability` | `PATCH /api/management/availability` | no | no | yes | falta endpoint | Read contract exists; write contract still missing. |
| `/management/rooms` | `GET /api/management/rooms` | yes | yes | yes | ok | Requires `prop_id` query param. |
| `/management/rooms` | `POST /api/management/rooms` | no | no | yes | falta endpoint | No JSON room create/update endpoint yet. |
| `/management/rates` | `GET /api/management/rates` | yes | yes | yes | ok | Requires `prop_id` query param. |
| `/management/rates` | `POST /api/management/rates/plans` | yes | yes | yes | ok | Minimal JSON rate plan creation endpoint now exists. |
| `/management/rates` | `POST /api/management/rates/calendar` | yes | yes | yes | ok | Minimal JSON rate calendar update endpoint now exists. |
| `/management/policies` | `GET /api/management/policies` | yes | yes | yes | ok | Requires `prop_id` query param. |
| `/management/policies` | `PUT /api/management/policies` | yes | yes | yes | ok | Minimal JSON policy update endpoint now exists. |
| `/management/amenities` | `GET /api/management/amenities` | yes | yes | yes | ok | Requires `prop_id` query param. |
| `/management/amenities` | `PUT /api/management/amenities` | yes | yes | yes | ok | Minimal JSON content/amenities update endpoint now exists. |
| `/system` | legacy `/system/*` routes | partial | mostly HTML | yes | falta endpoint | System experience still lacks a dedicated Angular JSON contract map. |

## Session and CORS Notes

- Angular local dev should use `frontend/proxy.conf.json` so calls to `/api`, `/auth`, and `/system` stay same-origin from the browser point of view.
- FastAPI now allows CORS with credentials for:
  - `http://127.0.0.1:4200`
  - `http://localhost:4200`
- Unauthenticated `/api/*` requests now return JSON `401` instead of HTML redirect, which is friendlier for Angular guards/interceptors.
- If a currently running backend process still returns the legacy login HTML for `/api/*`, the process needs to be restarted to pick up these code changes.

## Highest Priority Remaining Gaps

1. Check-ins JSON endpoints
2. Check-outs JSON endpoints
3. Availability write endpoint
4. Rooms write endpoint
5. System/backoffice JSON contracts

## Angular Source Blocker

The current workspace still does not contain:

- `frontend/src/`
- `frontend/package.json`
- `frontend/angular.json`

So backend contracts can be prepared, but these frontend source tasks are still blocked in this checkout:

- route guard wiring
- interceptor registration
- `withCredentials` verification in actual services
- route protection wiring
