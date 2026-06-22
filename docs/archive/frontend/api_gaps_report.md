# API Gaps Report

## Scope

This report reflects the current Angular + FastAPI contract in this workspace.

- FastAPI remains the source of truth.
- Legacy Jinja pages remain active.
- Angular source is present again under `frontend/src`.

## Contract Matrix

| Angular route | Backend endpoint | Exists | Returns JSON | Requires session | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `/login` | `GET /api/auth/me` | yes | yes | no for probe | ok | Used by guard/interceptor as session probe; unauthenticated should return `401` JSON. |
| `/search` | `GET /api/hotels/search` | yes | yes | no | ok | Public traveler search. |
| `/hotels/:hotelId` | `GET /api/hotels/{prop_id}` | yes | yes | no | ok | Public hotel detail. |
| `/account/bookings/new` | `GET /api/reservations/options` | yes | yes | yes | ok | Booking form options. |
| `/account/bookings/new` | `POST /api/reservations` | yes | yes | yes | ok | Create booking request. |
| `/account/bookings/:bookingId` | `GET /api/reservations/{booking_id}` | yes | yes | yes | ok | Booking detail. |
| `/management` | `GET /api/dashboard/overview` | yes | yes | yes | ok | Main management dashboard. |
| `/management/reservations` | `GET /api/reservations` | yes | yes | yes | ok | Reuses reservations list. |
| `/management/check-ins` | `GET /api/management/check-ins?date=...` | yes | yes | yes | ok | Uses reservation data plus operational stay status. |
| `/management/check-ins` | `POST /api/management/check-ins/{booking_id}/complete` | yes | yes | yes | ok | Front-desk operational state change. |
| `/management/check-outs` | `GET /api/management/check-outs?date=...` | yes | yes | yes | ok | Uses reservation data plus operational stay status. |
| `/management/check-outs` | `POST /api/management/check-outs/{booking_id}/complete` | yes | yes | yes | ok | Front-desk operational state change. |
| `/management/properties` | `GET /api/management/properties` | yes | yes | yes | ok | Management property list. |
| `/management/properties/:propertyId` | `GET /api/management/properties/{prop_id}` | yes | yes | yes | ok | Management property detail. |
| `/management/availability` | `GET /api/management/availability?prop_id=...` | yes | yes | yes | ok | Availability snapshot. |
| `/management/availability` | `PATCH /api/management/availability` | yes | yes | yes | ok | Inventory update. |
| `/management/rooms` | `GET /api/management/rooms?prop_id=...` | yes | yes | yes | ok | Room types list. |
| `/management/rooms` | `POST /api/management/rooms` | yes | yes | yes | ok | Room type creation. |
| `/management/rates` | `GET /api/management/rates?prop_id=...` | yes | yes | yes | ok | Rates overview. |
| `/management/rates` | `POST /api/management/rates/plans` | yes | yes | yes | ok | Rate plan creation. |
| `/management/rates` | `POST /api/management/rates/calendar` | yes | yes | yes | ok | Rate calendar update. |
| `/management/policies` | `GET /api/management/policies?prop_id=...` | yes | yes | yes | ok | Hotel policies detail. |
| `/management/policies` | `PUT /api/management/policies` | yes | yes | yes | ok | Hotel policies update. |
| `/management/amenities` | `GET /api/management/amenities?prop_id=...` | yes | yes | yes | ok | Amenities detail. |
| `/management/amenities` | `PUT /api/management/amenities` | yes | yes | yes | ok | Amenities update. |
| `/system` | legacy `/system/*` routes | partial | mixed | yes | gap | Angular shell exists, but JSON contract map for system operations is still incomplete. |

## Remaining Gaps

1. System/backoffice JSON contracts are still only partial.
2. Availability, rooms and rates can still grow richer write flows, but the current Angular screens already have working minimal JSON contracts.
3. End-to-end authenticated browser validation still depends on restarting the running backend if an older process is serving stale code.
