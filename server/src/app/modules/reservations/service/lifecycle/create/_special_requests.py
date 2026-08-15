"""Special-request validation and charge generation for booking creation.

Validates the guest's selected special requests against the hotel's real
configuration before a booking is created:

- ``pet_related`` requests are checked against the hotel-wide ``pets_allowed``
  policy; disallowed pets block the booking with the ``pet_policy`` text.
- ``high_floor`` requests are checked against the assigned room's ``floor``
  and the hotel's ``high_floor_from`` threshold; a room below the threshold
  blocks the booking (the request can't be honored).

Priced requests (``chargeable`` with unit_price > 0) generate an automatic
additional charge, mirroring paid amenities.
"""
from __future__ import annotations

import logging
from typing import Any

from src.app.modules.partner.services._common import normalize_label
from src.app.modules.partner.services.content.special_requests import (
    special_requests_lookup,
)
from src.database.connection import get_database

logger = logging.getLogger(__name__)

_DEFAULT_HIGH_FLOOR_FROM = 3

# Hora (HH:MM, inclusiva) a partir de la cual una llegada se considera tardía
# cuando el huésped da una hora estimada de llegada pero no marcó la petición
# "Llegada tarde". Convención hotelera estándar (~20:00).
LATE_CHECKIN_THRESHOLD = "20:00"


def resolve_late_checkin(
    prop_id: int,
    special_requests: list[str] | None,
    estimated_arrival_time: str,
) -> bool:
    """Whether a reservation is a late check-in.

    True when the guest selected a special request flagged ``late_arrival`` in
    the hotel catalog (default label "Llegada tarde"), or when the estimated
    arrival time is at/after ``LATE_CHECKIN_THRESHOLD`` (20:00).
    """
    selected = [str(s).strip() for s in (special_requests or []) if str(s).strip()]
    if selected:
        lookup = special_requests_lookup(prop_id)
        for raw in selected:
            entry = lookup.get(normalize_label(raw))
            if entry and entry.get("late_arrival"):
                return True
    arrival = (estimated_arrival_time or "").strip()
    return bool(arrival and arrival >= LATE_CHECKIN_THRESHOLD)


def validate_special_requests(
    prop_id: int,
    hotel_room_id: str,
    special_requests: list[str] | None,
) -> str | None:
    """Return an error message if any selected request can't be honored, else None.

    Unknown labels are informational (stored as free text, not validated).
    """
    selected = [str(s).strip() for s in (special_requests or []) if str(s).strip()]
    if not selected:
        return None

    lookup = special_requests_lookup(prop_id)
    db = get_database()

    for raw in selected:
        entry = lookup.get(normalize_label(raw))
        if not entry:
            continue

        if entry["pet_related"]:
            policy = db.hotel_policies.find_one(
                {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
                {"_id": 0, "pets_allowed": 1, "pet_policy": 1},
            )
            pets_allowed = bool(policy.get("pets_allowed", True)) if policy else True
            if not pets_allowed:
                msg = "El hotel no admite mascotas."
                pet_text = str((policy or {}).get("pet_policy") or "").strip()
                if pet_text:
                    msg += f" {pet_text}"
                return msg

        if entry["high_floor"]:
            if not hotel_room_id:
                return "La petición de piso alto requiere seleccionar una habitación específica."
            page = db.hotel_content_pages.find_one(
                {"prop_id": prop_id},
                {"_id": 0, "high_floor_from": 1},
            )
            try:
                threshold = int((page or {}).get("high_floor_from") or _DEFAULT_HIGH_FLOOR_FROM)
            except (ValueError, TypeError):
                threshold = _DEFAULT_HIGH_FLOOR_FROM
            room = db.hotel_rooms.find_one(
                {"prop_id": prop_id, "hotel_room_id": hotel_room_id},
                {"_id": 0, "floor": 1, "room_label": 1},
            )
            # ``floor`` llega como int o string (datos reales mezclan ambos).
            try:
                floor = int((room or {}).get("floor"))
            except (ValueError, TypeError):
                floor = None
            if floor is None or floor < threshold:
                label = str((room or {}).get("room_label") or hotel_room_id)
                floor_txt = str(floor) if floor is not None else "desconocido"
                return (
                    f"La petición de piso alto no puede cumplirse: la habitación {label} "
                    f"está en el piso {floor_txt} y el hotel reserva pisos altos desde el {threshold}."
                )

    return None


def _generate_special_request_charges(
    *,
    booking_id: str,
    prop_id: int,
    selected_requests: list[str] | None,
) -> list[dict[str, Any]]:
    """Generate an additional charge for each priced (chargeable) request."""
    selected = [str(s).strip() for s in (selected_requests or []) if str(s).strip()]
    if not selected:
        return []

    lookup = special_requests_lookup(prop_id)

    from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
    from src.app.modules.housekeeping.service.lifecycle.charges import (
        create_additional_charge,
    )

    created: list[dict[str, Any]] = []
    for raw in selected:
        entry = lookup.get(normalize_label(raw))
        if not entry or not entry["chargeable"]:
            continue
        unit_price = entry["unit_price"]
        if unit_price <= 0:
            continue
        try:
            charge_payload = AdditionalChargeCreate(
                booking_id=booking_id,
                prop_id=prop_id,
                concept=f"Petición especial: {raw}",
                amount=unit_price,
                quantity=1,
                note="Generado automáticamente al crear la reserva.",
            )
            charge_result = create_additional_charge(charge_payload)
            if charge_result:
                created.append(charge_result)
        except Exception:
            logger.exception("Failed to generate special-request charge for %s on booking %s", raw, booking_id)

    return created
